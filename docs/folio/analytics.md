# Analytics y audit de Folio (5.9)

## Qué se cuenta

- **Lecturas:** abrir una página publicada en la web cuenta una vista (`POST /api/v1/folio/analytics/views`). Se guarda una fila por lector, página y día (`folio_page_views`), así que las vistas por día y los lectores únicos salen de una sola consulta. Las lecturas por la API o el MCP no cuentan.
- **Búsquedas:** cada búsqueda de `GET /search` queda en `folio_search_logs` con su modo y cuántos resultados dio, y regresa `search_id`. Al abrir un resultado desde la página de búsqueda se guarda cuál fue. La búsqueda mientras se escribe (barra superior, selector de páginas del editor de la home) manda `track=false` y no se guarda, para que las palabras a medias no llenen la lista. Las búsquedas de agentes por `search_docs` sí cuentan.
- **Tiempo de lectura:** aproximado, a 200 palabras por minuto del texto publicado.

## Quién ve qué

| Qué | Quién |
| --- | --- |
| Analytics de una página (`GET /analytics/pages/{id}`, botón Analytics, tool `get_page_analytics`) | Dueño de la página (metadata `owner`) y admins del space |
| Nombres de lectores | Solo si el space lo permite: ajuste "Mostrar quién leyó" (`show_readers`, apagado por default). Si no, solo se cuentan |
| Tablero del sitio (`GET /analytics/site`, Admin → Analytics) | Admins de Folio |
| Búsquedas sin resultados y preguntas del chat sin respuesta (tool `get_search_gaps`) | Admins de Folio |

El tablero del sitio solo lista páginas que el admin puede ver. Las preguntas sin respuesta son las de 4.5 (`chat.unanswered`): sin cita o con pulgar abajo.

## Audit

Las entradas de Folio van al audit log de platform con `app = folio`. Para escribir una, usa `radicle.folio.services.audit_log.record(db, actor, "accion", target_type=..., target_id=..., before=..., after=...)`; la acción va sin el prefijo `folio.` y tiene que estar en `audit.ACTIONS`.

| Acción | Cuándo |
| --- | --- |
| `folio.grant_set`, `folio.grant_remove` | Roles globales |
| `folio.space_grants_change` | Permisos de un space |
| `folio.restrictions_change` | Restricciones de una página |
| `folio.submission_approve`, `folio.submission_reject` | Aprobaciones |
| `folio.public_link_create`, `folio.public_link_revoke` | Links públicos (5.1) |
| `folio.export_create` | Exports (5.2) |
| `folio.import_run` | Imports (5.3) |
