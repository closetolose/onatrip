"""Optimize phone camera uploads (iPhone / Realme) for web display."""

from __future__ import annotations

from pathlib import Path

# Long edge cap: sharp on retina, smaller than typical 12 MP originals (~4032 px).
MAX_LONG_EDGE = 2048
JPEG_QUALITY = 88


def _save_image(im, path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    elif suffix == ".webp":
        im.save(path, "WEBP", quality=JPEG_QUALITY, method=6)
    elif suffix == ".png":
        im.save(path, "PNG", optimize=True)
    else:
        im.save(path, optimize=True)


def optimize_image_file(path: Path, *, max_edge: int = MAX_LONG_EDGE) -> bool:
    """Fix EXIF orientation and downscale large phone photos in place."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return False

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return False

    with Image.open(path) as src:
        im = ImageOps.exif_transpose(src)
        resized = max(im.size) > max_edge
        if resized:
            im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        _save_image(im, path)

    return resized
