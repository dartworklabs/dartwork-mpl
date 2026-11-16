"""Pure decisions: which layers a request applies, and what a step is worth."""

from __future__ import annotations

import math

from ..vocab import DefaultLocale, KoreanLocale
from .model import KOREAN_LAYER, Active, Chain, Points, Preset, Steps, Weight

#: One ``dm.fs`` / ``dm.lw`` step on paper, reports and the web.
POINT = Points(1.0)
WEIGHT_STEP = 100
#: The weights matplotlib draws: 0 falls back, below or above 900 fails.
LIGHTEST, HEAVIEST = 100, 900


def chain(presets: tuple[Preset, ...]) -> Chain:
    """The presets' layers in order; Korean if any layer is ``lang-kr``."""
    layers = tuple(layer for preset in presets for layer in preset.layers)
    locale = KoreanLocale() if KOREAN_LAYER in layers else DefaultLocale()
    return Chain(presets, layers, locale)


def step(active: Active) -> Points:
    """One step on the ordinary page: a point (slides: see ``edges``)."""
    return POINT


def offset(base: Points, n: Steps, size: Points) -> Points:
    """``base`` moved by ``n`` steps of ``size``."""
    return Points(base.pt + n.n * size.pt)


def thinner(base: Points, n: Steps, size: Points) -> Points:
    """A line width ``n`` steps of ``size`` from ``base``, never zero.

    Above the base and down to half a step, as :func:`offset`; below that
    each step halves the width (``report``: 1, 0.5, 0.25), so a thinner
    line is still drawn.
    """
    # Whole steps that leave at least half a step: 0 on report, 1 on poster.
    ladder = max(0, math.floor(base.pt / size.pt - 0.5))
    if n.n >= -ladder:
        return offset(base, n, size)
    last = base.pt - ladder * size.pt
    return Points(last * 2.0 ** (n.n + ladder))


def smaller(base: Points, n: Steps, size: Points) -> Points:
    """A font size ``n`` steps of ``size`` from ``base``, never zero.

    As :func:`offset` while that is above zero; past it, the smallest whole
    step above zero (``report``: 1 pt, ``scientific``: 0.5 pt).
    """
    moved = offset(base, n, size)
    if moved.pt > 0:
        return moved
    floor = base.pt - (math.ceil(base.pt / size.pt) - 1) * size.pt
    return Points(floor)


def bolder(base: Weight, n: Steps) -> Weight:
    """``base`` moved by ``n`` steps of 100, rounded to a whole weight and
    held within 100-900."""
    moved = round(base.value + WEIGHT_STEP * n.n)
    return Weight(min(HEAVIEST, max(LIGHTEST, moved)))
