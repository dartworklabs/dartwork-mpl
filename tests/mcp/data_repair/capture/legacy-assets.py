"""Resolve MCP asset IDs to regular files confined to their bundled roots.

The package installation is trusted and stable during reads; this boundary does
not protect against concurrent hostile replacement of bundled files.
"""

import re
from pathlib import Path

__all__ = ["resolve_style_path", "resolve_template_path"]

_ASSET_DIR = Path(__file__).parent.parent / "asset"
_TEMPLATE_DIR = _ASSET_DIR / "prompt" / "05-templates"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"
_TEMPLATE_ID_RE = re.compile(r"[a-z0-9_]+")
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


def resolve_template_path(
    plot_type: str, *, advanced: bool = False
) -> Path | None:
    """Resolve a case-insensitive bare template ID within its selected tier.

    Reject incomplete/encoded paths and nonfiles with None. Advanced lookup
    does not fall back; callers apply fallback through this same boundary.
    """
    stem = plot_type.lower()
    if _TEMPLATE_ID_RE.fullmatch(stem) is None:
        return None
    root = _TEMPLATE_DIR / "advanced" if advanced else _TEMPLATE_DIR
    return _resolve_file(root, stem, ".py")


def resolve_style_path(preset: str) -> Path | None:
    """Resolve a bare style ID without case normalization, or None for unsafe/missing files."""
    if _STYLE_ID_RE.fullmatch(preset) is None:
        return None
    return _resolve_file(_MPLSTYLE_DIR, preset, ".mplstyle")
