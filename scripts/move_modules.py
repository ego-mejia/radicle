"""Move backend modules and rewrite every import that points at them (ADR 0034).

    uv run python ../scripts/move_modules.py platform   # from backend/

Each step lists (old module, new module) pairs; a package moves with everything in it.
The script only renames: it runs `git mv`, rewrites `from x import y` and `import x`
statements, and replaces dotted paths left in strings (job module lists, patches).
Run `ruff check --fix` and `ruff format` afterwards to sort the imports again.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"

STEPS: dict[str, list[tuple[str, str]]] = {
    "platform": [
        ("radicle.core.config", "radicle.platform.config"),
        ("radicle.core.crypto", "radicle.platform.crypto"),
        ("radicle.core.errors", "radicle.platform.errors"),
        ("radicle.core.security", "radicle.platform.security"),
        ("radicle.core.mcp_tools", "radicle.platform.mcp_tools"),
        ("radicle.storage", "radicle.platform.storage"),
        ("radicle.db.session", "radicle.platform.db.session"),
        ("radicle.db.models.base", "radicle.platform.db.models.base"),
        ("radicle.db.models.users", "radicle.platform.db.models.users"),
        ("radicle.db.models.audit", "radicle.platform.db.models.audit"),
        ("radicle.db.models.sso", "radicle.platform.db.models.sso"),
        ("radicle.db.models.jobs", "radicle.platform.db.models.jobs"),
        ("radicle.db.models.groups", "radicle.platform.db.models.groups"),
        ("radicle.services.auth", "radicle.platform.services.auth"),
        ("radicle.services.users", "radicle.platform.services.users"),
        ("radicle.services.audit", "radicle.platform.services.audit"),
        ("radicle.services.groups", "radicle.platform.services.groups"),
        ("radicle.services.sso", "radicle.platform.services.sso"),
        ("radicle.services.jobs", "radicle.platform.services.jobs"),
        ("radicle.services.queue", "radicle.platform.services.queue"),
        ("radicle.services.images", "radicle.platform.services.images"),
        ("radicle.services.markdown", "radicle.platform.services.markdown"),
        ("radicle.services.validation", "radicle.platform.services.validation"),
    ],
    # Everything left besides the composition (main, cli, seed, worker) is Docket.
    "docket": [
        (f"radicle.{package}", f"radicle.docket.{package}")
        for package in ("api", "core", "db", "mcp", "public", "query", "services")
    ],
    # What every app's routers need: the caller, pagination, rate limits, base schemas.
    "platform-api": [
        ("radicle.docket.api.deps", "radicle.platform.api.deps"),
        ("radicle.docket.api.pagination", "radicle.platform.api.pagination"),
        ("radicle.docket.api.ratelimit", "radicle.platform.api.ratelimit"),
        ("radicle.docket.api.schemas.common", "radicle.platform.api.schemas"),
    ],
}

# Inside a moved package, `from radicle.db.models import X` must use that package's own
# models: platform never imports the aggregate that also loads Docket's tables.
AGGREGATES: dict[str, tuple[str, str]] = {
    "platform": ("radicle.db.models", "radicle.platform.db.models"),
    "platform-api": ("radicle.docket.db.models", "radicle.platform.db.models"),
}

SOURCES = ("radicle", "tests", "migrations")


def module_of(path: Path) -> str:
    parts = path.relative_to(BACKEND).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def path_of(module: str, package: bool) -> Path:
    base = BACKEND.joinpath(*module.split("."))
    return base / "__init__.py" if package else base.with_suffix(".py")


def expand(moves: list[tuple[str, str]]) -> dict[str, str]:
    """Every module affected, old dotted name to new dotted name."""
    mapping: dict[str, str] = {}
    for old, new in moves:
        package = path_of(old, package=True)
        if package.exists():
            for f in sorted(package.parent.rglob("*.py")):
                mod = module_of(f)
                mapping[mod] = new + mod[len(old) :]
        else:
            mapping[old] = new
    return mapping


def git_mv(moves: list[tuple[str, str]]) -> None:
    """Packages move as whole folders, with their templates and data files."""
    for old, new in moves:
        package = path_of(old, package=True).exists()
        src, dst = path_of(old, package), path_of(new, package)
        if package:
            src, dst = src.parent, dst.parent
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", str(src), str(dst)], check=True, cwd=BACKEND)


def add_inits(mapping: dict[str, str]) -> None:
    # New packages need an __init__.py of their own.
    for new in mapping.values():
        parts = new.split(".")
        for i in range(2, len(parts)):
            init = path_of(".".join(parts[:i]), package=True)
            if not init.exists():
                init.write_text("")
                subprocess.run(["git", "add", str(init)], check=True, cwd=BACKEND)


def rewrite_imports(source: str, mapping: dict[str, str], aggregate: tuple[str, str] | None) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            groups: dict[str, list[str]] = {}
            for alias in node.names:
                full = f"{node.module}.{alias.name}"
                if full in mapping:  # a module imported from its package
                    target, _, name = mapping[full].rpartition(".")
                elif aggregate and node.module == aggregate[0]:
                    target, name = aggregate[1], alias.name
                else:
                    target, name = mapping.get(node.module, node.module), alias.name
                groups.setdefault(target, []).append(
                    f"{name} as {alias.asname}" if alias.asname else name
                )
            if list(groups) == [node.module]:
                continue
            indent = re.match(r"\s*", lines[node.lineno - 1]).group(0)  # type: ignore[union-attr]
            new = "".join(f"{indent}from {t} import {', '.join(n)}\n" for t, n in groups.items())
            edits.append((node.lineno, node.end_lineno or node.lineno, new))
        elif isinstance(node, ast.Import):
            if not any(a.name in mapping for a in node.names):
                continue
            indent = re.match(r"\s*", lines[node.lineno - 1]).group(0)  # type: ignore[union-attr]
            new = ""
            for a in node.names:
                name = mapping.get(a.name, a.name)
                new += f"{indent}import {name}{f' as {a.asname}' if a.asname else ''}\n"
            edits.append((node.lineno, node.end_lineno or node.lineno, new))
    for start, end, new in sorted(edits, reverse=True):
        lines[start - 1 : end] = [new]
    return "".join(lines)


def rewrite_paths(source: str, mapping: dict[str, str]) -> str:
    """Dotted paths outside import statements: strings, patches, `radicle.x.y` attributes."""
    for old in sorted(mapping, key=len, reverse=True):
        source = re.sub(rf"(?<![\w.]){re.escape(old)}(?!\w)", mapping[old], source)
    return source


def main(step: str) -> None:
    mapping = expand(STEPS[step])
    git_mv(STEPS[step])
    add_inits(mapping)
    aggregate_for = AGGREGATES.get(step)
    root = AGGREGATES[step][1].removesuffix(".db.models") if step in AGGREGATES else None
    files = [f for d in SOURCES for f in (BACKEND / d).rglob("*.py")]
    files += list((BACKEND.parent / "scripts").glob("*.py"))
    for f in files:
        if f.name == Path(__file__).name:
            continue
        source = f.read_text()
        inside = root is not None and f.is_relative_to(BACKEND) and module_of(f).startswith(root)
        new = rewrite_imports(source, mapping, aggregate_for if inside else None)
        new = rewrite_paths(new, mapping)
        if new != source:
            f.write_text(new)
    if step == "platform":
        write_platform_models()


def write_platform_models() -> None:
    """The platform aggregate re-exports platform models, as `radicle.db.models` did."""
    old = BACKEND / "radicle/db/models/__init__.py"
    tree = ast.parse(old.read_text())
    imports, names = [], []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "radicle.platform.db.models."
        ):
            imports.append(ast.unparse(node))
            names += [a.asname or a.name for a in node.names]
    body = "\n".join(imports) + "\n\n__all__ = [\n"
    body += "".join(f'    "{n}",\n' for n in sorted(names)) + "]\n"
    (BACKEND / "radicle/platform/db/models/__init__.py").write_text(body)


if __name__ == "__main__":
    main(sys.argv[1])
