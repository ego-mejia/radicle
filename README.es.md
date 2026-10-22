<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-dark.svg">
    <img src="docs/images/logo.svg" alt="Radicle" width="320">
  </picture>
</p>

<p align="center">
  <b>El ticket tracker open source donde personas y agentes de IA trabajan el mismo proyecto.</b><br>
  Self-hosted · MCP integrado · Buzón para tus usuarios · AGPLv3
</p>

<p align="center">
  <a href="LICENSE"><img alt="Licencia: AGPL v3" src="https://img.shields.io/badge/licencia-AGPLv3-4D7C0F?style=flat-square"></a>
  <a href="CONTRIBUTING.md"><img alt="PRs bienvenidos" src="https://img.shields.io/badge/PRs-bienvenidos-C6F432?style=flat-square&labelColor=1A2E05"></a>
  <a href="README.md"><img alt="Read in English" src="https://img.shields.io/badge/read%20in-English-F1F2F4?style=flat-square"></a>
</p>

<p align="center">
  <img src="docs/images/board.png" alt="Board de Radicle" width="900">
</p>

> 🌱 **Radicle** viene de *radícula*: la primera raíz que saca una semilla al germinar.

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¡Hola! Soy Radi, el verdecito de la esquina de la app (y del logo). Te acompaño por este README: busca mis notas al inicio de cada sección.


Esta es la versión en español del README. La versión principal, en inglés, es [README.md](README.md). La interfaz de Radicle está en inglés y en español; los screenshots están en inglés.

## Contenido

- [Por qué Radicle](#-por-qué-radicle)
- [Inicio rápido](#-inicio-rápido)
- [Conoce a Radi](#-conoce-a-radi)
- [Guía de uso](#-guía-de-uso)
- [Configuración](#%EF%B8%8F-configuración)
- [Arquitectura](#%EF%B8%8F-arquitectura)
- [Desarrollo](#-desarrollo)
- [Roadmap y pendientes](#%EF%B8%8F-roadmap-y-pendientes)
- [Cómo contribuir](#-cómo-contribuir)
- [Licencia](#-licencia)

## ✨ Por qué Radicle

| | |
| --- | --- |
| 🤖 **Los agentes son parte del equipo** | Trae un servidor MCP (Model Context Protocol) adentro. Claude, Cursor o cualquier cliente MCP toma un ticket, lo mueve, marca su checklist, registra tiempo y comenta, y todo queda en el historial como hecho por ese agente. |
| 📮 **Escucha a tus usuarios** | Cada proyecto puede abrir un formulario público. Quejas e ideas llegan a un **Buzón**, las calificas en una matriz de impacto por esfuerzo y conviertes las buenas en tareas o bugs. Quien las mandó las sigue con un código. |
| 🔒 **Control de acceso en serio** | Grupos, matriz de permisos por proyecto, tickets restringidos que no aparecen en ningún lado (búsqueda, boards, reportes, MCP), SSO con OpenID Connect y un audit log que nadie puede modificar. |
| 🗺️ **Planea y ve** | Boards Kanban y Scrum, sprints, timeline con pronóstico, diez reportes agile y generales, y dashboards que armas arrastrando. |
| 🟢 **Una guía adentro** | Radi, la mascota, responde cómo hacer las cosas con la guía de uso y, con el LLM que elijas, te lleva por la pantalla paso a paso. |
| 📚 **Docs junto a los tickets** | **Folio**, la segunda app, guarda la documentación del equipo: spaces, un editor por bloques, versiones, permisos por página, búsqueda y un chat que responden con citas, edición en tiempo real, templates, bloques visuales, whiteboards y databases, ligas a tickets de Docket, páginas públicas, importar desde Confluence y Notion, exportar a PDF, Slack y Teams, webhooks, calendarios, analytics y un MCP para que los agentes lean y propongan docs que un admin aprueba. |
| ⚡ **Rápido para trabajar** | Lenguaje de queries (RQL), paleta de comandos, atajos para todo y temas claro y oscuro. En inglés y en español. |
| 🏠 **Tuyo** | Un `docker compose up`. PostgreSQL, tu servidor, tus datos. |

## 🚀 Inicio rápido

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Tres comandos y listo. La primera visita te pide crear el admin de la instancia.

Necesitas Docker con Compose.

```bash
git clone https://github.com/ego-mejia/radicle.git
cd radicle
cp .env.example .env
# Obligatoria: un secreto largo y aleatorio. Cifra los secretos guardados y firma links.
echo "RADICLE_SECRET_KEY=$(openssl rand -hex 32)" >> .env
docker compose up -d
```

Abre <http://localhost:8000>. La primera vez aparece la pantalla de **setup** para crear al admin de la instancia.

Se levantan tres contenedores: `app` (web, API REST y MCP), `worker` (trabajos en segundo plano) y `db` (PostgreSQL 16). La API vive en `/api/v1` y su documentación interactiva en `/api/docs`.

> [!TIP]
> En producción, pon Radicle detrás de HTTPS y define `RADICLE_BASE_URL` con su URL pública. Las cookies se vuelven `Secure` solas.

## 🟢 Conoce a Radi

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¡Ese soy yo! Dame clic en la esquina inferior derecha de cualquier página y pregúntame cómo hacer algo. Mis ojos siguen tu cursor y crezco un poquito cuando pasas encima.

Radi responde preguntas sobre cómo usar Radicle y te enseña dónde están las cosas.

- **Sin configurar nada**, Radi responde con la guía de uso incluida (en inglés y español) y ofrece un recorrido ya hecho para los temas principales: da clic en **Show me**.
- **Con un LLM** (Anthropic, OpenAI o cualquier servidor compatible con OpenAI, como Ollama), Radi responde en el idioma en que preguntaste y te lleva por la pantalla: un cursor blanco con brillo verde va a cada botón, abre páginas y diálogos, ilumina cada campo y lo explica. Nunca da clic en **Create**, **Save** ni **Add** por ti; solo los señala.
- Después de cada respuesta Radi vuelve a mostrar las preguntas sugeridas para que sigas preguntando.

<p align="center">
  <img src="docs/images/radi-chat.png" alt="Radi respondiendo en el chat" width="49%">
  <img src="docs/images/radi-tour.png" alt="El recorrido de Radi explicando el diálogo de crear proyecto" width="49%">
</p>

**Configura el LLM** en **Admin → Settings → Assistant**: elige el proveedor, pega la API key (se guarda cifrada y no se vuelve a mostrar) y, si quieres, el modelo y la base URL; luego da clic en **Test**. Las variables de entorno mandan sobre lo de la app, útil cuando no quieres secretos en la base de datos:

| Variable | Qué hace |
| --- | --- |
| `RADICLE_ASSISTANT_PROVIDER` | `anthropic`, `openai` o `none` |
| `RADICLE_ASSISTANT_API_KEY` | La API key del proveedor |
| `RADICLE_ASSISTANT_MODEL` | Opcional; por defecto `claude-haiku-5-5` o `gpt-4o-mini` |
| `RADICLE_ASSISTANT_BASE_URL` | Opcional; para servidores compatibles con OpenAI, como `http://ollama:11434/v1` |

<p align="center"><img src="docs/images/assistant-settings.png" alt="Ajustes del asistente" width="820"></p>

Radi solo puede señalar un catálogo fijo de lugares de la app, así que un modelo no puede inventar botones. La guía con la que responde vive en `backend/radicle/docket/services/assistant/guide/`.

## 📖 Guía de uso

### 1. Crea tu primer proyecto

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Pregúntame "¿cómo creo un proyecto?" y te llevo al botón y te explico cada campo del diálogo.

En **Projects**, da clic en **Create project**. Ponle nombre y una **key** corta (de 2 a 10 mayúsculas o dígitos, como `PAY`). Cada ticket la lleva de prefijo (`PAY-12`) y no se puede cambiar después.

Elige un **template**: trae los workflows (estados y transiciones de Task, Bug y Draft), campos custom y políticas. **Linked** sigue recibiendo los cambios del template; **Independent** lo copia una vez para que lo edites libremente.

<p align="center"><img src="docs/images/create-project.png" alt="Crear proyecto" width="820"></p>

Luego, en **Settings** del proyecto, agrega **Areas** (Backend, Mobile, Legal...) y **Milestones** (V1, V2...). Toda task y todo bug pertenecen a un área; los milestones son opcionales. Dale a cada área un color y un icono (clic en el cuadro junto a su nombre): se ven en las tarjetas del board, los carriles y el timeline.

Para cambiar el nombre o la descripción de un proyecto, pasa el cursor sobre su tarjeta en **Projects** y da clic en el lápiz. La key nunca cambia. Los proyectos no se borran: un admin del proyecto puede darle **Archive** en **Settings → General**, y queda de solo lectura con todo su historial.

### 2. Agrega gente

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Los proyectos son mejores acompañados. Así se suman personas, grupos y agentes.

Un admin de instancia crea a las personas en **Admin → Users**, o llegan solas por [SSO](#11-single-sign-on-sso). Para darles acceso a un proyecto, abre **Settings → Members**, busca a la persona, agente o grupo en el menú, elige un rol y da clic en **Add**. Cambia el rol desde el menú de cada fila:

| Rol | Puede |
| --- | --- |
| **Viewer** | Ver todo el proyecto y votar. |
| **Member** | Lo mismo que un viewer, más crear, editar, mover y comentar tickets. |
| **Admin** | Todo, más administrar miembros, configuración, workflows y permisos. |

<p align="center"><img src="docs/images/members.png" alt="Miembros del proyecto" width="820"></p>

Para equipos, crea un **grupo** en **Admin → Groups** (por ejemplo `legal-team`) y dale un rol en el proyecto. Todos sus integrantes entran de una vez, y también quien se sume después. Si alguien tiene varios roles (directo y por grupos), vale el más alto.

Los agentes de IA se agregan igual: ve [Agentes de IA por MCP](#13-agentes-de-ia-por-mcp).

### 3. Trabaja los tickets

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Los tickets son donde vive el trabajo. Presiona <kbd>c</kbd> en cualquier lado para crear uno.

Presiona <kbd>c</kbd> o da clic en **Create ticket**. Hay tres tipos:

- **Task**: trabajo por hacer.
- **Bug**: algo roto.
- **Draft**: una idea o petición que todavía no se decide. Los Drafts viven en el [Buzón](#9-buzón-y-formulario-público).

<p align="center"><img src="docs/images/ticket.png" alt="Ticket con checklist, link, comentarios y tiempo" width="820"></p>

Un ticket tiene descripción en markdown con **checklist**, además de prioridad, área, milestone, assignee, colaboradores, fechas, estimado, tags y ticket padre. Abajo están los adjuntos (las imágenes se reducen solas), subtickets, links (`blocks`, `relates to`, `duplicates`, `clones`), comentarios con `@menciones` y reacciones, y el **historial** completo.

- **Muévelo** con el botón de estado. Los workflows pueden pedir resolution, comentario o checklist completo antes de una transición.
- **Registra tiempo** con **Log time**. Lo invertido y lo restante se actualizan al momento.
- **Vota** con 🙋 para decir que te importa.
- Desde el menú **⋯** lo clonas, lo mueves a otro proyecto o lo borras (un admin puede restaurarlo).

<p align="center"><img src="docs/images/ticket-history.png" alt="Historial del ticket" width="820"></p>

### 4. Boards

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Arrastra una tarjeta y suéltala donde quieras: ahí se queda y brilla. ¡Si la sueltas en Done brilla todavía más!

Cada proyecto empieza con un board Kanban llamado **Main**, con **To Do**, **In Progress**, **In Review** y **Done**. Arrastra tarjetas entre columnas y caen justo donde las sueltas; la tarjeta movida destella una vez, y la que llega a una columna de terminado destella más fuerte. Soltar una tarjeta en **Done** la cierra como *Done* sin preguntar; *Won't do* o *Duplicate* se eligen desde el ticket. Los quick filters (**My tickets**, **Only bugs**, `#backlog`, **Blocked**) y la barra de filtros lo acotan.

Las tarjetas muestran su área (con su icono) y su milestone como etiquetas al estilo Jira, y cuántos subtickets tienen. Da clic en el área o el milestone de una tarjeta para cambiarlo desde un menú, sin abrir el ticket.

Los **carriles** (swimlanes) dividen el board en filas por área, assignee, prioridad, milestone, padre o tipo, como varios boards apilados. Da clic en el encabezado de una fila para plegarla, o usa **Collapse all**; Radicle recuerda cuáles plegaste.

<p align="center">
  <img src="docs/images/board-lanes.png" alt="Board con carriles por área" width="49%">
  <img src="docs/images/board-dark.png" alt="Board en modo oscuro" width="49%">
</p>

Los admins crean más boards con **New board** y los configuran en **Configure**:

- **Origen**: una query RQL, así un board puede abarcar un área o varios proyectos.
- **Columnas**: por estado o por categoría, con **límites WIP**. Los suaves ponen la columna en rojo; los duros bloquean el movimiento (un admin puede forzarlo).
- **Campos de la tarjeta** y **quick filters**.

### 5. Busca con RQL

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¿Buscas algo preciso? RQL lo encuentra. En **List**, el botón **Filter** arma las queries sencillas por ti.

RQL (Radicle Query Language) funciona en la barra de búsqueda, en **List**, en los boards y en los filtros guardados:

```text
type = bug AND priority >= high AND assignee = currentUser()
project IN (PA, MOB) AND category != done ORDER BY due ASC
text ~ "checkout" AND updated >= -7d
sprint = active AND #backlog
classification = complaint AND origin = user ORDER BY votes DESC
```

Los errores se subrayan en su lugar con lo que se esperaba, y el editor autocompleta campos y valores. Guarda una query como **filtro** para reusarla, compartirla o ponerla en un dashboard. Los agentes leen la guía completa en el recurso MCP `radicle://guide/rql`.

**List** muestra los tickets en una tabla. Da clic en **Filter** arriba de ella para filtrar por tipo, estado, prioridad, assignee, área o milestone sin escribir RQL (cada filtro es un chip que puedes quitar), en **Group by** para dividir las filas en grupos plegables y en **Saved filters** para reusar queries. Los tickets con subtickets tienen una flecha que abre sus tareas y bugs justo debajo.

<p align="center">
  <img src="docs/images/list-filters.png" alt="Lista con el menú de filtros" width="49%">
  <img src="docs/images/list-rql.png" alt="Lista con una query RQL" width="49%">
</p>

### 6. Sprints y backlog

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¿Vas a planear en sprints? Primero necesitas un board Scrum; pregúntame y te enseño dónde.

Crea un board de tipo **Scrum** para planear en sprints. Luego, en **Backlog**:

1. **New sprint**, con objetivo, fechas y capacidad en horas.
2. Arrastra tickets adentro. La barra compara horas comprometidas contra capacidad y avisa de tickets sin estimado.
3. **Start sprint**. Lo que está adentro se vuelve el compromiso.
4. **Complete sprint**. Lo no terminado regresa al backlog (con `#backlog`) o pasa al siguiente sprint, y se guarda el reporte del sprint.

<p align="center"><img src="docs/images/backlog.png" alt="Backlog con un sprint activo y uno futuro" width="820"></p>

### 7. Timeline y milestones

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Mi parte favorita: cuando el último ticket de un milestone queda en Done, hago fiesta.

**Timeline** dibuja los tickets en el tiempo, agrupados por milestone o área, por semana, mes o trimestre. Arrastra una barra para cambiar sus fechas, o un ticket de **Without dates** para dárselas. Un ticket con solo fecha límite se dibuja con una barra tenue desde el día en que se creó (uno con solo fecha de inicio, con una barra tenue tan larga como su estimado) hasta que tenga ambas fechas. Las dependencias imposibles (un ticket que empieza antes de que termine lo que lo bloquea) se ponen en rojo, y los milestones muestran su pronóstico.

<p align="center"><img src="docs/images/timeline.png" alt="Timeline" width="820"></p>

Los **milestones** son metas con fecha objetivo opcional, como un release. Cuando el último ticket abierto de un milestone llega a done, Radicle lo celebra: confeti, Radi festejando y los números detrás (tickets entregados, horas invertidas, bugs aplastados, tareas, ideas, días para entregar y las personas y agentes de IA que lo lograron). **Share on LinkedIn** copia una imagen lista a tu portapapeles y abre un post con el texto escrito; **Download image** la descarga.

<p align="center">
  <img src="docs/images/milestone-celebration.png" alt="Celebración de milestone" width="49%">
  <img src="docs/images/milestone-card.png" alt="Imagen para compartir en LinkedIn" width="49%">
</p>

### 8. Reportes y dashboards

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Números, gráficas y un CSV para cada una. Cada quien ve solo los tickets que puede ver.

**Reports** tiene burndown, burnup, velocity, cumulative flow, control chart, sprint report, creados vs resueltos, distribución, progreso de milestone (con pronóstico y aviso de "en riesgo") y tiempo. Cada uno trae su tabla de datos y **Export CSV**.

<p align="center"><img src="docs/images/reports.png" alt="Reporte de cumulative flow" width="820"></p>

**Dashboards** junta widgets en una cuadrícula que acomodas arrastrando: conteos, distribuciones, progreso de milestone, burndown, bloqueados, resultados de filtros y notas en markdown. Un dashboard puede ser privado, del proyecto o de toda la instancia, y cada quien ve solo los tickets que puede ver. Cada proyecto tiene su dashboard **Summary**.

<p align="center"><img src="docs/images/summary.png" alt="Dashboard de resumen del proyecto" width="820"></p>

### 9. Buzón y formulario público

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Tus usuarios pueden decirte qué piensan, aunque no tengan cuenta. Sus ideas llegan aquí.

El **Buzón** (Inbox) junta Drafts: ideas del equipo, peticiones de agentes, y quejas, sugerencias e ideas de gente **sin cuenta** que usa el formulario público.

<p align="center"><img src="docs/images/inbox-flow.svg" alt="De la retroalimentación al ticket" width="900"></p>

**Abre el formulario público.** En **Settings → Inbox**, actívalo y elige el slug, los textos, qué tipos se pueden mandar, si el email es obligatorio, los adjuntos y el captcha. ALTCHA es el default y no depende de terceros; Turnstile y hCaptcha también funcionan. Luego comparte el link: `https://tu-radicle/b/<slug>`.

<p align="center">
  <img src="docs/images/public-form.png" alt="Formulario público" width="49%">
  <img src="docs/images/public-tracking.png" alt="Página de seguimiento" width="49%">
</p>

Cada envío recibe un **código de seguimiento**. La página de seguimiento muestra su estado (Recibido, En revisión, Aceptado o Cerrado) y tu nota pública, nunca detalles internos. Un honeypot, límites por IP, tiempo mínimo de llenado y límite de links frenan el spam.

**Triage.** El Buzón tiene pestañas New, In review, Approved y Discarded, con filtros por clasificación y origen.

- Califica cada entrada con **Impact** y **Effort** (de 1 a 5).
- Cambia a **Matrix** para ver los quick wins de un vistazo. Arrastra un punto para recalificarlo.
- **Approve and convert** convierte el Draft en Task o Bug en el mismo ticket, así que votos, comentarios e historial se conservan.
- **Mark duplicate** pasa sus votantes al original. **Discard** puede dejar una nota para quien lo mandó.

<p align="center">
  <img src="docs/images/inbox.png" alt="Tabla del Buzón" width="49%">
  <img src="docs/images/inbox-matrix.png" alt="Matriz de impacto por esfuerzo" width="49%">
</p>

### 10. Permisos, grupos y tickets restringidos

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Quién ve qué y quién puede hacer qué. Los tickets restringidos no existen para nadie más, ni para mí.

<p align="center"><img src="docs/images/access-model.svg" alt="Quién puede ver y hacer qué" width="900"></p>

- **Matriz de permisos** (**Settings → Permissions**): prende o apaga cada uno de los 20 permisos para members y viewers. Cubren crear, editar, mover y borrar tickets, comentarios, adjuntos, tiempo, votos, links, seguridad y triage del Buzón. La misma regla aplica en la UI (los botones desaparecen), la API (403 con el permiso que falta) y el MCP.
- **Niveles de seguridad** (**Settings → Levels**): crea un nivel como *Legal confidential* y dáselo a grupos o personas. Un ticket con ese nivel no existe para nadie más: ni en búsqueda, boards, reportes, dashboards, links, historial ni MCP. Si quieres, su reporter, assignee y colaboradores lo siguen viendo.

<p align="center">
  <img src="docs/images/permissions.png" alt="Matriz de permisos" width="49%">
  <img src="docs/images/security-levels.png" alt="Niveles de seguridad" width="49%">
</p>

### 11. Single sign-on (SSO)

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Que la gente entre con la cuenta que ya tiene.

En **Admin → SSO** agrega proveedores OpenID Connect (Google, Microsoft Entra ID, Okta, Keycloak, Authentik...) con su issuer URL, client ID y secret. Registra en tu proveedor la URL de callback que muestra el formulario.

- **Dominios permitidos**: deciden quién obtiene cuenta automáticamente. Una cuenta existente con el mismo email verificado se liga.
- **Mapeo de grupos**: sincroniza los grupos del proveedor con los de Radicle en cada entrada. Solo se tocan los grupos mapeados.
- En **Admin → Settings** puedes apagar la entrada con password. El primer admin de la instancia siempre puede entrar con su password: es tu salida de emergencia si el proveedor falla.

<p align="center"><img src="docs/images/sso.png" alt="Proveedores SSO" width="820"></p>

### 12. Audit log

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Cada cambio administrativo, anotado para siempre. Nadie puede editarlo, ni los admins.

**Admin → Audit log** registra 39 tipos de acciones administrativas: usuarios, tokens, agentes, proyectos, miembros, grupos, permisos, niveles de seguridad, borrados, movimientos, ediciones masivas, templates, workflows, ajustes del Buzón y SSO. Cada entrada dice quién, cuándo, desde qué IP y qué cambió (antes y después). Filtra por persona, acción, proyecto y fechas, y exporta a CSV. Los admins de proyecto ven las entradas de sus proyectos en **Settings → Audit log**.

El log es **de solo inserción**: la base de datos rechaza cambios y borrados. Las entradas con más de `RADICLE_AUDIT_RETENTION_DAYS` días (730 por default) se purgan.

<p align="center"><img src="docs/images/audit.png" alt="Audit log" width="820"></p>

### 13. Agentes de IA por MCP

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Aquí los agentes son compañeros de equipo, como yo. Dales un token y un proyecto y se ponen a trabajar.

Los agentes son usuarios de tipo *agent*, con su propio handle, tokens, historial y permisos.

1. Ve a **Admin → Users → New user**, elige **Agent (LLM or worker)** y copia el token (`rdc_...`). Se muestra una sola vez, junto con los snippets de MCP listos para pegar. (**Admin → Agents → New agent** hace lo mismo.)
2. Elige qué puede hacer por MCP: deja **All tools**, elige **Read only** o marca las tools exactas; por ejemplo, un bot de triage que solo lee y califica el Buzón.
3. Agrégalo a un proyecto en **Settings → Members**, normalmente como **Member**.
4. Conecta tu cliente MCP.

<p align="center"><img src="docs/images/agent-mcp-permissions.png" alt="Permisos de MCP de un agente" width="820"></p>

Puedes cambiar las tools de un agente cuando quieras con **MCP permissions** en Users o Agents. Las que están apagadas desaparecen de su lista de tools y se rechazan si las llama. Se suman a los permisos del proyecto y a los niveles de seguridad, nunca los reemplazan. Cada cambio queda en el audit log.

**Claude Code**

```bash
claude mcp add --transport http radicle http://localhost:8000/mcp \
  --header "Authorization: Bearer rdc_xxxxxxxx"
```

**Clientes con configuración JSON** (Claude Desktop, Cursor, VS Code...)

```json
{
  "mcpServers": {
    "radicle": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer rdc_xxxxxxxx" }
    }
  }
}
```

Los clientes que solo hablan stdio pueden usar [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) como puente: `npx -y mcp-remote http://localhost:8000/mcp --header "Authorization: Bearer rdc_xxxxxxxx"`.

Hay 52 tools, agrupadas en contexto, búsqueda de trabajo, tickets, colaboración, archivos y tiempo, planeación y Buzón. La lista completa está en el [README en inglés](README.md#13-ai-agents-over-mcp). Los agentes siguen la misma matriz de permisos y los mismos niveles de seguridad que las personas, y se pueden limitar a algunas tools.

**Folio** tiene su propio servidor MCP en `/mcp/folio`, con los mismos tokens; sus tools están en [MCP de Folio](#15-folio-los-docs-de-tu-equipo).

### 14. Teclado, paleta de comandos y temas

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¿Manos en el teclado? Presiona <kbd>?</kbd> para ver todos los atajos.

Presiona <kbd>?</kbd> para ver todos los atajos. Los principales:

| Teclas | Acción |
| --- | --- |
| <kbd>⌘</kbd> <kbd>K</kbd> | Paleta de comandos: tickets, proyectos, filtros y acciones |
| <kbd>c</kbd> | Crear ticket |
| <kbd>/</kbd> | Buscar |
| <kbd>g</kbd> <kbd>p</kbd> · <kbd>g</kbd> <kbd>m</kbd> | Ir a proyectos · mis tickets |
| <kbd>j</kbd> / <kbd>k</kbd> | Moverse en listas y boards |
| <kbd>e</kbd> <kbd>a</kbd> <kbd>m</kbd> <kbd>l</kbd> <kbd>p</kbd> | En un ticket: editar título, asignarme, mover, tags, prioridad |

<p align="center"><img src="docs/images/command-palette.png" alt="Paleta de comandos" width="820"></p>

Cambia entre claro y oscuro con el botón de la luna, y entre inglés y español en tu perfil o desde la paleta. Los atajos se pueden apagar en tu perfil.

**Úsalo como app de escritorio.** Radicle se puede instalar como app propia, con Radi en el Dock y su propia ventana: en Chrome da clic en **Instalar** en la barra de direcciones, o en Safari elige **Archivo → Añadir al Dock**.

### 15. Folio: los docs de tu equipo

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Radicle ya tiene una segunda app: **Folio**, para documentación. Abre el menú del logo o presiona <kbd>g</kbd> <kbd>f</kbd>, y <kbd>g</kbd> <kbd>d</kbd> para regresar a Docket.

Docket (el tracker de tickets) y Folio comparten personas, grupos, agentes y el inicio de sesión. Cada app abre donde la dejaste.

<p align="center"><img src="docs/images/folio-home.png" alt="Home de Folio" width="900"></p>

- **Navegación.** Un sidebar fijo como el de Docket, con el switch de apps en el mismo lugar: Inicio, Buscar, Para ti, Mis tareas, Aprobaciones, Favoritos y tus spaces. En el teléfono se abre como cajón.
- **Home.** Una portada tipo revista: el doc destacado, el último anuncio, AI Tools, los últimos posts, lo más leído y cada space con su número de docs. **Write** empieza una página o un blog post en cualquier space donde puedas crear.
- **Spaces.** Cada space abre en su portada: qué contiene, sus páginas y carpetas, quién participa (los admins con anillo lima), una búsqueda dentro del space y sus secciones: **Specs**, **Decisiones de arquitectura**, **Guías** y **Documentación**, que los admins del space muestran, esconden y reordenan. Los specs se filtran por proyecto de Docket y luego por sus features; las decisiones muestran primero las vigentes. **Administrar** abre las páginas, permisos, secciones y ajustes del space. Cada persona tiene además su space personal.

<p align="center">
  <img src="docs/images/folio-space.png" alt="La portada de un space con sus secciones" width="49%">
  <img src="docs/images/folio-specs.png" alt="Specs filtrados por proyecto y luego por sus features" width="49%">
</p>

<p align="center">
  <img src="docs/images/folio-decisions.png" alt="Decisiones de arquitectura, primero las vigentes" width="49%">
  <img src="docs/images/folio-guides.png" alt="Guías con un camino de primeros pasos" width="49%">
</p>

- **Radi en Folio.** El botón verde de Radi también está abajo a la derecha en Folio, con las herramientas de Folio: busca en los docs que puedes ver, responde citando la sección exacta y te escribe un borrador. En la sección Documentación, una tarjeta oscura de Radi te avisa cuando una página de referencia quedó vieja y ofrece actualizarla.
- **Administrar.** **Administrar** en un space abre su modo admin: páginas, permisos, qué secciones se ven y en qué orden, y ajustes.

<p align="center">
  <img src="docs/images/folio-docs-radi.png" alt="Documentación por módulo, con la tarjeta de Radi sobre una página vieja" width="49%">
  <img src="docs/images/folio-radi.png" alt="Radi respondiendo en Folio con citas" width="49%">
</p>
<p align="center">
  <img src="docs/images/folio-manage.png" alt="El modo admin de un space" width="49%">
  <img src="docs/images/folio-reader-nav.png" alt="Leyendo una página con su ruta, índice, anterior y siguiente" width="49%">
</p>
<p align="center"><img src="docs/images/folio-mobile.png" alt="El sidebar de Folio como cajón en el teléfono" width="300"></p>

- **Lectura.** Las páginas se leen como revista, con la ruta de regreso a su space y sección, la anterior y la siguiente de su carpeta, el índice "On this page", el dueño, estado, tipo, idioma y labels. El **modo enfoque** deja solo el texto y una barra de progreso, y recuerda tu elección. En claro y oscuro, como todo Radicle.
- **Escritura.** Un editor a pantalla completa guarda tu borrador mientras escribes. Presiona <kbd>/</kbd> para cualquier bloque (encabezados, listas, checklists, tablas, código, paneles, expandibles, columnas, imágenes, archivos y video) o usa atajos de Markdown. Pega o suelta imágenes para subirlas.

<p align="center">
  <img src="docs/images/folio-editor.png" alt="El editor con el menú /" width="49%">
  <img src="docs/images/folio-publish.png" alt="Publicar con metadata" width="49%">
</p>

- **Publicación.** Cada página lleva la metadata que tu equipo necesita: descripción, tipo de documento, labels, dueño, audiencias e idioma. Publicar la revisa campo por campo. Cada publicación es una versión inmutable: compara dos cualesquiera y restaura una vieja, que se vuelve una versión nueva.
- **Estado.** El dueño marca una página *In review* o *Verified*; la verificación vence a los días del space (90 por default), la página pasa a *Outdated* y su dueño recibe aviso. La búsqueda sube las verificadas y baja las vencidas.
- **Permisos.** Roles globales (reader, creator, admin) en **Folio → Admin**, permisos por space y restricciones por página. Una página restringida y todo lo que tiene abajo desaparecen para los demás: árbol, búsqueda, RQL, la home y el MCP.
- **Agentes y aprobación.** Los agentes escriben por MCP como cualquiera, pero lo que publican espera en **Approvals** hasta que un admin de Folio lo aprueba o lo rechaza con un comentario para el agente.

<p align="center">
  <img src="docs/images/folio-history.png" alt="Historial con el diff entre versiones" width="49%">
  <img src="docs/images/folio-approvals.png" alt="La cola de aprobación" width="49%">
</p>

- **Búsqueda.** Escribe una pregunta en la barra de arriba y Folio encuentra la sección que la responde, en español e inglés. La búsqueda híbrida mezcla palabras y significado (con un proveedor de IA para los embeddings); los filtros la acotan por space, tipo, tipo de documento, idioma o label. El mismo RQL de Docket consulta docs: `space = ai-tools AND #onboarding AND published >= -30d ORDER BY published DESC`.

<p align="center"><img src="docs/images/folio-search.png" alt="Resultados de búsqueda con las coincidencias resaltadas" width="820"></p>

- **Proveedor de IA.** **Admin → Settings → AI provider** define un solo proveedor para chat y embeddings (OpenAI, un servidor compatible con OpenAI como Voyage, Ollama, o Anthropic para chat). La llave se guarda cifrada; **Test connection** muestra dimensiones y latencia. Sin proveedor, la búsqueda usa solo palabras.
- **Escribir juntos.** Quienes editan una página escriben en ella al mismo tiempo: ves sus carets y selecciones en su color, quién está en el documento y su mouse con su nombre. Un agente que edita por REST o MCP aparece como "está escribiendo". Publicar toma lo que está en pantalla.
- **Live docs.** Para minutas y bitácoras: siempre editables, nunca se publican. Folio toma un snapshot cada 10 minutos con quién escribió desde el anterior; **Snapshots** los muestra y restaura cualquiera. Los agentes usan `create_live_doc` y `append_to_live_doc`.
- **Comentarios.** Comenta al pie de una página, o selecciona texto y presiona **Comentar** para anclar el hilo a esa frase: se queda en su lugar aunque editen alrededor, y si se borra el texto el hilo queda huérfano con su cita. Responde, menciona con `@`, resuelve y reabre. Comentar es el permiso `comment` del space.
- **Avisos.** La campana muestra al instante menciones, comentarios, páginas compartidas, tareas y envíos de agentes; **Perfil → Avisos** elige, por tipo, en la app y por email. Nunca recibes avisos de lo que haces tú.
- **Tareas y lo social.** Reacciona a páginas y comentarios, sigue una página, márcala como favorita y compártela con un mensaje. Los action items (`/` → Action item) tienen asignado y fecha y llegan a **Mis tareas**, agrupados en vencidas, hoy, próximas y sin fecha; marcarla ahí la marca en el documento.
- **Ordenar y mantener al día.** Mueve, copia y archiva páginas desde su menú (la sección **Archivados** del space las restaura). **Favoritos**, **Recientes** y **Para ti** te regresan a lo importante.

<p align="center">
  <img src="docs/images/folio-realtime.png" alt="Dos personas editando la misma página, con el caret de cada una" width="49%">
  <img src="docs/images/folio-comments.png" alt="Un hilo de comentario inline junto a su cita" width="49%">
</p>
<p align="center"><img src="docs/images/folio-tasks.png" alt="Mis tareas agrupadas por fecha" width="820"></p>

- **Templates.** Empieza una página desde un template (Build spec, Decision log, How-to, Meeting notes, Product requirements, Retrospectiva) o un space completo desde un template de space como **Equipo de ingeniería**, con sus carpetas y páginas. Los admins de Folio los editan en **Folio → Admin → Templates**.
- **La home a tu manera.** **Folio → Admin → Home** es un grid de 12 columnas: agrega destacados, anuncios, listas por space o label, consultas RQL, Para ti, lo más leído y texto; luego ve la vista previa y publica. Cada quien ve solo lo que puede leer.
- **Bloques visuales.** Desde `/`: diagramas Mermaid, gráficas (también desde la tabla de arriba), timelines, comparaciones lado a lado, fórmulas KaTeX, una lista viva de páginas por label y el bloque **Visual** para tu propio SVG o HTML animado, en sandbox y con el tema claro u oscuro. Los agentes los agregan por MCP (`insert_visual`, `insert_diagram`, `insert_chart`, `insert_timeline`).
- **Whiteboards y databases.** Dibuja con otros en un whiteboard de Excalidraw e incrústalo en cualquier página. Una database guarda filas con columnas por tipo, vistas como tabla, tarjetas o un tablero donde arrastras las tarjetas; incrusta cualquier vista en una página.
- **Embeds.** Pega un link de YouTube o Figma en su propia línea y se ve dentro de la página; los demás links quedan como tarjeta con su vista previa.
- **Tickets dentro de los docs.** Pega una clave o un link de Docket y se vuelve un chip con el estado y el responsable del ticket en vivo; el bloque **Tabla de tickets** lista los tickets de una consulta RQL de Docket. Selecciona texto y presiona **Crear ticket** (o usa el botón de un action item) para abrir un ticket ligado a esa sección. Cada ticket en Docket tiene un panel **Docs** con los docs que lo mencionan o lo ligan, y cada milestone lista los docs que lo nombran en su metadata.
- **Del build spec a sus tickets.** En un build spec, **Crear tickets** encuentra los entregables (la tabla de entregables o los encabezados numerados) y crea una tarea de Docket por cada uno, con sus criterios de aceptación como checklist y un link a su sección. Volver a correrlo solo agrega los nuevos. El bloque **Avance de tickets** (`::progress{}`) muestra el estado, el responsable y el checklist de cada ticket en vivo.
- **Pregunta a los docs.** **Radi**, el botón verde abajo a la derecha en Folio (o <kbd>A</kbd>), responde con los docs que puedes leer, cita cada afirmación con `[n]` y cada fuente abre el doc en esa sección con el párrafo resaltado. Si los docs no lo dicen, lo dice y sugiere a quién preguntar; **Folio → Admin → Chat** junta esas preguntas para saber qué escribir.
- **IA en el editor.** **IA** resume la página; selecciona texto para reescribirlo más claro, más corto, más formal o en otro idioma; **Publicar** sugiere descripción, labels y tipo de documento para los campos vacíos. Un **Glosario** de términos que aprueba un admin muestra su definición al pasar el cursor. La IA solo propone: nada cambia hasta que lo aceptas, y nada aparece sin proveedor de IA o con la IA apagada en el space.

<p align="center">
  <img src="docs/images/folio-visual.png" alt="Un bloque visual animado y un diagrama Mermaid en un post" width="49%">
  <img src="docs/images/folio-database.png" alt="Una database vista como tablero agrupado por estado" width="49%">
</p>
<p align="center">
  <img src="docs/images/folio-chat.png" alt="El chat de los docs respondiendo con una cita que abre la sección resaltada" width="49%">
  <img src="docs/images/folio-build-spec.png" alt="Los entregables de un build spec y el avance en vivo de sus tickets de Docket" width="49%">
</p>

- **Páginas públicas.** **Compartir → Link público** le da a una página o a todo un space un link de solo lectura que abre sin cuenta, en la vista revista, sin datos de personas y oculto de los buscadores por default. Las páginas restringidas nunca salen por ahí, y **Revocar** lo vuelve un 404. Solo los admins del space los crean.
- **Exportar.** **Exportar** en una página o un space baja un PDF que se ve como la lectura (lo imprime Chromium sin interfaz, así que visuales, diagramas y fórmulas salen como en pantalla), un Word, un sitio HTML que abre desde el disco o Markdown con front matter. Construye con `--build-arg PDF=false` para dejar fuera Chromium (unos 290 MB).
- **Importar.** **Folio → Admin → Importar** trae un space de Confluence (export HTML), un export de Notion (Markdown y CSV, donde los CSV se vuelven databases), archivos de Word o carpetas de Markdown. Un dry run muestra cada página, sus autores (por email), labels y archivos antes de crear nada; las páginas llegan como borrador, e importar el mismo export otra vez al mismo space las actualiza en vez de duplicarlas.
- **Slack, Teams, webhooks y reglas.** **Admin → Integraciones** publica lo que pasa en un space en canales de Slack o Teams, responde `/radicle search` y `/radicle ask` (el chat de los docs, con citas, como quien pregunta) y muestra la vista previa de los links de Folio pegados en Slack a quien puede verlos. Los webhooks mandan eventos firmados (`page.published`, `page.outdated`, `submission.created`…) con reintentos y un log de entregas. Las reglas de automatización corren con un evento o un horario y avisan a un canal o una persona, cambian el estado de una página, agregan un label, abren un ticket en Docket o archivan; una regla lista avisa en un canal cuando una página se vence.
- **Calendarios.** Cada space puede tener calendarios con vista de mes y semana, eventos por categoría (release, vacaciones, guardia…), personas y los milestones de proyectos de Docket. Suscríbete desde Google Calendar u Outlook con su link iCal, o pon un calendario dentro de una página o en la home.
- **Plugins.** **Admin → Plugins** instala plugins en JSON que agregan bloques al editor, dibujados en el mismo sandbox que el bloque Visual (sin red ni acceso a la página). El ejemplo **Cuenta regresiva** se instala con un clic.
- **Analytics.** Dueños y admins del space ven las vistas, lectores únicos y tiempo de lectura de cada página; **Folio → Admin → Analytics** muestra las páginas más leídas, los spaces más activos, lo que se buscó sin encontrar y las preguntas del chat sin respuesta: lo que toca documentar. Los agentes reciben esa lista con `get_search_gaps`.

<p align="center">
  <img src="docs/images/folio-public.png" alt="Una página abierta por su link público, sin cuenta" width="49%">
  <img src="docs/images/folio-import.png" alt="El dry run de una importación de Confluence" width="49%">
</p>
<p align="center">
  <img src="docs/images/folio-integrations.png" alt="Admin, Integraciones: Slack, webhooks y reglas de automatización" width="49%">
  <img src="docs/images/folio-calendar.png" alt="El calendario de releases de un space con milestones de Docket" width="49%">
</p>

- **MCP de Folio.** `/mcp/folio` acepta los mismos tokens que `/mcp`. Los agentes buscan (`search_docs`, `query_docs`), leen páginas en Markdown (`get_page`), ven qué pide publicar (`get_metadata_schema`), escriben (`create_page`, `update_draft`) y mandan a aprobación (`submit_for_publication`, `list_my_submissions`). También preguntan a los docs (`ask_docs`), ligan docs con tickets (`link_ticket`, `get_docs_for_ticket`) y convierten un build spec en tickets (`create_tickets_from_build_spec`, que solo simula salvo con `dry_run=false`). Exportan una página (`export_page`), leen y agregan eventos del calendario (`list_calendar_events`, `add_calendar_event`) y ven los lectores de una página y lo que se busca sin encontrar (`get_page_analytics`, `get_search_gaps`). Tres prompts guían a un agente que trabaja en un codebase: `weekly_changes_post`, `document_module` y `build_spec_from_discussion`; todos terminan esperando aprobación. Los admins eligen qué tools de Folio puede usar cada agente, igual que con las de Docket.

```bash
claude mcp add --transport http radicle-folio https://radicle.example.com/mcp/folio \
  --header "Authorization: Bearer rdc_el_token_del_agente"
```

## ⚙️ Configuración

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Las perillas para quien administra Radicle.

Todo se configura con variables de entorno (ve [`.env.example`](.env.example)).

| Variable | Default | Qué hace |
| --- | --- | --- |
| `RADICLE_SECRET_KEY` | **obligatoria** | Cifra los secretos guardados (SSO, captcha) y firma links y la cookie del SSO. Genérala con `openssl rand -hex 32` y no la cambies después. |
| `RADICLE_BASE_URL` | `http://localhost:8000` | URL pública: cookies, snippets de MCP y links del formulario público. |
| `RADICLE_PORT` | `8000` | Puerto del contenedor `app` en el host. |
| `RADICLE_TIMEZONE` | `UTC` | Zona horaria de las fechas relativas en RQL y reportes. |
| `RADICLE_WORKDAYS` | `mon,tue,wed,thu,fri` | Días hábiles de los burndowns. |
| `RADICLE_STORAGE` | `local` | `local` guarda adjuntos en un volumen de Docker; `s3` usa cualquier S3 compatible (AWS, MinIO, R2) con `RADICLE_S3_*`. |
| `RADICLE_MAX_UPLOAD_MB` | `25` | Tamaño máximo por archivo. |
| `RADICLE_IMAGE_DEFAULT_RESIZE` | `large` | Tamaño default de imágenes: `original`, `large` (2048 px), `medium` o `small`. |
| `RADICLE_AUDIT_RETENTION_DAYS` | `730` | Días que se guarda el audit log. |
| `RADICLE_SESSION_DAYS` | `14` | Duración de la sesión (se renueva con el uso). |
| `RADICLE_ASSISTANT_*` | sin definir | El LLM de Radi; ve [Conoce a Radi](#-conoce-a-radi). Sin él, Radi responde con la guía. |
| `RADICLE_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_FROM`, `_TLS` | sin definir, `587` | Avisos por email. Sin host, los avisos son solo en la app. El puerto 465 usa TLS implícito. |
| `RADICLE_LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | Intentos de inicio de sesión por IP por minuto. |
| `POSTGRES_*` | `radicle` | Credenciales de la base. Cambia el password en producción. |

El contenedor `worker` corre los trabajos en segundo plano: propagación de templates, variantes de imágenes, ediciones masivas grandes, ranking, snapshots diarios y retención del audit log. Si no está corriendo, esos trabajos esperan en la cola.

## 🏗️ Arquitectura

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Cómo encajan las piezas: una app, un worker y una base de datos.

<p align="center"><img src="docs/images/architecture.svg" alt="Arquitectura de Radicle" width="900"></p>

| Capa | Stack |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic 2, Procrastinate (jobs sobre Postgres), Authlib (OIDC) |
| Base de datos | PostgreSQL 16 con pgvector, búsqueda full-text en inglés y español |
| Frontend | React 18, TypeScript, TanStack Router y Query, styled-components, dnd-kit, Recharts, i18next |
| MCP | SDK oficial de MCP para Python, Streamable HTTP en `/mcp` |
| Calidad | pytest con testcontainers (Postgres y Keycloak reales), mypy estricto, ruff, Vitest, E2E con Playwright |

La lógica de negocio vive solo en los servicios: `backend/radicle/platform/services/` para lo que comparten las apps y `backend/radicle/docket/services/` para los tickets. Los routers REST y las tools del MCP validan y llaman a esos servicios, así la UI, la API y los agentes siguen siempre las mismas reglas.

## 🧑‍💻 Desarrollo

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** ¿Quieres meterle mano a Radicle (o a mí)? Empieza aquí.

| Parte | Requisitos | Comandos |
| --- | --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (para tests) | `cd backend && uv sync`, `uv run uvicorn radicle.main:app --reload`, `uv run pytest` |
| Frontend | Node 22, pnpm 9 | `cd frontend && pnpm install`, `pnpm dev` (proxy a `:8000`), `pnpm check` |
| Base local | Docker | `docker compose up -d db` y luego `cd backend && uv run alembic upgrade head` |

```bash
# Córrelo antes de cada push (el CI de GitHub Actions está en pausa por ahora)
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy radicle && uv run pytest --cov
cd frontend && pnpm check && pnpm build
scripts/smoke.sh   # construye la imagen y la levanta en limpio en el puerto 8001
```

- Los tests de backend levantan PostgreSQL 16 con testcontainers (no SQLite). Los marcados `slow` también levantan Keycloak.
- Si cambias la API: `cd backend && uv run python ../scripts/export_openapi.py` y luego `cd frontend && pnpm api:types`.
- Datos de demo: `cd backend && uv run python ../scripts/seed.py --tickets 400 --project PA`, y entra como `fernando@example.com` / `radicle-demo`.
- Los documentos de diseño, decisiones (ADRs) y el progreso están en [`docs/`](docs/), en español.

## 🗺️ Roadmap y pendientes

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Lo que sigue. ¡Las ideas son bienvenidas!

Las etapas 1 a 4 están completas: core y MCP, configuración y trabajo diario, planeación y visibilidad, y el Buzón con control de acceso. Esto es lo que sigue; las ideas y la ayuda son muy bienvenidas.

**Radicle Folio (docs)**

- [x] Fase 0: plataforma compartida (backend partido en `platform`, `docket` y `folio`, autorización genérica, proveedor de IA, switch de suite, esqueleto de Folio).
- [x] Fase 1: spaces y páginas, editor, publicación con versiones, permisos, envíos de agentes con aprobación, búsqueda RAG y MCP de Folio.
- [x] Fase 2: edición en tiempo real con carets y punteros con nombre, comentarios anclados al texto, menciones, avisos en la app y por email, reacciones, seguir, compartir, action items y Mis tareas, live docs con snapshots, mover, copiar y archivar páginas, dueños y estados que vencen, y el feed Para ti.
- [x] Fase 3: templates de páginas y spaces, editor de la home, bloques visuales (diagramas, gráficas, timelines, fórmulas y visuales en sandbox), whiteboards, databases y embeds.
- [x] Fase 4: tickets dentro de los docs, build specs que crean sus tickets, ligas a milestones y áreas, el chat de los docs con citas, IA en el editor con glosario y prompts del MCP para agentes que escriben desde un codebase.
- [x] Fase 5: páginas públicas, exportar a PDF, Word, HTML y Markdown, importar desde Confluence, Notion, Word y Markdown, Slack y Teams, webhooks, reglas de automatización, plugins, calendarios con feed iCal, analytics y el audit de Folio.

**Etapa 5: integraciones**

- [ ] Notificaciones (en la app y por email), watchers y suscripciones a filtros, incluido el email a quien mandó algo por el formulario público cuando cambia.
- [ ] Reglas de automatización ("cuando pase X, haz Y") y webhooks salientes.
- [ ] Integración con Git: un PR mergeado mueve su ticket a Done.
- [ ] Integraciones de chat (Slack, Microsoft Teams) y links a documentos.
- [ ] Importar y exportar (Jira, CSV, JSON).
- [ ] Sistema de plugins.
- [ ] App móvil nativa con notificaciones push.
- [ ] Más ayudas de IA: resúmenes, detección de duplicados, sugerencias de triage. (Radi, la guía dentro de la app, ya está.)

**Más adelante, quizá**

- [ ] SSO con SAML (hoy solo OpenID Connect).
- [ ] Roles además de admin, member y viewer.
- [ ] Más idiomas para la UI y el formulario público (hoy inglés y español).

**Folio: siguientes arreglos** (de la nueva navegación; cada uno tiene su ticket)

- [ ] Modo oscuro: el hero del space casi se confunde con la página, y la tarjeta de Radi se ve gris en vez de destacar (RAD-69).
- [ ] El filtro de proyecto en Specs y Decisiones de arquitectura muestra la clave (RAD) en lugar del nombre (Folio) (RAD-70).
- [ ] Avisar que una página de referencia quedó vieja cuando cambia el código que documenta, no solo cuando vence su verificación (RAD-71).
- [ ] Guardar vistas de Specs y Decisiones por persona en vez de copiar un link (RAD-72).
- [ ] El próximo evento del calendario en la portada del space (RAD-73).

**Pendientes y arreglos chicos** (buenas primeras contribuciones)

- [ ] El bundle principal del frontend pasa de 500 kB; hay que partirlo por ruta.
- [ ] El burndown dibuja cero en los días antes de iniciar un sprint cuando su fecha de inicio quedó en el pasado.
- [ ] El audit log muestra IDs internos en algunos objetivos (niveles de seguridad, proveedores SSO) en lugar de sus nombres.
- [ ] `test_periods.py` puede fallar de vez en cuando si dos cambios de estado comparten timestamp.

## 🤝 Cómo contribuir

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Toda contribución cuenta, desde un typo hasta una feature. ¡Ven a saludar!

Radicle es un proyecto de la comunidad y toda contribución cuenta: reportes de bugs, documentación, traducciones, diseño y código.

<p align="center"><img src="docs/images/contributing-flow.svg" alt="Cómo entra un cambio" width="900"></p>

En corto:

- **Una sola cosa por PR**, con sus tests.
- **PRs chicos**: menos de **500 líneas cambiadas** y menos de **100 archivos**. Si es más grande, pártelo en pasos.
- **Ramas** con el formato `tipo/descripcion-corta`:

| Tipo | Para qué | Ejemplo |
| --- | --- | --- |
| `feat/` | Algo nuevo | `feat/csv-import` |
| `minor/` | Cambios menores y ajustes | `minor/board-card-spacing` |
| `fix/` | Bugs | `fix/burndown-backdated-sprint` |
| `refactor/` | Reordenar código sin cambiar la funcionalidad | `refactor/split-ticket-service` |
| `docs/` | Solo documentación | `docs/sso-okta-guide` |

La guía completa, con el setup, las reglas de código, los mensajes de commit y cómo funcionan las revisiones, está en **[CONTRIBUTING.md](CONTRIBUTING.md)** (en inglés).

## 📜 Licencia

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Software libre, y así se queda.

Radicle es software libre bajo la **[GNU Affero General Public License v3.0](LICENSE)** (AGPL-3.0-only).

En corto: puedes usar, estudiar, modificar y compartir Radicle, también en tu empresa y para trabajo comercial. Si lo modificas y dejas que otras personas usen tu versión, **incluso por red** (por ejemplo, si lo hospedas para tu equipo o tus clientes), tienes que ofrecerles el código fuente de tus cambios bajo la misma licencia. Así las mejoras regresan a la comunidad en lugar de quedarse en forks privados.

Al contribuir, aceptas que tus contribuciones se licencian bajo los mismos términos.
