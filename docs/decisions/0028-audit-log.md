# 0028. Audit log inmutable

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 4 (4.6)

- Tabla `audit_log` (migración `0022`) con actor, tipo de actor, acción, objetivo, proyecto, `details` (JSONB con `before` y `after` cuando aplica), IP y user agent. Índices por fecha, actor, acción y proyecto.
- Inmutabilidad en la base: un trigger rechaza `UPDATE`, `DELETE` y `TRUNCATE` con el error "audit_log is append-only". La única excepción es el rol de base `radicle_audit_retention` (sin login, creado por la migración y concedido al usuario de la app); el job de retención hace `SET LOCAL ROLE` dentro de su transacción, así que el permiso no sale de ahí.
- El catálogo de acciones vive en `services/audit.py` (`ACTIONS`, 39 acciones); `audit.record` rechaza una acción fuera del catálogo y nunca guarda secretos (el client secret de SSO, tokens y passwords no entran en `details`).
- La entrada se escribe en la misma transacción que el cambio; si el cambio se revierte, la entrada también. El login fallido es la excepción: se hace commit antes de responder el error.
- IP y user agent se toman de un middleware ASGI que los deja en un `contextvar`, así los servicios no reciben el request.
- Lectura: admin de instancia ve todo; admin de proyecto ve solo las entradas de los proyectos que administra; cualquier otro recibe 403. Filtros por actor, prefijo de acción (`user` → `user.*`), proyecto y fechas, paginación por cursor y export CSV con los mismos filtros.
- Retención con `RADICLE_AUDIT_RETENTION_DAYS` (default 730) y un job periódico diario (`audit_retention`, 03:30).
