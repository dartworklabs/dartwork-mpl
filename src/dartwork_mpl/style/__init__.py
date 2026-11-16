"""Presets, and sizes relative to the active one.

:func:`use` sets matplotlib's rcParams to a shipped preset and
:func:`context` does it for one block; each hands the preset's locale to the
function :func:`join` was given (the colour slice's role colours, joined in
by ``compose.style``). ``dm.fs(n)``, ``dm.lw(n)`` and ``dm.fw(n)`` read the preset's font size, line width and weight and move
them by ``n`` steps, so a chart keeps its proportions under every preset.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import MappingProxyType

from ..edgecase import settle
from ..vocab import Locale
from . import apply, decide, measure
from .apply import Tint
from .edges import EDGES
from .measure import load_style_dict
from .model import SLIDE_SCALE, Active, Points, Steps

__all__ = [
    "SLIDE_SCALE",
    "Tint",
    "active_locale",
    "active_presets",
    "context",
    "fs",
    "fw",
    "join",
    "load_style_dict",
    "lw",
    "presets",
    "use",
]

#: Every shipped preset and the style layers it applies, in order.
presets: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {name: p.layers for name, p in apply.REGISTRY.presets.items()}
)


def join(tint: Tint) -> None:
    """Hand every applied preset's locale to ``tint`` from now on.

    The slice knows no colours; ``compose.style`` joins the colour slice's
    role colours in, once, when the package is imported.
    """
    apply.TINT[0] = tint


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


def active_locale() -> Locale:
    """Whose convention the active preset follows (the default: none applied)."""
    return apply.STATE[0].locale


def active_presets() -> tuple[str, ...]:
    """The preset names the last :func:`use` (or innermost context) applied."""
    return tuple(p.name for p in apply.STATE[0].presets)


def fs(n: float) -> float:
    """The preset's font size plus ``n`` steps: ``dm.fs(-1)`` for a note,
    ``dm.fs(2)`` for a title. A step is 1 pt, 2.6 pt on slides; a step
    that would reach zero stops at the smallest whole step above it."""
    size = decide.smaller(measure.font_size(), Steps(float(n)), _step())
    return size.pt


def lw(n: float) -> float:
    """The preset's line width plus ``n`` steps (1 pt, 2.6 pt on slides).

    Below the base a step takes off one step while half a step is left,
    and halves the width after that: ``dm.lw(-1)`` is 0.5 pt on ``report``.
    """
    width = decide.thinner(measure.line_width(), Steps(float(n)), _step())
    return width.pt


def fw(n: float) -> int:
    """The preset's font weight plus ``100 * n``, held within 100-900:
    ``dm.fw(1)`` one step bolder. A weight name such as ``"light"`` counts
    as its number."""
    return decide.bolder(measure.font_weight(), Steps(float(n))).value


def _step() -> Points:
    state = apply.STATE[0]
    active = Active(state.presets, measure.in_force(state.values))
    return settle(active, decide.step(active), EDGES).plan
