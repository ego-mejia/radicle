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
