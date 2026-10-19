# 0017. Periodos de estado y snapshots diarios

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.1)

- Cada cambio de estado (crear, transicionar, cambiar de tipo, remapeo de template y mover de proyecto) cierra el periodo abierto y abre otro en la misma transacción, con el mismo instante del evento del historial. Por eso `history.record` fija `created_at` al crear el evento.
- El reconstructor (`services/period_builder.py`) es puro y lo usan la migración `0013` (con la conexión síncrona de Alembic) y `radicle backfill-periods`. Recorre los eventos `created`, `status_changed`, `status_remapped` y `moved`; recupera el tipo y el proyecto originales desde `type_changed` y `moved`. Un estado que ya no existe (renombrado o borrado) queda con `status_id` nulo y categoría `todo`.
- `daily_status_counts` se calcula desde los periodos: el estado de cada ticket al final del día en `RADICLE_TIMEZONE`. Como una llave primaria no admite nulos, "sin milestone" y "sin sprint" se guardan como el uuid cero. Milestone y restante son los actuales del ticket (el historial no guarda su valor diario); los reportes que necesitan exactitud por día (burndown) recalculan desde los eventos.
- El snapshot corre cada hora en el worker (tarea periódica de Procrastinate, minuto 5): recalcula ayer y hoy, y reemplaza. Así no depende de la zona horaria del worker y es idempotente. `radicle backfill-snapshots --from <fecha>` reconstruye días pasados.
