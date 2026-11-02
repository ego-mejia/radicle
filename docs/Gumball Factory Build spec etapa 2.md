# Radicle: Build spec etapa 2 (Configuración y trabajo diario)

Oct 18, 2026 · @Fernando

La etapa 2 hace que cada proyecto se adapte a su forma de trabajar y que el trabajo diario sea rápido, para personas y agentes. Parte de la etapa 1 aceptada y no rompe nada de la API v1.

## Objetivo y entregables

Al terminar la etapa 2, un admin arma un template con sus estados, reglas y campos, crea proyectos a partir de él, y los cambios al template llegan solos a los proyectos ligados. El trabajo diario se hace con teclado, con adjuntos, tiempo registrado y edición masiva.

Esta etapa introduce el servicio `worker` en docker compose (misma imagen, comando `radicle worker`) con Procrastinate para jobs en segundo plano.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 2.1 | Worker y campos custom | Procrastinate y servicio `worker`; definición de campos por proyecto, 7 tipos, validación, valores en tickets, RQL `cf.<key>` | Un campo select "environment" en Bugs se llena, se filtra con `cf.environment = prod` y se valida el valor |
| 2.2 | Templates y editor de workflows | Templates, crear proyecto desde template, guardar proyecto como template, modo ligado o independiente, propagación con mapeo de estados, editor de estados y transiciones | Agregar un estado al template aparece en todos los proyectos ligados y en ninguno independiente; borrar un estado exige mapeo y mueve los tickets |
| 2.3 | Reglas de transición | Conditions, validators y post-functions del catálogo, política de bloqueo avisar o impedir | Con `checklist_complete` en Complete, un ticket con items abiertos no pasa y el error dice cuáles faltan |
| 2.4 | Screens | Campos visibles y obligatorios por tipo y operación, endpoint de esquema | Crear un Bug sin un campo obligatorio de su screen falla en UI, API y MCP con el mismo mensaje |
| 2.5 | Adjuntos | Storage local o S3, subida, pegar y arrastrar, preview, variantes, reducción de imágenes, límite de tamaño | Pego un screenshot en un comentario, se ve en preview, lo reduzco a mediano y baja su tamaño en disco |
| 2.6 | Votos y tiempo real invertido | Votos 🙋, worklogs, estimado original, restante automático o manual | Un agente registra 2 h por MCP y el restante baja; el backlog se ordena por votos |
| 2.7 | Clonar, mover y bulk edit | Clon con opciones, mover con mapeos y alias de key, bulk por keys o RQL con dry run | Muevo PA-7 a PB y `GET /tickets/PA-7` regresa PB-15; un bulk de 120 tickets corre como job y reporta por ticket |
| 2.8 | Filtros, ranking, atajos y cmd+k | Filtros guardados y compartidos, ranking manual con drag, `next_ticket` para agentes, atajos de teclado y paleta de comandos | Un agente llama `next_ticket` con `claim=true` y recibe el de más arriba ya asignado y en progreso; todo el flujo diario se hace sin mouse |

## Modelo de datos

Solo lo nuevo o lo que cambia respecto a la etapa 1.

```
custom_field_definitions
  id, project_id
  key                text                    -- ^[a-z][a-z0-9_]{1,39}$, unique(project_id, key)
  name               text
  field_type         enum(text, number, date, select, checkbox, user, url)
  options            jsonb                   -- select: [{"value": "prod", "label": "Prod", "color": "#..."}]
  applies_to_types   enum[]                  -- task, bug, draft
  applies_to_area_ids uuid[] null            -- null = todas las áreas
  template_ref       text null               -- slug estable si viene de template
  position, archived_at null, created_at

tickets (columnas nuevas)
  custom_fields      jsonb default '{}'      -- { "environment": "prod", "requires_signature": true }
  original_estimate_hours numeric(7,2) null  -- se fija la primera vez que hay estimación
  remaining_hours    numeric(7,2) null
  remaining_mode     enum(auto, manual) default auto
  time_spent_minutes int default 0           -- suma de worklogs, desnormalizado
  vote_count         int default 0
  -- índice GIN(custom_fields jsonb_path_ops)

templates
  id, name, description_md
  config             jsonb                   -- ver esquema en la sección de templates
  version            int default 1
  created_by, created_at, updated_at, archived_at null

projects (columnas nuevas)
  template_id        null
  template_mode      enum(linked, detached) null
  template_version   int null                -- última versión aplicada
  blocked_policy     enum(warn, enforce) default warn

statuses, transitions (columna nueva)
  template_ref       text null               -- slug estable para mapear template y proyecto

transition_rules
  id, transition_id
  kind               enum(condition, validator, post_function)
  rule_type          text                    -- ver catálogo
  config             jsonb
  position           int

screens
  id, project_id, ticket_type
  operation          enum(create, edit, transition)
  transition_id      null                    -- solo si operation = transition
  fields             jsonb                   -- [{"field": "area", "required": true}, {"field": "cf.environment", "required": false}]

template_sync_runs
  id, template_id, template_version, project_id
  status             enum(pending, running, succeeded, failed)
  error              text null
  started_at, finished_at

attachments
  id, ticket_id, comment_id null, uploader_id
  filename, mime_type, size_bytes, sha256
  storage_key        text                    -- ruta en disco o key en S3
  width, height      int null                -- imágenes
  variants           jsonb                   -- { "thumb": {...}, "preview": {...} }
  created_at, deleted_at null

ticket_votes
  ticket_id, user_id, created_at             -- pk compuesta

worklogs
  id, ticket_id, user_id
  started_at         timestamptz
  minutes            int                     -- 1 a 1440
  description        text null
  created_at, updated_at, deleted_at null

ticket_key_aliases
  old_key            citext pk               -- ej. PA-7 después de moverlo
  ticket_id

saved_filters
  id, owner_id, name, rql
  visibility         enum(private, project, instance)
  project_id         null                    -- obligatorio si visibility = project
  created_at, updated_at

user_preferences
  user_id pk, prefs jsonb                    -- tema, idioma, atajos activos, densidad

jobs                                         -- tabla propia para mostrar progreso en UI
  id, kind, status, progress int, total int, result jsonb, error, created_by, created_at, finished_at
```

Nuevos eventos de historial: `custom_field_changed`, `attachment_added`, `attachment_removed`, `attachment_resized`, `vote_added`, `vote_removed`, `worklog_added`, `worklog_updated`, `worklog_deleted`, `cloned_from`, `moved`, `rank_changed`, `status_remapped` (cuando un template borra un estado).

## Templates, editor de workflows y propagación

### Esquema de `templates.config`

```json
{
  "areas": [{ "name": "Legal", "color": "#C4572E" }],
  "tags": ["backlog"],
  "custom_fields": [{ "ref": "environment", "key": "environment", "name": "Environment", "field_type": "select", "options": [...], "applies_to_types": ["bug"] }],
  "workflows": {
    "task": {
      "statuses": [{ "ref": "todo", "name": "To Do", "category": "todo", "is_initial": true }],
      "transitions": [{ "ref": "start", "name": "Start", "from": "todo", "to": "in_progress", "allowed_resolutions": null, "rules": [] }]
    },
    "bug": { ... },
    "draft": { ... }
  },
  "screens": [{ "type": "bug", "operation": "create", "fields": [{ "field": "area", "required": true }] }],
  "settings": { "blocked_policy": "warn" }
}
```

El `ref` es un slug estable. Renombrar un estado cambia `name` pero no `ref`, así la propagación sabe que es el mismo.

### Operaciones

- **Template default:** al migrar a la etapa 2 se crea el template "Radicle default" con los workflows de la etapa 1, y los proyectos existentes quedan ligados a él.
- **Crear proyecto desde template:** copia toda la configuración y queda `linked` por default.
- **Guardar proyecto como template:** crea un template nuevo con la configuración actual del proyecto. No copia tickets, milestones ni miembros.
- **Desligar:** el proyecto pasa a `detached`; conserva su configuración y desde ahí la edita libremente. Volver a ligar queda fuera de esta etapa.

### Qué controla el template en un proyecto ligado

| Parte | Proyecto ligado | Proyecto independiente |
| --- | --- | --- |
| Workflows, reglas y screens | Solo los cambia el template | Los edita el admin del proyecto |
| Campos custom | Solo los cambia el template | Los edita el admin del proyecto |
| Áreas y tags | El template agrega; el proyecto puede tener extras propios | Libres |
| Política de bloqueo | Del template | Del proyecto |

Intentar editar workflows o campos de un proyecto ligado regresa 409 con el nombre del template.

### Propagación

1. Editar un template incrementa `version` y crea un `template_sync_run` por cada proyecto ligado.
2. El worker aplica el diff por `ref`: agrega, renombra o reordena estados, transiciones, reglas, campos y screens; agrega áreas y tags nuevos.
3. **Quitar un estado** exige `status_mappings` en la petición (`{"old_ref": "new_ref"}`). Los tickets en ese estado se mueven al nuevo con evento `status_remapped` y actor `system`. Sin mapeo la edición se rechaza con 422.
4. **Quitar un campo custom** lo archiva; los valores se conservan y dejan de mostrarse.
5. Cada proyecto se actualiza en su propia transacción. Si uno falla, se marca `failed` con el error, los demás siguen, y el admin puede reintentar.
6. La UI del template muestra el progreso de la propagación.

### Editor de workflows

Vive en Settings del template y en Settings de proyectos independientes, una pestaña por tipo de ticket.

- **Estados:** agregar, renombrar, reordenar con drag, cambiar categoría, marcar inicial.
- **Transiciones:** matriz desde por hacia con toggles; al activar una celda se nombra la transición y se eligen resolutions permitidas si va a Done.
- **Reglas:** panel por transición para agregar conditions, validators y post-functions del catálogo.
- **Vista previa:** diagrama de estados generado automáticamente (Mermaid renderizado en cliente).
- **Validaciones al guardar:** exactamente un estado inicial, al menos un estado en Done, todo estado alcanzable desde el inicial (aviso, no error), y mapeo obligatorio para estados borrados con tickets.

## Reglas de transición y screens

### Orden de ejecución de una transición

1. Conditions: si alguna falla, la transición ni siquiera aparece en `GET /transitions` (con `?include_unavailable=true` aparece con el motivo).
2. Screen de la transición: campos obligatorios presentes.
3. Validators: si alguno falla, 409 con `failed_rules: [{"rule", "message"}]`.
4. Cambio de estado y resolution.
5. Post-functions, en orden, dentro de la misma transacción. Sus cambios generan eventos con el mismo actor.

### Catálogo de reglas

| Tipo | `rule_type` | Config | Efecto |
| --- | --- | --- | --- |
| Condition | `only_assignee` |  | Solo el assignee puede ejecutarla |
| Condition | `only_reporter` |  | Solo el reporter |
| Condition | `only_roles` | `roles: ["admin"]` | Solo esos roles del proyecto |
| Condition | `only_user_kind` | `kind: human` o `agent` | Ej. solo humanos aprueban |
| Condition | `not_blocked` |  | Usa la política de bloqueo: `warn` deja pasar con aviso, `enforce` la bloquea |
| Validator | `checklist_complete` |  | Todos los items del checklist marcados; el error lista los pendientes |
| Validator | `field_required` | `field` | El campo (fijo o `cf.<key>`) tiene valor |
| Validator | `has_estimate` |  | Tiene estimación |
| Validator | `children_done` |  | Todos los subtickets en categoría Done |
| Validator | `has_worklog` |  | Al menos un worklog |
| Validator | `comment_required` |  | La petición incluye `comment`; se guarda como comentario |
| Post-function | `assign_to_actor` |  | Asigna a quien hizo la transición |
| Post-function | `unassign` |  | Quita el assignee |
| Post-function | `set_field` | `field`, `value` | Fija un campo fijo o custom |
| Post-function | `clear_field` | `field` | Limpia un campo |
| Post-function | `add_tag`, `remove_tag` | `tag` |  |
| Post-function | `add_comment` | `template` | Comenta con variables `{actor}`, `{from}`, `{to}` |

La política de bloqueo (`blocked_policy`) aplica también sin regla explícita: con `enforce`, cualquier transición a categoría in\_progress o done de un ticket bloqueado falla con 409, salvo para admins con `force=true` (queda en historial).

### Screens

- Definen qué campos se piden por tipo de ticket y operación: `create`, `edit` y cada transición.
- Si no hay screen definida para una operación, aplican los defaults de la etapa 1 (área obligatoria en Task y Bug; resolution al entrar a Done).
- En `edit`, un campo que no está en la screen es de solo lectura (salvo para post-functions y admins).
- Las validaciones se aplican en el servicio, así valen igual para UI, API y MCP.
- `GET /projects/{key}/schema?type=bug&operation=create` regresa los campos con tipo, si son obligatorios y sus opciones. La UI arma los formularios con esto y el MCP lo expone como `get_ticket_schema`.

Ejemplo de respuesta del esquema:

```json
{
  "type": "bug",
  "operation": "create",
  "fields": [
    { "field": "title", "kind": "text", "required": true },
    { "field": "area", "kind": "area", "required": true, "options": ["Legal", "Marketing", "Backend", "Frontend"] },
    { "field": "cf.environment", "kind": "select", "required": true, "options": ["prod", "staging", "dev"] },
    { "field": "priority", "kind": "enum", "required": false, "options": ["highest", "high", "medium", "low", "lowest"] }
  ]
}
```

## Campos custom, adjuntos, votos y tiempo real invertido

### Campos custom

| Tipo | Valor guardado | Validación | RQL |
| --- | --- | --- | --- |
| text | string, máx 2,000 |  | `~`, `=`, `IS EMPTY` |
| number | número | finito | `=`, `>`, `<`, `>=`, `<=` |
| date | `YYYY-MM-DD` | fecha válida | como `due` |
| select | `value` de una opción | debe existir en `options` | `=`, `!=`, `IN` |
| checkbox | booleano |  | `= true` |
| user | `user_id` (se expone como handle) | miembro del proyecto | `=`, `currentUser()` |
| url | string | http o https | `~` |

- Solo se aceptan campos que aplican al tipo y área del ticket; un campo que no aplica regresa 422.
- Cambiar las opciones de un select no borra valores viejos; quedan marcados como "opción eliminada" en la UI.
- En RQL se usan como `cf.<key>`, ej. `cf.environment = prod AND cf.requires_signature = true`.

### Adjuntos

**Storage.** `RADICLE_STORAGE=local` guarda en `/data/attachments` (volumen de docker compose). `RADICLE_STORAGE=s3` usa cualquier S3 compatible (AWS, MinIO, R2) con `RADICLE_S3_*`. Ambos implementan la misma interfaz `StorageBackend`.

**Subida.**

- `POST /tickets/{key}/attachments` multipart, opcional `comment_id` y `resize`.
- Límite por archivo `RADICLE_MAX_UPLOAD_MB` (default 25); más grande regresa 413.
- El tipo se detecta por contenido, no por extensión.
- En el editor de descripción y comentarios se puede pegar (ctrl+v) o arrastrar; se inserta `![nombre](attachment:<id>)` y se renderiza con URL firmada.

**Imágenes (png, jpg, webp, gif estático).**

- Se borra EXIF (privacidad) y se corrige la orientación.
- El worker genera variantes webp: `thumb` (320 px) y `preview` (1280 px).
- **Reducir tamaño:** al subir se elige `resize` entre `original`, `large` (2048 px), `medium` (1280 px) y `small` (800 px), lado mayor, calidad 82. El default lo define `RADICLE_IMAGE_DEFAULT_RESIZE` (default `large`).
- Una imagen ya subida se puede reducir después con `POST /attachments/{id}/resize`; reemplaza el archivo, actualiza tamaño y genera evento `attachment_resized`. No se puede agrandar.

**Descarga.** `GET /attachments/{id}/content?variant=thumb|preview|original` con auth; en S3 redirige a URL firmada de 5 minutos. Imágenes se sirven inline; todo lo demás con `Content-Disposition: attachment`.

### Votos 🙋

- Un voto por usuario por ticket. `PUT` y `DELETE /tickets/{key}/vote`.
- `vote_count` se actualiza en la misma transacción.
- Votar no suscribe ni notifica.
- RQL: `votes >= 5` y `ORDER BY votes DESC`.
- La UI muestra el ícono de persona levantando la mano con el conteo; al pasar el cursor se ve quién votó.
- Los agentes no votan: el MCP no tiene tool de voto, pero `get_ticket` regresa `vote_count`.

### Tiempo real invertido

- **Estimado original:** la primera vez que un ticket recibe `estimate_hours`, se copia a `original_estimate_hours` y ya no cambia.
- **Worklogs:** cada quien registra minutos, fecha de inicio y descripción. Editar o borrar solo el propio (admin cualquiera).
- **Restante:** en modo `auto` es `max(estimate_hours - spent_hours, 0)`; si alguien lo edita a mano pasa a `manual` hasta que se elija volver a `auto`.
- **RQL:** `spent > 4`, `remaining = 0`, `original_estimate > 8`.
- **UI:** barra estimado contra real en el ticket; se pone en `warning` cuando lo invertido supera el estimado original.
- Al hacer una transición se puede registrar tiempo en el mismo diálogo (campo opcional `log_minutes`).

## Clonar, mover, bulk edit, filtros, ranking y atajos

### Clonar

- `POST /tickets/{key}/clone` con `target_project?` (default el mismo), `area_mapping?` y `include`: `description`, `checklist_state` (si no, el checklist se copia desmarcado), `tags`, `custom_fields`, `collaborators`, `attachments`, `children`.
- El clon empieza en el estado inicial, sin assignee, con el usuario actual como reporter y título sin cambios.
- Se crea el link `clones` del clon al original y evento `cloned_from`.
- Con `children`, clona el árbol completo manteniendo la jerarquía.

### Mover entre proyectos

- `POST /tickets/{key}/move` con `target_project`, `area_mapping` (obligatorio para Task y Bug si el área no existe en destino), `milestone?`, `status_mapping?` y `include_children` (default true).
- Recibe número nuevo en el destino; la key vieja se guarda en `ticket_key_aliases`.
- Cualquier `GET` con la key vieja regresa el ticket con su key nueva y `moved_from`. En la UI la URL vieja redirige.
- Estados: si hay mapeo se usa; si no, se busca por nombre; si no existe, va al estado inicial.
- Campos custom con la misma `key` en destino se conservan; los demás se descartan con evento.
- Links, comentarios, adjuntos, worklogs y el historial completo se conservan.
- Permiso: admin en el origen y member en el destino.

### Bulk edit

- `POST /tickets/bulk` con `keys` o `query` (RQL) y `operations`:

```json
{
  "query": "project = PA AND #backlog AND area = Backend",
  "operations": [
    { "op": "set_field", "field": "milestone", "value": "V1" },
    { "op": "remove_tag", "tag": "backlog" },
    { "op": "transition", "to_status": "In Progress" }
  ],
  "dry_run": true
}
```

- Operaciones: `set_field`, `clear_field`, `add_tag`, `remove_tag`, `transition`, `assign`, `add_collaborator`.
- `dry_run` regresa cuántos tickets aplican y cuáles fallarían y por qué, sin cambiar nada.
- Máximo 500 tickets. Hasta 100 se ejecuta en línea; más de 100 se vuelve job con progreso en `GET /jobs/{id}`.
- Cada ticket se procesa en su propia transacción con las mismas reglas y screens que una edición normal. El resultado lista éxito o error por ticket.

### Filtros guardados

- CRUD en `/filters`. Visibilidad privada, de proyecto o de toda la instancia.
- Solo el dueño edita; los visibles para otros se pueden duplicar.
- En la lista aparecen en una barra lateral. En RQL se referencian con `filter = "Bugs abiertos de V1"`.

### Ranking manual

- Cada ticket tiene `rank` (fractional indexing) por proyecto.
- `POST /tickets/{key}/rank` con `before` o `after` (otra key). Evento `rank_changed`.
- En lista ordenada por rank y en el board se reordena con drag.
- Si dos keys colisionan o el rank se vuelve muy largo, un job rebalancea el proyecto.

### `next_ticket` para agentes

Regresa el ticket de mayor rank que cumple: categoría todo, no bloqueado, sin assignee o asignado al que pregunta, filtrable por `project`, `area` y `type`. Con `claim=true` lo asigna al que pregunta y ejecuta la primera transición hacia in\_progress, todo atómico con `SELECT ... FOR UPDATE SKIP LOCKED` para que dos agentes nunca tomen el mismo.

### Atajos de teclado

| Atajo | Acción |
| --- | --- |
| `c` | Crear ticket |
| `/` | Enfocar búsqueda |
| `cmd+k` o `ctrl+k` | Paleta de comandos |
| `?` | Ayuda de atajos |
| `g` luego `p` | Ir a proyectos |
| `g` luego `m` | Ir a mis tickets |
| `j`, `k` | Siguiente y anterior en lista o board |
| `enter` | Abrir ticket seleccionado |
| `e` | Editar título |
| `a` | Asignarme |
| `m` | Mover (abre transiciones) |
| `l` | Tags |
| `p` | Prioridad |
| `esc` | Cerrar panel o diálogo |

No se disparan dentro de inputs. Se pueden apagar en preferencias.

### Paleta de comandos

Un input que busca a la vez: tickets (key exacta o título con trigramas), proyectos, filtros guardados y acciones (crear ticket, cambiar tema, cambiar idioma, ir a settings). Muestra recientes cuando está vacía y se navega con flechas.

## API REST y MCP

### Endpoints nuevos

| Método | Ruta | Qué hace | Permiso |
| --- | --- | --- | --- |
| GET, POST | `/projects/{key}/fields` | Campos custom | viewer, admin |
| PATCH, DELETE | `/projects/{key}/fields/{field_key}` | Editar, archivar | admin |
| GET, POST | `/templates` | Listar, crear | autenticado, admin de instancia |
| GET, PATCH | `/templates/{id}` | Ver, editar (incluye `status_mappings`) | autenticado, admin de instancia |
| POST | `/templates/{id}/archive` | Archivar | admin de instancia |
| GET | `/templates/{id}/sync-runs` | Progreso de la propagación | admin de instancia |
| POST | `/templates/{id}/sync-runs/{run}/retry` | Reintentar un proyecto | admin de instancia |
| POST | `/projects` | Ahora acepta `template_id` | admin de instancia |
| POST | `/projects/{key}/save-as-template` | Crear template desde el proyecto | admin |
| POST | `/projects/{key}/detach` | Desligar del template | admin |
| PUT | `/projects/{key}/workflows/{type}` | Reemplazar workflow (solo independientes) | admin |
| PUT | `/projects/{key}/settings` | `blocked_policy` (solo independientes) | admin |
| GET, PUT | `/projects/{key}/screens` | Screens | viewer, admin |
| GET | `/projects/{key}/schema?type&operation&transition` | Campos para un formulario | viewer |
| GET, POST | `/tickets/{key}/attachments` | Listar, subir | viewer, member |
| GET | `/attachments/{id}/content?variant` | Descargar | viewer |
| POST | `/attachments/{id}/resize` | `{ "preset": "medium" }` | member |
| DELETE | `/attachments/{id}` | Borrar (propio o admin) | member |
| PUT, DELETE | `/tickets/{key}/vote` | Votar, quitar voto | member |
| GET | `/tickets/{key}/voters` | Quién votó | viewer |
| GET, POST | `/tickets/{key}/worklogs` | Listar, registrar | viewer, member |
| PATCH, DELETE | `/worklogs/{id}` | Editar, borrar | autor o admin |
| POST | `/tickets/{key}/clone` | Clonar | member |
| POST | `/tickets/{key}/move` | Mover | admin origen, member destino |
| POST | `/tickets/bulk` | Edición masiva | member |
| GET | `/jobs/{id}` | Estado de un job | creador |
| POST | `/tickets/{key}/rank` | Reordenar | member |
| POST | `/tickets/next` | `next_ticket` con `claim` | member |
| GET, POST | `/filters` | Filtros visibles, crear | autenticado |
| PATCH, DELETE | `/filters/{id}` | Editar, borrar | dueño |
| GET, PATCH | `/me/preferences` | Preferencias | humano |

`GET /tickets/{key}` agrega `custom_fields`, `attachments` (resumen), `vote_count`, `voted_by_me`, `original_estimate_hours`, `remaining_hours` y `spent_hours`.

### Tools nuevas del MCP

| Tool | Parámetros | Qué hace |
| --- | --- | --- |
| `get_ticket_schema` | `project`, `type`, `operation`, `transition?` | Campos obligatorios y opciones antes de crear, editar o mover |
| `next_ticket` | `project?`, `area?`, `type?`, `claim=false` | El siguiente ticket listo para trabajar |
| `log_work` | `key`, `minutes`, `description?`, `started_at?` | Registra tiempo invertido |
| `list_worklogs` | `key` | Tiempo registrado |
| `upload_attachment` | `key`, `filename`, `content_base64`, `resize?`, `comment_id?` | Máximo 10 MB por esta vía |
| `list_attachments` | `key` | Nombre, tipo, tamaño, URL |
| `read_attachment` | `id` | Contenido de archivos de texto (md, txt, json, csv, logs) hasta 200 KB |
| `clone_ticket` | `key`, `target_project?`, `include?` |  |
| `move_ticket` | `key`, `target_project`, `area_mapping?`, `status_mapping?` |  |
| `bulk_update` | `keys?` o `query?`, `operations`, `dry_run=true` | Default en dry run para que el agente confirme |
| `rank_ticket` | `key`, `before?` o `after?` |  |
| `list_filters`, `run_filter` | `name` | Usar filtros guardados |
| `save_filter` | `name`, `query`, `visibility=private` |  |

`create_ticket` y `update_ticket` aceptan `custom_fields` como objeto. `transition_ticket` acepta `comment` y `log_minutes`. `get_project` agrega campos custom, template y modo, política de bloqueo y un resumen de reglas por transición. Los errores de validators incluyen la lista de reglas que fallaron.

## UI

| Pantalla o cambio | Detalle |
| --- | --- |
| Admin, Templates | Lista de templates con proyectos ligados y versión; crear, editar, archivar; progreso de propagación con estado por proyecto y botón reintentar |
| Editor de template | Pestañas: Workflows (un sub-tab por tipo), Campos custom, Screens, Áreas y tags, Settings. Al guardar con estados borrados, diálogo de mapeo obligatorio |
| Crear proyecto | Selector de template con vista previa de estados y campos |
| Settings del proyecto | Banner "Ligado a \<template> v3" con botón Desligar (confirmación). Si está ligado, workflows, campos y screens en solo lectura con link al template |
| Formularios | Crear, editar y transicionar se arman con `/schema`; los obligatorios marcados y validados antes de enviar |
| Diálogo de transición | Campos de la screen, resolution, comentario y "Registrar tiempo". Si un validator falla, muestra la lista exacta (ej. items del checklist pendientes) |
| Detalle de ticket | Sección de campos custom en el panel lateral; sección Adjuntos con grid de thumbnails, visor de imágenes, menú Reducir tamaño; botón 🙋 con conteo; barra de tiempo y botón Registrar tiempo; pestaña Tiempo con worklogs |
| Editores markdown | Pegar o arrastrar archivos con barra de progreso; al pegar una imagen, selector de tamaño con el default preseleccionado |
| Lista | Checkbox por fila y barra de acciones masivas (Editar campo, Tags, Mover estado, Asignar) con vista previa del dry run y progreso si es job |
| Lista, sidebar | Filtros guardados: míos, del proyecto, de la instancia; Guardar filtro actual |
| Lista y board | Drag para ranking cuando el orden es por rank |
| Menú del ticket | Clonar (diálogo con opciones), Mover (diálogo con mapeo de áreas y estados) |
| Global | Paleta `cmd+k`, overlay de ayuda `?`, foco visible en navegación con `j` y `k` |
| Perfil | Preferencias: atajos activos, densidad, tema, idioma |

## Tests

| Área | Casos mínimos |
| --- | --- |
| Campos custom | Validación por cada tipo; campo que no aplica al tipo o área; opción de select eliminada; RQL `cf.*` con cada operador |
| Templates | Diff por `ref`: agregar, renombrar, reordenar y quitar estados, transiciones, reglas, campos y screens; quitar estado sin mapeo da 422; con mapeo mueve tickets con evento `status_remapped` |
| Propagación | 3 proyectos ligados y 1 independiente: solo los ligados cambian; un proyecto que falla no afecta a los demás y se puede reintentar; correr el mismo sync dos veces no duplica nada |
| Reglas | Cada regla del catálogo con caso que pasa y que falla; orden de ejecución; post-functions dentro de la misma transacción (si una falla, nada se guarda); `blocked_policy` warn y enforce; `force` de admin queda en historial |
| Screens | Obligatorios en create, edit y transición aplican igual en API y MCP; campos fuera de la screen de edit son solo lectura |
| Adjuntos | Storage local y S3 (MinIO con testcontainers); límite 413; detección de tipo por contenido; EXIF borrado; tamaños exactos de cada preset; resize posterior reduce bytes y no agranda; variantes generadas por el worker; URL firmada expira |
| Votos | Un voto por usuario; `vote_count` consistente con concurrencia; RQL `votes` |
| Tiempo | Estimado original se fija una sola vez; restante auto y manual; worklogs de otro usuario no se editan; RQL `spent` y `remaining` |
| Clonar y mover | Cada opción de `include`; árbol de hijos; alias de key resuelve en API, MCP y UI; mapeos de estado y área; campos custom que no existen en destino |
| Bulk | Dry run no cambia nada; errores parciales reportados por ticket; más de 100 tickets corre como job con progreso; más de 500 da 422 |
| Ranking y `next_ticket` | Reordenar antes y después; rebalanceo; 10 agentes llamando `next_ticket` con `claim=true` al mismo tiempo nunca reciben el mismo ticket |
| MCP | Cada tool nueva con caso feliz y error; `bulk_update` sin `dry_run=false` nunca modifica |
| Frontend | Formularios generados desde schema; diálogo de mapeo; pegar imagen; barra de acciones masivas; atajos no se disparan en inputs; paleta de comandos |
| E2E | Crear template desde PA, crear PB desde él, agregar estado al template y verlo en PB; desligar PC y comprobar que no cambia; regla checklist bloquea Complete; pegar y reducir imagen; registrar tiempo; clonar, mover y bulk; filtro guardado; reordenar con drag; flujo diario completo solo con teclado |

## Criterios de aceptación de la etapa

- [ ] Creo un template "Producto digital" desde ProyectoA y creo ProyectoB a partir de él.
- [ ] Agrego el estado "Blocked" al template y aparece en ProyectoB en segundos, sin tocar ProyectoC que está desligado.
- [ ] Quito un estado del template, el sistema me pide a dónde mandar sus tickets y los mueve con historial.
- [ ] Configuro `checklist_complete` en Complete y un ticket con items abiertos no pasa; el error dice cuáles faltan.
- [ ] Cambio la política de bloqueo a enforce y un ticket bloqueado ya no se puede mover a In Progress.
- [ ] Un Bug exige el campo custom Environment al crearse, en UI, API y MCP.
- [ ] Pego un screenshot en un comentario, lo reduzco a mediano y su tamaño baja.
- [ ] Voto con 🙋 y ordeno el backlog por votos.
- [ ] Un agente registra 2 h por MCP y la barra de tiempo del ticket se actualiza.
- [ ] Muevo PA-7 a ProyectoB y el link viejo sigue funcionando.
- [ ] Le quito #backlog y pongo milestone V1 a 120 tickets con bulk edit, con vista previa antes.
- [ ] Un agente llama `next_ticket` con `claim=true` y queda asignado y en progreso el de más arriba.
- [ ] Hago el flujo diario (abrir, asignarme, mover, comentar) solo con teclado y `cmd+k`.
- [ ] Todas las reglas generales del documento de control se cumplen.

## Fuera de alcance

Boards configurables, Scrum, timeline, reportes y dashboards (etapa 3). Buzón, grupos, permisos configurables, tickets restringidos, SSO y audit log (etapa 4). Notificaciones, automatización, webhooks, integraciones, plugins, import/export, móvil e IA (etapa 5). Volver a ligar un proyecto desligado tampoco entra.
