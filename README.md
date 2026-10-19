# Radicle

Ticket tracker open source y self-hosted con servidor MCP desde el día 1: personas y agentes trabajan el mismo proyecto.

> Estado: etapa 1 en construcción (entregable 1.1 listo). Ver [docs/progress.md](docs/progress.md).

## Instalar

Requisitos: Docker con Compose.

```bash
cp .env.example .env        # opcional: cambia RADICLE_BASE_URL y POSTGRES_PASSWORD
docker compose up -d
```

Abre `http://localhost:8000`. La API está en `/api/v1` y su documentación interactiva en `/api/docs`.

### Primer admin

Mientras llega la UI de setup (1.8), se crea por API:

```bash
curl -c jar -H 'Content-Type: application/json' http://localhost:8000/api/v1/setup \
  -d '{"handle":"admin","display_name":"Admin","email":"admin@example.com","password":"una-contraseña-larga"}'
```

`/setup` solo funciona una vez.

### Crear un agente

Como admin de instancia (con la cookie del paso anterior y su token CSRF):

```bash
CSRF=$(awk '$6=="radicle_csrf"{print $7}' jar)
curl -b jar -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  http://localhost:8000/api/v1/agents -d '{"handle":"agent-backend","display_name":"Backend agent"}'
```

La respuesta trae `token.token` (`rdc_...`). Se muestra una sola vez. El agente se autentica con `Authorization: Bearer rdc_...`. La conexión por MCP (`/mcp`) llega en el entregable 1.7.

## Desarrollo

| Parte | Requisitos | Comandos |
| --- | --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (tests) | `cd backend && uv sync`, `uv run uvicorn radicle.main:app --reload`, `uv run pytest` |
| Frontend | Node 22, pnpm 9 | `cd frontend && pnpm install`, `pnpm dev` (proxy a `:8000`), `pnpm check` |
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
