# 0044. Navegación de Folio: sidebar fijo, portada del space y secciones (RAD-57)

- Fecha: 2026-10-22
- Estado: aceptada
- Afecta: la UI de Folio de las fases 1 a 3 (barra superior, home del space y lectura)

Folio usaba una barra superior y Docket un sidebar. Al cambiar de app el selector con el logo cambiaba de lugar, y dentro de una página no había forma clara de volver a la home de Folio ni de moverse entre spaces. El diseño se iteró en un canvas y se probó en un MVP navegable antes de programarlo.

## Decisión

### Sidebar fijo

- Folio tiene un sidebar a la izquierda con la misma anatomía que el de Docket: el selector de app (`SuiteSwitch`) va en la misma posición, tamaño y padding, así no se mueve al cambiar de app.
- Contenido: Inicio, Buscar, Para ti, Mis tareas, Aprobaciones (solo admins de Folio), Favoritos, la lista de spaces que la persona puede ver, Nuevo space (creators), Admin de Folio (admins) y la tarjeta del usuario.
- El sidebar nunca cambia según dónde estés: dentro de un space solo se resalta ese space. La navegación dentro del space vive en el contenido, no en el sidebar.
- En el teléfono el sidebar es un cajón que se abre con un botón de menú.

### Portada del space y secciones

- La home de un space es una portada: hero oscuro con título, descripción, páginas, carpetas y participantes (los admins se distinguen), una búsqueda limitada al space, pastillas de secciones y el contenido en bento.
- Una sección es una vista filtrada del space por tipo de documento. Cada una tiene una clave en inglés que es también su ruta (`/folio/s/$key/specs`, `/decisions`, `/guides`, `/docs`):

| Sección | Tipos de documento | Vista |
| --- | --- | --- |
| Specs (`specs`) | `build-spec` | Tabla con filtros proyecto → feature, estado y dueño |
| Decisiones de arquitectura (`decisions`) | `decision-log` | Tabla con filtros de tema, proyecto y estado |
| Guías (`guides`) | `how-to`, `guide` | Camino de primeros pasos (label `getting-started`) y guías por categoría (sus labels) |
| Documentación (`docs`) | `reference` | Un módulo por carpeta, con sus páginas |

- Las secciones son configurables por space: un admin elige cuáles se muestran y en qué orden (`folio_spaces.sections`, migración 0065; `PUT /folio/spaces/{key}/sections`). Un space sin configurar muestra las cuatro en ese orden: las pastillas del hero enseñan qué cabe en el space aunque una sección esté vacía, y una sección vacía explica cómo llenarla. La portada solo pinta tarjetas de secciones con páginas.
- `GET /folio/spaces/{key}/overview` da las páginas y carpetas que la persona puede abrir, cada sección con su conteo y los participantes por rol (admin, editor, lector; los grupos se expanden y los agentes cuentan).
- "Administrar" abre el modo admin del space: páginas, permisos, secciones y ajustes.

### Lectura

- La página muestra la ruta Space / Sección / Página con enlaces, un índice "En esta página" que sigue al encabezado visible, y anterior y siguiente dentro de la misma carpeta.

### Radi en Folio

- El botón de Radi aparece también en Folio y usa las herramientas de Folio: buscar docs, leer páginas citando la sección y crear borradores que pasan por la cola de aprobación.
- Las sugerencias de Radi dentro de una página (por ejemplo, "esta página quedó vieja") usan una tarjeta oscura propia para no confundirse con el contenido.

## Por qué

- Un solo patrón de navegación para la suite: quien usa Docket ya sabe dónde está todo en Folio.
- El sidebar con el árbol de páginas se descartó en el diseño: cambia según el space y se vuelve ruido con muchas páginas. Las secciones dejan que cada tipo de documento tenga la vista que le sirve.
- Las tablas con filtros dependientes (proyecto → feature) escalan con muchos proyectos y features sin listar todo de golpe.

## Consecuencias

- La barra superior de Folio desaparece; la búsqueda, la campana y Escribir pasan a una barra delgada sobre el contenido.
- Las secciones necesitan la configuración por space (qué secciones y en qué orden), con su migración.
- Diseño y MVP de referencia: ticket RAD-57.
