"""Tests for Color API — cspace interpolation and convenience constructors."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors import Color, cspace, hex, oklab, oklch, rgb

# ============================================================================
# Convenience constructors
# ============================================================================


class TestOklab:
    """Tests for oklab() convenience constructor."""

    def test_creates_color(self) -> None:
        c = oklab(0.5, 0.1, -0.1)
        assert isinstance(c, Color)

    def test_roundtrip(self) -> None:
        L, a, b = 0.7, 0.05, -0.03
        c = oklab(L, a, b)
        L2, a2, b2 = c.to_oklab()
        assert pytest.approx(L, abs=1e-6) == L2
        assert a2 == pytest.approx(a, abs=1e-6)
        assert b2 == pytest.approx(b, abs=1e-6)


class TestOklch:
    """Tests for oklch() convenience constructor."""

    def test_creates_color(self) -> None:
        c = oklch(0.7, 0.15, 120.0)
        assert isinstance(c, Color)

    def test_roundtrip(self) -> None:
        L, C, h = 0.6, 0.12, 200.0
        c = oklch(L, C, h)
        L2, C2, h2 = c.to_oklch()
        assert pytest.approx(L, abs=1e-4) == L2
        assert pytest.approx(C, abs=1e-4) == C2
        assert h2 == pytest.approx(h, abs=1.0)


class TestRgb:
    """Tests for rgb() convenience constructor."""

    def test_creates_color(self) -> None:
        c = rgb(0.5, 0.3, 0.8)
        assert isinstance(c, Color)

    def test_roundtrip(self) -> None:
        r, g, b = 0.2, 0.7, 0.9
        c = rgb(r, g, b)
        r2, g2, b2 = c.to_rgb()
        assert r2 == pytest.approx(r, abs=1e-3)
        assert g2 == pytest.approx(g, abs=1e-3)
        assert b2 == pytest.approx(b, abs=1e-3)


class TestHex:
    """Tests for hex() convenience constructor."""

    def test_creates_color(self) -> None:
        c = hex("#FF6600")
        assert isinstance(c, Color)

    def test_known_value(self) -> None:
        c = hex("#FF0000")
        r, g, b = c.to_rgb()
        assert r == pytest.approx(1.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)


# ============================================================================
# cspace interpolation
# ============================================================================


class TestCspace:
    """Tests for cspace() color interpolation."""

    def test_oklch_interpolation(self) -> None:
        colors = cspace("#FF0000", "#0000FF", n=5, space="oklch")
        assert len(colors) == 5
        assert all(isinstance(c, Color) for c in colors)

    def test_oklab_interpolation(self) -> None:
        colors = cspace("#FF0000", "#0000FF", n=3, space="oklab")
        assert len(colors) == 3
        assert all(isinstance(c, Color) for c in colors)

    def test_rgb_interpolation(self) -> None:
        colors = cspace("#FF0000", "#0000FF", n=4, space="rgb")
        assert len(colors) == 4

    def test_endpoints_match(self) -> None:
        """First and last colors should match start/end."""
        start = "#FF0000"
        end = "#0000FF"
        colors = cspace(start, end, n=5, space="oklch")
        start_rgb = hex(start).to_rgb()
        end_rgb = hex(end).to_rgb()
        result_start = colors[0].to_rgb()
        result_end = colors[-1].to_rgb()
        for a, b in zip(start_rgb, result_start, strict=False):
            assert a == pytest.approx(b, abs=0.02)
        for a, b in zip(end_rgb, result_end, strict=False):
            assert a == pytest.approx(b, abs=0.02)

    def test_color_objects_as_input(self) -> None:
        """cspace should accept Color objects directly."""
        c1 = Color.from_hex("#FF0000")
        c2 = Color.from_hex("#00FF00")
        colors = cspace(c1, c2, n=3)
        assert len(colors) == 3

    def test_invalid_space_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported color space"):
            cspace("#FF0000", "#0000FF", n=3, space="hsv")

    def test_invalid_input_type_raises(self) -> None:
        with pytest.raises(TypeError):
            cspace(123, "#0000FF", n=3)  # type: ignore[arg-type]

    def test_hue_wrapping(self) -> None:
        """OKLCH interpolation should handle hue wrapping (>180°)."""
        # Red (h≈29°) to Blue (h≈264°) — diff > 180, should wrap
        colors = cspace("#FF0000", "#0000FF", n=3, space="oklch")
        assert len(colors) == 3

    def test_n_one(self) -> None:
        """n=1 should return a single color (start)."""
        colors = cspace("#FF0000", "#0000FF", n=1)
        assert len(colors) == 1

    def test_n_two(self) -> None:
        """n=2 should return start and end."""
        colors = cspace("#FF0000", "#0000FF", n=2)
        assert len(colors) == 2


# ============================================================================
# Color.__repr__
# ============================================================================


class TestColorRepr:
    """Tests for Color repr."""

    def test_repr_format(self) -> None:
        c = Color.from_hex("#FF0000")
        r = repr(c)
        assert r.startswith("Color(oklab=(")
        assert ")" in r
