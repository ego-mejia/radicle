from fastapi import APIRouter, Response

from radicle.docket.api.deps import CurrentPrincipal, Db
from radicle.docket.api.schemas.common import Page
from radicle.docket.api.schemas.fields import (
    CustomFieldCreate,
    CustomFieldOut,
    CustomFieldPatch,
    option_dicts,
)
from radicle.docket.api.serializers import fields_out
from radicle.docket.db.models import ProjectRole
from radicle.docket.services import custom_fields, templates
from radicle.docket.services.access import project_access

router = APIRouter(prefix="/projects/{key}/fields", tags=["custom fields"])

ADMIN = ProjectRole.admin


@router.get("", response_model=Page[CustomFieldOut])
async def list_fields(
    key: str, principal: CurrentPrincipal, db: Db, include_archived: bool = False
) -> Page[CustomFieldOut]:
    """Custom fields of the project, in display order."""
    access = await project_access(db, principal.user, key)
    fields = await custom_fields.list_fields(
        db, access.project.id, include_archived=include_archived
    )
    return Page(items=await fields_out(db, fields))


@router.post("", response_model=CustomFieldOut, status_code=201)
async def create_field(
    key: str, body: CustomFieldCreate, principal: CurrentPrincipal, db: Db
) -> CustomFieldOut:
    """Types: text, number, date, select, checkbox, user, url."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    await templates.ensure_editable(db, access.project)
    field = await custom_fields.create_field(
        db,
        access.project,
        custom_fields.FieldSpec(
            key=body.key,
            name=body.name,
            field_type=body.field_type,
            options=option_dicts(body.options),
            applies_to_types=body.applies_to_types,
            applies_to_areas=body.applies_to_areas,
        ),
    )
    return (await fields_out(db, [field]))[0]


@router.patch("/{field_key}", response_model=CustomFieldOut)
async def patch_field(
    key: str, field_key: str, body: CustomFieldPatch, principal: CurrentPrincipal, db: Db
) -> CustomFieldOut:
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    await templates.ensure_editable(db, access.project)
    field = await custom_fields.get_field(db, access.project, field_key)
    changes = custom_fields.FieldChanges(
        name=body.name,
        options=option_dicts(body.options),
        applies_to_types=body.applies_to_types,
        applies_to_areas=body.applies_to_areas,
        all_areas="applies_to_areas" in body.model_fields_set and body.applies_to_areas is None,
        position=body.position,
        archived=body.archived,
    )
    field = await custom_fields.update_field(db, access.project, field, changes)
    return (await fields_out(db, [field]))[0]


@router.delete("/{field_key}", status_code=204)
async def archive_field(key: str, field_key: str, principal: CurrentPrincipal, db: Db) -> Response:
    """Archives the field: tickets keep their values but they stop showing."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    await templates.ensure_editable(db, access.project)
    field = await custom_fields.get_field(db, access.project, field_key)
    await custom_fields.update_field(
        db, access.project, field, custom_fields.FieldChanges(archived=True)
    )
    return Response(status_code=204)
