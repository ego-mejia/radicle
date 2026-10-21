# Radicle

Ticket tracker self-hosted con MCP. Antes de programar lee `docs/Radicle Documento de control.md` (reglas para todas las etapas) y el build spec de la etapa en curso. El estado está en `docs/progress.md`.

## Reglas que más se olvidan

- La lógica vive en `services/` (`backend/radicle/platform/services/` y `backend/radicle/docket/services/`, ver ADR 0034; `platform` nunca importa de una app). Routers (`api/`) y tools del MCP (`mcp/`) solo validan y llaman servicios.
- Errores siempre como `ProblemError` (`platform/errors.py`) con mensaje accionable; salen como RFC 9457.
- Todo cambio de esquema: migración Alembic con upgrade y downgrade. `tests/integration/test_migrations.py` corre up/down/up y `alembic check`.
- Cada endpoint: test feliz, de error y de permisos. Tests contra Postgres real (testcontainers).
- Cobertura: 85% en `services/` y `query/`, 70% total. mypy estricto en `services/` y `query/`.
- Código, API y commits en inglés (Conventional Commits). Docs internos (`docs/`) en español; `README.md` y `CONTRIBUTING.md` en inglés, con `README.es.md` en español.
- Ramas `tipo/descripcion` (`feat/`, `minor/`, `fix/`, `refactor/`, `docs/`). Un PR hace una sola cosa, con tests, menos de 500 líneas y menos de 100 archivos (`scripts/pr-size.sh`). Ver `CONTRIBUTING.md`.
- Si algo se desvía del spec, primero un ADR en `docs/decisions/`.
- Al cerrar un entregable: `docs/progress.md`, `CHANGELOG.md` y README (inglés y español).

## Frontend

Ver `docs/decisions/0001-frontend-styled-components.md`:

- styled-components con los tokens de `src/styles/theme.ts`; nada de Tailwind ni colores sueltos.
- Una carpeta por componente: `index.tsx` sin estilos + `style.ts` (`import * as S from './style'`) + tests.
- Máximo 500 líneas por archivo (ESLint `max-lines`). Si crece, se parte en `components/` dentro de su carpeta.
- Textos siempre por i18n (`src/i18n/locales/en.json` y `es.json`).

## Comandos

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy radicle && uv run pytest --cov
cd frontend && pnpm check && pnpm build
scripts/smoke.sh
```
