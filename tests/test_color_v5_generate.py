"""Compatibility tests for the NeutralTone palette compiler."""

import ast
import hashlib
import inspect
import json
import math
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import pytest

from dartwork_mpl._colors import _conversion, _generate, _tone
from dartwork_mpl._colors._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    TONE_TOP,
    FamilyParams,
)

Rgb = tuple[float, float, float]
PALETTE_SHA256 = (
    "4431b8d1accbeca9527e6097a62c048a51fd6fd699588998c202c359b98b458e"
)


def _canonical_sha256(value: object) -> str:
    """Hash one JSON value with the compatibility-manifest encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _frozen_decode_srgb(channel: float) -> float:
    """Decode one sRGB channel with the frozen v5 transfer function."""
    if channel <= 0.04045:
        return channel / 12.92
    return float(((channel + 0.055) / 1.055) ** 2.4)


def _frozen_encode_srgb(channel: float) -> float:
    """Clamp and encode one linear channel with the frozen v5 transfer."""
    bounded = min(max(channel, 0.0), 1.0)
    if bounded <= 0.0031308:
        return 12.92 * bounded
    return float(1.055 * bounded ** (1.0 / 2.4) - 0.055)


def _frozen_linear_srgb(
    lightness: float, chroma: float, hue_radians: float
) -> Rgb:
    """Convert OKLCH to raw linear sRGB using the frozen v5 matrices."""
    a = chroma * math.cos(hue_radians)
    b = chroma * math.sin(hue_radians)
    l_root = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_root = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_root = lightness - 0.0894841775 * a - 1.2914855480 * b
    l_value = l_root * l_root * l_root
    m_value = m_root * m_root * m_root
    s_value = s_root * s_root * s_root
    return (
        4.0767416621 * l_value
        - 3.3077115913 * m_value
        + 0.2309699292 * s_value,
        -1.2684380046 * l_value
        + 2.6097574011 * m_value
        - 0.3413193965 * s_value,
        -0.0041960863 * l_value
        - 0.7034186147 * m_value
        + 1.7076147010 * s_value,
    )


def _frozen_in_gamut(rgb: Rgb) -> bool:
    """Apply the frozen inclusive raw-gamut tolerance."""
    return all(-1e-6 <= channel <= 1.0 + 1e-6 for channel in rgb)


def _frozen_map_oklch(
    lightness: float, chroma: float, hue_degrees: float
) -> Rgb:
    """Render one request with the independent frozen 24-step mapper."""
    hue_radians = math.radians(hue_degrees)
    raw = _frozen_linear_srgb(lightness, chroma, hue_radians)
    if not _frozen_in_gamut(raw):
        # v5 stored OKLab first, then reconstructed polar coordinates inside
        # ``Color.to_rgb()`` before its gamut search. Preserve that otherwise
        # unnecessary round trip so this really is the frozen implementation,
        # not a copy of the candidate degree-based mapper.
        requested_a = chroma * math.cos(hue_radians)
        requested_b = chroma * math.sin(hue_radians)
        mapped_chroma = math.sqrt(
            requested_a * requested_a + requested_b * requested_b
        )
        mapped_hue = math.atan2(requested_b, requested_a)
        lower = 0.0
        upper = mapped_chroma
        for _ in range(24):
            midpoint = (lower + upper) / 2.0
            probe = _frozen_linear_srgb(lightness, midpoint, mapped_hue)
            if _frozen_in_gamut(probe):
                lower = midpoint
            else:
                upper = midpoint
        raw = _frozen_linear_srgb(lightness, lower, mapped_hue)
    return cast(Rgb, tuple(_frozen_encode_srgb(channel) for channel in raw))


def _frozen_legacy_lstar(rgb: Rgb) -> float:
    """Measure raw-row CIELAB L* exactly as the frozen solver did."""
    red, green, blue = (_frozen_decode_srgb(channel) for channel in rgb)
    raw_y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    if raw_y > 216.0 / 24389.0:
        fy = float(raw_y ** (1.0 / 3.0))
    else:
        fy = (24389.0 / 27.0 * raw_y + 16.0) / 116.0
    return 116.0 * fy - 16.0


def _frozen_legacy_solver(
    hue_degrees: float, chroma: float, target_lstar: float
) -> Rgb:
    """Solve one v5 L* request without importing candidate construction."""
    lower = 0.0
    upper = 1.0
    for _ in range(40):
        midpoint = (lower + upper) / 2.0
        rendered = _frozen_map_oklch(midpoint, chroma, hue_degrees)
        if _frozen_legacy_lstar(rendered) < target_lstar:
            lower = midpoint
        else:
            upper = midpoint
    return _frozen_map_oklch((lower + upper) / 2.0, chroma, hue_degrees)


def _frozen_hex(rgb: Rgb) -> str:
    """Quantize a frozen float RGB result with Python round semantics."""
    return "#" + "".join(
        f"{round(min(max(channel, 0.0), 1.0) * 255):02x}" for channel in rgb
    )


def _legacy_family_row(
    v5_ssot: Mapping[str, object], family: str
) -> Mapping[str, float]:
    """Return one typed frozen family recipe row."""
    params = cast(Mapping[str, object], v5_ssot["params"])
    return cast(Mapping[str, float], params[family])


def _family_coordinate(
    params: FamilyParams, fraction: float
) -> tuple[float, float, float]:
    """Return the migrated tone, chroma, and hue for one dense point."""
    tone = float(TONE_TOP + (params.tone_floor - TONE_TOP) * fraction)
    hue = float((params.h0 + params.dh * fraction**params.gamma) % 360)
    chroma = float(
        params.cmax
        * _generate.shape(fraction, params.tp, params.c0, params.cend)
    )
    return tone, chroma, hue


def _candidate_swatch(
    params: FamilyParams, fraction: float, *, luminance_lock: bool
) -> Rgb:
    """Call the future swatch signature while inspect tests type its policy."""
    function = cast(Callable[..., Rgb], _generate.swatch)
    return function(params, fraction, luminance_lock=luminance_lock)


def _compile_palette(*, luminance_lock: bool) -> dict[str, list[str]]:
    """Call the future palette signature while inspect tests type its policy."""
    function = cast(
        Callable[..., dict[str, list[str]]], _generate.compile_palette
    )
    return function(luminance_lock=luminance_lock)


def test_unlocked_swatch_uses_tone_as_direct_oklch_lightness() -> None:
    """Make the explicit opt-out a direct OKLCH-L render, not a Y solve."""
    params = FAMILY_PARAMS["blue"]
    fraction = 0.37
    tone, chroma, hue = _family_coordinate(params, fraction)

    actual = _candidate_swatch(params, fraction, luminance_lock=False)
    expected = _tone.render_oklch_at_tone(
        tone=tone, chroma=chroma, hue=hue, luminance_lock=False
    )

    assert actual == expected


def test_dense_family_solver_matches_frozen_v5_at_all_2299_points(
    v5_ssot: Mapping[str, object],
) -> None:
    """Block float or hex drift at every family equalization input point."""
    count = 0
    hex_mismatches = 0
    max_rgb_drift = 0.0
    max_achieved_y_drift = 0.0
    max_residual_worsening = -math.inf

    for family in FAMILIES:
        params = FAMILY_PARAMS[family]
        legacy = _legacy_family_row(v5_ssot, family)
        for index in range(121):
            fraction = index / 120.0
            tone, chroma, hue = _family_coordinate(params, fraction)
            legacy_lstar = 96.0 + (legacy["floor"] - 96.0) * fraction
            baseline = _frozen_legacy_solver(hue, chroma, legacy_lstar)
            candidate = _candidate_swatch(params, fraction, luminance_lock=True)
            baseline_y = _conversion.relative_y_srgb_d65(baseline)
            candidate_y = _conversion.relative_y_srgb_d65(candidate)
            target_y = tone**3

            count += 1
            hex_mismatches += _frozen_hex(candidate) != _frozen_hex(baseline)
            max_rgb_drift = max(
                max_rgb_drift,
                *(
                    abs(new - old)
                    for new, old in zip(candidate, baseline, strict=True)
                ),
            )
            max_achieved_y_drift = max(
                max_achieved_y_drift, abs(candidate_y - baseline_y)
            )
            max_residual_worsening = max(
                max_residual_worsening,
                abs(candidate_y - target_y) - abs(baseline_y - target_y),
            )

    assert count == 2299
    assert hex_mismatches == 0
    assert max_rgb_drift <= 5e-12
    assert max_achieved_y_drift <= 5e-13
    assert max_residual_worsening <= 1e-15


def test_compile_blue_matches_frozen_palette(
    v5_ssot: Mapping[str, object],
) -> None:
    """Preserve one sensitive family through the locked default path."""
    palette = cast(Mapping[str, list[str]], v5_ssot["palette"])

    function = cast(Callable[..., list[str]], _generate.compile_family)

    assert (
        function(FAMILY_PARAMS["blue"], luminance_lock=True) == palette["blue"]
    )


def test_compile_gray_matches_frozen_palette(
    v5_ssot: Mapping[str, object],
) -> None:
    """Preserve the tinted neutral ladder through the locked path."""
    palette = cast(Mapping[str, list[str]], v5_ssot["palette"])

    function = cast(Callable[..., list[str]], _generate.compile_gray)

    assert function(luminance_lock=True) == palette["gray"]


def test_locked_palette_matches_frozen_exact_hash(
    v5_ssot: Mapping[str, object],
) -> None:
    """Pin all 200 shipped swatches with one canonical digest."""
    expected = v5_ssot["palette"]
    actual = _compile_palette(luminance_lock=True)

    assert actual == expected
    assert _canonical_sha256(actual) == PALETTE_SHA256


def test_unlocked_palette_is_explicit_and_non_shipped() -> None:
    """Expose direct OKLCH diagnostics without changing the locked default."""
    locked = _compile_palette(luminance_lock=True)
    direct = _compile_palette(luminance_lock=False)

    assert set(direct) == set(locked)
    assert {name: len(row) for name, row in direct.items()} == dict.fromkeys(
        locked, 10
    )
    assert direct != locked


def test_generate_entry_points_have_keyword_only_true_lock() -> None:
    """Keep every palette construction boundary explicit and shipped-safe."""
    for name in ("swatch", "compile_family", "compile_gray", "compile_palette"):
        function = getattr(_generate, name)
        parameter = inspect.signature(function).parameters["luminance_lock"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is True, name


def test_equalization_keeps_the_frozen_dense_and_pass_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retain 121 dense samples and fourteen refinement opportunities."""
    calls = 0
    distance_calls = 0

    def swatch_at(value: float) -> Rgb:
        """Return a nonlinear neutral path while counting evaluations."""
        nonlocal calls
        calls += 1
        return (value * value, value * value, value * value)

    def uneven_distance(left: Rgb, right: Rgb) -> float:
        """Force every refinement pass to remain above the CV cutoff."""
        nonlocal distance_calls
        del left, right
        distance_calls += 1
        return 1.0 if distance_calls % 2 else 2.0

    monkeypatch.setattr(_generate, "de_ok_rgb", uneven_distance)
    result = _generate.equalize(swatch_at, n=10)

    assert _generate.__file__ is not None
    tree = ast.parse(Path(_generate.__file__).read_text(encoding="utf-8"))
    equalize = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "equalize"
    )
    range_literals = [
        node.args[0].value
        for node in ast.walk(equalize)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "range"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, int)
    ]

    assert len(result) == 10
    assert (
        inspect.signature(_generate.equalize).parameters["dense"].default == 121
    )
    assert range_literals.count(14) == 1
    assert calls == 121 + 10 + 14 * 8


@pytest.mark.parametrize("luminance_lock", [True, False])
def test_palette_compiler_accepts_lock_only_by_keyword(
    luminance_lock: bool,
) -> None:
    """Reject a positional Boolean whose meaning is otherwise opaque."""
    with pytest.raises(TypeError):
        cast(Callable[..., object], _generate.compile_palette)(luminance_lock)
