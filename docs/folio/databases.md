# Folio: databases

Un nodo de tipo `database` guarda columnas con tipo, vistas guardadas y filas (fase 3.6). Las filas siguen los permisos del nodo: quien lo ve las lee, quien lo puede editar las escribe. Una database nunca se publica: se lee como está, igual que un live doc.

## Columnas

`{key, name, type, options}`. La `key` se genera del nombre la primera vez (`Owner` → `owner`) y ya no cambia, así que renombrar una columna no toca sus valores.

| Tipo | Valor guardado |
| --- | --- |
| `text` | texto, hasta 10,000 caracteres |
| `number` | número (entero si no tiene decimales) |
| `date` | `YYYY-MM-DD` |
| `select` | una de `options.choices[].value` |
| `multi_select` | lista de valores de `options.choices` |
| `person` | handle de una persona activa, en minúsculas |
| `checkbox` | `true` o `false` |
| `url` | link `http` o `https` |
| `page` | id de una página que quien escribe puede ver |

Las opciones de `select` y `multi_select` son `{value, color}` con color `grey`, `blue`, `green`, `yellow`, `red` o `purple`.

Cambiar el tipo de una columna convierte lo que se puede (`"12"` → `12`, una fecha en texto → fecha) y borra lo demás; la respuesta dice cuántos valores se borraron (`cleared`). Quitar una opción borra ese valor de las filas; quitar una columna borra sus valores.

## Vistas

`{id, name, kind, group_by, filters, sort, visible_columns}`:

- `kind`: `table`, `cards` o `board`. Un tablero agrupa por una columna `select` (`group_by`).
- `filters`: `[{column, op, value}]`, todos deben cumplirse. `op`: `eq`, `neq`, `contains`, `gt`, `gte`, `lt`, `lte`, `empty`, `not_empty`. En `multi_select`, `eq` y `contains` buscan el valor en la lista; en texto no distinguen mayúsculas.
- `sort`: `[{column, direction}]`, con `asc` o `desc`; los vacíos van al final. Sin orden, las filas siguen su rank (el orden en que se arrastran).
- `visible_columns`: las columnas que muestra, en orden.

El servidor aplica filtros y orden: quien lee una vista ve las mismas filas. Límites: 50 columnas, 20 vistas y 10,000 filas por database.

## Bloque en una página

Un bloque `databaseView` con `{database, view}` muestra una vista dentro de una página. Si quien lee la página no puede ver la database, el bloque dice que no tiene acceso.

## Fuera de alcance

Las filas no entran al índice de búsqueda ni al RAG en esta fase: la database aparece en el árbol y en RQL (`kind = database`), y sus filas se consultan con su vista, por la API o con la tool `query_database` del MCP.
