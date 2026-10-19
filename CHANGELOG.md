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
- 2.6: votos 🙋, worklogs, estimado original y restante automático o manual, RQL de tiempo y votos, tools MCP de tiempo.
- 2.5: adjuntos en disco o S3 con detección por contenido, EXIF borrado, reducción de imágenes, variantes, URLs firmadas, pegar y arrastrar en la UI y tools MCP.
- 2.4: screens por tipo y operación con esquema de formulario en API, MCP y UI; campos obligatorios y de solo lectura validados igual en todos los canales.
- 2.3: reglas de transición (conditions, validators y post-functions del catálogo), política de bloqueo avisar o impedir con forzado para admins.
- 2.2: templates con propagación a proyectos ligados por el worker, mapeo de estados borrados, desligar, guardar proyecto como template y editor de workflows con diagrama.
- 2.1: worker de jobs en segundo plano (Procrastinate, servicio `worker`), campos custom de 7 tipos por proyecto con RQL `cf.<key>`, en API, MCP y UI.
- 1.8: UI web completa: board con drag and drop, lista con RQL, detalle de ticket, settings, admin, perfil, tema lima claro y oscuro, inglés y español.
