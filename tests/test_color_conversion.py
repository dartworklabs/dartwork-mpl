"""Tests for color space conversion functions."""

from __future__ import annotations

import ast
import math
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from dartwork_mpl._colors import Color
from dartwork_mpl._colors import _conversion as conversion
from dartwork_mpl._colors._conversion import (
    _linear_srgb_to_oklab,
    _linear_to_srgb,
    _oklab_to_linear_srgb,
    _oklab_to_oklch,
    _oklch_to_oklab,
    _parse_hex,
    _rgb_to_hex,
    _srgb_to_linear,
)

_OKLAB_PRIMARY_VECTORS = (
    (
        (1.0, 0.0, 0.0),
        (0.6279553606145516, 0.2248630610659740, 0.1258462985307351),
    ),
    (
        (0.0, 1.0, 0.0),
        (0.8664396115356694, -0.2338875741879082, 0.1794984798967299),
    ),
    (
        (0.0, 0.0, 1.0),
        (0.4520137183853429, -0.0324569841687640, -0.3115281476783751),
    ),
)

# ============================================================================
# sRGB ↔ Linear RGB
# ============================================================================


class TestSrgbLinear:
    """Tests for sRGB ↔ linear gamma conversion."""

    def test_zero_stays_zero(self) -> None:
        assert float(_srgb_to_linear(0.0)) == pytest.approx(0.0, abs=1e-10)

    def test_one_stays_one(self) -> None:
        assert float(_srgb_to_linear(1.0)) == pytest.approx(1.0, abs=1e-10)

    def test_roundtrip(self) -> None:
        """srgb → linear → srgb should be identity."""
        for v in [0.0, 0.04, 0.1, 0.5, 0.8, 1.0]:
            linear = _srgb_to_linear(v)
            back = _linear_to_srgb(linear)
            assert float(back) == pytest.approx(v, abs=1e-8)

    def test_below_threshold(self) -> None:
        """Values ≤ 0.04045 use linear formula."""
        v = 0.02
        expected = v / 12.92
        assert float(_srgb_to_linear(v)) == pytest.approx(expected, abs=1e-10)


# ============================================================================
# OKLab ↔ Linear sRGB
# ============================================================================


class TestOklabLinearSrgb:
    """Tests for OKLab ↔ linear sRGB conversion."""

    def test_black(self) -> None:
        """Black (0,0,0) in linear sRGB → L≈0 in OKLab."""
        L, a, b = _linear_srgb_to_oklab(0.0, 0.0, 0.0)
        assert pytest.approx(0.0, abs=1e-8) == L
        assert a == pytest.approx(0.0, abs=1e-8)
        assert b == pytest.approx(0.0, abs=1e-8)

    def test_white(self) -> None:
        """White (1,1,1) in linear sRGB → L≈1 in OKLab."""
        L, a, b = _linear_srgb_to_oklab(1.0, 1.0, 1.0)
        assert pytest.approx(1.0, abs=1e-6) == L
        assert a == pytest.approx(0.0, abs=1e-6)
        assert b == pytest.approx(0.0, abs=1e-6)

    def test_roundtrip(self) -> None:
        """linear_srgb → oklab → linear_srgb should be identity."""
        test_values = [
            (0.5, 0.3, 0.1),
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0),
            (0.8, 0.2, 0.6),
        ]
        for r, g, b in test_values:
            L, a, b_val = _linear_srgb_to_oklab(r, g, b)
            r2, g2, b2 = _oklab_to_linear_srgb(L, a, b_val)
            assert r2 == pytest.approx(r, abs=1e-6)
            assert g2 == pytest.approx(g, abs=1e-6)
            assert b2 == pytest.approx(b, abs=1e-6)


# ============================================================================
# OKLab ↔ OKLCH
# ============================================================================


class TestOklabOklch:
    """Tests for OKLab ↔ OKLCH conversion."""

    def test_achromatic(self) -> None:
        """Achromatic color (a=0, b=0) → C=0."""
        L, C, h = _oklab_to_oklch(0.5, 0.0, 0.0)
        assert pytest.approx(0.0, abs=1e-10) == C

    def test_roundtrip(self) -> None:
        """oklab → oklch → oklab should be identity."""
        test_values = [(0.7, 0.1, 0.2), (0.3, -0.1, 0.05)]
        for L, a, b in test_values:
            L2, C, h = _oklab_to_oklch(L, a, b)
            L3, a3, b3 = _oklch_to_oklab(L2, C, h)
            assert pytest.approx(L, abs=1e-10) == L3
            assert a3 == pytest.approx(a, abs=1e-10)
            assert b3 == pytest.approx(b, abs=1e-10)

    def test_chroma_positive(self) -> None:
        """Chroma is always non-negative."""
        _, C, _ = _oklab_to_oklch(0.5, -0.1, -0.2)
        assert C >= 0.0

    def test_hue_range(self) -> None:
        """Hue in radians should be in (-π, π]."""
        _, _, h = _oklab_to_oklch(0.5, 0.1, 0.2)
        assert -math.pi <= h <= math.pi


# ============================================================================
# Hex Parsing
# ============================================================================


class TestHexParsing:
    """Tests for hex color string parsing and conversion."""

    def test_rrggbb_format(self) -> None:
        r, g, b = _parse_hex("#ff0000")
        assert r == pytest.approx(1.0, abs=1e-3)
        assert g == pytest.approx(0.0, abs=1e-3)
        assert b == pytest.approx(0.0, abs=1e-3)

    def test_rgb_shorthand(self) -> None:
        r, g, b = _parse_hex("#f00")
        assert r == pytest.approx(1.0, abs=1e-3)
        assert g == pytest.approx(0.0, abs=1e-3)
        assert b == pytest.approx(0.0, abs=1e-3)

    def test_no_hash(self) -> None:
        r, g, b = _parse_hex("00ff00")
        assert g == pytest.approx(1.0, abs=1e-3)

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            _parse_hex("#1234")

    def test_hex_roundtrip(self) -> None:
        """rgb → hex → parse_hex should be close to identity."""
        r, g, b = 0.5, 0.3, 0.8
        hex_str = _rgb_to_hex(r, g, b)
        r2, g2, b2 = _parse_hex(hex_str)
        assert r2 == pytest.approx(r, abs=2.0 / 255)
        assert g2 == pytest.approx(g, abs=2.0 / 255)
        assert b2 == pytest.approx(b, abs=2.0 / 255)

    def test_negative_hex_rejected(self) -> None:
        """A minus sign must not slip through to int(..., 16) (#229)."""
        with pytest.raises(ValueError):
            _parse_hex("#-10000")

    def test_double_hash_rejected(self) -> None:
        """``lstrip('#')`` used to swallow extra hashes silently (#229)."""
        with pytest.raises(ValueError):
            _parse_hex("##ff0000")
        with pytest.raises(ValueError):
            _parse_hex("###f00")

    def test_non_hex_digit_rejected(self) -> None:
        """Out-of-alphabet characters must raise, not produce a color."""
        with pytest.raises(ValueError):
            _parse_hex("#gggggg")

    def test_rgb_to_hex_rejects_nan(self) -> None:
        """NaN must raise, not silently clamp to white/black (#229)."""
        with pytest.raises(ValueError):
            _rgb_to_hex(float("nan"), 0.0, 0.0)

    def test_rgb_to_hex_rejects_inf(self) -> None:
        """inf must raise rather than silently clamp (#229)."""
        with pytest.raises(ValueError):
            _rgb_to_hex(float("inf"), 0.0, 0.0)
        with pytest.raises(ValueError):
            _rgb_to_hex(0.0, float("-inf"), 0.0)


# ============================================================================
# Full Color roundtrips (via Color class)
# ============================================================================


class TestColorRoundtrip:
    """Tests for full end-to-end color space roundtrips."""

    def test_rgb_to_oklab_roundtrip(self) -> None:
        """Color.from_rgb → to_rgb should preserve values."""
        test_values = [
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0),
            (0.8, 0.2, 0.3),
            (0.5, 0.5, 0.5),
        ]
        for r, g, b in test_values:
            color = Color.from_rgb(r, g, b)
            r2, g2, b2 = color.to_rgb()
            assert r2 == pytest.approx(r, abs=1e-4)
            assert g2 == pytest.approx(g, abs=1e-4)
            assert b2 == pytest.approx(b, abs=1e-4)

    def test_oklch_to_oklab_roundtrip(self) -> None:
        """Color.from_oklch → to_oklch should preserve."""
        color = Color.from_oklch(0.7, 0.2, 120.0)
        L, C, h = color.to_oklch()
        assert pytest.approx(0.7, abs=1e-8) == L
        assert pytest.approx(0.2, abs=1e-8) == C
        assert h == pytest.approx(120.0, abs=1e-6)

    def test_hex_roundtrip(self) -> None:
        color = Color.from_hex("#3a7bd5")
        hex_out = color.to_hex()
        assert hex_out == "#3a7bd5"

    def test_from_rgb_auto_detect_255(self) -> None:
        """Values > 1 are treated as 0-255 range."""
        c1 = Color.from_rgb(255, 0, 0)
        c2 = Color.from_rgb(1.0, 0.0, 0.0)
        r1, _, _ = c1.to_rgb()
        r2, _, _ = c2.to_rgb()
        assert r1 == pytest.approx(r2, abs=1e-4)

    def test_from_name(self) -> None:
        """Named colors should resolve correctly."""
        color = Color.from_name("red")
        r, g, b = color.to_rgb()
        assert r == pytest.approx(1.0, abs=1e-3)
        assert g == pytest.approx(0.0, abs=1e-3)

    def test_from_name_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid color name"):
            Color.from_name("notacolor_xyzzy")


@pytest.mark.parametrize(
    ("encoded", "expected"),
    [
        (
            math.nextafter(0.04045, -math.inf),
            math.nextafter(0.04045, -math.inf) / 12.92,
        ),
        (0.04045, 0.04045 / 12.92),
        (
            math.nextafter(0.04045, math.inf),
            ((math.nextafter(0.04045, math.inf) + 0.055) / 1.055) ** 2.4,
        ),
    ],
)
def test_srgb_decode_breakpoint(encoded: float, expected: float) -> None:
    """Pin the IEC sRGB decode branch and both adjacent floats."""
    assert float(conversion._srgb_to_linear(encoded)) == expected


@pytest.mark.parametrize(
    ("linear", "expected"),
    [
        (
            math.nextafter(0.0031308, -math.inf),
            12.92 * math.nextafter(0.0031308, -math.inf),
        ),
        (0.0031308, 12.92 * 0.0031308),
        (
            math.nextafter(0.0031308, math.inf),
            1.055 * math.nextafter(0.0031308, math.inf) ** (1.0 / 2.4) - 0.055,
        ),
    ],
)
def test_srgb_encode_breakpoint(linear: float, expected: float) -> None:
    """Pin the IEC sRGB encode branch and both adjacent floats."""
    assert float(conversion._linear_to_srgb(linear)) == expected


@pytest.mark.parametrize(("rgb", "expected"), _OKLAB_PRIMARY_VECTORS)
def test_published_oklab_primary_vectors(
    rgb: tuple[float, float, float], expected: tuple[float, float, float]
) -> None:
    """Match Ottosson's published linear-sRGB primary vectors."""
    linear = tuple(
        float(conversion._srgb_to_linear(channel)) for channel in rgb
    )
    actual = conversion._linear_srgb_to_oklab(*linear)

    assert actual == pytest.approx(expected, abs=1e-15, rel=0.0)


def test_oklab_extended_domain_uses_real_cube_root() -> None:
    """Keep negative LMS values in the real domain via ``numpy.cbrt``."""
    actual = conversion._linear_srgb_to_oklab(-0.07739938080495357, 0.0, 0.0)

    assert actual == pytest.approx(
        (-0.2676134484186351, -0.09582907156799111, -0.05363145859217086),
        abs=1e-15,
        rel=0.0,
    )
    assert all(type(value) is float for value in actual)


@pytest.mark.parametrize(
    "function", (conversion._srgb_to_linear, conversion._linear_to_srgb)
)
def test_gamma_scalar_returns_python_float(
    function: Callable[..., object],
) -> None:
    """Return Python floats to scalar production callers."""
    result = function(0.25)

    assert type(result) is float


@pytest.mark.parametrize(
    "function", (conversion._srgb_to_linear, conversion._linear_to_srgb)
)
def test_gamma_array_preserves_shape(function: Callable[..., object]) -> None:
    """Retain the existing ndarray broadcasting surface for color views."""
    channels = np.array([[0.0, 0.25], [0.5, 1.0]])
    result = function(channels)

    assert isinstance(result, np.ndarray)
    assert result.shape == channels.shape


@pytest.mark.parametrize(
    ("function", "values"),
    (
        (
            conversion._srgb_to_linear,
            (
                -0.1,
                math.nextafter(0.04045, -math.inf),
                0.04045,
                math.nextafter(0.04045, math.inf),
                0.5,
                1.1,
            ),
        ),
        (
            conversion._linear_to_srgb,
            (
                -0.1,
                math.nextafter(0.0031308, -math.inf),
                0.0031308,
                math.nextafter(0.0031308, math.inf),
                0.5,
                1.1,
            ),
        ),
    ),
)
def test_gamma_array_matches_scalar_elementwise_exactly(
    function: Callable[..., object], values: tuple[float, ...]
) -> None:
    """Pin ndarray arithmetic to the canonical scalar branch results."""
    channels = np.array(values, dtype=np.float64)
    array_result = function(channels)
    scalar_result = np.array([function(float(value)) for value in channels])

    assert isinstance(array_result, np.ndarray)
    assert np.array_equal(array_result, scalar_result)


def test_scalar_gamma_evaluates_only_the_selected_branch() -> None:
    """Avoid invalid fractional powers on unused scalar branches."""
    with np.errstate(invalid="raise"):
        decoded = conversion._srgb_to_linear(-0.1)
        encoded = conversion._linear_to_srgb(-0.1)

    assert decoded == -0.1 / 12.92
    assert encoded == 12.92 * -0.1


def test_modeled_relative_y_uses_normalized_d65_row() -> None:
    """Pin modeled-relative-CIE-Y primaries and white normalization."""
    assert conversion.SRGB_D65_Y == (
        0.21267287873271212,
        0.7151521284847872,
        0.07217499278250072,
    )
    assert (
        conversion.relative_y_srgb_d65((1.0, 0.0, 0.0))
        == (conversion.SRGB_D65_Y[0])
    )
    assert (
        conversion.relative_y_srgb_d65((0.0, 1.0, 0.0))
        == (conversion.SRGB_D65_Y[1])
    )
    assert (
        conversion.relative_y_srgb_d65((0.0, 0.0, 1.0))
        == (conversion.SRGB_D65_Y[2])
    )
    assert conversion.relative_y_srgb_d65((1.0, 1.0, 1.0)) == 1.0


def test_mixed_modeled_y_is_float_and_left_associated() -> None:
    """Pin scalar type and multiply/add order independently of BLAS."""
    rgb = (0.1, 0.2, 0.3)
    red = float(conversion._srgb_to_linear(rgb[0]))
    green = float(conversion._srgb_to_linear(rgb[1]))
    blue = float(conversion._srgb_to_linear(rgb[2]))
    expected = (
        conversion.SRGB_D65_Y[0] * red
        + conversion.SRGB_D65_Y[1] * green
        + conversion.SRGB_D65_Y[2] * blue
    )
    actual = conversion.relative_y_srgb_d65(rgb)

    assert type(actual) is float
    assert actual == expected
    assert actual == 0.031092548556125525


def test_hex_round_to_even_half_byte_values() -> None:
    """Preserve Python round-to-even at exact half-byte coordinates."""
    assert conversion._rgb_to_hex(0.5 / 255, 1.5 / 255, 2.5 / 255) == "#000202"
    assert conversion._rgb_to_hex(3.5 / 255, 4.5 / 255, 5.5 / 255) == "#040406"


@pytest.mark.parametrize(
    "hex_color", ("", "#12", "#1234", "#gg0000", "##ff0000", "#-10000")
)
def test_hex_parser_rejects_malformed_input(hex_color: str) -> None:
    """Reject malformed strings before attempting integer conversion."""
    with pytest.raises(ValueError, match="Invalid hex color format"):
        conversion._parse_hex(hex_color)


@pytest.mark.parametrize("non_finite", (math.nan, math.inf, -math.inf))
def test_hex_encoder_rejects_every_non_finite_channel(
    non_finite: float,
) -> None:
    """Reject NaN and both infinities before channel clamping."""
    with pytest.raises(ValueError, match="RGB channels must be finite"):
        conversion._rgb_to_hex(0.0, non_finite, 0.0)


def test_conversion_has_no_validation_or_luminance_import_edge() -> None:
    """Keep the canonical math kernel below metrics and luminance wrappers."""
    source_path = Path(conversion.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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

    assert all("_metrics" not in name for name in imported)
    assert all("_luminance" not in name for name in imported)


def test_cold_package_import_succeeds_in_subprocess() -> None:
    """Guard the conversion/luminance import order against a package cycle."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import dartwork_mpl; "
                "from dartwork_mpl._luminance import _contrast_ratio; "
                "assert _contrast_ratio((0,0,0),(1,1,1)) == 21.0; "
                "print(dartwork_mpl.__version__)"
            ),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
