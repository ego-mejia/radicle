# 0011. Reglas de transición

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.3)

- Las reglas viven en `transition_rules` y viajan en la configuración del workflow (`transitions[].rules`), así llegan igual por template o por el editor de un proyecto independiente.
- El catálogo se valida al guardar: tipo conocido, `kind` correcto y parámetros completos. Los campos de `field_required`, `set_field` y `clear_field` son `priority`, `area`, `milestone`, `assignee`, `due_date`, `estimate_hours`, `description_md`, `parent` o `cf.<key>`.
- `GET /tickets/{key}/transitions` solo regresa las transiciones cuyas conditions pasan. Con `include_unavailable=true` regresa todas con `available` y `reasons`. También dice `requires_comment` para que la UI pida el comentario.
- Si la transición existe pero una condition la impide, la respuesta es 409 `transition_unavailable` con el motivo, en vez del genérico "transición no permitida".
- Los validators fallidos responden 409 `transition_rules_failed` con `failed_rules: [{rule, message}]`. Todos los que fallan se reportan juntos.
- Las post-functions reutilizan la edición normal de tickets, con las mismas validaciones e historial y el mismo actor. Si una falla (por ejemplo, `set_field` con un área que no existe), se deshace todo, incluido el cambio de estado.
- El `comment` de la petición siempre se guarda como comentario, haya o no `comment_required`.
- `add_comment` reemplaza `{actor}` (como `@handle`), `{from}` y `{to}`; cualquier otra llave queda tal cual.
- Política de bloqueo `enforce`: un ticket bloqueado no entra a in_progress ni done (409 `ticket_blocked` con `can_force`). Un admin puede mandar `force=true`; el evento guarda `forced: true` y la respuesta trae el aviso `forced`. `force` también salta la condition `not_blocked`, no las demás.
- `has_worklog` usa `tickets.time_spent_minutes`, columna que agregó la migración `0007` y que llenan los worklogs del 2.6.
