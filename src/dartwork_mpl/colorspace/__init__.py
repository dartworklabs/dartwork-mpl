"""Colour arithmetic: sRGB, OKLab and OKLCH values, compositing, WCAG contrast.

Platform code, pure: ``color`` builds its names and palettes on these values,
``labels`` composites a bar over its background and lifts ink to a readable
contrast, ``check`` measures text contrast. Parsing a colour a caller or
matplotlib gives stays with each shell (``matplotlib.colors``).
"""

from ..edgecase import settle
from .decide import composite_layers, composite_over, contrast, lift, readable
from .edges import LIFT_EDGES
from .model import (
    Color,
    ContrastFacts,
    DarkInk,
    Hex,
    Ink,
    Lift,
    LightInk,
    Oklab,
    Oklch,
    Ratio,
    Rgb,
    Rgba,
    finite,
)

__all__ = [
    "Color",
    "ContrastFacts",
    "DarkInk",
    "Hex",
    "Ink",
    "Lift",
    "LightInk",
    "Oklab",
    "Oklch",
    "Ratio",
    "Rgb",
    "Rgba",
    "composite_layers",
    "composite_over",
    "contrast",
    "finite",
    "lifted",
    "readable",
]


def lifted(facts: ContrastFacts) -> Lift | None:
    """The least lightness move that reaches the target ratio once written as
    hex; ``None`` when the colour already reaches it."""
    return settle(facts, lift(facts), LIFT_EDGES).plan
