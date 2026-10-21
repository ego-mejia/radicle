# Folio: documentos en Markdown

Los documentos de Folio se guardan como JSON de TipTap (`backend/radicle/folio/services/schema.py`). El MCP, los imports y el índice RAG trabajan en Markdown; `convert.py` traduce en los dos sentidos. Lo que Markdown sabe decir va en Markdown (con tablas y tachado de GFM); lo demás usa estas directivas.

## Bloques

| Bloque | Markdown |
| --- | --- |
| Panel | `:::panel{kind=warning}` … `:::` (`info`, `tip`, `warning`, `error`, `note`) |
| Expand | `:::expand{title="Más"}` … `:::` |
| Columnas | `::::columns{layout=two}`, cada columna en `:::column` … `:::`, y cierra `::::` (`two`, `three`, `sidebar_left`, `sidebar_right`) |
| Tabla de contenido | `[[toc]]` en su propia línea |
| Árbol de hijas | `[[children]]` en su propia línea |
| Imagen | `![alt](src "pie de foto"){size=large align=center}`; una imagen subida a Folio usa `asset:<id>` como src |
| Archivo | `::file{asset=<id> name="spec.pdf" type=application/pdf size=1024}` |
| Video | `::video{src="https://…" caption="Demo"}` o `::video{asset=<id>}` |
| Checklist | `- [ ]` y `- [x]` |
| Visual (3.3) | Un bloque de código ` ```visual{format=svg title="…" description="…"} ` con el SVG o HTML; `format` es `svg` o `html` y la descripción es obligatoria |
| Diagrama | ` ```mermaid ` con el código de Mermaid; opcional `{caption="…"}` |
| Fórmula | ` ```math ` con LaTeX (KaTeX) |
| Gráfica | ` ```chart{kind=bar title="…"} ` con una tabla GFM: la primera fila nombra las columnas, la primera columna son etiquetas y el resto números (`bar`, `line`, `area`, `pie`) |
| Timeline | ` ```timeline ` con una línea por hito: `fecha \| título \| texto` (fecha y texto opcionales) |
| Comparación | `::::compare`, cada lado en `:::side{title="Antes"}` … `:::`, y cierra `::::` (2 o 3 lados) |
| Lista por label | `::pages{label=onboarding limit=5 space=docs}`: las páginas con ese label que puede ver quien lee |
| Vista de una database | `::database{id=<uuid> view=board}`: las filas de esa vista; sin `view`, la primera. Quien no puede ver la database ve que no tiene acceso |

Un bloque de código con esos nombres que no forma un bloque válido (una gráfica sin filas, un visual sin descripción) se queda como bloque de código.
| Action item | `::task[texto]{id=ai-1 assignee=ana due=2026-11-01 done=true}` en su propia línea; sin `id`, se genera uno estable. Va a Mis tareas del asignado (fase 2) |

Un contenedor dentro de otro usa un `:` más en su apertura y su cierre (`:::expand` con un `::::panel` adentro), para que se lean bien. Al leer, cada `:::` cierra el contenedor abierto más reciente.

## En línea

| Elemento | Markdown |
| --- | --- |
| Mención | `@handle` |
| Status | `:status[Listo]{color=green}` (`grey`, `blue`, `green`, `yellow`, `red`, `purple`) |
| Subrayado | `:u[texto]` |
| Salto de línea | `\` al final de la línea |

## Lo que se pierde

Las celdas combinadas, el ancho y el color de fondo de las celdas no tienen equivalente en Markdown y no sobreviven la ida y vuelta. El `id` de los encabezados se vuelve a calcular del texto.
