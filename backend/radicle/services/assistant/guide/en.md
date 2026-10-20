## Getting started
Radicle is a ticket tracker for people and AI agents. The left menu has Projects, My tickets, Dashboards and, for admins, Admin. Press `?` to see every keyboard shortcut and `⌘K` (or Ctrl+K) to open the command palette.

## Create a project {#create-project}
Go to **Projects** and click **Create project**. Give it a name and a short key of 2 to 10 uppercase letters or digits, like PAY: every ticket gets it as a prefix (PAY-12) and it cannot change later. Pick a template: **Linked** keeps receiving the template's changes, **Independent** copies it once. Then add **Areas** and **Milestones** in the project's **Settings**. Only instance admins create projects.

## Edit a project
On **Projects**, hover a card and click the pencil to change its name or description. The key never changes. Project admins and instance admins can edit.

## Add people to a project {#add-people}
Open the project's **Settings → Members**. Use the search box to find people, agents or groups, pick a role and click **Add**. Roles: **Viewer** reads and votes, **Member** works tickets, **Admin** also manages members, settings and permissions. Change someone's role with the dropdown on their row, or remove them with the ×. New people are created by an instance admin in **Admin → Users**.

## Groups
In **Admin → Groups** create a group (for example legal-team) and add people. Then add the group to a project in **Settings → Members** with a role: everyone in it gets access, also people who join later. When someone has several roles, the highest one wins.

## Create a ticket {#create-ticket}
Press `c` or click **Create ticket**. Types: **Task** (work to do), **Bug** (something broken) and **Draft** (an idea not decided yet, it goes to the Inbox). Tasks and bugs need an area. The description is markdown; lines like `- [ ] step` become a checklist.

## Work on a ticket
Open a ticket to change its status with the status button, assign it, set priority, area, milestone, dates and estimate, add tags, collaborators and a parent ticket. Below you find attachments, subtickets, links (blocks, relates to, duplicates), comments with @mentions and the history. **Log time** records hours worked. The ⋯ menu clones, moves to another project or deletes the ticket.

## Statuses and workflows
Each ticket type has its own workflow. Tasks go To Do → In Progress → In Review → Done; bugs go Reported → In Progress → QA Verified → Done. From In Review (or QA Verified) you can go back to the start. Some moves ask for a resolution, a comment or a finished checklist. Admins edit workflows in **Settings → Workflows**.

## Board
**Board** shows tickets as cards in columns: To Do, In Progress, In Review and Done. Drag a card to another column to change its status, or up and down to reorder; it lands where you drop it. If a move needs more information, a dialog asks for it. Quick filters (My tickets, Only bugs, #backlog, Blocked) and the filter bar narrow the board.

## Swimlanes {#swimlanes}
Split the board in rows with the swimlanes selector: by area, assignee, priority, milestone, parent or type. Click a row header to hide or show it, or use **Collapse all**. Radicle remembers which rows you hid.

## Configure a board
Admins click **Configure** on the board. The source is an RQL query, so a board can cover one area or several projects. Columns hold statuses by category or by name; a status named in a column goes there even if another column covers its category. Set WIP limits (soft turns the column red, hard blocks), card fields and quick filters. **New board** creates another one; a board of kind Scrum adds sprints.

## List and filters {#list-filters}
**List** shows tickets in a table. Click **Filter** above the table to filter by type, status, priority, assignee, area or milestone; each filter shows as a chip you can remove. **Group by** splits the rows in groups you can fold. Tickets with subtickets have an arrow to open their tasks and bugs. **Saved filters** keeps queries you reuse.

## Search with RQL
RQL is the query language of the search bar, List, boards and filters. Examples: `type = bug AND priority >= high`, `assignee = currentUser() AND category != done`, `text ~ "checkout" AND updated >= -7d`, `sprint = active`. Combine with AND, OR, NOT and parentheses, sort with ORDER BY. Mistakes are underlined with what was expected.

## Sprints and backlog
Create a Scrum board, then open **Backlog**. Click **New sprint**, set a goal, dates and capacity, and drag tickets in. **Start sprint** fixes the commitment; **Complete sprint** sends unfinished tickets back to the backlog or the next sprint and saves the sprint report.

## Timeline
**Timeline** draws tickets over time by milestone or area. Drag a bar to move its dates or an edge to change one. A ticket with only a due date shows a faded bar from its creation day. Drag tickets from **Without dates** onto the chart to give them dates. Impossible dependencies turn red.

## Reports
**Reports** has burndown, burnup, velocity, cumulative flow, control chart, sprint report, created vs resolved, distribution, milestone progress and time. Each one has a data table and **Export CSV**.

## Dashboards
**Dashboards** group widgets you arrange by dragging: counts, distributions, milestone progress, burndown, blocked tickets, filter results and notes. Share a dashboard with yourself, a project or everyone; each person sees only the tickets they may see. Every project has a **Summary** dashboard.

## Inbox and public form
The **Inbox** collects Drafts: ideas from the team, agents and people without an account. Turn on the public form in **Settings → Inbox** and share `/b/<slug>`. Score each item with Impact and Effort, look at the **Matrix**, then **Approve and convert** it into a task or bug, **Mark duplicate** or **Discard** with a note. The sender follows it with a tracking code.

## Permissions
In **Settings → Permissions** admins switch each permission on or off for members and viewers: creating, editing, moving and deleting tickets, comments, attachments, time, votes, links and more. Buttons disappear for people without the permission, and the API and agents follow the same rule.

## Restricted tickets
In **Settings → Levels** create a security level (like Legal confidential) and choose the groups or people who may see it. Put a ticket in that level from the lock button on the ticket; nobody else will find it anywhere.

## Single sign-on
In **Admin → SSO** add an OpenID Connect provider (Google, Microsoft, Okta, Keycloak...) with its issuer, client ID and secret. Allowed domains create accounts automatically and group mapping keeps groups in sync. **Admin → Settings** can turn password sign-in off; the first admin can always still sign in with a password.

## Audit log
**Admin → Audit log** lists administrative changes: who, when, from which IP and what changed. Filter by person, action, project and dates, and export to CSV. Project admins see their projects' entries in **Settings → Audit log**. Nobody can edit or delete it.

## AI agents and MCP {#agents}
Agents are users for AI tools. In **Admin → Users** click **New user** and choose **Agent (LLM or worker)**, or use **Admin → Agents**. Copy the token: it is shown only once. Add the agent to a project in **Settings → Members**, then connect your MCP client to `/mcp` with the header `Authorization: Bearer <token>`. With Claude Code: `claude mcp add --transport http radicle <url>/mcp --header "Authorization: Bearer <token>"`.

## Agent MCP permissions
Each agent can be limited to some MCP tools. Use **MCP permissions** on the agent in Admin → Users or Agents: keep **All tools**, choose **Read only**, or tick tools one by one. Tools that are off disappear for that agent. Project permissions still apply.

## Keyboard shortcuts
`?` shows all shortcuts. `c` creates a ticket, `/` searches, `⌘K` opens the palette, `g p` goes to projects, `g m` to my tickets, `j` and `k` move through lists and boards. On a ticket: `e` edit title, `a` assign to me, `m` move, `l` tags, `p` priority. You can turn shortcuts off in your profile.

## Profile, language and theme
Click your name at the bottom left to open your profile: change your name, password, language (English or Spanish) and personal API tokens. The moon button at the top switches light and dark mode.

## Radi, the assistant {#radi}
Radi is the green ball at the bottom right. Click it to ask how to use Radicle. An instance admin can connect an LLM in **Admin → Settings → Assistant** (Anthropic or any OpenAI-compatible server, like Ollama); without one, Radi answers from this guide.
