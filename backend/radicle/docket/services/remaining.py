"""Original estimate and remaining time, shared by ticket edits and worklogs."""

from decimal import Decimal

from radicle.docket.db.models import RemainingMode, Ticket

CENT = Decimal("0.01")


def spent_hours(ticket: Ticket) -> Decimal:
    return (Decimal(ticket.time_spent_minutes) / 60).quantize(CENT)


def recompute_remaining(ticket: Ticket) -> None:
    if ticket.remaining_mode is not RemainingMode.auto:
        return
    if ticket.estimate_hours is None:
        ticket.remaining_hours = None
        return
    ticket.remaining_hours = max(ticket.estimate_hours - spent_hours(ticket), Decimal(0)).quantize(
        CENT
    )


def estimate_changed(ticket: Ticket) -> None:
    """Call after estimate_hours changes: fixes the original once, refreshes remaining."""
    if ticket.original_estimate_hours is None and ticket.estimate_hours is not None:
        ticket.original_estimate_hours = ticket.estimate_hours
    recompute_remaining(ticket)


__all__ = ["estimate_changed", "recompute_remaining", "spent_hours"]
