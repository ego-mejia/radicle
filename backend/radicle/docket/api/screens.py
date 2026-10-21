from fastapi import APIRouter

from radicle.docket.api.schemas.screens import (
    FormSchemaOut,
    SchemaFieldOut,
    ScreenFieldOut,
    ScreenOut,
    ScreensPut,
)
from radicle.docket.db.models import ScreenOperation, TicketType, Transition
from radicle.docket.services import screens, templates
from radicle.docket.services.access import project_access
from radicle.docket.services.workflows import load_workflows
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Page
from radicle.platform.errors import ValidationFailed

router = APIRouter(prefix="/projects/{key}", tags=["screens"])


def _find_transition(
    transitions: list[Transition], ticket_type: TicketType, value: str
) -> Transition:
    wanted = value.strip().lower()
    for t in transitions:
        if (t.template_ref or "") == wanted or t.name.lower() == wanted:
            return t
    names = ", ".join(sorted({t.name for t in transitions})) or "none"
    raise ValidationFailed(
        f"Transition '{value}' does not exist for {ticket_type.value}. Transitions: {names}.",
        errors=[{"field": "transition", "message": "unknown"}],
    )


@router.get("/screens", response_model=Page[ScreenOut])
async def list_screens(key: str, principal: CurrentPrincipal, db: Db) -> Page[ScreenOut]:
    """Screens defined in the project. Operations without one use the defaults."""
    access = await project_access(db, principal.user, key)
    workflows = await load_workflows(db, access.project.id)
    by_id = {t.id: t for w in workflows.values() for t in w.transitions}
    items = []
    for s in await screens.list_screens(db, access.project.id):
        transition = by_id.get(s.transition_id) if s.transition_id else None
        items.append(
            ScreenOut(
                type=s.ticket_type,
                operation=s.operation,
                transition=transition.template_ref if transition else None,
                transition_name=transition.name if transition else None,
                fields=[ScreenFieldOut(**f) for f in s.fields],
            )
        )
    return Page(items=items)


@router.put("/screens", response_model=Page[ScreenOut])
async def put_screens(
    key: str, body: ScreensPut, principal: CurrentPrincipal, db: Db
) -> Page[ScreenOut]:
    """Replace every screen of an independent project."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    await templates.ensure_editable(db, access.project)
    workflows = await load_workflows(db, access.project.id)
    rows: list[screens.ScreenRow] = []
    seen: set[tuple[str, str, object]] = set()
    for screen in body.screens:
        transition_id = None
        if screen.operation is ScreenOperation.transition:
            if not screen.transition:
                raise ValidationFailed(
                    "Transition screens need `transition` (its ref or name).",
                    errors=[{"field": "transition", "message": "required"}],
                )
            transition_id = _find_transition(
                workflows[screen.type].transitions, screen.type, screen.transition
            ).id
        elif screen.transition:
            raise ValidationFailed(
                "Only transition screens name a transition.",
                errors=[{"field": "transition", "message": "not allowed"}],
            )
        marker = (screen.type.value, screen.operation.value, transition_id)
        if marker in seen:
            raise ValidationFailed(
                f"Two screens for {screen.type.value} {screen.operation.value}.",
                errors=[{"field": "screens", "message": "duplicate"}],
            )
        seen.add(marker)
        fields = screens.check_fields([f.model_dump() for f in screen.fields])
        rows.append((screen.type, screen.operation, transition_id, fields))
    await screens.replace_screens(db, access.project, rows)
    return await list_screens(key, principal, db)


@router.get("/schema", response_model=FormSchemaOut)
async def form_schema(
    key: str,
    type: TicketType,
    principal: CurrentPrincipal,
    db: Db,
    operation: ScreenOperation = ScreenOperation.create,
    transition: str | None = None,
) -> FormSchemaOut:
    """Fields for a create, edit or transition form: kind, whether required, options."""
    access = await project_access(db, principal.user, key)
    found = None
    if operation is ScreenOperation.transition:
        if not transition:
            raise ValidationFailed(
                "Send `transition` (name or ref) for operation=transition.",
                errors=[{"field": "transition", "message": "required"}],
            )
        workflows = await load_workflows(db, access.project.id)
        found = _find_transition(workflows[type].transitions, type, transition)
    schema = await screens.form_schema(db, access.project, type, operation, found)
    return FormSchemaOut(
        type=schema.ticket_type,
        operation=schema.operation,
        transition=schema.transition,
        from_screen=schema.from_screen,
        fields=[
            SchemaFieldOut(
                field=f.field,
                label=f.label,
                kind=f.kind,
                required=f.required,
                options=f.options,
                areas=f.areas,
            )
            for f in schema.fields
        ],
    )
