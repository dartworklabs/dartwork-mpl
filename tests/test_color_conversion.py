"""Tests for color space conversion functions."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl.color import Color
from dartwork_mpl.color._conversion import (
    _linear_srgb_to_oklab,
    _linear_to_srgb,
    _oklab_to_linear_srgb,
    _oklab_to_oklch,
    _oklch_to_oklab,
    _parse_hex,
    _rgb_to_hex,
    _srgb_to_linear,
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
        assert L == pytest.approx(0.0, abs=1e-8)
        assert a == pytest.approx(0.0, abs=1e-8)
        assert b == pytest.approx(0.0, abs=1e-8)

    def test_white(self) -> None:
        """White (1,1,1) in linear sRGB → L≈1 in OKLab."""
        L, a, b = _linear_srgb_to_oklab(1.0, 1.0, 1.0)
        assert L == pytest.approx(1.0, abs=1e-6)
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
        assert C == pytest.approx(0.0, abs=1e-10)

    def test_roundtrip(self) -> None:
        """oklab → oklch → oklab should be identity."""
        test_values = [(0.7, 0.1, 0.2), (0.3, -0.1, 0.05)]
        for L, a, b in test_values:
            L2, C, h = _oklab_to_oklch(L, a, b)
            L3, a3, b3 = _oklch_to_oklab(L2, C, h)
            assert L3 == pytest.approx(L, abs=1e-10)
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
        assert L == pytest.approx(0.7, abs=1e-8)
        assert C == pytest.approx(0.2, abs=1e-8)
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
