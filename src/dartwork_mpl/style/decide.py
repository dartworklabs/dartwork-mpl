"""Pure decisions: which layers a request applies, and what a step is worth."""

from __future__ import annotations

from ..vocab import DefaultLocale, KoreanLocale
from .model import KOREAN_LAYER, Active, Chain, Points, Preset, Steps, Weight

#: One ``dm.fs`` / ``dm.lw`` step on paper, reports and the web.
POINT = Points(1.0)
WEIGHT_STEP = 100


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


def bolder(base: Weight, n: Steps) -> Weight:
    """``base`` moved by ``n`` steps of 100, rounded to a whole weight."""
    return Weight(round(base.value + WEIGHT_STEP * n.n))
