"""Example rules are listed once, however many times an app registers them."""

from gumball_factory.folio.services import automation_actions
from gumball_factory.platform.services import automation


def test_registering_twice_lists_each_example_once() -> None:
    automation_actions.register()
    automation_actions.register()
    names = [e["name"] for e in automation.examples()]
    assert len(names) == len(set(names)) == 3
    assert "Outdated pages to a channel" in names
