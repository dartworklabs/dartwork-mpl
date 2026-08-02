"""Operational OKLab/OKLCH recipe loaded from the packaged v6 authority.

The JSON asset is the sole recipe literal authority.  This module exposes
typed immutable values and the established Fourier-based family extension
mechanism without performing historical coordinate migration at runtime.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from ._ssot import load_color_v6_ssot
from ._tone import NeutralTone, neutral_tone

__all__ = [
    "FAMILIES",
    "FAMILY_PARAMS",
    "FOURIER",
    "GAMUT_CHROMA_FRAC",
    "GRAY_C_PROFILE",
    "GRAY_TINT_HUE",
    "GRAY_TONE_FLOOR",
    "SHAPE_Q",
    "SHAPE_R",
    "TONE_DERIVATION_GRID",
    "TONE_TOP",
    "FamilyParams",
    "derive_family",
    "fourier_eval",
    "mid_hue",
]


@dataclass(frozen=True, slots=True)
class FamilyParams:
    """Define one OKLCH color-family construction recipe.

    Parameters
    ----------
    h0 : float
        Starting OKLCH hue in degrees.
    dh : float
        Total hue drift in degrees.
    gamma : float
        Hue-drift timing exponent.
    tp : float
        Chroma-profile peak position.
    cmax : float
        Peak chroma.
    tone_floor : NeutralTone
        Dark endpoint as cube root of modeled relative CIE Y.
    cend : float
        Dark-end retained-chroma fraction.
    c0 : float
        Pastel-start chroma fraction.
    """

    h0: float
    dh: float
    gamma: float
    tp: float
    cmax: float
    tone_floor: NeutralTone
    cend: float
    c0: float


def _mapping(value: object, label: str) -> Mapping[str, object]:
    """Narrow a validated SSOT value to a string-keyed mapping."""
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a mapping")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    """Narrow a validated SSOT value to a non-string sequence."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise RuntimeError(f"{label} must be a sequence")
    return cast(Sequence[object], value)


def _number(value: object, label: str) -> float:
    """Read one already-validated numeric SSOT leaf as ``float``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{label} must be numeric")
    return float(value)


def _family_params(value: object) -> FamilyParams:
    """Construct one typed family row from validated packaged data."""
    row = _mapping(value, "family params")
    return FamilyParams(
        h0=_number(row["h0"], "h0"),
        dh=_number(row["dh"], "dh"),
        gamma=_number(row["gamma"], "gamma"),
        tp=_number(row["tp"], "tp"),
        cmax=_number(row["cmax"], "cmax"),
        tone_floor=neutral_tone(_number(row["tone_floor"], "tone_floor")),
        cend=_number(row["cend"], "cend"),
        c0=_number(row["c0"], "c0"),
    )


_SSOT = load_color_v6_ssot()
_RECIPE = _mapping(_SSOT["recipe"], "recipe")
_FAMILY_ROWS = _mapping(_RECIPE["family_params"], "family params")
FAMILIES: tuple[str, ...] = tuple(
    cast(Sequence[str], _sequence(_RECIPE["family_order"], "family order"))
)
FAMILY_PARAMS: Mapping[str, FamilyParams] = MappingProxyType(
    {name: _family_params(_FAMILY_ROWS[name]) for name in FAMILIES}
)

_FOURIER_ROWS = _mapping(_RECIPE["fourier"], "Fourier curves")
FOURIER: Mapping[str, tuple[float, ...]] = MappingProxyType(
    {
        name: tuple(
            _number(coefficient, f"{name} coefficient")
            for coefficient in _sequence(values, name)
        )
        for name, values in _FOURIER_ROWS.items()
    }
)

_CONSTANTS = _mapping(_RECIPE["constants"], "recipe constants")
TONE_TOP = neutral_tone(_number(_CONSTANTS["TONE_TOP"], "TONE_TOP"))
SHAPE_Q = _number(_CONSTANTS["SHAPE_Q"], "SHAPE_Q")
SHAPE_R = _number(_CONSTANTS["SHAPE_R"], "SHAPE_R")
GAMUT_CHROMA_FRAC = _number(
    _CONSTANTS["GAMUT_CHROMA_FRAC"], "GAMUT_CHROMA_FRAC"
)
GRAY_TONE_FLOOR = neutral_tone(
    _number(_CONSTANTS["GRAY_TONE_FLOOR"], "GRAY_TONE_FLOOR")
)
GRAY_TINT_HUE = _number(_CONSTANTS["GRAY_TINT_HUE"], "GRAY_TINT_HUE")
GRAY_C_PROFILE: tuple[float, ...] = tuple(
    _number(value, "gray chroma")
    for value in _sequence(_CONSTANTS["GRAY_C_PROFILE"], "GRAY_C_PROFILE")
)
TONE_DERIVATION_GRID = _number(
    _CONSTANTS["TONE_DERIVATION_GRID"], "TONE_DERIVATION_GRID"
)


def fourier_eval(coef: tuple[float, ...], h_deg: float) -> float:
    """Evaluate a cosine/sine-interleaved Fourier coefficient row."""
    hue = math.radians(h_deg)
    harmonic_count = (len(coef) - 1) // 2
    value = coef[0]
    for harmonic in range(1, harmonic_count + 1):
        value += coef[2 * harmonic - 1] * math.cos(harmonic * hue) + coef[
            2 * harmonic
        ] * math.sin(harmonic * hue)
    return float(value)


def mid_hue(params: FamilyParams) -> float:
    """Return the recipe hue at the family midpoint."""
    return float((params.h0 + params.dh * 0.5**params.gamma) % 360)


def _chroma_grid(value: float, grid: float) -> float:
    """Round a chroma/profile value on its established decimal grid."""
    return round(round(value / grid) * grid, 10)


def _tone_grid(value: float) -> NeutralTone:
    """Round a derived tone on the full-double migrated unit grid."""
    steps = round(value / TONE_DERIVATION_GRID)
    denominator = 1.0 / TONE_DERIVATION_GRID
    return neutral_tone(steps / denominator)


def derive_family(
    h0: float, dh: float, gamma: float, tp: float
) -> FamilyParams:
    """Derive an extension family from the packaged Fourier curves."""
    hue_midpoint = (h0 + dh * 0.5**gamma) % 360
    return FamilyParams(
        h0=h0,
        dh=dh,
        gamma=gamma,
        tp=tp,
        cmax=_chroma_grid(
            fourier_eval(FOURIER["cmax_k3"], hue_midpoint), 0.005
        ),
        tone_floor=_tone_grid(
            fourier_eval(FOURIER["tone_floor_k3"], hue_midpoint)
        ),
        cend=_chroma_grid(fourier_eval(FOURIER["cend_k2"], hue_midpoint), 0.05),
        c0=_chroma_grid(fourier_eval(FOURIER["c0_k2"], hue_midpoint), 0.05),
    )
