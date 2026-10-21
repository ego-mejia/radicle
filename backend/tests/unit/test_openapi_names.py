"""Every API model has a name of its own. When two share one, FastAPI renames both to
`radicle__<module>__<Name>` and the frontend's generated types change under it."""

import pytest

from radicle.main import create_app


def test_no_two_api_models_share_a_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RADICLE_SECRET_KEY", "test-only-not-secret-0123456789abcdef")
    from radicle.platform.config import get_settings

    get_settings.cache_clear()
    try:
        schemas = create_app().openapi()["components"]["schemas"]
    finally:
        get_settings.cache_clear()
    clashes = sorted(name for name in schemas if name.startswith("radicle__"))
    assert not clashes, f"Give these API models unique names: {clashes}"
