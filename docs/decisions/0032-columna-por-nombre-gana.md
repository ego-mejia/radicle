# 0032. Un estado elegido por nombre gana sobre su categoría en las columnas

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec etapa 3 (columnas configurables), reemplaza la regla "la primera columna que lo tiene"

Antes, un estado aparecía en la primera columna que lo cubría, por nombre o por categoría. Si alguien agregaba una columna "In Review" con ese estado después de "In Progress" (que cubre toda la categoría *in progress*), la columna nueva quedaba vacía y no se podía arrastrar nada a ella.

- Un estado elegido por nombre va a la primera columna que lo nombra, aunque una columna anterior cubra su categoría.
- Los demás estados van a la primera columna cuya categoría los cubre, como antes.
- La regla está en `resolve_columns` (backend) y en `columnIndexOf` (frontend), con tests en ambos lados.
