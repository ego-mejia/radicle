# Radicle Folio: Build spec fase 3 (Templates, home y visuales)

Oct 20, 2026 · @Fernando

La fase 3 hace que crear sea fácil y que todo se vea increíble: templates, la home editable como revista, visuales vivos y las herramientas para explicar cualquier cosa. Los diseños de referencia están en el [canvas de diseños](https://claude.ai/artifact/EcGroniKDdJSqb9iJ6XB6C).

## Objetivo y entregables

Al terminar la fase 3, el admin arma la home como revista, cualquiera crea un doc desde un template en segundos, y un post puede explicar un sistema con diagramas, gráficas y visuales animados que se ven bien en claro y oscuro, hechos por personas o por agentes.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 3.1 | Templates | Templates de página y de space, globales o por space, con variables y metadata default; panel de admin; templates incluidos, entre ellos Build spec | Creo un build spec desde su template y ya trae sus secciones y metadata |
| 3.2 | Editor de la home | Grid de 12 columnas con bloques que se arrastran y redimensionan, fuentes de datos por bloque, vista previa, publicar layout e historial | Armo la home del canvas aprobado desde el panel sin tocar código |
| 3.3 | Bloque Visual | SVG o HTML en sandbox con tokens de Radicle y modo claro u oscuro, alto automático, descripción obligatoria | El visual animado del canvas corre dentro de un post y no puede tocar la página ni la red |
| 3.4 | Suite visual | Diagramas (Mermaid), gráficas desde tabla, timeline, comparación lado a lado, fórmulas (KaTeX), lista automática por label | Cada bloque del canvas se inserta con `/` y respeta el tema |
| 3.5 | Whiteboards | Excalidraw colaborativo como tipo de nodo y como bloque incrustado | Dos personas dibujan en el mismo whiteboard y se incrusta en una página |
| 3.6 | Databases | Columnas tipadas, vistas tabla, tarjetas y tablero, filtros y orden; como nodo y como bloque | Armo el inventario de AI Tools y lo veo como tablero agrupado por estado |
| 3.7 | Embeds | Vista previa de links (OpenGraph y oEmbed) y embeds de YouTube, Figma, Loom, Google Docs y GitHub | Pego un link de Figma y se ve el embed interactivo |

## Modelo de datos

```
folio_templates
  id
  kind               enum(page, space)
  scope              enum(global, space)
  space_id null
  name, description, icon
  doc_type_key null                        -- para templates de página
  content_json null                        -- página: documento con variables {{fecha}}, {{autor}}, {{space}}, {{titulo}}
  default_metadata jsonb
  structure jsonb null                     -- space: árbol de páginas y folders con sus templates, grants y portada
  created_by, updated_at, archived_at null

folio_home_layouts (forma del layout)
  layout: { "columns": 12, "blocks": [ { "id", "type", "x", "y", "w", "h", "config" } ] }
  -- historial: cada publicación del layout es una fila nueva; is_active marca la vigente

folio_databases
  node_id pk
  columns            jsonb                 -- [{key, name, type, options}] tipos: text, number, date, select, multi_select, person, checkbox, url, page
  views              jsonb                 -- [{id, name, kind: table|cards|board, group_by?, filters, sort, visible_columns}]
folio_db_rows
  id, node_id, values jsonb, rank, created_by, updated_by, updated_at, deleted_at null

folio_link_previews
  url_hash pk, url, title, description, site_name, icon_url, image_url, provider, embed_html_allowed bool, fetched_at

folio_nodes.kind     agrega whiteboard y database
```

Los bloques Visual, diagrama, gráfica, timeline, comparación y fórmula viven dentro del JSON del documento como nodos del esquema con sus atributos; no tienen tabla propia.

## Comportamiento, API, MCP y UI

### Templates

- Al crear una página se elige template o página en blanco. Las variables se sustituyen al crear; la metadata default precarga el diálogo de publicar.
- Incluidos: Meeting notes, How-to, Decision log, Retrospectiva, Product requirements y **Build spec** (objetivo y alcance, entregables con criterios, modelo de datos, API, tests, criterios de aceptación, fuera de alcance; tipo de documento `build-spec`).
- Un template de space crea su árbol, folders, portada y permisos de una vez.
- Los edita un admin de Folio (globales) o un admin del space (los suyos) con el mismo editor.

### Editor de la home

- react-grid-layout sobre 12 columnas; en celular los bloques se apilan en el orden del grid.
- Tipos de bloque y su fuente: Destacado (un post fijo), Anuncio (post fijo con fondo lima), Lista de posts (últimos N de un space o de un label), Consulta (RQL), Para ti, Más leídos, Spaces, Texto (markdown), Caja de búsqueda y un espacio reservado para el chat de la fase 4.
- El contenido de cada bloque se calcula con los permisos de quien ve la home; un bloque que queda vacío para alguien se oculta.
- Borrador del layout con vista previa "como lo ve un reader"; publicar crea una fila nueva y conserva el historial para regresar.

### Bloque Visual: seguridad y tema

| Regla | Cómo |
| --- | --- |
| Aislado | `<iframe sandbox="allow-scripts" srcdoc="...">` sin `allow-same-origin`, así corre en un origen opaco sin acceso a cookies, storage ni al DOM de Folio. Opcionalmente servido desde `RADICLE_SANDBOX_ORIGIN` |
| Sin red | CSP inyectada: `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:` |
| Tamaño | Máximo 512 KB de código por bloque |
| Tema | El host manda por `postMessage` el modo y los tokens de Radicle; el visual los usa como variables CSS (`--rdc-bg`, `--rdc-surface`, `--rdc-text`, `--rdc-muted`, `--rdc-accent`, `--rdc-accent-fill`, `--rdc-border`) y cambia en vivo |
| Alto | El visual reporta su alto por `postMessage` y el host ajusta el iframe; tope de 2,000 px |
| Accesible | Título y descripción obligatorios para publicar; la descripción es lo que se indexa en el RAG y lo que lee un lector de pantalla |
| Movimiento | El starter incluye `prefers-reduced-motion`; el host lo propaga |

El editor del bloque es código y vista previa lado a lado, con toggle claro y oscuro, indicador de tamaño y validación de la CSP.

### Suite visual

| Bloque | Detalle |
| --- | --- |
| Diagrama | Mermaid (flujo, secuencia, estados, entidad relación, gantt) con tema Radicle; fuente editable y error legible si no compila |
| Gráfica | Barras, líneas, área y pie con Recharts, desde una tabla del documento o datos propios; toggle Gráfica y Tabla |
| Timeline | Hitos con fecha, estado y descripción en línea horizontal |
| Comparación | Dos o tres columnas lado a lado con encabezado |
| Fórmula | KaTeX en línea y en bloque |
| Lista por label | Lista viva de páginas con un label, con orden y límite |

### Whiteboards, databases y embeds

- **Whiteboard:** Excalidraw con sincronización por Yjs; tipo de nodo propio y bloque incrustable; exportar PNG y SVG; los textos se indexan.
- **Database:** CRUD de columnas y filas, vistas con filtros, orden y agrupación; incrustable con una vista elegida; filas con columna tipo página para ligar docs; se indexa como tabla Markdown.
- **Embeds:** al pegar una URL, el servidor obtiene la vista previa (timeout 5 s, protección SSRF) y la guarda en caché 24 h. Solo YouTube, Figma, Loom, Google Docs y GitHub se incrustan interactivos, en iframe con sandbox; lo demás se ve como tarjeta.

### Endpoints nuevos (prefijo `/api/v1/folio`)

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET, POST | `/templates?kind&space` | Listar, crear |
| GET, PATCH, DELETE | `/templates/{id}` | |
| POST | `/nodes/from-template` | `{template, space, parent?, title}` |
| POST | `/spaces/from-template` | `{template, key, name}` |
| GET, PUT | `/admin/home/draft` | Layout en edición |
| POST | `/admin/home/publish` | Publicar layout |
| GET | `/admin/home/history` | Layouts anteriores |
| GET, PATCH | `/databases/{node_id}` | Columnas y vistas |
| GET, POST | `/databases/{node_id}/rows?view` | Filas |
| PATCH, DELETE | `/rows/{id}` | |
| GET | `/link-preview?url` | Vista previa de un link |

### Tools nuevas del MCP

| Tool | Qué hace |
| --- | --- |
| `list_templates`, `create_from_template` | Crear docs con la estructura correcta, incluido un build spec |
| `insert_visual` | Agrega un bloque Visual con código, título y descripción después de un encabezado dado |
| `validate_visual` | Revisa tamaño, CSP, uso de tokens y descripción antes de insertarlo |
| `insert_diagram`, `insert_chart`, `insert_timeline` | Bloques de la suite desde datos |
| `query_database`, `add_database_rows` | Leer y escribir databases |

Recurso `folio://guide/visuals`: tokens, starter, reglas de sandbox y ejemplos, para que el agente genere visuales que se vean como Radicle.

### UI

| Pantalla | Detalle |
| --- | --- |
| Crear | Galería de templates con vista previa |
| Admin, Templates | Lista y editor con variables y metadata default |
| Admin, Home | Editor de grid con paleta de bloques, panel de configuración, vista previa como reader, publicar e historial |
| Editor | Nuevos bloques en `/`; editor del Visual en panel lateral |
| Whiteboard | Página completa con presencia |
| Database | Barra de vistas, filtros y botón Agregar fila |

## Tests

| Área | Casos mínimos |
| --- | --- |
| Templates | Sustitución de variables; metadata default; template de space crea árbol, folders, permisos y portada; templates archivados no aparecen |
| Home | Validación del layout (sin solapes, dentro de 12 columnas); cada fuente de datos; contenido calculado con permisos del lector; bloque vacío se oculta; historial y regresar a un layout anterior |
| Sandbox del Visual | Dentro del iframe `document.cookie` está vacío, `parent.document` lanza error, `fetch` y `XMLHttpRequest` fallan por CSP, `localStorage` no comparte con Folio; código de más de 512 KB rechazado; sin descripción no publica |
| Tema | Cambiar de claro a oscuro actualiza los tokens dentro del visual sin recargar; reduced motion se propaga |
| Suite | Mermaid válido e inválido; gráfica desde tabla del documento se actualiza al editar la tabla; KaTeX; lista por label respeta permisos |
| Whiteboard | Dos clientes sincronizan; export PNG y SVG; textos indexados |
| Database | Tipos de columna y validación; vistas con filtros, orden y agrupación; incrustado con vista elegida; indexado como tabla |
| Embeds | Proveedores permitidos incrustan; otros quedan como tarjeta; timeout; SSRF bloquea IPs privadas y metadata |
| RAG | Descripción del Visual, fuente de diagramas, datos de gráficas y filas de databases entran al índice |
| MCP | Cada tool nueva; un agente genera un visual con `validate_visual` y `insert_visual` y queda pendiente de aprobación |
| E2E | Admin arma la home del canvas; creo un build spec desde template; inserto el visual animado y lo veo en claro y oscuro |

## Criterios de aceptación de la fase

- [ ] Armo desde el panel la home del canvas aprobado y la publico; un reader ve solo lo que puede leer.
- [ ] Creo un build spec desde su template con sus secciones y metadata listas.
- [ ] Creo el space Ingeniería desde un template de space con su estructura.
- [ ] Un post con el visual animado del canvas se anima, responde a clics y cambia con el tema.
- [ ] Un agente genera un diagrama de arquitectura y un visual para un post por MCP; al aprobarlo se ven bien.
- [ ] Inserto diagrama, gráfica, timeline, comparación y fórmula desde `/`.
- [ ] Dibujamos entre dos en un whiteboard y lo incrusto en una página.
- [ ] Armo el inventario de AI Tools como database y lo veo como tablero.
- [ ] Pego links de Figma y YouTube y se ven incrustados.
- [ ] Docket sigue pasando todos sus tests.

## Fuera de alcance

Liga con Docket (smart links de tickets, tablas de tickets, build spec a tickets) y todo lo de IA (fase 4). Páginas públicas, import y export, Slack, Teams, webhooks, automatización, plugins, calendarios y analytics (fase 5).
