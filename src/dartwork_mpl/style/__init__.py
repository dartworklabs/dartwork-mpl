"""Presets, and sizes relative to the active one.

``dm.style.use("report")`` sets matplotlib's rcParams to a shipped preset;
``dm.style.context(...)`` does it for one block. ``dm.fs(n)``, ``dm.lw(n)``
and ``dm.fw(n)`` read the preset's font size, line width and weight and move
them by ``n`` steps, so a chart keeps its proportions under every preset.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import MappingProxyType

from ..edgecase import settle
from . import apply, decide, measure
from .edges import EDGES
from .measure import load_style_dict
from .model import SLIDE_SCALE, Active, Points, Steps

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

#: Every shipped preset and the style layers it applies, in order.
presets: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {name: p.layers for name, p in apply.REGISTRY.presets.items()}
)


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
    apply.use(preset, rc)


def context(
    preset: str | list[str], **rc: object
) -> AbstractContextManager[None]:
    """:func:`use` for one ``with`` block; everything is restored after."""
    return apply.context(preset, rc)


def active_presets() -> tuple[str, ...]:
    """The preset names the last :func:`use` (or innermost context) applied."""
    return tuple(p.name for p in apply.STATE[0].presets)


def active_preset_rcparams() -> dict[str, object]:
    """Copies of the values the active preset's layers set, without the
    keys passed as overrides; ``{}`` when no preset is in force (none
    applied, or a native ``plt.rcdefaults()`` since)."""
    values = copy.deepcopy(apply.STATE[0].values)
    return values if measure.in_force(values) else {}


def step_pt() -> float:
    """Points one ``dm.fs`` / ``dm.lw`` step adds now: 1, or
    :data:`SLIDE_SCALE` under ``presentation`` / ``presentation-kr``."""
    return _step().pt


def fs(n: float) -> float:
    """The preset's font size plus ``n`` steps: ``dm.fs(-1)`` for a note,
    ``dm.fs(2)`` for a title. A step is 1 pt, 2.6 pt on slides."""
    size = decide.offset(measure.font_size(), Steps(float(n)), _step())
    return size.pt


def lw(n: float) -> float:
    """The preset's line width plus ``n`` steps (1 pt, 2.6 pt on slides)."""
    width = decide.offset(measure.line_width(), Steps(float(n)), _step())
    return width.pt


def fw(n: float) -> int:
    """The preset's font weight plus ``100 * n``: ``dm.fw(1)`` one step
    bolder. A weight name such as ``"light"`` counts as its number."""
    return decide.bolder(measure.font_weight(), Steps(float(n))).value


def _step() -> Points:
    state = apply.STATE[0]
    active = Active(state.presets, measure.in_force(state.values))
    return settle(active, decide.step(active), EDGES).plan
