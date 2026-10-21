"""Reading an uploaded export safely: size limits, zip bombs and paths that try to leave
the archive are refused before any importer sees a file."""

import io
import posixpath
import zipfile

from radicle.folio.services.assets import PayloadTooLarge
from radicle.platform.errors import ValidationFailed

MAX_UPLOAD = 100 * 1024 * 1024
MAX_FILES = 5_000
MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
MAX_RATIO = 200  # uncompressed / compressed, for files over 1 MB

Files = dict[str, bytes]


def _invalid(message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": "file", "message": "invalid"}])


def safe_path(name: str) -> str | None:
    """The archive path normalized, or None for one that leaves the archive or is noise."""
    path = name.replace("\\", "/")
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return None
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        return None
    if parts[0] == "__MACOSX" or any(p.startswith(".") for p in parts):
        return None
    return posixpath.join(*parts)


def read(filename: str, data: bytes) -> Files:
    """The files in the upload: a zip's contents, or the single file itself."""
    if len(data) > MAX_UPLOAD:
        raise PayloadTooLarge(
            f"The upload is {len(data) / 1024 / 1024:.0f} MB; imports take up to "
            f"{MAX_UPLOAD // 1024 // 1024} MB. Split the export and import it in parts."
        )
    if not data:
        raise _invalid("The file is empty.")
    if not zipfile.is_zipfile(io.BytesIO(data)) or filename.lower().endswith(".docx"):
        name = safe_path(filename.rsplit("/", 1)[-1]) or "upload"
        return {name: data}
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise _invalid("The zip file is damaged. Export it again.") from None
    entries = [i for i in archive.infolist() if not i.is_dir()]
    if len(entries) > MAX_FILES:
        raise _invalid(f"The zip has {len(entries)} files; imports take up to {MAX_FILES}.")
    out: Files = {}
    total = 0
    for info in entries:
        path = safe_path(info.filename)
        if path is None:
            continue
        if info.file_size > MAX_FILE:
            raise _invalid(f"{path} is over {MAX_FILE // 1024 // 1024} MB.")
        if info.file_size > 1024 * 1024 and info.file_size > MAX_RATIO * max(info.compress_size, 1):
            raise _invalid(f"{path} expands too much to be a real export.")
        total += info.file_size
        if total > MAX_TOTAL:
            raise _invalid(
                f"The zip expands to over {MAX_TOTAL // 1024 // 1024} MB. Import it in parts."
            )
        with archive.open(info) as f:
            content = f.read(MAX_FILE + 1)
        if len(content) > MAX_FILE:  # the header lied about the size
            raise _invalid(f"{path} is over {MAX_FILE // 1024 // 1024} MB.")
        out[path] = content
    if not out:
        raise _invalid("The zip has no files to import.")
    return out


def text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
