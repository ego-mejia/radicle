"""The templates Folio ships with (phase 3.1). They are created in the database the first
time someone lists templates, and from then on a Folio admin edits them like any other."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Builtin:
    key: str
    name: str
    description: str
    icon: str
    doc_type: str
    markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)


BUILTINS: tuple[Builtin, ...] = (
    Builtin(
        "build-spec",
        "Build spec",
        "Una etapa de trabajo: alcance, entregables con criterios, modelo de datos, API, "
        "tests y aceptación.",
        "🧱",
        "build-spec",
        """{{fecha}} · @{{autor}}

## Objetivo y alcance

Qué queremos lograr en esta etapa y qué queda fuera.

## Entregables

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 1 |  |  |  |

## Modelo de datos

```
tabla
  columna   tipo
```

## API y MCP

| Método | Ruta | Qué hace |
| --- | --- | --- |
|  |  |  |

## UI

| Pantalla | Detalle |
| --- | --- |
|  |  |

## Tests

| Área | Casos mínimos |
| --- | --- |
|  |  |

## Criterios de aceptación

- [ ] 

## Fuera de alcance

- 
""",
        {"labels": ["spec"]},
    ),
    Builtin(
        "meeting-notes",
        "Meeting notes",
        "Minuta con asistentes, agenda, decisiones y action items.",
        "🗓️",
        "minutes",
        """{{fecha}} · {{space}}

## Asistentes

- @{{autor}}

## Agenda

1. 

## Notas

## Decisiones

- 

## Action items

- [ ] 
""",
        {"labels": ["minuta"]},
    ),
    Builtin(
        "how-to",
        "How-to",
        "Una guía paso a paso para lograr algo concreto.",
        "🧭",
        "how-to",
        """En esta guía aprendes a {{titulo}}.

[[toc]]

## Antes de empezar

:::panel{kind=info}
Lo que necesitas tener listo.
:::

## Pasos

1. 
2. 
3. 

## Cómo saber que funcionó

## Problemas comunes
""",
    ),
    Builtin(
        "decision-log",
        "Decision log",
        "Una decisión con su contexto, las opciones y por qué se eligió una.",
        "⚖️",
        "decision-log",
        """{{fecha}} · Decide: @{{autor}} · Estado: :status[Propuesta]{color=yellow}

## Contexto

## Opciones

| Opción | A favor | En contra |
| --- | --- | --- |
|  |  |  |

## Decisión

## Consecuencias
""",
    ),
    Builtin(
        "retrospective",
        "Retrospectiva",
        "Qué salió bien, qué no y qué vamos a cambiar.",
        "🔁",
        "retrospective",
        """{{fecha}} · {{space}}

::::columns{layout=three}
:::column
### Salió bien

- 
:::
:::column
### Salió mal

- 
:::
:::column
### Qué cambiamos

- 
:::
::::

## Action items

- [ ] 
""",
    ),
    Builtin(
        "product-requirements",
        "Product requirements",
        "El problema, para quién, qué debe hacer y cómo sabremos que funcionó.",
        "📐",
        "requirements",
        """{{fecha}} · Dueño: @{{autor}}

## Problema

## Para quién

## Requisitos

| # | Requisito | Prioridad |
| --- | --- | --- |
| 1 |  | Alta |

## Métricas de éxito

## Fuera de alcance

## Preguntas abiertas
""",
    ),
)


@dataclass(frozen=True)
class SpaceBuiltin:
    key: str
    name: str
    description: str
    icon: str
    structure: dict[str, Any]


SPACE_BUILTINS: tuple[SpaceBuiltin, ...] = (
    SpaceBuiltin(
        "engineering-team",
        "Equipo de ingeniería",
        "Un space para un equipo técnico: inicio, specs, decisiones, guías y minutas.",
        "🛠️",
        {
            "description": "Specs, decisiones y guías del equipo.",
            "pages": [
                {"title": "Inicio"},
                {
                    "title": "Specs",
                    "kind": "folder",
                    "children": [{"title": "Primer build spec", "template": "build-spec"}],
                },
                {
                    "title": "Decisiones",
                    "kind": "folder",
                    "children": [{"title": "Registro de decisiones", "template": "decision-log"}],
                },
                {"title": "Guías", "kind": "folder"},
                {"title": "Minutas", "kind": "folder"},
            ],
        },
    ),
)
