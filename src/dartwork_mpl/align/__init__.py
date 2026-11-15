"""Text alignment: left, centre or right of an anchor; above, below or on it.

Platform vocabulary: labels and ticks both align text to an anchor; pure, no
matplotlib import.
"""

from .model import (
    AlignCentre,
    AlignLeft,
    AlignRight,
    Baseline,
    Bottom,
    HAlign,
    HAlignName,
    Top,
    VAlign,
    VAlignName,
    VCentre,
    VCentreBaseline,
    parse_halign,
    parse_valign,
)

__all__ = [
    "AlignCentre",
    "AlignLeft",
    "AlignRight",
    "Baseline",
    "Bottom",
    "HAlign",
    "HAlignName",
    "Top",
    "VAlign",
    "VAlignName",
    "VCentre",
    "VCentreBaseline",
    "parse_halign",
    "parse_valign",
]
