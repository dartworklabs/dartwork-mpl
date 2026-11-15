"""Horizontal text alignment: left, centre, right.

Platform vocabulary: labels and ticks both align text to an anchor; pure, no
matplotlib import.
"""

from .model import (
    AlignCentre,
    AlignLeft,
    AlignRight,
    HAlign,
    HAlignName,
    parse_halign,
)

__all__ = [
    "AlignCentre",
    "AlignLeft",
    "AlignRight",
    "HAlign",
    "HAlignName",
    "parse_halign",
]
