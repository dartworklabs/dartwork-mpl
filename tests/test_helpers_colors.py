"""Smoke tests for ``dartwork_mpl.helpers.colors``."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pytest

from dartwork_mpl.helpers.colors import make_palette


class TestMakePalette:
    """Happy-path coverage of the categorical / sequential / diverging
    branches plus the highlight path.
    """

    def test_categorical_default(self) -> None:
        colors = make_palette(3)
        assert len(colors) == 3
        # All entries should be Open-Color tokens.
        assert all(c.startswith("oc.") for c in colors)
        # No duplicates within a small categorical set.
        assert len(set(colors)) == 3

    def test_sequential_short(self) -> None:
        colors = make_palette(4, kind="sequential")
        assert len(colors) == 4
        assert all(c.startswith("oc.blue") for c in colors)

    def test_sequential_long(self) -> None:
        colors = make_palette(8, kind="sequential")
        assert len(colors) == 8
        assert all(c.startswith("oc.blue") for c in colors)

    def test_diverging(self) -> None:
        colors = make_palette(5, kind="diverging")
        assert len(colors) == 5
        # Diverging palette should mix red / blue / gray families.
        joined = " ".join(colors)
        assert "red" in joined
        assert "blue" in joined

    def test_repeats_when_oversubscribed(self) -> None:
        """Categorical palette has 8 colors; asking for 12 should
        repeat without raising."""
        colors = make_palette(12)
        assert len(colors) == 12

    def test_highlight_changes_palette(self) -> None:
        plain = make_palette(3)
        highlighted = make_palette(3, highlight=1)
        # The highlighted result should differ from the plain one
        # because the helper darkens/lightens via ``5`` -> ``7``/``3``.
        assert highlighted != plain

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError):
            make_palette(3, kind="bogus")  # type: ignore[arg-type]


class TestMakePaletteEdgeCases:
    """Branches not covered by the happy-path tests."""

    def test_diverging_long_branch(self) -> None:
        """``n > 5`` for diverging picks the 7-stop palette."""
        colors = make_palette(7, kind="diverging")
        assert len(colors) == 7
        joined = " ".join(colors)
        # Long diverging palette pulls deeper red7/blue7.
        assert "red7" in joined or "red5" in joined
        assert "blue7" in joined or "blue5" in joined

    def test_n_one(self) -> None:
        """A single-series request returns one colour token."""
        colors = make_palette(1)
        assert len(colors) == 1
        assert colors[0].startswith("oc.")

    def test_highlight_out_of_range_ignored(self) -> None:
        """Negative / out-of-range indices fall through unchanged."""
        plain = make_palette(3)
        # Index >= n should be ignored (no IndexError, no rewrite).
        same = make_palette(3, highlight=99)
        assert same == plain
        # Negative index should also short-circuit.
        same_neg = make_palette(3, highlight=-1)
        assert same_neg == plain

    def test_highlight_darkens_target_lightens_others(self) -> None:
        """Highlight steps the target's weight index up (darker) and every
        other's down (lighter). For the categorical base (shade 5) that is
        5 -> 7 for the target and 5 -> 3 for the rest."""
        result = make_palette(3, highlight=0)
        # First entry is the highlighted -> darker (7).
        assert result[0].endswith("7")
        # Remaining entries are dimmed (3).
        for c in result[1:]:
            assert c.endswith("3")

    def test_highlight_sequential_emphasizes_chosen_series(self) -> None:
        """Sequential palette names (``oc.blue3..7``) carry no fixed ``5``,
        so the old string-replace highlighted the wrong series. Weight-index
        stepping must darken exactly the chosen index and keep valid names."""
        seq = make_palette(3, kind="sequential", highlight=1)
        assert all(c.startswith("oc.blue") and c[-1].isdigit() for c in seq)
        shades = [int(c[-1]) for c in seq]
        assert shades[1] == max(shades)  # chosen index is darkest
        assert shades[1] > shades[0] and shades[1] > shades[2]

    def test_highlight_diverging_no_name_corruption(self) -> None:
        """Diverging names include ``oc.gray5``; a blind ``5`` -> ``7``
        replace would corrupt it. Only the highlighted index is darkened."""
        div = make_palette(5, kind="diverging", highlight=0)
        assert all(
            any(c.startswith(f"oc.{fam}") for fam in ("red", "blue", "gray"))
            and c[-1].isdigit()
            for c in div
        )
        shades = [int(c[-1]) for c in div]
        assert shades[0] == max(shades)  # highlighted index 0 is darkest

    def test_categorical_repeated_palette_consistent(self) -> None:
        """When repeating, the cycle starts from the beginning each loop."""
        colors = make_palette(10)
        # First 8 are the base palette; entries 8..9 should mirror 0..1.
        assert colors[8] == colors[0]
        assert colors[9] == colors[1]

    def test_zero_returns_empty(self) -> None:
        """A zero-series request returns an empty list (no exception)."""
        colors = make_palette(0)
        assert colors == []
