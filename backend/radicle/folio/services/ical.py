"""A calendar as an iCal feed (RFC 5545), for Google Calendar or Outlook (Folio 5.8).
Events keep their category; Docket milestones come as all-day events."""

from datetime import UTC, datetime, timedelta

from radicle.folio.db.calendars import FolioCalendar
from radicle.folio.services.calendars import Agenda

PRODID = "-//Radicle//Folio calendars//EN"


def escape(text: str) -> str:
    """TEXT values: backslash, semicolon, comma and newlines escaped."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold(line: str) -> str:
    """Lines of at most 75 octets, continued with CRLF and a space, never splitting a
    UTF-8 character."""
    out: list[str] = []
    current, size, limit = "", 0, 75
    for char in line:
        width = len(char.encode())
        if size + width > limit:
            out.append(current)
            current, size, limit = "", 0, 74  # the leading space takes one octet
        current += char
        size += width
    out.append(current)
    return "\r\n ".join(out)


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def render(calendar: FolioCalendar, agenda: Agenda, *, host: str, now: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(calendar.name)}",
    ]
    for event in agenda.events:
        lines += ["BEGIN:VEVENT", f"UID:{event.id}@{host}", f"DTSTAMP:{_stamp(now)}"]
        if event.all_day:
            lines += [
                f"DTSTART;VALUE=DATE:{event.start_at.astimezone(UTC):%Y%m%d}",
                f"DTEND;VALUE=DATE:{event.end_at.astimezone(UTC):%Y%m%d}",
            ]
        else:
            lines += [f"DTSTART:{_stamp(event.start_at)}", f"DTEND:{_stamp(event.end_at)}"]
        lines += [
            f"SUMMARY:{escape(event.title)}",
            f"CATEGORIES:{event.category.value.upper()}",
            f"LAST-MODIFIED:{_stamp(event.updated_at)}",
        ]
        if event.description:
            lines.append(f"DESCRIPTION:{escape(event.description)}")
        lines.append("END:VEVENT")
    for milestone in agenda.milestones:
        lines += [
            "BEGIN:VEVENT",
            f"UID:milestone-{milestone.id}@{host}",
            f"DTSTAMP:{_stamp(now)}",
            f"DTSTART;VALUE=DATE:{milestone.due:%Y%m%d}",
            f"DTEND;VALUE=DATE:{milestone.due + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{escape(f'{milestone.project} · {milestone.name}')}",
            "CATEGORIES:MILESTONE",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(f"{fold(line)}\r\n" for line in lines)
