"""On-screen tutorials: steps that point at (or click) known parts of the UI.

The LLM may only use targets from this catalog. Each target is a `data-tour` value in the
web app and the page it lives on ({project} is filled in by the app). Tours never submit:
clicking a target marked `submit` is turned into pointing at it.
"""

from dataclasses import dataclass
from typing import Any, Literal

Action = Literal["point", "click"]


@dataclass(frozen=True)
class Target:
    page: str | None  # route, or None when it shows on every page or inside a dialog
    about: str  # for the model: what it is
    submit: bool = False


def _t(page: str | None, about: str, submit: bool = False) -> Target:
    return Target(page, about, submit)


P = "/p/{project}"
TARGETS: dict[str, Target] = {
    "nav.projects": _t("/", "Projects, in the left menu"),
    "nav.my-tickets": _t(None, "My tickets, in the left menu"),
    "nav.dashboards": _t(None, "Dashboards, in the left menu"),
    "nav.admin": _t(None, "Admin, in the left menu (instance admins)"),
    "topbar.search": _t(None, "Search bar at the top: ticket keys or RQL"),
    "topbar.create-ticket": _t(None, "Create ticket button, top right; opens the ticket dialog"),
    "radi": _t(None, "Radi, the green ball at the bottom right"),
    "projects.create": _t("/", "Create project button; opens the project dialog"),
    "project-form.name": _t(None, "Project dialog: name"),
    "project-form.key": _t(None, "Project dialog: key, the ticket prefix like PAY"),
    "project-form.template": _t(None, "Project dialog: template with workflows and fields"),
    "project-form.mode": _t(None, "Project dialog: Linked or Independent template"),
    "project-form.description": _t(None, "Project dialog: description"),
    "project-form.submit": _t(None, "Project dialog: Create button", submit=True),
    "ticket-form.type": _t(None, "Ticket dialog: Task, Bug or Draft"),
    "ticket-form.title": _t(None, "Ticket dialog: title"),
    "ticket-form.area": _t(None, "Ticket dialog: area"),
    "ticket-form.submit": _t(None, "Ticket dialog: Create button", submit=True),
    "project.tab.summary": _t(f"{P}/summary", "Project tab: Summary dashboard"),
    "project.tab.board": _t(f"{P}/board", "Project tab: Board"),
    "project.tab.backlog": _t(f"{P}/backlog", "Project tab: Backlog and sprints"),
    "project.tab.inbox": _t(f"{P}/inbox", "Project tab: Inbox of drafts"),
    "project.tab.list": _t(f"{P}/list", "Project tab: List of tickets"),
    "project.tab.timeline": _t(f"{P}/timeline", "Project tab: Timeline"),
    "project.tab.reports": _t(f"{P}/reports", "Project tab: Reports"),
    "project.tab.settings": _t(f"{P}/settings", "Project tab: Settings"),
    "board.swimlanes": _t(f"{P}/board", "Board: swimlanes selector (rows by area...)"),
    "board.quick-filters": _t(f"{P}/board", "Board: quick filters"),
    "board.configure": _t(f"{P}/board", "Board: Configure button (admins)"),
    "board.new": _t(f"{P}/board", "Board: New board button (admins)"),
    "list.rql": _t(f"{P}/list", "List: RQL query box"),
    "list.filter": _t(f"{P}/list", "List: Filter button; opens the filter panel"),
    "list.group-by": _t(f"{P}/list", "List: Group by selector"),
    "list.saved-filters": _t(f"{P}/list", "List: Saved filters dropdown"),
    "settings.tab.members": _t(f"{P}/settings?tab=members", "Settings: Members tab"),
    "settings.tab.permissions": _t(f"{P}/settings?tab=permissions", "Settings: Permissions"),
    "settings.tab.levels": _t(f"{P}/settings?tab=levels", "Settings: security Levels"),
    "settings.tab.inbox": _t(f"{P}/settings?tab=inbox", "Settings: Inbox and public form"),
    "settings.tab.workflows": _t(f"{P}/settings?tab=workflows", "Settings: Workflows"),
    "members.picker": _t(f"{P}/settings?tab=members", "Members: search people or groups"),
    "members.role": _t(f"{P}/settings?tab=members", "Members: role for the person to add"),
    "members.add": _t(f"{P}/settings?tab=members", "Members: Add button", submit=True),
    "admin.tab.users": _t("/admin?tab=users", "Admin: Users tab"),
    "admin.tab.agents": _t("/admin?tab=agents", "Admin: Agents tab"),
    "admin.tab.groups": _t("/admin?tab=groups", "Admin: Groups tab"),
    "admin.tab.sso": _t("/admin?tab=sso", "Admin: SSO tab"),
    "admin.tab.audit": _t("/admin?tab=audit", "Admin: Audit log tab"),
    "admin.tab.settings": _t("/admin?tab=settings", "Admin: Settings tab"),
    "users.new": _t("/admin?tab=users", "Users: New user button; opens the user dialog"),
    "user-form.kind": _t(None, "User dialog: Person or Agent (LLM or worker)"),
    "user-form.name": _t(None, "User dialog: name"),
    "user-form.handle": _t(None, "User dialog: handle"),
    "user-form.mcp": _t(None, "User dialog: MCP tools an agent may use"),
    "user-form.submit": _t(None, "User dialog: Create button", submit=True),
    "assistant.settings": _t("/admin?tab=settings", "Admin settings: Assistant (Radi's LLM)"),
}


@dataclass(frozen=True)
class Step:
    target: str
    action: Action
    text: str

    def view(self) -> dict[str, Any]:
        target = TARGETS[self.target]
        return {
            "target": self.target,
            "action": self.action,
            "page": target.page,
            "text": self.text,
        }


def clean(raw: Any) -> list[Step]:
    """Steps from the model, keeping only known targets; submits become pointing."""
    steps: list[Step] = []
    if not isinstance(raw, list):
        return steps
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target", ""))
        text = str(item.get("text", "")).strip()[:400]
        if target not in TARGETS or not text:
            continue
        action: Action = "click" if item.get("action") == "click" else "point"
        if TARGETS[target].submit:
            action = "point"
        steps.append(Step(target, action, text))
    return steps


SHOW_ME = {
    "name": "show_me",
    "description": (
        "Walk the user through the screen step by step: the app moves a cursor to each "
        "target, highlights it and shows your text. Use it whenever the user asks how to "
        "do something in the app. 'click' opens tabs, menus and dialogs; 'point' explains "
        "a part, such as each field of a dialog. Never rely on saving: Create, Add and Save "
        "buttons are only pointed at. Use 2 to 8 steps, each text one or two short "
        "sentences in the user's language."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "enum": list(TARGETS)},
                        "action": {"type": "string", "enum": ["point", "click"]},
                        "text": {"type": "string"},
                    },
                    "required": ["target", "action", "text"],
                },
            }
        },
        "required": ["steps"],
    },
}


def catalog() -> str:
    """The targets as a compact list for the system prompt."""
    return "\n".join(f"- {key}: {t.about}" for key, t in TARGETS.items())
