# Radicle Folio: Build spec fase 2 (Colaboración)

Oct 20, 2026 · @Fernando

La fase 2 convierte a Folio en un lugar donde el equipo escribe junto: edición en tiempo real, comentarios, avisos y herramientas para mantener los docs vivos.

## Objetivo y entregables

Al terminar la fase 2, varias personas y agentes escriben el mismo documento al mismo tiempo, se ven los cursores, se comenta sobre el texto, y los docs se mantienen al día con dueños, estados y vencimientos.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 2.1 | Bus de eventos y notificaciones en platform | Outbox transaccional, worker de despacho, notificaciones in-app (SSE) y email con preferencias, según el spec de Docket etapa 5 pero en `platform` | Una mención en Folio llega in-app al instante y por email; Docket podrá usar lo mismo en su etapa 5 |
| 2.2 | Tiempo real | Yjs en el editor, servidor pycrdt-websocket, presencia con cursores del mouse tipo Figma y selección de texto | Tres navegadores editan la misma página, convergen al mismo contenido y se ven los cursores |
| 2.3 | Comentarios | Al pie con hilos e inline anclados al texto; resolver; huérfanos | Un comentario inline sigue en su lugar después de editar el párrafo y se marca huérfano si se borra el texto |
| 2.4 | Menciones, reacciones, watch, compartir y action items | Avisos de menciones; reacciones; seguir página o space; compartir con mensaje; action items con assignee y fecha; Mis tareas | Marco una tarea desde Mis tareas y se marca en el documento |
| 2.5 | Live docs | Documentos siempre editables, sin publicación, con snapshots de historial | Una minuta se escribe entre tres y su historial guarda snapshots |
| 2.6 | Organización | Mover entre spaces, copiar con o sin hijas, archivar y restaurar | Archivar saca la página del árbol, la búsqueda y el índice RAG; restaurar la regresa |
| 2.7 | Calidad y navegación | Transferir dueño; estados In review, Verified y Outdated con vencimiento; recientes, favoritos, feed Para ti y su bloque en la home | Una página Verified vencida pasa sola a Outdated y su dueño recibe aviso |

## Modelo de datos

```
-- platform (el esquema de Docket etapa 5, ahora compartido)
events_outbox, event_deliveries, notifications, notification_preferences
users: timezone, digest_hour

folio_nodes (columnas nuevas)
  kind               agrega live_doc
  status             enum(draft, published, in_review, verified, outdated) default draft
  verified_by null, verified_until date null
  archived_at null, archived_by null

folio_spaces (columna nueva)
  verify_days        int default 90

folio_ydocs                                  -- estado colaborativo del borrador o live doc
  node_id pk, state bytea, updated_at
folio_yupdates                               -- updates incrementales antes de compactar
  id bigserial, node_id, update bytea, created_at

folio_live_snapshots                         -- historial de live docs
  id, node_id, content_json, authors uuid[], created_at

folio_comments
  id, node_id, thread_id, parent_id null
  kind               enum(footer, inline)
  author_id, body_json
  anchor             jsonb null              -- posiciones relativas de Yjs y texto citado
  orphaned           bool default false
  resolved_at null, resolved_by null
  created_at, edited_at null, deleted_at null

folio_reactions
  target_type enum(node, comment), target_id, user_id, emoji   -- pk compuesta

folio_watches
  user_id, target_type enum(node, space), target_id, source enum(auto, manual)

folio_action_items                           -- índice derivado del documento
  id, node_id, item_key                      -- id estable del bloque en el documento
  text, assignee_id null, due_date null, done bool, updated_at

folio_favorites
  user_id, target_type enum(node, space), target_id, created_at

folio_views                                  -- lecturas para recientes y más leídos
  node_id, user_id, viewed_at
folio_view_counts_daily
  node_id, date, views, unique_viewers
```

## Comportamiento

### Tiempo real

- WebSocket en `/api/v1/folio/collab/{node_id}` con la sesión del usuario. Al conectar se valida permiso de edición; quien solo lee no se conecta y ve la versión publicada.
- Un room de pycrdt-websocket por nodo. Los updates se guardan en `folio_yupdates` y se compactan en `folio_ydocs` cada 30 s o al quedar vacío el room.
- `folio_drafts.content_json` se regenera del Y.Doc cada 5 s para que API y MCP lean el borrador sin abrir el room.
- Migración: los borradores de fase 1 se convierten a Y.Doc al primer acceso; lo publicado no cambia.
- **Presencia tipo Figma:** cada cliente comparte por awareness su nombre, color (de una paleta de 8 tonos que pasan contraste sobre ambos fondos), selección de texto y posición del mouse relativa al contenedor del documento, a 30 actualizaciones por segundo como máximo. Se dibuja el puntero con una etiqueta con el nombre; se esconde tras 10 s sin moverse. Arriba se ven los avatares de quien está en el documento.
- **Agentes en vivo:** cuando un agente cambia un borrador por API o MCP, el servidor aplica el cambio al Y.Doc, así quien está editando lo ve aparecer con la etiqueta del agente.
- Publicar toma el estado del Y.Doc en ese instante.
- Límite de 50 editores simultáneos por documento.

### Comentarios

- **Al pie:** hilos con respuestas, markdown, editar y borrar lo propio.
- **Inline:** al seleccionar texto aparece Comentar; el ancla guarda posiciones relativas de Yjs y el texto citado. Las ediciones alrededor no lo mueven; si se borra todo el texto anclado, el hilo se marca huérfano y se muestra en el panel con su cita.
- Resolver oculta el hilo y el resaltado, y queda en el historial. Reabrir es posible.
- En la vista de lectura los comentarios inline se ven al margen, como en el diseño del modo enfoque.

### Avisos

| Evento | Quién recibe |
| --- | --- |
| @mención en un comentario | La persona mencionada, al instante |
| @mención en el contenido | Al publicar (o a los 10 s de inactividad en un live doc), para no avisar mientras se escribe |
| Comentario o respuesta | Watchers de la página y participantes del hilo |
| Publicación | Watchers de la página y del space |
| Action item asignado | El asignado |
| Compartir | Las personas o grupos elegidos, con el mensaje |
| Envío de agente pendiente | Admins de Folio |
| Página pasa a Outdated | Su dueño |

El autor sigue su página automáticamente. Nadie recibe aviso de su propia acción ni de algo que no puede ver.

### Action items

- Bloque propio del editor: casilla, texto, @persona y fecha opcional, con un id estable.
- Al guardar se sincroniza `folio_action_items` (índice derivado, la fuente es el documento).
- Mis tareas lista los pendientes de todos los documentos visibles, agrupados por fecha. Marcar uno desde ahí aplica el cambio al Y.Doc del documento.

### Live docs

- No tienen borrador ni publicación: el Y.Doc es el contenido. No exigen metadata.
- Cada 10 minutos con cambios se guarda un snapshot en `folio_live_snapshots` con sus autores; el historial los muestra y permite restaurar.
- No entran al índice RAG en esta fase.

### Organización

- **Mover entre spaces:** requiere crear en el destino y borrar en el origen; conserva restricciones, historial y URL (basada en id); reindexa.
- **Copiar:** crea nodos nuevos con borrador igual al contenido publicado, sin publicar; opcional con hijas.
- **Archivar:** el nodo y sus hijas salen del árbol (quedan en la sección Archivados del space), de la búsqueda por default y del índice RAG. Restaurar los regresa y reindexa.

### Calidad

- Al publicar por primera vez, el estado pasa a `published`. Desde ahí el dueño o un admin del space puede marcar In review o Verified.
- Verified pone `verified_until = hoy + verify_days` del space. Un job diario pasa a Outdated lo vencido y avisa al dueño; volver a verificar reinicia el plazo.
- El estado viaja en la metadata de los chunks; la búsqueda da un pequeño empuje a Verified y baja a Outdated.
- Transferir dueño queda en el historial.

### Navegación

- Recientes: lo último leído o editado. Favoritos: estrella en páginas y spaces.
- Feed Para ti: publicaciones de lo que el usuario sigue y lo más leído de la semana en sus spaces. La home agrega el bloque Para ti y Más leídos ya usa vistas reales.

## API REST, MCP y UI

### Endpoints nuevos (prefijo `/api/v1/folio` salvo los de platform)

| Método | Ruta | Qué hace |
| --- | --- | --- |
| WS | `/collab/{node_id}` | Sincronización Yjs y awareness |
| GET, POST | `/nodes/{id}/comments` | Hilos con respuestas; crear al pie o inline con `anchor` |
| PATCH, DELETE | `/comments/{id}` | Editar, borrar |
| POST | `/comments/{id}/resolve`, `/reopen` | |
| PUT, DELETE | `/reactions/{target_type}/{id}/{emoji}` | |
| PUT, DELETE | `/watch/{target_type}/{id}` | Seguir página o space |
| POST | `/nodes/{id}/share` | `{users?, groups?, message, grant_view?}` |
| GET | `/me/tasks?status` | Mis tareas |
| PATCH | `/action-items/{id}` | `{done}`; aplica al documento |
| POST | `/nodes` | Acepta `kind = live_doc` |
| GET | `/nodes/{id}/snapshots` | Historial de live docs |
| POST | `/nodes/{id}/move` | Acepta `space` destino |
| POST | `/nodes/{id}/copy` | `{space?, parent?, include_children}` |
| POST | `/nodes/{id}/archive`, `/unarchive` | |
| PATCH | `/nodes/{id}/status` | `{status}`; Verified calcula vencimiento |
| PATCH | `/nodes/{id}/owner` | Transferir dueño |
| PUT, DELETE | `/favorites/{target_type}/{id}` | |
| GET | `/me/recents`, `/me/favorites`, `/me/feed` | Navegación |
| GET | `/api/v1/me/notifications`, `/stream` | Platform: lista y SSE |
| POST | `/api/v1/me/notifications/read` | Platform |
| GET, PUT | `/api/v1/me/notification-preferences` | Platform |

RQL de docs agrega `status`, `archived` (default false), `watched_by`, `favorite_of` y `has_open_tasks`.

### Tools nuevas del MCP

| Tool | Parámetros | Qué hace |
| --- | --- | --- |
| `list_comments` | `id`, `include_resolved=false` | Hilos con texto citado de los inline |
| `add_comment` | `id`, `body`, `quote?`, `thread_id?` | Al pie, inline sobre la primera aparición de `quote`, o respuesta |
| `resolve_comment` | `thread_id` | |
| `create_live_doc` | `space`, `title`, `content_md?`, `parent?` | Para minutas y dailies |
| `append_to_live_doc` | `id`, `content_md` | Agrega al final sin pisar lo que otros escriben |
| `list_my_tasks` | `status=open` | Action items asignados al agente |
| `set_task_done` | `id`, `done` | |
| `watch` | `target_type`, `id` | |
| `get_feed` | `limit=20` | Para que un agente se entere de lo nuevo |
| `list_notifications` | `unread_only=true` | Menciones y asignaciones del agente |

### UI

| Pantalla o cambio | Detalle |
| --- | --- |
| Editor | Avatares de presencia arriba; cursores con etiqueta; selección de cada quien en su color; los cambios de un agente se ven con su etiqueta |
| Comentarios | Botón flotante al seleccionar; panel lateral con hilos, filtros (abiertos, resueltos, huérfanos); resaltado inline en lima suave |
| Lectura | Barra con reacciones, Seguir y Compartir; comentarios inline al margen |
| Mis tareas | Lista agrupada por vencidas, hoy, próximas y sin fecha, con link al documento |
| Space | Sección Archivados; menú del nodo con Mover, Copiar, Archivar |
| Estado | Badge en lectura y en tarjetas; botón Verificar para el dueño; aviso de vencimiento |
| Sidebar | Recientes y favoritos arriba del árbol |
| Home | Bloques Para ti y Más leídos con datos reales |
| Topbar | Campanita de notificaciones de platform |

## Tests

| Área | Casos mínimos |
| --- | --- |
| Bus y notificaciones | Evento en la misma transacción; worker detenido y reiniciado sin pérdidas ni duplicados; cada aviso de la tabla llega a quien debe; nunca al actor ni a quien no ve el nodo; preferencias por tipo y canal |
| Tiempo real | Tres clientes simulados con ediciones concurrentes convergen al mismo JSON; reconexión sin pérdida; compactación; quien solo lee es rechazado en el WebSocket; un agente edita por API mientras hay humanos conectados y todos lo ven |
| Presencia | Awareness con nombre, color, selección y puntero; límite de frecuencia; ocultar tras inactividad |
| Comentarios | Ancla sobrevive a ediciones antes, dentro y después del texto; huérfano al borrarlo todo; resolver y reabrir |
| Menciones | En comentario avisa al instante; en contenido solo al publicar; en live doc tras inactividad |
| Action items | Extracción con id estable; marcar desde Mis tareas cambia el documento; reasignar avisa |
| Live docs | Sin metadata ni publicación; snapshots cada 10 minutos con cambios; restaurar snapshot; fuera del RAG |
| Organización | Mover entre spaces con permisos en ambos; copiar con y sin hijas; archivar saca de árbol, búsqueda y RAG; restaurar reindexa |
| Calidad | Vencimiento por space; job diario idempotente; aviso al dueño; empuje en búsqueda |
| MCP | Cada tool nueva con caso feliz y error; `append_to_live_doc` con humanos editando no pisa sus cambios |
| E2E | Playwright con tres contextos de navegador escribiendo la misma minuta, viendo cursores, comentando inline y resolviendo |
| Rendimiento | 20 editores en un documento de 10,000 palabras: latencia de sincronización p95 menor a 150 ms en red local |

## Criterios de aceptación de la fase

- [ ] Tres personas escribimos la misma minuta y nos vemos los cursores del mouse con nombre.
- [ ] Un agente agrega una sección por MCP mientras escribimos y aparece en vivo con su etiqueta.
- [ ] Comento sobre una frase, alguien edita el párrafo y el comentario sigue en su lugar.
- [ ] Me mencionan en un comentario y me llega aviso in-app y por email.
- [ ] Asigno un action item, la persona lo marca desde Mis tareas y se marca en el documento.
- [ ] Archivo una página y ya no sale en la búsqueda semántica; la restauro y vuelve.
- [ ] Una página Verified que vence pasa a Outdated y su dueño recibe aviso.
- [ ] La home muestra Para ti y Más leídos con datos reales.
- [ ] Docket sigue pasando todos sus tests.

## Fuera de alcance

Templates, editor de la home, bloque Visual, suite visual, whiteboards, databases y embeds (fase 3). Liga con Docket, chat RAG y escritura con IA (fase 4). Slack, Teams, webhooks, automatización y páginas públicas (fase 5).
