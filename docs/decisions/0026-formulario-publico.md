# 0026. Formulario público y llave secreta obligatoria

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 4 (4.4)

- Las páginas `/b/{slug}` se renderizan en el servidor con Jinja (`radicle/public/`), fuera de la SPA y de `/api/v1`, con CSP estricta y sin cookies. Idioma por `Accept-Language` (inglés o español) y tema claro u oscuro por `prefers-color-scheme`. Los textos del admin (introducción y agradecimiento) se muestran como párrafos de texto plano escapado; no se interpreta markdown en la página pública.
- ALTCHA implementado en el servidor con el formato del proyecto ALTCHA (salt con expiración, número secreto, SHA-256 y firma HMAC) y un script propio de ~20 líneas que resuelve el reto con `crypto.subtle`; sin librerías ni terceros. Un reto resuelto se guarda en `used_challenges` hasta que expira, para que no se pueda reusar. Turnstile y hCaptcha se verifican contra su API con la llave secreta guardada cifrada.
- Anti-spam en este orden, todos con el mismo mensaje genérico: honeypot, tiempo mínimo de 3 s (token firmado con la hora de carga), rate limit (5 por hora y 20 por día por IP, en `inbox_submissions` con la IP como hash con sal diaria) y máximo 5 links; después los errores de campos (esos sí se dicen, porque se pueden corregir) y al final el captcha. El seguimiento tiene un límite en memoria de 20 consultas por minuto por IP.
- La descripción se guarda con markdown y HTML escapados (backslash) y saltos de línea respetados, así se ve tal cual se escribió.
- El reporter de los envíos es el usuario `inbox` de tipo `system` (no aparece en listas, no tiene tokens ni entra). Se usa `system` en vez de `agent` porque ese tipo ya existe justo para usuarios internos ocultos.
- Código de seguimiento: 10 caracteres Crockford base32 (sin I, L, O, U) = 50 bits, único en `tickets.tracking_code`.
- `RADICLE_SECRET_KEY` es obligatoria: `create_app` no arranca sin ella y Compose la exige. Cifra los secretos en la base con AES-GCM (`core/crypto.py`, prefijo `v1:`); si la llave cambia, el mensaje pide volver a capturar el secreto.
