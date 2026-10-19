# 0003. CSRF por cookie doble y endpoints de lectura para admin

- Fecha: 2026-10-18
- Estado: aceptada
- Afecta: build spec etapa 1 (API REST)

## CSRF

El spec pide `X-CSRF-Token` en mutaciones con cookie, sin decir de dónde sale. Al iniciar sesión se ponen dos cookies: `radicle_session` (HttpOnly) y `radicle_csrf` (legible por la SPA), que es un HMAC-SHA256 derivado de la sesión. El servidor no guarda estado extra: recalcula el HMAC y lo compara con el header. Con token bearer no se pide.

## Endpoints aditivos

Para que la pantalla de Admin (1.8) tenga paridad con la API se agregan dos lecturas que el spec no lista:

- `GET /api/v1/users/{handle}`: detalle de un usuario o agente.
- `GET /api/v1/users/{handle}/tokens`: tokens del usuario con prefijo, último uso y estado.

`POST /users/{handle}/tokens` solo crea tokens para agentes; los humanos crean los suyos en `/me/tokens` (422 con mensaje que lo indica). Ninguna instancia puede quedarse sin un admin activo (409).
