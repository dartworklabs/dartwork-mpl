"""Gamut-policy contracts for the v6 OKLCH color system."""

from __future__ import annotations

import ast
import importlib
import math
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest


def _gamut() -> ModuleType:
    return importlib.import_module("dartwork_mpl._colors._gamut")


def test_srgb_gamut_policy_is_pinned_frozen_and_slotted() -> None:
    """Expose one immutable deterministic sRGB gamut policy."""
    gamut = _gamut()
    policy = gamut.SRGB_GAMUT_POLICY

    assert (policy.iterations, policy.tolerance, policy.max_chroma_upper) == (
        24,
        1e-6,
        0.40,
    )
    assert not hasattr(policy, "__dict__")
    with pytest.raises(FrozenInstanceError):
        policy.iterations = 23


@pytest.mark.parametrize(
    ("kwargs", "error"),
    (
        (
            {"iterations": 0, "tolerance": 1e-6, "max_chroma_upper": 0.4},
            ValueError,
        ),
        (
            {"iterations": -1, "tolerance": 1e-6, "max_chroma_upper": 0.4},
            ValueError,
        ),
        (
            {"iterations": True, "tolerance": 1e-6, "max_chroma_upper": 0.4},
            TypeError,
        ),
        (
            {"iterations": 24, "tolerance": -1e-6, "max_chroma_upper": 0.4},
            ValueError,
        ),
        (
            {"iterations": 24, "tolerance": math.nan, "max_chroma_upper": 0.4},
            ValueError,
        ),
        (
            {"iterations": 24, "tolerance": 1e-6, "max_chroma_upper": 0.0},
            ValueError,
        ),
        (
            {"iterations": 24, "tolerance": 1e-6, "max_chroma_upper": math.inf},
            ValueError,
        ),
        (
            {"iterations": 24, "tolerance": "1e-6", "max_chroma_upper": 0.4},
            TypeError,
        ),
        (
            {
                "iterations": 24,
                "tolerance": Decimal("0.000001"),
                "max_chroma_upper": 0.4,
            },
            TypeError,
        ),
        (
            {"iterations": 24, "tolerance": True, "max_chroma_upper": 0.4},
            TypeError,
        ),
        (
            {"iterations": 24, "tolerance": 1e-6, "max_chroma_upper": "0.4"},
            TypeError,
        ),
    ),
)
def test_gamut_policy_rejects_invalid_values(
    kwargs: dict[str, object], error: type[Exception]
) -> None:
    gamut = _gamut()

    with pytest.raises(error):
        gamut.GamutPolicy(**kwargs)


def test_gamut_policy_normalizes_valid_real_fields_to_python_float() -> None:
    gamut = _gamut()

    policy = gamut.GamutPolicy(iterations=1, tolerance=0, max_chroma_upper=1)

    assert type(policy.tolerance) is float
    assert type(policy.max_chroma_upper) is float


def test_linear_gamut_bounds_are_inclusive_and_nextafter_pinned() -> None:
    gamut = _gamut()
    tolerance = 1e-6

    assert gamut.linear_srgb_in_gamut(
        (-tolerance, 0.5, 1.0 + tolerance), tolerance=tolerance
    )
    assert not gamut.linear_srgb_in_gamut(
        (math.nextafter(-tolerance, -math.inf), 0.5, 1.0), tolerance=tolerance
    )
    assert not gamut.linear_srgb_in_gamut(
        (0.0, 0.5, math.nextafter(1.0 + tolerance, math.inf)),
        tolerance=tolerance,
    )


@pytest.mark.parametrize("tolerance", (-1.0, math.nan, math.inf))
def test_linear_gamut_rejects_invalid_tolerance(tolerance: float) -> None:
    gamut = _gamut()

    with pytest.raises(ValueError):
        gamut.linear_srgb_in_gamut((0.0, 0.0, 0.0), tolerance=tolerance)


@pytest.mark.parametrize("tolerance", (True, "1e-6"))
def test_linear_gamut_rejects_non_real_tolerance(tolerance: object) -> None:
    gamut = _gamut()

    with pytest.raises(TypeError):
        gamut.linear_srgb_in_gamut((0.0, 0.0, 0.0), tolerance=tolerance)


@pytest.mark.parametrize(
    ("hue_deg", "mapped_chroma", "rgb"),
    (
        (
            16.0,
            0.1931710004806519,
            (0.9999999999999999, 0.37611047936061864, 0.4567553629851115),
        ),
        (
            99.0,
            0.14507789611816405,
            (0.7109795093242737, 0.622196064154534, 0.0),
        ),
        (
            238.0,
            0.15520212650299076,
            (0.0, 0.665824359817626, 0.9512736139958146),
        ),
        (
            298.0,
            0.1819107055664063,
            (0.6807930984856514, 0.5039412066646103, 0.9999999999999999),
        ),
    ),
)
def test_direct_degree_mapping_matches_frozen_boundary(
    hue_deg: float, mapped_chroma: float, rgb: tuple[float, float, float]
) -> None:
    gamut = _gamut()

    mapped = gamut.map_oklch_to_srgb(0.7, 0.4, hue_deg)

    assert mapped.oklab_l == 0.7
    assert mapped.hue_deg == hue_deg
    assert mapped.was_mapped is True
    assert mapped.mapped_chroma == mapped_chroma
    assert mapped.rgb == pytest.approx(rgb, abs=1e-15, rel=0.0)
    assert all(type(channel) is float for channel in mapped.rgb)


def test_in_gamut_mapping_is_a_chroma_noop() -> None:
    gamut = _gamut()

    mapped = gamut.map_oklch_to_srgb(0.7, 0.05, 30.0)

    assert mapped.was_mapped is False
    assert mapped.oklab_l == 0.7
    assert mapped.mapped_chroma == 0.05
    assert mapped.hue_deg == 30.0
    assert all(0.0 <= channel <= 1.0 for channel in mapped.rgb)


def test_general_mapper_searches_requested_chroma_not_policy_upper() -> None:
    """A C=.8 request must not silently cap the 24-step interval at .4."""
    gamut = _gamut()

    mapped = gamut.map_oklch_to_srgb(0.7, 0.8, 238.0)

    assert mapped.mapped_chroma == 0.15520210266113285


def test_custom_iteration_count_and_final_lo_are_observable() -> None:
    gamut = _gamut()
    one = gamut.GamutPolicy(iterations=1, tolerance=1e-6, max_chroma_upper=0.4)
    two = gamut.GamutPolicy(iterations=2, tolerance=1e-6, max_chroma_upper=0.4)

    after_one = gamut.map_oklch_to_srgb(0.7, 0.4, 238.0, policy=one)
    after_two = gamut.map_oklch_to_srgb(0.7, 0.4, 238.0, policy=two)

    assert after_one.mapped_chroma == 0.0
    assert after_two.mapped_chroma == 0.1


def test_default_out_of_gamut_mapping_performs_24_probes_plus_final_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gamut = _gamut()
    original = gamut._linear_srgb_at_oklch
    calls: list[float] = []

    def spy(
        lightness: float, chroma: float, hue_deg: float
    ) -> tuple[float, float, float]:
        calls.append(chroma)
        return cast(
            tuple[float, float, float], original(lightness, chroma, hue_deg)
        )

    monkeypatch.setattr(gamut, "_linear_srgb_at_oklch", spy)

    mapped = gamut.map_oklch_to_srgb(0.7, 0.4, 238.0)

    assert len(calls) == 26  # initial probe + 24 bisections + render at lo
    assert calls[-1] == mapped.mapped_chroma


def test_max_chroma_at_lightness_uses_pinned_point_four_interval() -> None:
    gamut = _gamut()

    assert gamut.max_chroma_at_lightness(0.7, 238.0) == 0.15520212650299076


def test_raw_oklch_boundary_respects_custom_tolerance() -> None:
    gamut = _gamut()

    assert gamut.oklch_in_srgb_gamut(0.7, 0.155202, 238.0) is True
    assert (
        gamut.oklch_in_srgb_gamut(0.7, 0.155202, 238.0, tolerance=0.0) is False
    )


@pytest.mark.parametrize(
    ("lightness", "chroma", "hue_deg"),
    (
        (math.nan, 0.1, 30.0),
        (math.inf, 0.1, 30.0),
        (0.5, math.nan, 30.0),
        (0.5, math.inf, 30.0),
        (0.5, -0.1, 30.0),
        (0.5, 0.1, math.nan),
        (0.5, 0.1, math.inf),
    ),
)
def test_mapping_rejects_invalid_coordinates(
    lightness: float, chroma: float, hue_deg: float
) -> None:
    gamut = _gamut()

    with pytest.raises(ValueError):
        gamut.map_oklch_to_srgb(lightness, chroma, hue_deg)


@pytest.mark.parametrize("lightness", (-0.2, 1.5))
def test_finite_extreme_lightness_clamps_to_valid_rgb(lightness: float) -> None:
    gamut = _gamut()

    mapped = gamut.map_oklch_to_srgb(lightness, 0.1, 30.0)

    assert mapped.mapped_chroma == 0.0
    assert all(math.isfinite(channel) for channel in mapped.rgb)
    assert all(0.0 <= channel <= 1.0 for channel in mapped.rgb)


@pytest.mark.parametrize("hue_deg", (-360.0, 0.0, 16.0, 238.0, 720.0))
@pytest.mark.parametrize("lightness", (0.0, 0.2, 0.7, 1.0))
@pytest.mark.parametrize("chroma", (0.0, 0.04, 0.2, 0.8))
def test_mapping_grid_is_finite_and_bounded(
    lightness: float, chroma: float, hue_deg: float
) -> None:
    gamut = _gamut()

    mapped = gamut.map_oklch_to_srgb(lightness, chroma, hue_deg)

    assert 0.0 <= mapped.mapped_chroma <= chroma
    assert all(math.isfinite(channel) for channel in mapped.rgb)
    assert all(0.0 <= channel <= 1.0 for channel in mapped.rgb)


def test_degree_conversion_wrappers_round_trip_and_normalize_hue() -> None:
    conversion = importlib.import_module("dartwork_mpl._colors._conversion")

    lab = conversion._oklch_degrees_to_oklab(0.7, 0.2, -60.0)
    actual = conversion._oklab_to_oklch_degrees(*lab)

    assert actual == pytest.approx((0.7, 0.2, 300.0), abs=1e-15, rel=0.0)


def test_gamut_module_stays_below_color_and_validation_layers() -> None:
    gamut = _gamut()
    module_file = gamut.__file__
    assert module_file is not None
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden = (
        "_color",
        "_metrics",
        "_compatibility_metrics",
        "matplotlib",
        "_generated",
    )

    assert all(
        not any(name in module for name in forbidden) for module in imported
    )
