"""Value equality / hashing (#233) and gamut introspection (#240).

Covers the 0.4.3 minimal fixes:

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
        # (0.7, 0.40, 30) is far outside sRGB — to_hex clamps to #ff0000.
        assert dm.Color.from_oklch(0.7, 0.40, 30).in_gamut() is False

    def test_hex_primary_is_in_gamut(self) -> None:
        assert dm.Color("#ff0000").in_gamut() is True

    def test_in_gamut_returns_bool(self) -> None:
        assert isinstance(dm.Color.from_oklch(0.7, 0.05, 30).in_gamut(), bool)
