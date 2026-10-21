# Radicle Folio: Build spec fase 0 (Plataforma compartida)

Oct 20, 2026 · @Fernando

La fase 0 saca de Docket lo que van a compartir las dos apps y deja listo el esqueleto de Folio. Es un refactor: Docket no puede cambiar su comportamiento, su API ni su MCP.

## Objetivo y entregables

Al terminar la fase 0, una persona entra una sola vez, cambia entre Docket y Folio desde el logo, y Folio ya tiene rutas, MCP y permisos globales listos para construir encima.

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 0.1 | Reorganizar el backend | Mover el código a `radicle/platform` y `radicle/docket` sin cambiar comportamiento; imports actualizados; regla de dependencias verificada en CI | Todos los tests de Docket pasan sin tocar sus aserciones y el diff del OpenAPI de Docket está vacío |
| 0.2 | Autorización genérica | Interfaz única `authorize(user, app, permission, resource)` en `platform` con un proveedor por app; Docket registra el suyo con su matriz actual | La matriz de permisos de Docket pasa igual que antes; un proveedor de prueba se registra y responde |
| 0.3 | Servicios compartidos | Storage de archivos, jobs (Procrastinate), audit log y configuración del proveedor de IA y embeddings en `platform` | Docket usa los servicios de `platform`; la config de IA se guarda cifrada y prueba la conexión |
| 0.4 | Frontend compartido y switch | Paquete `frontend/src/platform` (tema, componentes, auth, cliente API) y switch de suite en el logo | E2E: login, cambiar a Folio y de regreso a Docket sin volver a entrar |
| 0.5 | Esqueleto de Folio | Rutas `/folio`, `/api/v1/folio`, `/mcp/folio` con `whoami`; roles globales de Folio y su pantalla de admin | Un agente con su token llama `whoami` en los dos MCP; por default todos son reader en Folio |

## Platform, autorización genérica y modelo de datos

### Qué se mueve a platform

| Pieza | Viene de | Queda en `platform` |
| --- | --- | --- |
| Usuarios, agentes, sesiones, tokens | Docket etapa 1 | Igual, sin cambiar tablas |
| Grupos y miembros | Docket etapa 4 | Igual; Folio los usa directo |
| SSO (OIDC) | Docket etapa 4 | Igual |
| Audit log | Docket etapa 4 | Agrega columna `app` (docket, folio, platform) |
| Storage de archivos | Docket etapa 2 | `StorageBackend` local o S3; cada app guarda sus propias referencias |
| Jobs | Docket etapa 2 | Worker único; cada app registra sus tareas |
| Cifrado de secretos | Docket etapa 4 | `RADICLE_SECRET_KEY` |
| Proveedor de IA y embeddings | Nuevo | Tabla `ai_settings` con el esquema del spec de Docket etapa 5 |

Lo que es solo de tickets (proyectos, roles por proyecto, matriz de permisos de proyecto, niveles de seguridad) se queda en `docket`.

### Autorización genérica

```python
# platform/authz.py
class AuthzProvider(Protocol):
    app: str                                   # "docket" | "folio"
    def check(self, user, permission: str, resource) -> Decision: ...
    def visible_clause(self, user, model) -> ColumnElement: ...

def authorize(user, app: str, permission: str, resource=None) -> Decision
def visible(user, app: str, model) -> ColumnElement   # filtro SQL de visibilidad
```

- Cada app registra su proveedor al arrancar. `Decision` trae `allowed`, `reason` y si debe responder 404 o 403.
- Los grupos y la pertenencia a grupos se resuelven en `platform` una vez por petición y se cachean máximo 60 s.
- El `authorize` y el `visible_tickets_clause` de Docket pasan a ser su proveedor sin cambiar su lógica.

### Tablas nuevas

```
folio_global_grants                          -- roles globales de Folio
  id
  grantee_type   enum(user, group, everyone)
  grantee_id     uuid null                   -- null si everyone
  role           enum(reader, creator, admin)
  created_by, created_at
  -- semilla: everyone = reader

ai_settings                                  -- una sola fila, en platform
  provider       enum(none, anthropic, openai, openai_compatible, ollama)
  chat_model, embedding_model, embedding_dimensions int
  base_url null, api_key_encrypted null
  features jsonb, updated_by, updated_at

audit_log (columna nueva)
  app            enum(platform, docket, folio) default 'docket'
```

| Rol global de Folio | Puede |
| --- | --- |
| reader | Leer lo que sus permisos de space y página dejen |
| creator | Lo de reader, más crear spaces y publicar donde su space lo permita |
| admin | Todo en Folio: permisos, aprobaciones, tipos de documento, home |

El rol efectivo es el más alto entre el directo, el de sus grupos y `everyone`. El admin de instancia de Radicle es admin de Folio siempre.

## Switch de suite, rutas y esqueleto de Folio

### Switch de suite

Diseño aprobado en el [canvas de diseños](https://claude.ai/artifact/EcGroniKDdJSqb9iJ6XB6C).

- El logo de la topbar es un botón con el nombre de la app actual (`DOCKET` o `FOLIO` en mono sobre `accent-soft`) y una flecha.
- Al abrirlo muestra Radicle Docket y Radicle Folio con ícono, descripción y atajo (`g d` y `g f`), la actual marcada, y Administración de la instancia para admins.
- Cambiar de app no recarga sesión. Cada app recuerda la última ruta visitada del usuario.
- Solo aparecen las apps a las que el usuario tiene acceso.
- Accesible: `aria-expanded`, navegación con flechas, `esc` cierra.

### Rutas

| Capa | Docket | Folio |
| --- | --- | --- |
| UI | Rutas actuales sin cambio | `/folio`, `/folio/s/{space}`, `/folio/p/{id}-{slug}` |
| API | `/api/v1/...` sin cambio | `/api/v1/folio/...` |
| MCP | `/mcp` sin cambio | `/mcp/folio` |
| OpenAPI | `/api/v1/openapi.json` | Mismo documento, con tag `folio` |

### Esqueleto de Folio

- `GET /api/v1/folio/health` y `GET /api/v1/folio/me` (rol global efectivo).
- `GET`, `POST`, `DELETE /api/v1/folio/admin/grants` para roles globales; cada cambio va al audit log con `app = folio`.
- MCP de Folio montado con el mismo mecanismo que Docket (tools encima de la API en proceso) y una sola tool: `whoami`.
- UI: shell de Folio con topbar (switch, búsqueda deshabilitada, avatar), una home vacía con estado vacío de planta, y Admin, Roles globales con tabla de grants y botón para agregar usuario o grupo.
- Admin de instancia agrega la pantalla de proveedor de IA con botón Probar conexión (genera un embedding de prueba y muestra dimensiones y latencia).

## Tests

| Área | Casos mínimos |
| --- | --- |
| No regresión de Docket | Suite completa de Docket sin modificar aserciones; snapshot del OpenAPI de Docket idéntico al de antes del refactor; lista de tools del MCP de Docket idéntica |
| Dependencias | Test que importa cada módulo y falla si `platform` importa de `docket` o `folio`, o si `folio` importa tablas de `docket` |
| Autorización | `authorize` delega al proveedor correcto; app desconocida falla cerrado (deny); caché de grupos expira a los 60 s; quitar a alguien de un grupo le quita acceso al expirar |
| Roles globales de Folio | Default everyone = reader; rol efectivo máximo entre directo, grupos y everyone; admin de instancia siempre admin; cambios en audit log con `app = folio` |
| IA | Config cifrada; Probar conexión con proveedor simulado; sin proveedor, el resto funciona |
| MCP | `whoami` en `/mcp` y `/mcp/folio` con el mismo token |
| E2E | Login, cambiar a Folio con el logo y con `g f`, regresar con `g d`, sin pedir login; usuario sin acceso a Folio no lo ve en el switch |

## Criterios de aceptación de la fase

- [ ] Todo Docket funciona exactamente igual: tests, API y MCP.
- [ ] Entro una vez y cambio entre Docket y Folio desde el logo y con atajos.
- [ ] Doy rol creator a un grupo desde Admin de Folio y se refleja en `/api/v1/folio/me` de sus miembros.
- [ ] Configuro el proveedor de embeddings y la prueba de conexión pasa.
- [ ] Un agente llama `whoami` en los dos MCP con el mismo token.
- [ ] Todas las reglas generales del documento de control de Radicle se cumplen.

## Fuera de alcance

Cualquier contenido de Folio (spaces, páginas, editor) llega en fase 1. No se tocan las etapas pendientes de Docket.
