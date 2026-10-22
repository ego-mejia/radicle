# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Added

- Folio fase 5 (integraciones externas): páginas públicas con link revocable, exportar a PDF, Word, HTML y Markdown, importar desde Confluence, Notion, Word y Markdown con dry run, Slack y Teams (avisos por space, `/radicle search` y `/radicle ask`, vista previa de links), webhooks firmados, reglas de automatización, plugins con bloques para el editor, calendarios por space con milestones de Docket y feed iCal, y analytics con búsquedas sin resultados y el audit de Folio.
- Folio fase 4 (Docket + IA): smart links de tickets con estado en vivo, tabla de tickets por RQL, crear un ticket desde una selección o un action item, panel Docs en los tickets y milestones de Docket, build spec a tickets con checklist y bloque de avance en vivo, ligas de docs a proyectos, milestones y áreas, chat de los docs con citas a la sección exacta, IA en el editor (resumir, reescribir, sugerir metadata) con glosario, y prompts del MCP para agentes que escriben desde un codebase.
- Folio fase 3 (contenido rico): templates de página y de space (con "Equipo de ingeniería" incluido), editor de la home en un grid de 12 columnas, bloque Visual en sandbox, diagramas Mermaid, gráficas, timeline, comparación, fórmulas KaTeX, lista por label, whiteboards de Excalidraw en tiempo real, databases con vistas de tabla, tarjetas y tablero, y embeds con vista previa de links.
- Folio fase 2 (colaboración): avisos in-app y por email con preferencias, edición en tiempo real con carets y punteros con nombre, comentarios al pie e inline anclados al texto, menciones, reacciones, seguir, favoritos, compartir, action items con Mis tareas, live docs con snapshots, mover, copiar y archivar páginas, dueño y estados con vencimiento, recientes y el feed Para ti.

### Changed

- El parser, la gramática y las fechas de RQL viven en `platform/query`, compartidos por Docket y Folio.
- Screenshots del README actualizados (logo con el switch de suite, tarjetas con área y milestone) y nuevos de Folio.
- El logo es Radi: su cuadro verde con sus ojos.
- El CI de GitHub Actions queda en pausa (solo manual); los checks se corren local antes de cada push.
- Board con look de Jira, columna **In Review** en el board Main y carriles plegables con **Collapse all**.
- List: botón **Filter**, **Group by**, filtros guardados en menú y subtickets desplegables bajo su padre.
- Members: buscador para agregar personas, agentes o grupos y cambiar su rol.
- Licencia AGPL-3.0-only confirmada y archivo `LICENSE` agregado.
- Los datos de demo (`scripts/seed.py`) ahora son en inglés.

### Fixed

- Folio: importar el mismo export a otro space ya no actualiza las páginas del primero; el PDF de un doc en español sale en español; el botón Exportar de la lectura ya no se encoge; las reglas de ejemplo salen una vez; Slack muestra las negritas de `/radicle`; los bloques de plugins reciben el idioma de quien lee; crear tickets desde un doc arranca en su proyecto de Docket; el panel Docs de un ticket lista cada doc una vez.
- Folio: las respuestas del chat se guardan (antes se perdían y dejaban una conexión abierta), también si el lector se va en cuanto llegan; los tickets que crea Folio salen en el idioma del doc; la propuesta de reescritura de la IA ya no tapa los botones de comentar y crear ticket; las tareas del editor alinean su texto con la casilla; el menú ⋯ de la página muestra su icono.
- Folio: un whiteboard o una database sin elegir ya no impiden guardar el borrador en el editor en tiempo real; el iframe de un visual ya no se pinta blanco en modo oscuro y se encoge a su contenido; la vista y la columna default de una database se traducen.
- Folio: una tarea que te asignas tú mismo ya no te avisa (y los avisos de tareas dicen quién la asignó); los tipos de aviso en Perfil se traducen.

- Folio: la barra superior tapaba la barra del editor; portada vacía en las páginas; preguntas sin todas sus palabras no encontraban nada; fragmentos de búsqueda con marcas de Markdown; Editar visible pese a una restricción de edición; el tag de tipo no se veía en modo oscuro.
- E2E de etapas 1 y 3: el arrastre de tarjetas y el carril de área vuelven a pasar con los botones de área y milestone en las tarjetas.
- Board: soltar una tarjeta en Done la cierra como Done sin pedir resolución.
- My tickets y List: el encabezado de la tabla ya no se desfasa de las filas.
- Boards: un ticket en In Review o QA Verified se puede regresar al primer estado (nuevas transiciones *Back to To Do*, *Back to Reported* y *Back to New* en el template default y sus proyectos ligados), y soltar una tarjeta rápido ya no se ignora.
- Timeline: los tickets con una sola fecha se dibujan como barra, no como punto.
- CI: versión de pnpm, llave secreta para exportar el OpenAPI y conteo de archivos generados en `PR size`.
- Board: la tarjeta soltada se queda donde la sueltas (ya no regresa animada a su columna) y se puede mover de In Progress a In Review.
- Radi con modelos nuevos de OpenAI (`gpt-6.1-sol`): usa la Responses API.
- La gráfica de barras horizontal (Open by area) mostraba solo una etiqueta de cada dos.

### Added

- Folio 3.5, whiteboards: Excalidraw dibujado entre varios en tiempo real (Yjs) con presencia y punteros con nombre, exportar PNG y SVG, el texto en la búsqueda y el bloque `whiteboard` en páginas; E2E con dos personas dibujando a la vez (`e2e/suite-folio3-whiteboard.spec.ts`).
- Folio 3.6, databases: columnas tipadas, vistas de tabla, tarjetas y tablero con filtros y orden en el servidor, edición en línea, el bloque `databaseView` en páginas y las tools `query_database` y `add_database_rows`.
- Folio fase 1, la suite de documentación: spaces con árbol y blog, editor TipTap a pantalla completa con menú `/`, publicación con metadata obligatoria y versiones inmutables con diff y restaurar, roles globales, permisos por space y restricciones por página, envíos de agentes con cola de aprobación, búsqueda híbrida (texto en español e inglés y semántica con pgvector), RQL de docs, home bento, lectura revista y modo enfoque, y 12 tools en `/mcp/folio`.
- Folio fase 2 (en curso): bus de eventos con avisos en la app (SSE) y por email (SMTP), preferencias por tipo y canal; archivar, copiar y mover páginas entre spaces; estados In review, Verified y Outdated con vencimiento por space y aviso al dueño; transferir dueño; seguir, favoritos, reacciones y recientes.
- Folio: edición en tiempo real con Yjs (carets, presencia y punteros con nombre, ediciones de agentes con su etiqueta) y live docs siempre editables con snapshots cada 10 minutos, restaurar y las tools `create_live_doc` y `append_to_live_doc`; E2E con tres personas escribiendo a la vez (`e2e/suite-folio2-live.spec.ts`).
- Los límites de tools MCP por agente aplican a todas las apps, con los grupos "Folio: leer docs" y "Folio: escribir docs".
- E2E de Folio fase 1 (`e2e/suite-folio1.spec.ts`).
- Folio fase 0: el backend se parte en `platform`, `docket` y `folio` sin cambiar Docket; autorización genérica con un proveedor por app; `audit_log.app`; proveedor de IA para chat y embeddings (Admin → Settings → AI provider, con prueba de conexión); switch de suite en el logo con `g d` / `g f`; Folio en `/folio` con roles globales (Admin → Global roles), `/api/v1/folio` y `/mcp/folio` con `whoami`.
- Áreas con icono: se elige de un set de iconos SVG y se pinta con el color del área; se ve en tarjetas, carriles y timeline.
- Tarjetas del board con área, milestone y número de subtickets (campos de tarjeta `area`, `milestone` y `children`, prendidos en todos los boards); el área y el milestone se cambian desde la tarjeta.
- Crear ticket: pegar o soltar imágenes y archivos en la descripción; se suben al crear el ticket.
- MCP: tools `create_area`, `update_area`, `create_milestone` y `update_milestone` para que un agente cree, edite, archive y cierre áreas y milestones (solo admins del proyecto).
- Agentes: crear un agente (LLM o worker) desde Users y elegir con checks qué tools del MCP puede usar; el servidor MCP esconde y rechaza las demás. `GET /api/v1/mcp/tools` describe el catálogo.
- Radi, el asistente: bolita verde que sigue el cursor, chat con la guía de uso o con un LLM (Anthropic, OpenAI o compatible) configurable en la app o por `RADICLE_ASSISTANT_*`, y recorridos en pantalla que abren páginas, iluminan campos y los explican.
- Celebración de milestone: al cerrar el último ticket salen confeti, Radi y las métricas, con imagen para compartir en LinkedIn; endpoint `GET /projects/{key}/milestones/{name}/recap`.
- Destello al mover una tarjeta en el board, más brillante al llegar a Done.
- Editar nombre y descripción de proyectos; token nuevo de agente en un diálogo.
- README en inglés con guía de cada función, screenshots y diagramas; `README.es.md`; `CONTRIBUTING.md`; plantillas de PR e issues; check `PR size` (rama `tipo/descripcion`, menos de 500 líneas y 100 archivos).
- 1.1: base del monorepo, Docker Compose, CI, setup inicial, login con sesión y CSRF, usuarios, agentes, tokens personales y de agente, errores RFC 9457, pantalla de estado con tema lima e idiomas inglés y español.
- 1.2: proyectos con key, workflows default sembrados, miembros con rol, áreas y milestones, permisos por rol con 404 para no miembros.
- 1.3: tickets Task, Bug y Draft con campos fijos, checklist, menciones, colaboradores, ticket padre, versionado optimista, soft delete e historial inmutable.
- 1.4: transiciones por tipo con resolutions obligatorias en Done, cierre anticipado, reabrir, cambio de tipo y errores con las transiciones válidas.
- 1.5: links entre tickets con su inverso y aviso de bloqueado, comentarios markdown con menciones y reacciones.
- 1.6: lenguaje de queries RQL con full-text en inglés y español, errores con posición, autocompletado y seed de 10,000 tickets.
- 1.7: servidor MCP en `/mcp` con 19 tools, guía de RQL como recurso y autenticación por token de agente.
- 4.7: E2E de la etapa 4 (formulario público → Buzón → seguimiento, permisos, restringidos). Fixed: celdas de la matriz de impacto, calificaciones seguidas que chocaban por versión, slug default de keys de dos letras.
- 4.6: audit log inmutable con 39 acciones, antes y después, visor con filtros, CSV y retención configurable.
- 4.5: SSO con OpenID Connect (Authlib, PKCE), alta por dominio, liga por email verificado, sync de grupos y password apagable con salida de emergencia.
- 4.4: formulario público sin cuenta con ALTCHA, anti-spam, adjuntos y página de seguimiento; `RADICLE_SECRET_KEY` obligatoria para cifrar secretos.
- 4.3: Buzón con origen, clasificación, impacto y esfuerzo, matriz, triage, aprobar y convertir en el mismo ticket, duplicados con votos y tools MCP.
- 4.2: tickets restringidos con niveles de seguridad por proyecto y un único filtro de visibilidad en búsqueda, boards, reportes, dashboards, adjuntos y MCP.
- 4.1: grupos, rol efectivo por grupo y matriz de permisos por proyecto con una sola función de autorización en API, MCP y UI.
- 3.7: dashboards con diez widgets, visibilidad privada, de proyecto o de instancia, datos con los permisos de quien ve, modo edición con drag y resize, y un Resumen por proyecto.
- 3.5 y 3.6: reportes agile y generales con gráficas, tabla, CSV y tools MCP `get_report` y `get_milestone_progress`; pronóstico en milestones.
- 3.4: timeline (Gantt) con milestones, pronóstico, drag de fechas, dependencias en rojo y tickets sin fechas; `start_date` editable.
- 3.3: Scrum con sprints, backlog con capacidad, compromiso al iniciar, cierre con traspaso y reporte guardado; RQL `sprint` y `start`; tools MCP de sprints.
- 3.2: varios boards por proyecto con origen RQL, columnas por estado o categoría, WIP suave o duro, swimlanes, quick filters, campos de tarjeta y pantalla de configuración.
- 3.1: periodos de estado por ticket reconstruidos del historial y mantenidos en vivo, snapshots diarios y comandos de backfill.
- 2.8: filtros guardados y `filter =` en RQL, ranking manual con drag, `next_ticket` atómico para agentes, preferencias, atajos de teclado y paleta ⌘K.
- 2.7: clonar con opciones, mover entre proyectos con alias de la key vieja, edición masiva con dry run y jobs con progreso.
- 2.6: votos 🙋, worklogs, estimado original y restante automático o manual, RQL de tiempo y votos, tools MCP de tiempo.
- 2.5: adjuntos en disco o S3 con detección por contenido, EXIF borrado, reducción de imágenes, variantes, URLs firmadas, pegar y arrastrar en la UI y tools MCP.
- 2.4: screens por tipo y operación con esquema de formulario en API, MCP y UI; campos obligatorios y de solo lectura validados igual en todos los canales.
- 2.3: reglas de transición (conditions, validators y post-functions del catálogo), política de bloqueo avisar o impedir con forzado para admins.
- 2.2: templates con propagación a proyectos ligados por el worker, mapeo de estados borrados, desligar, guardar proyecto como template y editor de workflows con diagrama.
- 2.1: worker de jobs en segundo plano (Procrastinate, servicio `worker`), campos custom de 7 tipos por proyecto con RQL `cf.<key>`, en API, MCP y UI.
- 1.8: UI web completa: board con drag and drop, lista con RQL, detalle de ticket, settings, admin, perfil, tema lima claro y oscuro, inglés y español.
