"""Word documents (.docx), one page each; a zip of them keeps its folders as the tree.
Headings, lists, bold/italic, links, tables and pictures survive. The document title,
author and keywords become the page's title, author and labels. Office XML never
declares a DTD, so a part that does is refused before parsing."""

import io
import posixpath
import re
import zipfile
from xml.etree import ElementTree as ET

from radicle.folio.services.importing.bundle import Files
from radicle.folio.services.importing.files import IMAGE_EXTS, ordered, stem
from radicle.folio.services.importing.model import Bundle, Page, clean_label, clean_title

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
}
W = f"{{{NS['w']}}}"
R = f"{{{NS['r']}}}"
MAX_PART = 20 * 1024 * 1024


class _Doc:
    def __init__(self, path: str, archive: zipfile.ZipFile, bundle: Bundle, page: Page) -> None:
        self.path, self.archive, self.bundle, self.page = path, archive, bundle, page
        self.rels = self._rels()
        self.styles = self._styles()
        self.numbering = self._numbering()

    def xml(self, name: str) -> ET.Element | None:
        try:
            info = self.archive.getinfo(name)
        except KeyError:
            return None
        if info.file_size > MAX_PART:
            self.page.errors.append(f"{name} is too large to read.")
            return None
        data = self.archive.read(info)
        if b"<!DOCTYPE" in data or b"<!ENTITY" in data:  # never in Office XML
            self.page.errors.append(f"{name} declares entities; it was not read.")
            return None
        return ET.fromstring(data)  # noqa: S314 - no DTD, no entities (checked above)

    def _rels(self) -> dict[str, tuple[str, bool]]:
        root = self.xml("word/_rels/document.xml.rels")
        out: dict[str, tuple[str, bool]] = {}
        for rel in root if root is not None else []:
            external = rel.get("TargetMode") == "External"
            out[rel.get("Id", "")] = (rel.get("Target", ""), external)
        return out

    def _styles(self) -> dict[str, str]:
        root = self.xml("word/styles.xml")
        out = {}
        for style in root.iter(f"{W}style") if root is not None else []:
            name = style.find("w:name", NS)
            out[style.get(f"{W}styleId", "")] = name.get(f"{W}val", "") if name is not None else ""
        return out

    def _numbering(self) -> dict[tuple[str, str], str]:
        """(numId, level) -> numFmt, so numbered lists keep their numbers."""
        root = self.xml("word/numbering.xml")
        if root is None:
            return {}
        formats: dict[str, dict[str, str]] = {}
        for abstract in root.iter(f"{W}abstractNum"):
            levels: dict[str, str] = {}
            for lvl in abstract.iter(f"{W}lvl"):
                el = lvl.find("w:numFmt", NS)
                levels[lvl.get(f"{W}ilvl", "0")] = el.get(f"{W}val", "") if el is not None else ""
            formats[abstract.get(f"{W}abstractNumId", "")] = levels
        out: dict[tuple[str, str], str] = {}
        for num in root.iter(f"{W}num"):
            ref = num.find("w:abstractNumId", NS)
            used = formats.get(ref.get(f"{W}val", "") if ref is not None else "", {})
            for level, fmt in used.items():
                out[(num.get(f"{W}numId", ""), level)] = fmt
        return out

    def heading_level(self, p: ET.Element) -> int | None:
        style = p.find("w:pPr/w:pStyle", NS)
        if style is None:
            return None
        sid = style.get(f"{W}val", "")
        name = self.styles.get(sid, sid).lower().replace(" ", "")
        if name == "title":
            return 0
        match = re.fullmatch(r"(?:heading|titulo|título)(\d)", name)
        return min(int(match.group(1)), 6) if match else None

    def image(self, rid: str) -> str:
        target, external = self.rels.get(rid, ("", False))
        if external or not target:
            return ""
        inner = posixpath.normpath(posixpath.join("word", target))
        if not inner.lower().endswith(IMAGE_EXTS):
            return ""
        try:
            data = self.archive.read(inner)
        except KeyError:
            self.page.errors.append(f"Missing picture: {target}")
            return ""
        ref = self.bundle.attach(f"{self.path}#{inner}", data, posixpath.basename(inner))
        return f"\n\n![{posixpath.basename(inner)}](import:{ref})\n\n"

    def runs(self, parent: ET.Element) -> str:
        out = []
        for node in parent:
            if node.tag == f"{W}r":
                out.append(self.run(node))
            elif node.tag == f"{W}hyperlink":
                label = self.runs(node).strip()
                target, external = self.rels.get(node.get(f"{R}id", ""), ("", False))
                out.append(f"[{label}]({target})" if external and label and target else label)
            elif node.tag in (f"{W}ins", f"{W}smartTag", f"{W}sdt", f"{W}sdtContent"):
                out.append(self.runs(node))
        return "".join(out)

    def run(self, r: ET.Element) -> str:
        parts = []
        for node in r:
            if node.tag == f"{W}t":
                parts.append(re.sub(r"([\\`*_\[\]])", r"\\\1", node.text or ""))
            elif node.tag == f"{W}tab":
                parts.append(" ")
            elif node.tag == f"{W}br":
                parts.append("  \n")
            elif node.tag == f"{W}drawing":
                blip = node.find(".//a:blip", NS)
                if blip is not None:
                    parts.append(self.image(blip.get(f"{R}embed", "")))
        text = "".join(parts)
        props = r.find("w:rPr", NS)
        if props is None or not text.strip():
            return text

        def on(tag: str) -> bool:
            el = props.find(f"w:{tag}", NS)
            return el is not None and el.get(f"{W}val", "true") not in ("0", "false")

        core = text.strip()
        if on("b"):
            core = f"**{core}**"
        if on("i"):
            core = f"*{core}*"
        if on("strike"):
            core = f"~~{core}~~"
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        return lead + core + trail

    def paragraph(self, p: ET.Element) -> tuple[str, int | None]:
        text = self.runs(p).strip()
        level = self.heading_level(p)
        num = p.find("w:pPr/w:numPr", NS)
        if num is not None and text and level is None:
            ilvl_el, id_el = num.find("w:ilvl", NS), num.find("w:numId", NS)
            ilvl = ilvl_el.get(f"{W}val", "0") if ilvl_el is not None else "0"
            num_id = id_el.get(f"{W}val", "") if id_el is not None else ""
            fmt = self.numbering.get((num_id, ilvl), "bullet")
            marker = "-" if fmt in ("bullet", "none", "") else "1."
            return f"{'  ' * int(ilvl)}{marker} {text}", None
        if level and text:
            return f"{'#' * level} {text}", level
        return text, level

    def table(self, tbl: ET.Element) -> str:
        grid = []
        for tr in tbl.findall("w:tr", NS):
            cells = []
            for tc in tr.findall("w:tc", NS):
                texts = [self.runs(p).strip() for p in tc.findall("w:p", NS)]
                cells.append(" ".join(t for t in texts if t).replace("|", "\\|") or " ")
            if cells:
                grid.append(cells)
        if not grid:
            return ""
        width = max(len(r) for r in grid)
        grid = [r + [" "] * (width - len(r)) for r in grid]
        lines = ["| " + " | ".join(grid[0]) + " |", "|" + " --- |" * width]
        return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in grid[1:]])

    def body(self) -> tuple[str | None, str]:
        root = self.xml("word/document.xml")
        if root is None:
            self.page.errors.append("This .docx has no document body; is it a Word file?")
            return None, ""
        body = root.find("w:body", NS)
        blocks: list[str] = []
        title = None
        previous_list = False
        for node in body if body is not None else []:
            if node.tag == f"{W}tbl":
                blocks.append(self.table(node))
                previous_list = False
            elif node.tag == f"{W}p":
                text, level = self.paragraph(node)
                if level == 0 and title is None and not blocks:
                    title = re.sub(r"[*\\]", "", text)
                    continue
                if not text.strip():
                    previous_list = False
                    continue
                is_list = bool(re.match(r"^\s*(-|1\.) ", text))
                if is_list and previous_list:
                    blocks[-1] += "\n" + text
                else:
                    blocks.append(text)
                previous_list = is_list
        return title, "\n\n".join(b for b in blocks if b.strip()) + "\n"

    def properties(self) -> None:
        core = self.xml("docProps/core.xml")
        if core is None:
            return
        title = core.find("dc:title", NS)
        if title is not None and (title.text or "").strip():
            self.page.title = clean_title(title.text or "")
        creator = core.find("dc:creator", NS)
        if creator is not None and (creator.text or "").strip():
            self.page.author = (creator.text or "").strip()
        keywords = core.find("cp:keywords", NS)
        for word in re.split(r"[,;]", keywords.text or "") if keywords is not None else []:
            if (label := clean_label(word)) and label not in self.page.labels:
                self.page.labels.append(label)


def _page(path: str, data: bytes, bundle: Bundle) -> Page:
    page = Page(f"word:{path}", clean_title(stem(path)))
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        page.errors.append("This file is not a valid .docx. Save it again from Word.")
        return page
    try:
        doc = _Doc(path, archive, bundle, page)
        title, page.markdown = doc.body()
        if title:
            page.title = clean_title(title)
        doc.properties()
    except ET.ParseError as e:
        page.errors.append(f"The document's XML could not be read ({e}).")
    return page


def read_word(files: Files) -> Bundle:
    bundle = Bundle("word")
    pages: dict[str, Page] = {}
    for path in sorted(p for p in files if p.lower().endswith(".docx")):
        directory = posixpath.dirname(path)
        parent = None
        for depth in range(1, directory.count("/") + 2 if directory else 0):
            folder = "/".join(directory.split("/")[:depth])
            key = f"dir:{folder}"
            if key not in pages:
                pages[key] = Page(key, clean_title(posixpath.basename(folder)), parent, "folder")
            parent = key
        page = _page(path, files[path], bundle)
        page.parent_id = parent
        pages[page.external_id] = page
    if not pages:
        bundle.errors.append("No Word documents (.docx) were found in the upload.")
    bundle.pages = ordered(pages)
    return bundle
