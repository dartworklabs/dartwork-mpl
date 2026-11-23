"""The words slices share: pure types, no matplotlib import.

One module per vocabulary. A string from the user or from matplotlib
becomes one of these types here, once.

``axis``  An Axes' x and y axis, and which side of it an axis label sits on.
``align``  Text alignment: left, centre or right of an anchor; above, below or on it.
``box``  A rectangle and an extent in display pixels.
``edge``  A box's four edges, and the figure edge a figure legend reserves.
``projection``  An Axes' projection: plain 2D, 3D or curved.
``number``  The scale a number prints in: the factor, prefix and suffix of a tick.
``locale``  A figure's locale: the default convention or Korea's.
``room``  The distance a column of text keeps from a plot and from another text.
"""

from .align import (
    AlignBottom,
    AlignCentre,
    AlignLeft,
    AlignRight,
    AlignTop,
    Baseline,
    HAlign,
    VAlign,
    VCentre,
    VCentreBaseline,
    parse_halign,
    parse_valign,
)
from .axis import (
    AxisSide,
    Far,
    Letters,
    Near,
    Which,
    X,
    Y,
    bars_along,
    parse_axes,
    parse_axis_side,
)
from .box import Box, Span
from .edge import EDGES, Bottom, Edge, Left, Reserve, Right, Top, edge_of
from .locale import DefaultLocale, KoreanLocale, Locale
from .number import AffixedZero, BareZero, ScaleZero, TickScale
from .numeric_text import NumericText, has_math
from .projection import (
    Curved,
    Projection,
    Rectilinear,
    ThreeD,
    parse_projection,
)
from .room import BESIDE_PLOT, BESIDE_TEXT, Room

__all__ = [
    "BESIDE_PLOT",
    "BESIDE_TEXT",
    "EDGES",
    "AffixedZero",
    "AlignBottom",
    "AlignCentre",
    "AlignLeft",
    "AlignRight",
    "AlignTop",
    "AxisSide",
    "BareZero",
    "Baseline",
    "Bottom",
    "Box",
    "Curved",
    "DefaultLocale",
    "Edge",
    "Far",
    "HAlign",
    "KoreanLocale",
    "Left",
    "Letters",
    "Locale",
    "Near",
    "NumericText",
    "Projection",
    "Rectilinear",
    "Reserve",
    "Right",
    "Room",
    "ScaleZero",
    "Span",
    "ThreeD",
    "TickScale",
    "Top",
    "VAlign",
    "VCentre",
    "VCentreBaseline",
    "Which",
    "X",
    "Y",
    "bars_along",
    "edge_of",
    "has_math",
    "parse_axes",
    "parse_axis_side",
    "parse_halign",
    "parse_projection",
    "parse_valign",
]
