"""Transition rules. Pure decisions over a loaded Workflow; no database access.

1. A transition is allowed if it exists for the ticket type and starts at the current
   status, or has no `from` status (any status not in the done category).
2. Entering a done status requires a resolution from `allowed_resolutions`; when only
   one is allowed it is set automatically.
3. Entering done sets resolved_at; leaving done clears resolution and resolved_at.
4. Invalid transitions fail with the list of valid ones.
"""

from dataclasses import dataclass

from radicle.db.models import Resolution, Status, StatusCategory, Transition
from radicle.platform.errors import Conflict, ValidationFailed
from radicle.services.workflows import Workflow

ALL_RESOLUTIONS: tuple[Resolution, ...] = tuple(Resolution)


@dataclass(frozen=True)
class Option:
    transition: Transition
    to_status: Status

    @property
    def resolutions(self) -> tuple[Resolution, ...]:
        if self.to_status.category is not StatusCategory.done:
            return ()
        allowed = self.transition.allowed_resolutions
        return tuple(allowed) if allowed else ALL_RESOLUTIONS


@dataclass(frozen=True)
class Decision:
    option: Option
    resolution: Resolution | None


def available(workflow: Workflow, current: Status) -> list[Option]:
    options = []
    for t in workflow.transitions:
        starts_here = t.from_status_id == current.id
        from_anywhere = t.from_status_id is None and current.category is not StatusCategory.done
        if (starts_here or from_anywhere) and t.to_status_id != current.id:
            options.append(Option(t, workflow.status_by_id(t.to_status_id)))
    return options


def describe(options: list[Option]) -> str:
    if not options:
        return "none"
    parts = []
    for o in options:
        text = f"'{o.to_status.name}' via '{o.transition.name}'"
        if o.resolutions and o.resolutions != ALL_RESOLUTIONS:
            text += f" (resolutions: {', '.join(r.value for r in o.resolutions)})"
        parts.append(text)
    return "; ".join(parts)


def decide(
    workflow: Workflow,
    current: Status,
    to_status: str,
    resolution: Resolution | None = None,
    transition: str | None = None,
    options: list[Option] | None = None,
) -> Decision:
    """Pick the transition for a move. `options` narrows the candidates (e.g. to those
    whose conditions pass); by default every transition from the current status."""
    options = available(workflow, current) if options is None else options
    target = workflow.status_named(to_status)
    matches = [o for o in options if target is not None and o.to_status.id == target.id]
    if transition is not None:
        matches = [o for o in matches if o.transition.name.lower() == transition.strip().lower()]
    if not matches:
        what = f"'{target.name}'" if target else f"unknown status '{to_status}'"
        via = f" via '{transition}'" if transition else ""
        raise Conflict(
            f"Transition to {what}{via} not allowed from '{current.name}'. "
            f"Valid targets: {describe(options)}.",
            code="invalid_transition",
            extra={"valid_transitions": [_option_json(o) for o in options]},
        )
    done = matches[0].to_status.category is StatusCategory.done
    if not done:
        if resolution is not None:
            raise ValidationFailed(
                f"'{matches[0].to_status.name}' is not a done status, so it takes no resolution.",
                errors=[{"field": "resolution", "message": "not allowed"}],
            )
        return Decision(_prefer_specific(matches), None)

    if resolution is None:
        single = [o for o in matches if len(o.resolutions) == 1]
        if len(matches) == 1 and single:
            return Decision(matches[0], matches[0].resolutions[0])
        allowed = sorted({r.value for o in matches for r in o.resolutions})
        raise ValidationFailed(
            f"Moving to '{matches[0].to_status.name}' needs a resolution: {', '.join(allowed)}.",
            code="resolution_required",
            errors=[{"field": "resolution", "message": "required"}],
            extra={"allowed_resolutions": allowed},
        )
    fitting = [o for o in matches if resolution in o.resolutions]
    if not fitting:
        allowed = sorted({r.value for o in matches for r in o.resolutions})
        raise ValidationFailed(
            f"Resolution '{resolution.value}' is not allowed when moving from "
            f"'{current.name}' to '{matches[0].to_status.name}'. Allowed: {', '.join(allowed)}.",
            code="resolution_not_allowed",
            errors=[{"field": "resolution", "message": "not allowed"}],
            extra={"allowed_resolutions": allowed},
        )
    return Decision(_prefer_specific(fitting), resolution)


def _prefer_specific(options: list[Option]) -> Option:
    """A transition that starts at this status wins over a 'from anywhere' one."""
    return next((o for o in options if o.transition.from_status_id is not None), options[0])


def _option_json(option: Option) -> dict[str, object]:
    return {
        "name": option.transition.name,
        "to_status": option.to_status.name,
        "category": option.to_status.category.value,
        "allowed_resolutions": [r.value for r in option.resolutions] or None,
    }
