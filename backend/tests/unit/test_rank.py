import random

import pytest

from radicle.docket.services import rank


def test_first_key() -> None:
    assert rank.between(None, None) == "a0"


def test_append_1000_without_collision_and_short() -> None:
    keys = [rank.after(None)]
    for _ in range(1000):
        keys.append(rank.after(keys[-1]))
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    assert max(len(k) for k in keys) <= 4


def test_prepend_1000() -> None:
    keys = [rank.after(None)]
    for _ in range(1000):
        keys.insert(0, rank.before(keys[0]))
    assert keys == sorted(keys) and len(set(keys)) == len(keys)


def test_between_two_values_repeatedly() -> None:
    a, b = rank.after(None), rank.after(rank.after(None))
    for _ in range(1000):
        middle = rank.between(a, b)
        assert a < middle < b
        b = middle


def test_random_inserts_keep_order() -> None:
    rng = random.Random(42)
    keys = [rank.after(None)]
    for _ in range(1000):
        i = rng.randrange(-1, len(keys))
        lo = keys[i] if i >= 0 else None
        hi = keys[i + 1] if i + 1 < len(keys) else None
        keys.insert(i + 1, rank.between(lo, hi))
    assert keys == sorted(keys) and len(set(keys)) == len(keys)


@pytest.mark.parametrize(("a", "b"), [("a1", "a0"), ("a0", "a0")])
def test_rejects_unordered(a: str, b: str) -> None:
    with pytest.raises(ValueError, match="must sort before"):
        rank.between(a, b)


@pytest.mark.parametrize("bad", ["", "!", "a", "a00", "a0!", "A" + "0" * 26])
def test_rejects_invalid_keys(bad: str) -> None:
    with pytest.raises((ValueError, IndexError)):
        rank.after(bad)
