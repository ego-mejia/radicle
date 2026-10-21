import uuid

import pytest

from radicle.docket.db.models import Resolution, Status, TicketType, Transition
from radicle.docket.services.workflow_engine import available, decide
from radicle.docket.services.workflows import DEFAULT_WORKFLOWS, Workflow
from radicle.platform.errors import Conflict, ValidationFailed

R = Resolution


def build(ticket_type: TicketType) -> Workflow:
    spec = DEFAULT_WORKFLOWS[ticket_type]
    wf = Workflow(ticket_type)
    for i, (name, category) in enumerate(spec.statuses):
        wf.statuses.append(
            Status(
                id=uuid.uuid4(),
                name=name,
                category=category,
                position=i,
                is_initial=i == 0,
                ticket_type=ticket_type,
            )
        )
    ids = {s.name: s.id for s in wf.statuses}
    for i, t in enumerate(spec.transitions):
        wf.transitions.append(
            Transition(
                id=uuid.uuid4(),
                name=t.name,
                ticket_type=ticket_type,
                position=i,
                from_status_id=ids[t.from_status] if t.from_status else None,
                to_status_id=ids[t.to_status],
                allowed_resolutions=list(t.allowed_resolutions) if t.allowed_resolutions else None,
            )
        )
    return wf


TASK, BUG, DRAFT = build(TicketType.task), build(TicketType.bug), build(TicketType.draft)


def st(wf: Workflow, name: str) -> Status:
    status = wf.status_named(name)
    assert status is not None
    return status


def test_available_from_todo() -> None:
    names = [(o.transition.name, o.to_status.name) for o in available(TASK, st(TASK, "To Do"))]
    assert names == [("Start", "In Progress"), ("Close", "Done")]


def test_close_not_offered_from_done() -> None:
    names = [o.transition.name for o in available(TASK, st(TASK, "Done"))]
    assert names == ["Reopen"]


def test_valid_transition() -> None:
    d = decide(TASK, st(TASK, "To Do"), "in progress")
    assert d.option.transition.name == "Start" and d.resolution is None


def test_invalid_transition_lists_valid_ones() -> None:
    with pytest.raises(Conflict) as exc:
        decide(TASK, st(TASK, "To Do"), "In Review")
    assert "Transition to 'In Review' not allowed from 'To Do'" in exc.value.detail
    assert "'In Progress' via 'Start'" in exc.value.detail
    assert "'Done' via 'Close' (resolutions: wont_do, duplicate)" in exc.value.detail
    assert [v["to_status"] for v in exc.value.extra["valid_transitions"]] == ["In Progress", "Done"]


def test_unknown_status() -> None:
    with pytest.raises(Conflict, match="unknown status 'Shipped'"):
        decide(TASK, st(TASK, "To Do"), "Shipped")


def test_done_requires_resolution() -> None:
    with pytest.raises(ValidationFailed, match="needs a resolution") as exc:
        decide(TASK, st(TASK, "In Review"), "Done")
    assert exc.value.extra["allowed_resolutions"] == [
        "cannot_reproduce",
        "done",
        "duplicate",
        "wont_do",
    ]


def test_close_from_todo_only_allows_wont_do_and_duplicate() -> None:
    d = decide(TASK, st(TASK, "To Do"), "Done", R.wont_do)
    assert d.option.transition.name == "Close" and d.resolution is R.wont_do
    with pytest.raises(ValidationFailed, match="'done' is not allowed"):
        decide(TASK, st(TASK, "To Do"), "Done", R.done)


def test_from_in_review_specific_transition_wins() -> None:
    assert decide(TASK, st(TASK, "In Review"), "Done", R.done).option.transition.name == "Complete"
    # wont_do fits both Complete (all) and Close; the specific one wins.
    assert (
        decide(TASK, st(TASK, "In Review"), "Done", R.wont_do).option.transition.name == "Complete"
    )
    d = decide(TASK, st(TASK, "In Review"), "Done", R.wont_do, transition="close")
    assert d.option.transition.name == "Close"


def test_bug_close_allows_cannot_reproduce() -> None:
    d = decide(BUG, st(BUG, "Reported"), "Done", R.cannot_reproduce)
    assert d.option.transition.name == "Close"
    with pytest.raises(ValidationFailed):
        decide(TASK, st(TASK, "To Do"), "Done", R.cannot_reproduce)


def test_single_allowed_resolution_is_automatic() -> None:
    d = decide(DRAFT, st(DRAFT, "In Review"), "Approved")
    assert d.resolution is R.done and d.option.transition.name == "Approve"


def test_resolution_on_non_done_target_rejected() -> None:
    with pytest.raises(ValidationFailed, match="takes no resolution"):
        decide(TASK, st(TASK, "To Do"), "In Progress", R.done)


def test_draft_reopen_from_both_done_statuses() -> None:
    for name in ("Approved", "Discarded"):
        assert decide(DRAFT, st(DRAFT, name), "New").option.transition.name == "Reopen"


def test_named_transition_must_match() -> None:
    with pytest.raises(Conflict, match="via 'Teleport'"):
        decide(TASK, st(TASK, "To Do"), "In Progress", transition="Teleport")
