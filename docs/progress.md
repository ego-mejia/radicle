# Progreso

Estado de cada entregable. Se actualiza al cerrar cada uno.

## Etapa 1: Core + MCP

| # | Entregable | Estado |
| --- | --- | --- |
| 1.1 | Base, auth y usuarios | Aceptado |
| 1.2 | Proyectos, miembros, áreas y milestones | Listo |
| 1.3 | Tickets e historial | Listo |
| 1.4 | Workflows y transiciones | Pendiente |
| 1.5 | Links, comentarios y reacciones | Pendiente |
| 1.6 | RQL y búsqueda | Pendiente |
| 1.7 | Servidor MCP | Pendiente |
| 1.8 | UI web | Pendiente |

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

**Pendiente para entregables siguientes:** `/me` regresa `projects: []` hasta 1.2; el smoke agrega MCP en 1.7.

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
