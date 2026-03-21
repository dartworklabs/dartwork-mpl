"""Standard figure-width constants for Matplotlib charts.

Defines standardized figure widths commonly used in academic papers
and presentations.
"""

from .util import cm2in

__all__ = [
    "DW",
    "SW",
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
]

# Single column figure width. STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
SW: float = cm2in(9)

# Double column figure width. STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
DW: float = cm2in(17)

# Standard figure size tuple (width, height) for single-column width.
FS_SINGLE: tuple[float, float] = (SW, SW * 0.75)

# Standard figure size tuple (width, height) for double-column width.
FS_DOUBLE: tuple[float, float] = (DW, DW * 0.5)

# Square aspect ratio figures
FS_SQUARE: tuple[float, float] = (SW, SW)

# Wide aspect ratio (good for timelines, horizontal comparisons)
FS_WIDE: tuple[float, float] = (DW, DW * 0.4)

# Tall aspect ratio (good for vertical stacking)
FS_TALL: tuple[float, float] = (SW, SW * 1.4)

# Golden ratio aspect
FS_GOLDEN: tuple[float, float] = (SW, SW / 1.618)

# 16:9 presentation slide aspect ratio
FS_SLIDE: tuple[float, float] = (10, 5.625)

# A4 paper aspect ratio (portrait)
FS_A4: tuple[float, float] = (8.27, 11.69)
