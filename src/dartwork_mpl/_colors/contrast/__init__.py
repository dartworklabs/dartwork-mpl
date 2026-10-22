"""WCAG contrast: relative luminance, contrast ratio and readable ink.

Responsibility: the WCAG 2.x luminance and contrast arithmetic, computed with
the colour model's sRGB linearisation, and the ink helpers built on it.

Surface: ``ensure_contrast`` and ``readable_text_color`` (re-exported by
``dartwork_mpl._colors``), ``contrast_ratio`` and ``wcag_relative_luminance``
(used by the validation checks).
"""

from ._contrast import ensure_contrast, readable_text_color
from ._luminance import _contrast_ratio as contrast_ratio
from ._luminance import _wcag_relative_luminance as wcag_relative_luminance

__all__ = [
    "contrast_ratio",
    "ensure_contrast",
    "readable_text_color",
    "wcag_relative_luminance",
]
