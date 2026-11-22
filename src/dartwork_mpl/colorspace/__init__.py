"""Colour arithmetic: sRGB, OKLab and OKLCH values, compositing, WCAG contrast.

Platform code, pure: ``color`` builds its names and palettes on these values,
``labels`` composites a bar over its background and lifts ink to a readable
contrast, ``check`` measures text contrast, and both judge a text's ink
pixel by pixel against what is drawn behind it (:class:`Legibility`). Parsing a colour a caller or
matplotlib gives stays with each shell (``matplotlib.colors``).
"""

from ..edgecase import settle
from .decide import (
    composite_over,
    contrast,
    contrasts,
    legibility,
    lift,
    readable,
)
from .edges import LIFT_EDGES
from .model import (
    LEGIBLE,
    Color,
    Colours,
    ContrastFacts,
    DarkInk,
    Hex,
    Ink,
    Legibility,
    Lift,
    LightInk,
    Oklab,
    Oklch,
    Places,
    Ratio,
    Ratios,
    Rgb,
    Rgba,
    finite,
)

__all__ = [
    "LEGIBLE",
    "Color",
    "Colours",
    "ContrastFacts",
    "DarkInk",
    "Hex",
    "Ink",
    "Legibility",
    "Lift",
    "LightInk",
    "Oklab",
    "Oklch",
    "Places",
    "Ratio",
    "Ratios",
    "Rgb",
    "Rgba",
    "composite_over",
    "contrast",
    "contrasts",
    "finite",
    "legibility",
    "lifted",
    "readable",
]


def lifted(facts: ContrastFacts) -> Lift | None:
    """The least lightness move that reaches the target ratio once written as
    hex; ``None`` when the colour already reaches it."""
    return settle(facts, lift(facts), LIFT_EDGES).plan
