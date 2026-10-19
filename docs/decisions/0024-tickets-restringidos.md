# 0024. Tickets restringidos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 4 (4.2)

- Un solo punto de verdad: `core.permissions.visible_tickets_clause(user)`. Lo usa `search.base_query`, y por él el compilador RQL, boards, backlog, timeline, reportes, widgets, la paleta, `next_ticket`, bulk por query y el MCP. Los fetch por key (`load_ticket`, incluido el alias de una key movida) y los cargadores de comentarios, adjuntos, worklogs y links llaman `can_see`, que usa la misma cláusula. Sin caché: salir de un grupo o del nivel quita el acceso en el siguiente request.
- Ve un ticket con nivel: quien tiene el nivel (directo o por grupo), los admins de su proyecto (directos o por grupo) y los admins de instancia y, si `include_participants`, su reporter, assignee y colaboradores. Un ticket no visible da 404, nunca 403.
- Links y padre hacia un ticket no visible salen como `{key: null, title: null, restricted: true}` ("Ticket restringido"). Los hijos no visibles se omiten de la lista y del conteo. En el historial, las keys de tickets no visibles en eventos de links, padre y clon se reemplazan por `restricted`. El carril "por padre" de un board usa la etiqueta "Restricted ticket".
- Reportes: los números agregados (CFD, creados vs resueltos, distribución, burndown, burnup, progreso y pronóstico de milestone) cuentan los tickets restringidos del proyecto para que cuadren (`base_query(include_restricted=True)`); las listas (control chart, tiempo por ticket, filas del sprint report, widgets de listas) no los muestran.
- Poner o quitar nivel es un campo más del `PATCH /tickets/{key}` (`security_level` por nombre) y pide `ticket.set_security`; queda como `field_changed`. Un nivel con tickets no se puede borrar.
- `tests/integration/test_restricted.py` lee todas las rutas GET del OpenAPI y falla si aparece una que no está cubierta o exenta con razón; también recorre las tools de lectura del MCP.
