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

- Gramática Lark (`query/grammar.lark`), árbol en `query/ast.py` (desde Folio 1.6 en `platform/query/`, compartidos con Folio), parser con errores que dicen posición, qué se encontró y qué se esperaba.
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

## Etapa 3: Planeación y visibilidad

| # | Entregable | Estado |
| --- | --- | --- |
| 3.1 | Periodos de estado y snapshots | Listo |
| 3.2 | Boards configurables | Listo |
| 3.3 | Scrum | Listo |
| 3.4 | Timeline | Listo |
| 3.5 | Reportes agile | Listo |
| 3.6 | Reportes generales | Listo |
| 3.7 | Dashboards | Listo |

### 3.1 Periodos de estado y snapshots

**Qué se hizo**

- Migración `0013`: `tickets.start_date`, `ticket_status_periods` (llenada desde `ticket_events` al migrar) y `daily_status_counts`. Decisión: [0017](decisions/0017-periodos-y-snapshots.md).
- Periodos mantenidos en la misma transacción de cada cambio de estado.
- Snapshot diario idempotente en el worker (cada hora recalcula ayer y hoy) y comandos `radicle backfill-periods` y `radicle backfill-snapshots --from AAAA-MM-DD`.

**Cómo verificarlo**

- `tests/integration/test_periods.py::test_backfill_rebuilds_exactly_the_live_periods`: con reapertura, cambio de tipo y movimiento de proyecto, el backfill da exactamente los periodos que se escribieron en vivo.
- `test_snapshot_is_idempotent_and_uses_the_time_zone`: dos snapshots del mismo día no duplican, y el corte del día sigue `RADICLE_TIMEZONE`.

### 3.2 Boards configurables

**Qué se hizo**

- Migración `0014`: `boards` y `board_quick_filters`; cada proyecto recibe un board Kanban "Main" con una columna por categoría y cuatro quick filters (Mis tickets, Solo bugs, #backlog, Bloqueados). Decisión: [0018](decisions/0018-boards-configurables.md).
- API `/projects/{key}/boards`, `/boards/{id}`, quick filters, `/boards/{id}/data` (agrupado por columna y carril, 50 por columna) y `/boards/{id}/move` (transición y rank juntos, WIP duro con forzado de admin).
- MCP: `list_boards` y `get_board`.
- UI: selector de boards, quick filters, carriles plegables con conteo, WIP en rojo al pasarse, campos de tarjeta elegibles y la pantalla `/p/{key}/boards/{id}` para configurar todo.

**Cómo verificarlo**

- `tests/integration/test_boards.py::test_acceptance_review_column_with_wip_3`: columna "Review" con In Review y QA Verified, WIP 3, en rojo con el cuarto.
- Mismo archivo: mover con una, varias y ninguna transición, WIP duro y forzado, cada swimlane, quick filters combinados y tickets no visibles.
- `test_performance.py` (marca `slow`): board de 500 tickets con swimlanes en menos de 1 s.

### 3.3 Scrum

**Qué se hizo**

- Migración `0015`: `sprints`, `sprint_tickets` y `sprint_commitments`, con un solo sprint activo por board y un ticket en a lo más un sprint abierto garantizados por índices. Decisión: [0019](decisions/0019-scrum.md).
- API de sprints (crear, editar según estado, borrar futuros, iniciar con compromiso, cerrar con traspaso, meter y sacar tickets, reporte) y `GET /boards/{id}/backlog`.
- RQL `sprint` (`active`, `future`, nombre, `IS EMPTY`) y `start`; `start_date` editable en API, MCP y UI.
- MCP: `list_sprints`, `get_sprint`, `add_to_sprint`, `remove_from_sprint`, `start_sprint`, `complete_sprint`.
- UI: pestaña Backlog con sprints arriba (capacidad, aviso de tickets sin estimar), backlog abajo, drag entre listas, selección múltiple, diálogos Iniciar y Cerrar sprint; el board Scrum muestra el sprint activo.

**Cómo verificarlo**

- `tests/integration/test_sprints.py::test_acceptance_full_sprint`: planear con capacidad, iniciar, agregar a mitad (cambio de alcance), cerrar mandando lo pendiente a #backlog; el reporte guardado no cambia después.
- Mismo archivo: máquina de estados, un solo activo, un ticket en un solo sprint abierto, traspaso al siguiente sprint, permisos, RQL `start` y `sprint`, snapshot por sprint y las tools del MCP.

### 3.4 Timeline

**Qué se hizo**

- `GET /projects/{key}/timeline` con grupos por milestone (objetivo y pronóstico) o área, tickets sin fechas aparte y dependencias Blocks con conflicto marcado. Decisión: [0020](decisions/0020-timeline.md).
- Pronóstico de milestone en `services/forecast.py` (lo reutiliza 3.6).
- UI `/p/{key}/timeline`: Gantt en SVG con zoom semana, mes y trimestre, línea de hoy, rombo de milestone y marcador de pronóstico, barras por categoría, drag de barra y bordes, panel "Sin fechas" con drag al timeline, flechas en rojo con conflicto, filas virtualizadas y barra RQL.
- Corrección en boards: un estado aparece solo en la primera columna que lo tiene, también cuando una columna toma la categoría completa.

**Cómo verificarlo**

- `tests/integration/test_timeline.py`: grupos, sin fechas, conflicto que se resuelve al mover fechas, historial de fechas y pronóstico "en riesgo"/"en tiempo"/"sin pronóstico".
- E2E `drag a bar on the timeline and see a dependency in red`.

### 3.5 y 3.6 Reportes

**Qué se hizo**

- `GET /reports/{type}` y `/reports/{type}.csv`: burndown, burnup, velocity, cumulative flow, control chart, sprint report, creados vs resueltos, distribución por campo, progreso de milestone con pronóstico y tiempo. Decisión: [0021](decisions/0021-reportes.md).
- Restante reconstruible por día: todo cambio de `remaining_hours` queda en el historial. Nueva variable `RADICLE_WORKDAYS`.
- MCP: `get_report` y `get_milestone_progress`.
- UI `/p/{key}/reports` con Recharts: lista de reportes, filtros comunes (board, sprint, milestone, área, rango), cifras clave, tabla plegable y Exportar CSV. Las tarjetas de milestones muestran el pronóstico y si está en tiempo o en riesgo.

**Cómo verificarlo**

- `tests/integration/test_reports.py`: un sprint sembrado con fechas controladas; cada reporte da los números calculados a mano (burndown ideal y real, burnup, sprint report, velocity, CSV, CFD, cycle time y percentiles, creados vs resueltos, distribución, pronóstico en tiempo y en riesgo, tiempo).
- `test_performance.py` (marca `slow`): CFD de un año con 10,000 tickets en menos de 1 s (unos 80 ms).
- E2E `the sprint report and burndown add up, and V1 has a forecast`.

### 3.7 Dashboards

**Qué se hizo**

- Migración `0016`: `dashboards` y `dashboard_widgets`; cada proyecto recibe su "Summary". Decisión: [0022](decisions/0022-dashboards.md).
- API `/dashboards`, `/dashboards/{id}`, widgets, `/projects/{key}/dashboard` y `/widgets/{id}/data` (datos con los permisos de quien ve).
- Diez widgets: resultados de filtro, conteo, distribución (barras o pastel), progreso de milestone, creados vs resueltos, burndown del sprint, cumulative flow, bloqueados, mis tickets y markdown.
- UI: `/dashboards`, `/d/{id}` con modo edición (catálogo, configuración, drag y resize), compartir, refresco cada 5 minutos, y la pestaña "Resumen" en cada proyecto.

**Cómo verificarlo**

- `tests/integration/test_dashboards.py::test_acceptance_v1_go_to_market`: el dashboard con progreso, bugs por área y bloqueados se comparte con el proyecto y un miembro lo ve con sus permisos (sin los bugs de otro proyecto).
- E2E `build "V1 Go to market" and share it with the project`.

### Aceptación de la etapa 3

| Criterio | Dónde |
| --- | --- |
| Columna "Review" con In Review y QA Verified, WIP 3, en rojo con el cuarto | E2E; `test_acceptance_review_column_with_wip_3` |
| Swimlanes por área y quick filter "Solo bugs" responden al instante | E2E; `test_swimlanes_and_quick_filters` |
| Planear un sprint con capacidad, iniciar, agregar a mitad y cerrar a #backlog | E2E; `test_acceptance_full_sprint` |
| El burndown y el sprint report cuadran con lo que pasó | `test_reports.py` con fechas controladas; E2E de reportes |
| Timeline con V1; arrastrar cambia fechas; dependencia imposible en rojo | E2E; `test_timeline.py` |
| Progreso de V1 con % y pronóstico; "en riesgo" si pasa la fecha | `test_milestone_forecast`, `test_general_reports` |
| Dashboard "V1 Go to market" compartido y visto con permisos propios | E2E; `test_acceptance_v1_go_to_market` |
| Un agente consulta `get_milestone_progress` y `get_sprint` por MCP | `test_mcp_reports`, `test_mcp_sprints` |
| Rendimiento: CFD de un año con 10,000 tickets < 1 s; board de 500 con swimlanes < 1 s | `test_performance.py` (marca `slow`) |

## Etapa 4: Buzón y control de acceso

| # | Entregable | Estado |
| --- | --- | --- |
| 4.1 | Grupos y permisos por rol | Listo |
| 4.2 | Tickets restringidos | Listo |
| 4.3 | Buzón interno | Listo |
| 4.4 | Formulario público | Listo |
| 4.5 | SSO | Listo |
| 4.6 | Audit log | Listo |
| 4.7 | MCP y UI de la etapa | Listo |

### 4.1 Grupos y permisos por rol

**Qué se hizo**

- Migración `0017`: `groups`, `group_members`, `project_group_roles` y `project_role_permissions`. Decisión: [0023](decisions/0023-grupos-y-permisos.md).
- `core/permissions.py`: catálogo, rol efectivo (directo o por grupo, el más alto) y `authorize()`, usado por todas las rutas y tools.
- API: `/groups` (admin de instancia), `/projects/{key}/group-roles`, `/projects/{key}/permissions` (leer, cambiar y restaurar defaults); `/me` y el detalle del proyecto traen los permisos efectivos.
- UI: pestaña Permisos con la matriz, grupos en Miembros con rol efectivo, Admin → Grupos; los botones se ocultan según los permisos.

**Cómo verificarlo**

- `tests/integration/test_permission_matrix.py`: cada permiso del catálogo para member y viewer, directo con default y por grupo con override (76 casos), más las tools del MCP con el permiso quitado; rol efectivo, acceso solo por grupo y pérdida inmediata al salir del grupo.

### 4.2 Tickets restringidos

**Qué se hizo**

- Migración `0018`: `security_levels`, `security_level_grants` y `tickets.security_level_id`. Decisión: [0024](decisions/0024-tickets-restringidos.md).
- `visible_tickets_clause(user)` como único filtro de visibilidad en todo el sistema; 404 para lo restringido; links y padre como "Ticket restringido"; historial sin keys ocultas.
- API de niveles (`/projects/{key}/security-levels`, `/security-levels/{id}`, `/grants`) y `security_level` en el ticket.
- UI: candado en el ticket (con permiso), banner de restringido, pestaña Niveles en Settings.

**Cómo verificarlo**

- `tests/integration/test_restricted.py`: recorre todas las rutas GET y las tools de lectura del MCP como un miembro fuera del nivel y falla si aparece el ticket; 404 por key, alias, comentario, adjunto y worklog; grants por grupo, admins y participantes; `next_ticket`, bulk y permiso `ticket.set_security`.

### 4.3 Buzón interno

**Qué se hizo**

- Migración `0019` con origen, clasificación, impacto, esfuerzo y conversión. Decisión: [0025](decisions/0025-buzon.md).
- `GET /projects/{key}/inbox` con pestañas, filtros y orden; `POST /tickets/{key}/inbox/approve`, `/discard` y `/duplicate`; RQL `origin`, `classification`, `impact`, `effort` y `converted`.
- MCP: `list_inbox`, `score_inbox_item`, `approve_inbox_item`, `discard_inbox_item`, `mark_inbox_duplicate`; `create_ticket` acepta `classification`.
- UI: pestaña Buzón con contador de nuevos, tabla con calificación en línea, matriz impacto por esfuerzo con drag, diálogos de aprobar, descartar y duplicado; en el ticket, datos del Buzón y badge "Vino del Buzón".

**Cómo verificarlo**

- `tests/integration/test_inbox.py`: clasificación obligatoria y origen por canal, pestañas, orden por puntaje y RQL, permiso `inbox.triage`, aprobar y convertir atómico conservando votos, comentarios y origen, descartar y duplicado con traspaso de votos sin repetir, y las tools del MCP.

### 4.4 Formulario público

**Qué se hizo**

- Migración `0020`: `inbox_settings`, `inbox_submissions`, `used_challenges` y el usuario de sistema `inbox`. Decisión: [0026](decisions/0026-formulario-publico.md).
- Página pública `/b/{slug}` (Jinja) con ALTCHA, honeypot, tiempo mínimo, rate limit, máximo de links, adjuntos (imágenes reducidas y PDF) y página de seguimiento `/b/{slug}/t/{code}`.
- `GET/PUT /projects/{key}/inbox-settings` y la pestaña Buzón en Settings con link para copiar.
- `RADICLE_SECRET_KEY` ahora es obligatoria y cifra secretos (AES-GCM).

**Cómo verificarlo**

- `tests/integration/test_public_form.py`: envío sin cuenta con captura que aparece en el Buzón con origen Usuario, seguimiento Recibido, Aceptado y Cerrado con nota y sin datos internos; ALTCHA inválido y reusado, honeypot, tiempo mínimo, links, rate limit del sexto envío, tipos y tamaños de archivos, email obligatorio, escape de HTML y markdown, secretos cifrados y rate limit del seguimiento.

### 4.5 SSO

**Qué se hizo**

- Migración `0021`: `sso_providers`, `instance_settings` e identidad SSO en `users`. Decisión: [0027](decisions/0027-sso.md).
- OIDC con Authlib y PKCE, varios proveedores, alta automática por dominio, liga por email verificado, sync de grupos mapeados, usuarios desactivados fuera y password apagable con salida de emergencia para el primer admin.
- API: `/auth/options`, `/auth/sso/{id}/login` y `/callback`, `/admin/sso-providers` (con Probar conexión) y `/admin/settings`.
- UI: un botón por proveedor en el login, Admin → SSO y Admin → Ajustes.

**Cómo verificarlo**

- `tests/integration/test_sso.py` (marca `slow`, Keycloak en testcontainers): login que crea la cuenta en el grupo mapeado, dominio rechazado, liga por email verificado, sync que agrega y quita solo los mapeados, usuario desactivado rechazado, password apagado con la salida del admin inicial y estado inválido.

### 4.6 Audit log

**Qué se hizo**

- Migración `0022`: `audit_log` con trigger que rechaza `UPDATE`, `DELETE` y `TRUNCATE`, y el rol `radicle_audit_retention` para la retención. Decisión: [0028](decisions/0028-audit-log.md).
- Catálogo de 39 acciones (usuarios, tokens, agentes, proyectos, miembros, grupos, permisos, niveles de seguridad, tickets, templates, workflows, Buzón, SSO y ajustes) registradas con antes y después, IP y user agent.
- API: `GET /audit` y `GET /audit.csv` con filtros por actor, acción, proyecto y fechas; admins de proyecto ven solo sus proyectos.
- Job diario `audit_retention` con `RADICLE_AUDIT_RETENTION_DAYS` (730).
- UI: Admin → Audit log y Configuración del proyecto → Audit log, con filtros, detalle antes/después y CSV.

**Cómo verificarlo**

- `tests/integration/test_audit.py`: cada acción del catálogo deja su entrada, filtros y CSV, admin de proyecto filtrado y member con 403, `UPDATE`/`DELETE`/`TRUNCATE` fallan, la retención borra solo lo vencido.

### 4.7 MCP y UI de la etapa

**Qué se hizo**

- Tools MCP del Buzón (`list_inbox`, `score_inbox_item`, `approve_inbox_item`, `discard_inbox_item`, `mark_inbox_duplicate`); el MCP queda con 48 tools que siguen la matriz de permisos y los niveles de seguridad.
- Pantallas: Settings → Permisos, Grupos con rol, Niveles de seguridad y Buzón; Admin → Grupos, SSO, Audit log y Ajustes; Buzón con tabla y matriz; login con SSO; página pública y seguimiento.
- Correcciones que salieron del E2E: la matriz de impacto acomodaba mal las celdas (las etiquetas de cuadrante ocupaban su lugar), calificar impacto y esfuerzo seguidos perdía uno por choque de versión (ahora se guardan en orden), y el slug default de un proyecto con key de dos letras no pasaba la validación (ahora 2 a 40 caracteres).

**Cómo verificarlo**

- E2E `frontend/e2e/stage4.spec.ts`: queja con screenshot desde un navegador sin sesión, aparece en el Buzón con origen Usuario, se califica y aparece en la matriz, se aprueba como Bug en Backend y el seguimiento dice Accepted; quitar `comment.create` a member esconde el botón de comentar; un ticket restringido no se ve ni se encuentra para otro member. Los 25 E2E de las etapas 1 a 4 pasan.

### Aceptación de la etapa 4

| Criterio | Dónde |
| --- | --- |
| Grupo equipo-legal en ProyectoA como member, sus integrantes trabajan sin agregarlos uno por uno | `test_group_only_members_see_the_project`, `test_effective_role_is_the_highest` |
| Quitar `ticket.transition` a member lo bloquea en UI, API y MCP | `test_permission` (matriz parametrizada), `test_mcp_follows_the_matrix`; E2E con `comment.create` |
| Nivel "Legal confidencial": nadie más lo ve, ni por key, links, reportes o MCP | `test_nothing_leaks_through_get_routes` (enumera todas las rutas GET), `test_mcp_tools_do_not_leak`, `test_next_ticket_bulk_and_aliases_skip_it`; E2E |
| Buzón activo, queja con screenshot en incógnito y código de seguimiento | `test_acceptance_send_a_complaint_and_track_it`; E2E |
| Origen Usuario, matriz, aprobar como Bug en Backend conservando votos, comentarios y origen | `test_acceptance_approve_and_convert`; E2E |
| Seguimiento dice Aceptado sin nada interno | `test_acceptance_send_a_complaint_and_track_it`, `test_discarded_shows_the_public_note`; E2E |
| Duplicado pasa sus votantes al original | `test_discard_and_duplicate` |
| El sexto envío en una hora desde la misma IP se bloquea | `test_sixth_submission_in_an_hour_is_blocked` |
| Entrar con Keycloak crea la cuenta en el grupo mapeado | `test_acceptance_login_creates_the_user_in_the_mapped_group` (marca `slow`) |
| Todo queda en el audit log y no se puede modificar | `test_every_action_of_the_catalog_is_logged`, `test_the_log_cannot_be_changed` |
| Un agente lista el Buzón, califica un Draft y descarta otro por MCP | `test_mcp_inbox_tools` |
| Reglas generales del documento de control | CI: ruff, mypy estricto, cobertura, migraciones up/down/up y `alembic check`, E2E |


## Después de la etapa 4: mejoras de uso y Radi

Fuera del spec de etapas, pedidas al probar la app (ADRs 0032 y 0033 para el board):

- Board con look de Jira, la tarjeta cae donde se suelta, destello al moverla (más brillante en Done), columna In Review en Main y carriles plegables.
- List con botón Filter, Group by, filtros guardados en menú y subtickets bajo su padre.
- Members con buscador de personas, agentes y grupos; edición de proyectos; agentes desde Admin → Users con permisos de tools MCP.
- Radi: asistente con la guía de uso y LLM opcional (app o `RADICLE_ASSISTANT_*`), recorridos en pantalla y logo nuevo.
- Celebración de milestone con recap, confeti e imagen para LinkedIn.
- El CI de GitHub Actions queda en pausa; los checks se corren local antes de cada push.
- Tarjetas con área, milestone y subtickets (editables desde la tarjeta), áreas con icono SVG en su color, pegar imágenes al crear un ticket y Done sin modal de resolución.
- MCP: `create_area`, `update_area`, `create_milestone` y `update_milestone` (paridad con la API; piden `project.settings`). El MCP queda con 52 tools (`tests/mcp/test_area_milestone_tools.py`).

## Folio fase 0: Plataforma compartida

Folio es la suite de documentación de Radicle; sus specs están en `docs/folio/`. Tickets en el proyecto RAD (área Folio, milestones Folio Fase 0 a 5).

| # | Entregable | Estado |
| --- | --- | --- |
| 0.1 | Reorganizar el backend | Listo |
| 0.2 | Autorización genérica | Listo |
| 0.3 | Servicios compartidos | Listo |
| 0.4 | Frontend compartido y switch | Listo |
| 0.5 | Esqueleto de Folio | Listo |

Decisiones: [0034](decisions/0034-folio-fase-0-1-reorganizar-backend.md), [0035](decisions/0035-autorizacion-generica.md), [0036](decisions/0036-frontend-compartido-sin-carpeta-platform.md).

### 0.1 Reorganizar el backend

**Qué se hizo**

- `radicle/platform` (config, cifrado, errores, seguridad, sesión de base de datos, modelos y servicios de usuarios, tokens, SSO, grupos, audit y jobs, storage, cola, imágenes, Markdown, validación, piezas comunes de la API y el cliente MCP en proceso) y `radicle/docket` (todo lo de tickets). En `radicle/` solo queda la composición: `main.py`, `cli.py`, `seed.py` y `worker/`.
- Primero se cortaron los imports de `platform` hacia Docket: la consulta del audit log y los roles de grupos en proyectos pasaron a módulos de Docket, y el catálogo de tools del MCP se registra al arrancar. Luego se movió todo con `scripts/move_modules.py` (`git mv` más reescritura de imports, sin cambios de lógica).
- `tests/unit/test_dependencies.py`: falla si `platform` importa de una app o si `folio` toca tablas de `docket`.

**Cómo verificarlo**

- La suite de Docket pasa sin tocar aserciones; `scripts/export_openapi.py` no cambia `frontend/openapi.json`; `test_tool_catalog` lista las mismas tools.

### 0.2 Autorización genérica

**Qué se hizo**

- `platform/authz.py`: `authorize(db, user, app, permission, resource)` devuelve un `Decision` (403 o 404 y un motivo accionable) y `visible(user, app, model)` el filtro SQL. Una app o un recurso desconocido se niega.
- El proveedor de Docket envuelve su `authorize`, `can_see` y `visible_tickets_clause` sin cambiarlos. `platform.services.groups.group_ids` cachea los grupos de cada usuario 60 s para las apps que los resuelven en Python (Folio); Docket los sigue resolviendo en su SQL, y salir de un grupo ahí sigue siendo inmediato.

**Cómo verificarlo**

- `tests/integration/test_authz.py`: matriz de Docket, ticket restringido (404), app desconocida, proveedor de prueba y caché a 59 y 61 s.

### 0.3 Servicios compartidos

**Qué se hizo**

- Migración `0028`: `audit_log.app` (platform, docket o folio; lo anterior queda docket). `GET /audit` lo regresa.
- Migración `0029`: `ai_settings`, un solo proveedor de IA para chat y embeddings (none, anthropic, openai, openai_compatible, ollama) con la llave cifrada. `GET` y `PUT /admin/ai` y `POST /admin/ai/test`, que genera un embedding de prueba y da dimensiones y latencia. Anthropic no tiene embeddings y el error lo dice.
- UI: tarjeta **AI provider** en Admin → Settings.

**Cómo verificarlo**

- `tests/integration/test_ai_settings.py` con un proveedor simulado; `test_audit.py` para la columna `app`.

### 0.4 Frontend compartido y switch

**Qué se hizo**

- El logo es el switch de suite (`components/layout/SuiteSwitch`), con el diseño aprobado del canvas: apps visibles para el usuario, la actual marcada, atajos, administración para admins de instancia. Cada app reabre en su última página.
- `g d` y `g f` cambian de app. `/folio` tiene su propio shell.

**Cómo verificarlo**

- `e2e/suite.spec.ts`: login, cambiar a Folio con el logo y con `g f`, regresar con `g d` sin volver a entrar, y Folio ausente para alguien sin rol.

### 0.5 Esqueleto de Folio

**Qué se hizo**

- `radicle/folio`. Migración `0030`: `folio_global_grants` (reader, creator o admin para una persona, un grupo o todos; semilla everyone = reader). El rol efectivo es el más alto entre el directo, el de sus grupos y el de todos; el admin de instancia siempre es admin.
- `GET /api/v1/folio/health`, `GET /folio/me`, y `GET`, `POST` y `DELETE /folio/admin/grants` para admins de Folio, con audit `app = folio`.
- `/mcp/folio` con `whoami`, con el mismo token que `/mcp`.
- UI: shell de Folio con home vacía y **Admin → Global roles**.

**Cómo verificarlo**

- `tests/integration/test_folio_roles.py`, `test_folio.py` y `tests/mcp/test_folio_mcp.py`; en el E2E, dar rol creator a un grupo desde Admin de Folio.

### Aceptación de la fase

| Criterio | Dónde |
| --- | --- |
| Todo Docket funciona igual: tests, API y MCP | Suite completa (798), OpenAPI sin diff en los movimientos, `test_tool_catalog` |
| Entro una vez y cambio entre Docket y Folio desde el logo y con atajos | `e2e/suite.spec.ts` |
| Doy rol creator a un grupo y se refleja en `/api/v1/folio/me` de sus miembros | `test_folio.py::test_group_role_reaches_its_members`, `e2e/suite.spec.ts` |
| Configuro el proveedor de embeddings y la prueba de conexión pasa | `test_ai_settings.py::test_configure_encrypt_test_and_audit` |
| Un agente llama `whoami` en los dos MCP con el mismo token | `test_folio_mcp.py::test_whoami_on_both_servers_with_one_token` |
| Reglas generales | ruff, mypy estricto (también `folio.services`), cobertura 95%, migraciones up/down/up, E2E completo (28) en una instancia limpia |

Nota: los E2E `stage1` y `stage3` estaban rotos desde #60 (botones de área y milestone en las tarjetas); se arreglaron en #78.

## Folio fase 1: Core de publicación + MCP

Spec: `docs/folio/fase-1.md`. Decisión de base: [0037](decisions/0037-pgvector-y-dimension-de-embeddings.md). Tickets RAD-16 a RAD-23 cerrados con screenshots; milestone Folio Fase 1 cerrado.

| # | Entregable | Estado | PRs |
| --- | --- | --- | --- |
| 1.1 | Spaces y árbol | Listo | #84–#87, #139, #144, #145 |
| 1.2 | Editor base | Listo | #88–#92, #119, #127, #130, #140, #146, #163 |
| 1.3 | Publicación y versiones | Listo | #93–#96, #121, #124, #153, #154, #165 |
| 1.4 | Permisos | Listo | #97–#100, #162 |
| 1.5 | Agentes y aprobación | Listo | #101, #102, #131, #148 |
| 1.6 | RAG, búsqueda y RQL | Listo | #103–#113, #149, #152, #157, #164, #166 |
| 1.7 | MCP de Folio | Listo | #111, #114, #115, #168 |
| 1.8 | UI | Listo | #116, #118, #125–#159 y los arreglos de abajo |

**Qué se hizo**

- **Spaces y árbol:** spaces de equipo y personales, páginas, folders y blog posts con rank fraccional (`COLLATE "C"`), mover dentro del árbol, eventos de nodo append-only.
- **Editor:** esquema TipTap validado en el servidor, Markdown en los dos sentidos (directivas en `docs/folio/markdown.md`), borradores, assets (imágenes, archivos, video), ícono y portada. En la UI: TipTap a pantalla completa con menú `/`, atajos de Markdown, subir al pegar y autoguardado.
- **Publicación:** catálogos de tipos, audiencias e idiomas; metadata obligatoria con errores por campo; versiones inmutables (trigger), diff por bloques y de metadata, restaurar como versión nueva.
- **Permisos:** roles globales, permisos por space y restricciones de vista y edición por página, con la regla de visibilidad en SQL (CTE recursivo). `tests/integration/test_folio_leaks.py` enumera todas las rutas GET de Folio y falla si una no está cubierta.
- **Agentes:** lo que publica un agente es un envío pendiente; los admins lo aprueban o lo rechazan con comentario.
- **Búsqueda:** chunks por sección con metadata, pgvector con índices HNSW por dimensión, búsqueda de texto (español e inglés), semántica e híbrida (RRF), con visibilidad en SQL antes de rankear. Si ninguna página tiene todas las palabras, busca con cualquiera (#164). RQL de docs sobre el motor de Docket, que pasó a `platform/query`.
- **MCP:** 12 tools en `/mcp/folio`; un solo catálogo de tools con límites por agente para todas las apps (`platform/mcp_tools.py`, `platform/mcp/server.py`).
- **UI:** home bento (`GET /folio/home`), space con árbol arrastrable, lectura revista y modo enfoque, editor, publicar, historial con diff, cola de aprobación, catálogos y búsqueda con barra RQL. Hecha en paralelo por cuatro agentes, cada uno en su worktree.

**Bugs encontrados al probar en Chrome y corregidos:** la barra de Folio tapaba la del editor (#163); la portada de las páginas salía vacía (#163); una pregunta sin todas sus palabras no encontraba nada (#164); los fragmentos de búsqueda mostraban Markdown (#166); los títulos largos del árbol se cortaban sin "…" y el diff se veía como texto plano (#165); Editar se mostraba aunque una restricción de edición lo impidiera (#162); el tag de tipo no se veía en modo oscuro (#169); una página titulada como su primera sección caía en la intro (#113).

### Aceptación de la fase

| Criterio | Dónde |
| --- | --- |
| Space con folder, páginas anidadas y blog post, en su sidebar y en la home | `test_folio_tree.py`, `test_folio_home.py`, screenshots en RAD-16 |
| Guía con todos los bloques y una imagen pegada | `folio_docs.EVERY_BLOCK` (round-trip servidor y editor), `test_folio_assets.py` |
| Sin descripción no publica; completarla publica | `test_folio_publish.py`, `e2e/suite-folio1.spec.ts` |
| Comparar la versión 1 con la 3 y restaurar la 1 | `test_folio_versions.py`, screenshot en RAD-18 |
| Rol creator solo para un grupo; los demás no ven Escribir | `test_folio_roles.py`, `e2e/suite.spec.ts`, screenshot en RAD-19 |
| Una página restringida desaparece para los demás, también en la búsqueda semántica | `test_folio_leaks.py`, `test_folio_search.py`, `tests/mcp/test_folio_mcp_read.py` |
| Un agente por MCP propone un post a partir de un repo; queda pendiente y se aprueba en la cola | `tests/mcp/test_folio_mcp_write.py`, `e2e/suite-folio1.spec.ts` |
| "cómo conecto un agente" da la guía correcta en la sección correcta | `test_folio_search.py::test_acceptance_the_right_guide_at_the_right_section` |
| Lectura revista y modo enfoque, claro y oscuro | Screenshots en RAD-23 |
| Docket sigue pasando todos sus tests | Suite completa y E2E: 31/31 en Chrome sobre una instancia limpia |

## Folio fase 2: Colaboración

Cerrada el 21 de octubre de 2026 (RAD-24 a RAD-30, milestone "Folio Fase 2"). Spec: `docs/folio/fase-2.md`. Decisiones: [0038](decisions/0038-eventos-y-notificaciones-en-platform.md), [0039](decisions/0039-tiempo-real-con-pycrdt-sin-pycrdt-websocket.md), [0040](decisions/0040-anclas-de-comentarios-por-contexto.md).

| # | Entregable | Estado |
| --- | --- | --- |
| 2.1 | Bus de eventos y notificaciones en platform | Listo (#120, #122, #123, #129, #176, #178, #182, #187, #293) |
| 2.2 | Tiempo real | Listo (#174, #185, #188, #192, #235, #236, #239, #251) |
| 2.3 | Comentarios | Listo (#155, #179, #181, #189, #196, #200, #212, #216, #218, #220, #228) |
| 2.4 | Menciones, reacciones, watch, compartir y action items | Listo (#140, #160, #161, #191, #195, #197, #199, #210, #217, #288) |
| 2.5 | Live docs | Listo (#198, #208, #241, #242, #251) |
| 2.6 | Organización | Listo (#142, #147, #201, #204, #219) |
| 2.7 | Calidad y navegación | Listo (#133, #151, #172, #173, #175, #184, #190, #205, #207, #211) |

- **Eventos:** outbox en la misma transacción, despacho con `SKIP LOCKED`, entregas únicas por evento, persona y canal, preferencias por tipo y canal, email por SMTP con reintentos, y un stream SSE sobre `LISTEN/NOTIFY`.
- **Tiempo real:** Yjs con `pycrdt` en el servidor y sala propia sobre su protocolo, sin pycrdt-websocket ([0039](decisions/0039-tiempo-real-con-pycrdt-sin-pycrdt-websocket.md)). WebSocket `/api/v1/folio/collab/{node_id}` solo para quien edita (sesión o bearer), una sala por documento en el proceso, máximo 50 editores. Los updates van a `folio_yupdates` y se compactan en `folio_ydocs` cada 30 s o al vaciarse la sala; el `content_json` del borrador se regenera cada 5 s. Los borradores de fase 1 se convierten la primera vez. Publicar toma el estado del Y.Doc. Las ediciones de agentes por REST o MCP entran al Y.Doc con su etiqueta. En el editor: carets y selecciones en el color de cada quien, avatares de presencia y punteros de mouse con nombre (≤30 por segundo, se ocultan tras 10 s quietos).
- **Live docs:** `kind=live_doc`, siempre editables, sin publicar, metadata ni RAG. Snapshot cada 10 minutos con sus autores, historial con restaurar (`GET /nodes/{id}/snapshots`, `POST /snapshots/{id}/restore`) y en el MCP `create_live_doc` y `append_to_live_doc`.
- **Comentarios:** al pie con hilos e inline anclados a la cita con su contexto ([0040](decisions/0040-anclas-de-comentarios-por-contexto.md)); resolver, reabrir y huérfanos cuando se borra el texto. Comentar es el permiso `comment` del space, que por defecto solo tienen sus admins (los defaults de fase 1: everyone con `view`).
- **Social y tareas:** reacciones, seguir, favoritos, compartir con mensaje, y action items con asignado y fecha que llegan a Mis tareas. Quien se asigna una tarea a sí mismo no recibe aviso (#288).
- **Calidad y navegación:** dueño, estados (publicada, en revisión, verificada con vencimiento por space, desactualizada), recientes, favoritos y el feed Para ti.
- **E2E:** `RADICLE_LOGIN_RATE_LIMIT_PER_MINUTE` se puede subir para correrlos (las specs entran más de diez veces por minuto).

### Aceptación de la fase

Probada en el navegador sobre un stack aislado (main `f06a60e`), en claro y oscuro, con capturas en cada ticket. Dos navegadores editan el mismo doc y se ven caret y puntero con nombre; un comentario inline sigue en su cita después de editar el párrafo; una mención avisa al instante; las tareas llegan a Mis tareas por vencimiento; el live doc guarda snapshots con autores.

Pendiente: los títulos de los avisos los arma el servidor en inglés; las preferencias ya se traducen (#293).

## Folio fase 3: Contenido rico (en curso)

Spec: `docs/folio/fase-3.md`.

### 3.5 Whiteboards

Listo: #266, #268, #272, #273, #275, #278, #279, #283, #295. Referencia en `docs/folio/whiteboards.md`.

- **Modelo:** nodo `kind=whiteboard` (migración 0047, downgrade reconstruye el enum) y `folio_whiteboards` con la escena en JSON y su texto. Nunca se publica ni tiene draft: quien lo ve lo lee como está.
- **Tiempo real:** la misma sala de 2.2 ([0039](decisions/0039-tiempo-real-con-pycrdt-sin-pycrdt-websocket.md)). La escena es `Y.Map("elements")`, un elemento de Excalidraw por id; gana la versión más alta y, si empatan, el `versionNonce` menor, igual en el servidor y en cada cliente. La sala guarda la escena cada 5 s y al cerrarse.
- **Búsqueda:** el texto de los elementos entra al índice cuando cambia; sus chunks no tienen versión (migración 0048 hace opcional `folio_chunks.version_id`).
- **API:** `GET /whiteboards/{id}` (la escena actual y `can_edit`), en `test_folio_leaks.py` y `test_restricted.py`. Para dibujar, el WebSocket de `/collab/{id}`.
- **UI:** Excalidraw 0.18.1 con sus fuentes servidas por Radicle (no un CDN) y en su propio chunk. Página del whiteboard con presencia y punteros con nombre, exportar PNG y SVG; quien solo lee ve la escena guardada, refrescada cada 10 s. "Nuevo whiteboard" en el space e icono en el árbol. Bloque `whiteboard` desde `/` y en la lectura, solo para ver, con aviso de sin acceso; en Markdown `::whiteboard{id=…}`.
- **Fuera de alcance:** imágenes dentro del whiteboard (la herramienta está apagada; los archivos no se sincronizan) y tools del MCP para whiteboards.

| Aceptación | Prueba |
| --- | --- |
| Dos personas dibujan en el mismo whiteboard | `test_folio_whiteboards.py::test_two_people_draw_together_and_the_scene_is_kept`, `whiteboard/sync.test.ts`, `e2e/suite-folio3-whiteboard.spec.ts` |
| Se incrusta en una página | `WhiteboardBlock.test.tsx`, `e2e/suite-folio3-whiteboard.spec.ts` |
| Export PNG y SVG; textos indexados | `e2e/suite-folio3-whiteboard.spec.ts`, `test_folio_whiteboards.py::test_its_text_is_found_by_search` |

### 3.6 Databases

Listo: #226, #227, #229, #231, #234, #237, #240, #245, #246, #248, #250, #254, #257, #258, #260, #262. Referencia en `docs/folio/databases.md`.

- **Modelo:** nodo `kind=database` (migración 0046, downgrade reconstruye el enum), `folio_databases` (columnas y vistas en JSONB) y `folio_db_rows` (valores JSONB, rank fraccional, borrado suave). Nueve tipos de columna; un cambio de tipo convierte lo que cabe y la respuesta dice cuántos valores borró (`cleared`). Límites: 50 columnas, 20 vistas, 10,000 filas.
- **API:** `GET/PATCH /databases/{id}`, `GET/POST /databases/{id}/rows?view` con filtros y orden en el servidor, `POST .../rows/batch` (hasta 100, todo o nada), `PATCH/DELETE /rows/{id}`. Los permisos siguen al nodo; las dos rutas GET están en `test_folio_leaks.py` y `test_restricted.py`.
- **MCP:** `query_database` y `add_database_rows` (por nombre de columna), en el catálogo y en las pruebas de páginas restringidas y sin acceso.
- **UI:** página de la database con barra de vistas (tabla, tarjetas y tablero agrupado por una columna select, con arrastre entre grupos), edición de celdas por tipo, agregar y borrar filas, editar vistas (filtros, orden, columnas visibles) y columnas (agregar, renombrar, cambiar tipo, opciones de los select). Bloque `databaseView` desde `/` y en la lectura, con aviso de sin acceso; en Markdown `::database{id=… view=…}`.
- **Fuera de alcance:** las filas no entran a la búsqueda ni al RAG en esta fase.

| Aceptación | Prueba |
| --- | --- |
| Inventario de AI Tools visto como tablero por estado | `test_folio_databases.py`, `test_folio_databases_api.py::test_build_and_read_a_board`, `tests/mcp/test_folio_mcp_databases.py` |

