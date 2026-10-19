# Radicle

Ticket tracker open source y self-hosted con servidor MCP desde el día 1: personas y agentes trabajan el mismo proyecto.

> Estado: etapa 1 completa; etapa 2 en curso. Ver [docs/progress.md](docs/progress.md).

## Instalar

Requisitos: Docker con Compose.

```bash
cp .env.example .env        # opcional: cambia RADICLE_BASE_URL y POSTGRES_PASSWORD
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

Tools: `whoami`, `list_projects`, `get_project`, `search_tickets`, `my_tickets`, `get_ticket`, `create_ticket`, `update_ticket`, `get_transitions`, `transition_ticket`, `change_ticket_type`, `set_checklist_item`, `add_comment`, `list_comments`, `link_tickets`, `unlink_tickets`, `add_collaborator`, `remove_collaborator`, `get_history`. Recursos: `radicle://guide/rql` y `radicle://projects/{key}/schema`.

## Desarrollo

| Parte | Requisitos | Comandos |
| --- | --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (tests) | `cd backend && uv sync`, `uv run uvicorn radicle.main:app --reload`, `uv run pytest` |
| Frontend | Node 22, pnpm 9 | `cd frontend && pnpm install`, `pnpm dev` (proxy a `:8000`), `pnpm check`, `pnpm e2e` (Radicle limpio en `:8000`) |
| Base local | Docker | `docker compose up -d db` y `cd backend && uv run alembic upgrade head` |

- Los tests de backend levantan Postgres 16 con testcontainers; no usan SQLite.
- Si cambias la API: `cd backend && uv run python ../scripts/export_openapi.py` y `cd frontend && pnpm api:types`.
- Smoke completo: `scripts/smoke.sh` (construye la imagen, la levanta en limpio y la borra al terminar).

## Documentación

- [Documento de control](docs/Radicle%20Documento%20de%20control.md): etapas, stack y reglas.
- Build specs: [etapa 1](docs/Radicle%20Build%20spec%20etapa%201.md), [2](docs/Radicle%20Build%20spec%20etapa%202.md), [3](docs/Radicle%20Build%20spec%20etapa%203.md), [4](docs/Radicle%20Build%20spec%20etapa%204.md).
- [Decisiones](docs/decisions/) y [progreso](docs/progress.md).

## Licencia

AGPL-3.0 (pendiente de confirmar, ver supuestos del documento de control).
