"""SSO against a real Keycloak (testcontainers): login, accounts by domain, linking by
verified email, group sync, deactivated users and password sign-in switched off."""

import html
import re
import time
from collections.abc import Iterator
from urllib.parse import urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from tests.conftest import ADMIN_PASSWORD, Team

API = "/api/v1"
IMAGE = "quay.io/keycloak/keycloak:26.0.7"
REALM = "acme"
SECRET = "kc-client-secret"
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def keycloak() -> Iterator[str]:
    container = (
        DockerContainer(IMAGE)
        .with_command("start-dev")
        .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
        .with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
        .with_exposed_ports(8080)
        .waiting_for(LogMessageWaitStrategy("Listening on").with_startup_timeout(180))
    )
    with container:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        # The master realm wants HTTPS from outside the container: allow HTTP for the test.
        kcadm = "/opt/keycloak/bin/kcadm.sh"
        for _ in range(60):
            code, _out = container.exec(
                f"{kcadm} config credentials --server http://localhost:8080 --realm master "
                "--user admin --password admin"
            )
            if code == 0:
                break
            time.sleep(1)
        code, out = container.exec(f"{kcadm} update realms/master -s sslRequired=NONE")
        assert code == 0, out
        _setup_realm(base)
        yield f"{base}/realms/{REALM}"


def _setup_realm(base: str) -> None:
    with httpx.Client(base_url=base, timeout=30) as c:
        token = None
        for _ in range(60):  # the admin account appears a moment after the server listens
            r = c.post(
                "/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": "admin",
                    "password": "admin",
                },
            )
            if r.status_code == 200:
                token = r.json()["access_token"]
                break
            time.sleep(1)
        assert token, r.text
        h = {"Authorization": f"Bearer {token}"}
        assert c.post(
            "/admin/realms",
            headers=h,
            json={"realm": REALM, "enabled": True, "sslRequired": "none"},
        ).is_success
        for name in ("radicle-backend", "otros"):
            c.post(f"/admin/realms/{REALM}/groups", headers=h, json={"name": name})
        r = c.post(
            f"/admin/realms/{REALM}/clients",
            headers=h,
            json={
                "clientId": "radicle",
                "secret": SECRET,
                "publicClient": False,
                "redirectUris": ["*"],
                "standardFlowEnabled": True,
                "protocolMappers": [
                    {
                        "name": "groups",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-group-membership-mapper",
                        "config": {
                            "claim.name": "groups",
                            "full.path": "false",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "userinfo.token.claim": "true",
                        },
                    }
                ],
            },
        )
        assert r.is_success, r.text
        users = [
            ("ana", "ana@acme.com", ["/radicle-backend"]),
            ("fer", "admin@example.com", []),
            ("eve", "eve@other.com", []),
            ("leo", "leo@acme.com", ["/otros"]),
        ]
        for username, email, groups in users:
            r = c.post(
                f"/admin/realms/{REALM}/users",
                headers=h,
                json={
                    "username": username,
                    "email": email,
                    "emailVerified": True,
                    "enabled": True,
                    "firstName": username.title(),
                    "lastName": "Test",
                    "groups": groups,
                    "credentials": [
                        {"type": "password", "value": "pw-" + username, "temporary": False}
                    ],
                },
            )
            assert r.is_success, r.text


async def sso_login(client: AsyncClient, provider_id: str, username: str) -> AsyncClient:
    """The browser dance: our login -> Keycloak form -> our callback. Returns a client with
    whatever cookies the callback set (its own jar, the admin's session stays)."""
    browser = AsyncClient(transport=client._transport, base_url="http://test")
    r = await browser.get(f"{API}/auth/sso/{provider_id}/login?next=/p/PA/board")
    assert r.status_code == 302, r.text
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as kc:
        page = await kc.get(r.headers["location"])
        action = html.unescape(re.search(r'id="kc-form-login"[^>]*action="([^"]+)"', page.text)[1])
        # Keycloak marks its cookies Secure (SameSite=None); over plain HTTP the client
        # would not send them back, so pass them by hand.
        jar = "; ".join(f"{c.name}={c.value}" for c in kc.cookies.jar)
        back = await kc.post(
            action,
            data={"username": username, "password": "pw-" + username},
            headers={"Cookie": jar},
            follow_redirects=False,
        )
    assert back.status_code == 302, re.findall(
        r"(?:kc-feedback-text|input-error|alert)[^>]*>([^<]{3,200})", back.text
    )
    callback = urlparse(back.headers["location"])
    done = await browser.get(f"{callback.path}?{callback.query}")
    assert done.status_code == 302
    browser.last_redirect = done.headers["location"]  # type: ignore[attr-defined]
    return browser


@pytest.fixture
async def provider(client: AsyncClient, board: Team, keycloak: str) -> dict:
    r = await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "backend"})
    assert r.status_code == 201
    await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "otros-rad"})
    await client.put(
        f"{API}/projects/PA/group-roles/backend",
        headers=board.admin.headers,
        json={"role": "member"},
    )
    r = await client.post(
        f"{API}/admin/sso-providers",
        headers=board.instance.headers,
        json={
            "name": "Acme Keycloak",
            "issuer_url": keycloak,
            "client_id": "radicle",
            "client_secret": SECRET,
            "allowed_domains": ["acme.com"],
            "group_claim": "groups",
            "group_mapping": {"radicle-backend": "backend", "otros": "otros-rad"},
        },
    )
    assert r.status_code == 201, r.text
    assert SECRET not in r.text and r.json()["has_secret"] is True
    return r.json()


async def test_acceptance_login_creates_the_user_in_the_mapped_group(
    client: AsyncClient, board: Team, provider: dict
) -> None:
    options = (await client.get(f"{API}/auth/options")).json()
    assert [p["name"] for p in options["providers"]] == ["Acme Keycloak"]
    test = await client.post(
        f"{API}/admin/sso-providers/{provider['id']}/test", headers=board.instance.headers
    )
    assert test.json()["ok"] is True, test.text

    browser = await sso_login(client, provider["id"], "ana")
    assert browser.last_redirect == "/p/PA/board"  # type: ignore[attr-defined]
    me = (await browser.get(f"{API}/me")).json()
    # "ana" is taken in the test team, so the handle gets a number.
    assert (me["handle"], me["email"], me["auth_source"]) == ("ana2", "ana@acme.com", "oidc")
    assert [p["key"] for p in me["projects"]] == ["PA"]  # via the mapped group
    group = (await client.get(f"{API}/groups/backend", headers=board.instance.headers)).json()
    assert [m["handle"] for m in group["members"]] == ["ana2"]
    # Same person again: same account.
    again = await sso_login(client, provider["id"], "ana")
    assert (await again.get(f"{API}/me")).json()["handle"] == "ana2"


async def test_domains_linking_groups_and_deactivated(
    client: AsyncClient, board: Team, provider: dict
) -> None:
    browser = await sso_login(client, provider["id"], "eve")
    assert browser.last_redirect.startswith("/login?sso_error=")  # type: ignore[attr-defined]
    assert "other.com" in browser.last_redirect  # type: ignore[attr-defined]

    # admin@example.com already exists locally and Keycloak verified the email: linked.
    fer = await sso_login(client, provider["id"], "fer")
    me = (await fer.get(f"{API}/me")).json()
    assert me["handle"] == "fernando" and me["is_instance_admin"] is True

    # Sync touches only mapped groups: leo is in "otros"; a manual group stays.
    await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "manual"})
    await sso_login(client, provider["id"], "leo")
    await client.put(f"{API}/groups/manual/members/leo", headers=board.instance.headers)
    await client.put(f"{API}/groups/backend/members/leo", headers=board.instance.headers)
    await sso_login(client, provider["id"], "leo")
    groups = {}
    for name in ("manual", "backend", "otros-rad"):
        detail = (await client.get(f"{API}/groups/{name}", headers=board.instance.headers)).json()
        groups[name] = [m["handle"] for m in detail["members"]]
    assert groups == {"manual": ["leo"], "backend": [], "otros-rad": ["leo"]}

    await client.patch(
        f"{API}/users/leo", headers=board.instance.headers, json={"is_active": False}
    )
    blocked = await sso_login(client, provider["id"], "leo")
    assert "deactivated" in blocked.last_redirect  # type: ignore[attr-defined]


async def test_password_login_off_keeps_the_first_admin(
    client: AsyncClient, board: Team, provider: dict
) -> None:
    r = await client.patch(
        f"{API}/admin/settings",
        headers=board.instance.headers,
        json={"password_login_enabled": False},
    )
    assert r.json() == {"password_login_enabled": False, "emergency_admin": "admin@example.com"}
    other = AsyncClient(transport=client._transport, base_url="http://test")
    r = await other.post(
        f"{API}/auth/login", json={"email": "luis@example.com", "password": "temporary-pass"}
    )
    assert r.status_code in (401, 403)
    r = await other.post(
        f"{API}/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200, r.text
    assert (await client.get(f"{API}/auth/options")).json()["password_login_enabled"] is False


async def test_bad_state_and_admin_only(client: AsyncClient, board: Team, provider: dict) -> None:
    other = AsyncClient(transport=ASGITransport(app=client._transport.app), base_url="http://test")  # type: ignore[attr-defined]
    r = await other.get(f"{API}/auth/sso/{provider['id']}/callback?code=x&state=y")
    assert r.status_code == 302 and "sso_error" in r.headers["location"]
    r = await client.get(f"{API}/admin/sso-providers", headers=board.member.headers)
    assert r.status_code == 403
