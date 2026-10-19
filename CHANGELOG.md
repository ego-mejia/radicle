# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Added

- 1.1: base del monorepo, Docker Compose, CI, setup inicial, login con sesión y CSRF, usuarios, agentes, tokens personales y de agente, errores RFC 9457, pantalla de estado con tema lima e idiomas inglés y español.
- 1.2: proyectos con key, workflows default sembrados, miembros con rol, áreas y milestones, permisos por rol con 404 para no miembros.
- 1.3: tickets Task, Bug y Draft con campos fijos, checklist, menciones, colaboradores, ticket padre, versionado optimista, soft delete e historial inmutable.
- 1.4: transiciones por tipo con resolutions obligatorias en Done, cierre anticipado, reabrir, cambio de tipo y errores con las transiciones válidas.
- 1.5: links entre tickets con su inverso y aviso de bloqueado, comentarios markdown con menciones y reacciones.
- 1.6: lenguaje de queries RQL con full-text en inglés y español, errores con posición, autocompletado y seed de 10,000 tickets.
- 1.7: servidor MCP en `/mcp` con 19 tools, guía de RQL como recurso y autenticación por token de agente.
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
