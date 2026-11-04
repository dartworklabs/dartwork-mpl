"""The bundled plot templates and style files: lookup and the resource replies.

Templates live in ``asset/prompt/05-templates/{plot_type}.py`` (tier 2 in
``advanced/``) and styles in ``asset/mplstyle/*.mplstyle``; IDs are resolved
through prompt's corpus operations and the platform's style lookup.
"""

import json
from pathlib import Path

from dartwork_mpl.prompt import (
    list_template_names,
    resolve_template_path,
    template_exists,
)

from .._platform import resolve_style_path

_ASSET_DIR = Path(__file__).parents[2] / "asset"
_MPLSTYLE_DIR = _ASSET_DIR / "mplstyle"


def _resolve_template_path(
    plot_type: str, *, advanced: bool = False
) -> Path | None:
    """Delegate template lookup to the prompt owner's confined corpus boundary.

    Preserve the private compatibility surface while returning the resolved
    regular file checked by that boundary, or None for invalid/missing IDs.
    """
    return resolve_template_path(plot_type, advanced=advanced)


def exists(stem: str, *, advanced: bool = False) -> bool:
    """Whether a bundled template file named exactly ``stem`` exists in the tier."""
    return template_exists(stem, advanced=advanced)


def template_list() -> str:
    """JSON array of the basic template stems (``dartwork-mpl://templates/list``)."""
    names = list_template_names()
    return json.dumps(names, indent=2)


def template_source(plot_type: str) -> str:
    """A basic template's source by case-insensitive bare ID, or not-found text."""
    path = resolve_template_path(plot_type)
    if path is None:
        available = list_template_names()
        return f"No template for {plot_type!r}. Available: {available}"
    return path.read_text(encoding="utf-8")


def advanced_template_source(plot_type: str) -> str:
    """An advanced template's source, else the basic one's, else not-found text."""
    advanced = resolve_template_path(plot_type, advanced=True)
    if advanced is not None:
        return advanced.read_text(encoding="utf-8")
    basic = resolve_template_path(plot_type)
    if basic is not None:
        return basic.read_text(encoding="utf-8")
    available = list_template_names()
    return f"No template for {plot_type!r}. Available: {available}"


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
