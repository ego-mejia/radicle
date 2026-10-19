# 0018. Boards configurables

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.2)

- Una columna guarda `status_ids` y además `categories`. El board "Main" que crea la migración `0014` (y cada proyecto nuevo) usa categorías: así sigue igual al board de la etapa 1 aunque el workflow gane estados, y sirve para boards con varios proyectos, cuyos estados son distintos por proyecto. Un estado cae en la primera columna que lo tiene.
- El origen es RQL y se compila con los permisos de quien ve el board, junto con los quick filters activos (AND) y el filtro extra `q` de la barra de filtros. Lo que el usuario no ve nunca aparece.
- `POST /boards/{id}/move` busca las transiciones del ticket que llegan a algún estado de la columna. Una se ejecuta; varias piden `transition`; ninguna da 422. Si la transición necesita resolution, comentario o screen, la UI abre el diálogo de transición antes de llamar a `move`. El rank va en la misma transacción.
- WIP duro: se cuenta la columna con el origen del board (sin quick filters). Pasarse da 409 `wip_limit_reached` con `can_force` para admins; forzar deja `wip_forced` en la nota del evento.
- Swimlanes: la API regresa cada tarjeta con su `lane` y la lista de carriles en orden; la paginación sigue siendo por columna (50 tarjetas).
- Desviación: el editor de columnas usa casillas de estados y categorías por columna en vez de drag entre columnas; es accesible con teclado y el aviso de estados sin columna es el mismo. Los campos custom en la tarjeta (`cf.<key>`) se aceptan por API y se pintan, pero el editor solo ofrece los campos fijos.
