import pytest

from radicle.docket.services.assistant import guide


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("How do I create a new project?", "Create a project"),
        ("add someone as admin of my project", "Add people to a project"),
        ("connect claude code with a token", "AI agents and MCP"),
        ("hide swimlanes rows by area", "Swimlanes"),
        ("can I limit which MCP tools an agent uses?", "Agent MCP permissions"),
        ("restricted confidential tickets", "Restricted tickets"),
    ],
)
def test_finds_the_right_section(question: str, expected: str) -> None:
    assert guide.search(question)[0].title == expected


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("¿Cómo creo un proyecto nuevo?", "Crear un proyecto"),
        ("quiero hacer admin a alguien del proyecto", "Agregar gente a un proyecto"),
        ("ocultar carriles por área", "Carriles"),
    ],
)
def test_finds_spanish_sections(question: str, expected: str) -> None:
    assert guide.search(question, "es")[0].title == expected


def test_both_guides_cover_the_same_topics() -> None:
    assert len(guide.contents("en")) == len(guide.contents("es"))


def test_terms_fold_accents_endings_and_stopwords() -> None:
    assert guide.terms("¿Cómo creo proyectos y tickets?") == ["cre", "proyect", "ticket"]
    assert guide.stem("crear") == guide.stem("creo") == "cre"


def test_nothing_matches_nothing() -> None:
    assert guide.search("zzz qqq") == []
    assert guide.search("the of and") == []
    assert "Board" in guide.contents()


def test_weak_matches_are_left_out() -> None:
    assert [s.title for s in guide.search("how can I hide swimlanes?")] == ["Swimlanes"]
