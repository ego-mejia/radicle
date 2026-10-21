# 0042. Eventos públicos, webhooks, Slack y Teams, y reglas en platform

Fecha: 2026-10-21 · Estado: aceptada · Folio fase 5 (5.4, 5.5, 5.6)

## Contexto

La fase 5 de Folio pide webhooks, avisos a Slack y Teams, comandos `/radicle` y un motor de reglas, todo en `platform` para que Docket lo reuse en su etapa 5. No hay spec de Docket etapa 5 todavía, así que este ADR fija el diseño. El bus de eventos (ADR 0038) ya guarda cada evento en un outbox y el worker lo despacha.

## Decisión

**Eventos públicos.** Un evento interno (`folio.page_published`) no sale tal cual. Cada app registra un *publisher* (`events.publisher(app, type)`) que lo convierte en cero o más eventos públicos con nombre estable (`page.published`), datos que se pueden mandar afuera y un `scope` (`{"app": "folio", "space": "eng"}`) para filtrar. Los consumidores (webhooks, canales de chat, reglas) se registran con `events.subscriber` y el despacho del worker les pasa los eventos públicos en la misma transacción, así un despacho repetido no duplica nada (cada consumidor guarda su propia marca por evento).

**Webhooks.** Tablas `webhooks` (secreto cifrado con `RADICLE_SECRET_KEY`, eventos elegidos, filtro por scope) y `webhook_deliveries` (una por webhook, evento y nombre; es el log). Firma `Radicle-Signature: t=<unix>,v1=<hex HMAC-SHA256(secreto, "t.body")>`, como Stripe. Reintentos a 1 min, 5 min, 30 min, 2 h y 6 h; después queda `failed` y el admin puede reenviar. El POST pasa por `safe_fetch` (solo direcciones públicas, IP fijada, sin seguir redirects).

**Slack y Teams.** Tabla `integrations` (tipo, nombre, credenciales cifradas, y en `config` los avisos por scope y canal). Avisos con `chat.postMessage` en Slack y con el webhook entrante del canal en Teams. Comandos: Slack slash command firmado con el signing secret (`v0`), Teams outgoing webhook firmado con HMAC base64. La persona de Slack se liga por email (`users.info`); Teams no manda el email, así que la primera vez el bot responde con un link de un solo uso para ligar la cuenta en Radicle. Las identidades quedan en `integration_identities`.

**Reglas.** Tablas `automation_rules` (trigger, condiciones por scope y acciones en JSON) y `automation_runs` (log). Triggers: un evento público, o programado (cada hora o cada día) sobre lo que la app seleccione. Las acciones son de cada app (`automation.action("folio", "add_label")`); platform trae avisar a un canal y avisar a una persona. Para evitar loops, lo que hace una regla lleva su cadena de reglas en el evento que genera; una regla no corre dos veces en la misma cadena y la cadena no pasa de 3.

## Desviaciones del spec

- La vista previa de links solo es en Slack (`link_shared` + `chat.unfurl`); en Teams requiere un bot con messaging extension, fuera de alcance.
- `integration_identities` es una tabla nueva que el spec no lista.
- Los webhooks los administra el admin de la instancia, no el de cada space. Los datos que salen son ids, título, space, versión, link y handle de quien actuó, nunca contenido.

## Consecuencias

Docket solo tiene que registrar publishers y acciones para tener webhooks, avisos y reglas. Un consumidor que falla hace fallar el despacho del evento y se reintenta como cualquier evento (ADR 0038).
