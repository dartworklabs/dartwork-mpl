"""Independent standard-library oracle for color compatibility validation.

This module deliberately does not import the candidate color compiler.  It
exists so an implementation cannot validate itself with the same conversion
or metric code that produced its output.
"""

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TypeAlias, cast

Rgb: TypeAlias = tuple[float, float, float]
Lab: TypeAlias = tuple[float, float, float]
JsonObject: TypeAlias = dict[str, object]
Matrix3: TypeAlias = tuple[Rgb, Rgb, Rgb]

QUALITY_SCHEMA = "dartwork-mpl.color-quality/v2"
ACCEPTED_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
ACCEPTED_COMPATIBILITY_PATH = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_compatibility.json"
)
ACCEPTED_COMPATIBILITY_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
ACCEPTED_ORACLE_PATH = "src/dartwork_mpl/_colors/_compatibility_metrics.py"
SHARMA_SOURCE_SHA256 = (
    "44aebb39107128328add54fbef5ac8ee89909e50508f448a1580adea2058a4b8"
)
MACHADO_PROVENANCE_SHA256 = (
    "379c549025f91ac05a611631114ff8202fa2d802bc29e15f79479c7985373346"
)
BVM_ADAPTATION_COMMIT = "1a01fc1bf8d8dd419af8343b80b05e98ba50a75d"
BVM_ADAPTATION_SOURCE_SHA256 = (
    "6503e903876280e66e3fbaae983c0f647da502d1c555ac200e32cb04e2905999"
)
BVM_PAPER_SHA256 = (
    "09f9d742d363a18b9ff1ea090cccebe090b1605da92fdac0fc9b48472285f1ba"
)

_LEGACY_D65_Y = (0.2126729, 0.7151522, 0.0721750)
_D65_Y = (0.21267287873271212, 0.7151521284847872, 0.07217499278250072)
_WCAG_Y = (0.2126, 0.7152, 0.0722)
_RGB_TO_XYZ: Matrix3 = (
    (0.4124564, 0.3575761, 0.1804375),
    _LEGACY_D65_Y,
    (0.0193339, 0.1191920, 0.9503041),
)
_D65_WHITE = (0.95047, 1.0, 1.08883)

_MACHADO: dict[str, Matrix3] = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}
_BVM_TRITAN_SEPARATION = (0.03901, -0.02788, -0.01113)
_BVM_TRITAN_HIGH: Matrix3 = (
    (1.01277, 0.13548, -0.14826),
    (-0.01243, 0.86812, 0.14431),
    (0.07589, 0.80500, 0.11911),
)
_BVM_TRITAN_LOW: Matrix3 = (
    (0.93678, 0.18979, -0.12657),
    (0.06154, 0.81526, 0.12320),
    (-0.37562, 1.12767, 0.24796),
)

_SHARMA_VECTORS: tuple[tuple[Lab, Lab, float], ...] = (
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
)


class OracleValidationError(ValueError):
    """Raised when an oracle input or pinned reference is invalid."""


@dataclass(frozen=True, slots=True)
class NumericSummary:
    """Deterministic summary using Type-7 percentile interpolation.

    Parameters
    ----------
    min, p05, p50, p95, max, mean : float
        Finite raw values.  No display rounding is applied.
    """

    min: float
    p05: float
    p50: float
    p95: float
    max: float
    mean: float

    def __post_init__(self) -> None:
        """Reject non-finite or internally inconsistent direct construction."""
        values = (self.min, self.p05, self.p50, self.p95, self.max, self.mean)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise OracleValidationError(
                "numeric summary fields must be finite numbers"
            )
        if not self.min <= self.p05 <= self.p50 <= self.p95 <= self.max:
            raise OracleValidationError(
                "numeric summary percentiles must be ordered"
            )
        if not self.min <= self.mean <= self.max:
            raise OracleValidationError(
                "numeric summary mean must lie within its range"
            )

    def to_json_value(self) -> dict[str, float]:
        """Return a JSON-safe literal mapping.

        Returns
        -------
        dict[str, float]
            Summary fields in stable semantic order.
        """
        return {
            "min": self.min,
            "p05": self.p05,
            "p50": self.p50,
            "p95": self.p95,
            "max": self.max,
            "mean": self.mean,
        }


def _finite_float(value: object, *, label: str) -> float:
    """Validate and return one finite non-boolean float."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise OracleValidationError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise OracleValidationError(f"{label} must be finite")
    return result


def _validate_rgb(rgb: object, *, unit_range: bool = True) -> Rgb:
    """Validate a three-channel RGB-like sequence."""
    if isinstance(rgb, str) or not isinstance(rgb, Sequence) or len(rgb) != 3:
        raise OracleValidationError("RGB must contain exactly three channels")
    channels = tuple(
        _finite_float(channel, label=f"RGB channel {index}")
        for index, channel in enumerate(rgb)
    )
    if unit_range and any(
        channel < 0.0 or channel > 1.0 for channel in channels
    ):
        raise OracleValidationError("sRGB channels must be in [0, 1]")
    return cast(Rgb, channels)


def _validate_lab(lab: object, *, label: str) -> Lab:
    """Validate a three-coordinate Lab-like sequence."""
    if isinstance(lab, str) or not isinstance(lab, Sequence) or len(lab) != 3:
        raise OracleValidationError(f"{label} must contain three coordinates")
    return cast(
        Lab,
        tuple(
            _finite_float(item, label=f"{label} coordinate {index}")
            for index, item in enumerate(lab)
        ),
    )


def hex_to_srgb(color: str) -> Rgb:
    """Parse a strict lower- or upper-case ``#RRGGBB`` color.

    Parameters
    ----------
    color : str
        Exactly seven characters including the leading hash.

    Returns
    -------
    tuple[float, float, float]
        Gamma-encoded channels in ``[0, 1]``.
    """
    if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
        raise OracleValidationError("hex colors must have form #RRGGBB")
    digits = color[1:]
    if any(character not in "0123456789abcdefABCDEF" for character in digits):
        raise OracleValidationError("hex colors contain a non-hex digit")
    return cast(
        Rgb,
        tuple(
            int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)
        ),
    )


def srgb_to_hex(rgb: Rgb) -> str:
    """Encode finite unit-range sRGB using Python round-to-even.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Gamma-encoded channels in ``[0, 1]``.

    Returns
    -------
    str
        Lower-case ``#RRGGBB``.
    """
    channels = _validate_rgb(rgb)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in channels)


def srgb_channel_to_linear(channel: float) -> float:
    """Decode one finite unit-range sRGB channel."""
    value = _finite_float(channel, label="sRGB channel")
    if value < 0.0 or value > 1.0:
        raise OracleValidationError("sRGB channel must be in [0, 1]")
    if value <= 0.04045:
        return value / 12.92
    return cast(float, ((value + 0.055) / 1.055) ** 2.4)


def linear_channel_to_srgb(channel: float) -> float:
    """Clamp and encode one finite linear-sRGB channel."""
    value = _finite_float(channel, label="linear RGB channel")
    value = min(max(value, 0.0), 1.0)
    if value <= 0.0031308:
        return 12.92 * value
    return cast(float, 1.055 * value ** (1.0 / 2.4) - 0.055)


def _linear_rgb(rgb: Rgb) -> Rgb:
    """Gamma-decode a validated sRGB triple."""
    channels = _validate_rgb(rgb)
    return cast(Rgb, tuple(srgb_channel_to_linear(value) for value in channels))


def relative_y_srgb_d65(rgb: Rgb) -> float:
    """Return relative-Y using the white-normalized v5 D65 row.

    Parameters
    ----------
    rgb : tuple[float, float, float]
        Gamma-encoded sRGB.

    Returns
    -------
    float
        Modeled relative CIE Y calculated from nominal D65 sRGB, with exact
        white mapped to ``1.0`` by the project compatibility convention.
    """
    linear = _linear_rgb(rgb)
    return sum(
        coefficient * channel
        for coefficient, channel in zip(_D65_Y, linear, strict=True)
    )


def wcag_relative_luminance(rgb: Rgb) -> float:
    """Return WCAG relative luminance using its rounded coefficients."""
    linear = _linear_rgb(rgb)
    return sum(
        coefficient * channel
        for coefficient, channel in zip(_WCAG_Y, linear, strict=True)
    )


def wcag_contrast_ratio(first: Rgb, second: Rgb) -> float:
    """Return the WCAG contrast ratio between two sRGB colors."""
    first_luminance = wcag_relative_luminance(first)
    second_luminance = wcag_relative_luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def srgb_to_oklab(rgb: Rgb) -> Lab:
    """Convert gamma-encoded sRGB to OKLab."""
    red, green, blue = _linear_rgb(rgb)
    l_value = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    m_value = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    s_value = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    l_root = l_value ** (1.0 / 3.0)
    m_root = m_value ** (1.0 / 3.0)
    s_root = s_value ** (1.0 / 3.0)
    return (
        0.2104542553 * l_root + 0.7936177850 * m_root - 0.0040720468 * s_root,
        1.9779984951 * l_root - 2.4285922050 * m_root + 0.4505937099 * s_root,
        0.0259040371 * l_root + 0.7827717662 * m_root - 0.8086757660 * s_root,
    )


def delta_e_ok(first: Rgb, second: Rgb) -> float:
    """Return Euclidean OKLab distance scaled by 100."""
    return math.dist(srgb_to_oklab(first), srgb_to_oklab(second)) * 100.0


def _srgb_to_lab(rgb: Rgb) -> Lab:
    """Convert encoded sRGB to CIELAB D65 in the separate quality oracle."""
    linear = _linear_rgb(rgb)
    xyz = tuple(
        sum(
            coefficient * channel
            for coefficient, channel in zip(row, linear, strict=True)
        )
        for row in _RGB_TO_XYZ
    )
    transformed: list[float] = []
    for coordinate, white in zip(xyz, _D65_WHITE, strict=True):
        ratio = coordinate / white
        if ratio > 216.0 / 24389.0:
            transformed.append(ratio ** (1.0 / 3.0))
        else:
            transformed.append((24389.0 / 27.0 * ratio + 16.0) / 116.0)
    x_value, y_value, z_value = transformed
    return (
        116.0 * y_value - 16.0,
        500.0 * (x_value - y_value),
        200.0 * (y_value - z_value),
    )


def ciede2000_lab(first: Lab, second: Lab) -> float:
    """Return CIEDE2000 between two CIELAB triples."""
    l1, a1, b1 = _validate_lab(first, label="first Lab")
    l2, a2, b2 = _validate_lab(second, label="second Lab")
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    mean_c = (c1 + c2) / 2.0
    mean_c7 = mean_c**7
    g_value = 0.5 * (1.0 - math.sqrt(mean_c7 / (mean_c7 + 25.0**7)))
    a1_prime = (1.0 + g_value) * a1
    a2_prime = (1.0 + g_value) * a2
    c1_prime = math.hypot(a1_prime, b1)
    c2_prime = math.hypot(a2_prime, b2)
    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360.0
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360.0
    delta_l = l2 - l1
    delta_c = c2_prime - c1_prime
    if c1_prime * c2_prime == 0.0:
        delta_h_angle = 0.0
    else:
        raw_delta_h = h2_prime - h1_prime
        if raw_delta_h > 180.0:
            delta_h_angle = raw_delta_h - 360.0
        elif raw_delta_h < -180.0:
            delta_h_angle = raw_delta_h + 360.0
        else:
            delta_h_angle = raw_delta_h
    delta_h = (
        2.0
        * math.sqrt(c1_prime * c2_prime)
        * math.sin(math.radians(delta_h_angle) / 2.0)
    )
    mean_l = (l1 + l2) / 2.0
    mean_c_prime = (c1_prime + c2_prime) / 2.0
    if c1_prime * c2_prime == 0.0:
        mean_h = h1_prime + h2_prime
    else:
        hue_sum = h1_prime + h2_prime
        hue_difference = abs(h1_prime - h2_prime)
        if hue_difference <= 180.0:
            mean_h = hue_sum / 2.0
        elif hue_sum < 360.0:
            mean_h = (hue_sum + 360.0) / 2.0
        else:
            mean_h = (hue_sum - 360.0) / 2.0
    t_value = (
        1.0
        - 0.17 * math.cos(math.radians(mean_h - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * mean_h))
        + 0.32 * math.cos(math.radians(3.0 * mean_h + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * mean_h - 63.0))
    )
    delta_theta = 30.0 * math.exp(-(((mean_h - 275.0) / 25.0) ** 2))
    mean_c_prime7 = mean_c_prime**7
    r_c = 2.0 * math.sqrt(mean_c_prime7 / (mean_c_prime7 + 25.0**7))
    s_l = 1.0 + 0.015 * (mean_l - 50.0) ** 2 / math.sqrt(
        20.0 + (mean_l - 50.0) ** 2
    )
    s_c = 1.0 + 0.045 * mean_c_prime
    s_h = 1.0 + 0.015 * mean_c_prime * t_value
    r_t = -math.sin(math.radians(2.0 * delta_theta)) * r_c
    l_term = delta_l / s_l
    c_term = delta_c / s_c
    h_term = delta_h / s_h
    return math.sqrt(l_term**2 + c_term**2 + h_term**2 + r_t * c_term * h_term)


def ciede2000_rgb(first: Rgb, second: Rgb) -> float:
    """Return CIEDE2000 between two gamma-encoded sRGB colors."""
    return ciede2000_lab(_srgb_to_lab(first), _srgb_to_lab(second))


def _multiply_matrix(matrix: Matrix3, rgb: Rgb) -> Rgb:
    """Multiply a 3x3 row-major matrix by one RGB vector."""
    return cast(
        Rgb,
        tuple(
            sum(
                coefficient * channel
                for coefficient, channel in zip(row, rgb, strict=True)
            )
            for row in matrix
        ),
    )


def tritan_branch(linear_rgb: Rgb) -> str:
    """Return the BVM tritan half-plane name for a linear RGB vector."""
    rgb = _validate_rgb(linear_rgb, unit_range=False)
    separation = sum(
        coefficient * channel
        for coefficient, channel in zip(
            _BVM_TRITAN_SEPARATION, rgb, strict=True
        )
    )
    return "high" if separation >= 0.0 else "low"


def simulate_cvd_linear(linear_rgb: Rgb, mode: str) -> Rgb:
    """Apply a pinned CVD projection to an unclamped linear RGB vector."""
    rgb = _validate_rgb(linear_rgb, unit_range=False)
    if mode in _MACHADO:
        return _multiply_matrix(_MACHADO[mode], rgb)
    if mode == "tritan":
        matrix = (
            _BVM_TRITAN_HIGH
            if tritan_branch(rgb) == "high"
            else _BVM_TRITAN_LOW
        )
        return _multiply_matrix(matrix, rgb)
    raise OracleValidationError(f"unsupported CVD mode: {mode!r}")


def simulate_cvd(color: str | Rgb, mode: str) -> Rgb:
    """Simulate CVD and return clamped gamma-encoded sRGB."""
    rgb = hex_to_srgb(color) if isinstance(color, str) else _validate_rgb(color)
    projected = simulate_cvd_linear(_linear_rgb(rgb), mode)
    return cast(
        Rgb, tuple(linear_channel_to_srgb(value) for value in projected)
    )


def simulate_cvd_hex(color: str | Rgb, mode: str) -> str:
    """Simulate CVD and quantize the result to lower-case 8-bit hex."""
    return srgb_to_hex(simulate_cvd(color, mode))


def _percentile_type7(
    sorted_values: Sequence[float], probability: float
) -> float:
    """Return a Hyndman-Fan Type-7 percentile from sorted finite values."""
    if not sorted_values:
        raise OracleValidationError("cannot summarize an empty sequence")
    if probability < 0.0 or probability > 1.0:
        raise OracleValidationError("percentile probability must be in [0, 1]")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return sorted_values[lower] + fraction * (
        sorted_values[upper] - sorted_values[lower]
    )


def summarize_numeric(values: Sequence[float]) -> NumericSummary:
    """Summarize a non-empty finite sequence with Type-7 percentiles."""
    if not values:
        raise OracleValidationError("cannot summarize an empty sequence")
    validated = sorted(
        _finite_float(value, label=f"summary value {index}")
        for index, value in enumerate(values)
    )
    return NumericSummary(
        min=validated[0],
        p05=_percentile_type7(validated, 0.05),
        p50=_percentile_type7(validated, 0.50),
        p95=_percentile_type7(validated, 0.95),
        max=validated[-1],
        mean=math.fsum(validated) / len(validated),
    )


def meets_minimum(value: float, minimum: float) -> bool:
    """Compare raw finite values without display rounding."""
    raw_value = _finite_float(value, label="gate value")
    raw_minimum = _finite_float(minimum, label="gate minimum")
    return raw_value >= raw_minimum


def reference_payload() -> JsonObject:
    """Return fresh literal metadata and vectors for oracle conformance.

    Returns
    -------
    dict[str, object]
        JSON-safe provenance, matrices, and reference/derived vectors.
    """
    sharma_vectors: list[object] = [
        [list(first), list(second), expected]
        for first, second, expected in _SHARMA_VECTORS
    ]
    return {
        "schema": "dartwork-mpl.color-oracle-references/v1",
        # ``physical_y`` is a compatibility identifier in the frozen format.
        # The value is calculated from nominal encoded sRGB, not measured from
        # a particular display or print process.
        "physical_y": {
            "kind": (
                "v5-compatible modeled relative CIE Y row for nominal D65 sRGB"
            ),
            "coefficients": list(_D65_Y),
            "legacy_raw_coefficients": list(_LEGACY_D65_Y),
            "normalization": "legacy row divided by its 1.0000001 white sum",
            "private_cielab_uses_legacy_raw_xyz": True,
        },
        "sharma_ciede2000": {
            "kind": "published_reference_vectors",
            "source": (
                "Sharma, Wu, Dalal CIEDE2000 supplementary "
                "ciede2000testdata.txt"
            ),
            "source_sha256": SHARMA_SOURCE_SHA256,
            "tolerance": 5e-5 + 1e-12,
            "vectors": sharma_vectors,
        },
        "machado_2009": {
            "kind": (
                "source_pinned_published_matrices_and_project_derived_vectors"
            ),
            "provenance": "Machado et al. 2009 official severity-1 table",
            "provenance_sha256": MACHADO_PROVENANCE_SHA256,
            "derived_vectors_role": "project-derived regression cases",
            "severity_1_matrices": {
                mode: [list(row) for row in matrix]
                for mode, matrix in sorted(_MACHADO.items())
            },
            "derived_vectors": [
                {
                    "input_hex": "#ff0000",
                    "mode": "protan",
                    "expected_rgb": [
                        0.4266084717107862,
                        0.37265427742344537,
                        0.0,
                    ],
                    "expected_hex": "#6d5f00",
                },
                {
                    "input_hex": "#00ff00",
                    "mode": "deutan",
                    "expected_rgb": [
                        0.936051045605102,
                        0.8392477353639614,
                        0.22919186560921978,
                    ],
                    "expected_hex": "#efd63a",
                },
                {
                    "input_hex": "#123456",
                    "mode": "protan",
                    "expected_rgb": [
                        0.14283413377226134,
                        0.21187566093436755,
                        0.3427561566870771,
                    ],
                    "expected_hex": "#243657",
                },
            ],
        },
        "bvm_1997_tritan": {
            "kind": (
                "published_model_project_adapted_matrices_and_"
                "project_derived_vectors"
            ),
            "paper": "Brettel, Vienot, Mollon 1997",
            "paper_sha256": BVM_PAPER_SHA256,
            "adaptation": "libDaltonLens linear-sRGB combined matrices",
            "adaptation_commit": BVM_ADAPTATION_COMMIT,
            "adaptation_source_sha256": BVM_ADAPTATION_SOURCE_SHA256,
            "derived_vectors_role": "project-derived regression cases",
            "separation_plane": list(_BVM_TRITAN_SEPARATION),
            "high_matrix": [list(row) for row in _BVM_TRITAN_HIGH],
            "low_matrix": [list(row) for row in _BVM_TRITAN_LOW],
            "derived_vectors": [
                {
                    "branch": "high",
                    "input_hex": "#ff0000",
                    "expected_rgb": [
                        0.9999999999999999,
                        0.0,
                        0.30529869571761742,
                    ],
                    "expected_hex": "#ff004e",
                },
                {
                    "branch": "low",
                    "input_hex": "#00ff00",
                    "expected_rgb": [
                        0.4728773308242827,
                        0.9139302520470625,
                        0.9999999999999999,
                    ],
                    "expected_hex": "#79e9ff",
                },
                {
                    "branch": "separation_plane",
                    "input_hex": "#808080",
                    "expected_rgb": [
                        0.5019607843137255,
                        0.5019607843137255,
                        0.5019607843137255,
                    ],
                    "expected_hex": "#808080",
                },
            ],
        },
    }


def _is_json_finite(value: object) -> bool:
    """Return whether a nested literal value is finite and JSON-shaped."""
    if value is None or isinstance(value, bool | str | int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list | tuple):
        return all(_is_json_finite(item) for item in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and _is_json_finite(item)
            for key, item in value.items()
        )
    return False


def canonical_json_bytes(value: object) -> bytes:
    """Serialize finite JSON data canonically for provenance hashing."""
    if not _is_json_finite(value):
        raise OracleValidationError(
            "payload contains non-finite or non-JSON data"
        )
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise OracleValidationError(
            "payload is not canonical JSON data"
        ) from error
    return text.encode("utf-8")


def canonical_json_sha256(value: object) -> str:
    """Return the SHA-256 of canonical compact JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _matrix_projection_error(matrix: Matrix3) -> float:
    """Return the largest absolute element of ``M*M - M``."""
    maximum = 0.0
    for row_index in range(3):
        for column_index in range(3):
            squared = math.fsum(
                matrix[row_index][inner] * matrix[inner][column_index]
                for inner in range(3)
            )
            maximum = max(
                maximum, abs(squared - matrix[row_index][column_index])
            )
    return maximum


def verify_reference_suite(
    references: Mapping[str, object] | None = None,
) -> None:
    """Validate pinned provenance and every numerical conformance vector.

    Parameters
    ----------
    references : mapping, optional
        Decoded reference payload to validate.  The built-in literal payload
        is used when omitted.

    Raises
    ------
    OracleValidationError
        If metadata or any numerical vector differs from its pin.
    """
    expected_payload = reference_payload()
    actual_payload: object = (
        expected_payload if references is None else references
    )
    if not _is_json_finite(actual_payload):
        raise OracleValidationError("reference suite is not finite JSON data")
    if canonical_json_bytes(actual_payload) != canonical_json_bytes(
        expected_payload
    ):
        raise OracleValidationError(
            "reference suite metadata or vectors drifted"
        )

    tolerance = 5e-5 + 1e-12
    for index, (first, second, expected) in enumerate(_SHARMA_VECTORS):
        actual = ciede2000_lab(first, second)
        if abs(actual - expected) > tolerance:
            raise OracleValidationError(
                f"Sharma CIEDE2000 vector {index} failed: {actual!r}"
            )

    for matrix_name, matrix in (
        ("BVM high", _BVM_TRITAN_HIGH),
        ("BVM low", _BVM_TRITAN_LOW),
    ):
        if _matrix_projection_error(matrix) > 3e-5:
            raise OracleValidationError(
                f"{matrix_name} matrix is not idempotent"
            )

    vectors = cast(
        list[dict[str, object]],
        cast(dict[str, object], expected_payload["machado_2009"])[
            "derived_vectors"
        ],
    )
    tritan_vectors = cast(
        list[dict[str, object]],
        cast(dict[str, object], expected_payload["bvm_1997_tritan"])[
            "derived_vectors"
        ],
    )
    for vector in [*vectors, *tritan_vectors]:
        input_hex = cast(str, vector["input_hex"])
        mode = cast(str, vector.get("mode", "tritan"))
        expected_rgb = _validate_rgb(vector["expected_rgb"])
        actual_rgb = simulate_cvd(input_hex, mode)
        if any(
            abs(actual - expected) > 3e-6
            for actual, expected in zip(actual_rgb, expected_rgb, strict=True)
        ):
            raise OracleValidationError(
                f"derived CVD vector failed: {vector!r}"
            )
        if simulate_cvd_hex(input_hex, mode) != vector["expected_hex"]:
            raise OracleValidationError(
                f"derived CVD hex vector failed: {vector!r}"
            )


def _as_mapping(value: object, *, label: str) -> Mapping[str, object]:
    """Validate a string-keyed mapping."""
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise OracleValidationError(f"{label} must be a string-keyed mapping")
    return cast(Mapping[str, object], value)


def _as_hex_row(value: object, *, label: str) -> tuple[str, ...]:
    """Validate a non-empty sequence of strict hex colors."""
    if isinstance(value, str) or not isinstance(value, Sequence) or not value:
        raise OracleValidationError(f"{label} must be a non-empty color row")
    row: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise OracleValidationError(
                f"{label}[{index}] must be a hex string"
            )
        hex_to_srgb(item)
        row.append(item.lower())
    return tuple(row)


def _summary_json(values: Sequence[float]) -> dict[str, float]:
    """Return a numeric summary's JSON form."""
    return summarize_numeric(values).to_json_value()


def _neighbor_values(row: Sequence[Rgb], metric: str) -> list[float]:
    """Compute one neighbor-distance profile."""
    if metric == "oklab":
        return [delta_e_ok(first, second) for first, second in pairwise(row)]
    if metric == "ciede2000":
        return [ciede2000_rgb(first, second) for first, second in pairwise(row)]
    raise OracleValidationError(f"unsupported neighbor metric: {metric!r}")


def _step_cv(values: Sequence[float]) -> float | None:
    """Return population coefficient of variation for neighbor distances."""
    if not values:
        return None
    mean = sum(values) / len(values)
    if mean == 0.0:
        return None
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance) / mean


def _contrast_profiles(row: Sequence[Rgb]) -> tuple[list[float], list[float]]:
    """Return WCAG contrast profiles against frozen light/dark backgrounds."""
    light = (1.0, 1.0, 1.0)
    dark = hex_to_srgb("#1e1e1e")
    return (
        [wcag_contrast_ratio(color, light) for color in row],
        [wcag_contrast_ratio(color, dark) for color in row],
    )


def _quantization_cell(hex_color: str) -> tuple[Rgb, Rgb, Rgb]:
    """Return the center and half-step bounds of one shipped 8-bit sRGB cell.

    The interval models values that round to the stored channel under IEEE
    round-to-nearest, ties-to-even.  Open/closed endpoint details at exact ties
    do not affect the conservative relative-Y margin.
    """
    channels = tuple(
        int(hex_color[index : index + 2], 16) for index in (1, 3, 5)
    )
    center = cast(Rgb, tuple(channel / 255.0 for channel in channels))
    lower = cast(
        Rgb, tuple(max(0.0, (channel - 0.5) / 255.0) for channel in channels)
    )
    upper = cast(
        Rgb, tuple(min(1.0, (channel + 0.5) / 255.0) for channel in channels)
    )
    return center, lower, upper


def _relative_y_quantization(
    hex_row: Sequence[str], *, direction: str
) -> JsonObject:
    """Return the weakest adjacent modeled-Y margin over local 8-bit cells."""
    if len(hex_row) < 2:
        return {
            "worst_pair_index": None,
            "oriented_delta_y": None,
            "local_tolerance": None,
            "margin": None,
        }

    records: list[tuple[float, int, float, float]] = []
    for index, (first, second) in enumerate(pairwise(hex_row)):
        low_hex, high_hex = (
            (first, second) if direction == "increasing" else (second, first)
        )
        low_center, low_bound, _ = _quantization_cell(low_hex)
        high_center, _, high_bound = _quantization_cell(high_hex)
        low_y = relative_y_srgb_d65(low_center)
        high_y = relative_y_srgb_d65(high_center)
        oriented_delta = high_y - low_y
        tolerance = (
            low_y
            - relative_y_srgb_d65(low_bound)
            + relative_y_srgb_d65(high_bound)
            - high_y
        )
        records.append(
            (oriented_delta + tolerance, index, oriented_delta, tolerance)
        )

    margin, pair_index, oriented_delta, tolerance = min(records)
    return {
        "worst_pair_index": pair_index,
        "oriented_delta_y": oriented_delta,
        "local_tolerance": tolerance,
        "margin": margin,
    }


def ordered_quality(row_value: object) -> JsonObject:
    """Compute ordered/profile metrics for one literal hex row.

    Parameters
    ----------
    row_value : object
        Non-empty sequence of strict ``#RRGGBB`` strings.

    Returns
    -------
    dict[str, object]
        Raw, unrounded profile summaries and monotonicity diagnostics.
    """
    hex_row = _as_hex_row(row_value, label="ordered row")
    row = [hex_to_srgb(color) for color in hex_row]
    y_values = [relative_y_srgb_d65(color) for color in row]
    oklab_l_values = [srgb_to_oklab(color)[0] for color in row]
    direction = "increasing" if y_values[-1] >= y_values[0] else "decreasing"
    sign = 1.0 if direction == "increasing" else -1.0
    neighbor_ok = _neighbor_values(row, "oklab")
    neighbor_de00 = _neighbor_values(row, "ciede2000")
    oriented_y = [
        sign * (second - first) for first, second in pairwise(y_values)
    ]
    oriented_l = [
        sign * (second - first) for first, second in pairwise(oklab_l_values)
    ]
    light_contrast, dark_contrast = _contrast_profiles(row)
    result: JsonObject = {
        "count": len(row),
        "direction": direction,
        "relative_y": _summary_json(y_values),
        "oklab_l": _summary_json(oklab_l_values),
        "neighbor_delta_e_ok": (
            _summary_json(neighbor_ok) if neighbor_ok else None
        ),
        "neighbor_delta_e00": (
            _summary_json(neighbor_de00) if neighbor_de00 else None
        ),
        "oriented_delta_y": _summary_json(oriented_y) if oriented_y else None,
        "oriented_delta_l": _summary_json(oriented_l) if oriented_l else None,
        "relative_y_quantization": _relative_y_quantization(
            hex_row, direction=direction
        ),
        "step_cv": _step_cv(neighbor_ok),
        "degenerate_neighbor_steps": any(step == 0.0 for step in neighbor_ok),
        "y_span": max(y_values) - min(y_values),
        "light_contrast": _summary_json(light_contrast),
        "dark_contrast": _summary_json(dark_contrast),
    }
    for mode in ("protan", "deutan", "tritan"):
        simulated = [
            hex_to_srgb(simulate_cvd_hex(color, mode)) for color in hex_row
        ]
        simulated_y = [relative_y_srgb_d65(color) for color in simulated]
        oriented = [
            sign * (second - first) for first, second in pairwise(simulated_y)
        ]
        result[f"{mode}_oriented_delta_y"] = (
            _summary_json(oriented) if oriented else None
        )
    return result


def _pairwise_distances(
    row: Sequence[Rgb], metric: str
) -> tuple[list[float], list[list[int]]]:
    """Return pairwise values and aligned index pairs."""
    values: list[float] = []
    pairs: list[list[int]] = []
    for first_index in range(len(row)):
        for second_index in range(first_index + 1, len(row)):
            first = row[first_index]
            second = row[second_index]
            if metric == "ciede2000":
                value = ciede2000_rgb(first, second)
            elif metric == "oklab":
                value = delta_e_ok(first, second)
            else:
                raise OracleValidationError(
                    f"unsupported pairwise metric: {metric!r}"
                )
            values.append(value)
            pairs.append([first_index, second_index])
    return values, pairs


def _categorical_mode(
    hex_row: Sequence[str], mode: str | None
) -> tuple[JsonObject, float | None]:
    """Compute pairwise categorical metrics for one vision mode."""
    if mode is None:
        row = [hex_to_srgb(color) for color in hex_row]
    else:
        row = [hex_to_srgb(simulate_cvd_hex(color, mode)) for color in hex_row]
    de00, pairs = _pairwise_distances(row, "ciede2000")
    de_ok, ok_pairs = _pairwise_distances(row, "oklab")
    if not de00:
        return (
            {
                "delta_e00": None,
                "min_delta_e00": None,
                "min_pair_delta_e00": None,
                "delta_e_ok": None,
                "min_delta_e_ok": None,
                "min_pair_delta_e_ok": None,
            },
            None,
        )
    min_de00_index = min(range(len(de00)), key=de00.__getitem__)
    min_de_ok_index = min(range(len(de_ok)), key=de_ok.__getitem__)
    minimum = de00[min_de00_index]
    return (
        {
            "delta_e00": _summary_json(de00),
            "min_delta_e00": minimum,
            "min_pair_delta_e00": pairs[min_de00_index],
            "delta_e_ok": _summary_json(de_ok),
            "min_delta_e_ok": de_ok[min_de_ok_index],
            "min_pair_delta_e_ok": ok_pairs[min_de_ok_index],
        },
        minimum,
    )


def categorical_quality(row_value: object) -> JsonObject:
    """Compute normal and CVD pairwise quality for a categorical row."""
    hex_row = _as_hex_row(row_value, label="categorical row")
    row = [hex_to_srgb(color) for color in hex_row]
    light_contrast, dark_contrast = _contrast_profiles(row)
    result: JsonObject = {
        "count": len(row),
        "light_contrast": _summary_json(light_contrast),
        "dark_contrast": _summary_json(dark_contrast),
    }
    minima: dict[str, float | None] = {}
    for label, mode in (
        ("normal", None),
        ("protan", "protan"),
        ("deutan", "deutan"),
        ("tritan", "tritan"),
    ):
        mode_payload, minimum = _categorical_mode(hex_row, mode)
        minima[label] = minimum
        for key, value in mode_payload.items():
            result[f"{label}_{key}"] = value
    common_values = [
        minimum
        for label in ("normal", "protan", "deutan")
        if (minimum := minima[label]) is not None
    ]
    result["common_min_delta_e00"] = (
        min(common_values) if common_values else None
    )
    return result


def diverging_topology(row_value: object) -> JsonObject:
    """Compute two-arm topology metrics for an even-length diverging row."""
    hex_row = _as_hex_row(row_value, label="diverging row")
    if len(hex_row) < 4 or len(hex_row) % 2 != 0:
        raise OracleValidationError(
            "diverging topology requires an even row of at least four colors"
        )
    row = [hex_to_srgb(color) for color in hex_row]
    midpoint = len(row) // 2
    left_neighbor = _neighbor_values(row[:midpoint], "oklab")
    right_neighbor = _neighbor_values(row[midpoint:], "oklab")
    left_arc = sum(left_neighbor)
    right_arc = sum(right_neighbor)
    if min(left_arc, right_arc) <= 0.0:
        raise OracleValidationError("diverging arm arc must be positive")
    mirror_delta_y = [
        abs(
            relative_y_srgb_d65(row[index])
            - relative_y_srgb_d65(row[-index - 1])
        )
        for index in range(midpoint)
    ]
    center_delta_y = abs(
        relative_y_srgb_d65(row[midpoint - 1])
        - relative_y_srgb_d65(row[midpoint])
    )
    y_values = [relative_y_srgb_d65(color) for color in row]
    left_oriented_y = [
        second - first for first, second in pairwise(y_values[:midpoint])
    ]
    right_from_endpoint = list(reversed(y_values[midpoint:]))
    right_oriented_y = [
        second - first for first, second in pairwise(right_from_endpoint)
    ]
    mirrored_right_steps = list(reversed(right_neighbor))
    mirror_step_delta = [
        abs(left - right)
        for left, right in zip(left_neighbor, mirrored_right_steps, strict=True)
    ]
    mirror_step_ratio = [
        max(left, right) / min(left, right)
        for left, right in zip(left_neighbor, mirrored_right_steps, strict=True)
        if min(left, right) > 0.0
    ]
    center_values = y_values[midpoint - 1 : midpoint + 1]
    return {
        "left_arm_arc_delta_e_ok": left_arc,
        "right_arm_arc_delta_e_ok": right_arc,
        "arm_arc_ratio": max(left_arc, right_arc) / min(left_arc, right_arc),
        "mirror_delta_y": _summary_json(mirror_delta_y),
        "center_delta_y": center_delta_y,
        "center_is_global_max": max(center_values) == max(y_values),
        "left_arm_oriented_delta_y": _summary_json(left_oriented_y),
        "right_arm_oriented_delta_y": _summary_json(right_oriented_y),
        "left_arm_min_oriented_delta_y": min(left_oriented_y),
        "right_arm_min_oriented_delta_y": min(right_oriented_y),
        "left_neighbor_delta_e_ok": _summary_json(left_neighbor),
        "right_neighbor_delta_e_ok": _summary_json(right_neighbor),
        "arm_mean_step_ratio": max(
            sum(left_neighbor) / len(left_neighbor),
            sum(right_neighbor) / len(right_neighbor),
        )
        / min(
            sum(left_neighbor) / len(left_neighbor),
            sum(right_neighbor) / len(right_neighbor),
        ),
        "mirror_step_delta_e_ok": _summary_json(mirror_step_delta),
        "mirror_step_ratio": _summary_json(mirror_step_ratio),
    }


def cyclic_topology(row_value: object) -> JsonObject:
    """Compute seam and luminance-spread metrics for a cyclic row."""
    hex_row = _as_hex_row(row_value, label="cyclic row")
    if len(hex_row) < 2:
        raise OracleValidationError(
            "cyclic topology requires at least two colors"
        )
    row = [hex_to_srgb(color) for color in hex_row]
    neighbor_ok = _neighbor_values(row, "oklab")
    neighbor_de00 = _neighbor_values(row, "ciede2000")
    seam_ok = delta_e_ok(row[-1], row[0])
    seam_de00 = ciede2000_rgb(row[-1], row[0])
    mean_ok = sum(neighbor_ok) / len(neighbor_ok)
    if mean_ok <= 0.0:
        raise OracleValidationError("cyclic neighbor arc must be positive")
    y_values = [relative_y_srgb_d65(color) for color in row]
    y_spread = max(y_values) - min(y_values)
    result: JsonObject = {
        "seam_delta_e_ok": seam_ok,
        "seam_delta_e00": seam_de00,
        "seam_to_mean_delta_e_ok_ratio": seam_ok / mean_ok,
        "neighbor_delta_e_ok": _summary_json(neighbor_ok),
        "neighbor_delta_e00": _summary_json(neighbor_de00),
        "relative_y_spread": y_spread,
    }
    if y_spread <= 0.02:
        result["topology_kind"] = "isoluminant"
        result["two_arm"] = None
        return result

    midpoint = len(row) // 2
    if len(row) % 2 != 0 or midpoint < 2:
        raise OracleValidationError(
            "twilight cyclic topology requires an even row of at least four"
        )
    left_y = y_values[:midpoint]
    right_y = y_values[midpoint:]
    left_oriented = [first - second for first, second in pairwise(left_y)]
    right_oriented = [second - first for first, second in pairwise(right_y)]
    left_steps = neighbor_ok[: midpoint - 1]
    right_steps = neighbor_ok[midpoint:]
    mirrored_right_steps = list(reversed(right_steps))
    mirror_y = [
        abs(y_values[index] - y_values[-index - 1]) for index in range(midpoint)
    ]
    mirror_l = [
        abs(srgb_to_oklab(row[index])[0] - srgb_to_oklab(row[-index - 1])[0])
        for index in range(midpoint)
    ]
    mirror_step = [
        abs(left - right)
        for left, right in zip(left_steps, mirrored_right_steps, strict=True)
    ]
    left_arc = sum(left_steps)
    right_arc = sum(right_steps)
    if min(left_arc, right_arc) <= 0.0:
        raise OracleValidationError("cyclic arm arc must be positive")
    global_y_min = min(y_values)
    result["topology_kind"] = "twilight"
    result["two_arm"] = {
        "midpoint_contains_global_y_min": any(
            y_values[index] == global_y_min
            for index in (midpoint - 1, midpoint)
        ),
        "left_min_oriented_delta_y": min(left_oriented),
        "right_min_oriented_delta_y": min(right_oriented),
        "left_oriented_delta_y": _summary_json(left_oriented),
        "right_oriented_delta_y": _summary_json(right_oriented),
        "left_arc_delta_e_ok": left_arc,
        "right_arc_delta_e_ok": right_arc,
        "arm_arc_ratio": max(left_arc, right_arc) / min(left_arc, right_arc),
        "mirror_delta_y": _summary_json(mirror_y),
        "mirror_delta_oklab_l": _summary_json(mirror_l),
        "mirror_step_delta_e_ok": _summary_json(mirror_step),
    }
    return result


def _quality_map(
    values: Mapping[str, object], *, categorical: bool
) -> dict[str, object]:
    """Compute ordered or categorical quality for a named row mapping."""
    function = categorical_quality if categorical else ordered_quality
    return {name: function(values[name]) for name in sorted(values)}


def _discrete_quality(values: Mapping[str, object]) -> dict[str, object]:
    """Compute categorical metrics for every named discrete ``n`` form."""
    result: dict[str, object] = {}
    for name in sorted(values):
        forms = _as_mapping(values[name], label=f"discrete {name}")
        result[name] = {
            n_text: categorical_quality(forms[n_text])
            for n_text in sorted(forms, key=lambda value: int(value))
        }
    return result


def _oriented_profile(
    row_value: object, mode: str | None = None
) -> tuple[list[float], str]:
    """Return oriented modeled-Y steps using the normal endpoint direction."""
    hex_row = _as_hex_row(row_value, label="oriented row")
    normal = [hex_to_srgb(color) for color in hex_row]
    normal_y = [relative_y_srgb_d65(color) for color in normal]
    direction = "increasing" if normal_y[-1] >= normal_y[0] else "decreasing"
    sign = 1.0 if direction == "increasing" else -1.0
    if mode is None:
        simulated = normal
    else:
        simulated = [
            hex_to_srgb(simulate_cvd_hex(color, mode)) for color in hex_row
        ]
    simulated_y = [relative_y_srgb_d65(color) for color in simulated]
    return (
        [sign * (second - first) for first, second in pairwise(simulated_y)],
        direction,
    )


def _named_extreme(
    metrics: Mapping[str, object], field: str, *, maximum: bool
) -> JsonObject:
    """Find one named scalar metric extreme with deterministic tie-breaking."""
    candidates: list[tuple[float, str]] = []
    for name in sorted(metrics):
        payload = _as_mapping(metrics[name], label=f"metric {name}")
        value = payload.get(field)
        if value is None:
            continue
        candidates.append((_finite_float(value, label=f"{name}.{field}"), name))
    if not candidates:
        raise OracleValidationError(f"no values for metric field {field!r}")
    value, name = max(candidates) if maximum else min(candidates)
    return {"asset": name, "value": value}


def _global_extrema(
    *,
    taxonomy: Mapping[str, object],
    cmaps: Mapping[str, object],
    palette_quality: Mapping[str, object],
    preview_quality: Mapping[str, object],
    diverging: Mapping[str, object],
    cyclic: Mapping[str, object],
    cycle_quality: Mapping[str, object],
    dark_quality: Mapping[str, object],
) -> JsonObject:
    """Compute deterministic scalar extrema and their asset/index provenance."""
    ordered_names = [
        name
        for name in sorted(cmaps)
        if taxonomy.get(name) in ("sequential", "multi-hue")
    ]
    if not ordered_names:
        raise OracleValidationError(
            "catalog has no sequential/multi-hue colormaps"
        )
    worst_y: tuple[float, str, int] | None = None
    worst_cvd: tuple[float, str, str, int] | None = None
    for name in ordered_names:
        profile, _ = _oriented_profile(cmaps[name])
        index = min(range(len(profile)), key=profile.__getitem__)
        candidate = (profile[index], name, index)
        if worst_y is None or candidate < worst_y:
            worst_y = candidate
        for mode in ("protan", "deutan", "tritan"):
            cvd_profile, _ = _oriented_profile(cmaps[name], mode)
            cvd_index = min(
                range(len(cvd_profile)), key=cvd_profile.__getitem__
            )
            cvd_candidate = (cvd_profile[cvd_index], name, mode, cvd_index)
            if worst_cvd is None or cvd_candidate < worst_cvd:
                worst_cvd = cvd_candidate
    if worst_y is None or worst_cvd is None:
        raise OracleValidationError("could not compute ordered global extrema")

    diverging_ratio = _named_extreme(diverging, "arm_arc_ratio", maximum=True)
    cyclic_seams = {
        name: _finite_float(
            _as_mapping(cyclic[name], label=f"cyclic {name}")[
                "seam_delta_e_ok"
            ],
            label=f"cyclic {name} seam",
        )
        for name in sorted(cyclic)
    }
    cycle_floors: dict[str, object] = {}
    for name in sorted(cycle_quality):
        payload = _as_mapping(cycle_quality[name], label=f"cycle {name}")
        cycle_floors[name] = {
            "common_min_delta_e00": payload["common_min_delta_e00"],
            "tritan_min_delta_e00": payload["tritan_min_delta_e00"],
        }
    cycle_floors["dark"] = {
        "common_min_delta_e00": dark_quality["common_min_delta_e00"],
        "tritan_min_delta_e00": dark_quality["tritan_min_delta_e00"],
    }
    return {
        "palette_step_cv_min": _named_extreme(
            palette_quality, "step_cv", maximum=False
        ),
        "palette_step_cv_max": _named_extreme(
            palette_quality, "step_cv", maximum=True
        ),
        "direct_32_step_cv_min": _named_extreme(
            {
                name: preview_quality[name]
                for name in ordered_names
                if name in preview_quality
            },
            "step_cv",
            maximum=False,
        ),
        "direct_32_step_cv_max": _named_extreme(
            {
                name: preview_quality[name]
                for name in ordered_names
                if name in preview_quality
            },
            "step_cv",
            maximum=True,
        ),
        "worst_oriented_delta_y": {
            "asset": worst_y[1],
            "index": worst_y[2],
            "value": worst_y[0],
        },
        "worst_cvd_oriented_delta_y": {
            "asset": worst_cvd[1],
            "mode": worst_cvd[2],
            "index": worst_cvd[3],
            "value": worst_cvd[0],
        },
        "max_diverging_arm_arc_ratio": diverging_ratio,
        "cyclic_seam_delta_e_ok": cyclic_seams,
        "cycle_floors": cycle_floors,
    }


def compute_catalog_quality(
    catalog_value: object, direct_preview_32_value: object
) -> tuple[JsonObject, JsonObject]:
    """Compute quality from plain frozen literal mappings.

    Parameters
    ----------
    catalog_value : object
        Decoded v5 compatibility JSON mapping.
    direct_preview_32_value : object
        Literal 43-by-32 preview LUT mapping from the archived baseline.

    Returns
    -------
    tuple[dict[str, object], dict[str, object]]
        Per-asset metric sections and global extrema.
    """
    verify_reference_suite()
    catalog = _as_mapping(catalog_value, label="catalog")
    previews = _as_mapping(direct_preview_32_value, label="direct preview 32")
    palette = _as_mapping(catalog.get("palette"), label="catalog.palette")
    cmaps = _as_mapping(catalog.get("cmaps256"), label="catalog.cmaps256")
    cycles = _as_mapping(catalog.get("cycles"), label="catalog.cycles")
    curated = _as_mapping(
        catalog.get("curated_rows"), label="catalog.curated_rows"
    )
    discrete = _as_mapping(
        catalog.get("discrete_hex"), label="catalog.discrete_hex"
    )
    taxonomy = _as_mapping(catalog.get("taxonomy"), label="catalog.taxonomy")
    dark_cycle = catalog.get("dark_cycle")
    if set(previews) != set(cmaps):
        raise OracleValidationError(
            "direct preview names must match full LUT names"
        )
    for name in sorted(previews):
        if len(_as_hex_row(previews[name], label=f"preview {name}")) != 32:
            raise OracleValidationError(
                f"preview {name} must contain 32 colors"
            )
        if len(_as_hex_row(cmaps[name], label=f"full LUT {name}")) != 256:
            raise OracleValidationError(
                f"full LUT {name} must contain 256 colors (at least two)"
            )

    palette_quality = _quality_map(palette, categorical=False)
    preview_quality = _quality_map(previews, categorical=False)
    cmap_quality = _quality_map(cmaps, categorical=False)
    cycle_quality = _quality_map(cycles, categorical=True)
    dark_quality = categorical_quality(dark_cycle)
    curated_quality = _quality_map(curated, categorical=True)
    discrete_quality = _discrete_quality(discrete)
    diverging = {
        name: diverging_topology(cmaps[name])
        for name in sorted(cmaps)
        if taxonomy.get(name) == "diverging"
    }
    cyclic = {
        name: cyclic_topology(cmaps[name])
        for name in sorted(cmaps)
        if taxonomy.get(name) == "cyclic"
    }
    metrics: JsonObject = {
        "palette": palette_quality,
        "cmaps_direct_32": preview_quality,
        "cmaps_full_256": cmap_quality,
        "cycles": cycle_quality,
        "dark_cycle": dark_quality,
        "curated_rows": curated_quality,
        "discrete": discrete_quality,
        "topology": {"diverging": diverging, "cyclic": cyclic},
    }
    extrema = _global_extrema(
        taxonomy=taxonomy,
        cmaps=cmaps,
        palette_quality=palette_quality,
        preview_quality=preview_quality,
        diverging=diverging,
        cyclic=cyclic,
        cycle_quality=cycle_quality,
        dark_quality=dark_quality,
    )
    if not _is_json_finite(metrics) or not _is_json_finite(extrema):
        raise OracleValidationError("computed quality contains non-finite data")
    return metrics, extrema


def _quality_policy() -> JsonObject:
    """Return the versioned raw-value gate policy literal."""
    return {
        "decision_values": "raw_unrounded",
        "display_rounding_is_non_normative": True,
        "ordered_asset_kinds": ["sequential", "multi-hue"],
        "cvd_gate_pipeline": (
            "hex -> linear -> simulation -> clamp/gamma -> "
            "8-bit hex -> Lab/DeltaE00"
        ),
        "categorical_common_modes": ["normal", "protan", "deutan"],
        "tritan_mode": "tritan",
        "undefined_metrics": "json_null",
        "gate_rules": {
            "exact_migration": "all frozen hex and indices must match",
            "palette_step_cv": "candidate <= min(asset_v5, 0.08)",
            "ordered_direct_32_step_cv": ("candidate <= min(asset_v5, 0.08)"),
            "nonordered_direct_32_step_cv": "candidate <= asset_v5",
            "full_256_step_cv": "candidate <= asset_v5",
            "ordered_y_and_oklab_l": "candidate >= asset_v5 monotonic floor",
            "ordered_full_256_quantized_y": (
                "every normal-sRGB adjacent pair must have a non-negative "
                "modeled-relative-Y margin within its local 8-bit "
                "round-to-even cells"
            ),
            "ordered_y_span": "candidate >= asset_v5",
            "diverging_topology": "candidate no worse than each asset_v5 field",
            "cyclic_topology": "candidate no worse than each asset_v5 field",
            "categorical_delta_e": "candidate minimum >= asset_v5 by mode",
        },
    }


def build_quality_payload(
    catalog_value: object,
    direct_preview_32_value: object,
    *,
    baseline_commit: str,
    compatibility_path: str,
    compatibility_sha256: str,
    oracle_path: str,
    oracle_sha256: str,
) -> JsonObject:
    """Build the complete immutable quality payload from frozen literals."""
    if baseline_commit != ACCEPTED_BASELINE_COMMIT:
        raise OracleValidationError(
            "baseline commit differs from its accepted pin"
        )
    for label, digest in (
        ("compatibility SHA-256", compatibility_sha256),
        ("oracle SHA-256", oracle_sha256),
    ):
        _validate_sha256(digest, label=label)
    if compatibility_path != ACCEPTED_COMPATIBILITY_PATH:
        raise OracleValidationError(
            "compatibility path differs from its accepted pin"
        )
    if compatibility_sha256 != ACCEPTED_COMPATIBILITY_SHA256:
        raise OracleValidationError(
            "compatibility SHA-256 differs from its pin"
        )
    if oracle_path != ACCEPTED_ORACLE_PATH:
        raise OracleValidationError("oracle path differs from its accepted pin")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != oracle_sha256:
        raise OracleValidationError(
            "oracle SHA-256 differs from its source bytes"
        )
    previews = _as_mapping(direct_preview_32_value, label="direct preview 32")
    preview_literal = {
        name: list(_as_hex_row(previews[name], label=f"preview {name}"))
        for name in sorted(previews)
    }
    metrics, extrema = compute_catalog_quality(catalog_value, preview_literal)
    payload: JsonObject = {
        "schema": QUALITY_SCHEMA,
        "baseline_commit": baseline_commit,
        "compatibility": {
            "path": compatibility_path,
            "raw_sha256": compatibility_sha256,
        },
        "oracle": {
            "path": oracle_path,
            "source_sha256": oracle_sha256,
            "references": reference_payload(),
        },
        "literal_inputs": {
            "cmaps_preview_32": preview_literal,
            "cmaps_preview_32_canonical_sha256": canonical_json_sha256(
                preview_literal
            ),
        },
        "backgrounds": {"light": "#ffffff", "dark": "#1e1e1e"},
        "metrics": metrics,
        "policy": _quality_policy(),
        "global_extrema": extrema,
    }
    canonical_json_bytes(payload)
    return payload


def _validate_sha256(value: object, *, label: str) -> str:
    """Validate a lower-case hexadecimal SHA-256 string."""
    if not isinstance(value, str) or len(value) != 64:
        raise OracleValidationError(f"{label} must be a 64-digit SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise OracleValidationError(f"{label} must be lower-case hexadecimal")
    return value


_SUMMARY_KEYS = {"min", "p05", "p50", "p95", "max", "mean"}
_ORDERED_KEYS = {
    "count",
    "direction",
    "relative_y",
    "oklab_l",
    "neighbor_delta_e_ok",
    "neighbor_delta_e00",
    "oriented_delta_y",
    "oriented_delta_l",
    "relative_y_quantization",
    "step_cv",
    "degenerate_neighbor_steps",
    "y_span",
    "light_contrast",
    "dark_contrast",
    "protan_oriented_delta_y",
    "deutan_oriented_delta_y",
    "tritan_oriented_delta_y",
}
_QUANTIZATION_KEYS = {
    "worst_pair_index",
    "oriented_delta_y",
    "local_tolerance",
    "margin",
}
_CATEGORICAL_BASE_KEYS = {
    "count",
    "light_contrast",
    "dark_contrast",
    "common_min_delta_e00",
}
_CATEGORICAL_MODE_SUFFIXES = {
    "delta_e00",
    "min_delta_e00",
    "min_pair_delta_e00",
    "delta_e_ok",
    "min_delta_e_ok",
    "min_pair_delta_e_ok",
}


def _positive_count(value: object, *, label: str) -> int:
    """Validate one positive, non-boolean JSON count."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OracleValidationError(f"{label} must be a positive integer")
    return value


def _nonnegative_float(value: object, *, label: str) -> float:
    """Validate one finite non-negative scalar."""
    result = _finite_float(value, label=label)
    if result < 0.0:
        raise OracleValidationError(f"{label} must be non-negative")
    return result


def _validate_summary(value: object, *, label: str) -> None:
    """Validate one complete finite numeric-summary mapping."""
    summary = _as_mapping(value, label=label)
    if set(summary) != _SUMMARY_KEYS:
        raise OracleValidationError(f"{label} fields are invalid")
    NumericSummary(
        min=_finite_float(summary["min"], label=f"{label}.min"),
        p05=_finite_float(summary["p05"], label=f"{label}.p05"),
        p50=_finite_float(summary["p50"], label=f"{label}.p50"),
        p95=_finite_float(summary["p95"], label=f"{label}.p95"),
        max=_finite_float(summary["max"], label=f"{label}.max"),
        mean=_finite_float(summary["mean"], label=f"{label}.mean"),
    )


def _validate_optional_summary(
    value: object, *, label: str, required: bool
) -> None:
    """Validate a summary or the contractually undefined JSON null."""
    if value is None:
        if required:
            raise OracleValidationError(f"{label} cannot be null")
        return
    _validate_summary(value, label=label)


def _validate_pair(value: object, *, count: int, label: str) -> None:
    """Validate one ordered two-index pair within a categorical row."""
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str)
        or len(value) != 2
        or any(
            isinstance(index, bool) or not isinstance(index, int)
            for index in value
        )
    ):
        raise OracleValidationError(f"{label} must contain two integer indices")
    first, second = cast(Sequence[int], value)
    if not 0 <= first < second < count:
        raise OracleValidationError(f"{label} indices are out of range")


def _validate_ordered_metric(
    value: object, *, label: str, expected_count: int | None = None
) -> int:
    """Validate one ordered-row quality record."""
    metric = _as_mapping(value, label=label)
    if set(metric) != _ORDERED_KEYS:
        raise OracleValidationError(f"{label} fields are invalid")
    count = _positive_count(metric["count"], label=f"{label}.count")
    if expected_count is not None and count != expected_count:
        raise OracleValidationError(
            f"{label}.count must equal {expected_count}"
        )
    if metric["direction"] not in {"increasing", "decreasing"}:
        raise OracleValidationError(f"{label}.direction is invalid")
    _validate_summary(metric["relative_y"], label=f"{label}.relative_y")
    _validate_summary(metric["oklab_l"], label=f"{label}.oklab_l")
    _validate_summary(metric["light_contrast"], label=f"{label}.light_contrast")
    _validate_summary(metric["dark_contrast"], label=f"{label}.dark_contrast")
    required = count > 1
    for field in (
        "neighbor_delta_e_ok",
        "neighbor_delta_e00",
        "oriented_delta_y",
        "oriented_delta_l",
        "protan_oriented_delta_y",
        "deutan_oriented_delta_y",
        "tritan_oriented_delta_y",
    ):
        _validate_optional_summary(
            metric[field], label=f"{label}.{field}", required=required
        )
    quantization = _as_mapping(
        metric["relative_y_quantization"],
        label=f"{label}.relative_y_quantization",
    )
    if set(quantization) != _QUANTIZATION_KEYS:
        raise OracleValidationError(
            f"{label}.relative_y_quantization fields are invalid"
        )
    if not required:
        if any(value is not None for value in quantization.values()):
            raise OracleValidationError(
                f"{label}.relative_y_quantization must be null-valued for "
                "a singleton row"
            )
    else:
        pair_index = quantization["worst_pair_index"]
        if (
            isinstance(pair_index, bool)
            or not isinstance(pair_index, int)
            or not 0 <= pair_index < count - 1
        ):
            raise OracleValidationError(
                f"{label}.relative_y_quantization.worst_pair_index is invalid"
            )
        oriented_delta = _finite_float(
            quantization["oriented_delta_y"],
            label=(f"{label}.relative_y_quantization.oriented_delta_y"),
        )
        tolerance = _nonnegative_float(
            quantization["local_tolerance"],
            label=f"{label}.relative_y_quantization.local_tolerance",
        )
        margin = _finite_float(
            quantization["margin"],
            label=f"{label}.relative_y_quantization.margin",
        )
        if not math.isclose(
            margin, oriented_delta + tolerance, rel_tol=0.0, abs_tol=1e-15
        ):
            raise OracleValidationError(
                f"{label}.relative_y_quantization.margin is inconsistent"
            )
    degenerate = metric["degenerate_neighbor_steps"]
    if not isinstance(degenerate, bool):
        raise OracleValidationError(
            f"{label}.degenerate_neighbor_steps must be boolean"
        )
    neighbor_ok = _as_mapping(
        metric["neighbor_delta_e_ok"], label=f"{label}.neighbor_delta_e_ok"
    )
    expected_degenerate = (
        required
        and neighbor_ok is not None
        and _finite_float(
            neighbor_ok["min"], label=f"{label}.neighbor_delta_e_ok.min"
        )
        == 0.0
    )
    if degenerate is not expected_degenerate:
        raise OracleValidationError(
            f"{label}.degenerate_neighbor_steps disagrees with neighbor data"
        )
    step_cv = metric["step_cv"]
    if step_cv is None:
        all_zero = (
            required
            and neighbor_ok is not None
            and _finite_float(
                neighbor_ok["max"], label=f"{label}.neighbor_delta_e_ok.max"
            )
            == 0.0
        )
        if required and not all_zero:
            raise OracleValidationError(
                f"{label}.step_cv can be null only for an all-zero row"
            )
    else:
        _nonnegative_float(step_cv, label=f"{label}.step_cv")
        if (
            required
            and neighbor_ok is not None
            and _finite_float(
                neighbor_ok["max"], label=f"{label}.neighbor_delta_e_ok.max"
            )
            == 0.0
        ):
            raise OracleValidationError(
                f"{label}.step_cv must be null for an all-zero row"
            )
    _nonnegative_float(metric["y_span"], label=f"{label}.y_span")
    return count


def _validate_categorical_metric(
    value: object, *, label: str, expected_count: int | None = None
) -> int:
    """Validate one categorical-row quality record."""
    metric = _as_mapping(value, label=label)
    expected_keys = set(_CATEGORICAL_BASE_KEYS)
    for mode in ("normal", "protan", "deutan", "tritan"):
        expected_keys.update(
            f"{mode}_{suffix}" for suffix in _CATEGORICAL_MODE_SUFFIXES
        )
    if set(metric) != expected_keys:
        raise OracleValidationError(f"{label} fields are invalid")
    count = _positive_count(metric["count"], label=f"{label}.count")
    if expected_count is not None and count != expected_count:
        raise OracleValidationError(
            f"{label}.count must equal {expected_count}"
        )
    _validate_summary(metric["light_contrast"], label=f"{label}.light_contrast")
    _validate_summary(metric["dark_contrast"], label=f"{label}.dark_contrast")
    required = count > 1
    for mode in ("normal", "protan", "deutan", "tritan"):
        for suffix in ("delta_e00", "delta_e_ok"):
            _validate_optional_summary(
                metric[f"{mode}_{suffix}"],
                label=f"{label}.{mode}_{suffix}",
                required=required,
            )
        for suffix in ("min_delta_e00", "min_delta_e_ok"):
            field = f"{mode}_{suffix}"
            if metric[field] is None:
                if required:
                    raise OracleValidationError(
                        f"{label}.{field} cannot be null"
                    )
            else:
                _nonnegative_float(metric[field], label=f"{label}.{field}")
        for suffix in ("min_pair_delta_e00", "min_pair_delta_e_ok"):
            field = f"{mode}_{suffix}"
            if metric[field] is None:
                if required:
                    raise OracleValidationError(
                        f"{label}.{field} cannot be null"
                    )
            else:
                _validate_pair(
                    metric[field], count=count, label=f"{label}.{field}"
                )
    common = metric["common_min_delta_e00"]
    if common is None:
        if required:
            raise OracleValidationError(
                f"{label}.common_min_delta_e00 cannot be null"
            )
    else:
        _nonnegative_float(common, label=f"{label}.common_min_delta_e00")
    return count


def _validate_named_metric_map(
    value: object,
    *,
    label: str,
    expected_size: int,
    categorical: bool,
    expected_count: int | None = None,
) -> Mapping[str, object]:
    """Validate a deterministically named map of row-quality records."""
    metrics = _as_mapping(value, label=label)
    if len(metrics) != expected_size:
        raise OracleValidationError(
            f"{label} must contain {expected_size} records"
        )
    validator = (
        _validate_categorical_metric
        if categorical
        else _validate_ordered_metric
    )
    for name in sorted(metrics):
        validator(
            metrics[name],
            label=f"{label}.{name}",
            expected_count=expected_count,
        )
    return metrics


def _validate_topology(value: object, *, preview_names: set[str]) -> None:
    """Validate topology section cardinality and record shapes."""
    topology = _as_mapping(value, label="quality topology")
    if set(topology) != {"diverging", "cyclic"}:
        raise OracleValidationError("quality topology sections are invalid")
    diverging = _as_mapping(topology["diverging"], label="diverging topology")
    cyclic = _as_mapping(topology["cyclic"], label="cyclic topology")
    if len(diverging) != 11 or len(cyclic) != 3:
        raise OracleValidationError("quality topology cardinality is invalid")
    if not (set(diverging) | set(cyclic)) <= preview_names:
        raise OracleValidationError("topology references an unknown colormap")
    for name, record in [*diverging.items(), *cyclic.items()]:
        if not _as_mapping(record, label=f"topology.{name}"):
            raise OracleValidationError(f"topology.{name} cannot be empty")


def _validate_global_extrema(value: object) -> None:
    """Validate the stable top-level extrema inventory and scalar provenance."""
    extrema = _as_mapping(value, label="quality global extrema")
    expected = {
        "palette_step_cv_min",
        "palette_step_cv_max",
        "direct_32_step_cv_min",
        "direct_32_step_cv_max",
        "worst_oriented_delta_y",
        "worst_cvd_oriented_delta_y",
        "max_diverging_arm_arc_ratio",
        "cyclic_seam_delta_e_ok",
        "cycle_floors",
    }
    if set(extrema) != expected:
        raise OracleValidationError("quality global-extrema fields are invalid")
    for field in (
        "palette_step_cv_min",
        "palette_step_cv_max",
        "direct_32_step_cv_min",
        "direct_32_step_cv_max",
        "max_diverging_arm_arc_ratio",
    ):
        record = _as_mapping(extrema[field], label=f"global_extrema.{field}")
        if set(record) != {"asset", "value"} or not isinstance(
            record["asset"], str
        ):
            raise OracleValidationError(f"global_extrema.{field} is invalid")
        _finite_float(record["value"], label=f"global_extrema.{field}.value")
    worst = _as_mapping(
        extrema["worst_oriented_delta_y"], label="worst oriented delta Y"
    )
    if set(worst) != {"asset", "index", "value"}:
        raise OracleValidationError("worst oriented delta-Y fields are invalid")
    if (
        not isinstance(worst["asset"], str)
        or isinstance(worst["index"], bool)
        or not isinstance(worst["index"], int)
        or worst["index"] < 0
    ):
        raise OracleValidationError(
            "worst oriented delta-Y provenance is invalid"
        )
    _finite_float(worst["value"], label="worst oriented delta-Y value")
    worst_cvd = _as_mapping(
        extrema["worst_cvd_oriented_delta_y"],
        label="worst CVD oriented delta Y",
    )
    if set(worst_cvd) != {"asset", "mode", "index", "value"}:
        raise OracleValidationError("worst CVD delta-Y fields are invalid")
    if (
        not isinstance(worst_cvd["asset"], str)
        or worst_cvd["mode"] not in {"protan", "deutan", "tritan"}
        or isinstance(worst_cvd["index"], bool)
        or not isinstance(worst_cvd["index"], int)
        or worst_cvd["index"] < 0
    ):
        raise OracleValidationError("worst CVD delta-Y provenance is invalid")
    _finite_float(worst_cvd["value"], label="worst CVD delta-Y value")
    seams = _as_mapping(
        extrema["cyclic_seam_delta_e_ok"], label="cyclic seam extrema"
    )
    if set(seams) != {"corona", "halo", "hue"}:
        raise OracleValidationError("cyclic seam extrema are invalid")
    for name, scalar in seams.items():
        _nonnegative_float(scalar, label=f"cyclic seam {name}")
    floors = _as_mapping(extrema["cycle_floors"], label="cycle floors")
    if set(floors) != {"dark", "octave", "octave_print"}:
        raise OracleValidationError("cycle-floor records are invalid")
    for name, value_record in floors.items():
        record = _as_mapping(value_record, label=f"cycle floor {name}")
        if set(record) != {"common_min_delta_e00", "tritan_min_delta_e00"}:
            raise OracleValidationError(
                f"cycle floor {name} fields are invalid"
            )
        for field, scalar in record.items():
            _nonnegative_float(scalar, label=f"cycle floor {name}.{field}")


def validate_quality_payload(
    payload_value: object, *, expected_oracle_sha256: str
) -> JsonObject:
    """Validate a decoded quality fixture and its embedded provenance."""
    expected_oracle = _validate_sha256(
        expected_oracle_sha256, label="expected oracle SHA-256"
    )
    payload = _as_mapping(payload_value, label="quality payload")
    if payload.get("schema") != QUALITY_SCHEMA:
        raise OracleValidationError("unsupported quality payload schema")
    required = {
        "schema",
        "baseline_commit",
        "compatibility",
        "oracle",
        "literal_inputs",
        "backgrounds",
        "metrics",
        "policy",
        "global_extrema",
    }
    if set(payload) != required:
        raise OracleValidationError(
            "quality payload keys are incomplete or unknown"
        )
    if not _is_json_finite(payload):
        raise OracleValidationError("quality payload contains non-finite data")
    if payload["baseline_commit"] != ACCEPTED_BASELINE_COMMIT:
        raise OracleValidationError(
            "quality baseline commit differs from its pin"
        )
    oracle = _as_mapping(payload["oracle"], label="quality oracle")
    if set(oracle) != {"path", "source_sha256", "references"}:
        raise OracleValidationError(
            "quality oracle keys are incomplete or unknown"
        )
    if oracle.get("path") != ACCEPTED_ORACLE_PATH:
        raise OracleValidationError("quality oracle path differs from its pin")
    embedded_sha = _validate_sha256(
        oracle.get("source_sha256"), label="embedded oracle SHA-256"
    )
    if embedded_sha != expected_oracle:
        raise OracleValidationError("quality fixture references another oracle")
    current_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if current_sha != expected_oracle:
        raise OracleValidationError("loaded oracle source differs from its pin")
    references = _as_mapping(
        oracle.get("references"), label="quality oracle references"
    )
    verify_reference_suite(references)
    compatibility = _as_mapping(
        payload["compatibility"], label="quality compatibility"
    )
    compatibility_sha = _validate_sha256(
        compatibility.get("raw_sha256"), label="compatibility raw SHA-256"
    )
    if (
        compatibility
        != {
            "path": ACCEPTED_COMPATIBILITY_PATH,
            "raw_sha256": ACCEPTED_COMPATIBILITY_SHA256,
        }
        or compatibility_sha != ACCEPTED_COMPATIBILITY_SHA256
    ):
        raise OracleValidationError(
            "quality compatibility provenance differs from its pin"
        )
    literal_inputs = _as_mapping(
        payload["literal_inputs"], label="quality literal inputs"
    )
    if set(literal_inputs) != {
        "cmaps_preview_32",
        "cmaps_preview_32_canonical_sha256",
    }:
        raise OracleValidationError("quality literal-input keys are invalid")
    previews = _as_mapping(
        literal_inputs.get("cmaps_preview_32"), label="quality previews"
    )
    if len(previews) != 43:
        raise OracleValidationError("quality fixture must contain 43 previews")
    for name in sorted(previews):
        if (
            len(_as_hex_row(previews[name], label=f"quality preview {name}"))
            != 32
        ):
            raise OracleValidationError(
                f"quality preview {name} must contain 32 colors"
            )
    embedded_preview_hash = _validate_sha256(
        literal_inputs.get("cmaps_preview_32_canonical_sha256"),
        label="preview canonical SHA-256",
    )
    if canonical_json_sha256(previews) != embedded_preview_hash:
        raise OracleValidationError("direct-preview literal hash mismatch")
    backgrounds = _as_mapping(
        payload["backgrounds"], label="quality backgrounds"
    )
    if backgrounds != {"light": "#ffffff", "dark": "#1e1e1e"}:
        raise OracleValidationError(
            "quality backgrounds differ from the contract"
        )
    metrics = _as_mapping(payload["metrics"], label="quality metrics")
    if set(metrics) != {
        "palette",
        "cmaps_direct_32",
        "cmaps_full_256",
        "cycles",
        "dark_cycle",
        "curated_rows",
        "discrete",
        "topology",
    }:
        raise OracleValidationError("quality metric sections are invalid")
    _validate_named_metric_map(
        metrics["palette"],
        label="quality palette",
        expected_size=20,
        categorical=False,
        expected_count=10,
    )
    direct_metrics = _validate_named_metric_map(
        metrics["cmaps_direct_32"],
        label="quality direct-32 colormaps",
        expected_size=43,
        categorical=False,
        expected_count=32,
    )
    full_metrics = _validate_named_metric_map(
        metrics["cmaps_full_256"],
        label="quality full-256 colormaps",
        expected_size=43,
        categorical=False,
        expected_count=256,
    )
    preview_names = set(previews)
    if (
        set(direct_metrics) != preview_names
        or set(full_metrics) != preview_names
    ):
        raise OracleValidationError(
            "quality colormap metric names differ from literal previews"
        )
    _validate_named_metric_map(
        metrics["cycles"],
        label="quality cycles",
        expected_size=2,
        categorical=True,
        expected_count=8,
    )
    _validate_categorical_metric(
        metrics["dark_cycle"], label="quality dark cycle", expected_count=7
    )
    _validate_named_metric_map(
        metrics["curated_rows"],
        label="quality curated rows",
        expected_size=15,
        categorical=True,
        expected_count=8,
    )
    discrete = _as_mapping(metrics["discrete"], label="quality discrete")
    if len(discrete) != 56:
        raise OracleValidationError(
            "quality discrete metrics must contain 56 families"
        )
    for family in sorted(discrete):
        forms = _as_mapping(
            discrete[family], label=f"quality discrete.{family}"
        )
        if not forms:
            raise OracleValidationError(
                f"quality discrete.{family} cannot be empty"
            )
        for n_text in sorted(forms):
            if not n_text.isdigit() or int(n_text) < 1:
                raise OracleValidationError(
                    f"quality discrete.{family} has an invalid size key"
                )
            _validate_categorical_metric(
                forms[n_text],
                label=f"quality discrete.{family}.{n_text}",
                expected_count=int(n_text),
            )
    _validate_topology(metrics["topology"], preview_names=preview_names)
    policy = _as_mapping(payload["policy"], label="quality policy")
    if policy != _quality_policy():
        raise OracleValidationError("quality policy differs from schema v2")
    _validate_global_extrema(payload["global_extrema"])
    return dict(payload)


def load_quality_payload(
    path: str | Path, *, expected_raw_sha256: str, expected_oracle_sha256: str
) -> JsonObject:
    """Load a raw-SHA-pinned immutable quality fixture.

    Parameters
    ----------
    path : str or pathlib.Path
        JSON fixture path.
    expected_raw_sha256 : str
        Independent literal raw-byte pin.
    expected_oracle_sha256 : str
        Independent literal oracle-source pin.

    Returns
    -------
    dict[str, object]
        Validated decoded payload.
    """
    expected_raw = _validate_sha256(
        expected_raw_sha256, label="expected quality raw SHA-256"
    )
    fixture_path = Path(path)
    try:
        raw = fixture_path.read_bytes()
    except OSError as error:
        raise OracleValidationError(
            f"could not read quality fixture: {error}"
        ) from error
    actual_raw = hashlib.sha256(raw).hexdigest()
    if actual_raw != expected_raw:
        raise OracleValidationError("quality fixture raw SHA-256 mismatch")
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OracleValidationError(
            "quality fixture is not valid UTF-8 JSON"
        ) from error
    return validate_quality_payload(
        decoded, expected_oracle_sha256=expected_oracle_sha256
    )
