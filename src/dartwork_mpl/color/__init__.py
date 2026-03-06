"""Color management and conversion utilities for matplotlib.

This package provides color loading, registration, and conversion
functionality including support for OKLab, OKLCH, RGB, and hex color
spaces.
"""

# Load and register colors on import (side-effect).
from . import _loader  # noqa: F401

# Public API — backward-compatible with the old single-file module.
from ._color import Color, cspace, hex, named, oklab, oklch, rgb
from ._views import (
    OklabView,
    OklabViewIterator,
    OklchView,
    OklchViewIterator,
    RgbView,
    RgbViewIterator,
)

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
]
