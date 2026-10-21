"""Content type detection and image processing for attachments. No database access."""

import io
import json
from dataclasses import dataclass

import filetype
from PIL import Image, ImageOps

# Longest side in pixels for each size preset; None keeps the original size.
PRESETS: dict[str, int | None] = {"original": None, "large": 2048, "medium": 1280, "small": 800}
VARIANTS: dict[str, int] = {"thumb": 320, "preview": 1280}
QUALITY = 82
IMAGE_TYPES = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP", "image/gif": "GIF"}
TEXT_SNIFF_BYTES = 8192


@dataclass(frozen=True)
class Processed:
    data: bytes
    mime_type: str
    width: int | None
    height: int | None


def detect(data: bytes) -> str:
    """MIME type from the bytes themselves, never from the file name."""
    kind = filetype.guess(data)
    if kind is not None:
        return str(kind.mime)
    head = data[:TEXT_SNIFF_BYTES]
    if b"\x00" in head:
        return "application/octet-stream"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "application/octet-stream"
    stripped = text.strip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(stripped)
            return "application/json"
        except ValueError:
            pass
    return "text/plain"


def is_image(mime_type: str) -> bool:
    return mime_type in IMAGE_TYPES


def _is_animated(image: Image.Image) -> bool:
    return bool(getattr(image, "is_animated", False))


def _save(image: Image.Image, fmt: str) -> bytes:
    out = io.BytesIO()
    if fmt == "JPEG":
        image = image.convert("RGB") if image.mode not in ("RGB", "L") else image
        image.save(out, fmt, quality=QUALITY, optimize=True)
    elif fmt == "WEBP":
        image.save(out, fmt, quality=QUALITY)
    elif fmt == "PNG":
        image.save(out, fmt, optimize=True)
    else:
        image.save(out, fmt)
    return out.getvalue()


def process(data: bytes, mime_type: str, preset: str) -> Processed:
    """Strip EXIF, fix the orientation and shrink to the preset (never enlarge).

    Animated GIFs are kept as they are.
    """
    with Image.open(io.BytesIO(data)) as source:
        if mime_type == "image/gif" and _is_animated(source):
            return Processed(data, mime_type, source.width, source.height)
        image = ImageOps.exif_transpose(source)
        limit = PRESETS[preset]
        if limit is not None and max(image.size) > limit:
            image.thumbnail((limit, limit), Image.Resampling.LANCZOS)
        clean = image.copy()  # drops EXIF and other metadata
        return Processed(_save(clean, IMAGE_TYPES[mime_type]), mime_type, clean.width, clean.height)


def dimensions(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.width, image.height


def variant(data: bytes, max_side: int) -> Processed:
    """A webp copy no larger than `max_side`, for thumbnails and previews."""
    with Image.open(io.BytesIO(data)) as source:
        image = source.copy()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        if max(image.size) > max_side:
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return Processed(_save(image, "WEBP"), "image/webp", image.width, image.height)
