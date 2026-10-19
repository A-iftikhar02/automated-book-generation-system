"""Locating stored files (covers, exports) after the data has moved between machines or setups."""

from pathlib import Path

from ..config import settings


def resolve(path: str | None) -> Path | None:
    """Return the file for a stored path, re-rooting it under STORAGE_DIR when the original location is gone.

    Paths are saved as absolute paths (e.g. /data/storage/books/<id>/cover.jpg in Docker, or a path under a
    previous laptop's home folder). After a restore on another machine, everything from `books/` onwards is the same.
    """
    if not path:
        return None
    original = Path(path)
    if original.exists():
        return original
    parts = original.parts
    if "books" in parts:
        idx = len(parts) - 1 - parts[::-1].index("books")
        moved = Path(settings.STORAGE_DIR).joinpath(*parts[idx:])
        if moved.exists():
            return moved
    return original


def exists(path: str | None) -> bool:
    resolved = resolve(path)
    return bool(resolved and resolved.exists())
