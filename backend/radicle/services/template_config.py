"""The configuration a template carries, its validation, and the default one.

Statuses, transitions and custom fields are matched by `ref`, a stable slug: renaming
a status changes its name but not its ref, so propagation knows it is the same one.
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from radicle.db.models import (
    BlockedPolicy,
    CustomFieldType,
    Resolution,
    StatusCategory,
    TicketType,
)
from radicle.platform.errors import ValidationFailed
from radicle.services.rule_catalog import check_rule
from radicle.services.screens import check_fields
from radicle.services.workflows import DEFAULT_WORKFLOWS

REF_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,59}$")
NAME_MAX = 60
STATUSES_MAX = 30
TRANSITIONS_MAX = 100


class _Conf(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)


class StatusConf(_Conf):
    ref: str
    name: str
    category: StatusCategory
    is_initial: bool = False


class RuleConf(_Conf):
    kind: str
    rule_type: str
    config: dict[str, Any] = Field(default_factory=dict)


class TransitionConf(_Conf):
    ref: str
    name: str
    from_: str | None = Field(default=None, alias="from")
    to: str
    allowed_resolutions: list[Resolution] | None = None
    rules: list[RuleConf] = Field(default_factory=list)


class WorkflowConf(_Conf):
    statuses: list[StatusConf]
    transitions: list[TransitionConf] = Field(default_factory=list)


class FieldOptionConf(_Conf):
    value: str
    label: str | None = None
    color: str | None = None


class FieldConf(_Conf):
    ref: str
    key: str
    name: str
    field_type: CustomFieldType
    options: list[FieldOptionConf] = Field(default_factory=list)
    applies_to_types: list[TicketType] | None = None
    applies_to_areas: list[str] | None = None


class AreaConf(_Conf):
    name: str
    color: str | None = None


class ScreenFieldConf(_Conf):
    field: str
    required: bool = False


class ScreenConf(_Conf):
    type: TicketType
    operation: str
    transition: str | None = None  # transition ref, only for operation = transition
    fields: list[ScreenFieldConf] = Field(default_factory=list)


class SettingsConf(_Conf):
    blocked_policy: BlockedPolicy = BlockedPolicy.warn


class TemplateConfig(_Conf):
    areas: list[AreaConf] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    custom_fields: list[FieldConf] = Field(default_factory=list)
    workflows: dict[TicketType, WorkflowConf]
    screens: list[ScreenConf] = Field(default_factory=list)
    settings: SettingsConf = Field(default_factory=SettingsConf)

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return value[:60] or "x"


def _fail(path: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": path, "message": "invalid"}])


def parse_workflow(raw: Any, ticket_type: TicketType, path: str = "workflow") -> WorkflowConf:
    try:
        workflow = WorkflowConf.model_validate(raw)
    except ValidationError as exc:
        raise _from_pydantic(exc, path) from None
    check_workflow(workflow, ticket_type, path)
    return workflow


def parse(raw: Any) -> TemplateConfig:
    """Parse and check a template config. Errors name the path, e.g. workflows.bug."""
    try:
        config = TemplateConfig.model_validate(raw)
    except ValidationError as exc:
        raise _from_pydantic(exc, "config") from None
    missing = [t.value for t in TicketType if t not in config.workflows]
    if missing:
        raise _fail("config.workflows", f"Workflows are missing for: {', '.join(missing)}.")
    for ticket_type, workflow in config.workflows.items():
        check_workflow(workflow, ticket_type, f"config.workflows.{ticket_type.value}")
    _unique([f.ref for f in config.custom_fields], "config.custom_fields", "field ref")
    _unique([f.key for f in config.custom_fields], "config.custom_fields", "field key")
    _unique([a.name.lower() for a in config.areas], "config.areas", "area")
    for f in config.custom_fields:
        _check_ref(f.ref, "config.custom_fields")
    check_screens(config.screens, config.workflows, "config.screens")
    return config


def check_screens(
    screens: list["ScreenConf"], workflows: dict[TicketType, WorkflowConf], path: str
) -> None:
    seen: set[tuple[str, str, str | None]] = set()
    for screen in screens:
        if screen.operation not in ("create", "edit", "transition"):
            raise _fail(path, "Screen operation must be create, edit or transition.")
        if (screen.operation == "transition") != (screen.transition is not None):
            raise _fail(path, "Only transition screens name a transition, and they must.")
        if screen.transition is not None:
            refs = {t.ref for t in workflows[screen.type].transitions}
            if screen.transition not in refs:
                raise _fail(
                    path,
                    f"Screen for {screen.type.value} uses unknown transition "
                    f"'{screen.transition}'.",
                )
        key = (screen.type.value, screen.operation, screen.transition)
        if key in seen:
            raise _fail(path, f"Two screens for {screen.type.value} {screen.operation}.")
        seen.add(key)
        checked = check_fields([f.model_dump() for f in screen.fields], path)
        screen.fields = [ScreenFieldConf(**f) for f in checked]


def check_workflow(workflow: WorkflowConf, ticket_type: TicketType, path: str) -> None:
    label = ticket_type.value
    if not workflow.statuses:
        raise _fail(path, f"The {label} workflow needs at least one status.")
    if len(workflow.statuses) > STATUSES_MAX:
        raise _fail(path, f"A workflow can have at most {STATUSES_MAX} statuses.")
    if len(workflow.transitions) > TRANSITIONS_MAX:
        raise _fail(path, f"A workflow can have at most {TRANSITIONS_MAX} transitions.")
    for s in workflow.statuses:
        _check_ref(s.ref, path)
        if not 1 <= len(s.name) <= NAME_MAX:
            raise _fail(path, f"Status names must be 1 to {NAME_MAX} characters.")
    for t in workflow.transitions:
        _check_ref(t.ref, path)
        if not 1 <= len(t.name) <= NAME_MAX:
            raise _fail(path, f"Transition names must be 1 to {NAME_MAX} characters.")
    _unique([s.ref for s in workflow.statuses], path, "status ref")
    _unique([s.name.lower() for s in workflow.statuses], path, "status name")
    _unique([t.ref for t in workflow.transitions], path, "transition ref")
    initial = [s for s in workflow.statuses if s.is_initial]
    if len(initial) != 1:
        raise _fail(
            path,
            f"The {label} workflow needs exactly one initial status (it has {len(initial)}).",
        )
    if not any(s.category is StatusCategory.done for s in workflow.statuses):
        raise _fail(path, f"The {label} workflow needs at least one status in the done category.")
    refs = {s.ref for s in workflow.statuses}
    for t in workflow.transitions:
        for end in (t.from_, t.to):
            if end is not None and end not in refs:
                raise _fail(
                    path,
                    f"Transition '{t.name}' in {label} points to unknown status '{end}'. "
                    f"Statuses: {', '.join(sorted(refs))}.",
                )
        if t.from_ == t.to:
            raise _fail(path, f"Transition '{t.name}' in {label} starts and ends at '{t.to}'.")
        for rule in t.rules:
            rule.config = check_rule(rule.kind, rule.rule_type, rule.config, f"{path}.{t.ref}")


def unreachable(workflow: WorkflowConf) -> list[str]:
    """Names of statuses that no path from the initial status reaches (a warning)."""
    by_ref = {s.ref: s for s in workflow.statuses}
    start = next(s.ref for s in workflow.statuses if s.is_initial)
    seen = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for t in workflow.transitions:
            from_ok = t.from_ == current or (
                t.from_ is None and by_ref[current].category is not StatusCategory.done
            )
            if from_ok and t.to not in seen:
                seen.add(t.to)
                frontier.append(t.to)
    return [s.name for s in workflow.statuses if s.ref not in seen]


def _check_ref(ref: str, path: str) -> None:
    if not REF_RE.fullmatch(ref):
        raise _fail(
            path,
            f"Invalid ref '{ref}'. Refs are 1 to 60 lowercase letters, digits or '_'.",
        )


def _unique(values: list[str], path: str, what: str) -> None:
    seen: set[str] = set()
    for v in values:
        if v in seen:
            raise _fail(path, f"Repeated {what} '{v}'.")
        seen.add(v)


def _from_pydantic(exc: ValidationError, prefix: str) -> ValidationFailed:
    errors = [
        {
            "field": ".".join([prefix, *(str(p) for p in e["loc"])]),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    summary = "; ".join(f"{e['field']}: {e['message']}" for e in errors[:3])
    return ValidationFailed(f"Invalid template configuration. {summary}", errors=errors)


def workflow_refs(names: list[tuple[str, str | None]]) -> list[str]:
    """Refs for transitions given (name, from ref): the slug, plus the origin when two
    transitions share a name (e.g. two Reopen)."""
    refs: list[str] = []
    for name, from_ref in names:
        ref = slug(name)
        if ref in refs:
            ref = f"{ref}_{from_ref or 'any'}"
        while ref in refs:
            ref += "_2"
        refs.append(ref)
    return refs


def default_config() -> TemplateConfig:
    """The stage 1 workflows as a template ("Radicle default")."""
    workflows: dict[TicketType, WorkflowConf] = {}
    for ticket_type, spec in DEFAULT_WORKFLOWS.items():
        status_refs = {name: slug(name) for name, _ in spec.statuses}
        statuses = [
            StatusConf(ref=status_refs[name], name=name, category=category, is_initial=i == 0)
            for i, (name, category) in enumerate(spec.statuses)
        ]
        refs = workflow_refs(
            [
                (t.name, status_refs[t.from_status] if t.from_status else None)
                for t in spec.transitions
            ]
        )
        transitions = [
            TransitionConf(
                ref=ref,
                name=t.name,
                from_=status_refs[t.from_status] if t.from_status else None,
                to=status_refs[t.to_status],
                allowed_resolutions=list(t.allowed_resolutions) if t.allowed_resolutions else None,
            )
            for ref, t in zip(refs, spec.transitions, strict=True)
        ]
        workflows[ticket_type] = WorkflowConf(statuses=statuses, transitions=transitions)
    return TemplateConfig(workflows=workflows)
