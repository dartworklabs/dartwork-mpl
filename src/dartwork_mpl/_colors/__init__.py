"""Color management and conversion utilities for Matplotlib.

Provides facilities for loading, registering, and converting colors
across OKLab, OKLCH, RGB, and Hex color spaces.
"""

from ._api import colors, list_colors, set_colors, show_colors
from ._color import Color, color, cspace, hex, oklab, oklch, rgb
from ._contrast import ensure_contrast, readable_text_color
from ._loader import ensure_loaded as _ensure_colors_loaded
from ._register import ensure_registered as _ensure_cmaps_registered
from ._semantic import apply_semantic as _apply_default_semantic
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
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    "color",
    "colors",
    "cspace",
    "ensure_contrast",
    "hex",
    "list_colors",
    "oklab",
    "oklch",
    "readable_text_color",
    "rgb",
    "set_colors",
    "show_colors",
]

# Register bundled color palettes with matplotlib on first import.
_ensure_colors_loaded()

# Register the v5 cmap catalog + qualitative cycles (dc.<name> / dc.<name>_r
# / dc.octave / dc.octave_print) on first import — mirrors the palette load
# immediately above.
_ensure_cmaps_registered()

# Register the locale-aware semantic tokens (dc.pos/neg/ref/hl, spec §10)
# with the default (non-KR) mapping on first import — same eager pattern
# as the two calls above, so the "dc." namespace count stays fixed
# regardless of whether a ``Style.use(...)`` call has happened yet in
# this process. ``Style.use`` re-applies with the correct locale (kr vs
# default) on every preset switch; it never changes which keys exist,
# only their values.
_apply_default_semantic("default")
