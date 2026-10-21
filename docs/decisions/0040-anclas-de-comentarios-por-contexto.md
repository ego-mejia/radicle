# 0040. Anclas de comentarios inline por texto y contexto (Folio 2.3)

- Fecha: 2026-10-21
- Estado: aceptada
- Afecta: build spec de Folio fase 2 (entregable 2.3)

El spec pide que el ancla de un comentario inline guarde posiciones relativas de Yjs y el texto citado. El editor colaborativo con Yjs (2.2) se construye en paralelo y todavía no hay Y.Doc al guardar un comentario.

## Decisión

- El ancla guarda el texto citado, hasta 32 caracteres de contexto antes y después en el texto plano de la página (`convert.to_text`) y la posición donde empezaba: `{"quote", "prefix", "suffix", "offset", "yjs": null}`.
- Cada vez que se guarda el borrador o se publica una versión, `anchors.relocate` vuelve a encontrarla: primero por el contexto de los dos lados (lo que quede entre ellos es el texto anclado, así que editar adentro conserva el comentario), luego por el texto citado más cercano a su lugar, y si no aparece o no queda nada entre el contexto, el hilo se marca huérfano y se muestra en el panel con su cita.
- `yjs` queda reservado: cuando el editor sea colaborativo, el cliente manda también las posiciones relativas y se usan primero; el contexto sigue sirviendo para la API, el MCP y las páginas sin room abierto.

## Por qué

- Los comentarios funcionan hoy, en la lectura, el editor y el MCP (que comenta sobre "la primera aparición de `quote`").
- El formato no cambia cuando llegue Yjs: se llena un campo que ya existe.
