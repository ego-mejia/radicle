# 0002. Cookie Secure automática según la URL base

- Fecha: 2026-10-18
- Estado: aceptada
- Afecta: build spec etapa 1 (modelo de datos, `sessions`)

## Contexto

El spec pide cookie de sesión `HttpOnly, Secure, SameSite=Lax`. Con `docker compose up` en local la app corre en `http://localhost:8000`, y algunos navegadores (Safari) descartan cookies `Secure` sobre HTTP, lo que rompe el login en la instalación por default.

## Decisión

`RADICLE_COOKIE_SECURE` sin valor significa automático: `Secure` se activa cuando `RADICLE_BASE_URL` empieza con `https://`. Se puede forzar con `true` o `false`.

## Consecuencias

En producción detrás de HTTPS la cookie es `Secure` sin configurar nada. En local funciona en todos los navegadores.
