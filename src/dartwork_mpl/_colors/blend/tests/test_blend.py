"""mix_colors blends in OKLab and pseudo_alpha flattens alpha onto a background."""

from __future__ import annotations

import matplotlib
import pytest

from dartwork_mpl._colors.blend import mix_colors, pseudo_alpha


class TestMixColors:
    """Tests for mix_colors()."""

    def test_same_color(self) -> None:
        """Mixing a color with itself should return the same color."""
        r, g, b = mix_colors("red", "red", alpha=0.5)
        expected = matplotlib.colors.to_rgb("red")
        assert r == pytest.approx(expected[0], abs=1e-4)
        assert g == pytest.approx(expected[1], abs=1e-4)
        assert b == pytest.approx(expected[2], abs=1e-4)

    def test_alpha_one(self) -> None:
        """alpha=1.0 should return the first color."""
        r, g, b = mix_colors("red", "blue", alpha=1.0)
        expected = matplotlib.colors.to_rgb("red")
        assert r == pytest.approx(expected[0], abs=1e-4)

    def test_alpha_zero(self) -> None:
        """alpha=0.0 should return the second color."""
        r, g, b = mix_colors("red", "blue", alpha=0.0)
        expected = matplotlib.colors.to_rgb("blue")
        assert b == pytest.approx(expected[2], abs=1e-4)

    def test_midpoint(self) -> None:
        """Midpoint should produce a blend."""
        r, g, b = mix_colors("black", "white", alpha=0.5)
        # Should be roughly gray
        assert r == pytest.approx(0.5, abs=0.15)
        assert g == pytest.approx(0.5, abs=0.15)
        assert b == pytest.approx(0.5, abs=0.15)

    # ------------------------------------------------------------------
    # OKLab-specific regression tests (added when mix_colors switched
    # from naïve gamma-sRGB blend to a perceptually oriented OKLab blend)
    # ------------------------------------------------------------------

    def test_oklab_midpoint_is_not_naive_rgb(self) -> None:
        """OKLab midpoint of red+blue must NOT equal naïve (0.5, 0, 0.5)."""
        r, g, b = mix_colors("red", "blue", alpha=0.5)
        naive_r, naive_g, naive_b = 0.5, 0.0, 0.5
        # At least one channel must differ meaningfully from the naive blend.
        differs = (
            abs(r - naive_r) > 0.02
            or abs(g - naive_g) > 0.02
            or abs(b - naive_b) > 0.02
        )
        assert differs, (
            f"mix_colors('red','blue',0.5) returned ({r:.4f},{g:.4f},{b:.4f}), "
            "indistinguishable from the naïve RGB midpoint — OKLab blend expected"
        )

    def test_alpha_one_returns_color1_oklab(self) -> None:
        """alpha=1.0 must round-trip back to color1 within OKLab float drift."""
        r, g, b = mix_colors("red", "blue", alpha=1.0)
        expected = matplotlib.colors.to_rgb("red")
        assert r == pytest.approx(expected[0], abs=0.02)
        assert g == pytest.approx(expected[1], abs=0.02)
        assert b == pytest.approx(expected[2], abs=0.02)

    def test_alpha_zero_returns_color2_oklab(self) -> None:
        """alpha=0.0 must round-trip back to color2 within OKLab float drift."""
        r, g, b = mix_colors("red", "blue", alpha=0.0)
        expected = matplotlib.colors.to_rgb("blue")
        assert r == pytest.approx(expected[0], abs=0.02)
        assert g == pytest.approx(expected[1], abs=0.02)
        assert b == pytest.approx(expected[2], abs=0.02)

    def test_idempotent_same_color_oklab(self) -> None:
        """mix_colors(c, c, 0.5) must return approximately c (idempotent)."""
        for color_name in ("red", "blue", "green", "#3a7ebf"):
            r, g, b = mix_colors(color_name, color_name, alpha=0.5)
            expected = matplotlib.colors.to_rgb(color_name)
            assert r == pytest.approx(expected[0], abs=0.02), color_name
            assert g == pytest.approx(expected[1], abs=0.02), color_name
            assert b == pytest.approx(expected[2], abs=0.02), color_name

    def test_returns_rgb_tuple(self) -> None:
        """Return value must be a 3-tuple of floats in [0, 1]."""
        result = mix_colors("red", "blue", alpha=0.5)
        assert len(result) == 3
        r, g, b = result
        for ch in (r, g, b):
            assert 0.0 <= ch <= 1.0


class TestPseudoAlpha:
    """Tests for pseudo_alpha()."""

    def test_full_opacity(self) -> None:
        """alpha=1.0 should return the original color."""
        r, g, b = pseudo_alpha("red", alpha=1.0)
        expected = matplotlib.colors.to_rgb("red")
        assert r == pytest.approx(expected[0], abs=1e-4)

    def test_zero_opacity(self) -> None:
        """alpha=0.0 should return background color (default white)."""
        r, g, b = pseudo_alpha("red", alpha=0.0)
        # Default background is white
        assert r == pytest.approx(1.0, abs=0.05)
        assert g == pytest.approx(1.0, abs=0.05)
        assert b == pytest.approx(1.0, abs=0.05)


class TestMixColorsAlphaValidation:
    """mix_colors rejects out-of-range alpha (2026-07 audit)."""

    @pytest.mark.parametrize("bad", [2.0, -1.0, float("nan"), float("inf")])
    def test_out_of_range_alpha_raises(self, bad: float) -> None:
        with pytest.raises(ValueError):
            mix_colors("red", "blue", bad)

    def test_boundary_alpha_ok(self) -> None:
        assert mix_colors("red", "blue", 0.0) is not None
        assert mix_colors("red", "blue", 1.0) is not None
