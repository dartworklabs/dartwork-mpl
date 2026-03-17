"""Standard figure-width constants for Matplotlib charts.

Defines standardized figure widths commonly used in academic papers
and presentations.
"""

from .util import cm2in

__all__ = ["DW", "FS_DOUBLE", "FS_SINGLE", "SW"]

# Single column figure width. STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
SW: float = cm2in(9)

# Double column figure width. STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
DW: float = cm2in(17)

# Standard figure size tuple (width, height) for single-column width.
FS_SINGLE: tuple[float, float] = (SW, SW * 0.75)

# Standard figure size tuple (width, height) for double-column width.
FS_DOUBLE: tuple[float, float] = (DW, DW * 0.5)
