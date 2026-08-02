"""Validated NeutralTone values and deterministic modeled-relative-Y solvers."""

from __future__ import annotations

__all__ = [
    "SHIPPED_TONE_POLICY",
    "NeutralTone",
    "RelativeY",
    "SolvedColor",
    "TonePolicy",
    "max_chroma_at_tone",
    "neutral_tone",
    "relative_y",
    "relative_y_from_tone",
    "render_oklch_at_tone",
    "solve_oklch_l_for_relative_y",
    "tone_from_relative_y",
]

import math
from dataclasses import dataclass
from numbers import Real
from typing import NewType, TypeAlias

import numpy as np

from . import _conversion as conversion
from . import _gamut as gamut

Rgb: TypeAlias = tuple[float, float, float]
RelativeY = NewType("RelativeY", float)
NeutralTone = NewType("NeutralTone", float)


def _require_finite(name: str, value: object) -> float:
    """Return a value as a finite Python float.

    Parameters
    ----------
    name : str
        Value name for the error message.
    value : float
        Candidate value.

    Returns
    -------
    float
        Validated Python float.

    Raises
    ------
    TypeError
        If ``value`` is not a real number or is a boolean.
    ValueError
        If ``value`` is non-finite.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(
            f"{name} must be a real number, got {type(value).__name__}"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return numeric


def _bounded_unit(name: str, value: object) -> float:
    """Return a finite value inside the closed unit interval.

    Parameters
    ----------
    name : str
        Value name for the error message.
    value : float
        Candidate value.

    Returns
    -------
    float
        Validated Python float.

    Raises
    ------
    ValueError
        If ``value`` is outside ``[0, 1]`` or non-finite.
    """
    numeric = _require_finite(name, value)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return numeric


def _positive_finite(name: str, value: object) -> float:
    """Return a finite value greater than zero.

    Parameters
    ----------
    name : str
        Value name for the error message.
    value : float
        Candidate value.

    Returns
    -------
    float
        Validated Python float.

    Raises
    ------
    ValueError
        If ``value`` is not finite and positive.
    """
    numeric = _require_finite(name, value)
    if numeric <= 0.0:
        raise ValueError(f"{name} must be greater than zero, got {value!r}")
    return numeric


def _positive_iteration(name: str, value: int) -> None:
    """Validate one deterministic iteration count.

    Parameters
    ----------
    name : str
        Field name for the error message.
    value : int
        Candidate iteration count.

    Raises
    ------
    TypeError
        If ``value`` is not an integer or is a boolean.
    ValueError
        If ``value`` is not positive.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


@dataclass(frozen=True, slots=True)
class TonePolicy:
    """Configure modeled-relative-Y locking and maximum-chroma searches.

    Parameters
    ----------
    luminance_search_iterations : int
        Bisections used by the modeled-relative-Y lock solver.
    max_chroma_tone_iterations : int
        Independent target-Y probes used to locate actual OKLCH L.
    max_chroma_search_iterations : int
        Raw-gamut chroma probes at the located OKLCH L.
    probe_chroma : float
        Chroma used only by the independent target-Y probe.
    max_chroma_upper : float
        Upper endpoint of the raw-gamut chroma search.
    catalog_chroma_fraction : float
        Compiler-only fraction of the geometric boundary.
    """

    luminance_search_iterations: int
    max_chroma_tone_iterations: int
    max_chroma_search_iterations: int
    probe_chroma: float
    max_chroma_upper: float
    catalog_chroma_fraction: float

    def __post_init__(self) -> None:
        """Reject policies that cannot define deterministic searches."""
        _positive_iteration(
            "luminance_search_iterations", self.luminance_search_iterations
        )
        _positive_iteration(
            "max_chroma_tone_iterations", self.max_chroma_tone_iterations
        )
        _positive_iteration(
            "max_chroma_search_iterations", self.max_chroma_search_iterations
        )
        probe_chroma = _positive_finite("probe_chroma", self.probe_chroma)
        max_chroma = _positive_finite("max_chroma_upper", self.max_chroma_upper)
        if probe_chroma > max_chroma:
            raise ValueError("probe_chroma must not exceed max_chroma_upper")
        fraction = _require_finite(
            "catalog_chroma_fraction", self.catalog_chroma_fraction
        )
        if not 0.0 < fraction <= 1.0:
            raise ValueError("catalog_chroma_fraction must be in (0, 1]")
        object.__setattr__(self, "probe_chroma", probe_chroma)
        object.__setattr__(self, "max_chroma_upper", max_chroma)
        object.__setattr__(self, "catalog_chroma_fraction", fraction)


@dataclass(frozen=True, slots=True)
class SolvedColor:
    """Record one modeled-relative-Y-locked rendered color.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Encoded rendered sRGB channels.
    oklab_l : float
        Actual chromatic OKLab/OKLCH lightness used for rendering.
    mapped_chroma : float
        Chroma remaining after gamut mapping.
    achieved_y : RelativeY
        Modeled relative CIE Y calculated from nominal D65 sRGB.
    residual : float
        Signed ``achieved_y - target_y`` residual.
    """

    rgb: Rgb
    oklab_l: float
    mapped_chroma: float
    achieved_y: RelativeY
    residual: float


SHIPPED_TONE_POLICY = TonePolicy(
    luminance_search_iterations=40,
    max_chroma_tone_iterations=30,
    max_chroma_search_iterations=22,
    probe_chroma=0.04,
    max_chroma_upper=0.40,
    catalog_chroma_fraction=0.97,
)


def relative_y(value: float) -> RelativeY:
    """Construct a validated modeled relative-Y value.

    Parameters
    ----------
    value : float
        Candidate value in ``[0, 1]``.

    Returns
    -------
    RelativeY
        Validated modeled-relative-Y value.
    """
    return RelativeY(_bounded_unit("relative_y", value))


def neutral_tone(value: float) -> NeutralTone:
    """Construct a validated NeutralTone value.

    Parameters
    ----------
    value : float
        Candidate value in ``[0, 1]``.

    Returns
    -------
    NeutralTone
        Validated NeutralTone value.
    """
    return NeutralTone(_bounded_unit("neutral_tone", value))


def tone_from_relative_y(value: float) -> NeutralTone:
    """Convert modeled relative Y to NeutralTone with NumPy cube root.

    Parameters
    ----------
    value : float
        Modeled relative Y in ``[0, 1]``.

    Returns
    -------
    NeutralTone
        ``cbrt(relative_y)``.
    """
    validated = relative_y(value)
    return neutral_tone(float(np.cbrt(float(validated))))


def relative_y_from_tone(value: NeutralTone) -> RelativeY:
    """Convert NeutralTone to modeled relative Y by explicit cubing.

    Parameters
    ----------
    value : NeutralTone
        NeutralTone in ``[0, 1]``.

    Returns
    -------
    RelativeY
        ``tone ** 3``.
    """
    validated = neutral_tone(value)
    return relative_y(float(validated) ** 3)


def _validate_hue_chroma(hue_deg: float, chroma: float) -> tuple[float, float]:
    """Validate finite hue and non-negative chroma coordinates.

    Parameters
    ----------
    hue_deg : float
        Hue in degrees.
    chroma : float
        OKLCH chroma.

    Returns
    -------
    tuple[float, float]
        Validated ``(hue, chroma)`` Python floats.
    """
    valid_hue = _require_finite("hue_deg", hue_deg)
    valid_chroma = _require_finite("chroma", chroma)
    if valid_chroma < 0.0:
        raise ValueError(f"chroma must be non-negative, got {chroma!r}")
    return (valid_hue, valid_chroma)


def _solved_endpoint(target_y: RelativeY) -> SolvedColor | None:
    """Return exact black/white records for locked endpoint targets.

    Parameters
    ----------
    target_y : RelativeY
        Validated modeled-relative-Y target.

    Returns
    -------
    SolvedColor or None
        Exact endpoint record, or ``None`` for an interior target.
    """
    if target_y == 0.0:
        return SolvedColor(
            rgb=(0.0, 0.0, 0.0),
            oklab_l=0.0,
            mapped_chroma=0.0,
            achieved_y=RelativeY(0.0),
            residual=0.0,
        )
    if target_y == 1.0:
        return SolvedColor(
            rgb=(1.0, 1.0, 1.0),
            oklab_l=1.0,
            mapped_chroma=0.0,
            achieved_y=RelativeY(1.0),
            residual=0.0,
        )
    return None


def solve_oklch_l_for_relative_y(
    hue_deg: float,
    chroma: float,
    target_y: RelativeY,
    policy: TonePolicy = SHIPPED_TONE_POLICY,
) -> SolvedColor:
    """Solve actual OKLCH L for a mapped modeled-relative-Y target.

    Parameters
    ----------
    hue_deg : float
        Hue in degrees.
    chroma : float
        Requested OKLCH chroma.
    target_y : RelativeY
        Modeled relative CIE Y target in ``[0, 1]``.
    policy : TonePolicy, optional
        Fixed iteration policy.

    Returns
    -------
    SolvedColor
        Final midpoint mapping and its signed modeled-relative-Y residual.
    """
    valid_hue, valid_chroma = _validate_hue_chroma(hue_deg, chroma)
    valid_target = relative_y(target_y)
    endpoint = _solved_endpoint(valid_target)
    if endpoint is not None:
        return endpoint

    lower = 0.0
    upper = 1.0
    for _ in range(policy.luminance_search_iterations):
        midpoint = (lower + upper) / 2.0
        mapped = gamut.map_oklch_to_srgb(midpoint, valid_chroma, valid_hue)
        achieved = conversion.relative_y_srgb_d65(mapped.rgb)
        if achieved < valid_target:
            lower = midpoint
        else:
            upper = midpoint

    actual_l = (lower + upper) / 2.0
    mapped = gamut.map_oklch_to_srgb(actual_l, valid_chroma, valid_hue)
    achieved_y = relative_y(conversion.relative_y_srgb_d65(mapped.rgb))
    residual = float(achieved_y) - float(valid_target)
    return SolvedColor(
        rgb=mapped.rgb,
        oklab_l=actual_l,
        mapped_chroma=mapped.mapped_chroma,
        achieved_y=achieved_y,
        residual=residual,
    )


def render_oklch_at_tone(
    *,
    tone: float,
    chroma: float,
    hue: float,
    luminance_lock: bool,
    policy: TonePolicy = SHIPPED_TONE_POLICY,
) -> Rgb:
    """Render degree-based OKLCH at a NeutralTone output coordinate.

    Parameters
    ----------
    tone : float
        NeutralTone in ``[0, 1]``.
    chroma : float
        Requested OKLCH chroma.
    hue : float
        Hue in degrees.
    luminance_lock : bool
        If true, solve actual L for ``Y=tone**3``; otherwise use tone as L.
    policy : TonePolicy, optional
        Fixed solver policy.

    Returns
    -------
    tuple[float, float, float]
        Encoded and gamut-mapped sRGB channels.
    """
    valid_tone = neutral_tone(tone)
    valid_hue, valid_chroma = _validate_hue_chroma(hue, chroma)
    if luminance_lock:
        target_y = relative_y_from_tone(valid_tone)
        return solve_oklch_l_for_relative_y(
            valid_hue, valid_chroma, target_y, policy=policy
        ).rgb
    return gamut.map_oklch_to_srgb(
        float(valid_tone), valid_chroma, valid_hue
    ).rgb


def max_chroma_at_tone(
    hue_deg: float, tone: NeutralTone, policy: TonePolicy = SHIPPED_TONE_POLICY
) -> float:
    """Return the geometric raw-sRGB chroma boundary at NeutralTone.

    Parameters
    ----------
    hue_deg : float
        Hue in degrees.
    tone : NeutralTone
        NeutralTone in ``[0, 1]``.
    policy : TonePolicy, optional
        Independent 30-step tone-probe and 22-step chroma policy.

    Returns
    -------
    float
        Lower endpoint of the raw-gamut chroma search.

    Notes
    -----
    This intentionally does not call the 40-step locked solver. The catalog
    fraction belongs to compiler policy and is not applied to this boundary.
    """
    valid_hue = _require_finite("hue_deg", hue_deg)
    valid_tone = neutral_tone(tone)
    if valid_tone == 0.0 or valid_tone == 1.0:
        return 0.0

    target_y = relative_y_from_tone(valid_tone)
    lower_l = 0.0
    upper_l = 1.0
    for _ in range(policy.max_chroma_tone_iterations):
        midpoint_l = (lower_l + upper_l) / 2.0
        mapped = gamut.map_oklch_to_srgb(
            midpoint_l, policy.probe_chroma, valid_hue
        )
        achieved_y = conversion.relative_y_srgb_d65(mapped.rgb)
        if achieved_y < target_y:
            lower_l = midpoint_l
        else:
            upper_l = midpoint_l

    probed_l = (lower_l + upper_l) / 2.0
    lower_c = 0.0
    upper_c = policy.max_chroma_upper
    for _ in range(policy.max_chroma_search_iterations):
        midpoint_c = (lower_c + upper_c) / 2.0
        if gamut.oklch_in_srgb_gamut(probed_l, midpoint_c, valid_hue):
            lower_c = midpoint_c
        else:
            upper_c = midpoint_c
    return lower_c
