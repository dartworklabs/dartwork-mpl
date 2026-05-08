"""Tests for Color View classes (OklabView, OklchView, RgbView)."""

import pytest

from dartwork_mpl.colors import Color


class TestOklabView:
    """Tests for OklabView class."""

    def test_attribute_access(self) -> None:
        """Test attribute-based access to OKLab coordinates."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        assert color.oklab.L == 0.7
        assert color.oklab.a == 0.1
        assert color.oklab.b == 0.2

    def test_unpacking(self) -> None:
        """Test unpacking OKLab coordinates."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        L, a, b = color.oklab

        assert L == 0.7
        assert a == 0.1
        assert b == 0.2

    def test_index_access(self) -> None:
        """Test index-based access to OKLab coordinates."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        assert color.oklab[0] == 0.7
        assert color.oklab[1] == 0.1
        assert color.oklab[2] == 0.2

    def test_index_out_of_range(self) -> None:
        """Test that index out of range raises IndexError."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        with pytest.raises(IndexError):
            _ = color.oklab[3]

    def test_length(self) -> None:
        """Test that OklabView has length 3."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        assert len(color.oklab) == 3

    def test_writing_assignment(self) -> None:
        """Test writing with assignment operator (=)."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        color.oklab.L = 0.8
        assert color.oklab.L == 0.8

        color.oklab.a = 0.2
        assert color.oklab.a == 0.2

        color.oklab.b = 0.3
        assert color.oklab.b == 0.3

    def test_writing_add(self) -> None:
        """Test writing with += operator."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        color.oklab.L += 0.1
        assert abs(color.oklab.L - 0.8) < 1e-10

        color.oklab.a += 0.05
        assert abs(color.oklab.a - 0.15) < 1e-10

    def test_writing_subtract(self) -> None:
        """Test writing with -= operator."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        color.oklab.L -= 0.1
        assert abs(color.oklab.L - 0.6) < 1e-10

        color.oklab.a -= 0.05
        assert abs(color.oklab.a - 0.05) < 1e-10

    def test_writing_multiply(self) -> None:
        """Test writing with *= operator."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        color.oklab.b *= 1.5
        assert abs(color.oklab.b - 0.3) < 1e-10

    def test_writing_divide(self) -> None:
        """Test writing with /= operator."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        color.oklab.L /= 2.0
        assert abs(color.oklab.L - 0.35) < 1e-10

    def test_repr(self) -> None:
        """Test string representation."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        repr_str = repr(color.oklab)
        assert "OklabView" in repr_str
        assert "L=" in repr_str
        assert "a=" in repr_str
        assert "b=" in repr_str


class TestOklchView:
    """Tests for OklchView class."""

    def test_attribute_access(self) -> None:
        """Test attribute-based access to OKLCH coordinates."""
        color = Color.from_oklch(0.7, 0.2, 120)

        assert abs(color.oklch.L - 0.7) < 1e-10
        assert abs(color.oklch.C - 0.2) < 1e-10
        assert abs(color.oklch.h - 120.0) < 1e-10

    def test_unpacking(self) -> None:
        """Test unpacking OKLCH coordinates."""
        color = Color.from_oklch(0.7, 0.2, 120)

        L, C, h = color.oklch

        assert abs(L - 0.7) < 1e-10
        assert abs(C - 0.2) < 1e-10
        assert abs(h - 120.0) < 1e-10

    def test_index_access(self) -> None:
        """Test index-based access to OKLCH coordinates."""
        color = Color.from_oklch(0.7, 0.2, 120)

        assert abs(color.oklch[0] - 0.7) < 1e-10
        assert abs(color.oklch[1] - 0.2) < 1e-10
        assert abs(color.oklch[2] - 120.0) < 1e-10

    def test_index_out_of_range(self) -> None:
        """Test that index out of range raises IndexError."""
        color = Color.from_oklch(0.7, 0.2, 120)

        with pytest.raises(IndexError):
            _ = color.oklch[3]

    def test_length(self) -> None:
        """Test that OklchView has length 3."""
        color = Color.from_oklch(0.7, 0.2, 120)

        assert len(color.oklch) == 3

    def test_writing_assignment(self) -> None:
        """Test writing with assignment operator (=)."""
        color = Color.from_oklch(0.7, 0.2, 120)

        color.oklch.L = 0.8
        assert abs(color.oklch.L - 0.8) < 1e-10

        color.oklch.C = 0.3
        assert abs(color.oklch.C - 0.3) < 1e-10

        color.oklch.h = 180.0
        assert abs(color.oklch.h - 180.0) < 1e-10

    def test_writing_add(self) -> None:
        """Test writing with += operator."""
        color = Color.from_oklch(0.7, 0.2, 120)

        color.oklch.C += 0.1
        assert abs(color.oklch.C - 0.3) < 1e-10

        color.oklch.h += 30.0
        assert abs(color.oklch.h - 150.0) < 1e-10

    def test_writing_multiply(self) -> None:
        """Test writing with *= operator."""
        color = Color.from_oklch(0.7, 0.2, 120)

        color.oklch.C *= 1.2
        assert abs(color.oklch.C - 0.24) < 1e-10

    def test_chroma_negative_raises_error(self) -> None:
        """Test that setting negative chroma raises ValueError."""
        color = Color.from_oklch(0.7, 0.2, 120)

        with pytest.raises(ValueError, match="Chroma must be >= 0"):
            color.oklch.C = -0.1

    def test_hue_normalization(self) -> None:
        """Test that hue is normalized to [0, 360)."""
        color = Color.from_oklch(0.7, 0.2, 120)

        color.oklch.h = 450.0
        assert abs(color.oklch.h - 90.0) < 1e-10

        color.oklch.h = -30.0
        assert abs(color.oklch.h - 330.0) < 1e-10

    def test_repr(self) -> None:
        """Test string representation."""
        color = Color.from_oklch(0.7, 0.2, 120)

        repr_str = repr(color.oklch)
        assert "OklchView" in repr_str
        assert "L=" in repr_str
        assert "C=" in repr_str
        assert "h=" in repr_str


class TestRgbView:
    """Tests for RgbView class."""

    def test_attribute_access(self) -> None:
        """Test attribute-based access to RGB coordinates."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        assert abs(color.rgb.r - 0.8) < 1e-6
        assert abs(color.rgb.g - 0.2) < 1e-6
        assert abs(color.rgb.b - 0.3) < 1e-6

    def test_unpacking(self) -> None:
        """Test unpacking RGB coordinates."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        r, g, b = color.rgb

        assert abs(r - 0.8) < 1e-6
        assert abs(g - 0.2) < 1e-6
        assert abs(b - 0.3) < 1e-6

    def test_index_access(self) -> None:
        """Test index-based access to RGB coordinates."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        assert abs(color.rgb[0] - 0.8) < 1e-6
        assert abs(color.rgb[1] - 0.2) < 1e-6
        assert abs(color.rgb[2] - 0.3) < 1e-6

    def test_index_out_of_range(self) -> None:
        """Test that index out of range raises IndexError."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        with pytest.raises(IndexError):
            _ = color.rgb[3]

    def test_length(self) -> None:
        """Test that RgbView has length 3."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        assert len(color.rgb) == 3

    def test_writing_assignment(self) -> None:
        """Test writing with assignment operator (=)."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        color.rgb.r = 0.9
        assert abs(color.rgb.r - 0.9) < 1e-6

        color.rgb.g = 0.3
        assert abs(color.rgb.g - 0.3) < 1e-6

    def test_writing_add(self) -> None:
        """Test writing with += operator."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        color.rgb.r += 0.1
        assert abs(color.rgb.r - 0.9) < 1e-6

    def test_writing_multiply(self) -> None:
        """Test writing with *= operator."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        color.rgb.g *= 1.5
        assert abs(color.rgb.g - 0.3) < 1e-6

    def test_clamping(self) -> None:
        """Test that RGB values are clamped to [0, 1]."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        color.rgb.r = 1.5
        assert color.rgb.r <= 1.0

        color.rgb.g = -0.1
        assert color.rgb.g >= 0.0

    def test_repr(self) -> None:
        """Test string representation."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        repr_str = repr(color.rgb)
        assert "RgbView" in repr_str
        assert "r=" in repr_str
        assert "g=" in repr_str
        assert "b=" in repr_str


class TestColorCopy:
    """Tests for Color.copy() method."""

    def test_copy_creates_new_instance(self) -> None:
        """Test that copy() creates a new Color instance."""
        color = Color.from_oklab(0.7, 0.1, 0.2)
        new_color = color.copy()

        # Verify they are different objects
        assert color is not new_color

        # Verify they have the same values
        assert abs(color.oklab.L - new_color.oklab.L) < 1e-10
        assert abs(color.oklab.a - new_color.oklab.a) < 1e-10
        assert abs(color.oklab.b - new_color.oklab.b) < 1e-10

    def test_copy_independence(self) -> None:
        """Test that modifying copy doesn't affect original."""
        color = Color.from_oklab(0.7, 0.1, 0.2)
        new_color = color.copy()

        # Modify the copy
        new_color.oklab.L += 0.1
        new_color.oklab.a = 0.3
        new_color.oklab.b *= 1.5

        # Verify original is unchanged
        assert abs(color.oklab.L - 0.7) < 1e-10
        assert abs(color.oklab.a - 0.1) < 1e-10
        assert abs(color.oklab.b - 0.2) < 1e-10

        # Verify copy is modified
        assert abs(new_color.oklab.L - 0.8) < 1e-10
        assert abs(new_color.oklab.a - 0.3) < 1e-10
        assert abs(new_color.oklab.b - 0.3) < 1e-10

    def test_copy_from_oklch(self) -> None:
        """Test copying a color created from OKLCH."""
        color = Color.from_oklch(0.7, 0.2, 120)
        new_color = color.copy()

        L, C, h = color.oklch
        L_new, C_new, h_new = new_color.oklch

        assert abs(L - L_new) < 1e-10
        assert abs(C - C_new) < 1e-10
        assert abs(h - h_new) < 1e-10

    def test_copy_from_rgb(self) -> None:
        """Test copying a color created from RGB."""
        color = Color.from_rgb(0.8, 0.2, 0.3)
        new_color = color.copy()

        r, g, b = color.rgb
        r_new, g_new, b_new = new_color.rgb

        assert abs(r - r_new) < 1e-10
        assert abs(g - g_new) < 1e-10
        assert abs(b - b_new) < 1e-10

    def test_copy_preserves_all_spaces(self) -> None:
        """Test that copy preserves values in all color spaces."""
        color = Color.from_oklab(0.7, 0.1, 0.2)
        new_color = color.copy()

        # Check OKLab
        L, a, b = color.to_oklab()
        L_new, a_new, b_new = new_color.to_oklab()
        assert abs(L - L_new) < 1e-10
        assert abs(a - a_new) < 1e-10
        assert abs(b - b_new) < 1e-10

        # Check OKLCH
        L, C, h = color.to_oklch()
        L_new, C_new, h_new = new_color.to_oklch()
        assert abs(L - L_new) < 1e-10
        assert abs(C - C_new) < 1e-10
        assert abs(h - h_new) < 1e-10

        # Check RGB
        r, g, b = color.to_rgb()
        r_new, g_new, b_new = new_color.to_rgb()
        assert abs(r - r_new) < 1e-10
        assert abs(g - g_new) < 1e-10
        assert abs(b - b_new) < 1e-10

        # Check hex
        assert color.to_hex() == new_color.to_hex()


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing API."""

    def test_oklab_backward_compatibility(self) -> None:
        """Test that to_oklab() and oklab view give same results."""
        color = Color.from_oklab(0.7, 0.1, 0.2)

        L_old, a_old, b_old = color.to_oklab()
        L_new, a_new, b_new = color.oklab

        assert abs(L_old - L_new) < 1e-10
        assert abs(a_old - a_new) < 1e-10
        assert abs(b_old - b_new) < 1e-10

    def test_oklch_backward_compatibility(self) -> None:
        """Test that to_oklch() and oklch view give same results."""
        color = Color.from_oklch(0.7, 0.2, 120)

        L_old, C_old, h_old = color.to_oklch()
        L_new, C_new, h_new = color.oklch

        assert abs(L_old - L_new) < 1e-10
        assert abs(C_old - C_new) < 1e-10
        assert abs(h_old - h_new) < 1e-10

    def test_rgb_backward_compatibility(self) -> None:
        """Test that to_rgb() and rgb view give same results."""
        color = Color.from_rgb(0.8, 0.2, 0.3)

        r_old, g_old, b_old = color.to_rgb()
        r_new, g_new, b_new = color.rgb

        assert abs(r_old - r_new) < 1e-10
        assert abs(g_old - g_new) < 1e-10
        assert abs(b_old - b_new) < 1e-10
