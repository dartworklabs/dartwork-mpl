"""WCAG relative-luminance helpers for validation checks."""

from __future__ import annotations

from collections.abc import Sequence


def _linearized(channel: float) -> float:
    """Convert an sRGB channel in 0..1 to linear light."""
    return (
        channel / 12.92
        if channel <= 0.03928
        else ((channel + 0.055) / 1.055) ** 2.4
    )


def _rel_lum(rgb: Sequence[float]) -> float:
    """Return WCAG relative luminance for an sRGB color."""
    r = _linearized(float(rgb[0]))
    g = _linearized(float(rgb[1]))
    b = _linearized(float(rgb[2]))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
