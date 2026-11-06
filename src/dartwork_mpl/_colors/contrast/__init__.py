"""WCAG contrast: relative luminance, contrast ratio and readable ink.

Responsibility: the WCAG 2.x luminance and contrast arithmetic, computed with
the colour model's sRGB linearisation, and the ink helpers built on it.

Surface: ``ensure_contrast`` and ``readable_text_color`` (re-exported by
``dartwork_mpl._colors``), ``composite_over`` and ``composite_layers`` (a colour
painted over an opaque one), ``contrast_ratio`` and ``wcag_relative_luminance``
(used by the validation checks).
"""

from ._contrast import (
    composite_layers,
    composite_over,
    ensure_contrast,
    readable_text_color,
)
from ._luminance import _contrast_ratio as contrast_ratio
from ._luminance import _wcag_relative_luminance as wcag_relative_luminance

__all__ = [
    "composite_layers",
    "composite_over",
    "contrast_ratio",
    "ensure_contrast",
    "readable_text_color",
    "wcag_relative_luminance",
]
