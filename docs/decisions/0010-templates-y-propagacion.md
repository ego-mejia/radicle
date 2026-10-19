# 0010. Templates y propagación

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.2)

## Proyectos sin template

`POST /projects` sin `template_id` usa el template "Radicle default" (id fijo, creado en la migración `0006`) en modo ligado. Así un proyecto nuevo se comporta igual que los existentes, que la migración ligó a ese template como pide el spec. El template default no se puede archivar.

## Un solo motor

Crear un proyecto desde template, propagar un cambio y guardar el editor de un proyecto independiente usan el mismo código (`services/template_sync.py`), que compara por `ref`. Aplicarlo dos veces con la misma configuración no cambia nada.

## Mapeos de estados

- `status_mappings` acepta la forma del spec, `{"in_review": "in_progress"}` (vale para cualquier tipo donde se quite ese ref), y también `{"task": {"in_review": "in_progress"}}` por tipo, porque un mismo ref (`done`, `in_progress`) existe en varios tipos.
- Al editar el template, el mapeo es obligatorio solo para estados que tienen tickets en algún proyecto ligado. Sin tickets se borran sin preguntar.
- Si entre el guardado y la propagación entra un ticket a un estado borrado sin mapeo, va al estado inicial de su tipo. El evento `status_remapped` lo deja claro.
- Un ticket que llega a un estado Done por mapeo queda con resolution `done` si no tenía una.

## Usuario system

Los cambios de la propagación los firma el usuario `system` ("Radicle"), un tipo de usuario nuevo (`user_kind = system`). No puede iniciar sesión ni tener tokens, y no aparece en listas de usuarios ni cuenta para el setup inicial. En un proyecto independiente, el `status_remapped` lo firma el admin que guardó el workflow.

## Tags del template

Los tickets no tienen una lista de tags por proyecto, así que los tags del template se guardan en `projects.suggested_tags` para autocompletado. No se agregan a tickets.

## Errores y reintentos

Cada proyecto se sincroniza en su propio job y en un savepoint: si falla, la corrida queda `failed` con el error y se puede reintentar (`POST /templates/{id}/sync-runs/{run}/retry`). Las demás corridas siguen. Una corrida para un proyecto que ya se desligó termina como `succeeded` sin cambios.

## Editor

Las reglas de transición (2.3) y las screens (2.4) viajan en la misma configuración. El editor de workflows es un componente compartido entre el template y los proyectos independientes. El diagrama usa Mermaid, que se carga solo cuando se muestra.
