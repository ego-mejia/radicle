"""Publishing metadata (Folio 1.3): every published page has a title, a description, a
document type, labels, an owner, audiences and a language. Validation lives here so the web
app, the API and the MCP get the same rules and the same list of missing fields."""

import re
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import catalogs, nodes
from radicle.platform import authz
from radicle.platform.db.models import User, UserKind
from radicle.platform.errors import ValidationFailed

LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
SENTENCE_END = re.compile(r"[.!?…](?:\s|$)")
FIELDS = ("title", "description", "doc_type", "labels", "owner", "audiences", "language")
# Optional links to Docket (Folio 4.4): the doc shows in those milestones and areas.
PROJECT_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
MAX_DOCKET_NAMES = 20
DECISION_STATUSES = ("accepted", "proposed", "replaced")


class MetadataIncomplete(ValidationFailed):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        fields = ", ".join(e["field"] for e in errors)
        super().__init__(
            f"Complete the metadata before publishing: {fields}. "
            "GET /api/v1/folio/metadata-schema lists the rules.",
            code="metadata_incomplete",
            errors=errors,
        )


def _sentences(text: str) -> int:
    return max(1, len(SENTENCE_END.findall(text.strip())))


async def validate_metadata(
    db: AsyncSession, node: FolioNode, metadata: dict[str, Any]
) -> dict[str, Any]:
    """The metadata, normalized, or MetadataIncomplete with every field that fails."""
    errors: list[dict[str, str]] = []

    def fail(field: str, message: str) -> None:
        errors.append({"field": field, "message": message})

    out: dict[str, Any] = {}
    title = str(metadata.get("title") or node.title).strip()
    if not 1 <= len(title) <= nodes.TITLE_MAX:
        fail("title", f"1 to {nodes.TITLE_MAX} characters")
    out["title"] = title

    description = str(metadata.get("description") or "").strip()
    if not 40 <= len(description) <= 400:
        fail("description", "40 to 400 characters")
    elif _sentences(description) > 3:
        fail("description", "1 to 3 sentences")
    out["description"] = description

    doc_type = metadata.get("doc_type")
    if doc_type not in await catalogs.active_keys(db, "doc-types"):
        fail("doc_type", "a key of doc_types")
    out["doc_type"] = doc_type

    labels = metadata.get("labels")
    if not isinstance(labels, list) or not 1 <= len(labels) <= 15:
        fail("labels", "1 to 15 labels")
        labels = []
    labels = list(dict.fromkeys(str(label).strip().lower().lstrip("#") for label in labels))
    if any(not LABEL_RE.fullmatch(label) for label in labels):
        fail("labels", "lowercase letters, digits, - and _ (up to 50)")
    out["labels"] = labels

    owner_handle = str(metadata.get("owner") or "").strip().lstrip("@").lower()
    owner = await db.scalar(select(User).where(User.handle == owner_handle))
    if (
        owner is None
        or not owner.is_active
        or owner.kind != UserKind.human
        or not (await authz.authorize(db, owner, "folio", "folio.read")).allowed
    ):
        fail("owner", "an active person who can read Folio")
    out["owner"] = owner_handle

    audiences = metadata.get("audiences")
    valid_audiences = await catalogs.active_keys(db, "audiences")
    if (
        not isinstance(audiences, list)
        or not audiences
        or any(a not in valid_audiences for a in audiences)
    ):
        fail("audiences", "one or more keys of audiences")
        audiences = []
    out["audiences"] = list(dict.fromkeys(audiences))

    language = metadata.get("language")
    if language not in await catalogs.active_keys(db, "languages"):
        fail("language", "a key of languages")
    out["language"] = language

    _docket_fields(metadata, out, fail)
    _decision_fields(metadata, out, fail)

    if errors:
        raise MetadataIncomplete(errors)
    return out


def _docket_fields(
    metadata: dict[str, Any], out: dict[str, Any], fail: Callable[[str, str], None]
) -> None:
    """docket_project, docket_milestones and docket_areas, kept only when set. Names are
    matched against Docket when they are read (`GET /links?milestone=PA:V1`), with the
    reader's access, so a milestone renamed later simply stops matching."""
    project = str(metadata.get("docket_project") or "").strip().upper()
    if project and not PROJECT_RE.fullmatch(project):
        fail("docket_project", "a Docket project key, e.g. PA")
    for field in ("docket_milestones", "docket_areas"):
        names = metadata.get(field) or []
        if not isinstance(names, list) or len(names) > MAX_DOCKET_NAMES:
            fail(field, f"a list of up to {MAX_DOCKET_NAMES} names")
            continue
        clean = list(dict.fromkeys(str(n).strip() for n in names if str(n).strip()))
        if any(len(n) > 100 for n in clean):
            fail(field, "names of up to 100 characters")
        elif clean and not project:
            fail(field, "set docket_project too")
        elif clean:
            out[field] = clean
    if project:
        out["docket_project"] = project


def _decision_fields(
    metadata: dict[str, Any], out: dict[str, Any], fail: Callable[[str, str], None]
) -> None:
    """decision_status, decision_topic and decision_replaces (ADR 0045), kept only when set.
    They describe an architecture decision; any doc type may carry them, but only decision
    logs are listed in that section."""
    status = str(metadata.get("decision_status") or "").strip()
    if status and status not in DECISION_STATUSES:
        fail("decision_status", f"one of {', '.join(DECISION_STATUSES)}")
    elif status:
        out["decision_status"] = status
    topic = str(metadata.get("decision_topic") or "").strip()
    if len(topic) > 40:
        fail("decision_topic", "up to 40 characters")
    elif topic:
        out["decision_topic"] = topic
    replaces = str(metadata.get("decision_replaces") or "").strip()
    if replaces:
        try:
            out["decision_replaces"] = str(uuid.UUID(replaces))
        except ValueError:
            fail("decision_replaces", "the id of the decision this one replaces")
