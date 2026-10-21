import re
from pathlib import Path

import pytest

from radicle.docket.services.assistant import guide, tours


def test_clean_keeps_known_targets_and_never_submits() -> None:
    steps = tours.clean(
        [
            {"target": "projects.create", "action": "click", "text": "Open it"},
            {"target": "made.up", "action": "click", "text": "Nope"},
            {"target": "project-form.submit", "action": "click", "text": "Save"},
            {"target": "project-form.key", "action": "dance", "text": "Key"},
            {"target": "project-form.name", "action": "point", "text": "  "},
            "junk",
        ]
    )
    assert [(s.target, s.action) for s in steps] == [
        ("projects.create", "click"),
        ("project-form.submit", "point"),
        ("project-form.key", "point"),
    ]
    assert tours.clean("not a list") == []
    many = [{"target": "radi", "action": "point", "text": "hi"}] * 30
    assert len(tours.clean(many)) == 12
    assert steps[0].view()["page"] == "/"


def test_every_guide_tour_is_valid_in_both_languages() -> None:
    keys = {s.key for s in guide.sections("en")} & {s.key for s in guide.sections("es")}
    for key, rows in tours.GUIDE_TOURS.items():
        assert key in keys, f"no guide section {key}"
        for lang in ("en", "es"):
            assert len(tours.guide_tour(key, lang)) == len(rows), (key, lang)
    assert tours.guide_tour("create-project", "es")[0].text == "Los proyectos viven aquí."


def test_the_tool_lists_every_target() -> None:
    schema = tours.SHOW_ME["parameters"]["properties"]["steps"]["items"]["properties"]  # type: ignore[index]
    assert schema["target"]["enum"] == list(tours.TARGETS)
    assert "projects.create" in tours.catalog()


def test_every_target_is_marked_in_the_web_app() -> None:
    """Each catalog target needs a `data-tour` in the frontend, or tours point at nothing."""
    src = Path(__file__).resolve().parents[3] / "frontend" / "src"
    if not src.is_dir():  # pragma: no cover - the backend alone, as in the Docker image
        pytest.skip("frontend sources not available")
    code = "\n".join(p.read_text(encoding="utf-8") for p in src.rglob("*.tsx"))
    marked = set(re.findall(r'data-tour="([\w.-]+)"', code))
    # data-tour={cond ? 'ticket-form.area' : undefined}: every quoted name counts.
    for expression in re.findall(r"data-tour=\{([^}]*)\}", code):
        marked.update(re.findall(r"'([\w.-]+)'", expression))
    # <Tabs tour="settings.tab"> marks each tab as settings.tab.<id>.
    prefixes = set(re.findall(r'\btour="([\w.-]+)"', code))
    missing = [
        key for key in tours.TARGETS if key not in marked and key.rsplit(".", 1)[0] not in prefixes
    ]
    assert not missing, f"Add data-tour to these targets: {missing}"
