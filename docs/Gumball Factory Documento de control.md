# Radicle: Documento de control

Oct 18, 2026 · @Fernando

Radicle es un ticket tracker open source y self-hosted con servidor MCP desde el día 1. Se construye en 5 etapas: cada una deja algo usable, no rompe lo anterior y tiene su propio build spec.

## Etapas

Cada etapa se divide en entregables numerados (1.1, 1.2...) que se aceptan uno por uno con los criterios de su build spec. Una etapa no empieza hasta que la anterior está aceptada completa.

| Etapa | Objetivo | Incluye | Entregable | Se acepta cuando |
| --- | --- | --- | --- | --- |
| 1. Core + MCP | Trabajar un proyecto completo, personas y agentes | Proyectos, milestones, áreas, tickets (Task, Bug, Draft) con campos fijos, checklist, tags, ticket padre, links, comentarios, historial, workflows por tipo con categorías y resolutions, usuarios y tokens de agente, roles básicos, REST API, lenguaje de queries (RQL), Kanban básico y MCP | Imagen Docker que levanta con `docker compose up`, UI web y MCP en `/mcp` | Un agente conectado por MCP toma un ticket, lo mueve, marca su checklist y comenta, y todo aparece en la UI y en el historial como hecho por el agente |
| 2. Configuración y trabajo diario | Adaptar cada proyecto y trabajar rápido | Campos custom, templates ligados o independientes, editor de workflows, reglas de transición, screens, adjuntos con reducción de imagen, votos 🙋, tiempo real invertido, clonar, mover, bulk edit, filtros guardados, ranking, atajos y cmd+k | Misma imagen con worker de jobs en segundo plano | Un template cambia y el cambio llega a todos los proyectos ligados; un agente usa `next_ticket`, registra tiempo y respeta las reglas de transición |
| 3. Planeación y visibilidad | Planear sprints y saber si se llega al milestone | Boards configurables (columnas, WIP limits, swimlanes, quick filters), Scrum, timeline, reportes agile y generales, dashboards | Vistas de planeación y reportes con datos reales | Se corre un sprint completo y su burndown, sprint report y el pronóstico de V1 cuadran con los datos |
| 4. Buzón y control de acceso | Abrirlo a usuarios externos y a más gente | Buzón con formulario público y matriz impacto por esfuerzo, grupos, permisos por rol, tickets restringidos, SSO (OIDC), audit log | Formulario público por proyecto y panel de permisos | Un usuario externo manda una queja, el equipo la califica y la convierte en Bug, y un ticket restringido no se filtra por ningún lado |
| 5. Integraciones externas | Conectar todo lo de afuera | Notificaciones, watchers, suscripciones a filtros, automatización, webhooks, Git, chat y docs, plugins, import/export, app móvil nativa e IA | Integraciones configurables desde la UI y app móvil publicada | Un PR mergeado mueve su ticket a Done, avisa por Slack y llega push al celular del assignee |

## Stack

Python (FastAPI) en backend y React en frontend, todo en una sola imagen Docker con Postgres al lado.

| Capa | Tecnología | Notas |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2 | API REST en `/api/v1`, OpenAPI automático |
| ORM y migraciones | SQLAlchemy 2.0 async + asyncpg, Alembic | Toda migración con upgrade y downgrade |
| Base de datos | PostgreSQL 16 | Full-text con `tsvector`, `jsonb` para campos custom, `pgvector` en etapa 5 |
| Lenguaje de queries | Lark | Gramática de RQL compilada a SQLAlchemy |
| MCP | SDK oficial de MCP para Python | Streamable HTTP en `/mcp`, encima de la API REST |
| Auth | argon2id, sesiones en cookie HttpOnly, tokens bearer | Tokens guardados como hash; OIDC con Authlib en etapa 4 |
| Jobs en segundo plano | Procrastinate (cola sobre Postgres) | Desde etapa 2, sin Redis |
| Imágenes | Pillow | Reducción y variantes en etapa 2 |
| Frontend | React 18, TypeScript, Vite | SPA servida por FastAPI en producción |
| Datos y rutas | TanStack Query, TanStack Router | Cliente generado desde OpenAPI con `openapi-typescript` + `openapi-fetch` |
| UI | Tailwind CSS, Radix UI primitives, dnd-kit, lucide-react | Tokens de color de la paleta lima |
| Markdown | CodeMirror 6 para editar, react-markdown + remark-gfm para mostrar | Sanitizado con rehype-sanitize |
| Gráficas | Recharts | Etapa 3 |
| i18n | react-i18next | Inglés y español desde etapa 1 |
| Tests backend | pytest, pytest-asyncio, httpx, testcontainers (Postgres real) |  |
| Tests frontend | Vitest, React Testing Library, Playwright | Playwright para E2E |
| Calidad | ruff, mypy, eslint, prettier, tsc | mypy estricto en `services/` y `query/` |
| Paquetes | uv (Python), pnpm (Node) |  |
| Despliegue | Dockerfile multi-stage, docker compose | Servicios `app`, `db` y desde etapa 2 `worker` |
| CI | GitHub Actions | Lint, tipos, tests, migraciones, build de imagen |
| Móvil | React Native con Expo | Etapa 5 |

## Reglas para todas las etapas

Un entregable está terminado solo si cumple todo esto, además de los criterios de su propio spec.

**Paridad UI, API y MCP**

- Todo lo que se hace en la UI existe en la API REST.
- Todo lo de la API que tenga sentido para un agente existe como tool del MCP, desde la etapa 1.
- REST y MCP pasan por la misma capa de servicios: mismas validaciones, permisos e historial.

**API y datos**

- API versionada en `/api/v1`. Dentro de v1 los cambios solo pueden ser aditivos.
- Errores en formato RFC 9457 (`application/problem+json`) con mensajes accionables. Ej. una transición inválida dice cuáles sí son válidas.
- Toda mutación de un ticket genera un evento en el historial.
- Cada cambio de esquema tiene migración Alembic con upgrade y downgrade, y CI prueba los dos.

**Tests**

- Cobertura mínima: 85% en `services/` y `query/`, 70% total en backend.
- Cada endpoint tiene al menos un test feliz, uno de error y uno de permisos.
- Cada tool del MCP tiene test de éxito y de error.
- Los flujos principales de la etapa tienen E2E en Playwright.
- Nunca se debilita un test para que pase; si el spec está mal, se corrige el spec.

**Operación**

- `docker compose up` en una máquina limpia levanta todo y pasa `scripts/smoke.sh`.
- Toda configuración por variables de entorno `RADICLE_*`, documentadas en `.env.example`. Nada de secretos en el repo.
- README, `docs/` y `CHANGELOG.md` actualizados al cerrar cada entregable.

**UI**

- Modo claro y oscuro con la paleta lima.
- Navegable con teclado y contraste AA en los dos modos.
- Textos en inglés y español con react-i18next.

**Rendimiento base**

- Con 10,000 tickets sembrados: búsqueda RQL p95 menor a 300 ms y board de 500 tickets carga en menos de 1 s.

## Repositorio y convenciones

Monorepo con backend, frontend y docs. Desde la etapa 5 se agrega `mobile/`.

```
radicle/
├── backend/
│   ├── radicle/
│   │   ├── api/          # routers FastAPI de /api/v1
│   │   ├── core/         # config, seguridad, errores, permisos
│   │   ├── db/           # modelos SQLAlchemy y sesión
│   │   ├── services/     # lógica de negocio, la usan REST y MCP
│   │   ├── query/        # RQL: gramática, parser y compilador
│   │   ├── mcp/          # servidor MCP y sus tools
│   │   ├── jobs/         # tareas de Procrastinate (etapa 2+)
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── mcp/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── components/
│   │   ├── api/          # cliente generado desde OpenAPI
│   │   ├── i18n/
│   │   └── theme/
│   ├── e2e/              # Playwright
│   └── package.json
├── docs/
│   ├── 00-control.md
│   ├── 01-features.md
│   ├── etapa-1.md ... etapa-5.md
│   ├── decisions/        # ADRs cuando algo se desvía del spec
│   └── progress.md       # estado de cada entregable
├── scripts/              # smoke.sh, seed.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
├── CHANGELOG.md
└── README.md
```

**Convenciones**

- Código, API, base de datos, comentarios y commits en inglés. Docs internos en español; `README.md` y `CONTRIBUTING.md` en inglés, con `README.es.md` como traducción ([0029](decisions/0029-proyecto-comunitario.md)).
- JSON de la API en `snake_case`. Fechas en UTC con ISO 8601; fechas sin hora como `YYYY-MM-DD`.
- IDs internos UUID. Hacia afuera los tickets se identifican por key (`PA-12`), los usuarios por handle y áreas y milestones por nombre.
- Commits con Conventional Commits (`feat:`, `fix:`, `test:`...). Ramas `tipo/descripcion` (`feat/`, `minor/`, `fix/`, `refactor/`, `docs/`) y PRs de una sola cosa con menos de 500 líneas y 100 archivos ([0029](decisions/0029-proyecto-comunitario.md)).
- La lógica vive en `services/`. Routers y tools del MCP solo validan entrada y llaman servicios.
- Si algo se desvía del spec, se documenta en `docs/decisions/` antes de hacerlo.
- Al cerrar cada entregable se actualiza `docs/progress.md` con qué se hizo y cómo verificarlo.

## Identidad visual

**Radicle**: la radícula, la primera raíz que saca una semilla al germinar. La vibe es de plantas y crecimiento orgánico, con acento lima, modo claro limpio y modo oscuro tipo terminal.

| Token | Claro | Oscuro | Uso |
| --- | --- | --- | --- |
| `bg` | `#F5F6F8` | `#0E0F11` | Fondo de página |
| `surface` | `#FFFFFF` | `#17191C` | Tarjetas, paneles |
| `surface-2` | `#F1F2F4` | `#23262A` | Hover, badges neutros |
| `border` | `#E5E7EB` | `#2A2D31` | Bordes |
| `text` | `#111827` | `#E6E6E6` | Texto principal |
| `text-muted` | `#6B7280` | `#7C8591` | Texto secundario |
| `accent` | `#4D7C0F` | `#C6F432` | Links, keys, foco |
| `accent-fill` | `#C6F432` | `#C6F432` | Botón primario |
| `on-accent` | `#1A2E05` | `#1A2E05` | Texto sobre `accent-fill` |
| `accent-soft` | `#ECF8C8` | `#2A3311` | Badges con acento |
| `danger` | `#DC2626` | `#F87171` | Errores, bloqueado |
| `warning` | `#B45309` | `#F5A524` | Avisos, WIP excedido |

**Tipografía**

- Inter para la UI.
- JetBrains Mono para keys (`PA-4`), RQL y código.

**Detalles de la vibe**

- Íconos de categoría: Draft es una semilla, In Progress un brote y Done una hoja.
- Estados vacíos con ilustraciones de plantas en línea delgada.
- Logo: una radícula saliendo de una semilla, en lima.
- Densidad compacta, pensada para trabajar con teclado.

## Supuestos a confirmar

Decisiones que tomé al escribir los specs y que no se discutieron. Marca las que van; las que no, se corrigen antes de programar esa etapa.

**Antes de la etapa 1**

- [x] **Licencia AGPL-3.0.** Evita que alguien lo venda como SaaS cerrado sin compartir cambios. Confirmada en [0029](decisions/0029-proyecto-comunitario.md).
- [ ] **Idioma.** Código, API y nombres default de estados en inglés; UI en inglés y español.
- [ ] **Estados default por tipo.** Task: To Do, In Progress, In Review, Done. Bug: Reported, In Progress, QA Verified, Done. Draft: New, In Review, Approved, Discarded.
- [ ] **Cierre anticipado.** No se puede ir de To Do a Done por el camino normal, pero sí existe una transición "Close" desde cualquier estado que solo acepta resolution Won't Do o Duplicate (y Cannot Reproduce en Bugs).
- [ ] **Área opcional en Draft.** Obligatoria en Task y Bug; un Draft puede no tenerla porque las entradas del Buzón llegan sin área.
- [ ] **Cambio de tipo.** Cambiar el tipo de un ticket (ej. Draft a Task) lo manda al estado inicial del nuevo workflow y queda en el historial.
- [ ] **Referencias por nombre.** API y MCP aceptan áreas y milestones por nombre y personas por handle, no solo por ID.
- [ ] **MCP en la misma app.** Montado en `/mcp`; cada tool llama a la API REST en proceso con el token del agente.
- [ ] **Bloqueo en etapa 1 solo avisa.** La opción de impedir mover un ticket bloqueado llega con las reglas de transición en etapa 2.
- [ ] **Workflows fijos en etapa 1.** Se siembran por proyecto; editarlos llega en etapa 2 con templates.
- [ ] **Kanban básico por categoría.** En etapa 1 las columnas son To Do, In Progress y Done; columnas por estado llegan en etapa 3.
- [ ] **Soft delete.** Borrar un ticket lo oculta pero conserva su historial; un admin lo puede restaurar.

**Etapas siguientes**

- [ ] **Fecha de inicio.** Campo opcional `start_date` en tickets para dibujar el timeline (etapa 3).
- [ ] **Backlog en Scrum.** Meter un ticket a un sprint le quita el tag #backlog; al cerrar el sprint, lo no terminado sale del sprint y recibe #backlog (etapa 3).
- [ ] **Buzón.** Calificación con Impacto y Esfuerzo de 1 a 5; aprobar un Draft lo convierte en Task o Bug en el mismo ticket; el usuario externo recibe un código para ver el estado de su envío (etapa 4).
- [ ] **SSO solo OIDC.** Cubre Google, Microsoft, Okta, Keycloak y Authentik; SAML queda fuera (etapa 4).
- [ ] **Líder de área.** Las áreas tienen un líder opcional para las reglas de notificación (etapa 5).
- [ ] **App móvil con React Native (Expo).** Compila a app nativa de iOS y Android; si prefieres Swift y Kotlin se cambia (etapa 5).
- [ ] **Nombre.** Ya existe otro proyecto open source llamado Radicle (colaboración de código peer-to-peer). Se usa de todos modos; si `radicle` está tomado en PyPI, npm o Docker Hub, los paquetes se publican como `radicle-tracker`.
