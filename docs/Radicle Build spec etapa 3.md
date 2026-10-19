# Radicle: Build spec etapa 3 (Planeación y visibilidad)

Oct 18, 2026 · @Fernando

La etapa 3 permite planear el trabajo en sprints, verlo en el tiempo y medir si se llega a cada milestone. Todas las métricas salen del historial que existe desde la etapa 1.

## Objetivo y entregables

Al terminar la etapa 3, el equipo planea sprints, ve el roadmap en el tiempo y sabe con datos si llega a V1. Las métricas son en horas, porque la estimación es en horas.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 3.1 | Periodos de estado y snapshots | Tabla `ticket_status_periods` mantenida en cada transición y llenada desde el historial existente; job diario de snapshots | El backfill reconstruye periodos exactos desde `ticket_events`; correr el snapshot dos veces el mismo día no duplica |
| 3.2 | Boards configurables | Varios boards por proyecto, origen por proyecto o filtro RQL, columnas por estado, WIP limits suaves o duros, swimlanes, quick filters, campos de tarjeta | Un board con columna "Review" que junta In Review y QA Verified, WIP 3 que se marca en rojo al pasarse |
| 3.3 | Scrum | Sprints, backlog del board, planning con capacidad, inicio con compromiso, cierre con traspaso | Un sprint completo de inicio a cierre con lo no terminado regresando a #backlog |
| 3.4 | Timeline | Gantt de milestones y tickets con `start_date` y `due_date`, flechas de Blocks, drag para cambiar fechas, zoom | Arrastro una barra y cambian las fechas del ticket con historial; una flecha en rojo marca un conflicto |
| 3.5 | Reportes agile | Burndown, burnup, velocity, cumulative flow, control chart, sprint report | Sobre un sprint sembrado con datos conocidos, cada reporte da los números esperados |
| 3.6 | Reportes generales | Created vs resolved, distribución por campo, progreso de milestone con pronóstico, tiempo | El pronóstico de V1 coincide con el cálculo a mano y avisa "en riesgo" cuando corresponde |
| 3.7 | Dashboards | Dashboards con grid de widgets, visibilidad, dashboard default por proyecto | Armo "V1 Go to market" con progreso, bugs por área y bloqueados, y lo comparto con el proyecto |

## Modelo de datos

```
tickets (columna nueva)
  start_date         date null               -- para el timeline

ticket_status_periods
  id, ticket_id, status_id
  category           enum(todo, in_progress, done)
  entered_at         timestamptz
  exited_at          timestamptz null        -- null = estado actual
  -- se escribe en la misma transacción de cada transición
  -- índices: (ticket_id, entered_at), (status_id, entered_at)

daily_status_counts                          -- agregado diario para reportes rápidos
  date, project_id, status_id
  milestone_id null, sprint_id null
  ticket_count       int
  remaining_hours    numeric
  -- pk (date, project_id, status_id, milestone_id, sprint_id)

boards
  id, project_id null                        -- null si su origen es un filtro multi-proyecto
  name
  kind               enum(kanban, scrum)
  source_rql         text                    -- filtro base, ej. "project = PA AND area = Backend"
  columns            jsonb                   -- [{"name": "Review", "status_ids": [...], "wip_limit": 3}]
  wip_mode           enum(soft, hard) default soft
  swimlane_by        enum(none, area, assignee, priority, milestone, parent, type) default none
  card_fields        text[]                  -- campos visibles en la tarjeta
  done_window_days   int default 14
  created_by, created_at, updated_at

board_quick_filters
  id, board_id, name, rql, position

sprints
  id, board_id, name, goal
  state              enum(future, active, closed)
  start_date, end_date date
  capacity_hours     numeric null
  started_at, completed_at null
  position           int
  -- un solo sprint active por board (índice único parcial)

sprint_tickets
  sprint_id, ticket_id
  added_at, removed_at null
  added_after_start  bool
  -- un ticket está en a lo más un sprint no cerrado

sprint_commitments                           -- foto al iniciar el sprint
  sprint_id, ticket_id
  estimate_hours, remaining_hours

dashboards
  id, owner_id, name
  visibility         enum(private, project, instance)
  project_id null
  is_project_default bool default false
  created_at, updated_at

dashboard_widgets
  id, dashboard_id
  widget_type        text                    -- ver catálogo de widgets
  title, config jsonb
  layout             jsonb                   -- {"x": 0, "y": 0, "w": 6, "h": 4}
```

Nuevos eventos de historial: `sprint_added` y `sprint_removed`. Los cambios de `start_date` y `due_date` desde el timeline se registran como `field_changed` normales.

Nueva variable de entorno: `RADICLE_TIMEZONE` (ya existente) define el corte del día para snapshots, y `RADICLE_WORKDAYS` (default `mon,tue,wed,thu,fri`) define los días hábiles para burndown.

## Boards configurables

- **Varios boards por proyecto.** Al migrar, cada proyecto recibe un board Kanban "Main" equivalente al board básico de la etapa 1 (una columna por categoría).
- **Origen:** `source_rql`. Puede ser un proyecto completo, un área (`project = PA AND area = Backend`) o varios proyectos. Los tickets que el usuario no puede ver nunca aparecen.
- **Columnas:** cada una agrupa uno o más estados, de cualquier tipo de ticket. En la configuración se muestran los estados sin columna con un aviso: sus tickets no aparecen en el board.
- **Mover entre columnas:** se busca una transición válida hacia algún estado de la columna destino para el tipo de ese ticket. Una sola se ejecuta directo; varias abren un selector; ninguna hace que la columna no acepte la tarjeta. Si la transición tiene screen, validators o resolution, se abre el diálogo de transición.
- **Orden dentro de columna:** por `rank`; arrastrar dentro de la columna reordena.
- **WIP limits:** por columna. En modo `soft`, la cabecera se pone en `warning` cuando el conteo pasa el límite. En modo `hard`, mover a una columna llena regresa 409; un admin puede forzar y queda en historial.
- **Swimlanes:** filas por área, assignee, prioridad, milestone, tipo o padre. Con `parent`, los subtickets aparecen en el carril de su padre y los tickets sin padre en "Sin padre". Carriles plegables y con conteo.
- **Quick filters:** botones definidos por RQL (ej. "Solo bugs": `type = bug`). Se combinan con AND al activar varios. Vienen cuatro por default: Mis tickets, Solo bugs, #backlog y Bloqueados.
- **Tarjeta:** el admin elige qué campos se ven (key, título y tipo siempre; opcionales prioridad, assignee, tags, due, estimación, restante, checklist, votos, campos custom).
- **Columna Done:** muestra solo lo resuelto en los últimos `done_window_days` días.
- **Rendimiento:** la API regresa el board ya agrupado por columna y carril, con paginación por columna (50 tarjetas iniciales por columna).

## Scrum

Los sprints viven en boards de tipo `scrum`. Sprint y milestone son independientes: un ticket puede estar en el sprint 4 y en el milestone V1 al mismo tiempo.

### Ciclo de vida

| Estado | Qué se puede hacer |
| --- | --- |
| future | Crear, renombrar, poner fechas, meter y sacar tickets, reordenar sprints |
| active | Meter tickets (cuenta como cambio de alcance), sacar tickets, editar meta y fecha de fin, cerrar |
| closed | Solo lectura; reporte disponible |

### Reglas

- Duración entre 1 y 28 días. Fechas obligatorias para iniciar.
- Un solo sprint `active` por board.
- Un ticket está en a lo más un sprint no cerrado.
- Meter un ticket a un sprint le quita el tag #backlog (evento normal de tags).

### Planning

- Vista **Backlog** del board: arriba los sprints future y el active con sus tickets; abajo los tickets del origen del board que no están en ningún sprint y no están en Done, ordenados por rank. Un quick filter de #backlog está activo por default.
- Se arrastran tickets al sprint o se seleccionan varios y "Mover a sprint".
- Cada sprint muestra: número de tickets, suma de estimación en horas y, si tiene `capacity_hours`, una barra de capacidad que se pone en `warning` al pasarse.
- Tickets sin estimación se marcan con aviso.

### Iniciar sprint

- Pide nombre, meta, fecha de inicio y fin, y capacidad opcional.
- Guarda en `sprint_commitments` la estimación y el restante de cada ticket en ese momento. Eso es el compromiso del sprint.

### Cerrar sprint

- Muestra resumen: terminados, no terminados, agregados después de iniciar, sacados.
- Los no terminados van al siguiente sprint future (si existe y se elige) o salen del sprint y reciben #backlog (opción marcada por default).
- Al cerrar se genera el sprint report y queda guardado.

## Timeline / roadmap

Vista tipo Gantt por proyecto en `/p/{key}/timeline`, hecha a mano con React y SVG (sin librería de Gantt) para controlar el estilo y el drag.

- **Filas:** agrupadas por milestone (default) o por área. Cada grupo se puede plegar. Dentro, tickets ordenados por `start_date` y luego por rank.
- **Milestones:** rombo en su `target_date`, con línea vertical punteada y, si existe, un marcador de pronóstico (del reporte de progreso) en `warning` cuando cae después de la fecha objetivo.
- **Tickets:** barra de `start_date` a `due_date`, coloreada por categoría de estado. Con solo `due_date` se dibuja un punto. Sin fechas, el ticket va al panel lateral "Sin fechas" y se puede arrastrar al timeline para asignárselas.
- **Interacción:** arrastrar la barra mueve ambas fechas; arrastrar un borde cambia solo esa fecha. Cada cambio es un PATCH normal con historial. Clic abre el panel del ticket.
- **Dependencias:** flechas desde el bloqueador hacia el bloqueado (link Blocks). La flecha se pinta en `danger` cuando el bloqueador termina después de que el bloqueado empieza.
- **Zoom:** semana, mes y trimestre. Línea vertical de hoy. Scroll horizontal dentro del contenedor.
- **Filtros:** la misma barra RQL que la lista.
- **Rendimiento:** virtualización de filas; fluido con 1,000 tickets.

## Métricas, reportes y dashboards

### Fuente de datos

- `ticket_status_periods` da cuándo entró y salió cada ticket de cada estado. La migración de la etapa 3 lo llena recorriendo `ticket_events` en orden; después se mantiene en cada transición.
- `daily_status_counts` se llena con un job periódico de Procrastinate a las 00:05 de `RADICLE_TIMEZONE`. Es idempotente: recalcula el día y reemplaza. Un comando `radicle backfill-snapshots --from 2026-01-01` reconstruye días pasados.
- **Cycle time** de un ticket: desde la primera vez que entra a categoría in\_progress hasta la última vez que entra a done. **Lead time:** desde `created_at` hasta esa misma entrada a done.

### Reportes agile

| Reporte | Alcance | Cálculo |
| --- | --- | --- |
| Burndown | Sprint | Línea ideal: del restante comprometido a 0 a lo largo de los días hábiles. Línea real: suma de `remaining_hours` de los tickets del sprint al cierre de cada día; un ticket en done cuenta 0. Marcadores en los días con cambio de alcance |
| Burnup | Sprint o milestone | Dos líneas: alcance total en horas y horas completadas (estimación de tickets en done), por día |
| Velocity | Board, últimos N sprints | Por sprint: horas comprometidas contra horas completadas. Promedio de los últimos 3 |
| Cumulative flow | Board o proyecto, rango de fechas | Conteo diario de tickets por estado, apilado en el orden del workflow |
| Control chart | Proyecto o board, rango | Un punto por ticket resuelto con su cycle time; media móvil y percentiles 50, 85 y 95 |
| Sprint report | Sprint cerrado o activo | Terminados, no terminados, agregados después de iniciar y sacados, con horas; meta del sprint y si se cumplió (marcado manual) |

### Reportes generales

| Reporte | Cálculo |
| --- | --- |
| Created vs resolved | Por día o semana: tickets creados y resueltos, y la diferencia acumulada |
| Distribución por campo | Conteo por área, prioridad, assignee, tipo, estado, tag o campo custom select; aplica a cualquier RQL |
| Progreso de milestone | % completado por conteo y por horas, horas restantes, y pronóstico: fecha de hoy más horas restantes dividido entre el throughput (horas completadas por semana, promedio de las últimas 4). Estado "en tiempo" o "en riesgo" si el pronóstico pasa la fecha objetivo. Sin datos suficientes dice "sin pronóstico" en vez de inventar |
| Tiempo | Estimado original contra invertido por ticket, milestone, área o persona; lista de tickets que se pasaron del estimado |

Cada reporte tiene endpoint de datos en JSON, vista con Recharts y botón de exportar los datos a CSV. Respeta los permisos de quien lo ve.

### Dashboards

- Grid con react-grid-layout, widgets que se arrastran y redimensionan.
- Visibilidad privada, de proyecto o de instancia. Cada proyecto tiene un dashboard default "Resumen" que su admin puede editar.
- Los datos de cada widget se calculan con los permisos de quien lo está viendo.
- Refresco automático cada 5 minutos y botón de refrescar.

| Widget | Config |
| --- | --- |
| `filter_results` | Filtro guardado o RQL, columnas, límite |
| `count` | RQL; muestra un número grande con etiqueta |
| `distribution` | RQL y campo; pie o barras |
| `milestone_progress` | Proyecto y milestone |
| `created_vs_resolved` | RQL y periodo |
| `sprint_burndown` | Board (usa el sprint activo) |
| `cumulative_flow` | Board y rango |
| `blocked_tickets` | RQL base; lista los bloqueados con su bloqueador |
| `my_tickets` | Sin config |
| `markdown` | Texto libre |

## API REST, MCP y UI

### Endpoints nuevos

| Método | Ruta | Qué hace | Permiso |
| --- | --- | --- | --- |
| GET, POST | `/projects/{key}/boards` | Listar, crear | viewer, admin |
| GET, PATCH, DELETE | `/boards/{id}` | Config del board | viewer, admin |
| GET, POST, PATCH, DELETE | `/boards/{id}/quick-filters` | Quick filters | viewer, admin |
| GET | `/boards/{id}/data?quick_filters&swimlane&cursor` | Board agrupado por columna y carril | viewer |
| POST | `/boards/{id}/move` | `{ "ticket", "column", "before?", "after?" }` transición y rank juntos | member |
| GET, POST | `/boards/{id}/sprints` | Listar, crear | viewer, admin |
| PATCH, DELETE | `/sprints/{id}` | Editar, borrar (solo future) | admin |
| POST | `/sprints/{id}/start` | Iniciar | admin |
| POST | `/sprints/{id}/complete` | `{ "move_unfinished_to": sprint_id o "backlog", "tag_backlog": true }` | admin |
| POST, DELETE | `/sprints/{id}/tickets` | Meter o sacar tickets `{ "keys": [...] }` | member |
| GET | `/boards/{id}/backlog` | Tickets sin sprint del origen del board | viewer |
| GET | `/projects/{key}/timeline?from&to&group_by&q` | Datos del timeline | viewer |
| GET | `/reports/{type}?...` | `burndown`, `burnup`, `velocity`, `cfd`, `control_chart`, `sprint`, `created_resolved`, `distribution`, `milestone_progress`, `time` | viewer |
| GET | `/reports/{type}.csv?...` | Exportar datos | viewer |
| GET, POST | `/dashboards` | Visibles, crear | autenticado |
| GET, PATCH, DELETE | `/dashboards/{id}` | Ver, editar, borrar | según visibilidad, dueño |
| POST, PATCH, DELETE | `/dashboards/{id}/widgets[/{wid}]` | Widgets | dueño |
| GET | `/widgets/{id}/data` | Datos del widget | según visibilidad |

RQL agrega `sprint` (`sprint = active`, `sprint = "Sprint 4"`, `sprint IS EMPTY`) y `start` (fecha).

### Tools nuevas del MCP

| Tool | Parámetros | Qué hace |
| --- | --- | --- |
| `list_boards` | `project` | Boards con tipo y columnas |
| `get_board` | `board`, `quick_filters?` | Columnas con tickets resumidos y conteo contra WIP |
| `list_sprints` | `board`, `state?` | Sprints con fechas, meta y avance |
| `get_sprint` | `sprint` | Meta, tickets, horas comprometidas y restantes |
| `add_to_sprint`, `remove_from_sprint` | `sprint`, `keys` |  |
| `start_sprint`, `complete_sprint` | `sprint`, opciones | Solo admins del proyecto |
| `get_milestone_progress` | `project`, `milestone` | %, restante, pronóstico y estado |
| `get_report` | `type`, parámetros | Datos del reporte en JSON resumido para que el agente lo interprete |

### UI

| Pantalla | Detalle |
| --- | --- |
| Board | Selector de boards del proyecto; columnas configurables con conteo y WIP; carriles plegables; barra de quick filters; tarjetas con campos elegidos |
| Config de board | Editor de columnas con drag de estados entre columnas, límite WIP, modo WIP, swimlanes, campos de tarjeta, quick filters, origen RQL |
| Backlog (boards scrum) | Sprints arriba con capacidad, backlog abajo, drag entre ellos, selección múltiple, botones Iniciar y Cerrar sprint con sus diálogos |
| Timeline | Descrita arriba |
| Reportes | `/p/{key}/reports` con lista de reportes, filtros comunes (milestone, sprint, área, rango) y cada gráfica con tabla de datos plegable y Exportar CSV |
| Milestones | Cada milestone muestra pronóstico y estado en tiempo o en riesgo |
| Dashboards | `/dashboards` y `/d/{id}`; modo edición con catálogo de widgets; el proyecto muestra su "Resumen" como pestaña |

Las gráficas usan la paleta lima: acento para la serie principal, `text-muted` para la línea ideal, y los colores de categoría (gris todo, lima in\_progress, verde oscuro done) en el cumulative flow.

## Tests

Los reportes se prueban con un **fixture de historia conocida**: un proyecto sembrado con eventos de fechas controladas (con freezegun) cuyos resultados se calculan a mano y se guardan como valores esperados.

| Área | Casos mínimos |
| --- | --- |
| Periodos de estado | Backfill desde `ticket_events` igual a los periodos mantenidos en vivo; reabrir y volver a cerrar; cambio de tipo; ticket movido de proyecto |
| Snapshots | Idempotencia; cambio de día según `RADICLE_TIMEZONE`; backfill de un rango |
| Boards | Mapeo de columnas con estados de varios tipos; mover con una, varias y ninguna transición válida; WIP soft y hard; force de admin; swimlanes por cada opción; quick filters combinados; tickets no visibles nunca aparecen |
| Scrum | Máquina de estados del sprint; un solo active; un ticket en un solo sprint abierto; compromiso al iniciar; cambio de alcance; cierre con traspaso a siguiente sprint y a #backlog |
| Timeline | Fechas por drag generan historial; conflicto de dependencia detectado; tickets sin fechas |
| Reportes | Cada reporte contra el fixture: burndown ideal y real, burnup, velocity, CFD, cycle time y percentiles, sprint report, created vs resolved, distribución, pronóstico de milestone (incluido "sin pronóstico"), tiempo |
| Dashboards | Visibilidad; datos calculados con permisos del que ve (un widget compartido no filtra tickets que el viewer no puede ver) |
| Rendimiento | CFD de 1 año con 10,000 tickets en menos de 1 s; board con 500 tickets y swimlanes en menos de 1 s |
| MCP | Cada tool nueva con caso feliz y error; `get_report` regresa datos coherentes con el endpoint |
| E2E | Configurar board con columnas y WIP; correr un sprint completo; arrastrar fechas en el timeline; crear dashboard y compartirlo |

## Criterios de aceptación de la etapa

- [ ] Creo un board con columna "Review" que junta In Review y QA Verified, WIP 3, y se pone en warning al meter el cuarto.
- [ ] Activo swimlanes por área y quick filter "Solo bugs" y el board responde al instante.
- [ ] Planeo un sprint desde el backlog viendo la capacidad, lo inicio, agrego un ticket a mitad (aparece como cambio de alcance) y lo cierro mandando lo pendiente a #backlog.
- [ ] El burndown y el sprint report de ese sprint cuadran con lo que pasó.
- [ ] El timeline muestra V1 con sus tickets; arrastro una barra y cambian las fechas; una dependencia imposible se marca en rojo.
- [ ] El progreso de V1 muestra % y pronóstico; si el pronóstico pasa la fecha objetivo dice "en riesgo".
- [ ] Armo el dashboard "V1 Go to market" con progreso, bugs abiertos por área y bloqueados, y alguien del proyecto lo ve con sus propios permisos.
- [ ] Un agente consulta `get_milestone_progress` y `get_sprint` por MCP y responde bien si se llega a V1.
- [ ] Todas las reglas generales del documento de control se cumplen.

## Fuera de alcance

Buzón, grupos, permisos configurables, tickets restringidos, SSO y audit log (etapa 4). Notificaciones, suscripciones a filtros, automatización, webhooks, integraciones, plugins, import/export, móvil e IA (etapa 5). Reportes por story points no existen: todo es en horas.
