"""Standard figure-width constants for Matplotlib charts.

Defines standardized figure widths commonly used in academic papers
and presentations.
"""

from .util import cm2in

__all__ = ["DW", "SW"]

# Single column figure width.
SW: float = cm2in(9)

# Double column figure width.
DW: float = cm2in(17)
