# 0014. Votos y tiempo invertido

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.6)

- Votar no es editar el ticket: no sube `version` (así no provoca conflictos con quien edita), pero sí deja `vote_added` o `vote_removed` en el historial.
- Solo personas votan. Como el MCP no tiene tool de voto, la API también rechaza el voto de un agente (403) para que no haya un camino distinto.
- `vote_count` y `time_spent_minutes` se actualizan con `UPDATE ... SET x = x + n` en la misma transacción del voto o del worklog; el voto usa `INSERT ... ON CONFLICT DO NOTHING`, así votos simultáneos nunca cuentan doble.
- La migración `0010` copia el `estimate_hours` existente a `original_estimate_hours` y a `remaining_hours`.
- El restante se guarda en horas con dos decimales. `remaining_hours` en un PATCH lo pasa a `manual`; `remaining_mode: "auto"` lo regresa a estimado menos invertido.
- RQL: `votes`, `spent` y `remaining` también sirven en `ORDER BY`; `spent` está en horas.
- `log_minutes` al transicionar crea el worklog antes de los validators, así `has_worklog` lo cuenta. Su descripción es "Moving to <estado>".
