"""The catalog of transition rules and the validation of their config. No database access.

Conditions decide whether a transition is offered at all, validators check the ticket
before it moves, and post-functions change it right after, in the same transaction.
"""

import re
from dataclasses import dataclass
from typing import Any

from radicle.db.models import ProjectRole, RuleKind, UserKind
from radicle.platform.errors import ValidationFailed

# Fixed fields that rules can require, set or clear. Custom fields go as cf.<key>.
RULE_FIELDS = (
    "priority",
    "area",
    "milestone",
    "assignee",
    "due_date",
    "estimate_hours",
    "description_md",
    "parent",
)
CUSTOM_FIELD_RE = re.compile(r"^cf\.[a-z][a-z0-9_]{1,39}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
TEMPLATE_MAX = 2000


@dataclass(frozen=True)
class RuleSpec:
    kind: RuleKind
    params: tuple[str, ...] = ()
    description: str = ""


CATALOG: dict[str, RuleSpec] = {
    "only_assignee": RuleSpec(RuleKind.condition, (), "Only the assignee can run it"),
    "only_reporter": RuleSpec(RuleKind.condition, (), "Only the reporter can run it"),
    "only_roles": RuleSpec(RuleKind.condition, ("roles",), "Only these project roles"),
    "only_user_kind": RuleSpec(RuleKind.condition, ("kind",), "Only humans or only agents"),
    "not_blocked": RuleSpec(RuleKind.condition, (), "Follows the project's blocked policy"),
    "checklist_complete": RuleSpec(RuleKind.validator, (), "Every checklist item is checked"),
    "field_required": RuleSpec(RuleKind.validator, ("field",), "The field has a value"),
    "has_estimate": RuleSpec(RuleKind.validator, (), "The ticket has an estimate"),
    "children_done": RuleSpec(RuleKind.validator, (), "Every subticket is done"),
    "has_worklog": RuleSpec(RuleKind.validator, (), "At least one worklog"),
    "comment_required": RuleSpec(RuleKind.validator, (), "A comment comes with the move"),
    "assign_to_actor": RuleSpec(RuleKind.post_function, (), "Assign to whoever moves it"),
    "unassign": RuleSpec(RuleKind.post_function, (), "Remove the assignee"),
    "set_field": RuleSpec(RuleKind.post_function, ("field", "value"), "Set a field"),
    "clear_field": RuleSpec(RuleKind.post_function, ("field",), "Clear a field"),
    "add_tag": RuleSpec(RuleKind.post_function, ("tag",), "Add a tag"),
    "remove_tag": RuleSpec(RuleKind.post_function, ("tag",), "Remove a tag"),
    "add_comment": RuleSpec(
        RuleKind.post_function, ("template",), "Comment with {actor}, {from}, {to}"
    ),
}


def _fail(path: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": path, "message": "invalid rule"}])


def check_rule(
    kind: str, rule_type: str, config: dict[str, Any], path: str = "rules"
) -> dict[str, Any]:
    """Normalize a rule's config or explain what is wrong with it."""
    spec = CATALOG.get(rule_type)
    if spec is None:
        raise _fail(path, f"Unknown rule '{rule_type}'. Rules: {', '.join(sorted(CATALOG))}.")
    if kind != spec.kind.value:
        raise _fail(path, f"'{rule_type}' is a {spec.kind.value}, not a {kind}.")
    extra = set(config) - set(spec.params)
    if extra:
        raise _fail(path, f"'{rule_type}' does not take: {', '.join(sorted(extra))}.")
    missing = [p for p in spec.params if p not in config and p != "value"]
    if missing:
        raise _fail(path, f"'{rule_type}' needs: {', '.join(missing)}.")
    out: dict[str, Any] = {}
    if rule_type == "only_roles":
        roles = config["roles"]
        valid = {r.value for r in ProjectRole}
        if not isinstance(roles, list) or not roles or not set(roles) <= valid:
            raise _fail(path, f"only_roles needs a list of roles: {', '.join(sorted(valid))}.")
        out["roles"] = [r.value for r in ProjectRole if r.value in roles]
    if rule_type == "only_user_kind":
        if config["kind"] not in (UserKind.human.value, UserKind.agent.value):
            raise _fail(path, "only_user_kind takes kind: human or agent.")
        out["kind"] = config["kind"]
    if "field" in spec.params:
        field = str(config["field"]).strip()
        if field not in RULE_FIELDS and not CUSTOM_FIELD_RE.fullmatch(field):
            raise _fail(
                path,
                f"'{field}' cannot be used in rules. Use {', '.join(RULE_FIELDS)} or cf.<key>.",
            )
        out["field"] = field
    if rule_type == "set_field":
        out["value"] = config.get("value")
    if "tag" in spec.params:
        tag = str(config["tag"]).strip().lstrip("#").lower()
        if not TAG_RE.fullmatch(tag):
            raise _fail(path, f"Invalid tag '{config['tag']}'.")
        out["tag"] = tag
    if rule_type == "add_comment":
        template = str(config["template"]).strip()
        if not template or len(template) > TEMPLATE_MAX:
            raise _fail(path, f"add_comment needs a template of 1 to {TEMPLATE_MAX} characters.")
        out["template"] = template
    return out


def describe(rule_type: str, config: dict[str, Any]) -> str:
    """Short human summary, e.g. for the MCP project schema."""
    spec = CATALOG[rule_type]
    if not config:
        return rule_type
    args = ", ".join(f"{k}={v}" for k, v in config.items())
    return f"{rule_type}({args})" if spec.params else rule_type
