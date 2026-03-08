"""Color management and conversion utilities for matplotlib.

This package provides color loading, registration, and conversion
functionality including support for OKLab, OKLCH, RGB, and hex color
spaces.
"""

from ._color import Color, cspace, hex, named, oklab, oklch, rgb
from ._loader import ensure_loaded as _ensure_colors_loaded
from ._views import (
    OklabView,
    OklabViewIterator,
    OklchView,
    OklchViewIterator,
    RgbView,
    RgbViewIterator,
)
from ._typing import DartworkColor, DartworkColormap

__all__ = [
    # Core
    "Color",
    "cspace",
    # Convenience constructors
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
    # View classes
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    # Typing
    "DartworkColor",
    "DartworkColormap",
]

# Register bundled color palettes with matplotlib on first import.
_ensure_colors_loaded()
