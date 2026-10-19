# 0025. Buzón interno

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 4 (4.3)

- El Buzón son los Drafts del proyecto con columnas nuevas en `tickets` (migración `0019`): `origin`, `classification`, `impact`, `effort`, `converted_at`, datos del remitente y `tracking_code`. Los Drafts existentes quedan como Equipo e Idea.
- La clasificación es obligatoria al crear un Draft (UI, API y MCP) y solo los Drafts la reciben al crearse; Experimento solo para el equipo. Calificar o reclasificar es parte del `PATCH /tickets/{key}` y pide `inbox.triage` en vez de `ticket.edit`.
- Pestañas: Nuevos (categoría to do), En revisión (in progress), Aprobados (`converted_at` lleno, ya como task o bug) y Descartados (draft en done sin convertir). Puntaje = impacto × 2 − esfuerzo.
- Aprobar y convertir corre en un savepoint: si el Draft está en New pasa primero por la transición a revisión, luego la transición a done con resolution `done` ("Approve"), el cambio de tipo, los campos opcionales y el evento `converted`. Cualquier error deshace todo. Las transiciones se buscan por categoría y resolution, no por nombre, para que funcione con workflows editados.
- Descartar usa la transición a done que acepta `wont_do`; el comentario para el remitente se guarda en `tickets.public_comment` (columna nueva, fuera del modelo del spec) para mostrarlo en la página de seguimiento sin abrir los comentarios internos.
- Duplicado: link `duplicates` al original, cierre con resolution `duplicate` y los votantes se insertan en el original con `ON CONFLICT DO NOTHING`, así no se repiten.
