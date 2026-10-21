"""The dependency rule (ADR 0034): docket and folio depend on platform, platform on
neither, and folio talks to docket only through `radicle.docket.public`, never its tables or
services."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

RADICLE = Path(__file__).resolve().parents[2] / "radicle"


def _imports(package: str) -> list[tuple[str, str]]:
    """(file, imported module) for every absolute radicle import under a package."""
    found = []
    for path in sorted((RADICLE / package).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            rel = str(path.relative_to(RADICLE.parent))
            found += [(rel, n) for n in names if n.startswith("radicle")]
    return found


def test_platform_imports_only_platform() -> None:
    bad = {(f, m) for f, m in _imports("platform") if not m.startswith("radicle.platform")}
    assert not bad, f"platform must not import from an app: {sorted(bad)}"


def test_folio_talks_to_docket_only_through_its_public_interface() -> None:
    if not (RADICLE / "folio").exists():
        pytest.skip("no folio package yet")
    from radicle.docket import public

    allowed = {"radicle.docket.public"} | {f"radicle.docket.public.{n}" for n in public.__all__}
    bad = {
        (f, m) for f, m in _imports("folio") if m.startswith("radicle.docket") and m not in allowed
    }
    assert not bad, f"folio may import only radicle.docket.public: {sorted(bad)}"


def test_importing_platform_loads_no_app() -> None:
    """At run time too: importing every platform module pulls in nothing else."""
    code = (
        "import importlib, pkgutil, sys, radicle.platform as p\n"
        "for m in pkgutil.walk_packages(p.__path__, 'radicle.platform.'):\n"
        "    importlib.import_module(m.name)\n"
        "print('\\n'.join(sorted(m for m in sys.modules if m.startswith('radicle.')\n"
        "    and not m.startswith('radicle.platform'))))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout
    assert out.strip() == "", f"platform loaded app modules:\n{out}"
