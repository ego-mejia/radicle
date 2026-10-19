# 0016. Filtros guardados, ranking, next_ticket y atajos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.8)

- **Filtros:** `filter = "<nombre>"` se resuelve antes de compilar la consulta: se cargan los filtros visibles con ese nombre (los propios ganan si hay dos iguales) y se compila su condición. Un filtro puede usar otro, hasta 5 niveles; uno que se usa a sí mismo da error con la posición. Un nombre que no existe no da error: no encuentra nada y regresa un aviso, igual que un área inexistente. Su `ORDER BY` no se hereda.
- Solo admins de instancia comparten filtros con toda la instancia. Los filtros de proyecto los ve cualquier miembro del proyecto. "Duplicar" en la UI es guardar el filtro actual con otro nombre.
- **Ranking:** `POST /tickets/{key}/rank` calcula una key fraccional entre los vecinos. Cuando una key llega a 24 caracteres, un job (`rebalance_ranks`, con `queueing_lock` por proyecto) reescribe todo el proyecto con keys cortas en el mismo orden.
- **next_ticket:** "el de mayor rank" es el primero del backlog, es decir el rank más bajo. La consulta se arma con RQL (`category = todo AND blocked = false AND (assignee IS EMPTY OR assignee = currentUser())`) y, con `claim`, usa `FOR UPDATE SKIP LOCKED`. Al reclamar se asigna y se ejecuta la primera transición disponible hacia una categoría in_progress, respetando las reglas. Si ninguna se puede, responde 409 y no cambia nada. Los viewers no reclaman.
- **Preferencias:** `GET` y `PATCH /me/preferences` (solo personas) guardan tema, idioma, atajos y densidad. Al cargar la app, las preferencias del servidor se aplican una vez; los cambios en el perfil se guardan en ambos lados.
- **Atajos:** `⌘K` o `Ctrl+K` siempre abre la paleta; los atajos de una tecla respetan la preferencia y no se disparan en campos de texto ni con un diálogo abierto. `j` y `k` mueven el foco entre filas y tarjetas (`[data-nav-item]`). Los atajos del ticket abierto (`e`, `a`, `m`, `l`, `p`) llegan como un evento de ventana a los componentes que controlan cada cosa.
- **Paleta:** la key exacta y los recientes siguen el texto escrito al instante. La búsqueda por título (`title ~`) espera 150 ms, así Enter justo después de escribir una key abre esa key.
