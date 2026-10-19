"""ALTCHA: a proof of work the browser solves and the server checks. No third parties.

Challenge: the server picks a salt (with its expiry) and a secret number, publishes
sha256(salt + number) and an HMAC of it; the browser tries numbers until the hash
matches. A solved challenge is spent: it is stored until it expires.
"""

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.config import get_settings
from radicle.db.models import UsedChallenge, utcnow

ALGORITHM = "SHA-256"
MAX_NUMBER = 50_000
TTL = timedelta(minutes=20)


def _sign(challenge: str) -> str:
    key = hashlib.sha256(b"radicle-altcha:" + get_settings().signing_key).digest()
    return hmac.new(key, challenge.encode(), hashlib.sha256).hexdigest()


def _hash(salt: str, number: int) -> str:
    return hashlib.sha256(f"{salt}{number}".encode()).hexdigest()


def create_challenge(max_number: int = MAX_NUMBER) -> dict[str, Any]:
    expires = int((utcnow() + TTL).timestamp())
    salt = f"{secrets.token_hex(12)}?expires={expires}"
    number = secrets.randbelow(max_number + 1)
    challenge = _hash(salt, number)
    return {
        "algorithm": ALGORITHM,
        "challenge": challenge,
        "maxnumber": max_number,
        "salt": salt,
        "signature": _sign(challenge),
    }


def solve(challenge: dict[str, Any]) -> str:
    """What the browser does; used by tests and the smoke script."""
    for number in range(int(challenge["maxnumber"]) + 1):
        if _hash(challenge["salt"], number) == challenge["challenge"]:
            payload = {k: challenge[k] for k in ("algorithm", "challenge", "salt", "signature")}
            return base64.b64encode(json.dumps({**payload, "number": number}).encode()).decode()
    raise ValueError("unsolvable challenge")  # pragma: no cover


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""


def check(payload: str) -> tuple[Verdict, str | None]:
    """Signature, hash and expiry; returns the challenge to mark as used."""
    try:
        data = json.loads(base64.b64decode(payload))
        salt, number = str(data["salt"]), int(data["number"])
        challenge, signature = str(data["challenge"]), str(data["signature"])
    except (ValueError, KeyError, TypeError):
        return Verdict(False, "malformed"), None
    if data.get("algorithm") != ALGORITHM:
        return Verdict(False, "algorithm"), None
    if not hmac.compare_digest(_sign(challenge), signature):
        return Verdict(False, "signature"), None
    if _hash(salt, number) != challenge:
        return Verdict(False, "hash"), None
    try:
        expires = int(salt.split("expires=", 1)[1])
    except (IndexError, ValueError):
        return Verdict(False, "expiry"), None
    if expires < utcnow().timestamp():
        return Verdict(False, "expired"), None
    return Verdict(True), challenge


async def verify(db: AsyncSession, payload: str | None) -> Verdict:
    if not payload:
        return Verdict(False, "missing")
    verdict, challenge = check(payload)
    if not verdict.ok or challenge is None:
        return verdict
    await db.execute(delete(UsedChallenge).where(UsedChallenge.expires_at < utcnow()))
    inserted = await db.execute(
        pg_insert(UsedChallenge)
        .values(challenge=challenge, expires_at=utcnow() + TTL)
        .on_conflict_do_nothing()
        .returning(UsedChallenge.challenge)
    )
    if inserted.first() is None:
        return Verdict(False, "replayed")
    return Verdict(True)
