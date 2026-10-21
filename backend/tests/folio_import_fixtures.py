"""Small real-shaped exports for Folio's importers (Folio 5.3), in tests/fixtures/folio_import."""

import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent / "fixtures" / "folio_import"


def load(name: str) -> dict[str, bytes]:
    base = ROOT / name
    return {
        str(p.relative_to(base)).replace("\\", "/"): p.read_bytes()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def zipped(name: str) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in load(name).items():
            z.writestr(path, data)
    return out.getvalue()
