"""Operational OKLab/OKLCH recipe loaded from the packaged v6 authority.

The JSON asset is the sole recipe literal authority.  This module exposes
typed immutable values and the established Fourier-based family extension
mechanism without performing historical coordinate migration at runtime.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .._ssot import RecipeFamily, load_color_v6_ssot
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


def _family_params(row: RecipeFamily) -> FamilyParams:
    """Construct one typed family row from the parsed authority."""
    return FamilyParams(
        h0=row.h0,
        dh=row.dh,
        gamma=row.gamma,
        tp=row.tp,
        cmax=row.cmax,
        tone_floor=neutral_tone(row.tone_floor),
        cend=row.cend,
        c0=row.c0,
    )


_RECIPE = load_color_v6_ssot().recipe
FAMILIES: tuple[str, ...] = _RECIPE.family_order
FAMILY_PARAMS: Mapping[str, FamilyParams] = MappingProxyType(
    {name: _family_params(_RECIPE.family_params[name]) for name in FAMILIES}
)
FOURIER: Mapping[str, tuple[float, ...]] = _RECIPE.fourier

_CONSTANTS = _RECIPE.constants
TONE_TOP = neutral_tone(_CONSTANTS.tone_top)
SHAPE_Q = _CONSTANTS.shape_q
SHAPE_R = _CONSTANTS.shape_r
GAMUT_CHROMA_FRAC = _CONSTANTS.gamut_chroma_frac
GRAY_TONE_FLOOR = neutral_tone(_CONSTANTS.gray_tone_floor)
GRAY_TINT_HUE = _CONSTANTS.gray_tint_hue
GRAY_C_PROFILE: tuple[float, ...] = _CONSTANTS.gray_c_profile
TONE_DERIVATION_GRID = _CONSTANTS.tone_derivation_grid


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
