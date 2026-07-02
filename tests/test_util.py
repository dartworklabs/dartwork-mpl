"""Tests for utility functions module."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.util import (
    fs,
    fw,
    lw,
    mix_colors,
    pseudo_alpha,
    save_formats,
    simple_layout,
)

matplotlib.use("Agg")


# ============================================================================
# Font / Line scaling
# ============================================================================


class TestFs:
    """Tests for fs() font size scaling."""

    def test_base_increment(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(0) == base
        assert fs(1) == base + 1
        assert fs(-1) == base - 1

    def test_large_offset(self) -> None:
        base = plt.rcParams["font.size"]
        assert fs(10) == base + 10


class TestFw:
    """Tests for fw() font weight scaling."""

    def test_integer_weight(self) -> None:
        """fw(n) should return base weight + 100*n for int weights."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = 300
            assert fw(0) == 300
            assert fw(1) == 400
            assert fw(-1) == 200
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_normal(self) -> None:
        """fw() should map 'normal' to 400."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "normal"
            assert fw(0) == 400
            assert fw(1) == 500
        finally:
            plt.rcParams["font.weight"] = original

    def test_string_weight_bold(self) -> None:
        """fw() should map 'bold' to 700."""
        original = plt.rcParams["font.weight"]
        try:
            plt.rcParams["font.weight"] = "bold"
            assert fw(0) == 700
            assert fw(1) == 800
        finally:
            plt.rcParams["font.weight"] = original


class TestLw:
    """Tests for lw() line width scaling."""

    def test_base_increment(self) -> None:
        base = plt.rcParams["lines.linewidth"]
        assert lw(0) == base
        assert lw(1) == base + 1
        assert lw(-0.5) == base - 0.5


# ============================================================================
# Color mixing
# ============================================================================


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
    # from naïve gamma-sRGB blend to perceptually-uniform OKLab blend)
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


# ============================================================================
# Pseudo alpha
# ============================================================================


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


# ============================================================================
# Save formats
# ============================================================================


class TestSaveFormats:
    """Tests for save_formats()."""

    def test_creates_files(self, tmp_path: Path) -> None:
        """save_formats should create output files."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        out_path = tmp_path / "test_chart"
        save_formats(fig, str(out_path), formats=("png",), dpi=72)

        assert (tmp_path / "test_chart.png").exists()
        plt.close(fig)

    def test_multiple_formats(self, tmp_path: Path) -> None:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        out_path = tmp_path / "test_multi"
        save_formats(fig, str(out_path), formats=("png", "pdf"), dpi=72)

        assert (tmp_path / "test_multi.png").exists()
        assert (tmp_path / "test_multi.pdf").exists()
        plt.close(fig)


# ============================================================================
# Simple layout
# ============================================================================


class TestSimpleLayout:
    """Tests for simple_layout()."""

    def test_does_not_crash(self) -> None:
        """simple_layout should not raise on a basic figure."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        # Should not raise
        simple_layout(fig)
        plt.close(fig)

    def test_multisubplot(self) -> None:
        """simple_layout should handle multi-subplot figures."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])
        simple_layout(fig)
        plt.close(fig)


# ============================================================================
# Set decimal
# ============================================================================


class TestSetDecimal:
    """Tests for set_decimal()."""

    def test_x_decimal(self) -> None:
        from dartwork_mpl.util import set_decimal

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()  # Ensure ticks are set
        set_decimal(ax, xn=2)
        labels = [t.get_text() for t in ax.get_xticklabels()]
        # Should contain decimal formatted labels
        assert any("." in label for label in labels if label)
        plt.close(fig)

    def test_y_decimal(self) -> None:
        from dartwork_mpl.util import set_decimal

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()
        set_decimal(ax, yn=1)
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert any("." in label for label in labels if label)
        plt.close(fig)

    def test_both_decimals(self) -> None:
        from dartwork_mpl.util import set_decimal

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()
        set_decimal(ax, xn=3, yn=0)
        plt.close(fig)


# ============================================================================
# Make offset
# ============================================================================


class TestMakeOffset:
    """Tests for make_offset()."""

    def test_creates_transform(self) -> None:
        from matplotlib.transforms import ScaledTranslation

        from dartwork_mpl.util import make_offset

        fig, _ax = plt.subplots()
        offset = make_offset(4, -4, fig)
        assert isinstance(offset, ScaledTranslation)
        plt.close(fig)

    def test_zero_offset(self) -> None:
        from dartwork_mpl.util import make_offset

        fig, _ax = plt.subplots()
        offset = make_offset(0, 0, fig)
        assert offset is not None
        plt.close(fig)


class TestMixColorsAlphaValidation:
    """mix_colors rejects out-of-range alpha (2026-07 audit)."""

    @pytest.mark.parametrize("bad", [2.0, -1.0, float("nan"), float("inf")])
    def test_out_of_range_alpha_raises(self, bad: float) -> None:
        with pytest.raises(ValueError):
            mix_colors("red", "blue", bad)

    def test_boundary_alpha_ok(self) -> None:
        assert mix_colors("red", "blue", 0.0) is not None
        assert mix_colors("red", "blue", 1.0) is not None
