"""Colour model: the ``Color`` value, its space views, conversion and gamut.

Responsibility: what a colour *is* — sRGB/OKLab/OKLCH conversion kernels,
sRGB gamut mapping and the public ``Color`` type with its views. It knows no
catalogue, registry or build.

Surface: the public ``Color`` constructors and views re-exported by
``dartwork_mpl._colors``; ``relative_y_srgb_d65`` and ``srgb_to_oklab`` for
validation checks; and the ``conversion`` and ``gamut`` kernel modules, which
the colour build and catalogue call by attribute (so tests can observe the
delegation). Narrowing those two namespaces to named functions is phase-3 work.
"""

from . import _conversion as conversion
from . import _gamut as gamut
from ._blend import mix_colors, pseudo_alpha
from ._color import Color, color, cspace, hex, oklab, oklch, rgb
from ._conversion import _srgb_to_oklab as srgb_to_oklab
from ._conversion import relative_y_srgb_d65
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
    "conversion",
    "cspace",
    "gamut",
    "hex",
    "mix_colors",
    "oklab",
    "oklch",
    "pseudo_alpha",
    "relative_y_srgb_d65",
    "rgb",
    "srgb_to_oklab",
]
