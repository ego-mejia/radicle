# 0037. pgvector en la base y embeddings de cualquier dimensión (Folio 1.6)

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec de Folio fase 1 (entregable 1.6), `docker-compose.yml`, tests

El índice RAG de Folio guarda embeddings con pgvector. La imagen `postgres:16-alpine` que usan las instalaciones y los tests no lo trae.

## Imagen de la base

- `docker-compose.yml` construye `docker/postgres/Dockerfile`: `postgres:16-alpine` con pgvector compilado de su versión publicada. Se queda en Alpine a propósito: cambiar a una imagen Debian sobre un volumen existente cambia la libc y con ella el orden de texto, lo que puede dejar índices de texto inconsistentes. Con la misma base el volumen de cada instalación sirve sin migrar datos.
- Los tests usan `pgvector/pgvector:pg16`: siempre arrancan con una base nueva, así que la libc da igual.
- La migración que crea `folio_chunks` hace `CREATE EXTENSION IF NOT EXISTS vector`. Si la extensión no está, falla con un mensaje que dice cómo reconstruir la imagen de la base.

## Dimensión de los embeddings

Cada modelo da su propia dimensión (1536, 1024, 768...) y el admin puede cambiar de proveedor.

- La columna es `vector` sin dimensión fija y cada chunk guarda la dimensión con la que se calculó.
- El índice HNSW (distancia coseno) se crea por dimensión, sobre `embedding::vector(N)` y solo para las filas de esa dimensión, cuando el servicio de RAG ve una dimensión nueva. Las consultas usan la misma expresión para que Postgres lo aproveche.
- Alembic ignora esos índices (`ix_folio_chunks_embedding_<N>`) en `alembic check`, porque no los crea una migración.
- Cambiar de modelo deja los embeddings viejos con su dimensión; `radicle folio reembed` los recalcula y la búsqueda semántica solo compara vectores de la dimensión del modelo actual.
