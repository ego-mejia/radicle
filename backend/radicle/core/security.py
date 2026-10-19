"""Password hashing and opaque token helpers."""

import hashlib
import hmac
import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

TOKEN_PREFIX = "rdc_"
TOKEN_BODY_LENGTH = 40
TOKEN_DISPLAY_PREFIX_LENGTH = 8
_BASE62 = string.ascii_letters + string.digits

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def generate_api_token() -> str:
    """`rdc_` followed by 40 base62 characters."""
    return TOKEN_PREFIX + "".join(secrets.choice(_BASE62) for _ in range(TOKEN_BODY_LENGTH))


def is_api_token_format(value: str) -> bool:
    body = value[len(TOKEN_PREFIX) :]
    return (
        value.startswith(TOKEN_PREFIX)
        and len(body) == TOKEN_BODY_LENGTH
        and all(c in _BASE62 for c in body)
    )


def token_display_prefix(token: str) -> str:
    return token[:TOKEN_DISPLAY_PREFIX_LENGTH]


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(session_token: str) -> str:
    """CSRF token derived from the session, so the server needs no extra state."""
    return hmac.new(session_token.encode(), b"radicle-csrf", hashlib.sha256).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
