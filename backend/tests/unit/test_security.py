import pytest

from radicle.core import security


def test_api_token_format() -> None:
    token = security.generate_api_token()
    assert token.startswith("rdc_")
    assert len(token) == 44
    assert security.is_api_token_format(token)


@pytest.mark.parametrize(
    "value",
    ["", "rdc_", "rdc_short", "xyz_" + "a" * 40, "rdc_" + "a" * 39 + "!", "rdc_" + "a" * 41],
)
def test_rejects_malformed_tokens(value: str) -> None:
    assert not security.is_api_token_format(value)


def test_tokens_are_unique() -> None:
    assert len({security.generate_api_token() for _ in range(200)}) == 200


def test_hash_is_stable_sha256() -> None:
    token = security.generate_api_token()
    assert security.hash_token(token) == security.hash_token(token)
    assert len(security.hash_token(token)) == 64
    assert security.hash_token(token) != token


def test_display_prefix_is_first_eight_chars() -> None:
    token = security.generate_api_token()
    assert security.token_display_prefix(token) == token[:8]


def test_password_hash_roundtrip() -> None:
    hashed = security.hash_password("correct horse")
    assert hashed.startswith("$argon2id$")
    assert security.verify_password(hashed, "correct horse")
    assert not security.verify_password(hashed, "wrong horse")
    assert not security.verify_password("not-a-hash", "correct horse")


def test_csrf_token_is_bound_to_session() -> None:
    a, b = security.generate_session_token(), security.generate_session_token()
    assert security.csrf_token_for(a) == security.csrf_token_for(a)
    assert security.csrf_token_for(a) != security.csrf_token_for(b)
    assert security.tokens_match("x", "x") and not security.tokens_match("x", "y")
