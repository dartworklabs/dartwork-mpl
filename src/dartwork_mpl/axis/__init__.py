"""An Axes' x and y axis, and which side of it an axis label sits on.

Platform vocabulary: pure types every slice names the same way, with no
matplotlib import, so a slice's pure files may use them.
"""

from .model import (
    AxisSide,
    Far,
    Letter,
    Letters,
    Near,
    Which,
    X,
    Y,
    bars_along,
    parse_axes,
    parse_axis_side,
    parse_which,
)

__all__ = [
    "AxisSide",
    "Far",
    "Letter",
    "Letters",
    "Near",
    "Which",
    "X",
    "Y",
    "bars_along",
    "parse_axes",
    "parse_axis_side",
    "parse_which",
]
