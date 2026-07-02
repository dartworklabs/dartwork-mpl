"""Tests for dartwork_mpl.explore — palette / colormap discovery + preview.

``explore`` is a public module (`dm.list_palettes`, `dm.list_colormaps`,
`dm.show_palette`) that was effectively untested (#236, domain G). The
four diagnostics re-exports (`classify_colormap`, `plot_colormaps`,
`plot_colors`, `plot_fonts`) are covered by test_diagnostics; this file
covers the explore-specific discovery helpers and `show_palette`.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.explore import list_colormaps, list_palettes, show_palette


class TestListPalettes:
    def test_returns_sorted_unique_names(self) -> None:
        palettes = list_palettes()
        assert isinstance(palettes, list)
        assert palettes == sorted(palettes)
        assert len(palettes) == len(set(palettes))

    def test_includes_known_palette_families(self) -> None:
        palettes = list_palettes()
        # Open Color and Tailwind families are always registered.
        assert any(p.startswith("oc.") for p in palettes)
        assert any(p.startswith("tw.") for p in palettes)

    def test_entries_have_prefix_dot_name_shape(self) -> None:
        for p in list_palettes():
            assert "." in p
            prefix, name = p.split(".", 1)
            assert prefix and name
            # The family name must not carry a trailing shade number.
            assert not name[-1].isdigit()

    def test_includes_multiword_dc_palettes(self) -> None:
        """Multi-word snake_case dc palettes (teal_indigo, teal_accent, …)
        must appear in discovery — the underscore-blind regex used to drop
        them even though ``get_palette`` resolves them fine."""
        palettes = list_palettes()
        for name in ("dc.teal_indigo", "dc.teal_accent", "dc.warm_gray"):
            assert name in palettes, f"{name} missing from list_palettes()"


class TestListColormaps:
    def test_only_dartwork_colormaps(self) -> None:
        cmaps = list_colormaps()
        assert cmaps == sorted(cmaps)
        assert cmaps  # dc.* colormaps are registered
        assert all(c.startswith("dc.") for c in cmaps)

    def test_excludes_reversed_by_default(self) -> None:
        assert all(not c.endswith("_r") for c in list_colormaps())

    def test_include_reversed_adds_more(self) -> None:
        base = list_colormaps()
        with_rev = list_colormaps(include_reversed=True)
        assert len(with_rev) >= len(base)
        assert any(c.endswith("_r") for c in with_rev)


class TestShowPalette:
    def test_renders_known_palette(self) -> None:
        # Should build + show a figure without raising. Patch plt.show so
        # the Agg backend doesn't try to display.
        shown = {"n": 0}
        original = plt.show

        def _fake_show(*_a, **_k) -> None:
            shown["n"] += 1

        plt.show = _fake_show  # type: ignore[assignment]
        try:
            name = next(p for p in list_palettes() if p.startswith("oc."))
            show_palette(name)
        finally:
            plt.show = original  # type: ignore[assignment]
            plt.close("all")
        assert shown["n"] == 1

    def test_unknown_palette_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            show_palette("zz.definitely-not-a-real-palette")


class TestListPalettesNoDeprecatedAliases:
    """list_palettes must not surface deprecated dm.* aliases (2026-07 audit)."""

    def test_no_dm_prefix(self) -> None:
        import dartwork_mpl as dm

        assert not [
            p for p in dm.explore.list_palettes() if p.startswith("dm.")
        ]
