"""Designed discrete forms for Model B color families."""

import math
from collections.abc import Sequence
from typing import NamedTuple

from . import _conversion, _curated, _generated
from ._families import DIVERGING, FAMILIES
from ._generated import CMAPS_256, MULTI_HUE_DISCRETE_INDICES

__all__ = ["DIVERGING_CANONICALS", "GENERATED_DIVERGING", "discrete_colors"]

GENERATED_DIVERGING: tuple[str, ...] = tuple(
    name for name in DIVERGING if name not in _curated.CURATED_DIVERGING_ORDER
)


def _generated_diverging_canonical(name: str) -> tuple[str, ...]:
    low, high = name.split("_", maxsplit=1)
    return tuple(_generated.PALETTE[low][i] for i in (7, 5, 3, 1)) + tuple(
        _generated.PALETTE[high][i] for i in (1, 3, 5, 7)
    )


DIVERGING_CANONICALS: dict[str, tuple[str, ...]] = {
    name: (
        tuple(_curated.CURATED[name])
        if name in _curated.CURATED_DIVERGING_ORDER
        else _generated_diverging_canonical(name)
    )
    for name in DIVERGING
}

_VIVID_CHROMA_FLOOR_RATIO = 0.6


class _VividCutoff(NamedTuple):
    cut_index: int
    dark_hi: bool
    peak_chroma: float
    cutoff_chroma: float
    threshold_chroma: float


def _family_name(name: str) -> str:
    return name[3:] if name.startswith("dc.") else name


def _max_n(name: str) -> int:
    family = FAMILIES[name]
    if family.kind == "sequential":
        return 10
    if family.kind == "diverging":
        return 9
    if family.kind == "multi-hue":
        return 8
    if family.kind == "cyclic":
        return 24
    return int(family.discrete_size or 0)


def _raise_bad_n(name: str, n: int) -> None:
    family = FAMILIES[name]
    raise ValueError(
        f"{name!r} is a {family.kind} family with max n={_max_n(name)}; "
        f"got n={n}"
    )


def _validate(name: str, n: int) -> None:
    if name not in FAMILIES:
        raise ValueError(f"unknown color family {name!r}")
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError(f"n must be an integer for {name!r}")
    if n < 1 or n > _max_n(name):
        _raise_bad_n(name, n)


def _sequential(name: str, n: int) -> list[str]:
    row = _generated.PALETTE[name]
    if n == 9:
        return list(row[:9])
    if n == 10:
        return list(row)
    if n == 1:
        return [row[5]]
    idx = [math.floor(1 + i * 7 / (n - 1) + 0.5) for i in range(n)]
    return [row[i] for i in idx]


def _diverging(name: str, n: int) -> list[str]:
    canonical = DIVERGING_CANONICALS[name]
    if n % 2 == 0:
        k = n // 2
        idx = list(range(k)) + list(range(8 - k, 8))
        return [canonical[i] for i in idx]

    k = (n - 1) // 2
    left = [canonical[i] for i in range(k)]
    right = [canonical[i] for i in range(8 - k, 8)]
    return [*left, _generated.CMAPS_256[name][128], *right]


def _chroma(hex_color: str) -> float:
    """Return canonical OKLCH chroma for one encoded sRGB hex color."""
    rgb = _conversion._parse_hex(hex_color)
    coordinates = _conversion._srgb_to_oklab(rgb)
    return _conversion._oklab_to_oklch_degrees(*coordinates)[1]


def _relative_y(hex_color: str) -> float:
    """Return modeled relative CIE Y calculated from nominal D65 sRGB."""
    return _conversion.relative_y_srgb_d65(_conversion._parse_hex(hex_color))


def _vivid_chroma_values(stops: Sequence[str]) -> tuple[float, ...]:
    return tuple(_chroma(hex_color) for hex_color in stops)


def _vivid_chroma_floor(chroma_values: Sequence[float]) -> float:
    if not chroma_values:
        raise ValueError("vivid cutoff needs at least one color stop")
    return _VIVID_CHROMA_FLOOR_RATIO * max(chroma_values)


def _vivid_cutoff(stops: Sequence[str]) -> _VividCutoff:
    """Return the dark-tail chroma cutoff for vivid sequential demos."""
    if not stops:
        raise ValueError("vivid cutoff needs at least one color stop")
    chroma_values = _vivid_chroma_values(stops)
    peak_i = max(range(len(chroma_values)), key=chroma_values.__getitem__)
    peak = chroma_values[peak_i]
    threshold = _vivid_chroma_floor(chroma_values)
    dark_hi = _relative_y(stops[-1]) < _relative_y(stops[0])
    index = peak_i
    if dark_hi:
        while (
            index + 1 <= len(chroma_values) - 1
            and chroma_values[index + 1] >= threshold
        ):
            index += 1
    else:
        while index - 1 >= 0 and chroma_values[index - 1] >= threshold:
            index -= 1
    dark_end = len(chroma_values) - 1 if dark_hi else 0
    if index == dark_end and len(chroma_values) > 1:
        index = index - 1 if dark_hi else index + 1
    return _VividCutoff(
        cut_index=index,
        dark_hi=dark_hi,
        peak_chroma=peak,
        cutoff_chroma=chroma_values[index],
        threshold_chroma=threshold,
    )


def _multi_hue(name: str, n: int) -> list[str]:
    row = CMAPS_256[name]
    return [row[index] for index in MULTI_HUE_DISCRETE_INDICES[name][n]]


def _cyclic(name: str, n: int) -> list[str]:
    row = _generated.CMAPS_256[name]
    return [row[min(int(i * len(row) / n), len(row) - 1)] for i in range(n)]


def _qualitative(name: str, n: int) -> list[str]:
    row = _generated.CYCLES.get(name, _curated.CURATED.get(name))
    if row is None:  # pragma: no cover - guarded by FAMILIES.
        raise ValueError(f"unknown qualitative family {name!r}")
    return list(row[:n])


def discrete_colors(name: str, n: int, *, reverse: bool = False) -> list[str]:
    """Return the designed discrete form for a Model B color family.

    Returned colors are hex strings. Discrete forms are deterministic and
    never produced by naive colormap resampling.
    """
    family_name = _family_name(name)
    _validate(family_name, n)
    family = FAMILIES[family_name]
    if family.kind == "sequential":
        colors = _sequential(family_name, n)
    elif family.kind == "diverging":
        colors = _diverging(family_name, n)
    elif family.kind == "multi-hue":
        colors = _multi_hue(family_name, n)
    elif family.kind == "cyclic":
        colors = _cyclic(family_name, n)
    else:
        colors = _qualitative(family_name, n)
    return list(reversed(colors)) if reverse else colors
