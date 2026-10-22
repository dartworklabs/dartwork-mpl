"""Tests for Color API — cspace interpolation and convenience constructors."""

from __future__ import annotations

import colorsys

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl as dm
from dartwork_mpl._colors import Color, cspace, hex, oklab, oklch, rgb


def _relative_luminance(color: str) -> float:
    r, g, b = mcolors.to_rgb(color)

    def linearize(channel: float) -> float:
        return (
            channel / 12.92
            if channel <= 0.03928
            else ((channel + 0.055) / 1.055) ** 2.4
        )

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(foreground: str, background: str) -> float:
    hi, lo = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (hi + 0.05) / (lo + 0.05)


def _hue(color: str) -> float:
    r, g, b = mcolors.to_rgb(color)
    hue, _lightness, _saturation = colorsys.rgb_to_hls(r, g, b)
    return hue


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
# Contrast-aware ink helpers
# ============================================================================


class TestReadableTextColor:
    """Tests for choosing readable text color from candidate inks."""

    def test_dark_background_uses_light_ink(self) -> None:
        assert dm.readable_text_color("#111111") == "white"

    def test_light_background_uses_standard_dark_ink(self) -> None:
        assert dm.readable_text_color("#f7f7f7") == "black"

    def test_candidates_are_compared_by_contrast_ratio(self) -> None:
        result = dm.readable_text_color(
            "#777777", light="#bbbbbb", dark="#111111"
        )

        assert result == "#111111"
        assert _contrast_ratio(result, "#777777") > _contrast_ratio(
            "#bbbbbb", "#777777"
        )


class TestEnsureContrast:
    """Tests for minimal deterministic lightness adjustment."""

    def test_passing_color_is_returned_unchanged(self) -> None:
        original = "#112233"

        assert dm.ensure_contrast(original, "white") == original

    def test_light_color_against_white_is_darkened_to_minimum_ratio(
        self,
    ) -> None:
        original = "#d9d97a"

        adjusted = dm.ensure_contrast(original, "white", min_ratio=4.5)

        assert adjusted != original
        assert _contrast_ratio(adjusted, "white") >= 4.5
        assert mcolors.to_rgb(adjusted)[0] < mcolors.to_rgb(original)[0]
        assert _hue(adjusted) == pytest.approx(_hue(original), abs=0.01)

    def test_adjustment_is_deterministic(self) -> None:
        first = dm.ensure_contrast("#d9d97a", "white", min_ratio=4.5)
        second = dm.ensure_contrast("#d9d97a", "white", min_ratio=4.5)

        assert first == second


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


# ============================================================================
# from_rgb input validation (#236, domain E)
# ============================================================================


class TestFromRgbValidation:
    """from_rgb rejects malformed input instead of silently producing an
    out-of-gamut color (the old range heuristic divided by 255 blindly)."""

    @pytest.mark.parametrize(
        "rgb",
        [
            (float("nan"), 0.5, 0.5),
            (float("inf"), 0.5, 0.5),
            (0.5, float("nan"), 0.5),
        ],
    )
    def test_non_finite_rejected(self, rgb) -> None:
        with pytest.raises(ValueError, match="finite"):
            Color.from_rgb(*rgb)

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Color.from_rgb(-1.0, 0.5, 0.5)

    def test_above_255_in_byte_mode_rejected(self) -> None:
        # One channel > 1.0 triggers 0-255 mode; a 300 then can't be a
        # valid byte value and must error, not normalize to > 1.0.
        with pytest.raises(ValueError, match="255"):
            Color.from_rgb(300.0, 0.5, 0.5)

    def test_fractional_mixed_into_byte_mode_rejected(self) -> None:
        # 255 triggers 0-255 mode, but 0.5 / 0.1 look like 0-1 unit values.
        # The ambiguous mix must error instead of silently dividing the
        # fractional channels by 255 (→ a near-black, distorted color).
        with pytest.raises(ValueError, match="not a mix"):
            Color.from_rgb(255, 0.5, 0.1)

    def test_byte_mode_accepts_zero_and_one(self) -> None:
        # 0 and 1 are valid byte values (not fractional 0-1 unit), so a
        # byte-mode call using them must still succeed, not get rejected by
        # the mixed-range guard.
        Color.from_rgb(255, 0, 1)

    def test_valid_byte_and_unit_agree(self) -> None:
        assert (
            Color.from_rgb(255, 107, 107).to_hex()
            == Color.from_rgb(1.0, 107 / 255, 107 / 255).to_hex()
        )


# ============================================================================
# from_oklab / from_oklch value-domain validation
# ============================================================================


class TestFromOklabOklchValidation:
    """OKLab/OKLCH constructors fail loud on out-of-domain input instead
    of silently rendering white (NaN) or flipping the hue (negative C)."""

    @pytest.mark.parametrize(
        "lab",
        [
            (float("nan"), 0.0, 0.0),
            (0.7, float("inf"), 0.0),
            (0.7, 0.0, float("nan")),
        ],
    )
    def test_from_oklab_non_finite_rejected(self, lab) -> None:
        with pytest.raises(ValueError, match="finite"):
            Color.from_oklab(*lab)

    def test_from_oklch_non_finite_component_rejected(self) -> None:
        # A NaN L propagates through the conversion and is caught by the
        # shared ``_from_oklab`` finiteness guard.
        with pytest.raises(ValueError, match="finite"):
            Color.from_oklch(float("nan"), 0.1, 120.0)

    def test_from_oklch_negative_chroma_rejected(self) -> None:
        # Negative chroma silently flips the hue; reject it to match the
        # OklchView.C setter contract.
        with pytest.raises(ValueError, match=">= 0"):
            Color.from_oklch(0.7, -0.1, 120.0)

    def test_from_oklch_zero_chroma_accepted(self) -> None:
        # C == 0 is the achromatic axis and must remain valid.
        Color.from_oklch(0.7, 0.0, 120.0)


# ============================================================================
# cspace accepts the same string forms as dm.color (#236, domain E)
# ============================================================================


class TestCspaceFunctionalStrings:
    """cspace routes string inputs through the unified Color parser, so
    rgb(...) / oklch(...) work — not just hex and palette names."""

    def test_oklch_string_endpoint(self) -> None:
        colors = cspace("oklch(0.7, 0.15, 30)", "#4ECDC4", n=5)
        assert len(colors) == 5
        assert all(isinstance(c, Color) for c in colors)

    def test_rgb_string_endpoint(self) -> None:
        colors = cspace("rgb(1, 0, 0)", "oklch(0.7, 0.15, 200)", n=4)
        assert len(colors) == 4


class TestCspaceAchromaticHue:
    """Achromatic endpoints must not inject a noise hue (2026-07 audit)."""

    def test_white_to_blue_stays_blue(self) -> None:
        ramp = cspace("white", "oc.blue9", n=5, space="oklch")
        mid = ramp[2].to_rgb()
        # Before the fix the midpoint was green/teal (g > b); a white->blue
        # tint ramp must keep blue dominant.
        assert mid[2] >= mid[1]

    def test_black_to_red_stays_red(self) -> None:
        ramp = cspace("black", "#ff0000", n=5, space="oklch")
        mid = ramp[2].to_rgb()
        assert mid[0] >= mid[1] and mid[0] >= mid[2]
