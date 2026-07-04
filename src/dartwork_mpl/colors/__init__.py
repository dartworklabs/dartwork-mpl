"""Color management and conversion utilities for Matplotlib.

Provides facilities for loading, registering, and converting colors
across OKLab, OKLCH, RGB, and Hex color spaces.
"""

from ._color import Color, color, cspace, hex, oklab, oklch, rgb
from ._compat_v4 import set_palette_version
from ._loader import ensure_loaded as _ensure_colors_loaded
from ._register import ensure_registered as _ensure_cmaps_registered
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
    "set_palette_version",
]

# Register bundled color palettes with matplotlib on first import.
_ensure_colors_loaded()

# Register the v5 cmap catalog + qualitative cycles (dc.<name> / dc.<name>_r
# / dc.cycle / dc.cycle_print) on first import — mirrors the palette load
# immediately above (eager, not lazy like the legacy asset/cmap/*.txt
# loader in dartwork_mpl.cmap).
_ensure_cmaps_registered()
