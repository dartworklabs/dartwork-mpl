"""The bundled plot templates and style files: lookup and the resource replies.

Templates are read through ``dartwork_mpl.guide`` by reference id
(``template/<id>``, ``template/advanced/<id>``); styles live in
``asset/mplstyle/*.mplstyle`` and are resolved through the platform's style
lookup.
"""

import json
from pathlib import Path

from dartwork_mpl import guide

from .._platform import resolve_style_path

_ASSET_DIR = Path(__file__).parents[2] / "asset"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"


def _prefix(advanced: bool) -> str:
    return "template/advanced/" if advanced else "template/"


def names(*, advanced: bool = False) -> list[str]:
    """The template ids of one tier, sorted."""
    prefix = _prefix(advanced)
    return sorted(
        ref.id.removeprefix(prefix)
        for ref in guide.references()
        if ref.id.startswith(prefix) and "/" not in ref.id.removeprefix(prefix)
    )


def source(plot_type: str, *, advanced: bool = False) -> str | None:
    """A template's source by case-insensitive id, or None for an unknown id."""
    try:
        return guide.read(_prefix(advanced) + plot_type.lower())
    except ValueError:
        return None


def exists(stem: str, *, advanced: bool = False) -> bool:
    """Whether a bundled template named exactly ``stem`` exists in the tier."""
    return stem in names(advanced=advanced)


def template_list() -> str:
    """JSON array of the basic template stems (``dartwork-mpl://templates/list``)."""
    return json.dumps(names(), indent=2)


def template_source(plot_type: str) -> str:
    """A basic template's source by case-insensitive bare ID, or not-found text."""
    found = source(plot_type)
    if found is None:
        return f"No template for {plot_type!r}. Available: {names()}"
    return found


def advanced_template_source(plot_type: str) -> str:
    """An advanced template's source, else the basic one's, else not-found text."""
    found = source(plot_type, advanced=True) or source(plot_type)
    if found is None:
        return f"No template for {plot_type!r}. Available: {names()}"
    return found


def style_list() -> str:
    """JSON array of the bundled style stems (``dartwork-mpl://styles/list``)."""
    if not _MPLSTYLE_DIR.exists():
        return json.dumps([])
    presets = sorted([p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")])
    return json.dumps(presets, indent=2)


def style_source(preset: str) -> str:
    """A bundled style's text by case-preserving bare ID, or not-found text."""
    style_file = resolve_style_path(preset)
    if style_file is None:
        available = sorted([p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")])
        return (
            f"Style preset '{preset}' not found. Available presets: {available}"
        )
    return style_file.read_text(encoding="utf-8")
