from radicle.services.assistant import guide, tours


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
