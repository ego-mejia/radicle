# Ticket Tracker: Features High Level

Oct 18, 2026 · @Fernando

## Modelo

El tracker se organiza en cuatro conceptos: Proyecto, Milestone, Área y Ticket.

| Concepto | Qué es |
| --- | --- |
| Proyecto | Contenedor principal, con su key (ej. PA para ProyectoA). |
| Milestone | Entrega con fecha objetivo (ej. V1 Go to market). Agrupa lo que tiene que estar listo para esa entrega. |
| Área | Disciplina que hace el trabajo (ej. Legal, Marketing, Backend, Frontend). Lista fija definida por proyecto. |
| Ticket | Unidad de trabajo. Pertenece a un proyecto y a un área, y opcionalmente a un milestone. Puede tener un ticket padre para partirlo en subtareas. |

### Tipos de ticket

| Tipo | Uso |
| --- | --- |
| Task | Algo por hacer, en cualquier área. |
| Bug | Algo que ya existe y no funciona como debería. |
| Draft | Algo que todavía no está bien definido. |

### Tags

Los tickets pueden llevar tags y se puede filtrar por ellos. El backlog no es un tipo ni un estado: es el tag #backlog.

### Campos del ticket

| Campo | Detalle |
| --- | --- |
| Título | Resumen de una línea. |
| Assignee | Quién está haciendo el ticket. |
| Colaboradores | Más personas involucradas en el ticket. Se pueden agregar varias. |
| Descripción | Markdown. Puede incluir un checklist de tasks, cada item asignado a una persona con @. |
| Reporter | Quién creó el ticket. |
| Prioridad | Highest, High, Medium, Low, Lowest. |
| Due date | Fecha límite del ticket, independiente de la del milestone. |
| Estimación | Esfuerzo en horas. |

Ejemplo de checklist en la descripción:

```markdown
- [ ] Redactar términos y condiciones @ana
- [ ] Revisión con abogado @luis
- [x] Definir países de operación @fernando
```

### Campos custom

Campos extra definidos por proyecto, además de los fijos. Se puede filtrar por sus valores.

Tipos: texto, número, fecha, select, checkbox, persona y URL.

| Ejemplo | Dónde | Tipo |
| --- | --- | --- |
| Ambiente (Prod, Staging, Dev) | Bugs | Select |
| Versión donde se encontró | Bugs | Texto |
| País | Área Legal | Select |
| Requiere firma | Área Legal | Checkbox |
| Canal (Instagram, Email, Ads) | Área Marketing | Select |

### Links entre tickets

Relaciones entre dos tickets que no son padre-hijo.

| Link | Significado | Ejemplo |
| --- | --- | --- |
| Blocks / Is blocked by | Uno no puede avanzar hasta que el otro termine. | PA-5 Checkout está bloqueado por PA-4 API de pagos. |
| Relates to | Relacionados, sin dependencia. | PA-3 Landing page se relaciona con PA-1 Términos y condiciones. |
| Duplicates | El mismo ticket reportado dos veces. Se cierra uno y apunta al otro. |  |
| Clones | Se creó copiando otro ticket. |  |

### Comentarios

Cada ticket tiene un hilo de comentarios.

- Formato markdown, igual que la descripción.
- @menciones que notifican a la persona mencionada.
- Cada quien puede editar y borrar sus propios comentarios.
- Reacciones con emoji.

### Adjuntos

Archivos que se suben a un ticket: screenshots, PDFs, contratos, diseños, logs.

- Se pueden adjuntar al ticket o dentro de un comentario.
- Las imágenes se ven en preview sin descargarlas.
- Permite reducir el tamaño de las imágenes.
- Se pueden pegar directo (ctrl+v) o arrastrar.
- Límite de tamaño por archivo definido por el admin.
- Se guardan en el disco del servidor o en un storage tipo S3 propio.

### Watchers

Personas que siguen un ticket para recibir notificaciones de cada cambio o comentario, sin trabajar en él. El assignee y el reporter quedan como watchers automáticamente. A diferencia de un colaborador, el watcher solo observa.

### Votos

Cualquier usuario puede votar por un ticket para decir "esto me importa" o "a mí también me pasa". Sirve para priorizar: el backlog se puede ordenar por votos. Votar no suscribe ni notifica.

Se muestran con el ícono de una persona levantando la mano 🙋, no con un like.

### Historial de cambios

Registro automático de todo lo que le pasa a un ticket: quién hizo el cambio, cuándo, qué campo cambió, valor anterior y valor nuevo. Nadie lo puede editar ni borrar. Permite auditar qué hizo cada persona y cada agente.

- Luis cambió Prioridad de Medium a High, 18 oct 10:42
- Ana movió el estado de To Do a En progreso, 18 oct 11:05
- Agente-backend agregó el tag #backlog, 18 oct 12:30

### Tiempo real invertido

Registro del tiempo real que se le mete a un ticket, distinto a la Estimación. Lo registra principalmente el agente.

- **Estimado original:** lo que se calculó al inicio. Ej. 8h.
- **Worklogs:** cada quien registra lo que trabajó. Ej. "Luis, 3h, 18 oct, armé los endpoints".
- **Restante:** lo que falta. Se ajusta conforme se registra tiempo.

Muestra estimado vs real para ver qué tickets se están pasando de lo planeado.

### Clonar, mover y bulk edit

- **Clonar:** crea una copia de un ticket con sus campos. Queda ligado al original con el link Clones.
- **Mover entre proyectos:** el ticket pasa a otro proyecto y cambia su key (PA-7 pasa a PB-15). El historial se conserva.
- **Bulk edit:** se seleccionan varios tickets y se les cambia algo a todos a la vez. Ej. ponerles milestone V1 o quitarles el tag #backlog.

## Proyectos

### Templates de proyecto

Molde para crear proyectos nuevos sin configurarlos desde cero. Un proyecto existente se puede guardar como template, y al crear uno nuevo se elige el template.

- Guarda: áreas, campos custom, workflow (estados) y tags.
- Solo copia la configuración, no tickets ni milestones.
- Puede haber varios. Ej. Producto digital, Evento, Investigación.

### Configuración ligada o independiente

Se soportan las dos formas a través del template:

- **Ligado (default):** el proyecto sigue a su template. Un cambio en el template, como un estado nuevo, se aplica a todos los proyectos ligados.
- **Independiente:** el proyecto se desliga de su template para personalizarlo. Desde ahí sus cambios no afectan a otros ni le llegan los del template.

## Workflows

### Estados y transiciones

- **Estados:** las etapas por las que pasa un ticket. Ej. To Do, En progreso, En review, Done.
- **Transiciones:** qué movimientos se permiten entre estados.

El admin del proyecto puede crear estados nuevos y reglas de transición en el template.

Cada tipo de ticket tiene su propio workflow. Ej:

```
Task:   To Do → En progreso → En review → Done
Bug:    Reportado → En progreso → Verificado por QA → Done
Draft:  Nuevo → En revisión → Aprobado / Descartado
```

### Categorías de estado

Cada estado pertenece a una de 3 categorías fijas. Así reportes, filtros y agentes saben si un ticket está pendiente, en curso o cerrado sin conocer los estados de cada proyecto.

| Categoría | Significado | Ejemplos de estados |
| --- | --- | --- |
| To Do | No ha empezado | To Do |
| In Progress | Se está trabajando | En progreso, En review, Verificado por QA |
| Done | Terminado | Done, Cancelado |

### Reglas de transición

El admin las configura en el template. Son de 3 tipos:

- **Conditions:** quién o cuándo se puede mover. Ej. solo el assignee puede mover a Done.
- **Validators:** checks al momento de mover. Ej. para pasar a Done, todo el checklist tiene que estar marcado.
- **Post-functions:** acciones automáticas después de mover. Ej. al pasar a En progreso, se asigna al que lo movió.

El admin también define si un ticket bloqueado (link Blocks) solo avisa o no se puede mover.

### Resolutions

Al cerrar un ticket, además del estado se indica cómo se cerró. Distingue terminado de descartado sin crear un estado por cada caso.

| Resolution | Significado |
| --- | --- |
| Done | Se hizo. |
| Won't Do | Se decidió no hacerlo. |
| Duplicate | Era duplicado de otro ticket. |
| Cannot Reproduce | Bug que no se pudo reproducir. |

### Screens

Qué campos se piden en cada momento. El MCP le dice al agente qué campos son obligatorios en cada acción.

- **Al crear:** ej. un Bug pide Ambiente y pasos para reproducir; un Draft solo título y descripción.
- **Al editar:** qué campos se pueden modificar.
- **Al transicionar:** ej. al pasar a Done pide la resolution y el tiempo invertido.

## Agile

### Kanban board

Tablero visual con los tickets como tarjetas.

- **Columnas:** cada una es un estado o varios estados juntos.
- **WIP limits:** máximo de tickets por columna. Ej. En progreso máx 3; si se pasa se marca en rojo.
- **Swimlanes:** filas horizontales para agrupar. Ej. una por área o por assignee.
- **Quick filters:** botones para filtrar rápido. Ej. Mis tickets, Bugs, #backlog.

### Scrum

Trabajo en ciclos cortos de tiempo fijo. Es distinto al Milestone: el milestone es una entrega con fecha (V1), el sprint es el ritmo de trabajo para llegar ahí.

- **Sprint:** periodo de 1 a 4 semanas con tickets comprometidos.
- **Sprint goal:** el objetivo del sprint.
- **Planning:** se pasan tickets del backlog al sprint.
- Al cerrar el sprint, lo no terminado regresa al backlog o pasa al siguiente.

### Ranking manual

Los tickets se ordenan arrastrándolos para decir cuál va primero. Es más fino que la prioridad: entre varios tickets High, el ranking dice cuál sigue. El agente toma el de hasta arriba.

### Timeline / roadmap

Vista tipo Gantt con milestones y tickets en el tiempo, con flechas entre los tickets que tienen link Blocks.

## Búsqueda

### Lenguaje de queries

Además de la búsqueda por texto libre, un lenguaje para filtros precisos. El tool de búsqueda del MCP recibe una query así y regresa exactamente los tickets que pide el agente.

```
project = PA AND type = Bug AND priority = High AND milestone = "V1" AND tag != backlog
```

### Filtros guardados y compartidos

Una query se guarda con nombre (ej. Bugs abiertos de V1) y se comparte con el equipo. Se reusa en boards y dashboards.

### Suscripciones a filtros

Los resultados de un filtro llegan cada cierto tiempo. Ej. cada lunes a las 9am, Mis tickets vencidos por email.

## Reportes y dashboards

### Reportes agile

| Reporte | Qué muestra |
| --- | --- |
| Burndown | Trabajo restante del sprint vs días, línea ideal contra la real. |
| Burnup | Trabajo completado vs alcance total. Muestra si el alcance creció a mitad. |
| Velocity | Cuánto termina el equipo por sprint, para planear el siguiente. |
| Cumulative flow | Cuántos tickets hay en cada estado a lo largo del tiempo. Muestra cuellos de botella. |
| Control chart | Cuánto tarda un ticket de En progreso a Done (cycle time). |
| Sprint report | Qué se terminó, qué no y qué se metió a mitad del sprint. |

### Reportes generales

| Reporte | Qué muestra |
| --- | --- |
| Created vs resolved | Tickets creados vs cerrados por periodo. Muestra si se están acumulando. |
| Distribución por campo | Pie chart por área, prioridad, assignee, tipo, etc. |
| Progreso de milestone | % completado, qué falta y si se llega a la fecha. |
| Tiempo | Estimado vs tiempo real invertido por ticket o milestone. |

### Dashboards

Página configurable con widgets: gráficas, filtros guardados, conteos. Ej. un dashboard V1 Go to market con el progreso del milestone, bugs abiertos por área y tickets bloqueados.

## Automatización

### Reglas de automatización

Reglas sin código: cuando pasa X, si se cumple Y, haz Z. A diferencia de las post-functions, corren ante cualquier evento o por horario, no solo al mover un ticket de estado.

- Cuando se mergea un PR que menciona PA-4, mover PA-4 a Done.
- Cuando un ticket lleva 5 días en En review, notificar al assignee.
- Cuando se crea un Bug Highest, asignarlo al líder de Backend.
- Cuando todos los subtickets están en Done, cerrar el padre.

### Webhooks salientes

El tracker manda un POST a una URL cuando pasa algo: ticket creado, cambiado, comentado, etc. Ej. avisarle a un agente que tiene un ticket nuevo asignado para que lo tome sin estar preguntando.

## Integraciones

### REST API completa

Todo lo que se hace en la UI se puede hacer por API. El MCP se construye encima de esta API.

### Integración con Git

Si un branch, commit o PR menciona la key de un ticket, aparece ligado en el ticket. Ej. branch `PA-4-api-pagos` o commit "PA-4 agrega endpoint de cobro". Proveedores: GitHub, GitLab, Bitbucket, Gitea y Forgejo.

### Chat y docs

- **Chat (Slack, Teams, Discord):** notificaciones en un canal, crear tickets desde un mensaje y preview del ticket al pegar su link.
- **Docs:** ligar páginas de documentación al ticket.

### Plugins

Sistema de plugins para que la comunidad extienda el tracker con campos, vistas o integraciones.

### Import/export

- Subir tickets desde un CSV o exportar los resultados de un filtro.
- Importar desde Jira.

## Usuarios, permisos y admin

### Usuarios, grupos y roles

- **Usuarios:** cada persona con su cuenta. Los agentes también tienen su propio usuario y token, para que el historial diga qué hizo cada uno.
- **Grupos:** conjuntos de usuarios. Ej. equipo-backend, equipo-legal.
- **Roles por proyecto:** Admin, Member, Viewer. Una persona puede ser Admin en ProyectoA y Viewer en ProyectoB.

### Permisos por rol

Qué puede hacer cada rol: crear, editar, mover, borrar, comentar, administrar. Ej. Viewer solo lee; un agente puede crear y comentar pero no borrar.

### Tickets restringidos

Tickets que solo ve cierto grupo dentro del mismo proyecto. Ej. un ticket legal con datos sensibles que solo ve equipo-legal.

### Reglas de notificación

Quién recibe qué aviso. Ej. al comentar se notifica a assignee, reporter y watchers; al crear un Bug Highest se notifica al líder del área.

### SSO y audit log

- **SSO:** entrar con la cuenta de la empresa (Google, Microsoft, Okta).
- **Audit log:** registro de cambios administrativos, como quién cambió permisos, borró un proyecto o creó un usuario. Es distinto al historial de cada ticket.

## Notificaciones y UX

### Notificaciones

- **In-app:** campanita con los avisos del usuario: menciones, asignaciones, comentarios en tickets que sigue.
- **Email:** los mismos avisos por correo.
- **Preferencias por usuario:** qué recibir y cómo, inmediato o en resumen diario.

### Atajos y búsqueda rápida

- Atajos de teclado: `c` crea ticket, `/` busca, `j` y `k` navegan entre tickets.
- Paleta de comandos (`cmd+k`) para saltar a cualquier ticket, proyecto o acción.

### Móvil

App móvil nativa para ver y comentar tickets, con notificaciones push.

## MCP e IA

### MCP server

Funciona desde el día 1, como parte de la etapa 1. Expone todo lo definido en este documento (tickets, milestones, áreas, checklist, tiempo invertido, links, etc.) y cada agente se autentica con su propio token.

### IA dentro del tracker

No hay IA dentro del tracker por ahora. Queda para la última etapa.

## Buzón: ideas, quejas y sugerencias

Un solo espacio (en Jira está separado en Service Management y Product Discovery) donde caen:

- Ideas y experimentos que crea el equipo.
- Quejas, sugerencias e ideas que mandan los usuarios desde un lugar dedicado para eso.

El equipo los revisa, los clasifica y decide si vale la pena convertirlos en trabajo, ya sea una idea o un fix.

Cada proyecto tiene su Buzón.

- **Entrada del equipo:** se crea desde el tracker.
- **Entrada de usuarios:** formulario público, sin necesitar cuenta en el tracker.
- **Tipo:** todo entra como Draft.
- **Origen:** Equipo o Usuario.
- **Clasificación:** Idea, Experimento, Queja o Sugerencia.
- **Revisión:** el equipo lo califica y los votos 🙋 ayudan a priorizar.
- **Decisión:** si vale la pena se convierte en Task o Bug y entra al flujo normal; si no, se cierra con resolution Won't Do.

```
Equipo ─┐
        ├─► Buzón (Draft) ─► Revisión ─┬─► Task / Bug
Usuario ┘                              └─► Won't Do
```

## Etapas para el build spec

- **Etapa 1:** el core del proyecto (tickets y lo esencial para trabajarlos) y el MCP funcionando desde el día 1.
- **Última etapa:** IA, notificaciones y demás integraciones externas que no afectan la funcionalidad core.
