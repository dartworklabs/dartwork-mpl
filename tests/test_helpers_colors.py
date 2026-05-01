"""Smoke tests for ``dartwork_mpl.helpers.colors``."""

from __future__ import annotations

import pytest

from dartwork_mpl.helpers.colors import auto_select_colors


class TestAutoSelectColors:
    """Happy-path coverage of the categorical / sequential / diverging
    branches plus the highlight-index path.
    """

    def test_categorical_default(self) -> None:
        colors = auto_select_colors(3)
        assert len(colors) == 3
        # All entries should be Open-Color tokens.
        assert all(c.startswith("oc.") for c in colors)
        # No duplicates within a small categorical set.
        assert len(set(colors)) == 3

    def test_sequential_short(self) -> None:
        colors = auto_select_colors(4, color_type="sequential")
        assert len(colors) == 4
        assert all(c.startswith("oc.blue") for c in colors)

    def test_sequential_long(self) -> None:
        colors = auto_select_colors(8, color_type="sequential")
        assert len(colors) == 8
        assert all(c.startswith("oc.blue") for c in colors)

    def test_diverging(self) -> None:
        colors = auto_select_colors(5, color_type="diverging")
        assert len(colors) == 5
        # Diverging palette should mix red / blue / gray families.
        joined = " ".join(colors)
        assert "red" in joined
        assert "blue" in joined

    def test_repeats_when_oversubscribed(self) -> None:
        """Categorical palette has 8 colors; asking for 12 should
        repeat without raising."""
        colors = auto_select_colors(12)
        assert len(colors) == 12

    def test_highlight_index_changes_palette(self) -> None:
        plain = auto_select_colors(3)
        highlighted = auto_select_colors(3, highlight_index=1)
        # The highlighted result should differ from the plain one
        # because the helper darkens/lightens via ``5`` -> ``7``/``3``.
        assert highlighted != plain

    def test_invalid_color_type_raises(self) -> None:
        with pytest.raises(ValueError):
            auto_select_colors(3, color_type="bogus")  # type: ignore[arg-type]


class TestAutoSelectColorsEdgeCases:
    """Branches not covered by the happy-path tests."""

    def test_diverging_long_branch(self) -> None:
        """``n_series > 5`` for diverging picks the 7-stop palette."""
        colors = auto_select_colors(7, color_type="diverging")
        assert len(colors) == 7
        joined = " ".join(colors)
        # Long diverging palette pulls deeper red7/blue7.
        assert "red7" in joined or "red5" in joined
        assert "blue7" in joined or "blue5" in joined

    def test_n_series_one(self) -> None:
        """A single-series request returns one colour token."""
        colors = auto_select_colors(1)
        assert len(colors) == 1
        assert colors[0].startswith("oc.")

    def test_highlight_index_out_of_range_ignored(self) -> None:
        """Negative / out-of-range indices fall through unchanged."""
        plain = auto_select_colors(3)
        # Index >= n_series should be ignored (no IndexError, no rewrite).
        same = auto_select_colors(3, highlight_index=99)
        assert same == plain
        # Negative index should also short-circuit.
        same_neg = auto_select_colors(3, highlight_index=-1)
        assert same_neg == plain

    def test_highlight_darkens_target_lightens_others(self) -> None:
        """Highlight rewrites ``5`` -> ``7`` for target, ``5`` -> ``3``
        for everyone else."""
        result = auto_select_colors(3, highlight_index=0)
        # First entry is the highlighted -> darker (7).
        assert result[0].endswith("7")
        # Remaining entries are dimmed (3).
        for c in result[1:]:
            assert c.endswith("3")

    def test_categorical_repeated_palette_consistent(self) -> None:
        """When repeating, the cycle starts from the beginning each loop."""
        colors = auto_select_colors(10)
        # First 8 are the base palette; entries 8..9 should mirror 0..1.
        assert colors[8] == colors[0]
        assert colors[9] == colors[1]

    def test_zero_series_returns_empty(self) -> None:
        """A zero-series request returns an empty list (no exception)."""
        colors = auto_select_colors(0)
        assert colors == []
