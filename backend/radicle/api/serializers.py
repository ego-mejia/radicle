"""Turn ORM objects into API response models. Shared by REST routers and MCP tools."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.api.schemas.fields import CustomFieldOut, FieldOptionOut
from radicle.api.schemas.projects import (
    AreaOut,
    CategoryCounts,
    MemberOut,
    MilestoneOut,
    ProjectDetail,
    ProjectOut,
    StatusOut,
    TransitionOut,
    WorkflowOut,
)
from radicle.db.models import (
    Area,
    CustomFieldDefinition,
    Milestone,
    Project,
    ProjectMember,
    ProjectRole,
)
from radicle.services import custom_fields, planning, projects, stats
from radicle.services.workflows import Workflow, load_workflows


def project_out(project: Project, role: ProjectRole, open_tickets: int = 0) -> ProjectOut:
    return ProjectOut(
        key=project.key,
        name=project.name,
        description_md=project.description_md,
        role=role,
        archived=project.archived_at is not None,
        open_tickets=open_tickets,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def area_out(area: Area) -> AreaOut:
    return AreaOut(
        name=area.name,
        color=area.color,
        position=area.position,
        archived=area.archived_at is not None,
    )


def milestone_out(milestone: Milestone, counts: CategoryCounts | None = None) -> MilestoneOut:
    return MilestoneOut(
        name=milestone.name,
        description_md=milestone.description_md,
        target_date=milestone.target_date,
        status=milestone.status,
        closed_at=milestone.closed_at,
        position=milestone.position,
        counts=counts or CategoryCounts(),
    )


async def milestones_out(db: AsyncSession, milestones: list[Milestone]) -> list[MilestoneOut]:
    counts = await stats.milestone_category_counts(db, [m.id for m in milestones])
    return [milestone_out(m, CategoryCounts(**counts.get(m.id, {}))) for m in milestones]


def member_out(member: ProjectMember) -> MemberOut:
    user = member.user
    return MemberOut(
        handle=user.handle,
        display_name=user.display_name,
        kind=user.kind,
        role=member.role,
        is_active=user.is_active,
    )


def workflow_out(workflow: Workflow) -> WorkflowOut:
    names = {s.id: s.name for s in workflow.statuses}
    return WorkflowOut(
        type=workflow.ticket_type,
        statuses=[
            StatusOut(name=s.name, category=s.category, is_initial=s.is_initial)
            for s in workflow.statuses
        ],
        transitions=[
            TransitionOut(
                name=t.name,
                from_status=names[t.from_status_id] if t.from_status_id else None,
                to_status=names[t.to_status_id],
                allowed_resolutions=t.allowed_resolutions,
            )
            for t in workflow.transitions
        ],
    )


def field_out(field: CustomFieldDefinition, areas: dict[uuid.UUID, str]) -> CustomFieldOut:
    return CustomFieldOut(
        key=field.key,
        name=field.name,
        field_type=field.field_type,
        options=[FieldOptionOut(**o) for o in field.options],
        applies_to_types=list(field.applies_to_types),
        applies_to_areas=(
            [areas[a] for a in field.applies_to_area_ids if a in areas]
            if field.applies_to_area_ids is not None
            else None
        ),
        position=field.position,
        archived=field.archived_at is not None,
        from_template=field.template_ref is not None,
        created_at=field.created_at,
    )


async def fields_out(db: AsyncSession, fields: list[CustomFieldDefinition]) -> list[CustomFieldOut]:
    areas = await custom_fields.area_names(db, fields)
    return [field_out(f, areas) for f in fields]


async def project_detail(db: AsyncSession, project: Project, role: ProjectRole) -> ProjectDetail:
    workflows = await load_workflows(db, project.id)
    open_counts = await stats.open_ticket_counts(db, [project.id])
    base = project_out(project, role, open_counts.get(project.id, 0))
    return ProjectDetail(
        **base.model_dump(),
        areas=[area_out(a) for a in await planning.list_areas(db, project)],
        milestones=await milestones_out(db, await planning.list_milestones(db, project)),
        workflows=[workflow_out(w) for w in workflows.values()],
        members=[member_out(m) for m in await projects.list_members(db, project)],
        custom_fields=await fields_out(db, await custom_fields.list_fields(db, project.id)),
    )
