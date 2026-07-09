"""Contrast-aware ink helpers."""

from __future__ import annotations

__all__ = ["ensure_contrast", "readable_text_color"]

import colorsys
import math
from typing import Any

import matplotlib.colors as mcolors

from .._luminance import _contrast_ratio

_DEFAULT_LIGHT_INK = "white"
_DEFAULT_DARK_INK = "black"
_SEARCH_ITERS = 32


def _rgb(color: Any) -> tuple[float, float, float]:
    raw = mcolors.to_rgb(color)
    return (float(raw[0]), float(raw[1]), float(raw[2]))


def _contrast(foreground: Any, background: Any) -> float:
    return _contrast_ratio(_rgb(foreground), _rgb(background))


def _to_hex(rgb: tuple[float, float, float]) -> str:
    return mcolors.to_hex(rgb, keep_alpha=False)


def _hls_color(
    hue: float, lightness: float, saturation: float
) -> tuple[float, float, float]:
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (float(r), float(g), float(b))


def readable_text_color(
    background: Any,
    *,
    light: str | None = None,
    dark: str | None = None,
    threshold: float | None = None,
) -> str:
    """Choose the more readable text color for a background.

    Parameters
    ----------
    background : color-like
        Background color accepted by Matplotlib.
    light : str or None, optional
        Candidate light ink. ``None`` uses the library's standard light
        ink, ``"white"``. Default ``None``.
    dark : str or None, optional
        Candidate dark ink. ``None`` uses the standard dark text color
        inherited by the light style presets, ``"black"``. Default ``None``.
    threshold : float or None, optional
        Accepted for compatibility with threshold-based callers. Selection
        is always based on the higher WCAG contrast ratio. Default ``None``.

    Returns
    -------
    str
        The selected ink color string, either ``light`` or ``dark``.

    Examples
    --------
    >>> readable_text_color("#222222")
    'white'
    >>> readable_text_color("#f7f7f7")
    'black'
    """
    del threshold
    light_ink = _DEFAULT_LIGHT_INK if light is None else light
    dark_ink = _DEFAULT_DARK_INK if dark is None else dark
    background_rgb = _rgb(background)

    light_ratio = _contrast_ratio(_rgb(light_ink), background_rgb)
    dark_ratio = _contrast_ratio(_rgb(dark_ink), background_rgb)
    return light_ink if light_ratio >= dark_ratio else dark_ink


def ensure_contrast(
    color: Any, background: Any, *, min_ratio: float = 4.5
) -> str:
    """Adjust a color until it reaches a minimum contrast ratio.

    ``color`` is returned unchanged when it already meets ``min_ratio``.
    Otherwise the color's HLS lightness is moved toward the pole, black or
    white, that gives the stronger WCAG contrast against ``background``.
    Hue and saturation are held constant while a binary search finds the
    smallest deterministic lightness change that reaches the requested
    ratio, or the pole if the requested ratio is unreachable.

    Parameters
    ----------
    color : color-like
        Foreground color accepted by Matplotlib.
    background : color-like
        Background color accepted by Matplotlib.
    min_ratio : float, optional
        Minimum WCAG contrast ratio to satisfy. Default ``4.5``.

    Returns
    -------
    str
        ``color`` unchanged when it already passes and is a string;
        otherwise an adjusted ``"#rrggbb"`` color.

    Raises
    ------
    ValueError
        If ``min_ratio`` is not a positive finite number.

    Examples
    --------
    >>> ensure_contrast("#ddddaa", "white")
    '#7a7a31'
    >>> ensure_contrast("black", "white")
    'black'
    """
    if not math.isfinite(min_ratio) or min_ratio <= 0:
        raise ValueError("min_ratio must be a positive finite number")

    background_rgb = _rgb(background)
    color_rgb = _rgb(color)
    if _contrast_ratio(color_rgb, background_rgb) >= min_ratio:
        return color if isinstance(color, str) else _to_hex(color_rgb)

    hue, lightness, saturation = colorsys.rgb_to_hls(*color_rgb)
    black_ratio = _contrast_ratio((0.0, 0.0, 0.0), background_rgb)
    white_ratio = _contrast_ratio((1.0, 1.0, 1.0), background_rgb)
    lighten = white_ratio > black_ratio

    if lighten:
        lo = lightness
        hi = 1.0
        best = 1.0
        for _ in range(_SEARCH_ITERS):
            mid = (lo + hi) / 2.0
            candidate = _hls_color(hue, mid, saturation)
            if _contrast_ratio(candidate, background_rgb) >= min_ratio:
                best = mid
                hi = mid
            else:
                lo = mid
    else:
        lo = 0.0
        hi = lightness
        best = 0.0
        for _ in range(_SEARCH_ITERS):
            mid = (lo + hi) / 2.0
            candidate = _hls_color(hue, mid, saturation)
            if _contrast_ratio(candidate, background_rgb) >= min_ratio:
                best = mid
                lo = mid
            else:
                hi = mid

    adjusted = _hls_color(hue, best, saturation)
    adjusted_hex = _to_hex(adjusted)

    step = 1.0 / 255.0
    while _contrast(adjusted_hex, background_rgb) < min_ratio:
        if lighten:
            if best >= 1.0:
                break
            best = min(1.0, best + step)
        else:
            if best <= 0.0:
                break
            best = max(0.0, best - step)
        adjusted_hex = _to_hex(_hls_color(hue, best, saturation))

    return adjusted_hex
