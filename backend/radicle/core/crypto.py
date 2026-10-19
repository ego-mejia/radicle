"""Secrets at rest: AES-GCM with a key derived from RADICLE_SECRET_KEY."""

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from radicle.core.config import get_settings

PREFIX = "v1:"


class SecretKeyMissing(RuntimeError):
    pass


def _key() -> bytes:
    secret = get_settings().secret_key
    if not secret:
        raise SecretKeyMissing(
            "RADICLE_SECRET_KEY is not set. Radicle encrypts secrets with it and does not "
            "start without it. Generate one with `openssl rand -hex 32` and put it in .env."
        )
    return hashlib.sha256(b"radicle-encryption:" + secret.encode()).digest()


def require_key() -> None:
    _key()


def encrypt(plain: str) -> str:
    nonce = os.urandom(12)
    sealed = AESGCM(_key()).encrypt(nonce, plain.encode(), None)
    return PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode()


def decrypt(token: str) -> str:
    if not token.startswith(PREFIX):
        raise ValueError("Not an encrypted value.")
    raw = base64.urlsafe_b64decode(token[len(PREFIX) :])
    try:
        return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode()
    except InvalidTag as exc:
        raise ValueError(
            "Cannot decrypt a stored secret: RADICLE_SECRET_KEY changed since it was saved. "
            "Enter the secret again."
        ) from exc
