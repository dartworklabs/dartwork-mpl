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
