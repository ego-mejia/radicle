# Radicle

Ticket tracker open source y self-hosted con servidor MCP desde el día 1: personas y agentes trabajan el mismo proyecto.

> Estado: etapas 1 a 4 completas. Ver [docs/progress.md](docs/progress.md).

## Instalar

Requisitos: Docker con Compose.

```bash
cp .env.example .env        # pon RADICLE_SECRET_KEY (openssl rand -hex 32); es obligatoria
docker compose up -d
```

Se levantan tres contenedores: `app` (API, UI y MCP), `worker` (jobs en segundo plano) y `db` (Postgres).

Abre `http://localhost:8000`: la primera vez aparece la pantalla de setup para crear el admin. La API está en `/api/v1` y su documentación interactiva en `/api/docs`.

### Crear un agente

En **Admin → Agentes → Nuevo agente**. El token (`rdc_...`) se muestra una sola vez, con botón para copiarlo y los snippets de conexión MCP ya llenos. Después agrégalo al proyecto en **Settings → Miembros** con rol Miembro para que pueda trabajar tickets.

Por API, como admin de instancia: `POST /api/v1/agents` con `{"handle": "agent-backend", "display_name": "Backend agent"}`.

### Conectar un agente por MCP

El servidor MCP vive en `/mcp` (Streamable HTTP) y acepta el token del agente o un token personal.

Claude Code:

```bash
claude mcp add --transport http radicle http://localhost:8000/mcp \
  --header "Authorization: Bearer rdc_xxxxxxxx"
```

Clientes con configuración JSON:

```json
{
  "mcpServers": {
    "radicle": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer rdc_xxxxxxxx" }
    }
  }
}
```

Clientes que solo hablan stdio usan [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) como puente:

```json
{
  "mcpServers": {
    "radicle": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp",
               "--header", "Authorization: Bearer rdc_xxxxxxxx"]
    }
  }
}
```

Tools (48): `whoami`, `list_projects`, `get_project`, `search_tickets`, `my_tickets`, `get_ticket`, `create_ticket`, `update_ticket`, `get_ticket_schema`, `get_transitions`, `transition_ticket`, `change_ticket_type`, `set_checklist_item`, `add_comment`, `list_comments`, `link_tickets`, `unlink_tickets`, `add_collaborator`, `remove_collaborator`, `get_history`, `upload_attachment`, `list_attachments`, `read_attachment`, `log_work`, `list_worklogs`, `clone_ticket`, `move_ticket`, `bulk_update`, `next_ticket`, `rank_ticket`, `list_filters`, `run_filter`, `save_filter`, `list_boards`, `get_board`, `get_milestone_progress`, `get_report`, `list_sprints`, `get_sprint`, `add_to_sprint`, `remove_from_sprint`, `start_sprint`, `complete_sprint`, `list_inbox`, `score_inbox_item`, `approve_inbox_item`, `discard_inbox_item`, `mark_inbox_duplicate`. Recursos: `radicle://guide/rql` y `radicle://projects/{key}/schema`.

## Configuración

Todo se configura con variables de entorno (ver `.env.example`). Las más importantes:

- `RADICLE_SECRET_KEY` (obligatoria): firma los links de los adjuntos y la cookie del SSO, y cifra los secretos guardados (client secret del SSO, secret del captcha). Usa un valor largo y aleatorio (`openssl rand -hex 32`) y no la cambies después.
- `RADICLE_AUDIT_RETENTION_DAYS` (730): cuántos días se guarda el audit log; un job diario borra lo más viejo.
- `RADICLE_STORAGE`: `local` guarda los adjuntos en el volumen `attachments`; `s3` usa cualquier S3 compatible (AWS, MinIO, R2) con `RADICLE_S3_*`.
- `RADICLE_MAX_UPLOAD_MB` (25) y `RADICLE_IMAGE_DEFAULT_RESIZE` (`large`): tamaño máximo por archivo y tamaño default de las imágenes.

El contenedor `worker` corre los trabajos en segundo plano: propagación de templates, variantes de imágenes, ediciones masivas grandes y rebalanceo del ranking. Si no está corriendo, esas tareas esperan en la cola.

## Boards

Cada proyecto empieza con un board Kanban "Main". Los admins crean más desde el board (**Nuevo board**) y los configuran en **Configurar**: origen RQL (un área o varios proyectos), columnas por estado o por categoría, límites WIP suaves (avisan en rojo) o duros (bloquean, un admin puede forzar), carriles, campos de la tarjeta y quick filters.

Los boards Scrum tienen sprints. En la pestaña **Backlog** se planean arrastrando tickets a cada sprint (con barra de capacidad), se inicia el sprint con fechas y meta, y al cerrarlo lo pendiente pasa al siguiente sprint o regresa a `#backlog`.

La pestaña **Timeline** muestra los tickets en el tiempo por milestone o área: arrastra una barra para cambiar sus fechas, o un ticket del panel "Sin fechas" para dárselas. Las dependencias imposibles se marcan en rojo.

En **Reportes** están burndown, burnup, velocity, cumulative flow, control chart, sprint report, creados vs resueltos, distribución, progreso de milestone con pronóstico y tiempo; cada uno con su tabla y Exportar CSV. `RADICLE_WORKDAYS` define los días hábiles del burndown.

**Dashboards** junta widgets (conteos, distribuciones, progreso de milestone, burndown, bloqueados...) en una cuadrícula que se arma arrastrando. Cada proyecto tiene su **Resumen**; los demás se comparten contigo, con un proyecto o con todos, y cada quien ve solo los tickets que puede ver.

**Buzón**: cada proyecto puede abrir un formulario público en `/b/{slug}` (Settings → Buzón) para que cualquiera mande quejas, sugerencias o ideas sin cuenta, con ALTCHA contra spam y un código para seguir su envío. Todo llega como Draft al Buzón del proyecto, donde se califica, se aprueba como task o bug, o se descarta.

### Permisos y acceso

Cada proyecto tiene roles admin, member y viewer, directos o vía **grupos** (Admin → Grupos); vale el rol más alto. En **Settings → Permisos** se prende o apaga cada permiso para member y viewer, y aplica igual en la UI, la API y el MCP. Los **niveles de seguridad** (Settings → Niveles) restringen un ticket a ciertos grupos o personas: para los demás no existe en ninguna búsqueda, board, reporte ni tool.

**Audit log** (Admin → Audit log, o Settings → Audit log para admins de proyecto) registra los cambios administrativos con quién, cuándo, IP y el antes y después; se filtra, se exporta a CSV y nadie lo puede modificar.

### SSO

En **Admin → SSO** se agregan proveedores OpenID Connect (Google, Microsoft Entra ID, Okta, Keycloak, Authentik): issuer, client ID y secret, dominios permitidos y mapeo de grupos. Registra en el proveedor la URL de callback que muestra el formulario. En **Admin → Ajustes** se puede apagar la entrada con password; aun así, el primer admin de la instancia siempre puede entrar con su password: es la salida de emergencia si el proveedor falla.

## Atajos

`?` muestra todos. Los principales: `c` crear ticket, `/` buscar, `⌘K` paleta de comandos, `g p` proyectos, `g m` mis tickets, `j`/`k` moverse en listas y board, y con un ticket abierto `e` título, `a` asignarme, `m` mover, `l` tags, `p` prioridad. Se pueden apagar en el perfil.

## Desarrollo

| Parte | Requisitos | Comandos |
| --- | --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (tests) | `cd backend && uv sync`, `uv run uvicorn radicle.main:app --reload`, `uv run pytest` |
| Frontend | Node 22, pnpm 9 | `cd frontend && pnpm install`, `pnpm dev` (proxy a `:8000`), `pnpm check`, `pnpm e2e` (Radicle limpio en `:8000`) |
| Base local | Docker | `docker compose up -d db` y `cd backend && uv run alembic upgrade head` |

- Los tests de backend levantan Postgres 16 con testcontainers; no usan SQLite.
- Si cambias la API: `cd backend && uv run python ../scripts/export_openapi.py` y `cd frontend && pnpm api:types`.
- Smoke completo: `scripts/smoke.sh` (construye la imagen, la levanta en limpio como proyecto `radicle-smoke` en el puerto 8001 y la borra al terminar; no toca tu stack).

## Documentación

- [Documento de control](docs/Radicle%20Documento%20de%20control.md): etapas, stack y reglas.
- Build specs: [etapa 1](docs/Radicle%20Build%20spec%20etapa%201.md), [2](docs/Radicle%20Build%20spec%20etapa%202.md), [3](docs/Radicle%20Build%20spec%20etapa%203.md), [4](docs/Radicle%20Build%20spec%20etapa%204.md).
- [Decisiones](docs/decisions/) y [progreso](docs/progress.md).

## Licencia

AGPL-3.0 (pendiente de confirmar, ver supuestos del documento de control).
