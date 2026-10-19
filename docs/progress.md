# Progreso

Estado de cada entregable. Se actualiza al cerrar cada uno.

## Etapa 1: Core + MCP

| # | Entregable | Estado |
| --- | --- | --- |
| 1.1 | Base, auth y usuarios | Aceptado |
| 1.2 | Proyectos, miembros, áreas y milestones | Listo |
| 1.3 | Tickets e historial | Listo |
| 1.4 | Workflows y transiciones | Listo |
| 1.5 | Links, comentarios y reacciones | Listo |
| 1.6 | RQL y búsqueda | Listo |
| 1.7 | Servidor MCP | Listo |
| 1.8 | UI web | Listo |

### 1.1 Base, auth y usuarios

**Qué se hizo**

- Monorepo `backend/` (FastAPI, SQLAlchemy async, Alembic) y `frontend/` (React 18, Vite, styled-components, i18n en/es, tema lima claro y oscuro).
- Migración `0001`: `users`, `api_tokens`, `sessions` con extensiones `citext` y `pg_trgm`.
- `/health`, `/api/v1/health`, `/api/v1/version`, `/api/v1/setup/status`, `/api/v1/setup`.
- Login con email y password (argon2id), sesión en cookie HttpOnly de 14 días deslizantes, CSRF, rate limit de 10 intentos por minuto por IP, logout.
- `/me` (GET, PATCH), tokens personales `/me/tokens`.
- Admin de instancia: `/users`, `/agents`, `/users/{handle}`, tokens de agente.
- Tokens `rdc_` + 40 base62, guardados como sha256, mostrados una sola vez; revocables y con expiración opcional.
- Errores RFC 9457 en toda la API.
- Dockerfile multi-stage (SPA + API en una imagen), `docker-compose.yml` con `app` y `db`, migraciones al arrancar.
- CI: lint, tipos, tests con cobertura, migraciones up/down/up, cliente OpenAPI al día, build de imagen y smoke.
- Pantalla temporal de estado en `/` (salud del servidor, setup pendiente, tema e idioma). La reemplaza la UI de 1.8.
- Decisiones: [0001](decisions/0001-frontend-styled-components.md), [0002](decisions/0002-cookies-secure-automatico.md), [0003](decisions/0003-csrf-y-endpoints-de-admin.md).

**Cómo verificarlo**

```bash
scripts/smoke.sh                       # levanta todo, hace setup, crea agente y usa su token
cd backend && uv run pytest --cov      # 109 tests contra Postgres real (requiere Docker)
cd frontend && pnpm check && pnpm build
```

A mano, con `docker compose up`:

```bash
curl -c jar -H 'Content-Type: application/json' localhost:8000/api/v1/setup \
  -d '{"handle":"fernando","display_name":"Fernando","email":"f@example.com","password":"cambia-esto"}'
CSRF=$(awk '$6=="radicle_csrf"{print $7}' jar)
curl -b jar -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  localhost:8000/api/v1/agents -d '{"handle":"agent-backend","display_name":"Backend agent"}'
curl -H "Authorization: Bearer rdc_..." localhost:8000/api/v1/me
```

**Cobertura al cerrar:** 93% total; `services/` entre 90% y 100%.



### 1.2 Proyectos, miembros, áreas y milestones

**Qué se hizo**

- Migración `0002`: `projects` (key inmutable por trigger), `project_members`, `areas`, `milestones`, `statuses`, `transitions` y los enums de rol, tipo, categoría, resolution y estado de milestone.
- Al crear un proyecto se siembran los workflows de Task, Bug y Draft del spec y el creador queda como admin.
- Endpoints de proyectos, archivar y desarchivar (solo lectura mientras está archivado), miembros (nunca sin admin), áreas (crear, editar, archivar y restaurar), milestones (crear, editar, cerrar, reabrir) y workflows.
- `/me` y el login regresan los proyectos con rol.
- Permisos en `services/access.py`, usados por todos los routers. Decisión: [0004](decisions/0004-admin-de-instancia-en-proyectos.md).
- El conteo por categoría de los milestones ya está en la respuesta; se llena con tickets reales en 1.3.

**Cómo verificarlo**

- `tests/integration/test_projects.py::test_acceptance_project_with_areas_and_milestone`: ProyectoA (PA) con Legal, Marketing, Backend, Frontend y V1.
- `tests/integration/test_project_permissions.py`: matriz de 10 acciones por 6 roles; viewer recibe 403 al editar y no miembro 404 en todo.

### 1.3 Tickets e historial

**Qué se hizo**

- Migración `0003`: `tickets` (con `search_vector` generado en inglés y español, índices GIN de tags, full-text y trigramas), `ticket_collaborators`, `mentions` y `ticket_events`.
- `ticket_events` es de solo inserción: un trigger rechaza `UPDATE`, `DELETE` y `TRUNCATE` aunque se haga desde SQL.
- CRUD de tickets con todos los campos fijos, áreas y milestones por nombre, personas por handle y padre por key. Errores con las opciones válidas (por ejemplo, "Valid areas: Legal, Marketing...").
- Numeración sin huecos ni duplicados con `UPDATE ... RETURNING` sobre `projects.ticket_seq`.
- Versionado optimista: `PATCH` exige `If-Match` o `expected_version`; si no coincide, 409 con el ticket actual.
- Un evento `field_changed` por campo con valor anterior y nuevo; `created`, `checklist_item_toggled`, `collaborator_added/removed`, `deleted`, `restored`.
- Checklist parseado de la descripción (ignora código, assignee por último `@handle`, `assignee_unknown`); `PATCH /checklist/{index}` reescribe solo esa línea.
- Menciones guardadas al crear o editar la descripción (fuera de código, sin contar emails).
- Soft delete y restore; los hijos pierden el padre con su evento.
- Rank con fractional indexing (máximo 4 caracteres tras 10,000 inserciones al final).
- Conteos reales por categoría en milestones y tickets abiertos por proyecto.

**Cómo verificarlo**

- `tests/integration/test_concurrency.py`: 50 creaciones en paralelo con commits reales dan PA-1 a PA-50.
- `tests/integration/test_history_integrity.py`: `UPDATE`, `DELETE` y `TRUNCATE` sobre el historial fallan.
- `tests/integration/test_tickets.py::test_patch_fields_and_history`: cada cambio con valor anterior y nuevo.
- `tests/integration/test_ticket_permissions.py`: matriz de 8 acciones por 6 roles.

### 1.4 Workflows y transiciones

**Qué se hizo**

- Motor de transiciones en `services/workflow_engine.py` (lógica pura, probada sin base de datos).
- `GET /tickets/{key}/transitions` con destino, categoría y resolutions permitidas.
- `POST /tickets/{key}/transitions` con `to_status`, `resolution` y opcionalmente `transition` cuando varias llegan al mismo destino (gana la que sale del estado actual sobre la de "cualquier estado").
- Transición inexistente: 409 con la lista de válidas en el mensaje y en `valid_transitions`. Done sin resolution o con una no permitida: 422 con `allowed_resolutions`. Una sola resolution permitida se pone sola (Draft Approve).
- Entrar a done llena `resolved_at`; salir limpia `resolution` y `resolved_at`.
- `POST /tickets/{key}/type`: estado inicial del nuevo workflow, limpia la resolution, pide `area` al pasar a Task o Bug sin área; eventos `type_changed`, `status_changed` y `field_changed` de área.
- Aviso `blocked` en transiciones a in_progress o done; se prueba en 1.5, cuando existen los links.

**Cómo verificarlo**

- `tests/integration/test_transitions.py::test_acceptance_task_lifecycle`: To Do a Done solo por Close con wont_do o duplicate, Complete pide resolution, Reopen la limpia.
- `tests/unit/test_workflow_engine.py`: 13 casos del motor.

### 1.5 Links, comentarios y reacciones

**Qué se hizo**

- Migración `0004`: `ticket_links`, `comments`, `comment_reactions` y la llave de `mentions.comment_id`.
- Links blocks, relates to, duplicates y clones; cada ticket los ve con su etiqueta (blocks / is blocked by, etc.). No se duplican en ningún sentido, ni hacia el mismo ticket. Evento `link_added` o `link_removed` en ambos tickets.
- `blocked` en el ticket y aviso `blocked` al moverlo a in_progress o done mientras un bloqueante no está en done.
- Comentarios markdown con menciones; editar solo el autor; borrar el autor o un admin del proyecto. Un comentario borrado queda como placeholder vacío y el historial registra `comment_deleted`. El historial guarda solo el id del comentario, no su texto.
- Reacciones con un emoji Unicode (incluye tonos de piel, secuencias ZWJ y banderas).
- Los tickets borrados desaparecen de los links.

**Cómo verificarlo**

- `tests/integration/test_links.py::test_acceptance_blocked_link_both_sides_and_warning`: PA-5 bloqueado por PA-4, etiqueta en ambos, aviso al mover PA-5.
- `tests/integration/test_comments.py::test_acceptance_comment_lifecycle`: comentar, reaccionar, editar, borrar y verlo en el historial.

### 1.6 RQL y búsqueda

**Qué se hizo**

- Gramática Lark (`query/grammar.lark`), árbol en `query/ast.py`, parser con errores que dicen posición, qué se encontró y qué se esperaba.
- Catálogo de 23 campos con operadores, IN y EMPTY (`query/fields.py`); sugerencias por distancia de edición ("Did you mean 'priority'?").
- Compilador a SQLAlchemy sin acceso a base de datos (`query/compiler.py`), probado comparando SQL generado.
- `GET /tickets?q=&limit=&cursor=` con filtro de permisos siempre aplicado (solo proyectos donde eres miembro, nunca tickets borrados), `total` y `warnings`.
- `GET /search/fields?project=PA`: campos, operadores, funciones, palabras clave y valores del proyecto (estados, áreas, milestones, handles, tags más usados).
- `scripts/seed.py --tickets 10000` crea un proyecto realista para medir y para demos.
- Decisión: [0005](decisions/0005-rql-cursor-y-semantica.md).

**Cómo verificarlo**

- `tests/integration/test_search.py::test_spec_examples`: los 7 ejemplos del spec regresan lo esperado.
- `tests/unit/test_rql_parser.py` (más de 60 casos) y `tests/unit/test_rql_compiler.py`: errores con posición.
- `tests/integration/test_performance.py` con 10,000 tickets: búsqueda p95 de 53 ms y board de 600 tickets en 122 ms (límites 300 ms y 1 s).

### 1.7 Servidor MCP

**Qué se hizo**

- SDK oficial `mcp` 2.x montado en la misma app en `/mcp` (Streamable HTTP, stateless, JSON).
- 19 tools con descripciones escritas para un LLM; cada una llama a la API REST en proceso con el token del agente, así comparten validaciones, permisos e historial.
- Respuestas compactas en listas (`compact`) y completas en `get_ticket` (con subtickets y últimos comentarios).
- Errores como tool errors con el mensaje accionable de la API, incluidas las transiciones válidas.
- Recursos `radicle://guide/rql` (generado del catálogo de campos) y `radicle://projects/{key}/schema`.
- `/mcp` rechaza con 401 conexiones sin token, con token desconocido o revocado.
- `scripts/smoke.sh` ahora hace `initialize`, `whoami` y `create_ticket` por MCP contra el contenedor.
- README con cómo conectar Claude Code, clientes JSON y `mcp-remote`. Decisión: [0006](decisions/0006-mcp-transporte-y-tools.md).

**Cómo verificarlo**

- `tests/mcp/test_agent_flow.py`: el agente hace `whoami`, `my_tickets`, `get_ticket`, mueve PA-4 a In Progress, marca el checklist, comenta, liga PA-4 bloqueando PA-5 y busca; el historial muestra cada evento con el agente como actor.
- `tests/mcp/test_tools.py`: éxito y error de cada tool, viewer sin permiso de crear, token revocado sin conexión.
- `scripts/smoke.sh` contra Docker.

### 1.8 UI web

**Qué se hizo**

- SPA en React 18 con TanStack Router y TanStack Query, styled-components con la paleta lima en claro y oscuro, inglés y español (`react-i18next`), organizada como vitaegap ([0001](decisions/0001-frontend-styled-components.md)).
- Pantallas: setup, login, proyectos, board, lista con RQL, detalle de ticket (página y panel lateral), milestones, settings (general, miembros, áreas, milestones y workflows en solo lectura), mis tickets, admin (usuarios, agentes y proyectos) y perfil.
- Board con columnas por categoría, tarjetas con key, tipo, prioridad, assignee (bot para agentes), tags, bloqueado y progreso del checklist; Drafts con borde punteado e ícono de semilla; drag and drop con dnd-kit que respeta las transiciones; filtros en la URL.
- Lista con barra RQL que autocompleta campos, operadores y valores y subraya el error en su posición; columnas ordenables que reescriben el `ORDER BY`; scroll infinito.
- Detalle: título editable, botón de estado con transiciones y resolutions, menú (cambiar tipo, copiar link, borrar), descripción con CodeMirror 6 y autocompletado de `@handle`, checklist clicable con avatares, campos editables en línea, subtickets, links agrupados, comentarios con reacciones e historial con diff de la descripción. Un 409 muestra "Alguien más cambió este ticket" y recarga sin perder lo escrito.
- Crear ticket en modal con "Más campos" y "Crear otro"; atajos `c` (crear) y `/` (buscar).
- Admin de agentes: el token se muestra una vez con botón copiar y los snippets de conexión MCP ya llenos.
- Estados vacíos con ilustraciones de plantas en línea delgada.
- Decisión: [0007](decisions/0007-ui-web.md).

**Cómo verificarlo**

```bash
cd frontend && pnpm check && pnpm build          # tipos, lint, formato y 15 tests de componentes
docker compose down -v && docker compose up -d --build
cd frontend && pnpm e2e                           # recorrido completo de la etapa en Playwright
```

El E2E cubre: setup, login, crear PA con 4 áreas y V1, crear Task, Bug y Draft (PA-1 a PA-3), mover en el board con drag and drop, comentar con mención, ligar "bloquea" y ver el aviso, buscar con RQL con error en posición, convertir Draft a Task y crear un agente copiando su token.

## Etapa 2: Configuración y trabajo diario

| # | Entregable | Estado |
| --- | --- | --- |
| 2.1 | Worker y campos custom | Listo |
| 2.2 | Templates y editor de workflows | Listo |
| 2.3 | Reglas de transición | Listo |
| 2.4 | Screens | Listo |
| 2.5 | Adjuntos | Listo |
| 2.6 | Votos y tiempo real invertido | Listo |
| 2.7 | Clonar, mover y bulk edit | Listo |
| 2.8 | Filtros, ranking, atajos y cmd+k | Listo |

### 2.1 Worker y campos custom

**Qué se hizo**

- Procrastinate como cola de jobs. Los jobs se encolan dentro de la transacción de la petición y el comando `radicle worker` los corre. Servicio `worker` en docker compose con la misma imagen. Decisión: [0008](decisions/0008-worker-y-cola-de-jobs.md).
- Tabla `jobs` con progreso y resultado, consultable en `GET /jobs/{id}` por quien lo inició.
- Migración `0005`: esquema de Procrastinate, `jobs`, `custom_field_definitions` y `tickets.custom_fields` (jsonb con índice GIN `jsonb_path_ops`).
- Campos custom por proyecto de 7 tipos (text, number, date, select, checkbox, user, url), restringibles por tipo de ticket y área. CRUD en `/projects/{key}/fields`; borrar archiva y conserva los valores. Decisión: [0009](decisions/0009-campos-custom.md).
- Los tickets aceptan `custom_fields` al crear y editar (solo cambian las keys enviadas; `null` limpia). Errores con las opciones válidas. Evento `custom_field_changed` en el historial.
- RQL `cf.<key>` con los operadores de cada tipo, autocompletado incluido.
- MCP: `create_ticket` y `update_ticket` aceptan `custom_fields`; `get_project` los lista.
- UI: pestaña Campos en Settings (crear, editar opciones con color, aplicar a tipos y áreas, archivar y restaurar) y campos editables en el panel del ticket, con "opción eliminada" cuando el valor ya no está entre las opciones.

**Cómo verificarlo**

- `tests/integration/test_custom_fields.py::test_acceptance_environment_select_on_bugs`: campo select "environment" en Bugs, se llena, se filtra con `cf.environment = prod` y un valor inválido da 422 con las opciones.
- `tests/integration/test_custom_fields.py`: validación por tipo, campo que no aplica, opción eliminada, archivar y restaurar, operadores RQL de cada tipo y permisos.
- `tests/integration/test_jobs.py`: el job encolado desaparece con un rollback y `queueing_lock` evita duplicados.
- `scripts/smoke.sh` comprueba que el contenedor `worker` está corriendo.

### 2.2 Templates y editor de workflows

**Qué se hizo**

- Migración `0006`: `templates`, `template_sync_runs`, `template_ref` en estados y transiciones, columnas de template y `blocked_policy` en proyectos, y el usuario `system`. Crea el template "Radicle default" con los workflows de la etapa 1 y liga a él los proyectos existentes. Decisión: [0010](decisions/0010-templates-y-propagacion.md).
- `/templates`: listar, crear, ver, editar (con `status_mappings`), archivar y restaurar; progreso de la propagación y reintento por proyecto.
- Proyectos: crear desde template (ligado o independiente), guardar como template, desligar, reemplazar un workflow (`PUT /projects/{key}/workflows/{type}`) y `blocked_policy` (`PUT /projects/{key}/settings`), estos dos solo en proyectos independientes. Editar campos, workflows o settings de un proyecto ligado regresa 409 con el nombre del template.
- Propagación en el worker por proyecto: agrega, renombra, reordena y quita estados y transiciones; agrega, actualiza y archiva campos custom; agrega áreas y tags. Los tickets de un estado borrado pasan al estado mapeado con evento `status_remapped` firmado por `system`.
- MCP: `get_project` incluye template, modo y política de bloqueo.
- UI: pestaña Templates en Admin; editor de template con pestañas General (nombre, áreas, tags, política), Workflows (estados con drag, matriz de transiciones, resolutions y diagrama Mermaid), Campos custom y Propagación (estado por proyecto con reintento). Diálogo de mapeo obligatorio al guardar con estados borrados. En el proyecto: banner "Ligado a Radicle default v1" con Desligar, editor de workflows si es independiente, campos en solo lectura si está ligado, "Guardar como template" y selector de template con vista previa al crear proyecto.

**Cómo verificarlo**

- `tests/integration/test_templates.py::test_acceptance_template_propagates_to_linked_projects_only`: "Producto digital" desde PA, PB ligado y PC desligado; agregar "Blocked" al template llega a PB y no a PC.
- `test_removing_a_status_needs_a_mapping_and_moves_tickets`: quitar In Review sin mapeo da 422 con los tickets afectados; con mapeo el ticket pasa a In Progress con `status_remapped` por `system`.
- `test_rename_reorder_and_fields_by_ref`, `test_failed_sync_does_not_stop_others_and_can_be_retried`, `test_independent_project_workflow_editor` y validaciones de configuración.
- `scripts/smoke.sh`: un cambio al template llega a un proyecto ligado a través del contenedor `worker`.

### 2.3 Reglas de transición

**Qué se hizo**

- Migración `0007`: `transition_rules` y `tickets.time_spent_minutes`.
- Catálogo completo del spec: conditions (`only_assignee`, `only_reporter`, `only_roles`, `only_user_kind`, `not_blocked`), validators (`checklist_complete`, `field_required`, `has_estimate`, `children_done`, `has_worklog`, `comment_required`) y post-functions (`assign_to_actor`, `unassign`, `set_field`, `clear_field`, `add_tag`, `remove_tag`, `add_comment`). Decisión: [0011](decisions/0011-reglas-de-transicion.md).
- Orden de ejecución: conditions, política de bloqueo, validators, cambio de estado, comentario y post-functions, todo en una transacción.
- Política de bloqueo `warn` o `enforce` con `force` para admins registrado en el historial.
- API: `include_unavailable` en las transiciones; `comment` y `force` al transicionar. MCP: `transition_ticket` acepta `comment` y `get_project` resume las reglas por transición.
- UI: panel de reglas por transición en el editor de workflows (template y proyecto independiente), contador de reglas en la matriz; al mover un ticket se ven las transiciones no disponibles con su motivo, se pide comentario cuando es obligatorio, los validators fallidos se listan exactos y un admin puede forzar un ticket bloqueado.

**Cómo verificarlo**

- `tests/integration/test_transition_rules.py::test_acceptance_checklist_complete_blocks_complete`: con `checklist_complete` en Complete, un ticket con dos items abiertos no pasa y el error los nombra.
- El mismo archivo prueba cada regla con caso que pasa y que falla, el orden de ejecución, el rollback de una post-function fallida, `warn` y `enforce` con `force`, y que las reglas viajan con el template.

### 2.4 Screens

**Qué se hizo**

- Migración `0008`: `screens` por proyecto, tipo de ticket y operación (create, edit o una transición).
- `GET` y `PUT /projects/{key}/screens` (editar solo en proyectos independientes) y `GET /projects/{key}/schema?type&operation&transition` con tipo, obligatorio y opciones de cada campo. Decisión: [0012](decisions/0012-screens.md).
- Validación en el servicio: obligatorios al crear, campos de solo lectura y obligatorios al editar, y campos de la screen al transicionar (se pueden mandar en `fields`). Mismo mensaje en UI, API y MCP.
- Las screens viajan en el template y se propagan a los proyectos ligados.
- MCP: tool `get_ticket_schema`; `transition_ticket` acepta `fields`.
- UI: crear ticket se arma con el esquema (obligatorios marcados con * y validados antes de enviar, opcionales en "Más campos"); el panel del ticket deja en solo lectura lo que no está en la screen de edición; al transicionar se piden los campos de su screen. Editor de screens en el template y en Settings del proyecto.

**Cómo verificarlo**

- `tests/integration/test_screens.py::test_acceptance_required_custom_field_same_in_api_and_mcp`: un Bug sin Environment falla en la API y en el MCP con el mismo mensaje.
- El mismo archivo prueba el esquema con y sin screen, solo lectura en edición, la screen de una transición, validaciones y propagación por template.
- `frontend/src/features/tickets/components/CreateTicketModal/CreateTicketModal.test.tsx`: el formulario sale del esquema y no envía sin los obligatorios.

### 2.5 Adjuntos

**Qué se hizo**

- Migración `0009`: `attachments`. Storage local (volumen compartido por app y worker) o S3 compatible. Decisión: [0013](decisions/0013-adjuntos.md).
- Subida multipart con límite `RADICLE_MAX_UPLOAD_MB` (413), tipo por contenido, EXIF borrado, orientación corregida y reducción a original, large, medium o small. Variantes `thumb` y `preview` hechas por el worker.
- `POST /attachments/{id}/resize` reduce una imagen ya subida (nunca la agranda) con evento `attachment_resized`; borrar por quien la subió o un admin. URLs firmadas de 5 minutos; en S3, redirección a URL prefirmada.
- `GET /tickets/{key}` incluye los adjuntos. MCP: `upload_attachment` (hasta 10 MB), `list_attachments` y `read_attachment` (texto hasta 200 KB).
- UI: sección Adjuntos con miniaturas, visor de imágenes con flechas, menú Reducir tamaño y borrar; subir con botón o arrastrando. En la descripción y los comentarios se puede pegar o arrastrar archivos, con barra de progreso; al pegar una imagen se elige el tamaño con el default preseleccionado. `![x](attachment:id)` se ve como imagen.

**Cómo verificarlo**

- `tests/integration/test_attachments.py::test_acceptance_screenshot_in_comment_resized_to_medium`: un screenshot en un comentario, preview hecho por el worker, reducido a mediano y su tamaño baja.
- El mismo archivo prueba presets exactos, EXIF, tipo por contenido, el 413, la expiración de la firma, permisos y borrado. `tests/integration/test_storage_s3.py` prueba S3 contra un servidor real.
- `frontend/src/features/tickets/components/UploadStatus/UploadStatus.test.tsx`: pegar una imagen pide tamaño y deja el markdown en el editor.

### 2.6 Votos y tiempo real invertido

**Qué se hizo**

- Migración `0010`: `ticket_votes`, `worklogs` y en tickets `original_estimate_hours`, `remaining_hours`, `remaining_mode` y `vote_count`. Decisión: [0014](decisions/0014-votos-y-tiempo.md).
- Votos 🙋: `PUT` y `DELETE /tickets/{key}/vote` y `GET /tickets/{key}/voters`; un voto por persona, sin notificaciones, los agentes no votan.
- Worklogs: registrar, listar, editar y borrar (propios o como admin); estimado original fijo, restante automático o manual. `log_minutes` al transicionar.
- RQL `votes`, `spent`, `remaining` y `original_estimate`, y `ORDER BY votes DESC`.
- MCP: `log_work` y `list_worklogs`; `transition_ticket` acepta `log_minutes`; `get_ticket` trae `vote_count` y el tiempo.
- UI: botón 🙋 con conteo y quién votó al pasar el cursor; columna Votos ordenable en la lista; barra estimado contra invertido que se pone en warning al pasar el original; restante editable con "volver a auto"; Registrar tiempo ("1h 30m"); pestaña Tiempo; tiempo opcional al mover un ticket.

**Cómo verificarlo**

- `tests/integration/test_votes_time.py::test_acceptance_agent_logs_two_hours`: el agente registra 2 h por MCP y el restante baja de 5 a 3.
- `test_votes_and_backlog_by_votes`: el backlog se ordena por votos. `tests/integration/test_concurrency.py::test_parallel_votes_keep_vote_count_exact`: 8 personas votando 3 veces a la vez dejan `vote_count = 8`.

### 2.7 Clonar, mover y bulk edit

**Qué se hizo**

- Migración `0011`: `ticket_key_aliases`. Decisión: [0015](decisions/0015-clonar-mover-bulk.md).
- `POST /tickets/{key}/clone` con proyecto destino, mapeo de áreas e `include` (descripción, estado del checklist, tags, campos custom, colaboradores, adjuntos, subtickets con su árbol). Link `clones` y evento `cloned_from`.
- `POST /tickets/{key}/move` (admin en origen, member en destino) con mapeo de áreas y estados, milestone y subtickets; la key vieja sigue resolviendo en API, MCP y UI.
- `POST /tickets/bulk` por keys o RQL, hasta 500 tickets, con `dry_run`; arriba de 100 corre como job con progreso en `GET /jobs/{id}` y resultado por ticket.
- MCP: `clone_ticket`, `move_ticket` y `bulk_update` (dry run por default).
- UI: Clonar y Mover en el menú del ticket con sus opciones y mapeos; la URL vieja redirige a la nueva; en la lista, checkbox por fila y barra de acciones (Editar campo, Tags, Mover estado, Asignar) con vista previa y progreso.

**Cómo verificarlo**

- `tests/integration/test_clone_move_bulk.py::test_acceptance_move_keeps_old_key`: PA-7 pasa a PB como PB-15 y `GET /tickets/PA-7` regresa PB-15 con `moved_from`.
- `test_acceptance_bulk_120_runs_as_job`: quitar #backlog y poner V1 a 120 tickets, con vista previa, corre como job y reporta por ticket.
- `frontend/src/features/list/components/BulkBar/BulkBar.test.tsx`: vista previa y aplicar.

### 2.8 Filtros, ranking, atajos y cmd+k

**Qué se hizo**

- Migración `0012`: `saved_filters` y `user_preferences`. Decisión: [0016](decisions/0016-filtros-ranking-atajos.md).
- Filtros guardados privados, de proyecto o de instancia (`/filters`), y `filter = "<nombre>"` en RQL, también anidados.
- Ranking manual `POST /tickets/{key}/rank` con evento `rank_changed` y rebalanceo por job.
- `POST /tickets/next` con `claim` atómico (`FOR UPDATE SKIP LOCKED`).
- Preferencias por persona `GET` y `PATCH /me/preferences`.
- MCP: `next_ticket`, `rank_ticket`, `list_filters`, `run_filter` y `save_filter`. Las tools quedaron en módulos por tema (`mcp/tools/`).
- UI: barra lateral de filtros en la lista (míos, del proyecto, de todos) y "Guardar"; arrastrar filas para reordenar cuando la lista va por rank, y soltar una tarjeta sobre otra en el board para ponerla arriba; atajos `c`, `/`, `⌘K`, `?`, `g p`, `g m`, `j`, `k`, `Enter`, `e`, `a`, `m`, `l`, `p` y `Esc` con ayuda en `?`; paleta de comandos con tickets, proyectos, filtros, acciones y recientes; preferencias de atajos, densidad, tema e idioma en el perfil.

**Cómo verificarlo**

- `tests/integration/test_filters_rank_next.py::test_acceptance_agent_claims_next_ticket`: el agente llama `next_ticket` con `claim=true` y queda asignado y en progreso el de más arriba.
- `tests/integration/test_concurrency.py::test_ten_agents_claim_different_tickets`: 10 agentes reclaman a la vez y reciben 10 tickets distintos.
- `frontend/e2e/stage2.spec.ts`, último paso: flujo diario solo con teclado.

## Etapa 2: aceptación

Los criterios de aceptación de la etapa se verifican así:

| Criterio | Dónde |
| --- | --- |
| Template "Producto digital" desde ProyectoA y ProyectoB a partir de él | E2E `template from PA reaches PB...`; `test_templates.py` |
| "Blocked" llega a ProyectoB en segundos y no a ProyectoC desligado | E2E (worker real); `test_acceptance_template_propagates_to_linked_projects_only` |
| Quitar un estado pide a dónde mandar sus tickets y los mueve con historial | `test_removing_a_status_needs_a_mapping_and_moves_tickets`; diálogo de mapeo |
| `checklist_complete` en Complete; el error dice qué falta | E2E; `test_acceptance_checklist_complete_blocks_complete` |
| Política enforce: un ticket bloqueado no pasa a In Progress | `test_blocked_policy_warn_and_enforce` |
| Un Bug exige Environment al crearse en UI, API y MCP | E2E; `test_acceptance_required_custom_field_same_in_api_and_mcp` |
| Pegar un screenshot, reducirlo a mediano y que baje su tamaño | E2E; `test_acceptance_screenshot_in_comment_resized_to_medium` |
| Votar con 🙋 y ordenar el backlog por votos | E2E; `test_votes_and_backlog_by_votes` |
| Un agente registra 2 h por MCP y la barra se actualiza | `test_acceptance_agent_logs_two_hours` |
| Mover PA-7 a ProyectoB y el link viejo sigue funcionando | E2E; `test_acceptance_move_keeps_old_key` |
| Quitar #backlog y poner V1 a 120 tickets con vista previa | `test_acceptance_bulk_120_runs_as_job`; E2E de bulk |
| `next_ticket` con `claim=true` | `test_acceptance_agent_claims_next_ticket` y la prueba de concurrencia |
| Flujo diario solo con teclado y `cmd+k` | E2E `daily work with the keyboard only` |
