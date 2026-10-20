"""default workflows: go back to the first status from review and QA

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-20

The default template only let tickets in review (or QA) move forward or one step back,
so a card in "In Review" could not be dragged to "To Do". This adds a "Back to ..."
transition to the default template and to every project still linked to it. Detached
projects own their workflows and are left alone.
"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TEMPLATE_ID = "00000000-0000-0000-0000-000000000002"
# ticket type -> (transition ref, name, from status ref, to status ref)
NEW = {
    "task": ("back_to_to_do", "Back to To Do", "in_review", "to_do"),
    "bug": ("back_to_reported", "Back to Reported", "qa_verified", "reported"),
    "draft": ("back_to_new", "Back to New", "in_review", "new"),
}


def _template(bind: sa.Connection) -> tuple[dict, int] | None:
    row = bind.execute(
        sa.text("SELECT config, version FROM templates WHERE id = CAST(:id AS uuid)"),
        {"id": DEFAULT_TEMPLATE_ID},
    ).first()
    return (row[0], row[1]) if row else None


def _save_template(bind: sa.Connection, config: dict, version: int) -> None:
    bind.execute(
        sa.text(
            "UPDATE templates SET config = CAST(:config AS jsonb), version = :version, "
            "updated_at = now() WHERE id = CAST(:id AS uuid)"
        ),
        {"config": json.dumps(config), "version": version, "id": DEFAULT_TEMPLATE_ID},
    )


def _linked_projects(bind: sa.Connection, version: int) -> list[uuid.UUID]:
    return list(
        bind.execute(
            sa.text(
                "SELECT id FROM projects WHERE template_id = CAST(:id AS uuid) "
                "AND template_mode = 'linked' AND template_version = :version"
            ),
            {"id": DEFAULT_TEMPLATE_ID, "version": version},
        ).scalars()
    )


def upgrade() -> None:
    bind = op.get_bind()
    found = _template(bind)
    if found is None:
        return
    config, version = found
    changed = False
    for ticket_type, (ref, name, from_ref, to_ref) in NEW.items():
        workflow = config.get("workflows", {}).get(ticket_type)
        if workflow is None:
            continue
        status_refs = {s["ref"] for s in workflow["statuses"]}
        exists = any(
            t["ref"] == ref or (t.get("from") == from_ref and t["to"] == to_ref)
            for t in workflow["transitions"]
        )
        if exists or not {from_ref, to_ref} <= status_refs:
            continue
        workflow["transitions"].append(
            {
                "ref": ref,
                "name": name,
                "from": from_ref,
                "to": to_ref,
                "allowed_resolutions": None,
                "rules": [],
            }
        )
        changed = True
    if not changed:
        return
    projects = _linked_projects(bind, version)
    _save_template(bind, config, version + 1)
    for project_id in projects:
        for ticket_type, (ref, name, from_ref, to_ref) in NEW.items():
            bind.execute(
                sa.text(
                    """
                    INSERT INTO transitions (id, project_id, ticket_type, name, from_status_id,
                                             to_status_id, position, template_ref)
                    SELECT CAST(:new_id AS uuid), :project, CAST(:type AS ticket_type), :name,
                           f.id, t.id,
                           (SELECT coalesce(max(position), -1) + 1 FROM transitions
                             WHERE project_id = :project AND ticket_type = CAST(:type AS ticket_type)),
                           :ref
                      FROM statuses f, statuses t
                     WHERE f.project_id = :project AND t.project_id = :project
                       AND f.ticket_type = CAST(:type AS ticket_type)
                       AND t.ticket_type = CAST(:type AS ticket_type)
                       AND f.template_ref = :from_ref AND t.template_ref = :to_ref
                       AND NOT EXISTS (
                           SELECT 1 FROM transitions x
                            WHERE x.project_id = :project
                              AND x.ticket_type = CAST(:type AS ticket_type)
                              AND (x.template_ref = :ref
                                   OR (x.from_status_id = f.id AND x.to_status_id = t.id)))
                    """
                ),
                {
                    "new_id": str(uuid.uuid4()),
                    "project": project_id,
                    "type": ticket_type,
                    "name": name,
                    "ref": ref,
                    "from_ref": from_ref,
                    "to_ref": to_ref,
                },
            )
        bind.execute(
            sa.text("UPDATE projects SET template_version = :version WHERE id = :project"),
            {"version": version + 1, "project": project_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    found = _template(bind)
    if found is None:
        return
    config, version = found
    refs = {ref for ref, *_ in NEW.values()}
    removed = False
    for workflow in config.get("workflows", {}).values():
        kept = [t for t in workflow["transitions"] if t["ref"] not in refs]
        removed = removed or len(kept) != len(workflow["transitions"])
        workflow["transitions"] = kept
    if not removed:
        return
    projects = _linked_projects(bind, version)
    _save_template(bind, config, version - 1)
    for project_id in projects:
        bind.execute(
            sa.text(
                "DELETE FROM transitions WHERE project_id = :project "
                "AND template_ref = ANY(CAST(:refs AS text[]))"
            ),
            {"project": project_id, "refs": sorted(refs)},
        )
        bind.execute(
            sa.text("UPDATE projects SET template_version = :version WHERE id = :project"),
            {"version": version - 1, "project": project_id},
        )
