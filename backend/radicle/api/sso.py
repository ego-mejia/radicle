from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import Field
from sqlalchemy import select

from radicle.api.deps import AppSettings, Db, InstanceAdmin, set_session_cookies
from radicle.api.schemas.common import Input, Output, Page
from radicle.core.errors import ProblemError, Unauthorized
from radicle.db.models import Group, SsoProvider, User
from radicle.services import auth, sso

router = APIRouter(tags=["sso"])
STATE_COOKIE = "radicle_sso"


class ProviderButton(Output):
    id: str
    name: str
    login_url: str


class AuthOptions(Output):
    password_login_enabled: bool
    providers: list[ProviderButton]


class ProviderOut(Output):
    id: str
    name: str
    issuer_url: str
    client_id: str
    has_secret: bool = Field(description="Stored encrypted; never returned")
    scopes: list[str]
    allowed_domains: list[str]
    auto_create_users: bool
    group_claim: str | None
    group_mapping: dict[str, str] = Field(description="Claim value -> group name")
    enabled: bool
    redirect_uri: str = Field(description="Register this callback URL with the provider")


class ProviderIn(Input):
    name: str | None = None
    issuer_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = Field(default=None, description="Write only")
    scopes: list[str] | None = None
    allowed_domains: list[str] | None = None
    auto_create_users: bool | None = None
    group_claim: str | None = None
    group_mapping: dict[str, str] | None = Field(
        default=None, description="Claim value -> group name or id"
    )
    enabled: bool | None = None


class TestCheck(Output):
    name: str
    ok: bool
    detail: str


class TestOut(Output):
    ok: bool
    checks: list[TestCheck]


class InstanceSettingsOut(Output):
    password_login_enabled: bool
    emergency_admin: str | None = Field(
        description="The first instance admin always keeps password sign-in"
    )


class InstanceSettingsIn(Input):
    password_login_enabled: bool | None = None


async def _out(db: Db, p: SsoProvider) -> ProviderOut:
    view = sso.provider_view(p)
    names = dict((await db.execute(select(Group.id, Group.name))).all())
    view["group_mapping"] = {
        claim: names.get(UUID(gid), gid) for claim, gid in view["group_mapping"].items()
    }
    return ProviderOut(
        id=str(p.id),
        has_secret=bool(p.client_secret_encrypted),
        redirect_uri=sso.redirect_uri(p),
        **view,
    )


@router.get("/auth/options", response_model=AuthOptions)
async def auth_options(db: Db) -> AuthOptions:
    """What the login page shows: password form and one button per active provider."""
    providers = await sso.list_providers(db, enabled_only=True)
    return AuthOptions(
        password_login_enabled=bool(await sso.get_setting(db, "password_login_enabled", True)),
        providers=[
            ProviderButton(id=str(p.id), name=p.name, login_url=f"/api/v1/auth/sso/{p.id}/login")
            for p in providers
        ],
    )


@router.get("/auth/sso/{provider_id}/login", include_in_schema=False)
async def sso_login(
    provider_id: UUID, db: Db, settings: AppSettings, next: str | None = None
) -> Response:
    provider = await sso.get_provider(db, provider_id)
    url, cookie = await sso.start_login(provider, next)
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(
        STATE_COOKIE,
        cookie,
        max_age=sso.STATE_SECONDS,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/api/v1/auth/sso",
    )
    return response


@router.get("/auth/sso/{provider_id}/callback", include_in_schema=False)
async def sso_callback(
    provider_id: UUID,
    request: Request,
    db: Db,
    settings: AppSettings,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    """Back from the provider: sign in (creating or linking the account) and go home."""
    try:
        if error or not code or not state:
            raise Unauthorized(f"The provider did not sign you in ({error or 'no code'}).")
        provider = await sso.get_provider(db, provider_id)
        saved = sso.unpack_state(request.cookies.get(STATE_COOKIE))
        who = await sso.finish_login(provider, saved, code=code, state=state)
        outcome = await sso.resolve_user(db, provider, who)
    except ProblemError as exc:
        await db.rollback()
        response = RedirectResponse(f"/login?sso_error={quote(exc.detail)}", status_code=302)
        response.delete_cookie(STATE_COOKIE, path="/api/v1/auth/sso")
        return response
    ip = request.client.host if request.client else None
    issued = await auth.create_session(
        db,
        outcome.user,
        days=settings.session_days,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    response = RedirectResponse(saved.get("next") or "/", status_code=302)
    set_session_cookies(response, issued.token, settings)
    response.delete_cookie(STATE_COOKIE, path="/api/v1/auth/sso")
    return response


@router.get("/admin/sso-providers", response_model=Page[ProviderOut])
async def list_providers(_: InstanceAdmin, db: Db) -> Page[ProviderOut]:
    return Page(items=[await _out(db, p) for p in await sso.list_providers(db)])


@router.post("/admin/sso-providers", response_model=ProviderOut, status_code=201)
async def create_provider(body: ProviderIn, _: InstanceAdmin, db: Db) -> ProviderOut:
    """An OpenID Connect provider; register `redirect_uri` with it."""
    return await _out(db, await sso.save_provider(db, body.model_dump(exclude_unset=True)))


@router.patch("/admin/sso-providers/{provider_id}", response_model=ProviderOut)
async def patch_provider(
    provider_id: UUID, body: ProviderIn, _: InstanceAdmin, db: Db
) -> ProviderOut:
    provider = await sso.get_provider(db, provider_id)
    saved = await sso.save_provider(db, body.model_dump(exclude_unset=True), provider)
    return await _out(db, saved)


@router.delete("/admin/sso-providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: UUID, _: InstanceAdmin, db: Db) -> Response:
    """Its users keep their accounts; they sign in another way."""
    await db.delete(await sso.get_provider(db, provider_id))
    return Response(status_code=204)


@router.post("/admin/sso-providers/{provider_id}/test", response_model=TestOut)
async def test_provider(provider_id: UUID, _: InstanceAdmin, db: Db) -> TestOut:
    """Discovery, signing keys and, when allowed, the client credentials."""
    result = await sso.test_provider(await sso.get_provider(db, provider_id))
    return TestOut(
        ok=result.ok, checks=[TestCheck(name=n, ok=o, detail=d) for n, o, d in result.checks]
    )


async def _settings(db: Db) -> InstanceSettingsOut:
    admin_id = await sso.initial_admin_id(db)
    admin = await db.get(User, admin_id) if admin_id else None
    return InstanceSettingsOut(
        password_login_enabled=bool(await sso.get_setting(db, "password_login_enabled", True)),
        emergency_admin=admin.email if admin else None,
    )


@router.get("/admin/settings", response_model=InstanceSettingsOut)
async def get_instance_settings(_: InstanceAdmin, db: Db) -> InstanceSettingsOut:
    return await _settings(db)


@router.patch("/admin/settings", response_model=InstanceSettingsOut)
async def patch_instance_settings(
    body: InstanceSettingsIn, _: InstanceAdmin, db: Db
) -> InstanceSettingsOut:
    """Turning password sign-in off leaves the first instance admin able to use it."""
    if body.password_login_enabled is not None:
        await sso.set_setting(db, "password_login_enabled", body.password_login_enabled)
    return await _settings(db)
