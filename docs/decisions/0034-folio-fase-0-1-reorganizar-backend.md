# 0034. Cómo se reorganiza el backend en platform y docket (Folio 0.1)

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec de Folio fase 0 (entregable 0.1), `CONTRIBUTING.md` (tamaño de PR)

El entregable 0.1 de Folio mueve el código a `radicle/platform` (lo que comparten las apps) y `radicle/docket` (los tickets) sin cambiar comportamiento. Aquí queda qué va a cada lado y cómo se parte el trabajo.

## Qué va a cada paquete

| Paquete | Contenido |
| --- | --- |
| `radicle/platform` | `config`, `crypto`, `errors`, `security` (hoy en `core/`); sesión y `Base` de la base de datos; modelos de usuarios, tokens, sesiones, SSO, ajustes de instancia, grupos y sus miembros, audit log y jobs; storage; worker y cola; servicios de auth, usuarios, grupos, SSO, audit, jobs, cola de jobs, imágenes, Markdown y validación |
| `radicle/docket` | Todo lo demás: routers de `/api/v1`, servicios de tickets y proyectos, RQL, MCP, formulario público, matriz de permisos de proyecto, niveles de seguridad y el resto de los modelos |
| `radicle/` (raíz) | Solo la composición: `main.py`, `cli.py`, `seed.py`, `worker/` (qué módulos registran jobs y cuáles corren con cron) y `__init__.py` importan de las dos apps y las montan |

- Los routers de usuarios, auth, SSO, grupos, audit y jobs se quedan en `docket/api` por ahora: sus respuestas traen datos de proyectos (por ejemplo, `/me` y el login regresan los proyectos con rol) y la API de Docket no cambia. Folio tendrá los suyos bajo `/api/v1/folio`.
- Las llaves foráneas de `platform` hacia tablas de Docket (por ejemplo `audit_log.project_id`) se quedan en la base: son strings en SQLAlchemy y no obligan a importar código de Docket.
- Alembic importa los modelos de las dos apps en `migrations/env.py`; las tablas no se renombran.
- Donde hoy `platform` necesita algo de Docket se invierte la dependencia con un registro: cada app registra su catálogo de tools del MCP (para los permisos de agentes de [0031](0031-permisos-mcp-por-agente.md)). La consulta del audit log, que filtra por proyecto, y los roles de grupos en proyectos pasan a módulos de Docket; `platform` solo guarda entradas y grupos.

## Cómo se parte

1. **Costuras.** PRs normales que quitan cada import de `platform` hacia Docket con los registros de arriba. No mueven archivos.
2. **Movimiento.** Un PR por paquete (`platform` y luego `docket`) hecho con un script que mueve archivos con `git mv` y reescribe imports. Solo renombra; ningún cambio de lógica.
3. **Regla de dependencias.** Un test que importa cada módulo y falla si `platform` importa de `docket` o `folio`, o si `folio` importa tablas de `docket`.

## Excepción al tamaño de PR

Mover un módulo que todos importan (`errors`, por ejemplo) toca casi todos los archivos del backend, así que los dos PRs de movimiento pasan de 100 archivos. Se aceptan porque:

- Las líneas cambiadas son pocas: con detección de renombres (`git diff -M`) solo cuentan las líneas de import.
- El PR incluye el script que lo generó; revisarlo es revisar el script y ver que la suite pasa.
- Dejar alias en las rutas viejas no lo evita: borrarlos después tocaría los mismos archivos otra vez.

La excepción es solo para estos dos PRs.

## Cómo se verifica

- La suite completa de Docket pasa sin tocar aserciones.
- `scripts/export_openapi.py` regenera `frontend/openapi.json` sin diff.
- `tests/mcp/test_tools.py::test_tool_catalog` sigue listando las mismas tools.
