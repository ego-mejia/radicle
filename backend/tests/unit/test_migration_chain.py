"""Migrations form one chain: unique revision ids and a single head. Two branches merged
in parallel can both take the next number, and then `alembic upgrade head` refuses to
start the app."""

import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
FIELD = re.compile(r'^(revision|down_revision): str(?: \| None)? = "([^"]+)"', re.M)


def test_one_chain_with_a_single_head() -> None:
    revisions: dict[str, str | None] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        fields = dict(FIELD.findall(path.read_text()))
        rev = fields["revision"]
        assert rev not in revisions, f"Revision {rev} is used twice (again in {path.name})"
        revisions[rev] = fields.get("down_revision")
    parents = {down for down in revisions.values() if down}
    heads = sorted(set(revisions) - parents)
    assert len(heads) == 1, f"Several heads: {heads}. Renumber the newest and chain it."
