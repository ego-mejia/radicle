"""The signed link to an export's print view: what the worker's browser opens to print a
PDF, without an account and only for a few minutes."""

import hashlib
import hmac
import time
import uuid

from radicle.platform.config import get_settings

PRINT_SECONDS = 15 * 60


def _signature(export_id: uuid.UUID, expires: int) -> str:
    message = f"folio-print:{export_id}:{expires}".encode()
    return hmac.new(get_settings().signing_key, message, hashlib.sha256).hexdigest()[:32]


def token(export_id: uuid.UUID, now: float | None = None) -> str:
    expires = int((now or time.time()) + PRINT_SECONDS)
    return f"{export_id}.{expires}.{_signature(export_id, expires)}"


def export_of(value: str, now: float | None = None) -> uuid.UUID | None:
    """The export a token opens, or None when it is forged, broken or expired."""
    try:
        raw_id, raw_expires, sig = value.split(".")
        export_id, expires = uuid.UUID(raw_id), int(raw_expires)
    except ValueError:
        return None
    if expires < (now or time.time()):
        return None
    return export_id if hmac.compare_digest(_signature(export_id, expires), sig) else None
