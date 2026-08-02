"""Tests for the packaged v6 NeutralTone recipe SSOT."""

import math
from collections.abc import Mapping, Sequence
from typing import cast

import pytest

from dartwork_mpl._colors import _recipe

EXPECTED_FAMILY_TONES = {
    "red": 0.4999999833333344,
    "rose": 0.4827586045977022,
    "coral": 0.5172413620689666,
    "tangerine": 0.5603448089080472,
    "orange": 0.6034482557471277,
    "amber": 0.6293103238505761,
    "yellow": 0.6551723919540244,
    "lime": 0.6206896344827599,
    "green": 0.5775861876436794,
    "teal": 0.5431034301724149,
    "cyan": 0.5172413620689666,
    "sky": 0.5086206727011505,
    "blue": 0.4999999833333344,
    "cobalt": 0.4827586045977022,
    "indigo": 0.4741379152298861,
    "violet": 0.4568965364942539,
    "purple": 0.4568965364942539,
    "fuchsia": 0.4568965364942539,
    "pink": 0.4741379152298861,
}
EXPECTED_TONE_FOURIER = (
    0.5329026632710612,
    -0.032555033397590874,
    0.08190118692513294,
    -0.03458183505416875,
    0.0022987585440643727,
    0.005924327388729323,
    -0.01160587892348221,
)


def _frozen_fourier_eval(
    coefficients: Sequence[float], hue_deg: float
) -> float:
    """Evaluate the v5 grouped harmonic arithmetic independently."""
    hue = math.radians(hue_deg)
    value = coefficients[0]
    for harmonic in range(1, (len(coefficients) - 1) // 2 + 1):
        value += coefficients[2 * harmonic - 1] * math.cos(
            harmonic * hue
        ) + coefficients[2 * harmonic] * math.sin(harmonic * hue)
    return float(value)


def _object_map(value: object) -> Mapping[str, object]:
    """Narrow a decoded fixture value to a string-keyed mapping."""
    assert isinstance(value, Mapping)
    return cast(Mapping[str, object], value)


def test_families_remain_complete_and_ordered() -> None:
    """Keep all 19 public family recipe rows in their canonical order."""
    assert _recipe.FAMILIES == (
        "red",
        "rose",
        "coral",
        "tangerine",
        "orange",
        "amber",
        "yellow",
        "lime",
        "green",
        "teal",
        "cyan",
        "sky",
        "blue",
        "cobalt",
        "indigo",
        "violet",
        "purple",
        "fuchsia",
        "pink",
    )


def test_family_tone_floors_match_full_double_migration() -> None:
    """Read every migrated floor without legacy decimal re-rounding."""
    actual = {
        family: params.tone_floor
        for family, params in _recipe.FAMILY_PARAMS.items()
    }

    assert actual == EXPECTED_FAMILY_TONES


def test_family_tone_floors_are_finite_unit_values() -> None:
    """Keep recipe tone coordinates inside their declared value domain."""
    assert all(
        math.isfinite(params.tone_floor) and 0.0 <= params.tone_floor <= 1.0
        for params in _recipe.FAMILY_PARAMS.values()
    )


def test_tone_constants_match_full_double_migration() -> None:
    """Pin the top, gray floor, and one-L-star provenance grid."""
    assert (
        _recipe.TONE_TOP,
        _recipe.GRAY_TONE_FLOOR,
        _recipe.TONE_DERIVATION_GRID,
    ) == (0.9655172091954044, 0.37931033218390886, 0.00862068936781611)


def test_tone_floor_fourier_matches_affine_curve_transform() -> None:
    """Transform the affine Fourier curve rather than each term as L*."""
    assert _recipe.FOURIER["tone_floor_k3"] == EXPECTED_TONE_FOURIER


@pytest.mark.parametrize("hue", [0.0, 3.0, 52.0, 176.0, 298.0, 359.0])
def test_tone_floor_fourier_preserves_the_sampled_affine_curve(
    hue: float, v5_ssot: Mapping[str, object]
) -> None:
    """Match ``(legacy_curve + 16) / D`` at representative hues."""
    fourier = _object_map(v5_ssot["fourier"])
    coefficients = cast(Sequence[float], fourier["floor_k3"])
    legacy = _frozen_fourier_eval(coefficients, hue)
    actual = _recipe.fourier_eval(_recipe.FOURIER["tone_floor_k3"], hue)

    assert actual == pytest.approx(
        (legacy + 16.0) / 116.00000386666655, abs=1e-15, rel=0.0
    )


def test_fourier_eval_preserves_grouped_v5_float_order() -> None:
    """Keep the grouped cosine-plus-sine rounding used by the frozen recipe."""
    assert _recipe.fourier_eval(_recipe.FOURIER["cmax_k3"], 52.0) == (
        0.19370197289410873
    )


def test_non_tone_recipe_values_match_v5_provenance(
    v5_ssot: Mapping[str, object],
) -> None:
    """Change only the legacy lightness coordinate in family parameters."""
    references = _object_map(v5_ssot["params"])
    for family, params in _recipe.FAMILY_PARAMS.items():
        reference = _object_map(references[family])
        for field in ("h0", "dh", "gamma", "tp", "cmax", "cend", "c0"):
            assert getattr(params, field) == reference[field], (family, field)


def test_non_tone_fourier_values_match_v5_provenance(
    v5_ssot: Mapping[str, object],
) -> None:
    """Keep chroma/profile Fourier curves byte-for-value compatible."""
    fourier = _object_map(v5_ssot["fourier"])
    for key in ("cmax_k3", "cend_k2", "c0_k2"):
        assert list(_recipe.FOURIER[key]) == fourier[key]


def test_cycle_print_ssot_maps_to_octave_print_spec(
    v5_ssot: Mapping[str, object],
) -> None:
    """Keep the historical-named cycle independent from tone migration."""
    from dartwork_mpl._colors._cycles import CYCLE_SPECS

    expected = [
        ["blue", 5],
        ["orange", 8],
        ["green", 1],
        ["pink", 2],
        ["amber", 5],
        ["violet", 9],
        ["cyan", 8],
        ["gray", 9],
    ]
    cycle_print = _object_map(v5_ssot["cycle_print"])
    assert cycle_print["spec"] == expected
    assert [list(value) for value in CYCLE_SPECS["octave_print"]] == expected


def test_derive_family_stays_within_one_migrated_grid_step() -> None:
    """Retain the three documented table-vs-Fourier deviations."""
    mismatches: set[tuple[str, str]] = set()
    for family in _recipe.FAMILIES:
        params = _recipe.FAMILY_PARAMS[family]
        derived = _recipe.derive_family(
            params.h0, params.dh, params.gamma, params.tp
        )
        assert abs(derived.cmax - params.cmax) <= 0.005 + 1e-12, family
        assert (
            abs(derived.tone_floor - params.tone_floor)
            <= _recipe.TONE_DERIVATION_GRID + 1e-15
        ), family
        assert abs(derived.cend - params.cend) <= 0.05 + 1e-12, family
        assert abs(derived.c0 - params.c0) <= 0.05 + 1e-12, family
        mismatches.update(
            (family, field)
            for field in ("cmax", "tone_floor", "cend", "c0")
            if getattr(derived, field) != getattr(params, field)
        )

    assert mismatches == {
        ("rose", "c0"),
        ("teal", "tone_floor"),
        ("violet", "cmax"),
    }


def test_derive_family_uses_full_double_tone_grid() -> None:
    """Prevent the former ten-decimal legacy grid from returning."""
    params = _recipe.FAMILY_PARAMS["red"]
    derived = _recipe.derive_family(
        params.h0, params.dh, params.gamma, params.tp
    )

    assert derived.tone_floor / _recipe.TONE_DERIVATION_GRID == pytest.approx(
        round(derived.tone_floor / _recipe.TONE_DERIVATION_GRID),
        abs=1e-14,
        rel=0.0,
    )


def test_gray_profile_length_remains_ten() -> None:
    """Keep one tint chroma for every palette gray step."""
    assert len(_recipe.GRAY_C_PROFILE) == 10


def test_fourier_eval_and_mid_hue_remain_stable() -> None:
    """Retain the established Fourier evaluation and hue midpoint math."""
    assert (
        _recipe.fourier_eval((1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 123.0) == 1.0
    )
    assert _recipe.mid_hue(_recipe.FAMILY_PARAMS["red"]) == pytest.approx(
        (16.0 + 11.0 * 0.5**1.10) % 360, abs=1e-9, rel=0.0
    )
