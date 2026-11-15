"""``dm.style``: presets, joined with the bundled fonts and the role colours.

The style slice writes rcParams and knows neither fonts nor colours. A preset
names bundled font families, so the fonts are registered first; a preset's
locale picks the role colours ``dc.pos`` / ``dc.neg``, so the colour slice
binds them after. The rest of the preset surface is the slice's own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartwork_mpl import style
from dartwork_mpl.color import apply_semantic
from dartwork_mpl.font import ensure_loaded
from dartwork_mpl.style import (
    SLIDE_SCALE,
    active_preset_rcparams,
    active_presets,
    fs,
    fw,
    load_style_dict,
    lw,
    presets,
    step_pt,
)

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

__all__ = [
    "SLIDE_SCALE",
    "active_preset_rcparams",
    "active_presets",
    "context",
    "fs",
    "fw",
    "load_style_dict",
    "lw",
    "presets",
    "step_pt",
    "use",
]


def use(preset: str | list[str], **rc: object) -> None:
    """Apply a preset, or several in order, then ``rc`` overrides.

    Presets: ``scientific`` (papers), ``report`` (documents, dashboards),
    ``minimal``, ``presentation`` (slides), ``poster``, ``web``, ``dark``,
    and a Korean ``-kr`` twin of each. rcParams start from matplotlib's
    defaults: nothing of an earlier preset is left, but your own rcParams
    edits on keys the preset does not set are kept.
    Overrides take ``font_size=12`` or ``**{"font.size": 12}``. ``TypeError``
    for a name that is not a string, ``KeyError`` for an unknown preset or
    rcParam, ``ValueError`` for an invalid value; a rejected call changes
    nothing::

        dm.style.use("report")
        dm.style.use("presentation-kr", font_size=16)
    """
    ensure_loaded()
    style.use(preset, rc, apply_semantic)


def context(
    preset: str | list[str], **rc: object
) -> AbstractContextManager[None]:
    """:func:`use` for one ``with`` block; everything is restored after."""
    ensure_loaded()
    return style.context(preset, rc, apply_semantic)
