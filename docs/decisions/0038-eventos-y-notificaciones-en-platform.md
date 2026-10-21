# 0038. Eventos y notificaciones en platform (Folio 2.1)

- Fecha: 2026-10-21
- Estado: aceptada
- Afecta: build spec de Folio fase 2 (entregable 2.1); Docket etapa 5 usará lo mismo

El spec de Folio fase 2 pide el bus de eventos y las notificaciones "según el spec de Docket etapa 5 pero en `platform`". Ese spec todavía no existe, así que el diseño queda aquí y Docket lo adopta cuando llegue su etapa 5.

## Bus de eventos

- `events_outbox`: cada app registra un evento (`app`, `type`, `actor_id`, `payload`, `occurred_at`) con `platform.services.events.emit(db, ...)` dentro de la misma transacción del cambio. Si el cambio hace rollback, el evento desaparece.
- `emit` también encola el job `platform_dispatch_events` (con `queueing_lock`, así ráfagas de eventos no apilan jobs). El worker procesa el outbox en orden, con `SELECT ... FOR UPDATE SKIP LOCKED`, y marca `dispatched_at`. Un worker detenido no pierde nada: al volver, el job (o el barrido periódico) recoge lo pendiente.
- Cada app registra **resolvers** por tipo de evento: dado el evento, devuelven quién debe enterarse (`user_id`, `reason`) y el texto y link del aviso. Platform no sabe de páginas ni tickets; aplica las reglas comunes: nunca al actor, nunca a usuarios inactivos, y la app ya filtró por visibilidad.
- `event_deliveries` guarda una fila por (evento, usuario, canal) con su estado. La clave única impide duplicados aunque el despacho se repita.

## Canales

- **In-app:** `notifications` (usuario, app, tipo, título, cuerpo, link, `read_at`). `GET /api/v1/me/notifications`, `POST /api/v1/me/notifications/read` y `GET /api/v1/me/notifications/stream` (SSE). El stream escucha `LISTEN radicle_notifications` en Postgres; al insertar una notificación el despacho hace `NOTIFY` con el id del usuario, así funciona con varios procesos de la app sin otro broker.
- **Email:** SMTP configurado por variables (`RADICLE_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_FROM`, `_TLS`). Sin SMTP el canal se apaga y las preferencias lo muestran deshabilitado. El envío es un job por entrega con reintentos; un error permanente queda en la entrega con su mensaje.
- **Preferencias:** `notification_preferences` por usuario, tipo y canal (`in_app`, `email`), con default por tipo que define la app. `users.timezone` y `users.digest_hour` quedan para el resumen diario (fase posterior); se agregan ya porque son parte del esquema.

## Por qué así

- El outbox en la misma base evita perder eventos sin agregar Kafka ni Redis, y Procrastinate ya corre como worker.
- LISTEN/NOTIFY alcanza para SSE en una instalación self-hosted; si algún día hace falta otro broker, solo cambia la capa del stream.
