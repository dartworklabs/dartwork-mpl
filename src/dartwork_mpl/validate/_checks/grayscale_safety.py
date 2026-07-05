"""GRAYSCALE_SAFETY: near-identical luminance in data colors."""

from __future__ import annotations

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

_DELTA_L = 0.10
_MAX_COLLISIONS = 6

_RGBA = tuple[float, float, float, float]
_RGB = tuple[float, float, float]


class _Collision(TypedDict):
    colors: tuple[str, str]
    delta_l: float


def _rgba(color: Any) -> _RGBA | None:
    try:
        raw = mcolors.to_rgba(color)
    except (TypeError, ValueError):
        return None
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _add_color(colors: dict[str, _RGB], color: object) -> None:
    rgba = _rgba(color)
    if rgba is None or rgba[3] == 0:
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
    """Detect data colors that collapse together in grayscale."""
    colors: dict[str, _RGB] = {}

    for ax in fig.axes:
        for line in ax.lines:
            if line.get_visible():
                _add_color(colors, line.get_color())

        for patch in ax.patches:
            if patch.get_visible():
                _add_color(colors, patch.get_facecolor())

        for collection in ax.collections:
            if not collection.get_visible():
                continue
            for facecolor in _facecolor_rows(collection.get_facecolor()):
                _add_color(colors, facecolor)

    if len(colors) < 2:
        return []

    collisions: list[_Collision] = []
    luminance = {hex_color: _rel_lum(rgb) for hex_color, rgb in colors.items()}
    for first, second in combinations(colors.keys(), 2):
        delta = abs(luminance[first] - luminance[second])
        if delta < _DELTA_L:
            collisions.append(
                {"colors": (first, second), "delta_l": round(delta, 3)}
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
                "Data colors have near-identical grayscale luminance: "
                f"{pair_text}"
            ),
            detail={
                "delta_l_threshold": _DELTA_L,
                "pairs": shown,
                "count": len(collisions),
                "omitted": omitted,
            },
        )
    ]
