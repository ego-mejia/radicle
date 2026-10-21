# Radicle Folio: Features high level

Oct 20, 2026 · @Fernando

## Contenido y estructura

| Feature | Detalle |
| --- | --- |
| Spaces | Contenedor de más arriba por equipo, área o proyecto (ej. Ingeniería, AI Tools, RRHH). Cada space tiene su portada, permisos, árbol de páginas y blog posts. |
| Páginas en árbol | Páginas que cuelgan de otras sin límite de niveles (ej. Get Started > Instalación > Windows). El árbol se ve en el sidebar como índice navegable. |
| Folders | Agrupan páginas sin tener contenido propio. |
| Blog posts | Entradas con fecha y autor, ordenadas cronológicamente y fuera del árbol. Sirven para noticias, anuncios o posts de documentación. Las noticias no son obligatorias: desde el panel de admin la home puede ser puro contenido de documentación. |
| Live docs | Documentos colaborativos siempre editables, sin borrador ni publicación. Para minutas de reunión, dailies y notas. En el space personal funcionan como cuaderno propio. |
| Whiteboards | Lienzo infinito y colaborativo con figuras, sticky notes, flechas y marcos. |
| Databases | Tablas con columnas tipadas (texto, persona, fecha, select) y vistas de tabla, tarjetas y tablero. |
| Embeds y Smart Links | Una URL pegada se muestra como vista previa (Figma, YouTube, Google Docs). Los tickets de Radicle se muestran como smart links nativos con estado y assignee en vivo. |
| Space personal | Cada usuario tiene su propio space para borradores y notas. |
| Archivar | Páginas y spaces salen del árbol y de la búsqueda sin borrarse, y se pueden restaurar. Lo archivado sale del índice del RAG. |
| Mover, copiar y reordenar | Reordenar con drag en el árbol, mover a otro space y copiar con o sin páginas hijas. |

Cualquier página o post se puede ligar a tickets, milestones o áreas de Radicle Tickets. Es opcional, nunca obligatorio.

## Editor

| Feature | Detalle |
| --- | --- |
| Editor visual con `/` | Menú con `/` para insertar bloques y atajos de markdown al escribir (`#`, `-`, ` ``` `, `>`). Se ve el resultado, no markdown crudo. |
| Bloques | Tablas con celdas combinadas y color, paneles (info, warning, success, error, nota), expand, código con resaltado y botón de copiar, status en línea, tabla de contenido automática, layouts en columnas y árbol de páginas hijas. |
| Imágenes, archivos y video | Subir, pegar o arrastrar. Imágenes con tamaño, alineación, pie de foto y zoom; PDFs con vista previa; videos con reproductor. |
| Edición colaborativa en tiempo real | Varias personas editando a la vez, tipo Figma: se ve literalmente el cursor del mouse de cada persona moviéndose en tiempo real, con su nombre y color, además de su posición en el texto. |
| Borrador y publicación | Los cambios no se ven hasta publicar, y al publicar se puede escribir qué cambió. Sin metadata y descripción no se puede publicar. |
| Ícono y portada | Emoji o ícono y una imagen de portada por página. La portada es la que aparece en las tarjetas de la home bento. |

## Templates

| Feature | Detalle |
| --- | --- |
| Templates de página | Estructura prellenada al crear una página: títulos, secciones, textos guía y variables como fecha y autor. Globales o solo de un space. Se editan desde el panel de admin. |
| Templates de space | Estructura inicial al crear un space: páginas default (ej. Get Started, FAQ, Glosario), folders, portada, permisos y templates de página disponibles. Ej. Space de equipo, Space de proyecto, Knowledge base. |

Templates de página que vienen incluidos:

| Template | Contenido |
| --- | --- |
| Meeting notes | Asistentes, agenda, notas y action items |
| How-to | Objetivo, requisitos y pasos numerados |
| Decision log | Contexto, opciones, decisión y quién decidió |
| Retrospectiva | Qué salió bien, qué salió mal y acciones |
| Product requirements | Objetivo, alcance, historias y preguntas abiertas |

**Build spec:** tipo de documento para especificar lo que se va a construir. Si a partir de él se generan tickets en Radicle Tickets, cada ticket queda ligado al build spec como su referencia.

## Colaboración

| Feature | Detalle |
| --- | --- |
| Comentarios | Al pie para la conversación general, con hilos y respuestas. Inline sobre un texto seleccionado, que queda resaltado y anclado aunque se edite; si el texto se borra, el comentario queda marcado como huérfano. Resolver oculta el hilo pero queda en el historial. |
| @menciones | @persona en una página o comentario notifica con link directo a ese punto. |
| Reacciones | Emojis en páginas, blog posts y comentarios. En un blog post el conteo se ve en su tarjeta. |
| Watch | Seguir una página avisa cuando la editan o comentan; seguir un space avisa de todo lo nuevo que se publica. El autor sigue su página automáticamente. |
| Compartir | Manda el link con un mensaje a personas o grupos. Si no tienen acceso, quien comparte se lo puede dar solo si sus permisos lo dejan. |
| Action items | Checklist dentro de la página con @persona y fecha límite. Cada persona ve los suyos en Mis tareas. Un action item se puede convertir en ticket de Radicle. |

## Historial y calidad

| Feature | Detalle |
| --- | --- |
| Historial de versiones | Cada publicación crea una versión con autor, fecha y nota de qué cambió. Se puede abrir cualquier versión, comparar dos (verde lo agregado, rojo lo quitado) y restaurar una vieja; restaurar crea una versión nueva sin borrar las demás. |
| Dueño | Persona responsable de que la página esté al día. Puede ser distinta del autor y se puede transferir. |
| Estado | Draft, In review, Verified u Outdated. Una página Verified puede tener vencimiento (ej. 90 días); si nadie la revisa pasa sola a Outdated y se avisa al dueño. |
| Analytics de página | Vistas totales y únicas, quién la leyó y cuándo, y ranking de páginas más leídas por space. |
| Labels | Etiquetas libres que agrupan páginas de distintos spaces. Se filtra y busca por label, y un bloque lista solas las páginas con cierto label. |

## Búsqueda y navegación

| Feature | Detalle |
| --- | --- |
| Búsqueda full-text | Busca en títulos, contenido, comentarios y texto de adjuntos. Resultados con el fragmento resaltado. Filtros por space, autor, tipo (página, blog post, live doc, whiteboard, database), fecha, label y estado. Resultados mientras se escribe en la barra de arriba. |
| Lenguaje de queries | RQL extendido para docs, el mismo lenguaje de Radicle Tickets. Ej. `space = ING AND label = onboarding AND updated > -30d AND status = verified`. |
| Recientes | Lo último que el usuario vio o editó. |
| Favoritos | Páginas y spaces marcados con estrella. |
| Feed "Para ti" | Actividad de los spaces que el usuario sigue y lo más leído por su equipo. La home bento puede tener un bloque con este feed. |

## Permisos

| Feature | Detalle |
| --- | --- |
| Permisos globales | Aplican a toda la instancia de Docs: quién es admin de Docs, quién puede crear spaces y quién puede tener space personal. Por default todos son read only y solo un grupo selecto crea y edita. |
| Permisos por space | Por persona o grupo en cada space: ver, crear páginas y blog posts, comentar, borrar lo propio, borrar lo de otros, administrar el space y exportar. Es el scope de área o grupo de docs. |
| Restricciones por página | Limitar quién ve o edita una página en particular, aunque el space diga otra cosa. Restringir quién la ve aplica también a sus páginas hijas. Es el scope de un solo post. |
| Páginas públicas o externas | Compartir una página o un space completo con gente sin cuenta, por link público. |
| Grupos | Los mismos usuarios y grupos de Radicle Tickets: una sola base de usuarios (personas y agentes) y cada suite con sus propios permisos. Los usuarios de Tickets se agregan a grupos de Docs sin volver a crearlos. |

## Integraciones

| Feature | Detalle |
| --- | --- |
| Integración con Tickets | Tickets pegados se ven como smart links con estado en vivo. Bloque de tabla de tickets por RQL que siempre está actualizado (ej. `milestone = "V1" AND type = bug`). Seleccionar texto y crear un ticket ligado a la página. Desde el ticket se ve qué páginas lo mencionan. |
| REST API y webhooks | API completa igual que Tickets, y webhooks salientes cuando se publica, edita, comenta o archiva una página. |
| Plugins | El mismo sistema de plugins de Tickets. En Docs el uso principal son bloques nuevos para el editor. |
| Exportar e importar | Exportar una página o un space completo a PDF, Word, HTML o Markdown. Importar desde Word, Markdown, Notion y desde un export de Confluence. |
| Slack y Teams | Avisos en un canal cuando se publica algo en un space, preview al pegar el link de una página y búsqueda de docs desde el chat (`/radicle search onboarding`). |

## Automatización

El mismo motor de reglas de Tickets, con triggers de Docs: página publicada, editada, comentada, cambio de estado y programado. Ejemplos:

- Al publicar en el space Anuncios, avisar al canal #general.
- Si una página Verified no se edita en 6 meses, marcarla Outdated y avisarle al dueño.
- Al crear una página con label incident, crear un ticket de postmortem ligado.

## IA

| Feature | Detalle |
| --- | --- |
| Resumir | Resumen de una página larga. |
| Escribir con IA | Generar o reescribir texto dentro del editor. |
| Preguntas y respuestas | Chat sobre todos los docs que responde citando las páginas de donde sacó la respuesta (RAG). |
| Glosario automático | Al pasar el cursor por un término interno muestra su definición sacada de los docs. |

## MCP

| Feature | Detalle |
| --- | --- |
| MCP desde el día 1 | Un agente (ej. Claude) se conecta por MCP y puede buscar, leer, crear y editar páginas y posts. Tiene su propia cuenta o, si ya existe, solo se le dan permisos. |
| Posts desde el codebase | El agente puede escribir posts a partir del codebase y sus cambios. |
| Aprobación del admin | Lo que un agente crea por MCP (documentos, posts, etc.) no se publica hasta que un admin lo aprueba. |

## Admin

| Feature | Detalle |
| --- | --- |
| Audit log | Igual que en Tickets: quién cambió permisos, borró un space o aprobó un post de un agente. |
| Analytics del sitio | Spaces más activos, contenido más leído, usuarios activos y búsquedas sin resultados, que muestran qué documentación falta. |
| Look and feel | Panel del admin para acomodar la home bento. Cada space puede tener su propia portada dentro de la paleta de Radicle. |
| Calendarios de equipo | Calendarios compartidos por space para vacaciones, releases, eventos u on-call, con vista de mes y semana. Pueden mostrar los milestones de Tickets y suscribirse desde Google Calendar u Outlook. |

## Lo nuestro

Lo que Confluence no trae. El diseño de los puntos visuales está aprobado en el [canvas de diseños](https://claude.ai/artifact/EcGroniKDdJSqb9iJ6XB6C).

| Feature | Detalle |
| --- | --- |
| Home tipo revista (bento) | Portada tipo sitio de noticias con bloques de distintos tamaños: destacado, anuncios, Get Started, últimos posts, feed Para ti, más leídos y chat con los docs. El admin los arrastra y redimensiona desde su panel y elige qué alimenta cada uno: un post fijo, los últimos N de un space, un label o un RQL. Diseño aprobado. |
| Metadata obligatoria | Para publicar: título, descripción de 1 a 3 frases, tipo de documento, al menos un label, dueño, audiencia e idioma. La IA puede sugerir descripción y labels, pero una persona confirma. La metadata viaja con los embeddings para filtrar el RAG. |
| Visuales animados e interactivos | Bloque Visual que acepta SVG o HTML como los artifacts: animaciones, hover, clics, pasos. Usa la paleta de Radicle y el modo claro u oscuro, corre aislado en sandbox y un agente lo puede generar por MCP. Diseño aprobado. |
| Suite de herramientas visuales | Bloques nativos: diagramas, gráficas desde una tabla, timeline, comparación lado a lado, fórmulas, paneles y whiteboard incrustado. Diseño aprobado. |
| Tickets desde un build spec | Se seleccionan entregables o secciones y se crea un ticket por cada uno, con sus criterios de aceptación como checklist y link a la sección exacta. El build spec muestra el estado de esos tickets en vivo. |
| Switch de suite | Clic en el logo abre un dropdown con Tickets y Docs. Misma sesión y mismos usuarios, sin volver a entrar. Diseño aprobado. |
| Vistas de lectura | Reemplazan el ancho de página de Confluence. Dos vistas aprobadas: revista (portada, columna centrada e índice de la página al lado) y modo enfoque (columna angosta, barra de herramientas mínima y comentarios al margen). La vista de docs en 3 columnas se descartó. |
