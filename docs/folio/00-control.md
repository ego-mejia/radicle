# Radicle Folio: Documento de control

Oct 20, 2026 · @Fernando

Radicle Folio es la suite de documentación de Radicle: se lee como revista, se escribe en equipo y alimenta un RAG. Comparte usuarios, grupos y agentes con Radicle Docket. Se construye en 6 fases (0 a 5). El stack base, las reglas generales y la identidad visual son las del documento de control de Radicle; aquí solo va lo propio de Folio.

## Fases

Cada fase se divide en entregables numerados que se aceptan uno por uno. Una fase no empieza hasta aceptar la anterior. La base es Docket ya programado hasta su etapa 4.

| Fase | Objetivo | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 0. Plataforma compartida | Que Docket y Folio sean dos apps sobre la misma base | Módulo `platform` con usuarios, agentes, tokens, grupos, autorización, audit log, storage, jobs y proveedor de IA; switch de suite; esqueleto de Folio | Entras una vez, cambias de Docket a Folio desde el logo, y todos los tests y la API de Docket siguen iguales |
| 1. Core de publicación + MCP | Publicar documentación real desde el día 1 | Spaces, árbol, folders, blog posts, space personal; editor con bloques base; publicación con metadata obligatoria; versiones; permisos global, por space y por página; aprobación de lo que crean agentes; vistas revista y enfoque; home bento default; búsqueda y RQL; índice RAG; MCP | Un agente propone un post por MCP, un admin lo aprueba, se publica con su metadata y aparece en la home, en la búsqueda y en el índice RAG |
| 2. Colaboración | Trabajar los docs en equipo | Tiempo real con cursores tipo Figma; comentarios al pie e inline; menciones, reacciones, watch, compartir; action items y Mis tareas; live docs; mover, copiar, reordenar, archivar; dueño, estado y vencimiento; labels; recientes, favoritos y feed | Tres personas editan la misma minuta al mismo tiempo viendo sus cursores y los comentarios inline sobreviven a las ediciones |
| 3. Templates, home y visuales | Que todo se vea increíble y sea fácil de crear | Templates de página y space (incluido Build spec) con panel de admin; editor de la home bento; bloque Visual animado; suite visual; whiteboards; databases; embeds | El admin arma la home bento y un post con bloque Visual animado se ve bien en claro y oscuro |
| 4. Docket + IA | Conectar docs con el trabajo y con la IA | Smart links y tablas de tickets, crear ticket desde texto, build spec a tickets en vivo, liga a milestones y áreas; chat RAG con citas, resumir, escribir con IA, glosario, sugerencia de metadata; agente que escribe posts desde el codebase | El chat responde con citas correctas y de un build spec salen sus tickets en Docket con estado en vivo |
| 5. Integraciones externas | Conectar todo lo de afuera | Páginas públicas; exportar e importar (Confluence, Notion, Word, Markdown); Slack y Teams; webhooks; automatización; plugins; calendarios; analytics; audit log de Folio | Se migra un space desde un export de Confluence y al publicar llega aviso a Slack |

## Arquitectura y stack adicional

### Arquitectura

- **Mismo monorepo, misma imagen, mismo deploy.** El backend se reorganiza en tres paquetes: `radicle/platform` (compartido), `radicle/docket` (lo que ya existe) y `radicle/folio` (nuevo).
- **Rutas:** Docket conserva `/api/v1/...` y `/mcp` sin cambios. Folio vive en `/api/v1/folio/...` y `/mcp/folio`. El mismo token funciona en los dos MCP, cada uno con sus permisos.
- **Frontend:** un solo SPA con dos shells. Docket en sus rutas actuales, Folio bajo `/folio/...`. Lo común (tema lima, componentes, auth, cliente API, switch de suite) vive en `frontend/src/platform`.
- **Base de datos:** tablas de Folio con prefijo `folio_`. Lo compartido sin prefijo, bajo `platform`.
- **Regla de dependencias:** `docket` y `folio` dependen de `platform`; `platform` no depende de ninguna; `folio` solo habla con `docket` por sus servicios públicos (fase 4), nunca por sus tablas.

```
radicle/backend/radicle/
├── platform/   # usuarios, agentes, tokens, grupos, autorización, audit, storage, jobs, IA
├── docket/     # tickets (etapas 1 a 4 ya programadas)
└── folio/      # docs
    ├── api/
    ├── services/
    ├── query/  # RQL de docs
    ├── rag/    # chunking, embeddings, búsqueda semántica
    └── mcp/
```

### Stack adicional

| Capa | Tecnología | Notas |
| --- | --- | --- |
| Editor | TipTap 2 (ProseMirror) | Esquema propio de bloques; JSON como formato canónico |
| Tiempo real | Yjs + y-prosemirror en cliente; pycrdt + pycrdt-websocket en servidor | Desde fase 2 |
| Markdown a documento | markdown-it-py con convertidor propio al esquema del editor | Para el MCP, imports y RAG |
| Diff de versiones | Diff por bloques sobre el JSON y diff de texto con diff-match-patch | |
| Embeddings | pgvector; proveedor configurable desde `platform` | Desde fase 1 |
| Diagramas | Mermaid renderizado en cliente | Fase 3 |
| Fórmulas | KaTeX | Fase 3 |
| Whiteboard | Excalidraw (MIT) | Fase 3 |
| Visuales de usuario | iframe con `sandbox="allow-scripts"` en un origen separado (`RADICLE_SANDBOX_ORIGIN`) y CSP estricta | Fase 3 |
| Gráficas | Recharts, igual que Docket | Fase 3 |

## Reglas propias de Folio

Además de las reglas generales de Radicle (paridad UI, API y MCP; tests; migraciones; errores; i18n; tema), todo entregable de Folio cumple:

- **Metadata completa para publicar.** Se valida en el servicio, así aplica igual en UI, API y MCP.
- **Agentes con aprobación.** Lo que crea o edita un agente nunca se publica sin que un admin lo apruebe, y queda en el audit log.
- **Versiones inmutables.** Una versión publicada no se modifica jamás; restaurar crea una nueva.
- **Contenido de usuario aislado.** HTML, SVG o embeds de usuario nunca entran al DOM principal; siempre en sandbox.
- **RAG fiel.** El índice refleja siempre la última versión publicada y no archivada. Reindexar es idempotente.
- **Docket intacto.** Ningún entregable de Folio puede cambiar la API, el MCP ni romper un test de Docket.

## Supuestos a confirmar

- [ ] La base es Docket programado hasta su etapa 4; la fase 0 lo refactoriza sin cambiar su comportamiento.
- [ ] Rutas: Folio bajo `/folio`, `/api/v1/folio` y `/mcp/folio`.
- [ ] Editor TipTap con JSON canónico desde fase 1; Yjs entra en fase 2 sin migrar contenido publicado.
- [ ] Los agentes escriben en Markdown y el servidor lo convierte al esquema del editor.
- [ ] El proveedor de IA y embeddings se configura en `platform` desde la fase 0; lo usa Folio en fase 1 y Docket en su etapa 5.
- [ ] La vista default es revista; el modo enfoque es un toggle que recuerda cada usuario.
- [ ] Tipos de documento iniciales: guía, referencia, how-to, anuncio, build spec, minuta, decision log, retrospectiva y requirements. El admin puede agregar más.
- [ ] Audiencias e idiomas son listas que define el admin.
- [ ] Whiteboard con Excalidraw por su licencia MIT.
- [ ] Un humano con permiso de publicar publica directo; solo los agentes pasan por aprobación.

## Documentos

Al exportarlos a Markdown para el repo, cada uno va en `docs/folio/` con el nombre de la tercera columna.

| Documento | Contenido | Archivo en el repo |
| --- | --- | --- |
| Documento de control de Folio | Este documento | `docs/folio/00-control.md` |
| [Features high level](https://claude.ai/artifact/WVpDGFGAtwdhZugWMNKFMZ) | Features aceptados de Folio | `docs/folio/01-features.md` |
| [Canvas de diseños](https://claude.ai/artifact/EcGroniKDdJSqb9iJ6XB6C) | Home, switch, lectura y visuales aprobados | Referencia visual, se abre en el navegador |
| [Build spec fase 0](https://claude.ai/artifact/EVmeUJRDpXTadU9wnid2tk) | Plataforma compartida | `docs/folio/fase-0.md` |
| [Build spec fase 1](https://claude.ai/artifact/4JdgVsJ3ETiXgLryGXqBTM) | Core de publicación + MCP | `docs/folio/fase-1.md` |
| [Build spec fase 2](https://claude.ai/artifact/Nhu8UVi6Ym7gYpbkdcYupE) | Colaboración | `docs/folio/fase-2.md` |
| [Build spec fase 3](https://claude.ai/artifact/T3QqWQdc6s8iDofEsiJoiB) | Templates, home y visuales | `docs/folio/fase-3.md` |
| [Build spec fase 4](https://claude.ai/artifact/6jNX6vzqLo6GpmYwwuS5nF) | Docket + IA | `docs/folio/fase-4.md` |
| [Build spec fase 5](https://claude.ai/artifact/SUG69WqjE6ztJpqfzVpMXR) | Integraciones externas | `docs/folio/fase-5.md` |
