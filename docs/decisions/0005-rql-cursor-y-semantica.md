# 0005. Cursor de búsqueda y detalles de semántica de RQL

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 1 (RQL, Límites)

## Cursor

`GET /tickets?q=` acepta cualquier `ORDER BY` (prioridad, key, estado, fechas con nulos). Un cursor por llave compuesta para todas esas combinaciones sería frágil. El cursor es opaco pero codifica un offset; se usa igual que los demás (`next_cursor`). Con 10,000 tickets la búsqueda queda en p95 de 53 ms. Si algún día hay millones de tickets por instancia, se cambia el contenido del cursor sin cambiar la API.

La respuesta trae además `total` (cuántos tickets cumplen la query) para la UI.

## Semántica

- Cada cláusula compila a una expresión que nunca es NULL (`coalesce(..., false)`), así `!=`, `NOT IN` y `NOT` incluyen los campos vacíos, como pide el spec.
- `status = "In Progress"` compara por nombre sin mayúsculas en todos los tipos.
- `text ~` busca con `websearch_to_tsquery` en inglés y en español sobre título (peso A) y descripción (peso B).
- Fechas sin hora (`created = 2026-10-01`) cubren el día completo en `RADICLE_TIMEZONE`. `startOfWeek()` empieza en lunes.
- `m` en fechas relativas son minutos.
- Nombres de área, milestone, estado, proyecto o handle inexistentes no son error: regresan cero y un `warning` con la posición.
- Los tickets de proyectos archivados sí aparecen en la búsqueda (siguen siendo legibles).
