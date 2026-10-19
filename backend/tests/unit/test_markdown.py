import pytest

from radicle.services.markdown import extract_mentions, parse_checklist, set_checklist_item

SAMPLE = """Integrar cobro.

- [x] Definir endpoints @luis
- [ ] Webhook de confirmación @agent-backend
* [X] Star bullet
  - [ ] Indented item @ana y @luis
-[ ] not an item
- [] not an item either

```
- [ ] inside code @ghost
```

~~~python
- [x] tilde code
~~~
- [ ] after code"""


def test_parse_checklist_items() -> None:
    items = parse_checklist(SAMPLE)
    assert [(i.index, i.text, i.checked, i.assignee) for i in items] == [
        (0, "Definir endpoints", True, "luis"),
        (1, "Webhook de confirmación", False, "agent-backend"),
        (2, "Star bullet", True, None),
        (3, "Indented item @ana y", False, "luis"),
        (4, "after code", False, None),
    ]


def test_last_handle_wins_and_mid_text_handle_kept() -> None:
    [item] = parse_checklist("- [ ] ask @ana about it")
    assert item.assignee == "ana"
    assert item.text == "ask @ana about it"


def test_email_is_not_an_assignee() -> None:
    [item] = parse_checklist("- [ ] write to ana@example.com")
    assert item.assignee is None


def test_toggle_rewrites_only_that_line() -> None:
    new_md, item = set_checklist_item(SAMPLE, 1, True)
    assert item.text == "Webhook de confirmación"
    old_lines, new_lines = SAMPLE.split("\n"), new_md.split("\n")
    changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines, strict=True)) if a != b]
    assert len(changed) == 1
    assert new_lines[changed[0]] == "- [x] Webhook de confirmación @agent-backend"


def test_toggle_preserves_indent_and_bullet() -> None:
    new_md, _ = set_checklist_item(SAMPLE, 3, True)
    assert "  - [x] Indented item @ana y @luis" in new_md
    new_md, _ = set_checklist_item(SAMPLE, 2, False)
    assert "* [ ] Star bullet" in new_md


def test_toggle_out_of_range() -> None:
    with pytest.raises(IndexError):
        set_checklist_item(SAMPLE, 5, True)
    with pytest.raises(IndexError):
        set_checklist_item(SAMPLE, -1, True)


def test_checklist_ignores_unclosed_fence() -> None:
    assert parse_checklist("```\n- [ ] hidden") == []


def test_mentions_outside_code_only() -> None:
    text = "Hey @Luis and @ana, see `@inline` and\n```\n@ghost\n```\n@ana again @agent-backend."
    assert extract_mentions(text) == ["luis", "ana", "agent-backend"]


@pytest.mark.parametrize(
    "text",
    ["mail ana@example.com", "path a/@b", "@a", "x@y", "@@double"],
)
def test_not_mentions(text: str) -> None:
    assert extract_mentions(text) == []


def test_mention_at_line_start_and_punctuation() -> None:
    assert extract_mentions("@ana: hi (@luis)") == ["ana", "luis"]
