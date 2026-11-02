# 0046. Renombrar Radicle a Gumball Factory

Fecha: 2026-11-01 · Estado: aceptada · Fase 1 del plan de Gumball Factory

## Contexto

El proyecto deja de llamarse Radicle y pasa a llamarse Gumball Factory, porque va a ser la casa de FruitCrew (organizaciones con tickets, docs, memoria, skills y agentes). El rename va antes de cualquier trabajo nuevo para que todo nazca con el nombre correcto. No cambia el comportamiento.

Convenciones: `Gumball Factory` (marca), `gumball-factory` (repo, npm, Docker, CLI, URLs), `gumball_factory` (paquete Python, DB), `GumballFactory` (clases), `gumballFactory` (variables), `GUMBALL_FACTORY` (env vars). Docket, Folio y la mascota Radi no cambian.

## Decisión

- **R1. Paquete y CLI.** `backend/radicle` pasa a `backend/gumball_factory` y el comando `radicle` a `gumball-factory`. Las migraciones viejas solo cambian sus imports.
- **R2. Env vars.** `RADICLE_*` pasa a `GUMBALL_FACTORY_*`. Si una nueva no está, se lee la vieja y se deja un aviso en el log. Lo mismo en `docker-compose.yml` (`${GUMBALL_FACTORY_X:-${RADICLE_X:-default}}`) y en el entrypoint. Las viejas se quitan en una versión futura.
- **R3. Base y Docker.** Los defaults nuevos son `gumball_factory` (usuario, base, imagen, proyecto de compose). Una instalación existente fija los valores viejos en su `.env` (`COMPOSE_PROJECT_NAME`, `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `GUMBALL_FACTORY_IMAGE`) para que Docker no cree un volumen vacío.
- **R4. Datos sembrados.** Una migración nueva renombra al usuario system "Radicle" y a la plantilla "Radicle default". Tiene downgrade.
- **R5. Cookies.** `radicle_session` y `radicle_csrf` pasan a `gumball_factory_session` y `gumball_factory_csrf`. Nadie pierde su sesión: el servidor todavía acepta la cookie vieja y en esa misma respuesta la cambia por la nueva, y el SPA lee el CSRF con cualquiera de los dos nombres.
- **R6. MCP.** Los servidores se llaman `gumball-factory` y `gumball-factory-folio`, y los recursos `gumball-factory://`. Los clientes actualizan su config; la URL y los tokens no cambian.
- **R7. Tokens.** Se queda el prefijo `rdc_`. Cambiarlo no aporta nada y obligaría a aceptar dos prefijos.
- **R8. Historia.** Se renombran los archivos `docs/Radicle *.md`. Las entradas viejas del CHANGELOG y las ADRs anteriores conservan el nombre Radicle, porque cuentan lo que pasó.
- **R9. Carpeta local.** Al mergear se renombra la carpeta del checkout a `gumball-factory` y se migran la memoria de Claude Code y los worktrees. No es parte del código del PR.

### Lo que conserva el nombre viejo, y por qué

Compatibilidad con lo que ya existe afuera o en la base:

- **Webhooks:** cada entrega lleva `Gumball-Factory-Event`, `-Delivery` y `-Signature`, y también `Radicle-*` con los mismos valores, para que los receptores ya escritos sigan funcionando.
- **Plugins de Folio:** el bloque recibe sus datos en `window.gumballFactory` y también en `window.radicle`. La llave del plugin de ejemplo sigue siendo `radicle.countdown`, porque las páginas guardan esa llave.
- **Preferencias del navegador:** las llaves `radicle.*` de localStorage se copian una vez a `gumball-factory.*` al cargar la app.
- **Rol de base `radicle_audit_retention`:** lo usa el trigger del audit log. Renombrarlo pide tocar el trigger y no lo ve nadie.
- **Historia:** las migraciones ya aplicadas, `scripts/move_modules.py`, las entradas viejas del CHANGELOG, las ADRs anteriores, los specs de etapas y fases y `docs/progress.md` conservan su texto.

Se conservan a propósito las sales de derivación de llaves (`radicle-encryption:`, `radicle:` del signing key, `radicle-altcha:`, `radicle-sso:`, `radicle-csrf`). Cambiarlas dejaría ilegibles los secretos guardados y rompería links firmados ya compartidos. Son bytes internos, nadie los ve.

## Excepción a las reglas del PR

Este PR pasa de 500 líneas y de 100 archivos porque es un rename mecánico. Se acepta la excepción. Va en commits separados por tipo de cambio para revisarlo y revertirlo por partes.

## Consecuencias

- Hay que hacer pasos manuales: renombrar el repo en GitHub, `git remote set-url`, ajustar el `.env` de la instalación viva y la config de los clientes MCP.
- Por un tiempo conviven dos nombres de env vars y dos prefijos de token.
