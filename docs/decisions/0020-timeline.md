# 0020. Timeline y pronóstico de milestone

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.4 y la base de 3.6)

- El Gantt está hecho a mano con React y SVG. Dos paneles: etiquetas a la izquierda y gráfica a la derecha con el scroll vertical sincronizado. Solo se dibujan las filas visibles (más un margen), así que 1,000 tickets no pesan; las flechas se dibujan si alguno de sus extremos está cerca de la vista.
- Escalas: semana 36 px por día, mes 12 y trimestre 4. Las fechas se manejan como días de calendario (sin zona horaria) para que arrastrar nunca corra un día.
- Arrastrar la barra mueve ambas fechas; un borde cambia solo esa (sin cruzar la otra). Cada cambio es un PATCH normal con `If-Match`, por eso el endpoint regresa `version` por ticket, y queda en el historial como `field_changed`. Un ticket sin fechas se arrastra desde el panel "Sin fechas" y recibe inicio en el día donde se suelta y fin dos días después.
- Conflicto de dependencia: el bloqueador termina (due, o start si no hay due) después de que empieza el bloqueado (start, o due). La flecha se pinta en `danger`.
- `start_date` sigue a `due_date` en las screens: si la screen de edición permite `due_date`, también permite `start_date`, para que las screens existentes no bloqueen el timeline.
- Pronóstico de milestone (`services/forecast.py`): restante = suma de `remaining_hours` (o la estimación) de los tickets abiertos; throughput = estimación de los tickets del milestone resueltos en las últimas 4 semanas, entre 4. Sin restante estimado o sin throughput no hay pronóstico y se dice por qué. Se usa el ritmo del propio milestone, no del proyecto entero, porque es el trabajo que se está midiendo.
- Se agregaron tokens de color para categorías (`catTodo`, `catProgress`, `catDone`) en el tema, para el timeline y las gráficas de la etapa 3.
