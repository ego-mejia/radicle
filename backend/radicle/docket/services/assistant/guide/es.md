## Primeros pasos
Radicle es un ticket tracker para personas y agentes de IA. El menú de la izquierda tiene Projects, My tickets, Dashboards y, para admins, Admin. Presiona `?` para ver todos los atajos de teclado y `⌘K` (o Ctrl+K) para abrir la paleta de comandos.

## Crear un proyecto {#create-project}
Ve a **Projects** y da clic en **Create project**. Ponle nombre y una key corta de 2 a 10 mayúsculas o dígitos, como PAY: cada ticket la lleva de prefijo (PAY-12) y no se puede cambiar después. Elige un template: **Linked** sigue recibiendo sus cambios, **Independent** lo copia una vez. Luego agrega **Areas** y **Milestones** en **Settings** del proyecto. Solo los admins de instancia crean proyectos.

## Editar un proyecto
En **Projects**, pasa el cursor sobre una tarjeta y da clic en el lápiz para cambiar el nombre o la descripción. La key nunca cambia. Pueden editarlo los admins del proyecto y de la instancia.

## Archivar un proyecto {#archive-project}
Radicle no borra proyectos, así que sus tickets e historial nunca se pierden. Para retirar uno, un admin del proyecto abre **Settings → General** y da clic en **Archive**: el proyecto sigue visible pero queda de solo lectura. **Unarchive**, en el mismo lugar, lo reactiva.

## Áreas y milestones {#milestones}
Las **Areas** dividen un proyecto por parte del producto, como Backend o Mobile; cada tarea y bug pertenece a una. Los **Milestones** son metas con fecha objetivo opcional, como un release, y están abiertos o cerrados. Los tickets apuntan a un milestone; **Timeline**, **Reports → Milestone progress** y los dashboards muestran cuánto avanza cada uno. Adminístralos en **Settings → Areas** y **Settings → Milestones** del proyecto.

## Agregar gente a un proyecto {#add-people}
Abre **Settings → Members** del proyecto. Usa el buscador para encontrar personas, agentes o grupos, elige un rol y da clic en **Add**. Roles: **Viewer** ve y vota, **Member** trabaja tickets, **Admin** además administra miembros, configuración y permisos. Cambia el rol de alguien con el menú de su fila o quítalo con la ×. Un admin de instancia crea a las personas nuevas en **Admin → Users**.

## Grupos
En **Admin → Groups** crea un grupo (por ejemplo legal-team) y agrega gente. Luego agrega el grupo a un proyecto en **Settings → Members** con un rol: todos sus integrantes entran, también quien se sume después. Si alguien tiene varios roles, vale el más alto.

## Crear un ticket {#create-ticket}
Presiona `c` o da clic en **Create ticket**. Tipos: **Task** (trabajo por hacer), **Bug** (algo roto) y **Draft** (una idea sin decidir, que va al Buzón). Tasks y bugs necesitan área. La descripción es markdown; las líneas como `- [ ] paso` se vuelven checklist.

## Trabajar un ticket
Abre un ticket para cambiar su estado con el botón de estado, asignarlo, poner prioridad, área, milestone, fechas y estimado, tags, colaboradores y ticket padre. Abajo están los adjuntos, subtickets, links (blocks, relates to, duplicates), comentarios con @menciones y el historial. **Log time** registra horas trabajadas. El menú ⋯ lo clona, lo mueve a otro proyecto o lo borra.

## Estados y workflows
Cada tipo de ticket tiene su workflow. Las tasks van To Do → In Progress → In Review → Done; los bugs, Reported → In Progress → QA Verified → Done. Desde In Review (o QA Verified) puedes regresar al inicio. Algunos movimientos piden resolution, comentario o checklist completo. Los admins editan los workflows en **Settings → Workflows**.

## Board
**Board** muestra los tickets como tarjetas en columnas: To Do, In Progress, In Review y Done. Arrastra una tarjeta a otra columna para cambiar su estado, o arriba y abajo para ordenarla; queda donde la sueltas. Si el movimiento necesita más datos, un diálogo te los pide. Los quick filters (My tickets, Only bugs, #backlog, Blocked) y la barra de filtros acotan el board.

## Carriles {#swimlanes}
Divide el board en filas con el selector de carriles (swimlanes): por área, asignado, prioridad, milestone, padre o tipo. Da clic en el encabezado de una fila para ocultarla o mostrarla, o usa **Collapse all**. Radicle recuerda qué filas ocultaste.

## Configurar un board
Los admins dan clic en **Configure** en el board. El origen es una query RQL, así un board puede cubrir un área o varios proyectos. Las columnas agrupan estados por categoría o por nombre; un estado nombrado en una columna va ahí aunque otra columna cubra su categoría. Pon límites WIP (suave pone la columna en rojo, duro bloquea), campos de tarjeta y quick filters. **New board** crea otro; un board tipo Scrum agrega sprints.

## Lista y filtros {#list-filters}
**List** muestra los tickets en una tabla. Da clic en **Filter** arriba de la tabla para filtrar por tipo, estado, prioridad, asignado, área o milestone; cada filtro aparece como chip que puedes quitar. **Group by** divide las filas en grupos plegables. Los tickets con subtickets tienen una flecha para desplegar sus tasks y bugs. **Saved filters** guarda las queries que reusas.

## Buscar con RQL
RQL es el lenguaje de búsqueda de la barra, List, boards y filtros. Ejemplos: `type = bug AND priority >= high`, `assignee = currentUser() AND category != done`, `text ~ "checkout" AND updated >= -7d`, `sprint = active`. Combina con AND, OR, NOT y paréntesis, y ordena con ORDER BY. Los errores se subrayan con lo que se esperaba.

## Sprints y backlog
Crea un board Scrum y abre **Backlog**. Da clic en **New sprint**, pon objetivo, fechas y capacidad, y arrastra tickets adentro. **Start sprint** fija el compromiso; **Complete sprint** regresa lo no terminado al backlog o al siguiente sprint y guarda el reporte.

## Timeline
**Timeline** dibuja los tickets en el tiempo por milestone o área. Arrastra una barra para mover sus fechas o un borde para cambiar una. Un ticket con solo fecha límite se ve con una barra tenue desde que se creó. Arrastra tickets de **Without dates** al timeline para darles fechas. Las dependencias imposibles se ponen en rojo.

## Reportes
**Reports** tiene burndown, burnup, velocity, cumulative flow, control chart, sprint report, creados vs resueltos, distribución, progreso de milestone y tiempo. Cada uno trae su tabla de datos y **Export CSV**.

## Dashboards
**Dashboards** junta widgets que acomodas arrastrando: conteos, distribuciones, progreso de milestone, burndown, bloqueados, resultados de filtros y notas. Compártelo contigo, con un proyecto o con todos; cada quien ve solo los tickets que puede ver. Cada proyecto tiene su dashboard **Summary**.

## Buzón y formulario público
El **Inbox** (Buzón) junta Drafts: ideas del equipo, de agentes y de gente sin cuenta. Activa el formulario público en **Settings → Inbox** y comparte `/b/<slug>`. Califica cada entrada con Impacto y Esfuerzo, revisa la **Matrix** y luego **Approve and convert** a task o bug, **Mark duplicate** o **Discard** con una nota. Quien lo mandó lo sigue con un código.

## Permisos
En **Settings → Permissions** los admins prenden o apagan cada permiso para members y viewers: crear, editar, mover y borrar tickets, comentarios, adjuntos, tiempo, votos, links y más. Los botones desaparecen para quien no tiene el permiso, y la API y los agentes siguen la misma regla.

## Tickets restringidos
En **Settings → Levels** crea un nivel de seguridad (como Legal confidential) y elige los grupos o personas que lo pueden ver. Pon un ticket en ese nivel con el candado del ticket; nadie más lo encontrará en ningún lado.

## SSO
En **Admin → SSO** agrega un proveedor OpenID Connect (Google, Microsoft, Okta, Keycloak...) con su issuer, client ID y secret. Los dominios permitidos crean cuentas solas y el mapeo de grupos los mantiene sincronizados. **Admin → Settings** puede apagar la entrada con password; el primer admin siempre puede entrar con password.

## Audit log
**Admin → Audit log** lista los cambios administrativos: quién, cuándo, desde qué IP y qué cambió. Filtra por persona, acción, proyecto y fechas, y exporta a CSV. Los admins de proyecto ven lo de sus proyectos en **Settings → Audit log**. Nadie lo puede editar ni borrar.

## Agentes de IA y MCP {#agents}
Los agentes son usuarios para herramientas de IA. En **Admin → Users** da clic en **New user** y elige **Agent (LLM or worker)**, o usa **Admin → Agents**. Copia el token: se muestra una sola vez. Agrega el agente a un proyecto en **Settings → Members** y conecta tu cliente MCP a `/mcp` con el header `Authorization: Bearer <token>`. Con Claude Code: `claude mcp add --transport http radicle <url>/mcp --header "Authorization: Bearer <token>"`.

## Permisos de MCP de un agente
Cada agente se puede limitar a algunas tools de MCP. Usa **MCP permissions** en el agente, en Admin → Users o Agents: deja **All tools**, elige **Read only** o marca tools una por una. Las apagadas desaparecen para ese agente. Los permisos del proyecto siguen aplicando.

## Atajos de teclado
`?` muestra todos los atajos. `c` crea un ticket, `/` busca, `⌘K` abre la paleta, `g p` va a proyectos, `g m` a mis tickets, `j` y `k` se mueven en listas y boards. En un ticket: `e` edita el título, `a` te lo asigna, `m` lo mueve, `l` tags, `p` prioridad. Puedes apagar los atajos en tu perfil.

## Perfil, idioma y tema
Da clic en tu nombre abajo a la izquierda para abrir tu perfil: cambia tu nombre, password, idioma (inglés o español) y tus tokens personales de API. El botón de la luna arriba cambia entre modo claro y oscuro.

## Radi, el asistente {#radi}
Radi es la bolita verde abajo a la derecha. Dale clic para preguntar cómo usar Radicle. Un admin de instancia puede conectar un LLM en **Admin → Settings → Assistant** (Anthropic o cualquier servidor compatible con OpenAI, como Ollama); sin LLM, Radi responde con esta guía.
