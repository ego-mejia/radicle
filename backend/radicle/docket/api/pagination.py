"""Opaque keyset cursors: base64 of (created_at, id)."""

import base64
import json
from datetime import datetime
from typing import Annotated

from fastapi import Query

from radicle.platform.errors import ValidationFailed

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]


def encode_cursor(created_at: datetime, id_: object) -> str:
    raw = json.dumps([created_at.isoformat(), str(id_)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, id_ = json.loads(base64.urlsafe_b64decode(padded))
        return datetime.fromisoformat(created_at), str(id_)
    except (ValueError, TypeError) as exc:
        raise ValidationFailed(
            "Invalid cursor. Use the next_cursor value from the previous page.",
            errors=[{"field": "cursor", "message": "invalid"}],
        ) from exc
