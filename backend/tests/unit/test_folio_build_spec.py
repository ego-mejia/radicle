"""Finding a build spec's deliverables (Folio 4.3): a deliverables table or numbered
level-3 headings."""

from radicle.folio.services.build_spec import detect
from radicle.folio.services.parse_markdown import from_markdown

TABLE = """# Fase 4

## Entregables

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 4.1 | Tickets **dentro** de los docs | Smart links | Veo su estado; PA-4 muestra el doc |
| 4.2 | Crear ticket desde texto | Selección |  |
|  |  |  |  |

## Tests

| Área | Casos |
| --- | --- |
| Chat | Cita |
"""

HEADINGS = """# Spec

## Entregables

### 1. Modelo de datos

Las tablas nuevas.

- [ ] Migración con downgrade
- [x] Índices

### Notas sueltas

No es un entregable.

### 2) API

Rutas REST.

## Fuera de alcance

- Nada de esto cuenta
"""


def test_a_deliverables_table() -> None:
    items = detect(from_markdown(TABLE))
    assert [(i.key, i.title) for i in items] == [
        ("4.1", "Tickets dentro de los docs"),
        ("4.2", "Crear ticket desde texto"),
    ]
    first = items[0]
    assert first.description == "Smart links" and first.anchor == "entregables"
    assert first.criteria == ["Veo su estado", "PA-4 muestra el doc"]
    assert items[1].criteria == []


def test_numbered_level_3_headings() -> None:
    items = detect(from_markdown(HEADINGS))
    assert [(i.key, i.title, i.anchor) for i in items] == [
        ("1", "Modelo de datos", "1-modelo-de-datos"),
        ("2", "API", "2-api"),
    ]
    assert items[0].description == "Las tablas nuevas."
    assert items[0].criteria == ["Migración con downgrade", "Índices"]
    assert items[1].criteria == []


def test_without_deliverables() -> None:
    assert detect(from_markdown("# Hola\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n")) == []


def test_repeated_keys_count_once() -> None:
    md = "### 1. Uno\n\n### 1. Otra vez\n"
    assert [i.title for i in detect(from_markdown(md))] == ["Uno"]
