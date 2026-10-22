"""Canonical sRGB, OKLab, OKLCH, hex, and modeled-relative-Y conversions.

This module is the sole production math kernel for color conversion. Validation
metrics and WCAG helpers delegate here; this module does not import them.
"""

from __future__ import annotations

__all__: list[str] = []  # All functions are private (_-prefixed)

import math
import re
from typing import Any, TypeAlias

import numpy as np

Rgb: TypeAlias = tuple[float, float, float]
Oklab: TypeAlias = tuple[float, float, float]

# Nominal D65 sRGB modeled-relative-CIE-Y row. These coefficients normalize
# the legacy v5 row to make white exactly 1 while preserving shipped 8-bit
# output. The result is calculated from source sRGB.
# It is not a measurement of a display or print process.
# The unnormalized legacy row belongs only to private CIELAB validation.
SRGB_D65_Y: Rgb = (0.21267287873271212, 0.7151521284847872, 0.07217499278250072)


def _srgb_to_linear(
    c: float | np.ndarray[Any, Any],
) -> float | np.ndarray[Any, Any]:
    """Convert an sRGB channel or array to linear RGB.

    Parameters
    ----------
    c : float or array
        sRGB value(s) in range [0, 1].

    Returns
    -------
    float or array
        Linear RGB value(s) in range [0, 1].
    """
    if isinstance(c, np.ndarray):
        channels: np.ndarray[Any, Any] = c
        linear: np.ndarray[Any, Any] = np.empty(
            channels.shape, dtype=np.result_type(channels.dtype, 1.0)
        )
        linear_branch: np.ndarray[Any, Any] = channels <= 0.04045
        linear[linear_branch] = channels[linear_branch] / 12.92
        nonlinear_branch: np.ndarray[Any, Any] = ~linear_branch
        linear[nonlinear_branch] = (
            (channels[nonlinear_branch] + 0.055) / 1.055
        ) ** 2.4
        return linear

    channel = float(c)
    if channel <= 0.04045:
        return channel / 12.92
    return float(((channel + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(
    c: float | np.ndarray[Any, Any],
) -> float | np.ndarray[Any, Any]:
    """Convert a linear-RGB channel or array to sRGB.

    Parameters
    ----------
    c : float or array
        Linear RGB value(s) in range [0, 1].

    Returns
    -------
    float or array
        sRGB value(s) in range [0, 1].
    """
    if isinstance(c, np.ndarray):
        channels: np.ndarray[Any, Any] = c
        encoded: np.ndarray[Any, Any] = np.empty(
            channels.shape, dtype=np.result_type(channels.dtype, 1.0)
        )
        linear_branch: np.ndarray[Any, Any] = channels <= 0.0031308
        encoded[linear_branch] = 12.92 * channels[linear_branch]
        nonlinear_branch: np.ndarray[Any, Any] = ~linear_branch
        encoded[nonlinear_branch] = (
            1.055 * channels[nonlinear_branch] ** (1.0 / 2.4) - 0.055
        )
        return encoded

    channel = float(c)
    if channel <= 0.0031308:
        return 12.92 * channel
    return float(1.055 * channel ** (1.0 / 2.4) - 0.055)


def _linear_srgb_to_oklab(
    r: float, g: float, b: float
) -> tuple[float, float, float]:
    """
    Convert linear sRGB to OKLab.

    Based on the C++ implementation provided.

    Parameters
    ----------
    r, g, b : float
        Linear RGB values in range [0, 1].

    Returns
    -------
    tuple[float, float, float]
        (L, a, b) OKLab coordinates.
    """
    # Matrix multiplication to LMS
    lms_l: float = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    lms_m: float = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    lms_s: float = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    # Cube root
    lms_l_cbrt: float = float(np.cbrt(lms_l))
    lms_m_cbrt: float = float(np.cbrt(lms_m))
    lms_s_cbrt: float = float(np.cbrt(lms_s))

    # Matrix multiplication to OKLab
    L: float = (
        0.2104542553 * lms_l_cbrt
        + 0.7936177850 * lms_m_cbrt
        - 0.0040720468 * lms_s_cbrt
    )
    a: float = (
        1.9779984951 * lms_l_cbrt
        - 2.4285922050 * lms_m_cbrt
        + 0.4505937099 * lms_s_cbrt
    )
    b_val: float = (
        0.0259040371 * lms_l_cbrt
        + 0.7827717662 * lms_m_cbrt
        - 0.8086757660 * lms_s_cbrt
    )

    return (L, a, b_val)


def _srgb_to_oklab(rgb: Rgb) -> Oklab:
    """Convert an encoded sRGB triple to OKLab.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Encoded sRGB channels.

    Returns
    -------
    tuple[float, float, float]
        OKLab ``(L, a, b)`` coordinates as Python floats.
    """
    red = float(_srgb_to_linear(rgb[0]))
    green = float(_srgb_to_linear(rgb[1]))
    blue = float(_srgb_to_linear(rgb[2]))
    return _linear_srgb_to_oklab(red, green, blue)


def relative_y_srgb_d65(rgb: Rgb) -> float:
    """Return modeled relative CIE Y for encoded nominal D65 sRGB.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Encoded sRGB channels.

    Returns
    -------
    float
        Linear-light normalized model coordinate. Nominal sRGB white is
        exactly ``1.0``.

    Notes
    -----
    The explicit multiply/add order is part of the compatibility contract.
    This calculated value is neither a display measurement nor perceived
    brightness, and it is not the rounded WCAG contrast-luminance calculation.
    """
    red = float(_srgb_to_linear(rgb[0]))
    green = float(_srgb_to_linear(rgb[1]))
    blue = float(_srgb_to_linear(rgb[2]))
    red_green = SRGB_D65_Y[0] * red + SRGB_D65_Y[1] * green
    return float(red_green + SRGB_D65_Y[2] * blue)


def _oklab_to_linear_srgb(
    L: float, a: float, b: float
) -> tuple[float, float, float]:
    """
    Convert OKLab to linear sRGB.

    Based on the C++ implementation provided.

    Parameters
    ----------
    L, a, b : float
        OKLab coordinates.

    Returns
    -------
    tuple[float, float, float]
        (r, g, b) linear RGB values in range [0, 1].
    """
    # Matrix multiplication to LMS
    lms_l_cbrt: float = L + 0.3963377774 * a + 0.2158037573 * b
    lms_m_cbrt: float = L - 0.1055613458 * a - 0.0638541728 * b
    lms_s_cbrt: float = L - 0.0894841775 * a - 1.2914855480 * b

    # Cube
    lms_l: float = lms_l_cbrt * lms_l_cbrt * lms_l_cbrt
    lms_m: float = lms_m_cbrt * lms_m_cbrt * lms_m_cbrt
    lms_s: float = lms_s_cbrt * lms_s_cbrt * lms_s_cbrt

    # Matrix multiplication to linear RGB
    r: float = (
        +4.0767416621 * lms_l - 3.3077115913 * lms_m + 0.2309699292 * lms_s
    )
    g: float = (
        -1.2684380046 * lms_l + 2.6097574011 * lms_m - 0.3413193965 * lms_s
    )
    b_val: float = (
        -0.0041960863 * lms_l - 0.7034186147 * lms_m + 1.7076147010 * lms_s
    )

    return (r, g, b_val)


def _oklab_to_oklch(L: float, a: float, b: float) -> tuple[float, float, float]:
    """
    Convert OKLab to OKLCH.

    Parameters
    ----------
    L, a, b : float
        OKLab coordinates.

    Returns
    -------
    tuple[float, float, float]
        (L, C, h) OKLCH coordinates, where h is in radians.
    """
    C: float = math.sqrt(a * a + b * b)
    h: float = math.atan2(b, a)
    return (L, C, h)


def _oklch_to_oklab(L: float, C: float, h: float) -> tuple[float, float, float]:
    """
    Convert OKLCH to OKLab.

    Parameters
    ----------
    L, C : float
        Lightness and Chroma.
    h : float
        Hue in radians.

    Returns
    -------
    tuple[float, float, float]
        (L, a, b) OKLab coordinates.
    """
    a: float = C * math.cos(h)
    b: float = C * math.sin(h)
    return (L, a, b)


def _oklab_to_oklch_degrees(
    L: float, a: float, b: float
) -> tuple[float, float, float]:
    """Convert OKLab to OKLCH with hue expressed in degrees.

    Parameters
    ----------
    L, a, b : float
        OKLab coordinates.

    Returns
    -------
    tuple[float, float, float]
        ``(L, C, h)`` with hue normalized to ``[0, 360)`` degrees.
    """
    lightness, chroma, hue_radians = _oklab_to_oklch(L, a, b)
    hue_degrees = math.degrees(hue_radians) % 360.0
    return (lightness, chroma, hue_degrees)


def _oklch_degrees_to_oklab(
    L: float, C: float, h: float
) -> tuple[float, float, float]:
    """Convert degree-based OKLCH coordinates to OKLab.

    Parameters
    ----------
    L, C : float
        OKLCH lightness and chroma.
    h : float
        Hue in degrees.

    Returns
    -------
    tuple[float, float, float]
        ``(L, a, b)`` OKLab coordinates.
    """
    return _oklch_to_oklab(L, C, math.radians(h))


def _parse_hex(hex_str: str) -> tuple[float, float, float]:
    """
    Parse hex color string to RGB tuple.

    Parameters
    ----------
    hex_str : str
        Hex color string (#RGB or #RRGGBB).

    Returns
    -------
    tuple[float, float, float]
        (r, g, b) in range [0, 1].

    Raises
    ------
    ValueError
        If the hex string format is invalid.
    """
    # Strip a single leading '#'. Using ``lstrip('#')`` here would
    # silently accept ``##ff0000`` / ``###f00``; require exactly one.
    stripped: str = hex_str.strip()
    hex_clean: str = stripped[1:] if stripped.startswith("#") else stripped

    # Whitelist the alphabet so a stray sign (``#-10000``) or any
    # non-hex digit cannot slip through to ``int(..., 16)``.
    if not re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", hex_clean):
        raise ValueError(f"Invalid hex color format: {hex_str}")

    if len(hex_clean) == 3:
        # #RGB format
        r: float = int(hex_clean[0] * 2, 16) / 255.0
        g: float = int(hex_clean[1] * 2, 16) / 255.0
        b: float = int(hex_clean[2] * 2, 16) / 255.0
    else:
        # #RRGGBB format
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0

    return (r, g, b)


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """
    Convert RGB to hex string.

    Parameters
    ----------
    r, g, b : float
        RGB values in range [0, 1].

    Returns
    -------
    str
        Hex color string (#RRGGBB).
    """
    # Reject non-finite channels before clamping. ``max(0, min(1, nan))``
    # collapses NaN to 1.0 and would otherwise emit a bogus color
    # silently instead of surfacing the upstream computation error.
    if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
        raise ValueError(
            f"RGB channels must be finite, got (r={r}, g={g}, b={b})"
        )

    # Clamp to [0, 1]
    r_clamped: float = max(0.0, min(1.0, r))
    g_clamped: float = max(0.0, min(1.0, g))
    b_clamped: float = max(0.0, min(1.0, b))

    # Convert to 0-255 and format as hex
    r_int: int = round(r_clamped * 255)
    g_int: int = round(g_clamped * 255)
    b_int: int = round(b_clamped * 255)

    return f"#{r_int:02x}{g_int:02x}{b_int:02x}"
