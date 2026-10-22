# Calendarios (Folio 5.8)

Cada space puede tener calendarios: vacaciones, releases, guardias, eventos. Se ven en `/folio/s/{space}/calendar` en vista de mes o de semana. Cada evento lleva el color de su categoría.

## Quién hace qué

| Permiso en el space | Puede |
| --- | --- |
| `view` | Ver los calendarios y copiar el link del feed |
| `create` | Agregar eventos y cambiar o borrar los suyos |
| `delete_any` | Cambiar o borrar cualquier evento |
| `admin` | Crear, renombrar y borrar calendarios, elegir sus proyectos de Docket y cambiar el link del feed |

## Eventos

- **Con hora:** se guardan en UTC y se ven en la hora local de quien lee.
- **De día completo:** son días enteros en UTC con el final exclusivo, como en iCal. En el formulario se escribe el último día.
- **Categoría:** `vacation`, `release`, `event`, `oncall` u `other`.
- **Personas:** ligadas por handle.
- **Duración:** un evento dura hasta 366 días. La agenda se pide en rangos de hasta 400 días.

## Milestones de Docket

Un calendario puede mostrar los milestones con fecha de los proyectos de Docket que elija su admin. Se leen con `docket.public` y con los permisos de quien lee: el milestone de un proyecto que no puedes ver no aparece.

## Feed iCal

- `GET /ical/{token}.ics` sirve el calendario en RFC 5545, para suscribirse desde Google Calendar u Outlook.
- No pide sesión: el link es el acceso. Quien tenga el link puede leer el calendario.
- Cambiar el link en los ajustes del calendario corta las suscripciones viejas, y borrar el calendario también.
- El feed cubre desde un año atrás hasta dos años adelante.
- Los milestones del feed son los que puede ver quien creó el calendario.

## Bloque y home

- **En una página:** `::calendar{id=<uuid> view=week}`, o `/` → Calendario en el editor.
- **En la home:** un bloque Calendario.
- **Sin acceso:** quien no puede ver el calendario ve un aviso en su lugar; en la home, el bloque no aparece.

## API y MCP

- REST: `/api/v1/folio/calendars` (sin `space` lista los de todos tus spaces), `/calendars/{id}`, `/calendars/{id}/ical-token` y `/calendars/{id}/events`.
- MCP: `list_calendar_events` y `add_calendar_event`, con el calendario por id o por nombre.
