# Radicle: Build spec etapa 4 (Buzón y control de acceso)

Oct 18, 2026 · @Fernando

La etapa 4 abre Radicle a usuarios externos con el Buzón y a equipos más grandes con grupos, permisos configurables, tickets restringidos, SSO y audit log.

## Objetivo y entregables

Al terminar la etapa 4, cualquier usuario de un producto puede mandar quejas, sugerencias o ideas sin cuenta, el equipo las revisa y decide en el Buzón, y el admin controla con detalle quién ve y hace qué.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 4.1 | Grupos y permisos por rol | Grupos, miembros por grupo en proyectos, matriz de permisos configurable por proyecto, servicio único de autorización | La matriz parametrizada de tests pasa para cada permiso, rol y canal (UI, API, MCP) |
| 4.2 | Tickets restringidos | Niveles de seguridad por proyecto, filtro de visibilidad único aplicado en todo el sistema | Un ticket restringido no se filtra por búsqueda, board, links, hijos, reportes, dashboards, adjuntos ni MCP |
| 4.3 | Buzón interno | Campos Origen, Clasificación, Impacto y Esfuerzo; vista Buzón; matriz; triage; conversión a Task o Bug | Un Draft se califica, se aprueba y queda como Bug en el mismo ticket con su origen preservado |
| 4.4 | Formulario público | Página pública por proyecto, anti-spam con ALTCHA, adjuntos limitados, código y página de seguimiento | Una queja enviada sin cuenta aparece en el Buzón y el usuario ve su estado con el código |
| 4.5 | SSO | OIDC con Authlib, varios proveedores, alta automática por dominio, mapeo de grupos | Login con Google o Keycloak crea al usuario en el grupo correcto |
| 4.6 | Audit log | Registro inmutable de acciones administrativas, visor con filtros, exportar CSV | Cada acción del catálogo deja su entrada y nadie la puede modificar |
| 4.7 | MCP y UI de la etapa | Tools del Buzón, pantallas de permisos, grupos, niveles, SSO y audit | E2E completo del flujo del Buzón y de permisos |

El orden es intencional: permisos y visibilidad primero, porque el Buzón y el formulario público dependen de ellos.

## Modelo de datos

```
tickets (columnas nuevas)
  origin             enum(team, user) null   -- se llena en Drafts; se conserva al convertir
  classification     enum(idea, experiment, complaint, suggestion) null
  impact             smallint null           -- 1 a 5
  effort             smallint null           -- 1 a 5
  converted_at       timestamptz null
  submitter_name     text null               -- envíos públicos
  submitter_email    citext null
  tracking_code      text unique null        -- 10 caracteres base32 sin ambiguos
  security_level_id  null fk security_levels

inbox_settings                               -- uno por proyecto
  project_id pk
  enabled            bool default false
  public_slug        citext unique           -- /b/{slug}
  title, intro_md, thank_you_md
  allowed_classifications enum[]             -- default complaint, suggestion, idea
  require_email      bool default false
  allow_attachments  bool default true
  max_attachments    int default 3
  captcha            enum(altcha, turnstile, hcaptcha, none) default altcha
  captcha_config     jsonb                   -- llaves si es turnstile o hcaptcha, cifradas
  auto_tags          text[]
  updated_at

groups
  id, name citext unique, description, created_at

group_members
  group_id, user_id                          -- pk compuesta; humanos y agentes

project_group_roles
  project_id, group_id, role                 -- un grupo entra al proyecto con un rol
  -- rol efectivo de un usuario = el más alto entre su rol directo y los de sus grupos

project_role_permissions
  project_id, role, permission text, allowed bool
  -- pk (project_id, role, permission); sin fila = default del catálogo

security_levels
  id, project_id, name, description
  include_participants bool default true     -- reporter, assignee y colaboradores siempre ven

security_level_grants
  level_id, group_id null, user_id null      -- uno de los dos

sso_providers
  id, name, issuer_url
  client_id, client_secret_encrypted
  scopes             text[] default '{openid,email,profile}'
  allowed_domains    text[]                  -- vacío = cualquiera
  auto_create_users  bool default true
  group_claim        text null               -- ej. "groups"
  group_mapping      jsonb                   -- {"radicle-backend": "<group_id>"}
  enabled            bool
  created_at, updated_at

users (columnas nuevas)
  auth_source        enum(local, oidc) default local
  sso_provider_id null, sso_subject text null  -- unique(sso_provider_id, sso_subject)

audit_log                                    -- solo inserción, igual que ticket_events
  id bigserial pk
  actor_id null, actor_kind enum(human, agent, system)
  action             text                    -- ver catálogo
  target_type, target_id
  project_id null
  details            jsonb                   -- antes y después cuando aplique
  ip, user_agent, created_at
```

El usuario de sistema `inbox` (kind `agent`, sin tokens, no aparece en listas) es el reporter de los envíos públicos.

Nueva variable `RADICLE_SECRET_KEY`: llave para cifrar secretos en DB (AES-GCM). Sin ella la app no arranca a partir de esta etapa.

## Buzón

El Buzón de un proyecto son sus tickets tipo Draft. No es una entidad aparte: es una vista con campos y acciones propias.

### Campos del Draft

| Campo | Valores | Cómo se llena |
| --- | --- | --- |
| Origen | Equipo, Usuario | Automático: Equipo si lo crea un miembro (UI, API o MCP), Usuario si llega por el formulario. No se edita |
| Clasificación | Idea, Experimento, Queja, Sugerencia | Obligatoria al crear. Experimento solo lo puede elegir el equipo |
| Impacto | 1 a 5 | Lo pone el equipo al revisar |
| Esfuerzo | 1 a 5 | Lo pone el equipo al revisar |

La migración llena los Drafts existentes con Origen Equipo y Clasificación Idea.

### Vista Buzón (`/p/{key}/inbox`)

- Tabla de Drafts con: key, título, clasificación, origen, 🙋 votos, impacto, esfuerzo, antigüedad y estado.
- Pestañas: Nuevos (New), En revisión (In Review), Aprobados y Descartados.
- Filtros rápidos por clasificación y origen. Orden por votos, antigüedad o puntaje (`impact * 2 - effort`).
- Contador de nuevos en el sidebar del proyecto.

### Matriz impacto por esfuerzo

- Grid de 5 por 5: impacto en el eje vertical, esfuerzo en el horizontal.
- Cada Draft es un punto con tamaño según votos y color según clasificación.
- Cuadrantes con etiqueta: Quick wins (alto impacto, bajo esfuerzo), Apuestas grandes (alto y alto), Relleno (bajo y bajo), No vale la pena (bajo impacto, alto esfuerzo).
- Se arrastra un punto para cambiar impacto y esfuerzo. Los que no tienen calificación se listan a un lado.

### Triage

| Acción | Qué pasa |
| --- | --- |
| Revisar | Transición New a In Review |
| Calificar | Edita impacto y esfuerzo |
| Marcar duplicado | Link `duplicates` al ticket original y transición Discard con resolution Duplicate. Los votantes del duplicado se suman al original sin repetir |
| Descartar | Transición Discard con resolution Won't Do y comentario opcional para el usuario (visible en la página de seguimiento) |
| Aprobar y convertir | Ver abajo |

### Aprobar y convertir

Una sola acción atómica, en una transacción:

1. Pide tipo destino (Task o Bug), área (obligatoria), milestone, prioridad y assignee opcionales.
2. Ejecuta la transición Approve (resolution Done) para que quede registro de la aprobación.
3. Cambia el tipo al destino; el ticket queda en el estado inicial del nuevo workflow.
4. Llena `converted_at`. Origen, clasificación, votos, comentarios, adjuntos e historial se conservan.
5. Evento `converted` en el historial con tipo origen y destino.

Así un Task puede decir "Origen: Usuario, Clasificación: Queja" y se puede medir cuánto trabajo viene de usuarios. RQL agrega `origin`, `classification`, `impact`, `effort` y `converted` (booleano).

## Formulario público

### Página `/b/{slug}`

- Página ligera separada de la SPA (render en servidor con plantillas Jinja y un poco de JS), para que cargue rápido y no exponga la app.
- Muestra nombre del proyecto, `title` e `intro_md`. Tema lima, claro u oscuro según el sistema, en inglés o español según el navegador.
- Campos: tipo (entre `allowed_classifications`: Queja, Sugerencia, Idea), título (5 a 150 caracteres), descripción (hasta 10,000 caracteres, texto plano con saltos de línea), nombre opcional, email (opcional u obligatorio según config), adjuntos.
- Adjuntos: solo imágenes y PDF, máximo `max_attachments` de 5 MB cada uno; las imágenes se reducen a `medium` automáticamente.
- Accesible: etiquetas, errores junto al campo, navegable con teclado.

### Al enviar

1. Valida anti-spam (abajo).
2. Crea un Draft con reporter `inbox`, origen Usuario, la clasificación elegida, `submitter_name`, `submitter_email`, `auto_tags` y estado New.
3. Genera `tracking_code` y muestra `thank_you_md` con el código y el link de seguimiento.
4. Evento `created` con actor `inbox`.

### Anti-spam

| Capa | Regla |
| --- | --- |
| ALTCHA | Prueba de trabajo en el navegador, verificada en el servidor. Open source y sin terceros; default |
| Turnstile o hCaptcha | Alternativa configurable si el admin pone sus llaves |
| Honeypot | Campo oculto que si viene lleno rechaza en silencio |
| Rate limit | 5 envíos por hora y 20 por día por IP (guardada como hash con sal diaria) |
| Tiempo mínimo | Menos de 3 segundos entre cargar y enviar se rechaza |
| Contenido | Máximo 5 links en la descripción; markdown no se interpreta, se escapa |

Un rechazo por spam regresa el mismo mensaje genérico que un error, para no dar pistas.

### Seguimiento `/b/{slug}/t/{code}`

- Muestra título, clasificación, fecha y un estado simple: Recibido (New), En revisión (In Review), Aceptado (convertido) o Cerrado (Discarded), más el comentario de descarte si existe.
- Nunca muestra datos internos: ni assignee, ni comentarios internos, ni key, ni el ticket destino.
- El código no es adivinable (10 caracteres base32, 50 bits) y la ruta tiene rate limit.
- La notificación por email al usuario llega en la etapa 5.

## Grupos, permisos por rol y tickets restringidos

### Grupos

- Los crea el admin de instancia. Pueden tener humanos y agentes.
- Un grupo se agrega a un proyecto con un rol. El rol efectivo de una persona es el más alto entre su rol directo y los de sus grupos.
- Los grupos también se usan en niveles de seguridad y, en etapa 5, en reglas de notificación.

### Permisos por rol

Los tres roles se quedan (admin, member, viewer), pero cada proyecto puede ajustar qué permite cada uno. Admin siempre tiene todo. Toda verificación pasa por una sola función `authorize(user, permission, project, ticket=None)` en `core/permissions.py`; ningún router ni tool revisa roles por su cuenta.

| Permiso | Default member | Default viewer |
| --- | --- | --- |
| `ticket.create` | sí |  |
| `ticket.edit` | sí |  |
| `ticket.transition` | sí |  |
| `ticket.delete` |  |  |
| `ticket.move` |  |  |
| `ticket.bulk_edit` | sí |  |
| `ticket.set_security` |  |  |
| `comment.create` | sí |  |
| `comment.delete_any` |  |  |
| `attachment.upload` | sí |  |
| `attachment.delete_any` |  |  |
| `worklog.create` | sí |  |
| `worklog.edit_any` |  |  |
| `vote` | sí | sí |
| `link.manage` | sí |  |
| `sprint.manage` |  |  |
| `board.manage` |  |  |
| `inbox.triage` | sí |  |
| `project.settings` |  |  |
| `members.manage` |  |  |

Quitar un permiso a member o viewer se refleja en UI (botones ocultos), API (404 si no puede ver, 403 si puede ver pero no hacer) y MCP (error claro con el permiso faltante). Cambios a la matriz van al audit log.

### Tickets restringidos

- Cada proyecto puede definir niveles de seguridad (ej. "Legal confidencial").
- Un ticket con nivel solo lo ven: los grupos y usuarios del nivel, los admins del proyecto y, si `include_participants`, su reporter, assignee y colaboradores.
- Poner o quitar nivel requiere `ticket.set_security` y queda en historial y en audit log.
- **Un solo punto de verdad:** la función `visible_tickets_clause(user)` genera el filtro SQL y se usa en el compilador de RQL, en todo fetch de ticket por key, boards, backlog, timeline, reportes, widgets, búsqueda de la paleta, `next_ticket`, bulk y MCP.
- Un ticket no visible responde 404 aunque se pida por key, nunca 403.
- Links e hijos hacia un ticket no visible se muestran como "Ticket restringido" sin key ni título. Conteos agregados en reportes sí lo incluyen sin detalle, para que los números cuadren; las listas no.
- Adjuntos de un ticket restringido devuelven 404 aunque se tenga el ID, y las URLs firmadas solo se generan para quien lo ve.
- Al bajar de nivel un usuario (sale de un grupo), pierde acceso de inmediato; no hay caché de permisos de más de 60 segundos.

## SSO con OIDC y audit log

### SSO

- Protocolo OIDC con Authlib: authorization code con PKCE y discovery por `issuer_url`. Cubre Google, Microsoft Entra ID, Okta, Keycloak y Authentik.
- Varios proveedores a la vez; cada uno es un botón en el login.
- **Alta automática:** si `auto_create_users` y el dominio del email está en `allowed_domains`, se crea el usuario al primer login con handle derivado del email (con sufijo numérico si choca).
- **Cuentas existentes:** si ya existe un usuario local con el mismo email y el proveedor confirma `email_verified`, se liga a esa cuenta.
- **Grupos:** si el proveedor manda `group_claim`, en cada login se sincroniza la membresía de los grupos mapeados (agrega y quita solo esos).
- **Solo SSO:** opción de instancia `password_login_enabled=false`. El admin inicial siempre conserva acceso por password como salida de emergencia, documentado en el README.
- Usuarios desactivados no entran aunque el proveedor los autentique.
- SAML queda fuera.

### Audit log

Registro inmutable (trigger igual que el historial) de acciones administrativas y de seguridad. Lo ve el admin de instancia completo; un admin de proyecto ve las entradas de su proyecto.

| Grupo | Acciones |
| --- | --- |
| Usuarios | `user.create`, `user.update`, `user.deactivate`, `user.make_admin`, `user.login`, `user.login_failed` |
| Tokens | `token.create`, `token.revoke` |
| Agentes | `agent.create`, `agent.update` |
| Proyectos | `project.create`, `project.update`, `project.archive`, `project.unarchive` |
| Miembros | `member.add`, `member.remove`, `member.role_change`, `group_role.add`, `group_role.remove` |
| Grupos | `group.create`, `group.update`, `group.delete`, `group.member_add`, `group.member_remove` |
| Permisos | `permission.change`, `security_level.create`, `security_level.update`, `security_level.delete`, `ticket.security_change` |
| Config | `template.update`, `workflow.change`, `inbox.settings_change`, `sso.create`, `sso.update`, `settings.change` |
| Datos | `ticket.delete`, `ticket.restore`, `ticket.move`, `ticket.bulk_edit` |

- Cada entrada guarda actor, IP, user agent y en `details` el antes y después.
- Visor con filtros por actor, acción, proyecto y fechas; exportar a CSV.
- Retención configurable con `RADICLE_AUDIT_RETENTION_DAYS` (default 730); un job borra lo vencido, y ese borrado es la única excepción al trigger (lo hace un rol de DB dedicado).
