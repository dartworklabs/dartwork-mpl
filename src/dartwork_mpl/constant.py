"""Standard figure width constants for matplotlib plots.

This module provides predefined figure width constants commonly used
in scientific publications and presentations.
"""

from .util import cm2in

__all__ = ["DW", "SW"]

# Single column figure width.
SW: float = cm2in(9)

# Double column figure width.
DW: float = cm2in(17)
