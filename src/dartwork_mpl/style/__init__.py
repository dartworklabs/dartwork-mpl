"""Presets, and sizes relative to the active one.

:func:`use` sets matplotlib's rcParams to a shipped preset and
:func:`context` does it for one block; each hands the preset's locale to a
function the caller passes (``dm.style`` passes the colour slice's). ``dm.fs(n)``, ``dm.lw(n)``
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
from .apply import Tint
from .edges import EDGES
from .measure import load_style_dict
from .model import SLIDE_SCALE, Active, Points, Steps

__all__ = [
    "SLIDE_SCALE",
    "Tint",
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


def use(preset: str | list[str], rc: dict[str, object], tint: Tint) -> None:
    """Apply ``preset`` (a name or several, in order), then the ``rc``
    overrides, then hand the preset's locale to ``tint``.

    ``dm.style.use`` is this joined with the bundled fonts and the colour
    slice's role colours (``compose.style``).
    """
    apply.use(preset, rc, tint)


def context(
    preset: str | list[str], rc: dict[str, object], tint: Tint
) -> AbstractContextManager[None]:
    """:func:`use` for one ``with`` block; everything is restored after,
    ``tint`` given the earlier preset's locale again."""
    return apply.context(preset, rc, tint)


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
