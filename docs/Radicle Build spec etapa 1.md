# Radicle: Build spec etapa 1 (Core + MCP)

Oct 18, 2026 · @Fernando

La etapa 1 entrega el core de Radicle y el servidor MCP: un proyecto se puede trabajar completo por personas y agentes desde el día 1. Las reglas generales, el stack y la estructura del repo están en el documento de control.

## Objetivo y alcance

Al terminar la etapa 1, una persona levanta Radicle con un comando, crea un proyecto con sus áreas y milestones, y lo trabaja junto con agentes conectados por MCP.

**Incluye**

- Instalación con Docker Compose y pantalla de setup inicial.
- Usuarios humanos con password y agentes con token. Tokens personales.
- Proyectos con key, miembros con rol (admin, member, viewer), áreas y milestones.
- Tickets Task, Bug y Draft con todos los campos fijos: título, descripción markdown, assignee, colaboradores, reporter, prioridad, due date, estimación en horas, tags, área, milestone y ticket padre.
- Checklist dentro de la descripción con assignee por item.
- Workflows default por tipo, categorías de estado y resolutions.
- Links entre tickets: blocks, relates to, duplicates, clones.
- Comentarios markdown con @menciones y reacciones.
- Historial inmutable de cada ticket.
- Lenguaje de queries RQL y búsqueda full-text.
- API REST completa con OpenAPI.
- Servidor MCP con las tools de todo lo anterior.
- UI web: board básico, lista con RQL, detalle de ticket, settings del proyecto y admin.

**No incluye**

Todo lo de las etapas 2 a 5. La lista completa está en Fuera de alcance al final.

## Entregables

Se construyen en orden; cada uno se acepta antes de empezar el siguiente.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 1.1 | Base, auth y usuarios | Monorepo, Dockerfile, docker compose, CI, config por env, `/health`, Alembic, setup inicial, login con sesión, usuarios, agentes, tokens personales y de agente | `docker compose up` levanta la app; el setup crea el admin; un token de agente autentica contra `/api/v1/me`; CI verde |
| 1.2 | Proyectos, miembros, áreas y milestones | CRUD de proyectos con key, siembra de workflows default, miembros con rol, áreas, milestones con conteo por categoría | Se crea ProyectoA (PA) con 4 áreas y milestone V1; un viewer no puede editar nada; un no miembro recibe 404 |
| 1.3 | Tickets e historial | CRUD de tickets, campos fijos, tags, colaboradores, ticket padre, checklist parseado, menciones en descripción, versionado optimista, soft delete, historial inmutable | Keys consecutivas sin duplicados bajo concurrencia; cada cambio aparece en el historial con valor anterior y nuevo; el historial no se puede modificar ni desde SQL |
| 1.4 | Workflows y transiciones | Transiciones válidas por tipo, resolutions obligatorias en Done, cierre anticipado, reabrir, cambio de tipo, aviso de bloqueado | Las transiciones inválidas regresan 409 con la lista de válidas; Done sin resolution falla; reabrir limpia la resolution |
| 1.5 | Links, comentarios y reacciones | Los 4 tipos de link con su inverso, comentarios markdown, editar y borrar propios, menciones, reacciones | Un link aparece en ambos tickets con la etiqueta correcta; un comentario borrado queda como "comentario eliminado" en el historial |
| 1.6 | RQL y búsqueda | Parser, compilador a SQL, filtro de permisos, full-text, orden, paginación, metadatos para autocompletar | Los ejemplos del spec regresan lo esperado; errores con posición; p95 menor a 300 ms con 10,000 tickets |
| 1.7 | Servidor MCP | Tools de la sección MCP, recurso con la guía de RQL, auth por token, errores accionables | Claude Code conectado con token de agente completa el flujo de aceptación del agente |
| 1.8 | UI web | Setup, login, proyectos, board básico, lista con RQL, detalle de ticket, crear ticket, milestones, settings, admin de usuarios y agentes, perfil, tema lima claro y oscuro, i18n | E2E de Playwright pasa; la UI se usa completa sin tocar la API a mano |

## Modelo de datos

PostgreSQL 16 con extensiones `citext` y `pg_trgm`. Todas las tablas tienen `id uuid` como llave primaria (salvo donde se indica) y `created_at` en UTC. Los enums se definen como tipos de Postgres.

```
users
  id                 uuid pk
  email              citext unique null      -- null en agentes
  handle             citext unique           -- ^[a-z0-9][a-z0-9_-]{1,31}$, para @menciones
  display_name       text
  kind               enum(human, agent)
  password_hash      text null               -- argon2id; null en agentes
  is_instance_admin  bool default false
  is_active          bool default true
  created_at, updated_at

api_tokens
  id, user_id fk users
  name               text                    -- ej. "claude-code laptop"
  prefix             text                    -- primeros 8 caracteres, se muestran en UI
  token_hash         text unique             -- sha256 del token completo
  last_used_at, expires_at null, revoked_at null, created_at
  -- formato del token: rdc_ + 40 caracteres base62, se muestra una sola vez

sessions
  id, user_id, token_hash unique, expires_at, ip, user_agent, created_at
  -- cookie HttpOnly, Secure, SameSite=Lax, 14 días deslizantes

projects
  id
  key                citext unique           -- ^[A-Z][A-Z0-9]{1,9}$, inmutable
  name, description_md
  ticket_seq         int default 0           -- contador de números de ticket
  created_by fk users, created_at, updated_at, archived_at null

project_members
  project_id, user_id                        -- pk compuesta
  role               enum(admin, member, viewer)
  created_at

areas
  id, project_id
  name               text                    -- unique(project_id, lower(name))
  color              text null               -- hex
  position           int
  archived_at null

milestones
  id, project_id
  name               text                    -- unique(project_id, lower(name))
  description_md, target_date date null
  status             enum(open, closed), closed_at null
  position           int

statuses
  id, project_id
  ticket_type        enum(task, bug, draft)
  name               text                    -- unique(project_id, ticket_type, lower(name))
  category           enum(todo, in_progress, done)
  position           int
  is_initial         bool                    -- exactamente uno por (project, type)

transitions
  id, project_id, ticket_type
  name               text                    -- ej. "Start", "Close", "Reopen"
  from_status_id     null                    -- null = desde cualquier estado no Done
  to_status_id
  allowed_resolutions enum[] null            -- null = todas; solo aplica si destino es Done
  position           int

tickets
  id, project_id
  number             int                     -- unique(project_id, number); key = project.key-number
  type               enum(task, bug, draft)
  title              text                    -- 1 a 255 caracteres
  description_md     text default ''
  status_id fk statuses
  resolution         enum(done, wont_do, duplicate, cannot_reproduce) null
  priority           enum(highest, high, medium, low, lowest) default medium
  area_id null, milestone_id null, parent_id null fk tickets
  assignee_id null, reporter_id fk users
  due_date           date null
  estimate_hours     numeric(7,2) null       -- 0 a 9999
  tags               text[] default '{}'     -- sin #, ^[a-z0-9][a-z0-9_-]{0,49}$, máx 20
  rank               text                    -- orden lexicográfico (fractional indexing)
  version            int default 1           -- bloqueo optimista
  search_vector      tsvector generated      -- título peso A, descripción peso B
  created_at, updated_at, resolved_at null, deleted_at null
  -- índices: GIN(tags), GIN(search_vector), GIN(title gin_trgm_ops),
  --          (project_id, status_id), assignee_id, milestone_id, area_id,
  --          parent_id, due_date, updated_at

ticket_collaborators
  ticket_id, user_id                         -- pk compuesta

ticket_links
  id, source_id fk tickets, target_id fk tickets
  type               enum(blocks, relates_to, duplicates, clones)
  created_by, created_at
  -- unique(source_id, target_id, type); check(source_id <> target_id)
  -- "A blocks B" se guarda source=A, target=B; B lo muestra como "is blocked by A"

comments
  id, ticket_id, author_id
  body_md            text                    -- 1 a 50,000 caracteres
  created_at, edited_at null, deleted_at null

comment_reactions
  comment_id, user_id, emoji                 -- pk compuesta; un emoji Unicode

mentions
  id, ticket_id, comment_id null, mentioned_user_id, created_at
  -- se recalculan al guardar descripción o comentario; se usan en etapa 5

ticket_events                                -- historial, solo inserción
  id                 bigserial pk
  ticket_id, actor_id
  event_type         text                    -- ver catálogo abajo
  field              text null
  old_value          jsonb null
  new_value          jsonb null
  created_at
  -- trigger BEFORE UPDATE OR DELETE que lanza excepción
  -- índice (ticket_id, id desc)
```

**Catálogo de eventos del historial:** `created`, `field_changed`, `status_changed`, `type_changed`, `checklist_item_toggled`, `collaborator_added`, `collaborator_removed`, `link_added`, `link_removed`, `comment_added`, `comment_edited`, `comment_deleted`, `deleted`, `restored`.

Cada `field_changed` guarda un evento por campo. Para `description_md` se guarda el texto completo anterior y nuevo; la UI muestra el diff.

## Workflows default y reglas de negocio

### Workflows que se siembran al crear un proyecto

**Task**

| Estado | Categoría | Inicial |
| --- | --- | --- |
| To Do | todo | sí |
| In Progress | in\_progress |  |
| In Review | in\_progress |  |
| Done | done |  |

| Transición | Desde | Hacia | Resolutions permitidas |
| --- | --- | --- | --- |
| Start | To Do | In Progress |  |
| Stop | In Progress | To Do |  |
| Send to review | In Progress | In Review |  |
| Request changes | In Review | In Progress |  |
| Complete | In Review | Done | todas |
| Close | cualquiera no Done | Done | wont\_do, duplicate |
| Reopen | Done | To Do |  |

**Bug**

| Estado | Categoría | Inicial |
| --- | --- | --- |
| Reported | todo | sí |
| In Progress | in\_progress |  |
| QA Verified | in\_progress |  |
| Done | done |  |

| Transición | Desde | Hacia | Resolutions permitidas |
| --- | --- | --- | --- |
| Start | Reported | In Progress |  |
| Stop | In Progress | Reported |  |
| Send to QA | In Progress | QA Verified |  |
| QA failed | QA Verified | In Progress |  |
| Complete | QA Verified | Done | todas |
| Close | cualquiera no Done | Done | wont\_do, duplicate, cannot\_reproduce |
| Reopen | Done | Reported |  |

**Draft**

| Estado | Categoría | Inicial |
| --- | --- | --- |
| New | todo | sí |
| In Review | in\_progress |  |
| Approved | done |  |
| Discarded | done |  |

| Transición | Desde | Hacia | Resolutions permitidas |
| --- | --- | --- | --- |
| Review | New | In Review |  |
| Approve | In Review | Approved | done |
| Discard | cualquiera no Done | Discarded | wont\_do, duplicate |
| Reopen | Approved, Discarded | New |  |

### Reglas de transición

1. Solo se permite una transición que exista para el tipo del ticket, desde su estado actual o con `from_status_id` nulo.
2. Si el destino es categoría `done`, la resolution es obligatoria y debe estar en `allowed_resolutions`. Si sólo hay una permitida, se pone sola.
3. Al entrar a `done` se llena `resolved_at`. Al salir de `done` se limpian `resolution` y `resolved_at`.
4. Un error de transición regresa 409 con las transiciones válidas desde el estado actual.
5. **Bloqueado:** si el ticket tiene links `is blocked by` hacia tickets que no están en `done` y el destino es `in_progress` o `done`, la transición se hace y la respuesta trae `warnings: [{"code": "blocked", "by": ["PA-4"]}]`.

### Cambio de tipo

- `POST /tickets/{key}/type` con el tipo nuevo. El ticket pasa al estado inicial del workflow del tipo nuevo y se limpia la resolution.
- Si el tipo nuevo es Task o Bug y el ticket no tiene área, la petición debe incluir `area`.
- Se registra un evento `type_changed` y un `status_changed`.

### Reglas de campos

| Campo | Regla |
| --- | --- |
| `area` | Obligatoria en Task y Bug, opcional en Draft. Debe ser del mismo proyecto y no estar archivada. |
| `milestone` | Del mismo proyecto y con status `open`. |
| `parent` | Del mismo proyecto, sin ciclos (un ticket no puede ser ancestro de sí mismo), sin límite de profundidad. |
| `assignee`, colaboradores | Miembros del proyecto con rol member o admin. Pueden ser humanos o agentes. |
| `reporter` | Quien crea el ticket; no se edita. |
| `tags` | Se normalizan a minúsculas y sin `#`. Máximo 20 por ticket. |
| `estimate_hours` | Entre 0 y 9999, dos decimales. |
| `title` | Sin saltos de línea, 1 a 255 caracteres, se recorta espacio. |

### Numeración de tickets

Dentro de la misma transacción de creación: `UPDATE projects SET ticket_seq = ticket_seq + 1 WHERE id = :id RETURNING ticket_seq`. Así no hay duplicados ni huecos aunque la transacción se revierta.

### Versionado optimista

`PATCH /tickets/{key}` requiere `If-Match: <version>` o `expected_version` en el body. Si no coincide, 409 con el ticket actual. En el MCP `expected_version` es opcional; si no se manda, gana el último cambio.

### Checklist

- Se parsea de `description_md`, ignorando bloques de código.
- Un item es una línea `- [ ] texto` o `- [x] texto` (también `*` y `X`), con o sin sangría.
- El assignee del item es el último `@handle` de la línea. Si el handle no existe, el item se marca `assignee_unknown: true`.
- Los items se numeran desde 0 en orden de aparición.
- `PATCH /tickets/{key}/checklist/{index}` reescribe solo esa línea y genera `checklist_item_toggled`.

### Menciones

Cualquier `@handle` válido fuera de bloques de código en descripción o comentarios se guarda en `mentions`. En esta etapa no notifica; las notificaciones llegan en etapa 5.

### Soft delete

Borrar un ticket llena `deleted_at`. Desaparece de búsquedas, boards y links. Sus hijos pierden el padre (con evento). Un admin lo puede restaurar.

### Permisos de la etapa 1

| Acción | Viewer | Member | Admin del proyecto | Admin de instancia |
| --- | --- | --- | --- | --- |
| Ver proyecto, tickets, historial | sí | sí | sí | sí |
| Crear, editar, mover tickets |  | sí | sí | sí |
| Comentar, reaccionar, linkear |  | sí | sí | sí |
| Editar o borrar comentarios propios |  | sí | sí | sí |
| Borrar comentarios de otros |  |  | sí | sí |
| Borrar y restaurar tickets |  |  | sí | sí |
| Áreas, milestones, miembros, settings |  |  | sí | sí |
| Crear proyectos |  |  |  | sí |
| Usuarios, agentes y sus tokens |  |  |  | sí |

Un no miembro recibe 404 en todo lo del proyecto, nunca 403, para no revelar que existe. Los agentes siguen exactamente la misma tabla según su rol, pero no pueden iniciar sesión en la UI.

## RQL (Radicle Query Language)

Lenguaje de filtros para la UI, la API y el MCP. Se parsea con Lark a un AST y se compila a un `select` de SQLAlchemy. El filtro de permisos (solo proyectos donde el usuario es miembro y tickets no borrados) se aplica siempre, aunque la query no lo pida.

### Gramática

```
query      := expr? ("ORDER BY" sort ("," sort)*)?
expr       := term (("AND" | "OR") term)*
term       := "NOT" term | "(" expr ")" | clause | tag_short
clause     := field op value
            | field ("IN" | "NOT IN") "(" value ("," value)* ")"
            | field "IS" "NOT"? "EMPTY"
tag_short  := "#" tag                       -- equivale a tag = <tag>
op         := "=" | "!=" | ">" | ">=" | "<" | "<=" | "~" | "!~"
value      := word | "quoted string" | number | date | rel_date | function
rel_date   := ("-" | "+") number ("m" | "h" | "d" | "w")
function   := "currentUser()" | "now()" | "startOfDay()" | "startOfWeek()" | "startOfMonth()"
sort       := sort_field ("ASC" | "DESC")?
```

Palabras clave sin distinguir mayúsculas. AND tiene mayor precedencia que OR. Valores con espacios van entre comillas.

### Campos

| Campo | Tipo | Operadores | Ejemplo |
| --- | --- | --- | --- |
| `project` | key | = != IN | `project = PA` |
| `key` | key | = != IN | `key IN (PA-1, PA-4)` |
| `type` | enum | = != IN | `type = bug` |
| `status` | nombre | = != IN | `status = "In Review"` |
| `category` | enum | = != IN | `category != done` |
| `resolution` | enum | = != IN, IS EMPTY | `resolution = wont_do` |
| `priority` | ordinal | = != IN > >= < <= | `priority >= high` |
| `area` | nombre | = != IN, IS EMPTY | `area = Legal` |
| `milestone` | nombre | = != IN, IS EMPTY | `milestone = "V1"` |
| `assignee` | handle | = != IN, IS EMPTY | `assignee = currentUser()` |
| `collaborator` | handle | = != | `collaborator = luis` |
| `reporter` | handle | = != IN | `reporter = ana` |
| `tag` | texto | = != IN | `tag = backlog` o `#backlog` |
| `parent` | key | = IN, IS EMPTY | `parent = PA-4` |
| `text` | full-text | \~ !\~ | `text ~ "pagos"` |
| `title` | texto | \~ !\~ | `title ~ checkout` |
| `due` | fecha | = > >= < <=, IS EMPTY | `due < +3d` |
| `created`, `updated`, `resolved` | fecha y hora | = > >= < <= | `updated >= -7d` |
| `estimate` | horas | = > >= < <=, IS EMPTY | `estimate > 8` |
| `blocked` | booleano | = | `blocked = true` |
| `linked` | key | = | `linked = PA-4` |

Campos para ordenar: `created`, `updated`, `due`, `priority`, `rank`, `key`, `status`, `estimate`. Orden default: `updated DESC`.

**Semántica a cuidar**

- `status = "In Progress"` compara por nombre sin distinguir mayúsculas, en todos los tipos.
- `priority` es ordinal: highest > high > medium > low > lowest.
- `!=` sobre un campo nulo incluye los nulos (`assignee != luis` incluye los sin asignar).
- `text ~` usa `websearch_to_tsquery` en inglés y español; `title ~` usa `ILIKE` con trigramas.
- `blocked = true` significa tiene al menos un `is blocked by` hacia un ticket que no está en `done`.
- Fechas relativas se calculan en la zona horaria `RADICLE_TIMEZONE` (default UTC).
- Un nombre de área, milestone o handle que no existe no es error: regresa cero resultados y un `warning`.

### Ejemplos que deben funcionar

```
project = PA AND type = bug AND priority >= high AND milestone = "V1" AND tag != backlog
assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC
#backlog AND area = Legal
text ~ "pagos" AND updated >= -7d
blocked = true AND milestone = "V1"
parent = PA-4 AND category = done
(type = bug OR type = draft) AND reporter = ana AND NOT #backlog
```

### Errores

Un error de sintaxis regresa 422 con `position` (carácter), `expected` (tokens válidos) y un mensaje legible. Ej. `Unknown field 'prioridad' at 0. Did you mean 'priority'?` (sugerencia por distancia de edición).

### Límites

- Query de máximo 2,000 caracteres.
- `limit` default 50, máximo 200. Paginación por cursor.

### Autocompletar

`GET /api/v1/search/fields` regresa los campos, sus operadores, y para un proyecto dado los valores posibles (estados, áreas, milestones, handles, tags más usados). La UI lo usa para autocompletar y el MCP lo expone como recurso.

## API REST

### Convenciones

- Base `/api/v1`. OpenAPI en `/api/v1/openapi.json` y docs interactivas en `/api/docs`.
- Auth: cookie de sesión (web) o `Authorization: Bearer rdc_...` (tokens). Las mutaciones con cookie requieren header `X-CSRF-Token`.
- Tickets por key (`PA-12`), personas por handle, áreas y milestones por nombre. También se aceptan los IDs.
- Listas: `?limit=50&cursor=...` y respuesta `{ "items": [...], "next_cursor": "..." }`.
- Mutaciones regresan el recurso completo y `warnings` cuando aplica.
- Errores RFC 9457: `{ "type", "title", "status", "detail", "errors": [...] }`. Códigos: 401 sin auth, 404 no existe o no visible, 409 conflicto (versión, transición, regla), 422 validación, 429 rate limit.
- Rate limit de login: 10 intentos por minuto por IP.

### Endpoints

**Auth y usuarios**

| Método | Ruta | Qué hace | Permiso |
| --- | --- | --- | --- |
| GET | `/health`, `/version` | Estado y versión | público |
| GET | `/setup/status` | Si falta crear el primer admin | público |
| POST | `/setup` | Crea el primer admin; después responde 409 | público, una vez |
| POST | `/auth/login` | Email y password, crea sesión | público |
| POST | `/auth/logout` | Cierra sesión | sesión |
| GET | `/me` | Usuario actual y sus proyectos con rol | autenticado |
| PATCH | `/me` | Nombre, password | humano |
| GET, POST | `/me/tokens` | Listar o crear token; el valor se muestra una vez | humano |
| DELETE | `/me/tokens/{id}` | Revocar | humano |
| GET | `/users` | Usuarios y agentes | admin de instancia |
| POST | `/users` | Crear humano con password temporal | admin de instancia |
| POST | `/agents` | Crear agente y su primer token | admin de instancia |
| PATCH | `/users/{handle}` | Editar, desactivar, hacer admin | admin de instancia |
| POST | `/users/{handle}/tokens` | Nuevo token para un agente | admin de instancia |
| DELETE | `/users/{handle}/tokens/{id}` | Revocar token | admin de instancia |

**Proyectos**

| Método | Ruta | Qué hace | Permiso |
| --- | --- | --- | --- |
| GET | `/projects` | Proyectos donde soy miembro | autenticado |
| POST | `/projects` | Crear; siembra los 3 workflows y agrega al creador como admin | admin de instancia |
| GET | `/projects/{key}` | Detalle con áreas, milestones, workflows y miembros | viewer |
| PATCH | `/projects/{key}` | Nombre, descripción | admin |
| POST | `/projects/{key}/archive`, `/unarchive` | Archivar es solo lectura | admin |
| GET | `/projects/{key}/members` | Miembros con rol | viewer |
| PUT | `/projects/{key}/members/{handle}` | Agregar o cambiar rol | admin |
| DELETE | `/projects/{key}/members/{handle}` | Quitar; no puede quedar sin admin | admin |
| GET, POST | `/projects/{key}/areas` | Listar, crear | viewer, admin |
| PATCH, DELETE | `/projects/{key}/areas/{name}` | Editar, archivar | admin |
| GET, POST | `/projects/{key}/milestones` | Listar con conteo por categoría, crear | viewer, admin |
| PATCH | `/projects/{key}/milestones/{name}` | Editar, cerrar, reabrir | admin |
| GET | `/projects/{key}/workflows` | Estados y transiciones por tipo | viewer |

**Tickets**

| Método | Ruta | Qué hace | Permiso |
| --- | --- | --- | --- |
| GET | `/tickets?q=<rql>&limit&cursor` | Búsqueda con RQL | viewer |
| POST | `/projects/{key}/tickets` | Crear | member |
| GET | `/tickets/{key}` | Detalle completo | viewer |
| PATCH | `/tickets/{key}` | Editar campos, requiere versión | member |
| DELETE | `/tickets/{key}` | Soft delete | admin |
| POST | `/tickets/{key}/restore` | Restaurar | admin |
| GET | `/tickets/{key}/transitions` | Transiciones disponibles | viewer |
| POST | `/tickets/{key}/transitions` | `{ "to_status", "resolution"? }` | member |
| POST | `/tickets/{key}/type` | `{ "type", "area"? }` | member |
| PATCH | `/tickets/{key}/checklist/{index}` | `{ "checked": true }` | member |
| GET | `/tickets/{key}/children` | Subtickets | viewer |
| PUT, DELETE | `/tickets/{key}/collaborators/{handle}` | Agregar, quitar | member |
| GET, POST | `/tickets/{key}/links` | Listar, crear `{ "type", "target" }` | viewer, member |
| DELETE | `/links/{id}` | Quitar | member |
| GET, POST | `/tickets/{key}/comments` | Listar, crear | viewer, member |
| PATCH, DELETE | `/comments/{id}` | Editar o borrar | autor; admin borra |
| PUT, DELETE | `/comments/{id}/reactions/{emoji}` | Reaccionar | member |
| GET | `/tickets/{key}/history` | Eventos, más nuevo primero | viewer |
| GET | `/search/fields?project=PA` | Metadatos de RQL | autenticado |

### Ejemplo de ticket

```json
{
  "key": "PA-4",
  "project": "PA",
  "type": "task",
  "title": "API de pagos",
  "description_md": "Integrar cobro con tarjeta.\n\n- [x] Definir endpoints @luis\n- [ ] Webhook de confirmación @agent-backend",
  "status": { "name": "In Progress", "category": "in_progress" },
  "resolution": null,
  "priority": "high",
  "area": "Backend",
  "milestone": "V1",
  "parent": null,
  "assignee": { "handle": "agent-backend", "kind": "agent" },
  "collaborators": [{ "handle": "luis", "kind": "human" }],
  "reporter": { "handle": "fernando", "kind": "human" },
  "due_date": "2026-11-15",
  "estimate_hours": 8,
  "tags": ["pagos"],
  "checklist": [
    { "index": 0, "text": "Definir endpoints", "checked": true, "assignee": "luis" },
    { "index": 1, "text": "Webhook de confirmación", "checked": false, "assignee": "agent-backend" }
  ],
  "links": [{ "id": "…", "label": "is blocked by", "ticket": { "key": "PA-1", "title": "Términos y condiciones", "category": "todo" } }],
  "children_count": 0,
  "comments_count": 3,
  "blocked": true,
  "version": 7,
  "created_at": "2026-10-18T15:02:11Z",
  "updated_at": "2026-10-18T17:40:03Z",
  "resolved_at": null
}
```

## MCP

### Transporte y autenticación

- SDK oficial de MCP para Python, montado en la misma app FastAPI en `/mcp` con transporte Streamable HTTP.
- Autenticación con `Authorization: Bearer rdc_...`. Normalmente el token de un agente, pero también sirve un token personal.
- Cada tool llama a la API REST en proceso con `httpx.AsyncClient(transport=ASGITransport(app))`, reenviando el token. Así el MCP tiene exactamente las mismas validaciones, permisos e historial que la API.
- Clientes que solo hablan stdio usan `mcp-remote` como puente; el README lo documenta.

### Diseño de las tools

- Nombres en `snake_case` y descripciones escritas para un LLM: qué hace, cuándo usarla y un ejemplo.
- Parámetros por nombre humano: keys, handles, nombres de área y milestone, nombres de estado.
- Respuestas en JSON compacto. Las listas regresan solo lo necesario para decidir; el detalle se pide con `get_ticket`.
- Errores como tool errors con mensaje accionable. Ej. `Transition to 'Done' not allowed from 'To Do'. Valid targets: 'In Progress', 'Done' via 'Close' (resolutions: wont_do, duplicate).`
- Los `warnings` de la API se incluyen en la respuesta (ej. ticket bloqueado).

### Tools

| Tool | Parámetros | Qué hace |
| --- | --- | --- |
| `whoami` |  | Usuario o agente actual y sus proyectos con rol |
| `list_projects` |  | Proyectos visibles con key y nombre |
| `get_project` | `project` | Áreas, milestones abiertos, estados y transiciones por tipo, miembros con handle |
| `search_tickets` | `query`, `limit=20`, `cursor?` | Busca con RQL; regresa key, título, tipo, estado, prioridad, assignee, área, milestone, tags, blocked |
| `my_tickets` | `include_done=false` | Atajo de `assignee = currentUser()` ordenado por prioridad y due |
| `get_ticket` | `key`, `comments=10` | Todo el ticket: campos, checklist, links, hijos, últimos comentarios, versión |
| `create_ticket` | `project`, `type`, `title`, `description?`, `area?`, `milestone?`, `priority?`, `assignee?`, `collaborators?`, `parent?`, `due_date?`, `estimate_hours?`, `tags?` | Crea y regresa el ticket |
| `update_ticket` | `key`, campos a cambiar, `expected_version?` | Solo cambia los campos enviados; `null` limpia |
| `get_transitions` | `key` | Transiciones disponibles y resolutions permitidas |
| `transition_ticket` | `key`, `to_status`, `resolution?` | Mueve el ticket; regresa warnings |
| `change_ticket_type` | `key`, `type`, `area?` | Ej. Draft a Task |
| `set_checklist_item` | `key`, `index`, `checked` | Marca o desmarca un item |
| `add_comment` | `key`, `body` | Comenta en markdown, con @menciones |
| `list_comments` | `key`, `limit=20`, `cursor?` | Comentarios, más nuevo primero |
| `link_tickets` | `source`, `type`, `target` | `type`: blocks, relates\_to, duplicates, clones |
| `unlink_tickets` | `link_id` | Quita un link |
| `add_collaborator`, `remove_collaborator` | `key`, `handle` |  |
| `get_history` | `key`, `limit=50` | Eventos del historial |

### Recursos

| URI | Contenido |
| --- | --- |
| `radicle://guide/rql` | Guía de RQL con campos, operadores y ejemplos |
| `radicle://projects/{key}/schema` | Mismo contenido que `get_project`, para clientes que prefieren recursos |

### Cómo se conecta un agente

La pantalla de admin muestra esto al crear un agente, con la URL y el token reales:

```bash
claude mcp add --transport http radicle https://radicle.tu-dominio.com/mcp \
  --header "Authorization: Bearer rdc_xxxxxxxx"
```

```json
{
  "mcpServers": {
    "radicle": {
      "type": "http",
      "url": "https://radicle.tu-dominio.com/mcp",
      "headers": { "Authorization": "Bearer rdc_xxxxxxxx" }
    }
  }
}
```

## UI

SPA en React servida por FastAPI. Usa los tokens de color, tipografía e íconos del documento de control. Todo texto pasa por i18n (inglés y español); el idioma y el tema se eligen en el perfil y por default siguen al navegador y al sistema.

### Layout

- **Sidebar:** logo, lista de proyectos, Mis tickets, Admin (solo admins de instancia), perfil abajo.
- **Topbar:** breadcrumb, barra de búsqueda (acepta key directa como `PA-4` o RQL), botón Crear ticket, toggle claro y oscuro.
- Responsive: completo en desktop y tablet; en celular se puede leer y comentar.

### Pantallas

| Pantalla | Ruta | Contenido |
| --- | --- | --- |
| Setup | `/setup` | Solo si no hay usuarios: nombre, handle, email, password del primer admin |
| Login | `/login` | Email y password, errores claros, rate limit visible |
| Proyectos | `/` | Tarjetas con key, nombre, conteo de tickets abiertos; botón Crear proyecto para admins de instancia |
| Board | `/p/{key}/board` | Kanban básico (abajo) |
| Lista | `/p/{key}/list` | Tabla de tickets con barra RQL |
| Ticket | `/t/{key}` | Detalle completo; también abre como panel lateral desde board y lista |
| Milestones | `/p/{key}/milestones` | Lista con fecha objetivo y barra de progreso por categoría |
| Settings | `/p/{key}/settings` | General, miembros, áreas, milestones y workflows (solo lectura) |
| Mis tickets | `/me/tickets` | `assignee = currentUser() AND category != done` de todos los proyectos |
| Admin | `/admin` | Usuarios, agentes y proyectos |
| Perfil | `/me` | Datos, password, idioma, tema y tokens personales |

### Board básico

- Tres columnas: To Do, In Progress y Done (por categoría de estado). Done muestra solo los últimos 14 días, con link a ver todo.
- Tarjeta: key en mono y lima, título, ícono de tipo, prioridad, avatar del assignee (los agentes con ícono de bot), tags, ícono rojo si está bloqueado, progreso del checklist (`2/5`).
- Los Draft se ven distintos: borde punteado e ícono de semilla.
- Drag and drop entre columnas con dnd-kit. Si hay una sola transición válida a esa categoría se ejecuta; si hay varias, aparece un selector; si pide resolution, aparece un selector de resolution. Si no hay transición válida, la columna no acepta la tarjeta.
- Filtros arriba: tipo, área, milestone, assignee, tag. Se reflejan en la URL.
- Orden dentro de la columna por `rank`.

### Lista

- Barra RQL con autocompletado de campos, operadores y valores, y error inline con subrayado en la posición.
- Columnas: key, tipo, título, estado, prioridad, assignee, área, milestone, due, actualizado. Orden al hacer clic en la cabecera (modifica el `ORDER BY`).
- Scroll infinito con el cursor de la API.

### Detalle de ticket

- **Cabecera:** key, título editable en línea, botón de estado que despliega las transiciones disponibles, menú con Cambiar tipo, Copiar link, Borrar.
- **Descripción:** vista renderizada; al hacer clic entra a edición con CodeMirror 6 (markdown, autocompletado de `@handle`), Guardar y Cancelar. El checklist renderizado tiene checkboxes clicables y el avatar del asignado de cada item.
- **Panel lateral de campos:** tipo, estado, resolution, prioridad, área, milestone, assignee, colaboradores, reporter, due date, estimación, tags, padre. Cada uno editable en línea.
- **Subtickets:** lista con estado y botón Crear subticket (hereda área y milestone).
- **Links:** agrupados por etiqueta (blocks, is blocked by, relates to, duplicates, is duplicated by, clones, is cloned by), con buscador de tickets para agregar.
- **Pestañas:** Comentarios (orden cronológico, editor markdown, reacciones, editar y borrar propios) e Historial (eventos con actor, ícono de bot si es agente, valor anterior y nuevo, diff en descripción).
- **Conflicto de versión:** si el guardado regresa 409, aviso "Alguien más cambió este ticket" con opción de recargar sin perder lo escrito.

### Crear ticket

Modal con tipo, título, área (obligatoria salvo Draft), prioridad, descripción y una sección "Más campos" plegada. Opción "Crear otro" para capturar varios seguidos.

### Admin

- **Usuarios:** tabla, crear con password temporal, desactivar, hacer admin.
- **Agentes:** crear con nombre y handle; al crearlo se muestra el token una sola vez con botón copiar y los snippets de conexión MCP ya llenos. Lista de tokens con prefijo, último uso y botón revocar.
- **Proyectos:** crear con key y nombre, archivar.

### Estados vacíos

Cada lista vacía tiene una ilustración de planta en línea delgada, un título que invita ("Siembra tu primer ticket") y un botón con verbo.

## Tests

Los tests de integración corren contra Postgres real con testcontainers; nada de SQLite. Cada test usa una transacción que se revierte al final.

### Unitarios (`backend/tests/unit`)

| Área | Casos mínimos |
| --- | --- |
| Parser RQL | Al menos 60 casos: cada campo con cada operador, precedencia AND y OR, NOT, paréntesis, `#tag`, fechas absolutas y relativas, funciones, ORDER BY múltiple, comillas, palabras clave en minúsculas |
| Errores RQL | Campo desconocido con sugerencia, operador inválido para el campo, paréntesis sin cerrar, query vacía, query de más de 2,000 caracteres; todos con `position` correcta |
| Compilador RQL | SQL generado para casos clave; `!=` incluye nulos; `priority` ordinal; filtro de permisos siempre presente |
| Checklist | `-` y `*`, `x` y `X`, sangría, items dentro de bloques de código ignorados, último `@handle` como assignee, handle desconocido, reescritura de una sola línea sin tocar las demás |
| Menciones | Fuera de código sí, dentro no; emails no cuentan como mención |
| Motor de workflow | Transición válida e inválida, `from` nulo, resolution obligatoria, `allowed_resolutions`, auto-resolution cuando hay una sola, limpiar al reabrir, aviso de bloqueado |
| Validaciones | Key de proyecto, handle, tags, título, estimación, ciclos de padre |
| Rank | Generar entre dos valores, al inicio, al final, 1,000 inserciones seguidas sin colisión |
| Tokens | Formato, hash, verificación, revocado, expirado |

### Integración (`backend/tests/integration`)

- Cada endpoint: caso feliz, error de validación y permisos.
- **Matriz de permisos parametrizada:** cada acción de la tabla de permisos contra viewer, member, admin, admin de instancia, no miembro y agente. No miembro siempre 404.
- **Concurrencia:** 50 creaciones de ticket en paralelo en el mismo proyecto generan números 1 a 50 sin duplicados ni huecos.
- **Versionado:** dos PATCH con la misma versión; el segundo regresa 409 con el ticket actual.
- **Historial:** cada mutación genera el evento esperado con valores correctos; `UPDATE` y `DELETE` directos sobre `ticket_events` fallan por el trigger.
- **Soft delete:** el ticket borrado no sale en búsqueda, board, links ni hijos; restaurar lo regresa.
- **Setup:** `/setup` funciona una sola vez.
- **Sesiones y CSRF:** mutación con cookie sin `X-CSRF-Token` falla; con bearer token no se pide.
- **Agentes:** un agente no puede hacer login con password; su token funciona en API y MCP.
- **Migraciones:** `alembic upgrade head`, `downgrade base` y `upgrade head` otra vez sin errores.

### MCP (`backend/tests/mcp`)

- Cliente del SDK de MCP contra la app en memoria.
- Cada tool: caso feliz y al menos un error con mensaje accionable verificado.
- Flujo completo de agente: `whoami`, `my_tickets`, `get_ticket`, `transition_ticket` a In Progress, `set_checklist_item`, `add_comment`, `link_tickets`, `search_tickets`; al final el historial tiene todos los eventos con el agente como actor.
- Un token de viewer recibe error en `create_ticket`; un token revocado no se conecta.

### Frontend

- **Vitest y React Testing Library:** render y toggle del checklist, barra RQL con error en posición, selector de transiciones y resolutions, conflicto de versión, cambio de idioma y tema.
- **Playwright (`frontend/e2e`):** setup, login, crear proyecto PA con áreas y milestone V1, crear Task, Bug y Draft, mover en el board con drag and drop, comentar con mención, linkear blocks y ver el aviso, buscar con RQL, convertir Draft a Task, crear agente y copiar su token.

### Smoke y rendimiento

- `scripts/smoke.sh`: `docker compose up -d`, espera `/health`, hace setup por API, crea agente, llama `whoami` y `create_ticket` por MCP y verifica la respuesta.
- `scripts/seed.py --tickets 10000`: proyecto con datos realistas para medir. Búsqueda RQL p95 menor a 300 ms; board con 500 tickets abiertos carga en menos de 1 s.

## Criterios de aceptación de la etapa

La etapa 1 se acepta cuando tú, a mano, puedes palomear todo esto:

- [ ] En una máquina limpia, `docker compose up` levanta Radicle en menos de 2 minutos y abre la pantalla de setup.
- [ ] Creo el admin, un usuario humano y un agente; el token del agente se muestra una sola vez y funciona.
- [ ] Creo ProyectoA con key PA, áreas Legal, Marketing, Backend y Frontend, y milestone V1 con fecha.
- [ ] Creo un Task, un Bug y un Draft con todos los campos fijos; las keys salen PA-1, PA-2, PA-3.
- [ ] Escribo un checklist con @handles en la descripción; se ve con checkboxes y avatares, y lo marco desde la UI.
- [ ] Un Task no puede ir de To Do a Done salvo con Close y resolution Won't Do o Duplicate; Complete pide resolution; Reopen la limpia.
- [ ] Cambio un Draft a Task eligiendo área y queda en To Do con el cambio en el historial.
- [ ] Ligo PA-5 como bloqueado por PA-4; aparece en ambos con su etiqueta, y mover PA-5 a In Progress muestra el aviso.
- [ ] Comento con markdown y @mención, reacciono, edito y borro mi comentario.
- [ ] El historial muestra cada cambio con actor, valor anterior y nuevo, y no hay forma de editarlo.
- [ ] Los ejemplos de RQL del spec funcionan en la lista; un error muestra dónde está.
- [ ] Muevo tickets en el board con drag and drop y respeta las transiciones.
- [ ] Un viewer no puede editar nada y un no miembro no ve el proyecto, ni en UI, ni en API, ni en MCP.
- [ ] Conecto Claude Code con el token del agente y le pido: "busca mis tickets, toma PA-4, ponlo en progreso, marca el primer item del checklist, comenta tu avance y liga PA-4 como bloqueante de PA-5". Todo se ve en la UI y en el historial como hecho por el agente.
- [ ] Modo claro y oscuro con la paleta lima; UI en inglés y en español.
- [ ] CI verde: lint, tipos, tests, cobertura mínima, migraciones y build de imagen.
- [ ] `docs/progress.md` y README explican cómo instalar, crear un agente y conectarlo.

## Fuera de alcance

No se construye en esta etapa aunque parezca fácil:

| Feature | Etapa |
| --- | --- |
| Campos custom, templates, editor de workflows, reglas de transición, screens | 2 |
| Adjuntos, votos, tiempo real invertido | 2 |
| Clonar, mover entre proyectos, bulk edit, filtros guardados, ranking manual, atajos y cmd+k | 2 |
| Columnas por estado, WIP limits, swimlanes, quick filters, Scrum, timeline, reportes, dashboards | 3 |
| Buzón y formulario público, grupos, permisos configurables, tickets restringidos, SSO, audit log | 4 |
| Notificaciones de cualquier tipo, watchers, suscripciones, automatización, webhooks | 5 |
| Git, chat, docs, plugins, import/export, app móvil, IA | 5 |

Si algo de esta lista hace falta para cumplir un criterio de la etapa 1, se documenta en `docs/decisions/` y se discute antes de hacerlo.
