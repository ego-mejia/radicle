# Radicle Folio: Build spec fase 1 (Core de publicación + MCP)

Oct 20, 2026 · @Fernando

La fase 1 entrega lo mínimo para publicar documentación real y que los agentes participen desde el día 1, con todo indexado para el RAG.

## Objetivo y entregables

Al terminar la fase 1, un equipo publica su documentación en spaces, se lee como revista o en modo enfoque, un agente propone posts que un admin aprueba, y todo lo publicado queda indexado para el RAG.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 1.1 | Spaces y árbol | Spaces de equipo y personales, páginas en árbol, folders, blog posts, orden por rank, slugs, soft delete | Creo el space AI Tools con un folder, tres páginas anidadas y un blog post; el árbol se ve en el sidebar |
| 1.2 | Editor base | TipTap con menú `/` y atajos de markdown; bloques base; imágenes, archivos y video con el storage compartido; ícono y portada | Escribo una página con todos los bloques base y se guarda como borrador sin perder nada |
| 1.3 | Publicación y versiones | Borrador y publicación con nota; metadata obligatoria; versiones inmutables; historial con comparar y restaurar | Sin descripción no se publica; restaurar la versión 1 crea la versión 4 con su contenido |
| 1.4 | Permisos | Roles globales (fase 0), permisos por space, restricciones por página heredadas | Un reader no ve el botón Escribir; una página restringida y sus hijas no aparecen para quien no tiene acceso, ni en búsqueda |
| 1.5 | Agentes y aprobación | Envíos de agentes a una cola, aprobar o rechazar con comentario, audit log | Un envío del agente aparece en la cola; al aprobarlo se publica como versión con autor el agente y aprobador el admin |
| 1.6 | RAG, búsqueda y RQL | Chunking por secciones con metadata, embeddings con pgvector, búsqueda full-text y semántica, RQL de docs | Publicar indexa en segundos; archivar o borrar saca del índice; los ejemplos de RQL regresan lo esperado |
| 1.7 | MCP de Folio | Tools de lectura, búsqueda, creación en Markdown y envío a aprobación | Claude Code conectado escribe un post a partir de un repo y queda pendiente de aprobación |
| 1.8 | UI | Home bento con layout default, home de space, lectura revista y enfoque, editor, diálogo de publicar, historial, cola de aprobación, admin de permisos y catálogos | E2E de punta a punta pasa y la UI coincide con el canvas de diseños aprobado |

## Modelo de datos

```
folio_spaces
  id
  key            citext unique             -- ^[a-z0-9][a-z0-9-]{1,39}$, va en la URL
  name, description
  kind           enum(team, personal)
  owner_id       null                      -- dueño del space personal
  icon           text null                 -- nombre de ícono o emoji
  cover_asset_id null
  created_by, created_at, updated_at, deleted_at null
  -- un solo space personal por usuario

folio_nodes                                -- todo el contenido del árbol
  id, space_id
  parent_id      null fk folio_nodes        -- null en raíz y en blog posts
  kind           enum(page, folder, blog_post)   -- fase 2 agrega live_doc; fase 3 whiteboard y database
  title          text                      -- 1 a 200
  slug           text                      -- derivado del título, no único; la URL usa id-slug
  icon           text null
  cover_asset_id null
  rank           text                      -- fractional indexing entre hermanos
  published_version_id null fk folio_versions
  published_at   timestamptz null          -- orden cronológico de blog posts
  created_by, created_at, updated_at, deleted_at null

folio_drafts                               -- borrador vivo, uno por nodo
  node_id pk
  content_json   jsonb                     -- documento TipTap
  metadata       jsonb                     -- puede estar incompleta
  base_version_id null                     -- versión de la que partió
  updated_by, updated_at

folio_versions                             -- solo inserción
  id, node_id
  number         int                       -- unique(node_id, number)
  title
  content_json   jsonb
  content_md     text                      -- derivado, para MCP y export
  content_text   text                      -- derivado, para búsqueda
  metadata       jsonb                     -- completa y validada
  change_note    text null
  author_id                                -- humano o agente
  approved_by    null                      -- admin que aprobó si el autor es agente
  restored_from  null fk folio_versions
  created_at
  -- trigger BEFORE UPDATE OR DELETE lanza excepción

folio_doc_types                            -- catálogo editable
  key pk, name, description, position, archived_at null

folio_audiences, folio_languages           -- catálogos editables, misma forma

folio_node_labels
  node_id, label                           -- pk compuesta; ^[a-z0-9][a-z0-9_-]{0,49}$

folio_space_grants
  id, space_id
  grantee_type   enum(user, group, everyone)
  grantee_id     null
  permissions    text[]                    -- view, create, comment, delete_own, delete_any, admin, export

folio_page_restrictions
  id, node_id
  mode           enum(view, edit)
  grantee_type   enum(user, group)
  grantee_id
  -- view se hereda a todos los descendientes; edit solo al nodo

folio_submissions                          -- envíos de agentes
  id, node_id
  content_json, metadata, title, change_note
  submitted_by                             -- agente
  status         enum(pending, approved, rejected, superseded)
  reviewed_by null, review_comment null
  created_at, decided_at null

folio_assets
  id, node_id null, uploader_id
  filename, mime_type, size_bytes, storage_key, width null, height null, variants jsonb
  created_at

folio_chunks                               -- índice RAG
  id, node_id, version_id
  position       int
  heading_path   text[]                    -- ["Conecta un agente", "Crea el agente"]
  anchor         text                      -- id del encabezado para el link
  text           text
  token_count    int
  metadata       jsonb                     -- copia plana para filtrar (ver sección RAG)
  embedding      vector null
  search_vector  tsvector generated
  embedded_at    null

folio_home_layouts
  id, name, layout jsonb, is_active bool, updated_by, updated_at
  -- fase 1 siembra el layout default; el editor llega en fase 3
```

Nuevos eventos de historial por nodo en `folio_node_events` (solo inserción, misma forma que `ticket_events`): `created`, `draft_saved` (agrupado por sesión de edición), `published`, `restored`, `moved`, `submitted`, `approved`, `rejected`, `restriction_changed`, `deleted`, `restored_from_trash`.

## Editor, publicación, permisos y aprobación

### Editor

- TipTap 2 con un esquema propio en `frontend/src/folio/editor/schema.ts` y su espejo en `backend/radicle/folio/services/schema.py` para validar el JSON en el servidor.
- **Bloques de fase 1:** párrafo, encabezados 1 a 4, listas, checklist simple, cita, código con lenguaje y botón copiar, tabla (celdas combinadas y color de fondo), panel (info, tip, warning, error, note), expand, status en línea, columnas (2, 3 y con barra lateral), tabla de contenido automática, árbol de hijas, imagen (tamaño, alineación, pie, zoom), archivo con vista previa de PDF, video, divisor, link y @mención de persona (sin notificar todavía).
- Menú `/` con búsqueda por nombre y alias en inglés y español. Atajos: `#`, `-`, `1.`, `[]`, ` ``` `, `>`, `---`.
- Pegar o arrastrar imágenes las sube con el selector de tamaño que ya existe en Docket.
- Autoguardado del borrador cada 2 s de inactividad, con indicador "Guardado".
- Convertidor Markdown al esquema en el servidor (`markdown-it-py`) y del esquema a Markdown, con pruebas de ida y vuelta. Lo usan el MCP y el RAG.

### Metadata obligatoria

| Campo | Regla |
| --- | --- |
| Título | 1 a 200 caracteres |
| Descripción | 40 a 400 caracteres, de 1 a 3 frases |
| Tipo de documento | Del catálogo `folio_doc_types` |
| Labels | Al menos 1, máximo 15 |
| Dueño | Usuario humano activo con acceso al space |
| Audiencia | Una o más del catálogo |
| Idioma | Del catálogo |

El servicio de publicación valida todo y regresa 422 con la lista exacta de campos faltantes. La UI los marca en el diálogo; el MCP los regresa en el error.

### Publicar y versiones

1. Publicar toma el borrador, valida esquema y metadata, crea la versión `n + 1` con `content_md` y `content_text` derivados, actualiza `published_version_id` y, en blog posts, `published_at` la primera vez.
2. Encola el reindexado RAG del nodo.
3. El historial lista versiones con autor, aprobador, fecha y nota. Comparar dos versiones muestra diff por bloques (agregado en verde, quitado en rojo) y diff de metadata.
4. Restaurar copia el contenido de una versión vieja a una nueva con `restored_from`; no borra nada.
5. Publicar con un borrador que partió de una versión vieja avisa que alguien publicó después y deja ver el diff antes de confirmar.

### Permisos

Proveedor `folio` registrado en `platform.authz`.

| Permiso | Quién lo tiene |
| --- | --- |
| Ver un nodo | Rol global reader o más, `view` en su space, y ninguna restricción de vista en él ni en sus ancestros que lo excluya |
| Crear y editar borradores | Rol creator o más y `create` en el space; si la página tiene restricción de edición, estar en ella |
| Publicar | Lo mismo que editar; agentes nunca publican directo |
| Borrar | `delete_own` para lo propio, `delete_any` para lo de otros |
| Administrar space | `admin` en el space o admin de Folio |

- Defaults al crear un space de equipo: everyone con `view`; el creador con `admin`. Space personal: solo su dueño.
- Restringir vista se hereda; la UI muestra un candado en el nodo restringido y en sus hijas.
- La visibilidad se aplica con `visible(user, "folio", ...)` en toda consulta, igual que los tickets restringidos en Docket. No visible responde 404.

### Aprobación de agentes

- Cuando un usuario `kind = agent` publica, el servicio crea un `folio_submission` en `pending` en vez de una versión. Si el nodo es nuevo, se crea sin versión publicada y no aparece para nadie más que admins y el agente.
- Un envío nuevo del mismo agente sobre el mismo nodo marca el anterior como `superseded`.
- La cola de aprobación muestra el envío como se vería publicado, el diff contra la versión actual y la metadata.
- **Aprobar** publica la versión con `author_id` del agente y `approved_by` del admin. **Rechazar** pide comentario, que el agente lee por MCP.
- Cada decisión va al audit log con `app = folio`.

## Índice RAG, búsqueda y RQL

### Chunking

- Se parte del JSON de la versión publicada, no del texto plano, para respetar la estructura.
- Un chunk por sección (encabezado y su contenido). Secciones largas se parten en trozos de 300 a 500 tokens con 50 de traslape, sin cortar tablas, bloques de código ni listas a la mitad.
- Cada chunk lleva `heading_path` y `anchor` para que una respuesta pueda citar la sección exacta.
- Tablas se serializan como Markdown; imágenes aportan su pie de foto; código se incluye con su lenguaje.
- El título y la descripción del documento se anteponen al texto de cada chunk antes de calcular el embedding.

### Metadata de cada chunk

```json
{
  "space": "ai-tools",
  "node_kind": "page",
  "doc_type": "how-to",
  "labels": ["mcp", "agentes"],
  "audiences": ["ingenieria"],
  "language": "es",
  "owner": "fernando",
  "author": "fernando",
  "version": 4,
  "published_at": "2026-10-20T16:00:00Z",
  "title": "Conecta un agente a Radicle por MCP",
  "description": "...",
  "url": "/folio/p/9f3c-conecta-un-agente#crea-el-agente",
  "restricted": false
}
```

### Indexado

- Job `folio.reindex_node(node_id)` en el worker: borra los chunks del nodo y crea los de su versión publicada en una transacción. Idempotente.
- Se encola al publicar, restaurar, mover a otro space, cambiar restricciones o labels, y borrar (que solo borra chunks).
- Embeddings en lotes con el proveedor de `platform`. Sin proveedor configurado, los chunks se guardan con `embedding` nulo y la búsqueda semántica queda deshabilitada; al configurarlo, `radicle folio reembed` calcula los faltantes.
- Índice HNSW de pgvector con distancia coseno.
- La consulta semántica siempre aplica el filtro de visibilidad del usuario antes del ranking, nunca después.

### Búsqueda

- **Full-text:** `websearch_to_tsquery` sobre título, descripción y texto, en español e inglés. Resultados con fragmento resaltado.
- **Semántica:** top 20 por embedding, agrupados por documento.
- **Híbrida (default):** combinación con Reciprocal Rank Fusion de las dos listas.
- Filtros: space, tipo de nodo, tipo de documento, label, autor, dueño, audiencia, idioma, fecha.
- En la topbar los resultados salen mientras se escribe (debounce de 150 ms).

### RQL de docs

La misma gramática y el mismo motor de Docket, con otro catálogo de campos registrado por el módulo `folio/query`.

| Campo | Ejemplo |
| --- | --- |
| `space` | `space = ai-tools` |
| `kind` | `kind = blog_post` |
| `doc_type` | `doc_type IN (how-to, guia)` |
| `label` | `label = onboarding` o `#onboarding` |
| `owner`, `author` | `owner = currentUser()` |
| `audience` | `audience = ingenieria` |
| `language` | `language = es` |
| `title`, `text` | `text ~ "mcp"` |
| `parent` | `parent = 9f3c` |
| `created`, `updated`, `published` | `published >= -30d` |

```
space = ai-tools AND doc_type = how-to AND published >= -30d ORDER BY published DESC
#onboarding AND audience = ingenieria AND language = es
kind = blog_post AND author = agente-docs
```

## API REST, MCP y UI

### Endpoints (prefijo `/api/v1/folio`)

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET, POST | `/spaces` | Spaces visibles, crear |
| GET, PATCH, DELETE | `/spaces/{key}` | Detalle con su portada, editar, borrar |
| GET | `/spaces/{key}/tree` | Árbol de nodos visibles |
| GET | `/spaces/{key}/posts?cursor` | Blog posts por fecha |
| GET, PUT | `/spaces/{key}/grants` | Permisos del space |
| POST | `/nodes` | Crear página, folder o blog post `{space, parent?, kind, title}` |
| GET | `/nodes/{id}` | Versión publicada con metadata, ícono, portada y migas |
| PATCH | `/nodes/{id}` | Título, ícono, portada |
| DELETE | `/nodes/{id}` | Soft delete |
| POST | `/nodes/{id}/move` | `{parent?, before?, after?}` dentro del space |
| GET, PUT | `/nodes/{id}/draft` | Leer y guardar el borrador `{content_json o content_md, metadata}` |
| POST | `/nodes/{id}/publish` | Publicar o, si es agente, mandar a aprobación `{change_note?}` |
| GET | `/nodes/{id}/versions` | Historial |
| GET | `/nodes/{id}/versions/{n}` | Una versión |
| GET | `/nodes/{id}/diff?from&to` | Diff por bloques y de metadata |
| POST | `/nodes/{id}/versions/{n}/restore` | Restaurar |
| GET, PUT | `/nodes/{id}/restrictions` | Restricciones de vista y edición |
| POST | `/nodes/{id}/assets` | Subir imagen o archivo |
| GET | `/submissions?status` | Cola de aprobación (admins) o mis envíos (agentes) |
| POST | `/submissions/{id}/approve`, `/reject` | Decidir `{comment?}` |
| GET | `/search?q&mode=hybrid\|text\|semantic&filters` | Búsqueda |
| GET | `/nodes?q=<rql>` | Consulta RQL |
| GET | `/metadata-schema` | Campos obligatorios y catálogos |
| GET, POST, PATCH | `/admin/doc-types`, `/admin/audiences`, `/admin/languages` | Catálogos |
| GET | `/home` | Layout activo con el contenido de cada bloque ya resuelto |
| GET | `/me/personal-space` | Space personal (se crea al primer uso) |

### MCP de Folio (`/mcp/folio`)

| Tool | Parámetros | Qué hace |
| --- | --- | --- |
| `whoami` | | Rol global y spaces con permisos |
| `list_spaces` | | Spaces visibles |
| `get_space_tree` | `space` | Árbol con ids y títulos |
| `search_docs` | `query`, `mode=hybrid`, `filters?`, `limit=10` | Resultados con título, descripción, sección y link |
| `query_docs` | `rql`, `limit=20` | Consulta RQL |
| `get_page` | `id`, `version?` | Contenido en Markdown y metadata |
| `get_metadata_schema` | | Qué se necesita para publicar |
| `create_page` | `space`, `kind`, `title`, `content_md`, `metadata`, `parent?` | Crea con borrador |
| `update_draft` | `id`, `content_md?`, `metadata?` | Reemplaza el borrador |
| `submit_for_publication` | `id`, `change_note` | Manda a aprobación (agentes) o publica (humanos con permiso) |
| `list_my_submissions` | `status?` | Estado y comentario de rechazo |
| `get_versions` | `id` | Historial |

Las descripciones de las tools explican el flujo esperado de un agente: buscar si ya existe, leer el esquema, crear o editar en Markdown, mandar a aprobación y revisar el resultado.

### UI

Todo según el [canvas de diseños](https://claude.ai/artifact/EcGroniKDdJSqb9iJ6XB6C).

| Pantalla | Detalle |
| --- | --- |
| Home | Bento con el layout default: destacado, anuncio, AI Tools, últimos posts, spaces, más leídos (por ahora los más recientes) y caja de búsqueda. Botón Escribir solo para creators |
| Space | Portada del space, sidebar con el árbol (drag para reordenar), lista de blog posts |
| Lectura | Vista revista por default; toggle de modo enfoque que recuerda cada usuario; índice de la página al lado; migas; dueño y metadata visibles |
| Editor | Pantalla completa con título, ícono y portada arriba, menú `/`, indicador de guardado y botón Publicar |
| Publicar | Diálogo con metadata (precargada del borrador), validación en vivo y nota de cambio; para agentes dice Mandar a aprobación |
| Historial | Lista de versiones y vista de diff con opción de restaurar |
| Aprobaciones | Cola con vista previa, diff y botones Aprobar y Rechazar |
| Admin | Roles globales (fase 0), catálogos de tipos, audiencias e idiomas |
| Búsqueda | Resultados híbridos con filtros y barra RQL |

## Tests

| Área | Casos mínimos |
| --- | --- |
| Esquema | El servidor rechaza JSON que no cumple el esquema; cada bloque de fase 1 valida |
| Convertidor | Ida y vuelta Markdown a documento a Markdown para cada bloque, sin pérdida en lo que Markdown puede expresar; bloques sin equivalente (panel, status, columnas) usan una sintaxis documentada de directivas |
| Árbol | Mover sin ciclos, rank entre hermanos, soft delete oculta descendientes, blog posts fuera del árbol |
| Metadata | Cada campo obligatorio faltante da 422 con su nombre, en API y MCP; catálogos archivados no se aceptan |
| Versiones | Inmutabilidad por trigger; restaurar crea versión nueva; aviso de publicación posterior; diff por bloques |
| Permisos | Matriz parametrizada de cada permiso por rol global, grant de space (usuario, grupo, everyone) y restricción de página, en API y MCP; herencia de restricción de vista; no visible da 404 |
| Fuga de restringidos | Una página restringida no aparece en árbol, búsqueda de texto, búsqueda semántica, RQL, home, MCP ni chunks; un test enumera todas las rutas GET y tools de Folio y falla si alguna no está cubierta |
| Aprobación | Agente nunca publica directo; superseded; aprobar y rechazar con audit log; el agente lee el comentario de rechazo |
| RAG | Chunks respetan secciones, tablas y código; metadata correcta en cada chunk; reindexar dos veces da el mismo resultado; borrar y archivar saca del índice; sin proveedor no truena |
| Búsqueda | Texto, semántica con proveedor simulado y fusión híbrida; filtros; visibilidad antes del ranking |
| RQL | Cada campo nuevo con sus operadores; errores con posición |
| MCP | Cada tool con caso feliz y error; flujo completo de agente: buscar, leer esquema, crear, mandar a aprobación, ver rechazo, corregir, aprobado |
| Frontend | Menú `/`, cada bloque, autoguardado, diálogo de publicar con validación, toggle de modo enfoque |
| E2E | Crear space, escribir con todos los bloques, publicar, ver en la home, editar y comparar versiones, restringir una página, aprobar el envío de un agente |
| Rendimiento | Con 5,000 páginas: búsqueda híbrida p95 menor a 400 ms; reindexar una página de 5,000 palabras en menos de 10 s con proveedor local |

## Criterios de aceptación de la fase

- [ ] Creo el space AI Tools con un folder, páginas anidadas y un blog post, y se ven en su sidebar y en la home.
- [ ] Escribo una guía con todos los bloques de fase 1 y una imagen pegada.
- [ ] Intento publicar sin descripción y no me deja; la completo y publica.
- [ ] Edito y publico dos veces más, comparo la versión 1 con la 3 y restauro la 1.
- [ ] Le doy rol creator solo al grupo equipo-docs; los demás leen pero no ven Escribir.
- [ ] Restrinjo una página a equipo-legal y desaparece para los demás, incluida la búsqueda semántica.
- [ ] Conecto Claude Code a `/mcp/folio` y le pido un post sobre los cambios de la semana en un repo; queda pendiente y lo apruebo desde la cola.
- [ ] Busco "cómo conecto un agente" y el primer resultado es la guía correcta en la sección correcta.
- [ ] Leo la guía en vista revista y en modo enfoque, en claro y oscuro.
- [ ] Docket sigue pasando todos sus tests.

## Fuera de alcance

Tiempo real, comentarios, menciones con aviso, reacciones, watch, live docs, archivar, estados y vencimiento (fase 2). Templates, editor de la home, visuales, whiteboards, databases y embeds (fase 3). Liga con Docket y chat RAG (fase 4). Integraciones externas (fase 5).
