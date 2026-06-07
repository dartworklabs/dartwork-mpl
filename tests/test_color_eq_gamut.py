"""Value equality / hashing (#233) and gamut introspection (#240).

Covers the 0.5.0 minimal fixes:

- ``Color.__eq__`` / ``Color.__hash__`` by OKLab coordinates so equal
  colors compare and hash equal (previously identity-based: equal colors
  were ``!=`` and dict/set membership was id-keyed).
- ``Color.in_gamut`` so callers can detect out-of-gamut colors whose
  ``to_rgb`` per-channel clamp silently distorts the requested L/h.
"""

from __future__ import annotations

import dartwork_mpl as dm


class TestColorEquality:
    def test_equal_colors_compare_equal(self) -> None:
        assert dm.Color("#ff0000") == dm.Color("#ff0000")

    def test_different_colors_compare_unequal(self) -> None:
        assert dm.Color("#ff0000") != dm.Color("#00ff00")

    def test_equality_across_constructors(self) -> None:
        assert dm.Color.from_oklab(0.7, 0.1, 0.2) == dm.Color.from_oklab(
            0.7, 0.1, 0.2
        )

    def test_compare_with_non_color_is_false(self) -> None:
        assert (dm.Color("#ff0000") == "#ff0000") is False
        assert (dm.Color("#ff0000") != "#ff0000") is True

    def test_equal_colors_hash_equal(self) -> None:
        assert hash(dm.Color("#ff0000")) == hash(dm.Color("#ff0000"))

    def test_color_usable_in_set(self) -> None:
        colors = {dm.Color("#ff0000"), dm.Color("#ff0000"), dm.Color("#00ff00")}
        assert len(colors) == 2

    def test_color_usable_as_dict_key(self) -> None:
        mapping = {dm.Color("#ff0000"): "red"}
        assert mapping[dm.Color("#ff0000")] == "red"


class TestColorInGamut:
    def test_in_gamut_true_for_representable(self) -> None:
        assert dm.Color.from_oklch(0.7, 0.05, 30).in_gamut() is True

    def test_in_gamut_false_for_out_of_gamut(self) -> None:
        # (0.7, 0.40, 30) is far outside sRGB — to_rgb gamut-maps it
        # (chroma reduction holding L/h), so in_gamut reports False.
        assert dm.Color.from_oklch(0.7, 0.40, 30).in_gamut() is False

    def test_hex_primary_is_in_gamut(self) -> None:
        assert dm.Color("#ff0000").in_gamut() is True

    def test_in_gamut_returns_bool(self) -> None:
        assert isinstance(dm.Color.from_oklch(0.7, 0.05, 30).in_gamut(), bool)


class TestGamutMapping:
    """``to_rgb`` maps out-of-gamut OKLCH colors by chroma reduction that
    holds lightness (L) and hue (h) fixed (#240), instead of the old
    per-channel clamp that drifted L/h."""

    def test_out_of_gamut_preserves_lightness_and_hue(self) -> None:
        # (0.7, 0.40, 30) is well outside sRGB. The per-channel clamp
        # used to land on #ff0000 (OKLCH ~0.628 / 29.2) — a shifted L.
        c = dm.Color.from_oklch(0.7, 0.40, 30)
        r, g, b = c.to_rgb()
        back_l, back_c, back_h = dm.Color.from_rgb(r, g, b).to_oklch()
        assert abs(back_l - 0.7) < 0.02, f"L drifted: {back_l}"
        assert abs(back_h - 30.0) < 2.0, f"h drifted: {back_h}"
        assert back_c < 0.40, f"chroma not reduced: {back_c}"

    def test_mapped_color_is_in_gamut(self) -> None:
        # The mapped result must itself be representable in sRGB.
        c = dm.Color.from_oklch(0.7, 0.40, 30)
        assert dm.Color.from_rgb(*c.to_rgb()).in_gamut() is True

    def test_in_gamut_color_is_unchanged(self) -> None:
        # Representable colors must round-trip exactly (mapping is a no-op
        # inside the gamut — no regression for the common case).
        c = dm.Color.from_oklch(0.7, 0.05, 30)
        assert c.in_gamut() is True
        back_l, back_c, back_h = dm.Color.from_rgb(*c.to_rgb()).to_oklch()
        assert abs(back_l - 0.7) < 1e-3
        assert abs(back_c - 0.05) < 1e-3
        assert abs(back_h - 30.0) < 0.5

    def test_hex_primary_unaffected(self) -> None:
        # An sRGB primary is in gamut: to_hex is the exact round-trip.
        assert dm.Color("#ff0000").to_hex() == "#ff0000"

    def test_extreme_lightness_clamps_without_error(self) -> None:
        # L outside [0, 1] can't be represented even at C=0; the final
        # clamp must still yield a valid hex rather than crash.
        assert dm.Color.from_oklch(1.5, 0.10, 30).to_hex().startswith("#")
        assert dm.Color.from_oklch(-0.2, 0.10, 30).to_hex().startswith("#")
