"""The Markdown export's links to files and its file names."""

import uuid
from types import SimpleNamespace

from radicle.folio.services.exporting import markdown
from radicle.folio.services.exporting.pages import ExportAsset

ID = "0b5c2a4e-1111-4111-8111-111111111111"


def _asset(filename: str) -> ExportAsset:
    return ExportAsset(SimpleNamespace(id=uuid.UUID(ID), filename=filename), b"x")  # type: ignore[arg-type]


def test_files_and_images_point_into_assets() -> None:
    assets = {ID: _asset("Plan Q4 (final).pdf")}
    md = f'![Plan](asset:{ID})\n\n::file{{asset={ID} name="Plan Q4.pdf" size=12}}\n'
    out = markdown._relink(md, "../", assets)
    assert "![Plan](../assets/0b5c2a4e-Plan-Q4-final-.pdf)" in out
    assert "[Plan Q4.pdf](../assets/0b5c2a4e-Plan-Q4-final-.pdf)" in out
    unknown = "::file{asset=00000000-0000-0000-0000-000000000000 name=x}"
    assert markdown._relink(unknown, "", assets) == unknown


def test_two_pages_with_one_slug_get_two_files() -> None:
    used: set[str] = set()
    names = [markdown.unique("guias/inicio", ".md", used) for _ in range(3)]
    assert names == ["guias/inicio.md", "guias/inicio-2.md", "guias/inicio-3.md"]
