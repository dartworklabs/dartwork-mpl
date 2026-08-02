"""GRAYSCALE_SAFETY: a bounded source-color proximity diagnostic."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sized
from itertools import combinations
from numbers import Real
from typing import TYPE_CHECKING, Any, TypedDict

import matplotlib.colors as mcolors

from .._types import Severity, VisualWarning
from ._luminance import _rel_lum
from ._registry import register_check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_grayscale_safety"]

_DELTA_Y = 0.10
# Deprecated compatibility alias. ``delta_l`` has always meant the rounded
# WCAG contrast-luminance helper here; keep that meaning for existing clients.
_DELTA_L = 0.10
_MAX_COLLISIONS = 6

_RGBA = tuple[float, float, float, float]
_RGB = tuple[float, float, float]


class _Collision(TypedDict):
    colors: tuple[str, str]
    relative_y: tuple[float, float]
    delta_y: float
    delta_e_ok: float
    delta_l: float


def _rgba(color: Any) -> _RGBA | None:
    try:
        raw = mcolors.to_rgba(color)
    except (TypeError, ValueError):
        return None
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _add_color(
    colors: dict[str, _RGB], color: object, artist_alpha: float | None = None
) -> None:
    """Collect one visible source RGB without modeling compositing."""
    rgba = _rgba(color)
    if rgba is None or rgba[3] == 0 or artist_alpha == 0:
        return
    hex_color = mcolors.to_hex(rgba, keep_alpha=False)
    colors.setdefault(hex_color, (rgba[0], rgba[1], rgba[2]))


def _looks_like_rgba(value: object) -> bool:
    if isinstance(value, str) or not isinstance(value, Iterable):
        return False
    parts = list(value)
    return len(parts) == 4 and all(isinstance(part, Real) for part in parts)


def _facecolor_rows(facecolors: object) -> Iterator[object]:
    if (
        facecolors is None
        or not isinstance(facecolors, Iterable)
        or not isinstance(facecolors, Sized)
        or len(facecolors) == 0
    ):
        return
    if _looks_like_rgba(facecolors):
        yield facecolors
        return
    yield from facecolors


@register_check("GRAYSCALE_SAFETY", order=82)
def check_grayscale_safety(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Report source colors close under the project's modeled-Y heuristic.

    Colors are compared within each Axes, not across the figure. Two series
    only collapse into each other where a reader compares them, and separate
    panels are read separately: a price panel's moving average and a multiple
    panel's series can sit at the same luminance without either becoming
    harder to identify. Pooling the whole figure reported those pairs on every
    multi-panel chart, which is noise that trains the warning away.
    """
    # Resolve the canonical color kernel lazily.  A module-level import would
    # reintroduce the cold-import cycle through ``validate`` and ``_colors``.
    from ..._colors._conversion import _srgb_to_oklab, relative_y_srgb_d65

    collisions: list[_Collision] = []
    seen: set[tuple[str, str]] = set()

    for ax in fig.axes:
        colors: dict[str, _RGB] = {}

        for line in ax.lines:
            if line.get_visible():
                _add_color(colors, line.get_color(), line.get_alpha())

        for patch in ax.patches:
            if patch.get_visible():
                _add_color(colors, patch.get_facecolor(), patch.get_alpha())

        for collection in ax.collections:
            if not collection.get_visible():
                continue
            for facecolor in _facecolor_rows(collection.get_facecolor()):
                _add_color(colors, facecolor, collection.get_alpha())

        if len(colors) < 2:
            continue

        relative_y = {
            hex_color: relative_y_srgb_d65(rgb)
            for hex_color, rgb in colors.items()
        }
        oklab = {
            hex_color: _srgb_to_oklab(rgb) for hex_color, rgb in colors.items()
        }
        # Deprecated compatibility value: keep using WCAG coefficients rather
        # than silently reinterpreting the public ``delta_l`` detail key.
        wcag_luminance = {
            hex_color: _rel_lum(rgb) for hex_color, rgb in colors.items()
        }
        for first, second in combinations(colors.keys(), 2):
            delta_y = abs(relative_y[first] - relative_y[second])
            if delta_y >= _DELTA_Y:
                continue
            pair = (first, second) if first <= second else (second, first)
            if pair in seen:
                # The same clash repeated across panels is one problem to fix.
                continue
            seen.add(pair)
            collisions.append(
                {
                    "colors": (first, second),
                    "relative_y": (
                        round(relative_y[first], 3),
                        round(relative_y[second], 3),
                    ),
                    "delta_y": round(delta_y, 3),
                    "delta_e_ok": round(
                        100.0 * math.dist(oklab[first], oklab[second]), 3
                    ),
                    "delta_l": round(
                        abs(wcag_luminance[first] - wcag_luminance[second]), 3
                    ),
                }
            )

    if not collisions:
        return []

    shown = collisions[:_MAX_COLLISIONS]
    pair_bits = [
        f"{collision['colors'][0]}/{collision['colors'][1]}"
        for collision in shown
    ]
    pair_text = ", ".join(pair_bits)
    omitted = max(0, len(collisions) - len(shown))
    if omitted:
        pair_text = f"{pair_text} (+{omitted} more)"

    return [
        VisualWarning(
            severity=Severity.INFO,
            check_id="GRAYSCALE_SAFETY",
            message=(
                "The project modeled-relative-Y proximity heuristic before "
                "compositing found source-RGB pairs below its ΔY threshold; "
                f"inspect ΔEOK separation: {pair_text}"
            ),
            detail={
                "delta_y_threshold": _DELTA_Y,
                # Deprecated WCAG compatibility alias; do not reinterpret.
                "delta_l_threshold": _DELTA_L,
                "metric_model": "project_modeled_relative_y_srgb_d65",
                "alpha_policy": (
                    "ignore_zero_alpha_compare_positive_alpha_source_rgb_"
                    "before_compositing"
                ),
                "pairs": shown,
                "count": len(collisions),
                "omitted": omitted,
            },
        )
    ]
