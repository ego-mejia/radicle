from radicle.services.assistant import tours


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


def test_the_tool_lists_every_target() -> None:
    schema = tours.SHOW_ME["parameters"]["properties"]["steps"]["items"]["properties"]  # type: ignore[index]
    assert schema["target"]["enum"] == list(tours.TARGETS)
    assert "projects.create" in tours.catalog()
