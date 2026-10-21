"""Single sign-on with OpenID Connect: authorization code with PKCE (Authlib), discovery by
issuer, id_token checked against the provider's keys, automatic accounts by domain, linking
by verified email and group sync from a claim."""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.config import get_settings
from radicle.platform.db.models import (
    Group,
    GroupMember,
    InstanceSetting,
    SsoProvider,
    User,
    UserKind,
    utcnow,
)
from radicle.platform.errors import Forbidden, NotFound, Unauthorized, ValidationFailed
from radicle.platform.services.validation import HANDLE_RE

STATE_SECONDS = 600
DISCOVERY_SECONDS = 600
_discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}
# Tests swap this for a transport that reaches a local provider.
http_transport: httpx.AsyncBaseTransport | None = None


def _client(**kwargs: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10, transport=http_transport, **kwargs)


# --- providers -------------------------------------------------------------------------------


def _fail(name: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": name, "message": "invalid"}])


async def list_providers(db: AsyncSession, *, enabled_only: bool = False) -> list[SsoProvider]:
    query = select(SsoProvider).order_by(SsoProvider.name)
    if enabled_only:
        query = query.where(SsoProvider.enabled.is_(True))
    return list(await db.scalars(query))


async def get_provider(db: AsyncSession, provider_id: uuid.UUID) -> SsoProvider:
    provider = await db.get(SsoProvider, provider_id)
    if provider is None:
        raise NotFound(f"SSO provider {provider_id} not found.", code="sso_provider_not_found")
    return provider


def _domains(values: list[str]) -> list[str]:
    out = []
    for v in values:
        d = v.strip().lower().lstrip("@")
        if d and not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", d):
            raise _fail("allowed_domains", f"'{v}' is not a domain like example.com.")
        if d:
            out.append(d)
    return out


async def _mapping(db: AsyncSession, mapping: dict[str, str]) -> dict[str, str]:
    """Claim value -> group id, given group names or ids."""
    out: dict[str, str] = {}
    for claim, group in mapping.items():
        try:
            found = await db.get(Group, uuid.UUID(str(group)))
        except ValueError:
            found = await db.scalar(select(Group).where(Group.name == str(group)))
        if found is None:
            raise _fail("group_mapping", f"Group '{group}' does not exist.")
        out[claim] = str(found.id)
    return out


async def save_provider(
    db: AsyncSession, changes: dict[str, Any], provider: SsoProvider | None = None
) -> SsoProvider:
    if provider is None:
        missing = [
            k for k in ("name", "issuer_url", "client_id", "client_secret") if not changes.get(k)
        ]
        if missing:
            raise _fail(missing[0], f"A provider needs {', '.join(missing)}.")
        provider = SsoProvider(
            scopes=["openid", "email", "profile"],
            allowed_domains=[],
            group_mapping={},
            auto_create_users=True,
            enabled=True,
        )
        db.add(provider)
    if changes.get("name") is not None:
        provider.name = str(changes["name"]).strip()
    if changes.get("issuer_url") is not None:
        issuer = str(changes["issuer_url"]).strip().rstrip("/")
        if not issuer.startswith(("https://", "http://")):
            raise _fail("issuer_url", "The issuer is a URL like https://accounts.google.com.")
        provider.issuer_url = issuer
    if changes.get("client_id") is not None:
        provider.client_id = str(changes["client_id"]).strip()
    if changes.get("client_secret"):
        provider.client_secret_encrypted = crypto.encrypt(str(changes["client_secret"]))
    if changes.get("scopes") is not None:
        scopes = [s for s in changes["scopes"] if s]
        provider.scopes = scopes if "openid" in scopes else ["openid", *scopes]
    if changes.get("allowed_domains") is not None:
        provider.allowed_domains = _domains(changes["allowed_domains"])
    for flag in ("auto_create_users", "enabled"):
        if changes.get(flag) is not None:
            setattr(provider, flag, bool(changes[flag]))
    if "group_claim" in changes:
        provider.group_claim = (changes["group_claim"] or "").strip() or None
    if changes.get("group_mapping") is not None:
        provider.group_mapping = await _mapping(db, changes["group_mapping"])
    provider.updated_at = utcnow()
    await db.flush()
    return provider


def provider_view(p: SsoProvider) -> dict[str, Any]:
    """For admins and the audit log: never the secret."""
    return {
        "name": p.name,
        "issuer_url": p.issuer_url,
        "client_id": p.client_id,
        "scopes": list(p.scopes),
        "allowed_domains": list(p.allowed_domains),
        "auto_create_users": p.auto_create_users,
        "group_claim": p.group_claim,
        "group_mapping": dict(p.group_mapping or {}),
        "enabled": p.enabled,
    }


async def discovery(issuer: str) -> dict[str, Any]:
    cached = _discovery_cache.get(issuer)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with _client() as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise _fail("issuer_url", f"Discovery at {url} answered {r.status_code}.")
    data: dict[str, Any] = r.json()
    if data.get("issuer", "").rstrip("/") != issuer.rstrip("/"):
        raise _fail("issuer_url", f"The provider says its issuer is {data.get('issuer')}.")
    _discovery_cache[issuer] = (time.monotonic() + DISCOVERY_SECONDS, data)
    return data


@dataclass(frozen=True)
class TestResult:
    ok: bool
    checks: list[tuple[str, bool, str]]


async def test_provider(provider: SsoProvider) -> TestResult:
    """Discovery, keys, and the client credentials when the provider allows that grant."""
    checks: list[tuple[str, bool, str]] = []
    try:
        meta = await discovery(provider.issuer_url)
        checks.append(("discovery", True, meta["authorization_endpoint"]))
    except (ValidationFailed, httpx.HTTPError, KeyError) as exc:
        checks.append(("discovery", False, str(getattr(exc, "detail", exc))))
        return TestResult(False, checks)
    async with _client() as client:
        jwks = await client.get(meta["jwks_uri"])
        checks.append(("keys", jwks.status_code == 200, f"{len(jwks.json().get('keys', []))} keys"))
        if "client_credentials" in meta.get("grant_types_supported", []):
            r = await client.post(
                meta["token_endpoint"],
                data={"grant_type": "client_credentials"},
                auth=(provider.client_id, crypto.decrypt(provider.client_secret_encrypted)),
            )
            ok = r.status_code == 200 or r.json().get("error") == "unauthorized_client"
            checks.append(("credentials", ok, "accepted" if ok else r.text[:200]))
    return TestResult(all(c[1] for c in checks), checks)


# --- login flow ------------------------------------------------------------------------------


def _sign(data: bytes) -> str:
    key = hashlib.sha256(b"radicle-sso:" + get_settings().signing_key).digest()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def pack_state(payload: dict[str, Any]) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{raw}.{_sign(raw.encode())}"


def unpack_state(value: str | None) -> dict[str, Any]:
    try:
        raw, sig = (value or "").rsplit(".", 1)
    except ValueError:
        raise Unauthorized(
            "The sign-in took too long or came from elsewhere. Start again."
        ) from None
    if not hmac.compare_digest(_sign(raw.encode()), sig):
        raise Unauthorized("The sign-in took too long or came from elsewhere. Start again.")
    data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(raw))
    if data.get("exp", 0) < time.time():
        raise Unauthorized("The sign-in took too long. Start again.")
    return data


def redirect_uri(provider: SsoProvider) -> str:
    return f"{get_settings().base_url.rstrip('/')}/api/v1/auth/sso/{provider.id}/callback"


def _safe_next(value: str | None) -> str:
    return value if value and value.startswith("/") and not value.startswith("//") else "/"


async def start_login(provider: SsoProvider, next_url: str | None) -> tuple[str, str]:
    """The provider's authorization URL and the signed cookie that remembers the attempt."""
    if not provider.enabled:
        raise NotFound("This sign-in option is off.", code="sso_provider_disabled")
    meta = await discovery(provider.issuer_url)
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)  # PKCE wants 43 to 128 characters
    client = AsyncOAuth2Client(
        client_id=provider.client_id,
        scope=" ".join(provider.scopes),
        redirect_uri=redirect_uri(provider),
        code_challenge_method="S256",
    )
    url, _ = client.create_authorization_url(
        meta["authorization_endpoint"], state=state, nonce=nonce, code_verifier=verifier
    )
    cookie = pack_state(
        {
            "provider": str(provider.id),
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "next": _safe_next(next_url),
            "exp": time.time() + STATE_SECONDS,
        }
    )
    return url, cookie


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    groups: list[str]


async def finish_login(
    provider: SsoProvider, saved: dict[str, Any], *, code: str, state: str
) -> Identity:
    if saved.get("provider") != str(provider.id) or not hmac.compare_digest(
        str(saved.get("state", "")), state
    ):
        raise Unauthorized("The sign-in answer does not match this attempt. Start again.")
    meta = await discovery(provider.issuer_url)
    client = AsyncOAuth2Client(
        client_id=provider.client_id,
        client_secret=crypto.decrypt(provider.client_secret_encrypted),
        redirect_uri=redirect_uri(provider),
        token_endpoint_auth_method="client_secret_post",  # noqa: S106 - a method name
        transport=http_transport,
        timeout=10,
    )
    try:
        token = await client.fetch_token(
            meta["token_endpoint"], code=code, code_verifier=saved["verifier"]
        )
    except Exception as exc:  # authlib raises several kinds
        raise Unauthorized(f"The provider did not accept the sign-in: {exc}") from None
    finally:
        await client.aclose()
    claims = await _verify_id_token(provider, meta, token.get("id_token"), saved["nonce"])
    groups = claims.get(provider.group_claim, []) if provider.group_claim else []
    if isinstance(groups, str):
        groups = [groups]
    return Identity(
        subject=str(claims["sub"]),
        email=(claims.get("email") or None),
        email_verified=bool(claims.get("email_verified")),
        name=claims.get("name") or claims.get("preferred_username"),
        groups=[str(g).lstrip("/") for g in groups],
    )


async def _verify_id_token(
    provider: SsoProvider, meta: dict[str, Any], id_token: str | None, nonce: str
) -> dict[str, Any]:
    if not id_token:
        raise Unauthorized("The provider did not send an id_token.")
    async with _client() as http:
        keys = KeySet.import_key_set((await http.get(meta["jwks_uri"])).json())
    try:
        claims: dict[str, Any] = jwt.decode(id_token, keys).claims
    except (JoseError, ValueError) as exc:
        raise Unauthorized(f"The id_token signature is not valid: {exc}") from None
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    problems = []
    if str(claims.get("iss", "")).rstrip("/") != provider.issuer_url.rstrip("/"):
        problems.append("issuer")
    if provider.client_id not in audiences:
        problems.append("audience")
    if float(claims.get("exp", 0)) < time.time():
        problems.append("expired")
    if claims.get("nonce") != nonce:
        problems.append("nonce")
    if problems:
        raise Unauthorized(f"The id_token is not valid ({', '.join(problems)}).")
    return claims


async def _free_handle(db: AsyncSession, email: str) -> str:
    base = re.sub(r"[^a-z0-9_-]", "-", email.split("@")[0].lower()).strip("-_") or "user"
    base = base[:28]
    if not HANDLE_RE.fullmatch(base):
        base = f"u-{base}"[:28]
    handle, n = base, 1
    while await db.scalar(select(User.id).where(User.handle == handle)):
        n += 1
        handle = f"{base}{n}"
    return handle


@dataclass(frozen=True)
class Outcome:
    user: User
    created: bool
    linked: bool
    groups_added: list[str]
    groups_removed: list[str]


async def resolve_user(db: AsyncSession, provider: SsoProvider, who: Identity) -> Outcome:
    """Existing SSO identity, else a local account with the same verified email, else a new
    account when its domain is allowed. Deactivated users never get in."""
    created = linked = False
    user = await db.scalar(
        select(User).where(User.sso_provider_id == provider.id, User.sso_subject == who.subject)
    )
    if user is None and who.email:
        existing = await db.scalar(select(User).where(User.email == who.email))
        if existing is not None:
            if not who.email_verified:
                raise Forbidden(
                    f"An account with {who.email} exists, but {provider.name} did not confirm "
                    "the email. Ask an admin to link it."
                )
            user, linked = existing, True
            user.sso_provider_id, user.sso_subject = provider.id, who.subject
    if user is None:
        email = (who.email or "").lower()
        domain = email.split("@")[-1] if "@" in email else ""
        if not provider.auto_create_users:
            raise Forbidden(f"There is no Radicle account for {email or 'you'}. Ask an admin.")
        if provider.allowed_domains and domain not in provider.allowed_domains:
            raise Forbidden(
                f"Accounts from {domain or 'your email'} cannot sign in here. Allowed: "
                f"{', '.join(provider.allowed_domains)}."
            )
        if not email:
            raise Forbidden(f"{provider.name} did not share an email; Radicle needs one.")
        user = User(
            handle=await _free_handle(db, email),
            display_name=(who.name or email.split("@")[0])[:120],
            email=email,
            kind=UserKind.human,
            password_hash=None,
            is_instance_admin=False,
            is_active=True,
            auth_source="oidc",
            sso_provider_id=provider.id,
            sso_subject=who.subject,
        )
        db.add(user)
        await db.flush()
        created = True
    if not user.is_active:
        raise Forbidden("This account is deactivated.")
    added, removed = await _sync_groups(db, provider, user, who.groups)
    await db.flush()
    return Outcome(user, created, linked, added, removed)


async def _sync_groups(
    db: AsyncSession, provider: SsoProvider, user: User, claimed: list[str]
) -> tuple[list[str], list[str]]:
    """Only mapped groups change: claimed ones are added, the rest of the mapped removed."""
    if not provider.group_claim or not provider.group_mapping:
        return [], []
    want = {uuid.UUID(gid) for claim, gid in provider.group_mapping.items() if claim in claimed}
    mapped = {uuid.UUID(gid) for gid in provider.group_mapping.values()}
    have = set(
        await db.scalars(
            select(GroupMember.group_id).where(
                GroupMember.user_id == user.id, GroupMember.group_id.in_(mapped)
            )
        )
    )
    for gid in want - have:
        db.add(GroupMember(group_id=gid, user_id=user.id))
    if have - want:
        await db.execute(
            delete(GroupMember).where(
                GroupMember.user_id == user.id, GroupMember.group_id.in_(have - want)
            )
        )
    names = dict((await db.execute(select(Group.id, Group.name).where(Group.id.in_(mapped)))).all())
    return sorted(names[g] for g in want - have), sorted(names[g] for g in have - want)


# --- instance settings -----------------------------------------------------------------------


async def get_setting(db: AsyncSession, key: str, default: Any) -> Any:
    row = await db.get(InstanceSetting, key)
    return default if row is None else row.value


async def set_setting(db: AsyncSession, key: str, value: Any) -> None:
    row = await db.get(InstanceSetting, key)
    if row is None:
        db.add(InstanceSetting(key=key, value=value))
    else:
        row.value = value
    await db.flush()


async def initial_admin_id(db: AsyncSession) -> uuid.UUID | None:
    """The first instance admin keeps password sign-in as the way back in."""
    found: uuid.UUID | None = await db.scalar(
        select(User.id)
        .where(User.is_instance_admin.is_(True), User.kind == UserKind.human)
        .order_by(User.created_at, User.id)
        .limit(1)
    )
    return found


async def check_password_login(db: AsyncSession, user: User) -> None:
    if await get_setting(db, "password_login_enabled", True):
        return
    if user.id == await initial_admin_id(db):
        return
    raise Forbidden(
        "Password sign-in is off on this instance. Use your company sign-in button.",
        code="password_login_disabled",
    )
