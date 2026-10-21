"""Deterministic sRGB gamut checks and fixed-L/h OKLCH mapping."""

from __future__ import annotations

__all__ = [
    "SRGB_GAMUT_POLICY",
    "GamutPolicy",
    "MappedColor",
    "linear_srgb_in_gamut",
    "map_oklch_to_srgb",
    "max_chroma_at_lightness",
    "oklch_in_srgb_gamut",
]

import math
from dataclasses import dataclass
from numbers import Real
from typing import TypeAlias

from . import _conversion as conversion

Rgb: TypeAlias = tuple[float, float, float]
LinearRgb: TypeAlias = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class GamutPolicy:
    """Configure deterministic OKLCH chroma-boundary searches.

    Parameters
    ----------
    iterations : int
        Number of bisection probes.
    tolerance : float
        Inclusive tolerance around the raw linear-sRGB ``[0, 1]`` bounds.
    max_chroma_upper : float
        Upper endpoint used only by geometric maximum-chroma searches.
    """

    iterations: int
    tolerance: float
    max_chroma_upper: float

    def __post_init__(self) -> None:
        """Reject policies that cannot define a finite search."""
        if isinstance(self.iterations, bool) or not isinstance(
            self.iterations, int
        ):
            raise TypeError("iterations must be an integer")
        if self.iterations <= 0:
            raise ValueError("iterations must be greater than zero")
        tolerance = _require_nonnegative_finite("tolerance", self.tolerance)
        max_chroma_upper = _require_positive_finite(
            "max_chroma_upper", self.max_chroma_upper
        )
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "max_chroma_upper", max_chroma_upper)


@dataclass(frozen=True, slots=True)
class MappedColor:
    """Describe one rendered OKLCH request and its gamut adjustment.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Encoded sRGB channels after final linear clamp.
    oklab_l : float
        Requested OKLab/OKLCH lightness.
    mapped_chroma : float
        Rendered chroma after any boundary search.
    hue_deg : float
        Requested hue in degrees.
    was_mapped : bool
        Whether the raw requested coordinate was outside the policy gamut.
    """

    rgb: Rgb
    oklab_l: float
    mapped_chroma: float
    hue_deg: float
    was_mapped: bool


def _require_finite(name: str, value: object) -> float:
    """Return a coordinate as a finite Python float.

    Parameters
    ----------
    name : str
        Coordinate name for the error message.
    value : float
        Candidate coordinate.

    Returns
    -------
    float
        Validated Python float.

    Raises
    ------
    TypeError
        If ``value`` is not a real number or is a boolean.
    ValueError
        If ``value`` is not finite.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(
            f"{name} must be a real number, got {type(value).__name__}"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return numeric


def _require_nonnegative_finite(name: str, value: object) -> float:
    """Return a finite non-negative Python float.

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
        If ``value`` is non-finite or negative.
    """
    numeric = _require_finite(name, value)
    if numeric < 0.0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return numeric


def _require_positive_finite(name: str, value: object) -> float:
    """Return a finite positive Python float.

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
        If ``value`` is non-finite or not positive.
    """
    numeric = _require_finite(name, value)
    if numeric <= 0.0:
        raise ValueError(f"{name} must be greater than zero, got {value!r}")
    return numeric


SRGB_GAMUT_POLICY = GamutPolicy(
    iterations=24, tolerance=1e-6, max_chroma_upper=0.40
)


def _validate_oklch(
    lightness: float, chroma: float, hue_deg: float
) -> tuple[float, float, float]:
    """Validate an OKLCH coordinate without restricting finite lightness.

    Parameters
    ----------
    lightness, chroma, hue_deg : float
        Requested degree-based OKLCH coordinate.

    Returns
    -------
    tuple[float, float, float]
        Validated Python floats.
    """
    valid_lightness = _require_finite("lightness", lightness)
    valid_chroma = _require_nonnegative_finite("chroma", chroma)
    valid_hue = _require_finite("hue_deg", hue_deg)
    return (valid_lightness, valid_chroma, valid_hue)


def linear_srgb_in_gamut(
    rgb: LinearRgb, *, tolerance: float = SRGB_GAMUT_POLICY.tolerance
) -> bool:
    """Return whether raw linear-sRGB channels meet inclusive bounds.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Raw linear-sRGB channels.
    tolerance : float, optional
        Inclusive numerical tolerance around ``[0, 1]``.

    Returns
    -------
    bool
        ``True`` when every channel is within ``[-tolerance, 1+tolerance]``.

    Raises
    ------
    TypeError
        If ``tolerance`` is not a real number or is a boolean.
    ValueError
        If ``tolerance`` is negative or non-finite.
    """
    valid_tolerance = _require_nonnegative_finite("tolerance", tolerance)
    return all(
        -valid_tolerance <= float(channel) <= 1.0 + valid_tolerance
        for channel in rgb
    )


def _linear_srgb_at_oklch(
    lightness: float, chroma: float, hue_deg: float
) -> LinearRgb:
    """Return raw linear sRGB for one degree-based OKLCH coordinate.

    Parameters
    ----------
    lightness, chroma, hue_deg : float
        Degree-based OKLCH coordinate.

    Returns
    -------
    tuple[float, float, float]
        Unclamped linear-sRGB channels.
    """
    oklab = conversion._oklch_degrees_to_oklab(lightness, chroma, hue_deg)
    return conversion._oklab_to_linear_srgb(*oklab)


def _encoded_srgb_from_linear(rgb: LinearRgb) -> Rgb:
    """Clamp linear channels and encode them as canonical Python floats.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Raw linear-sRGB channels.

    Returns
    -------
    tuple[float, float, float]
        Encoded, bounded sRGB channels.
    """
    red = float(conversion._linear_to_srgb(max(0.0, min(1.0, rgb[0]))))
    green = float(conversion._linear_to_srgb(max(0.0, min(1.0, rgb[1]))))
    blue = float(conversion._linear_to_srgb(max(0.0, min(1.0, rgb[2]))))
    return (red, green, blue)


def oklch_in_srgb_gamut(
    lightness: float,
    chroma: float,
    hue_deg: float,
    *,
    tolerance: float = SRGB_GAMUT_POLICY.tolerance,
) -> bool:
    """Return whether a degree-based OKLCH coordinate is raw-sRGB-safe.

    Parameters
    ----------
    lightness, chroma, hue_deg : float
        Degree-based OKLCH coordinate.
    tolerance : float, optional
        Inclusive raw linear-sRGB boundary tolerance.

    Returns
    -------
    bool
        Whether the unmodified coordinate lies in the tolerated gamut.
    """
    valid_l, valid_c, valid_h = _validate_oklch(lightness, chroma, hue_deg)
    return linear_srgb_in_gamut(
        _linear_srgb_at_oklch(valid_l, valid_c, valid_h), tolerance=tolerance
    )


def map_oklch_to_srgb(
    lightness: float,
    chroma: float,
    hue_deg: float,
    policy: GamutPolicy = SRGB_GAMUT_POLICY,
) -> MappedColor:
    """Map degree-based OKLCH to sRGB by reducing only chroma.

    Parameters
    ----------
    lightness, chroma, hue_deg : float
        Requested OKLCH coordinate. Finite lightness outside ``[0, 1]`` is
        accepted and clipped only during the final linear-RGB render.
    policy : GamutPolicy, optional
        Deterministic search and tolerance policy.

    Returns
    -------
    MappedColor
        Encoded RGB plus the preserved L/h and rendered chroma.
    """
    valid_l, valid_c, valid_h = _validate_oklch(lightness, chroma, hue_deg)
    linear_rgb = _linear_srgb_at_oklch(valid_l, valid_c, valid_h)
    if linear_srgb_in_gamut(linear_rgb, tolerance=policy.tolerance):
        return MappedColor(
            rgb=_encoded_srgb_from_linear(linear_rgb),
            oklab_l=valid_l,
            mapped_chroma=valid_c,
            hue_deg=valid_h,
            was_mapped=False,
        )

    lower = 0.0
    upper = valid_c
    for _ in range(policy.iterations):
        midpoint = (lower + upper) / 2.0
        probe = _linear_srgb_at_oklch(valid_l, midpoint, valid_h)
        if linear_srgb_in_gamut(probe, tolerance=policy.tolerance):
            lower = midpoint
        else:
            upper = midpoint

    rendered = _linear_srgb_at_oklch(valid_l, lower, valid_h)
    return MappedColor(
        rgb=_encoded_srgb_from_linear(rendered),
        oklab_l=valid_l,
        mapped_chroma=lower,
        hue_deg=valid_h,
        was_mapped=True,
    )


def _map_oklab_to_srgb(
    lightness: float,
    a: float,
    b: float,
    policy: GamutPolicy = SRGB_GAMUT_POLICY,
) -> Rgb:
    """Map a stored OKLab coordinate without a degree round trip.

    Parameters
    ----------
    lightness, a, b : float
        Stored OKLab coordinates.
    policy : GamutPolicy, optional
        Deterministic gamut policy.

    Returns
    -------
    tuple[float, float, float]
        Encoded and bounded sRGB channels.

    Notes
    -----
    This path intentionally retains the source OKLab-derived radian hue and
    chroma. It preserves the historical ``Color.to_rgb`` arithmetic, while
    :func:`map_oklch_to_srgb` operates directly on requested degree values.
    """
    linear_rgb = conversion._oklab_to_linear_srgb(lightness, a, b)
    if linear_srgb_in_gamut(linear_rgb, tolerance=policy.tolerance):
        return _encoded_srgb_from_linear(linear_rgb)

    valid_l, chroma, hue_radians = conversion._oklab_to_oklch(lightness, a, b)
    lower = 0.0
    upper = chroma
    for _ in range(policy.iterations):
        midpoint = (lower + upper) / 2.0
        _, probe_a, probe_b = conversion._oklch_to_oklab(
            valid_l, midpoint, hue_radians
        )
        probe = conversion._oklab_to_linear_srgb(valid_l, probe_a, probe_b)
        if linear_srgb_in_gamut(probe, tolerance=policy.tolerance):
            lower = midpoint
        else:
            upper = midpoint

    _, mapped_a, mapped_b = conversion._oklch_to_oklab(
        valid_l, lower, hue_radians
    )
    rendered = conversion._oklab_to_linear_srgb(valid_l, mapped_a, mapped_b)
    return _encoded_srgb_from_linear(rendered)


def max_chroma_at_lightness(
    lightness: float, hue_deg: float, policy: GamutPolicy = SRGB_GAMUT_POLICY
) -> float:
    """Return the raw-sRGB chroma boundary at actual OKLCH lightness.

    Parameters
    ----------
    lightness : float
        Actual chromatic OKLCH lightness.
    hue_deg : float
        Hue in degrees.
    policy : GamutPolicy, optional
        Policy whose explicit ``max_chroma_upper`` bounds the search.

    Returns
    -------
    float
        Largest probed in-gamut chroma, returning the lower endpoint.
    """
    valid_l = _require_finite("lightness", lightness)
    valid_h = _require_finite("hue_deg", hue_deg)
    lower = 0.0
    upper = policy.max_chroma_upper
    for _ in range(policy.iterations):
        midpoint = (lower + upper) / 2.0
        if oklch_in_srgb_gamut(
            valid_l, midpoint, valid_h, tolerance=policy.tolerance
        ):
            lower = midpoint
        else:
            upper = midpoint
    return lower
