# 0021. Reportes

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.5 y 3.6)

- Un solo endpoint `GET /reports/{type}` (y `.csv`) con los mismos parámetros para todos: `project`, `board`, `sprint`, `milestone`, `q`, `from`, `to`, `field`, `interval`, `by`. Cada reporte regresa `columns`, `rows` (la tabla y el CSV) y `summary` (las cifras clave, lo que lee el agente con `get_report`). El servicio vive en `services/reports/` (común, agile y generales).
- Permisos: el alcance se resuelve con los permisos de quien ve (proyecto o board) y solo cuentan los tickets que puede ver. Por eso el CFD sale de `ticket_status_periods` filtrados por visibilidad y no de `daily_status_counts`, que no sabe de permisos. Para que sea rápido, la base agrupa los periodos por (estado, día de entrada, día de salida) y los días se llenan con una suma acumulada: un año de 10,000 tickets tarda decenas de milisegundos.
- Burndown exacto por día: el restante de un ticket en un momento se reconstruye del historial. Para eso, todo cambio de `remaining_hours` queda como `field_changed`, también cuando es efecto de cambiar la estimación o de registrar tiempo. Un ticket en done cuenta 0. La línea ideal va del restante comprometido a 0 en los días hábiles (`RADICLE_WORKDAYS`). Los tickets que salen del sprint al cerrarlo siguen contando en su burndown.
- Burnup, velocity y tiempo usan la estimación actual de cada ticket (el historial guarda los cambios pero el spec mide "horas completadas" con la estimación vigente).
- Cycle time: de la primera entrada a in_progress a la última entrada a done; lead time: de la creación a esa entrada. Percentiles por rango más cercano.
- Para probar con fechas conocidas, `utcnow()` lee un reloj del módulo `db.models.base` que los tests reemplazan (fixture `clock`), en vez de agregar freezegun, que choca con el event loop de asyncio.
- El seed ahora escribe un historial de estados creíble (eventos y periodos), así el demo y la prueba de rendimiento tienen datos para los reportes.
