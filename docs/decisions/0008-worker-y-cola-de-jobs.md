# 0008. Worker y cola de jobs

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.1 y todo lo que corre en segundo plano)

## Encolar dentro de la transacción

El spec pide Procrastinate. Los jobs no se encolan con `defer_async` (que usa otra conexión), sino con un `INSERT` en `procrastinate_jobs` desde la misma sesión de SQLAlchemy (`services/queue.py`).

- Un job solo es visible para el worker cuando hace commit el cambio que lo necesita. Nunca corre antes de tiempo ni sobrevive a un rollback.
- La API no abre conexiones propias de Procrastinate; solo el worker lo hace.
- `queueing_lock` evita duplicados mientras un job igual sigue esperando (por ejemplo, la propagación de un template al mismo proyecto).

El costo es depender de las columnas de `procrastinate_jobs`, que son estables en la versión 3.

## Esquema

- La migración `0005` aplica una copia congelada del esquema de Procrastinate 3.10 (`migrations/sql/`), así la migración no cambia si se actualiza la librería. La dependencia queda fijada en `>=3.10,<4`; una versión nueva con cambios de esquema lleva su propia migración.
- El SQL se ejecuta por la conexión de asyncpg sin preparar, porque son varios comandos.
- `alembic check` ignora los objetos `procrastinate_*`.

## Procesos

- `radicle worker` (misma imagen) corre los handlers registrados con `@queue.handler`; cada job en su propia sesión y transacción.
- En docker compose el servicio `worker` arranca después de que `app` está sano y no corre migraciones (`RADICLE_MIGRATE=false`), para que dos procesos no migren a la vez.
- La tabla propia `jobs` solo guarda progreso y resultado para la UI (`GET /jobs/{id}`); la cola sigue siendo Procrastinate.

## Tests

`tests.conftest.run_jobs` saca los jobs pendientes de `procrastinate_jobs` y ejecuta sus handlers con la sesión del test, como lo haría el worker. Así se prueba el camino real de encolado.
