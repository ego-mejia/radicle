"""Field rules shared by every service."""

import re

from radicle.platform.errors import ValidationFailed

HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
PASSWORD_MIN = 8
PASSWORD_MAX = 256
DISPLAY_NAME_MAX = 100
TOKEN_NAME_MAX = 100


def normalize_handle(handle: str) -> str:
    value = handle.strip().lstrip("@").lower()
    if not HANDLE_RE.fullmatch(value):
        raise ValidationFailed(
            f"Invalid handle '{handle}'. Use 2 to 32 characters: lowercase letters, digits, "
            "'-' or '_', starting with a letter or digit.",
            errors=[{"field": "handle", "message": "invalid format"}],
        )
    return value


def normalize_display_name(name: str) -> str:
    value = " ".join(name.split())
    if not value or len(value) > DISPLAY_NAME_MAX:
        raise ValidationFailed(
            f"Display name must be 1 to {DISPLAY_NAME_MAX} characters.",
            errors=[{"field": "display_name", "message": "invalid length"}],
        )
    return value


def check_password(password: str) -> str:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise ValidationFailed(
            f"Password must be {PASSWORD_MIN} to {PASSWORD_MAX} characters.",
            errors=[{"field": "password", "message": "invalid length"}],
        )
    return password


def normalize_token_name(name: str) -> str:
    value = name.strip()
    if not value or len(value) > TOKEN_NAME_MAX:
        raise ValidationFailed(
            f"Token name must be 1 to {TOKEN_NAME_MAX} characters.",
            errors=[{"field": "name", "message": "invalid length"}],
        )
    return value
