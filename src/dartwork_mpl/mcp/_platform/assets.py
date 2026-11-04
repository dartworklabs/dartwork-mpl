"""Resolve MCP style IDs to regular files confined to their bundled roots.

The package installation is trusted and stable during reads; this boundary does
not protect against concurrent hostile replacement of bundled files.
"""

import re
from pathlib import Path

__all__ = ["resolve_style_path"]

_ASSET_DIR = Path(__file__).parents[2] / "asset"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"
_STYLE_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


def _resolve_file(root: Path, stem: str, suffix: str) -> Path | None:
    """Return a resolved regular file under root, or None for unsafe/missing files.

    Callers supply an already parsed bare stem. Symlink loops and filesystem
    errors deny access, just as missing assets do.
    """
    try:
        resolved_root = root.resolve()
        path = (resolved_root / f"{stem}{suffix}").resolve()
        if path.is_relative_to(resolved_root) and path.is_file():
            return path
    except (OSError, RuntimeError):
        return None
    return None


def resolve_style_path(preset: str) -> Path | None:
    """Resolve a bare style ID without case normalization, or None for unsafe/missing files."""
    if _STYLE_ID_RE.fullmatch(preset) is None:
        return None
    return _resolve_file(_MPLSTYLE_DIR, preset, ".mplstyle")
