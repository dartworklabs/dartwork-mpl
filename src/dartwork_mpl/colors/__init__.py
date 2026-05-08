"""Color management and conversion utilities for Matplotlib.

Provides facilities for loading, registering, and converting colors
across OKLab, OKLCH, RGB, and Hex color spaces.
"""

from ._color import Color, color, cspace, hex, oklab, oklch, rgb
from ._loader import ensure_loaded as _ensure_colors_loaded
from ._typing import DartworkColor, DartworkColormap
from ._views import (
    OklabView,
    OklabViewIterator,
    OklchView,
    OklchViewIterator,
    RgbView,
    RgbViewIterator,
)

__all__ = [
    "Color",
    "DartworkColor",
    "DartworkColormap",
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    "color",
    "cspace",
    "hex",
    "oklab",
    "oklch",
    "rgb",
]

# Register bundled color palettes with matplotlib on first import.
_ensure_colors_loaded()
