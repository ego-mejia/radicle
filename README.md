<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-dark.svg">
    <img src="docs/images/logo.svg" alt="Radicle" width="320">
  </picture>
</p>

<p align="center">
  <b>The open source ticket tracker where people and AI agents work the same project.</b><br>
  Self-hosted · MCP built in · Inbox for your users · AGPLv3
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: AGPL v3" src="https://img.shields.io/badge/license-AGPLv3-4D7C0F?style=flat-square"></a>
  <a href="CONTRIBUTING.md"><img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-C6F432?style=flat-square&labelColor=1A2E05"></a>
  <img alt="MCP tools" src="https://img.shields.io/badge/MCP-52%20tools-C6F432?style=flat-square&labelColor=1A2E05">
  <a href="README.es.md"><img alt="Leer en español" src="https://img.shields.io/badge/lee%20en-espa%C3%B1ol-F1F2F4?style=flat-square"></a>
</p>

<p align="center">
  <img src="docs/images/board.png" alt="Radicle board" width="900">
</p>

> 🌱 **Radicle** is named after the radicle: the first root a seed puts out when it sprouts.

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Hi! I'm Radi, the green fellow in the corner of the app (and in the logo). I'll walk you through this README: look for my notes at the start of each section.


## Contents

- [Why Radicle](#-why-radicle)
- [Quick start](#-quick-start)
- [Meet Radi](#-meet-radi)
- [User guide](#-user-guide)
  - [1. Create your first project](#1-create-your-first-project)
  - [2. Add people](#2-add-people)
  - [3. Work with tickets](#3-work-with-tickets)
  - [4. Boards](#4-boards)
  - [5. Search with RQL](#5-search-with-rql)
  - [6. Sprints and backlog](#6-sprints-and-backlog)
  - [7. Timeline and milestones](#7-timeline-and-milestones)
  - [8. Reports and dashboards](#8-reports-and-dashboards)
  - [9. Inbox and public form](#9-inbox-and-public-form)
  - [10. Permissions, groups and restricted tickets](#10-permissions-groups-and-restricted-tickets)
  - [11. Single sign-on (SSO)](#11-single-sign-on-sso)
  - [12. Audit log](#12-audit-log)
  - [13. AI agents over MCP](#13-ai-agents-over-mcp)
  - [14. Keyboard, command palette and themes](#14-keyboard-command-palette-and-themes)
  - [15. Folio and the AI provider](#15-folio-and-the-ai-provider)
- [Configuration](#%EF%B8%8F-configuration)
- [Architecture](#%EF%B8%8F-architecture)
- [Development](#-development)
- [Roadmap and known issues](#%EF%B8%8F-roadmap-and-known-issues)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Why Radicle

| | |
| --- | --- |
| 🤖 **Agents are teammates** | A Model Context Protocol (MCP) server ships inside the app. Claude, Cursor or any MCP client can take a ticket, move it, tick its checklist, log time and comment, and it all shows up in the history as done by that agent. |
| 📮 **Hear your users** | Every project can open a public form. Complaints and ideas land in an **Inbox**, you score them on an impact × effort matrix and turn the good ones into tasks or bugs. The sender follows it with a tracking code. |
| 🔒 **Serious access control** | Groups, a permission matrix per project, restricted tickets that are invisible everywhere (search, boards, reports, MCP), OpenID Connect SSO and an append-only audit log. |
| 🗺️ **Plan and see** | Kanban and Scrum boards, sprints, a timeline with forecasts, ten agile and general reports and drag-and-drop dashboards. |
| 🟢 **A guide inside** | Radi, the mascot, answers how-to questions from the usage guide and, with an LLM of your choice, walks you through the screen step by step. |
| ⚡ **Fast to work in** | A query language (RQL), a command palette, keyboard shortcuts for everything and light and dark themes. In English and Spanish. |
| 🏠 **Yours** | One `docker compose up`. PostgreSQL, your server, your data. |

## 🚀 Quick start

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Three commands and you are in. The first visit asks you to create the instance admin.

You need Docker with Compose.

```bash
git clone https://github.com/ego-mejia/radicle.git
cd radicle
cp .env.example .env
# Required: a long random secret. It encrypts stored secrets and signs links.
echo "RADICLE_SECRET_KEY=$(openssl rand -hex 32)" >> .env
docker compose up -d
```

Open <http://localhost:8000>. The first visit shows a **setup** screen where you create the instance admin.

Three containers start: `app` (web app, REST API and MCP), `worker` (background jobs) and `db` (PostgreSQL 16). The REST API lives at `/api/v1` and its interactive docs at `/api/docs`.

> [!TIP]
> In production, put Radicle behind HTTPS and set `RADICLE_BASE_URL` to its public URL. Cookies switch to `Secure` on their own.

## 🟢 Meet Radi

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** That's me! Click me in the bottom-right corner of any page and ask how to do something. My eyes follow your pointer, and I get a little bigger when you hover me.

Radi answers questions about using Radicle and shows you where things are.

- **Without any setup** Radi answers from the built-in usage guide (English and Spanish) and offers a ready-made tour for the main topics: click **Show me**.
- **With an LLM** (Anthropic, OpenAI or any OpenAI-compatible server such as Ollama), Radi writes the answer in the language you asked in and walks you through the screen: a white cursor with a green glow moves to each button, opens pages and dialogs, highlights each field and explains it. It never clicks **Create**, **Save** or **Add** for you; it only points at them.
- After each answer Radi shows the suggested questions again, so you can keep asking.

<p align="center">
  <img src="docs/images/radi-chat.png" alt="Radi answering in the chat" width="49%">
  <img src="docs/images/radi-tour.png" alt="Radi's tour explaining the create project dialog" width="49%">
</p>

**Set up the LLM** in **Admin → Settings → Assistant**: pick the provider, paste the API key (stored encrypted, never shown again) and optionally the model and base URL, then click **Test**. Environment variables override the app settings, which suits deployments that keep secrets out of the database:

| Variable | What it does |
| --- | --- |
| `RADICLE_ASSISTANT_PROVIDER` | `anthropic`, `openai` or `none` |
| `RADICLE_ASSISTANT_API_KEY` | The provider's API key |
| `RADICLE_ASSISTANT_MODEL` | Optional; defaults to `claude-haiku-5-5` or `gpt-4o-mini` |
| `RADICLE_ASSISTANT_BASE_URL` | Optional; for OpenAI-compatible servers, like `http://ollama:11434/v1` |

<p align="center"><img src="docs/images/assistant-settings.png" alt="Assistant settings" width="820"></p>

Radi can only point at a fixed catalog of places in the app, so a model cannot invent buttons. The guide it answers from lives in `backend/radicle/docket/services/assistant/guide/`.

## 📖 User guide

### 1. Create your first project

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Ask me "how do I create a project?" and I'll take you to the button and explain every field of the dialog.

From **Projects**, click **Create project**. Give it a name and a short **key** (2 to 10 uppercase letters or digits, like `PAY`). Every ticket gets the key as a prefix (`PAY-12`), and it cannot change later.

Pick a **template**. It brings the workflows (statuses and transitions for Task, Bug and Draft), custom fields and policies. Choose **Linked** to keep receiving the template's changes, or **Independent** to copy it once and edit it freely.

<p align="center"><img src="docs/images/create-project.png" alt="Create project dialog" width="820"></p>

Then, in the project's **Settings**, add **Areas** (Backend, Mobile, Legal...) and **Milestones** (V1, V2...). Every task and bug belongs to an area; milestones are optional. Give each area a color and an icon (click the square next to its name): they show on board cards, swimlanes and the timeline.

To rename a project or change its description, hover its card in **Projects** and click the pencil. The key never changes. Projects are never deleted: a project admin can **Archive** one in **Settings → General**, which keeps it read-only with all its history.

### 2. Add people

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Projects are better with company. Here is how to bring people, groups and agents in.

People are created by an instance admin in **Admin → Users**, or arrive through [SSO](#11-single-sign-on-sso). To give them access to a project, open **Settings → Members**, search for a person, agent or group in the dropdown, pick a role and click **Add**. Change a role from the dropdown on each row:

| Role | Can |
| --- | --- |
| **Viewer** | Read everything in the project and vote. |
| **Member** | Everything a viewer can, plus create, edit, move and comment on tickets. |
| **Admin** | Everything, plus manage members, settings, workflows and permissions. |

<p align="center"><img src="docs/images/members.png" alt="Project members" width="820"></p>

For teams, create a **group** in **Admin → Groups** (for example `legal-team`) and give the group a role in the project. Everyone in it gets access at once, and so does anyone who joins the group later. When someone has several roles (direct and through groups), the highest one wins.

AI agents are added the same way: see [AI agents over MCP](#13-ai-agents-over-mcp).

### 3. Work with tickets

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Tickets are where the work lives. Press <kbd>c</kbd> anywhere to create one.

Press <kbd>c</kbd> or click **Create ticket**. There are three types:

- **Task**: work to do.
- **Bug**: something broken.
- **Draft**: an idea or request that is not decided yet. Drafts live in the [Inbox](#9-inbox-and-public-form).

<p align="center"><img src="docs/images/ticket.png" alt="A ticket with checklist, link, comments and time" width="820"></p>

A ticket has a markdown description with a **checklist**, plus priority, area, milestone, assignee, collaborators, dates, estimate, tags and a parent. Below that you find attachments (images are resized for you), subtickets, links (`blocks`, `relates to`, `duplicates`, `clones`), comments with `@mentions` and reactions, and the full **history**.

- **Move it** with the status button. Workflows can ask for a resolution, a comment or a finished checklist before a transition.
- **Log time** with **Log time**. Spent and remaining hours update right away.
- **Vote** with 🙋 to show it matters to you.
- From the **⋯** menu you can clone it, move it to another project or delete it (admins can restore deleted tickets).

<p align="center"><img src="docs/images/ticket-history.png" alt="Ticket history" width="820"></p>

### 4. Boards

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Drag a card and drop it where you want it: it stays right there and glows. Drop it in Done and it shines brighter!

Each project starts with a Kanban board called **Main**, with **To Do**, **In Progress**, **In Review** and **Done**. Drag cards between columns and they land exactly where you drop them; a moved card flashes once, and one that reaches a done column flashes brighter. Dropping a card in **Done** closes it as *Done* without asking; pick *Won't do* or *Duplicate* from the ticket itself. Quick filters (**My tickets**, **Only bugs**, `#backlog`, **Blocked**) and the filter bar narrow it down.

Cards show their area (with its icon) and milestone like Jira's labels, plus how many subtickets they have. Click the area or milestone on a card to change it from a menu, without opening the ticket.

**Swimlanes** split the board into rows by area, assignee, priority, milestone, parent or type, like several boards stacked. Click a row header to fold it, or use **Collapse all**; Radicle remembers which rows you folded.

<p align="center">
  <img src="docs/images/board-lanes.png" alt="Board with swimlanes by area" width="49%">
  <img src="docs/images/board-dark.png" alt="Board in dark mode" width="49%">
</p>

Admins create more boards with **New board** and set them up in **Configure**:

- **Source**: an RQL query, so a board can cover one area or several projects.
- **Columns**: by status or by category, with **WIP limits**. Soft limits turn the column red; hard limits block the move (an admin can force it).
- **Card fields** and **quick filters**.

### 5. Search with RQL

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Want something precise? RQL finds it. In **List**, the **Filter** button builds simple queries for you.

RQL (Radicle Query Language) works in the search bar, in **List**, in boards and in saved filters:

```text
type = bug AND priority >= high AND assignee = currentUser()
project IN (PA, MOB) AND category != done ORDER BY due ASC
text ~ "checkout" AND updated >= -7d
sprint = active AND #backlog
classification = complaint AND origin = user ORDER BY votes DESC
```

Mistakes are underlined in place, with what was expected, and the editor autocompletes fields and values. Save a query as a **filter** to reuse it, share it or put it on a dashboard. Agents read the full guide as the MCP resource `radicle://guide/rql`.

**List** shows tickets in a table. Click **Filter** above it to filter by type, status, priority, assignee, area or milestone without writing RQL (each filter is a chip you can remove), **Group by** to split the rows into groups you can fold, and **Saved filters** to reuse queries. Tickets with subtickets have an arrow that opens their tasks and bugs right below them.

<p align="center">
  <img src="docs/images/list-filters.png" alt="List with the filter menu" width="49%">
  <img src="docs/images/list-rql.png" alt="List with an RQL query" width="49%">
</p>

### 6. Sprints and backlog

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Planning in sprints? You need a Scrum board first; ask me and I'll show you where.

Create a board of kind **Scrum** to plan in sprints. Then, in **Backlog**:

1. Click **New sprint** and set a goal, dates and capacity in hours.
2. Drag tickets in. The bar shows committed hours against capacity and warns about tickets without an estimate.
3. **Start sprint**. What is inside becomes the commitment.
4. **Complete sprint**. Unfinished tickets go back to the backlog (tagged `#backlog`) or to the next sprint, and the sprint report is saved.

<p align="center"><img src="docs/images/backlog.png" alt="Backlog with an active and a future sprint" width="820"></p>

### 7. Timeline and milestones

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** My favorite part: when the last ticket of a milestone is done, I throw a party.

**Timeline** draws tickets over time, grouped by milestone or area, by week, month or quarter. Drag a bar to change its dates, or drag a ticket from **Without dates** onto the timeline to give it some. A ticket with only a due date gets a faded bar from the day it was created (one with only a start date, a faded bar as long as its estimate) until you set both dates. Impossible dependencies (a ticket that starts before what blocks it ends) turn red, and milestones show their forecast.

<p align="center"><img src="docs/images/timeline.png" alt="Timeline" width="820"></p>

**Milestones** are goals with an optional target date, like a release. When the last open ticket of a milestone reaches done, Radicle celebrates: confetti, Radi cheering and the numbers behind it (tickets shipped, hours invested, bugs squashed, tasks, ideas, days to ship, and the people and AI agents who did it). **Share on LinkedIn** copies a ready-made image to your clipboard and opens a post with the text filled in; **Download image** saves it.

<p align="center">
  <img src="docs/images/milestone-celebration.png" alt="Milestone celebration" width="49%">
  <img src="docs/images/milestone-card.png" alt="Image to share on LinkedIn" width="49%">
</p>

### 8. Reports and dashboards

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Numbers, charts and a CSV for each one. Every person only sees the tickets they may see.

**Reports** has burndown, burnup, velocity, cumulative flow, control chart, sprint report, created vs resolved, distribution, milestone progress (with a forecast and an "at risk" flag) and time. Each one comes with its data table and **Export CSV**.

<p align="center"><img src="docs/images/reports.png" alt="Cumulative flow report" width="820"></p>

**Dashboards** put widgets on a grid you arrange by dragging: counts, distributions, milestone progress, burndown, blocked tickets, filter results and markdown notes. A dashboard can be private, shared with a project or shared with the whole instance, and everyone sees only the tickets they are allowed to see. Each project has its own **Summary** dashboard.

<p align="center"><img src="docs/images/summary.png" alt="Project summary dashboard" width="820"></p>

### 9. Inbox and public form

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Your users can tell you what they think, even without an account. Their ideas land here.

The **Inbox** collects Drafts: ideas from the team, requests from agents, and complaints, suggestions and ideas from people **without an account** who use the public form.

<p align="center"><img src="docs/images/inbox-flow.svg" alt="From feedback to ticket" width="900"></p>

**Open the public form.** In **Settings → Inbox**, switch it on and choose the slug, the texts, which kinds people can send, whether email is required, attachments and the captcha. ALTCHA is the default and needs no third party; Turnstile and hCaptcha also work. Then share the link: `https://your-radicle/b/<slug>`.

<p align="center">
  <img src="docs/images/public-form.png" alt="Public form" width="49%">
  <img src="docs/images/public-tracking.png" alt="Tracking page" width="49%">
</p>

Every submission gets a **tracking code**. The tracking page shows its state (Received, In review, Accepted or Closed) and your public note, never internal details. A honeypot, rate limits, a minimum fill time and link limits keep spam out.

**Triage.** The Inbox has tabs for New, In review, Approved and Discarded, with filters by classification and origin.

- Score each item with **Impact** and **Effort** (1 to 5).
- Switch to **Matrix** to see the quick wins at a glance. Drag a dot to rescore it.
- **Approve and convert** turns the Draft into a Task or Bug in the same ticket, so votes, comments and history stay.
- **Mark duplicate** moves its voters to the original. **Discard** can leave a note for the sender.

<p align="center">
  <img src="docs/images/inbox.png" alt="Inbox table" width="49%">
  <img src="docs/images/inbox-matrix.png" alt="Impact by effort matrix" width="49%">
</p>

### 10. Permissions, groups and restricted tickets

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Who sees what, and who can do what. Restricted tickets are invisible everywhere, even to me.

<p align="center"><img src="docs/images/access-model.svg" alt="Who can see and do what" width="900"></p>

- **Permission matrix** (**Settings → Permissions**): switch each of the 20 permissions on or off for members and viewers. They cover creating, editing, moving and deleting tickets, comments, attachments, time, votes, links, security and inbox triage. The same rule applies in the UI (buttons disappear), the API (403 naming the missing permission) and MCP.
- **Security levels** (**Settings → Levels**): create a level like *Legal confidential* and grant it to groups or people. A ticket with that level does not exist for anyone else: not in search, boards, reports, dashboards, links, history or MCP. If you want, its reporter, assignee and collaborators can still see it.

<p align="center">
  <img src="docs/images/permissions.png" alt="Permission matrix" width="49%">
  <img src="docs/images/security-levels.png" alt="Security levels" width="49%">
</p>

### 11. Single sign-on (SSO)

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Let people sign in with the account they already have.

In **Admin → SSO**, add OpenID Connect providers (Google, Microsoft Entra ID, Okta, Keycloak, Authentik...) with their issuer URL, client ID and secret. Register the callback URL shown in the form with your provider.

- **Allowed domains** decide who gets an account automatically. An existing account with the same verified email is linked.
- **Group mapping** syncs the provider's groups with Radicle groups on every sign-in. Only mapped groups are touched.
- In **Admin → Settings** you can turn off password sign-in. The first instance admin can still sign in with a password: that is your way back in if the provider fails.

<p align="center"><img src="docs/images/sso.png" alt="SSO providers" width="820"></p>

### 12. Audit log

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Every administrative change, written down forever. Nobody can edit it, not even admins.

**Admin → Audit log** records 39 kinds of administrative actions: users, tokens, agents, projects, members, groups, permissions, security levels, deletions, moves, bulk edits, templates, workflows, Inbox settings and SSO. Each entry says who, when, from which IP, and what changed (before and after). Filter by person, action, project and dates, and export to CSV. Project admins see their projects' entries in **Settings → Audit log**.

The log is **append-only**: the database itself rejects updates and deletes. Entries older than `RADICLE_AUDIT_RETENTION_DAYS` (730 by default) are purged.

<p align="center"><img src="docs/images/audit.png" alt="Audit log" width="820"></p>

### 13. AI agents over MCP

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Agents are teammates here, just like me. Give them a token and a project and they get to work.

Agents are users of kind *agent*, with their own handle, tokens, history and permissions.

1. Go to **Admin → Users → New user**, choose **Agent (LLM or worker)** and copy the token (`rdc_...`). It is shown only once, together with ready-to-paste MCP snippets. (**Admin → Agents → New agent** does the same.)
2. Choose what it may do over MCP. Leave **All tools** on, pick **Read only**, or tick the exact tools: for example, a triage bot that can only read and score the Inbox.
3. Add the agent to a project in **Settings → Members**, usually as **Member**.
4. Connect your MCP client.

<p align="center"><img src="docs/images/agent-mcp-permissions.png" alt="MCP permissions of an agent" width="820"></p>

You can change an agent's tools any time with **MCP permissions** in Users or Agents. Tools that are off disappear from the agent's tool list and are refused if called. They add to the project permissions and security levels; they never replace them. Every change is recorded in the audit log.

**Claude Code**

```bash
claude mcp add --transport http radicle http://localhost:8000/mcp \
  --header "Authorization: Bearer rdc_xxxxxxxx"
```

**Clients with a JSON config** (Claude Desktop, Cursor, VS Code...)

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

Clients that only speak stdio can use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) as a bridge: `npx -y mcp-remote http://localhost:8000/mcp --header "Authorization: Bearer rdc_xxxxxxxx"`.

<details>
<summary><b>All 52 tools</b></summary>

| Group | Tools |
| --- | --- |
| Context | `whoami`, `list_projects`, `get_project`, `get_ticket_schema` |
| Find work | `search_tickets`, `my_tickets`, `next_ticket`, `list_filters`, `run_filter`, `save_filter` |
| Tickets | `get_ticket`, `create_ticket`, `update_ticket`, `get_transitions`, `transition_ticket`, `change_ticket_type`, `set_checklist_item`, `clone_ticket`, `move_ticket`, `bulk_update`, `rank_ticket`, `get_history` |
| Collaboration | `add_comment`, `list_comments`, `link_tickets`, `unlink_tickets`, `add_collaborator`, `remove_collaborator` |
| Files and time | `upload_attachment`, `list_attachments`, `read_attachment`, `log_work`, `list_worklogs` |
| Planning | `create_area`, `update_area`, `create_milestone`, `update_milestone`, `list_boards`, `get_board`, `list_sprints`, `get_sprint`, `add_to_sprint`, `remove_from_sprint`, `start_sprint`, `complete_sprint`, `get_milestone_progress`, `get_report` |
| Inbox | `list_inbox`, `score_inbox_item`, `approve_inbox_item`, `discard_inbox_item`, `mark_inbox_duplicate` |

Resources: `radicle://guide/rql` and `radicle://projects/{key}/schema`. Agents follow the same permission matrix and security levels as people, and can be limited to some of these tools. `GET /api/v1/mcp/tools` lists them with their group and whether they only read.

</details>

**Folio** has its own MCP server at `/mcp/folio`, with the same tokens. For now it has `whoami`, which tells the agent its global Folio role; tools to read, search and propose docs come with Folio's phase 1.

### 14. Keyboard, command palette and themes

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Hands on the keyboard? Press <kbd>?</kbd> to see every shortcut.

Press <kbd>?</kbd> to see every shortcut. The main ones:

| Keys | Action |
| --- | --- |
| <kbd>⌘</kbd> <kbd>K</kbd> | Command palette: tickets, projects, filters and actions |
| <kbd>c</kbd> | Create ticket |
| <kbd>/</kbd> | Search |
| <kbd>g</kbd> <kbd>p</kbd> · <kbd>g</kbd> <kbd>m</kbd> | Go to projects · my tickets |
| <kbd>j</kbd> / <kbd>k</kbd> | Move through lists and boards |
| <kbd>e</kbd> <kbd>a</kbd> <kbd>m</kbd> <kbd>l</kbd> <kbd>p</kbd> | On a ticket: edit title, assign to me, move, tags, priority |

<p align="center"><img src="docs/images/command-palette.png" alt="Command palette" width="820"></p>

Switch between light and dark with the moon button, and between English and Spanish in your profile or from the palette. You can turn shortcuts off in your profile.

**Use it as a desktop app.** Radicle can be installed as its own app, with Radi in the Dock and its own window: in Chrome click **Install** in the address bar, or in Safari choose **File → Add to Dock**.

### 15. Folio and the AI provider

Radicle is growing a second app, **Radicle Folio**, for documentation (specs in `docs/folio/`). Docket, the ticket tracker, and Folio share users, groups, agents and the sign-in: open the menu on the logo (or press `g f` / `g d`) to switch, and each app opens where you left it.

- **Admin → Settings → AI provider** sets one provider for chat and embeddings (OpenAI, an OpenAI-compatible server such as Voyage, Ollama, or Anthropic for chat). The key is stored encrypted; **Test connection** embeds a short text and shows the dimensions and latency. Without a provider, everything else works.
- **Folio → Admin → Global roles** decides who reads, creates or administers Folio: a person, a group or everyone (everyone reads by default). People without any role don't see Folio.

## ⚙️ Configuration

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** The knobs for whoever runs Radicle.

Everything is set with environment variables (see [`.env.example`](.env.example)).

| Variable | Default | What it does |
| --- | --- | --- |
| `RADICLE_SECRET_KEY` | **required** | Encrypts stored secrets (SSO, captcha) and signs links and the SSO cookie. Generate it with `openssl rand -hex 32` and never change it afterwards. |
| `RADICLE_BASE_URL` | `http://localhost:8000` | Public URL, used for cookies, MCP snippets and public form links. |
| `RADICLE_PORT` | `8000` | Host port of the app container. |
| `RADICLE_TIMEZONE` | `UTC` | Time zone for relative dates in RQL and reports. |
| `RADICLE_WORKDAYS` | `mon,tue,wed,thu,fri` | Working days for burndowns. |
| `RADICLE_STORAGE` | `local` | `local` keeps attachments in a Docker volume; `s3` uses any S3-compatible store (AWS, MinIO, R2) with `RADICLE_S3_*`. |
| `RADICLE_MAX_UPLOAD_MB` | `25` | Maximum size per file. |
| `RADICLE_IMAGE_DEFAULT_RESIZE` | `large` | Default image size: `original`, `large` (2048 px), `medium` or `small`. |
| `RADICLE_AUDIT_RETENTION_DAYS` | `730` | Days the audit log is kept. |
| `RADICLE_SESSION_DAYS` | `14` | Session length (sliding). |
| `RADICLE_ASSISTANT_*` | unset | Radi's LLM; see [Meet Radi](#-meet-radi). Without it, Radi answers from the guide. |
| `POSTGRES_*` | `radicle` | Database credentials. Change the password in production. |

The `worker` container runs background jobs: template propagation, image variants, large bulk edits, ranking, daily snapshots and audit retention. If it is down, those jobs wait in the queue.

## 🏗️ Architecture

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** How the pieces fit: one app, one worker, one database.

<p align="center"><img src="docs/images/architecture.svg" alt="Radicle architecture" width="900"></p>

| Layer | Stack |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic 2, Procrastinate (jobs on Postgres), Authlib (OIDC) |
| Database | PostgreSQL 16, with full-text search in English and Spanish |
| Frontend | React 18, TypeScript, TanStack Router and Query, styled-components, dnd-kit, Recharts, i18next |
| MCP | Official Python MCP SDK, Streamable HTTP at `/mcp` (Docket) and `/mcp/folio` (Folio) |
| Quality | pytest with testcontainers (real Postgres and Keycloak), mypy strict, ruff, Vitest, Playwright E2E |

Business logic lives only in the services: `backend/radicle/platform/services/` for what the apps share and `backend/radicle/docket/services/` for tickets. The REST routers and the MCP tools validate input and call those services, so the UI, the API and agents always follow the same rules.

## 🧑‍💻 Development

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Want to hack on Radicle (or on me)? Start here.

| Part | Needs | Commands |
| --- | --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (for tests) | `cd backend && uv sync`, `uv run uvicorn radicle.main:app --reload`, `uv run pytest` |
| Frontend | Node 22, pnpm 9 | `cd frontend && pnpm install`, `pnpm dev` (proxies to `:8000`), `pnpm check` |
| Local database | Docker | `docker compose up -d db`, then `cd backend && uv run alembic upgrade head` |

```bash
# Run these before every push (GitHub Actions CI is paused for now)
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy radicle && uv run pytest --cov
cd frontend && pnpm check && pnpm build
scripts/smoke.sh   # builds the image and runs it from scratch on port 8001
```

- Backend tests start PostgreSQL 16 with testcontainers (no SQLite). Tests marked `slow` also start Keycloak.
- If you change the API: `cd backend && uv run python ../scripts/export_openapi.py`, then `cd frontend && pnpm api:types`.
- Demo data: `cd backend && uv run python ../scripts/seed.py --tickets 400 --project PA`, then sign in as `fernando@example.com` / `radicle-demo`.
- Design documents, decisions (ADRs) and progress notes live in [`docs/`](docs/). They are written in Spanish.

## 🗺️ Roadmap and known issues

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** What's next. Ideas welcome!

Stages 1 to 4 are complete: core and MCP, configuration and daily work, planning and visibility, and the Inbox with access control. This is what comes next. Ideas and help are very welcome.

**Radicle Folio (docs)**

- [x] Phase 0: shared platform (one backend split into `platform`, `docket` and `folio`, generic authorization, AI provider, suite switch, Folio's skeleton).
- [ ] Phase 1: spaces and pages, the editor, publishing with versions, permissions, agent submissions with approval, RAG search and Folio's MCP.
- [ ] Phase 2: real-time collaboration, comments, mentions, live docs.
- [ ] Phase 3: templates, the home editor, visual blocks, whiteboards and databases.
- [ ] Phase 4: tickets inside docs and chat with citations.
- [ ] Phase 5: public pages, import and export, Slack and Teams, webhooks.

**Stage 5: integrations**

- [ ] Notifications (in-app and email), watchers and subscriptions to filters, including an email to public-form senders when their item changes.
- [ ] Automation rules ("when X, do Y") and outgoing webhooks.
- [ ] Git integration: a merged PR moves its ticket to Done.
- [ ] Chat integrations (Slack, Microsoft Teams) and links to docs.
- [ ] Import and export (Jira, CSV, JSON).
- [ ] A plugin system.
- [ ] A native mobile app with push notifications.
- [ ] More AI helpers: summaries, duplicate detection, triage suggestions. (Radi, the in-app guide, already ships.)

**Later, maybe**

- [ ] SAML single sign-on (only OpenID Connect today).
- [ ] Roles beyond admin, member and viewer.
- [ ] More languages for the UI and the public form (English and Spanish today).

**Known issues and small fixes** (good first contributions)

- [ ] The main frontend bundle is over 500 kB; split it by route.
- [ ] The burndown draws zero for the days before a sprint was started when its start date is set in the past.
- [ ] The audit log shows internal IDs for some targets (security levels, SSO providers) instead of their names.
- [ ] `test_periods.py` can fail now and then when two status changes share the same timestamp.

## 🤝 Contributing

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Every contribution counts, from a typo to a feature. Come say hi!

Radicle is a community project, and contributions of every size are welcome: bug reports, docs, translations, design and code.

<p align="center"><img src="docs/images/contributing-flow.svg" alt="How a change gets in" width="900"></p>

The short version:

- **One thing per PR**, with its tests.
- **Small PRs**: under **500 changed lines** and under **100 files**. Split bigger work into steps.
- **Branches** are named `type/short-description`:

| Type | Use it for | Example |
| --- | --- | --- |
| `feat/` | Something new | `feat/csv-import` |
| `minor/` | Small changes and tweaks | `minor/board-card-spacing` |
| `fix/` | Bug fixes | `fix/burndown-backdated-sprint` |
| `refactor/` | Reordering code without changing behavior | `refactor/split-ticket-service` |
| `docs/` | Documentation only | `docs/sso-okta-guide` |

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide: setup, code rules, commit messages and how reviews work. New here? Pick something from the [known issues](#%EF%B8%8F-roadmap-and-known-issues) or open an issue to say hi.

## 📜 License

> <img src="docs/images/radi.svg" alt="Radi" width="22" align="top"> **Radi:** Free software, and it stays free.

Radicle is free software under the **[GNU Affero General Public License v3.0](LICENSE)** (AGPL-3.0-only).

In short: you can use, study, modify and share Radicle, including at your company and for commercial work. If you change it and let other people use your version, **including over a network** (for example, hosting it for your team or your customers), you must offer them the source code of your changes under the same license. That way, improvements come back to the community instead of staying in private forks.

By contributing, you agree that your contributions are licensed under the same terms.
