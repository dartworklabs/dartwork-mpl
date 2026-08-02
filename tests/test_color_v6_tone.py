"""NeutralTone and modeled-relative-CIE-Y locks for the v6 color system."""

from __future__ import annotations

import ast
import importlib
import inspect
import math
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import NoReturn, cast, get_type_hints

import pytest


def _tone() -> ModuleType:
    return importlib.import_module("dartwork_mpl._colors._tone")


def test_shipped_tone_policy_is_pinned_frozen_and_slotted() -> None:
    tone = _tone()
    policy = tone.SHIPPED_TONE_POLICY

    assert (
        policy.luminance_search_iterations,
        policy.max_chroma_tone_iterations,
        policy.max_chroma_search_iterations,
        policy.probe_chroma,
        policy.max_chroma_upper,
        policy.catalog_chroma_fraction,
    ) == (40, 30, 22, 0.04, 0.40, 0.97)
    assert not hasattr(policy, "__dict__")
    with pytest.raises(FrozenInstanceError):
        policy.luminance_search_iterations = 39


@pytest.mark.parametrize(
    ("kwargs", "error"),
    (
        (
            {
                "luminance_search_iterations": 0,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            ValueError,
        ),
        (
            {
                "luminance_search_iterations": True,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            TypeError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": -1,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            ValueError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": "0.04",
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            TypeError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": Decimal("0.04"),
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            TypeError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": True,
                "catalog_chroma_fraction": 0.97,
            },
            TypeError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": "0.97",
            },
            TypeError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": math.nan,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 0.97,
            },
            ValueError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.0,
                "catalog_chroma_fraction": 0.97,
            },
            ValueError,
        ),
        (
            {
                "luminance_search_iterations": 40,
                "max_chroma_tone_iterations": 30,
                "max_chroma_search_iterations": 22,
                "probe_chroma": 0.04,
                "max_chroma_upper": 0.4,
                "catalog_chroma_fraction": 1.1,
            },
            ValueError,
        ),
    ),
)
def test_tone_policy_rejects_invalid_values(
    kwargs: dict[str, object], error: type[Exception]
) -> None:
    tone = _tone()

    with pytest.raises(error):
        tone.TonePolicy(**kwargs)


def test_tone_policy_normalizes_valid_real_fields_to_python_float() -> None:
    tone = _tone()

    policy = tone.TonePolicy(
        luminance_search_iterations=1,
        max_chroma_tone_iterations=1,
        max_chroma_search_iterations=1,
        probe_chroma=1,
        max_chroma_upper=1,
        catalog_chroma_fraction=1,
    )

    assert type(policy.probe_chroma) is float
    assert type(policy.max_chroma_upper) is float
    assert type(policy.catalog_chroma_fraction) is float


@pytest.mark.parametrize("value", (-math.inf, -0.1, 1.1, math.inf, math.nan))
@pytest.mark.parametrize("constructor_name", ("relative_y", "neutral_tone"))
def test_value_constructors_reject_nonfinite_or_out_of_range(
    value: float, constructor_name: str
) -> None:
    tone = _tone()

    with pytest.raises(ValueError):
        getattr(tone, constructor_name)(value)


def test_neutral_tone_uses_cuberoot_of_modeled_relative_y() -> None:
    tone = _tone()

    assert tone.tone_from_relative_y(0.125) == 0.5
    assert tone.relative_y_from_tone(tone.neutral_tone(0.5)) == 0.125


@pytest.mark.parametrize("value", (0.0, 0.05, 0.18, 0.5, 1.0))
def test_neutral_tone_round_trip(value: float) -> None:
    tone = _tone()

    actual = tone.relative_y_from_tone(tone.tone_from_relative_y(value))

    assert actual == pytest.approx(value, abs=1e-15, rel=0.0)


def test_newtype_bypass_is_revalidated_at_entry_points() -> None:
    tone = _tone()

    with pytest.raises(ValueError):
        tone.relative_y_from_tone(tone.NeutralTone(1.1))
    with pytest.raises(ValueError):
        tone.solve_oklch_l_for_relative_y(238.0, 0.165, tone.RelativeY(-0.1))
    with pytest.raises(ValueError):
        tone.max_chroma_at_tone(238.0, tone.NeutralTone(math.nan))


def test_internal_entry_points_preserve_newtype_static_boundaries() -> None:
    tone = _tone()

    inverse_hints = get_type_hints(tone.relative_y_from_tone)
    solver_hints = get_type_hints(tone.solve_oklch_l_for_relative_y)
    maximum_hints = get_type_hints(tone.max_chroma_at_tone)

    assert inverse_hints["value"] is tone.NeutralTone
    assert solver_hints["target_y"] is tone.RelativeY
    assert maximum_hints["tone"] is tone.NeutralTone


def test_locked_solver_matches_pinned_modeled_relative_y_result() -> None:
    tone = _tone()

    solved = tone.solve_oklch_l_for_relative_y(
        238.0, 0.165, tone.relative_y(0.125)
    )

    assert not hasattr(solved, "__dict__")
    with pytest.raises(FrozenInstanceError):
        solved.oklab_l = 0.5
    assert solved.oklab_l == 0.49612370426120833
    assert solved.mapped_chroma == 0.1099998852610588
    assert solved.rgb == pytest.approx(
        (0.0, 0.41375341203764104, 0.5993827494721622), abs=1e-15, rel=0.0
    )
    assert solved.achieved_y == 0.12500000000004285
    assert solved.residual == 4.285460875053104e-14
    assert solved.residual == solved.achieved_y - 0.125


def test_unlocked_tone_uses_tone_as_actual_oklab_l() -> None:
    tone = _tone()
    conversion = importlib.import_module("dartwork_mpl._colors._conversion")

    rgb = tone.render_oklch_at_tone(
        tone=0.5, chroma=0.165, hue=238.0, luminance_lock=False
    )

    assert rgb == pytest.approx(
        (0.0, 0.41833593169922856, 0.6057799474826644), abs=1e-15, rel=0.0
    )
    assert conversion.relative_y_srgb_d65(rgb) == 0.12795288453262946


def test_locked_render_wrapper_returns_solver_rgb() -> None:
    tone = _tone()

    actual = tone.render_oklch_at_tone(
        tone=0.5, chroma=0.165, hue=238.0, luminance_lock=True
    )
    solved = tone.solve_oklch_l_for_relative_y(
        238.0, 0.165, tone.relative_y(0.125)
    )

    assert actual == solved.rgb


def test_render_wrapper_is_keyword_only() -> None:
    tone = _tone()
    signature = inspect.signature(tone.render_oklch_at_tone)

    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    with pytest.raises(TypeError):
        tone.render_oklch_at_tone(0.5, 0.165, 238.0, True)


@pytest.mark.parametrize(
    ("target_y", "expected_l", "expected_rgb"),
    ((0.0, 0.0, (0.0, 0.0, 0.0)), (1.0, 1.0, (1.0, 1.0, 1.0))),
)
def test_locked_solver_has_exact_black_white_endpoints(
    target_y: float, expected_l: float, expected_rgb: tuple[float, float, float]
) -> None:
    tone = _tone()

    solved = tone.solve_oklch_l_for_relative_y(
        238.0, 0.165, tone.relative_y(target_y)
    )

    assert solved.rgb == expected_rgb
    assert solved.oklab_l == expected_l
    assert solved.mapped_chroma == 0.0
    assert solved.achieved_y == target_y
    assert solved.residual == 0.0


def test_locked_solver_performs_40_probes_and_one_final_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tone = _tone()
    original = tone.gamut.map_oklch_to_srgb
    calls: list[float] = []

    def spy(
        lightness: float, chroma: float, hue_deg: float, **kwargs: object
    ) -> object:
        calls.append(lightness)
        return cast(object, original(lightness, chroma, hue_deg, **kwargs))

    monkeypatch.setattr(tone.gamut, "map_oklch_to_srgb", spy)

    solved = tone.solve_oklch_l_for_relative_y(
        238.0, 0.165, tone.relative_y(0.125)
    )

    assert len(calls) == 41
    assert calls[-1] == solved.oklab_l


@pytest.mark.parametrize(
    ("hue_deg", "probe_l", "expected_chroma"),
    (
        (16.0, 0.5048058149404824, 0.20192079544067384),
        (99.0, 0.499046518933028, 0.10343017578125001),
        (238.0, 0.49803974153473973, 0.11042461395263671),
        (298.0, 0.5031430018134415, 0.27159833908081055),
    ),
)
def test_max_chroma_at_tone_uses_independent_30_then_22_searches(
    hue_deg: float,
    probe_l: float,
    expected_chroma: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tone = _tone()
    map_original = tone.gamut.map_oklch_to_srgb
    raw_original = tone.gamut.oklch_in_srgb_gamut
    map_calls: list[float] = []
    raw_calls: list[tuple[float, float]] = []

    def map_spy(
        lightness: float, chroma: float, hue: float, **kwargs: object
    ) -> object:
        map_calls.append(lightness)
        return cast(object, map_original(lightness, chroma, hue, **kwargs))

    def raw_spy(
        lightness: float, chroma: float, hue: float, **kwargs: object
    ) -> bool:
        raw_calls.append((lightness, chroma))
        return cast(bool, raw_original(lightness, chroma, hue, **kwargs))

    def reject_solver(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(tone.gamut, "map_oklch_to_srgb", map_spy)
    monkeypatch.setattr(tone.gamut, "oklch_in_srgb_gamut", raw_spy)
    monkeypatch.setattr(tone, "solve_oklch_l_for_relative_y", reject_solver)

    actual = tone.max_chroma_at_tone(hue_deg, tone.neutral_tone(0.5))

    assert actual == expected_chroma
    assert len(map_calls) == 30
    assert len(raw_calls) == 22
    assert all(lightness == probe_l for lightness, _ in raw_calls)


@pytest.mark.parametrize("tone_value", (0.0, 1.0))
def test_max_chroma_at_tone_endpoints_are_exact_zero(tone_value: float) -> None:
    tone = _tone()

    assert tone.max_chroma_at_tone(238.0, tone.neutral_tone(tone_value)) == 0.0


@pytest.mark.parametrize("hue", (0.0, 99.0, 238.0, 360.0))
@pytest.mark.parametrize("tone_value", (0.05, 0.5, 0.95))
@pytest.mark.parametrize("chroma", (0.0, 0.04, 0.165, 0.4))
@pytest.mark.parametrize("luminance_lock", (False, True))
def test_render_grid_is_finite_and_bounded(
    hue: float, tone_value: float, chroma: float, luminance_lock: bool
) -> None:
    tone = _tone()

    rgb = tone.render_oklch_at_tone(
        tone=tone_value, chroma=chroma, hue=hue, luminance_lock=luminance_lock
    )

    assert all(type(channel) is float for channel in rgb)
    assert all(math.isfinite(channel) for channel in rgb)
    assert all(0.0 <= channel <= 1.0 for channel in rgb)


def test_tone_module_stays_below_color_and_validation_layers() -> None:
    tone = _tone()
    module_file = tone.__file__
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
