"""WCAG relative luminance and contrast ratio.

Private to the contrast sub-slice; validation reaches these through the
``dartwork_mpl._colors.contrast`` surface. Not part of the public API.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..model import conversion

RGB = Sequence[float]


def _linearized(channel: float) -> float:
    """Convert an sRGB channel in 0..1 to linear light."""
    # Attribute lookup stays dynamic so delegation remains observable.
    return float(conversion._srgb_to_linear(channel))


def _wcag_relative_luminance(rgb: RGB) -> float:
    """Return WCAG relative luminance using its rounded coefficients."""
    red = _linearized(float(rgb[0]))
    green = _linearized(float(rgb[1]))
    blue = _linearized(float(rgb[2]))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _rel_lum(rgb: RGB) -> float:
    """Return WCAG luminance through the historical compatibility name."""
    return _wcag_relative_luminance(rgb)


def _contrast_ratio(foreground: RGB, background: RGB) -> float:
    """Return the WCAG contrast ratio between two sRGB colors."""
    hi, lo = sorted(
        (
            _wcag_relative_luminance(foreground),
            _wcag_relative_luminance(background),
        ),
        reverse=True,
    )
    return (hi + 0.05) / (lo + 0.05)
