"""Templates (Folio 3.1): start a page or a whole space with the right structure.

Page templates hold a document whose text may use variables, replaced when the page is
created: {{date}} / {{fecha}}, {{author}} / {{autor}}, {{space}}, {{title}} / {{titulo}}.
Their default metadata (and document type) preloads the draft, so publishing asks only
for what's missing. Space templates create a tree of folders and pages (each page from a
template or blank) and the space's grants in one go.

Global templates are a Folio admin's; space templates belong to that space's admins.
"""

import copy
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft, FolioNode, FolioSpace, GranteeType, NodeKind
from radicle.folio.db.templates import FolioTemplate, TemplateKind, TemplateScope
from radicle.folio.services import access, nodes, schema, sharing, spaces
from radicle.folio.services.parse_markdown import from_markdown
from radicle.folio.services.quality import today
from radicle.folio.services.template_library import BUILTINS, SPACE_BUILTINS
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound, ValidationFailed

VARIABLE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
ALIASES = {"fecha": "date", "autor": "author", "titulo": "title", "título": "title"}
MAX_STRUCTURE_NODES = 200


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def ensure_builtins(db: AsyncSession) -> None:
    """Create the included templates the first time; never overwrite an admin's edits."""
    have = set(
        await db.scalars(
            select(FolioTemplate.builtin_key).where(FolioTemplate.builtin_key.is_not(None))
        )
    )
    for b in BUILTINS:
        if b.key in have:
            continue
        db.add(
            FolioTemplate(
                kind=TemplateKind.page,
                scope=TemplateScope.global_,
                builtin_key=b.key,
                name=b.name,
                description=b.description,
                icon=b.icon,
                doc_type_key=b.doc_type,
                content_json=from_markdown(b.markdown),
                default_metadata=b.metadata,
            )
        )
    for sb in SPACE_BUILTINS:
        if sb.key in have:
            continue
        db.add(
            FolioTemplate(
                kind=TemplateKind.space,
                scope=TemplateScope.global_,
                builtin_key=sb.key,
                name=sb.name,
                description=sb.description,
                icon=sb.icon,
                structure=sb.structure,
            )
        )
    await db.flush()


async def _is_folio_admin(db: AsyncSession, user: User) -> bool:
    return (await authz.authorize(db, user, "folio", "folio.admin")).allowed


async def list_templates(
    db: AsyncSession,
    user: User,
    *,
    kind: TemplateKind | None = None,
    space: FolioSpace | None = None,
) -> list[FolioTemplate]:
    """Global templates and those of the spaces you can see (or of `space` only), not
    archived, the included ones first."""
    await ensure_builtins(db)
    visible = await access.visible_space_ids(db, user)
    in_spaces = [space.id] if space is not None else list(visible)
    query = select(FolioTemplate).where(
        FolioTemplate.archived_at.is_(None),
        or_(
            FolioTemplate.scope == TemplateScope.global_,
            FolioTemplate.space_id.in_(in_spaces),
        ),
    )
    if kind is not None:
        query = query.where(FolioTemplate.kind == kind)
    rows = await db.scalars(query.order_by(FolioTemplate.builtin_key.is_(None), FolioTemplate.name))
    return list(rows)


async def get_template(db: AsyncSession, user: User, template_id: uuid.UUID) -> FolioTemplate:
    found = await db.get(FolioTemplate, template_id)
    if found is not None and found.scope == TemplateScope.space:
        if found.space_id not in await access.visible_space_ids(db, user):
            found = None
    if found is None or found.archived_at is not None:
        raise NotFound(f"Template {template_id} not found.", code="template_not_found")
    return found


async def _require_manage(db: AsyncSession, user: User, template: FolioTemplate) -> None:
    if template.scope == TemplateScope.global_:
        (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()
        return
    space = await db.get(FolioSpace, template.space_id)
    if space is None:  # pragma: no cover - a space template keeps its space
        raise NotFound("The template's space is gone.", code="space_not_found")
    await access.require_admin(db, user, space)


@dataclass
class TemplateData:
    kind: TemplateKind
    name: str
    description: str = ""
    icon: str | None = None
    doc_type_key: str | None = None
    content_json: dict[str, Any] | None = None
    content_md: str | None = None
    default_metadata: dict[str, Any] | None = None
    structure: dict[str, Any] | None = None


def _content(data: TemplateData) -> dict[str, Any] | None:
    if data.content_json is not None and data.content_md is not None:
        raise _invalid("content_md", "Send content_json or content_md, not both.")
    if data.content_md is not None:
        return from_markdown(data.content_md)
    if data.content_json is not None:
        return schema.validate(data.content_json)
    return None


def _check(data: TemplateData) -> None:
    if not data.name.strip():
        raise _invalid("name", "Give the template a name.")
    if data.kind == TemplateKind.page and data.structure is not None:
        raise _invalid("structure", "Page templates have content; structure is for spaces.")
    if data.kind == TemplateKind.space:
        _check_structure(data.structure or {"pages": []})


def _check_structure(structure: dict[str, Any]) -> int:
    count = 0

    def walk(items: Any, depth: int) -> None:
        nonlocal count
        if not isinstance(items, list):
            raise _invalid("structure", "structure.pages is a list of {title, kind, children}.")
        if depth > 10:
            raise _invalid("structure", "A space template nests at most 10 levels.")
        for item in items:
            count += 1
            if count > MAX_STRUCTURE_NODES:
                raise _invalid(
                    "structure", f"A space template has at most {MAX_STRUCTURE_NODES} pages."
                )
            if not isinstance(item, dict) or not str(item.get("title", "")).strip():
                raise _invalid("structure", "Each item needs a title.")
            if item.get("kind", "page") not in ("page", "folder"):
                raise _invalid("structure", "Items are pages or folders.")
            walk(item.get("children", []), depth + 1)

    walk(structure.get("pages", []), 0)
    return count


async def create_template(
    db: AsyncSession, user: User, data: TemplateData, *, space: FolioSpace | None = None
) -> FolioTemplate:
    _check(data)
    template = FolioTemplate(
        kind=data.kind,
        scope=TemplateScope.space if space else TemplateScope.global_,
        space_id=space.id if space else None,
        name=data.name.strip(),
        description=data.description.strip(),
        icon=data.icon,
        doc_type_key=data.doc_type_key,
        content_json=_content(data) if data.kind == TemplateKind.page else None,
        default_metadata=data.default_metadata or {},
        structure=data.structure if data.kind == TemplateKind.space else None,
        created_by=user.id,
    )
    await _require_manage(db, user, template)
    db.add(template)
    await db.flush()
    return template


async def update_template(
    db: AsyncSession, user: User, template: FolioTemplate, data: TemplateData
) -> FolioTemplate:
    await _require_manage(db, user, template)
    data.kind = template.kind
    _check(data)
    template.name, template.description = data.name.strip(), data.description.strip()
    template.icon, template.doc_type_key = data.icon, data.doc_type_key
    content = _content(data)
    if template.kind == TemplateKind.page and content is not None:
        template.content_json = content
    if data.default_metadata is not None:
        template.default_metadata = data.default_metadata
    if template.kind == TemplateKind.space and data.structure is not None:
        template.structure = data.structure
    template.updated_at = utcnow()
    await db.flush()
    return template


async def archive_template(db: AsyncSession, user: User, template: FolioTemplate) -> None:
    await _require_manage(db, user, template)
    template.archived_at = utcnow()
    await db.flush()


def fill(doc: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    """The document with its {{variables}} replaced in every text node; unknown ones stay."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1).lower()
        return values.get(ALIASES.get(name, name), match.group(0))

    out = copy.deepcopy(doc)

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") == "text" and isinstance(node.get("text"), str):
            node["text"] = VARIABLE.sub(replace, node["text"])
        for child in node.get("content", []) or []:
            walk(child)

    walk(out)
    return out


async def create_page(
    db: AsyncSession,
    user: User,
    template: FolioTemplate,
    space: FolioSpace,
    *,
    title: str,
    parent_id: uuid.UUID | None = None,
    kind: NodeKind = NodeKind.page,
) -> FolioNode:
    """A page (or post) with the template's document and metadata in its draft."""
    if template.kind != TemplateKind.page:
        raise _invalid("template", "That is a space template: use it to create a space.")
    node = await nodes.create_node(db, user, space, kind=kind, title=title, parent_id=parent_id)
    values = {
        "date": today().isoformat(),
        "author": user.handle,
        "space": space.name,
        "title": node.title,
    }
    metadata = dict(template.default_metadata)
    if template.doc_type_key:
        metadata.setdefault("doc_type", template.doc_type_key)
    metadata.setdefault("owner", f"@{user.handle}")
    db.add(
        FolioDraft(
            node_id=node.id,
            content_json=fill(template.content_json or schema.empty(), values),
            metadata_=metadata,
        )
    )
    nodes.record(db, node, user, "created_from_template", template=str(template.id))
    await db.flush()
    return node


async def create_space(
    db: AsyncSession, user: User, template: FolioTemplate, *, key: str, name: str
) -> FolioSpace:
    """A space with the template's tree of folders and pages, and its grants."""
    if template.kind != TemplateKind.space:
        raise _invalid("template", "That is a page template: use it to create a page.")
    structure = template.structure or {}
    space = await spaces.create_space(
        db, user, key=key, name=name, description=str(structure.get("description", ""))
    )
    by_ref = {str(t.id): t for t in await list_templates(db, user, kind=TemplateKind.page)}
    by_ref |= {t.builtin_key: t for t in by_ref.values() if t.builtin_key}

    async def build(items: list[dict[str, Any]], parent: uuid.UUID | None) -> None:
        for item in items:
            title = str(item["title"])
            ref = item.get("template")
            if item.get("kind") == "folder":
                node = await nodes.create_node(
                    db, user, space, kind=NodeKind.folder, title=title, parent_id=parent
                )
            elif ref and str(ref) in by_ref:
                node = await create_page(
                    db, user, by_ref[str(ref)], space, title=title, parent_id=parent
                )
            else:
                node = await nodes.create_node(
                    db, user, space, kind=NodeKind.page, title=title, parent_id=parent
                )
            await build(item.get("children", []), node.id)

    await build(structure.get("pages", []), None)
    grants = structure.get("grants")
    if grants:
        rows = [
            sharing.GrantRow(
                sharing.Grantee(GranteeType(g["grantee_type"]), g.get("grantee")),
                list(g["permissions"]),
            )
            for g in grants
        ]
        current = await sharing.space_grants(db, space)
        await sharing.set_space_grants(db, user, space, current + rows)
    return space
