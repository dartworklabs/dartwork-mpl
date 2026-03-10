"""Tests for cmap module."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import pytest
import matplotlib.pyplot as plt
import dartwork_mpl.cmap as dm

from dartwork_mpl.cmap import _parse_colormap, ensure_loaded

# The 16 curated colormaps (no _r variants).
EXPECTED_DC_NAMES = {
    # Sequential Single-Hue
    "obsidian", "sapphire", "emerald", "ruby", "amethyst", "topaz", "graphite", "coral",
    # Sequential Multi-Hue
    "aurora", "sunset_glow", "plasma_arc", "spring_bloom", "deep_sea", "autumn_leaf", "nebula_dust", "tropical_fruit",
    # Diverging
    "ice_fire", "earth_sky", "teal_rose", "purple_lime", "navy_gold", "forest_brick", "magenta_cyan", "slate_orange",
    # Cyclical
    "twilight_oklch", "phase_wheel",
    # Discrete
    "vivid", "lucid", "chalk",
}

EXPECTED_DC_CMAPS = set()
for name in EXPECTED_DC_NAMES:
    EXPECTED_DC_CMAPS.add(f"dc.{name}")
    EXPECTED_DC_CMAPS.add(f"dc.{name}_r")

assert len(EXPECTED_DC_NAMES) == 29
assert len(EXPECTED_DC_CMAPS) == 58


@pytest.fixture(scope="module", autouse=True)
def _load_colormaps() -> None:
    """Ensure colormaps are loaded once for all tests in this module."""
    ensure_loaded()


class TestEnsureLoaded:
    """Tests for ensure_loaded()."""

    def test_does_not_crash(self) -> None:
        # This is covered by the fixture, but good to have a direct test too.
        ensure_loaded()

    def test_idempotent(self) -> None:
        """Calling ensure_loaded() twice should not raise."""
        ensure_loaded()
        ensure_loaded()

    def test_registers_exactly_29_dc_colormaps(self) -> None:
        """After loading, exactly 29 dc.* colormaps (non-reversed) should exist."""
        dc_names = {
            name for name in mpl.colormaps
            if name.startswith("dc.") and not name.endswith("_r")
        }
        assert dc_names == EXPECTED_DC_NAMES, (
            f"Missing: {EXPECTED_DC_NAMES - dc_names}, "
            f"Extra: {dc_names - EXPECTED_DC_NAMES}"
        )

    def test_reversed_variants_exist(self) -> None:
        """Every dc.* cmap should have a dc.*_r reversed variant."""
        for name in EXPECTED_DC_NAMES:
            assert f"dc.{name}_r" in mpl.colormaps, (
                f"Reversed variant dc.{name}_r not found"
            )

    def test_cmap_count_and_names(self) -> None:
        """Verify exactly 58 `dc.*` colormaps exist (29 base + 29 reversed)."""
        # 1. Get all colormaps currently registered in Matplotlib
        all_mpl_cmaps = set(plt.colormaps())

        # 2. Filter for only those starting with 'dc.'
        dc_cmaps_registered = {name for name in all_mpl_cmaps if name.startswith("dc.")}

        # 3. Assert the count is exactly 58
        assert len(dc_cmaps_registered) == 58, (
            f"Expected exactly 58 'dc.' colormaps, but found {len(dc_cmaps_registered)}."
        )
        assert dc_cmaps_registered == EXPECTED_DC_CMAPS, (
            f"Missing: {EXPECTED_DC_CMAPS - dc_cmaps_registered}, "
            f"Extra: {dc_cmaps_registered - EXPECTED_DC_CMAPS}"
        )

    def test_discrete_cmap_colors(self) -> None:
        """Test that the discrete (categorical) maps have exactly 8 colors."""
        discrete_names = ["vivid", "lucid", "chalk"]
        for name in discrete_names:
            cmap = dm.cmap(f"dc.{name}")
            assert isinstance(cmap, mpl.colors.ListedColormap)
            assert len(cmap.colors) == 8, f"Expected 8 colors for dc.{name}, got {len(cmap.colors)}"


class TestParseColormap:
    """Tests for _parse_colormap()."""

    def test_parse_existing_file(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return  # skip if no cmap files

        cmap = _parse_colormap(txt_files[0])
        assert cmap.name.startswith("dc.")
        assert len(cmap.colors) > 0

    def test_parse_reverse(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return

        cmap = _parse_colormap(txt_files[0], reverse=True)
        assert cmap.name.endswith("_r")

    def test_reverse_has_flipped_colors(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return

        cmap_fwd = _parse_colormap(txt_files[0], reverse=False)
        cmap_rev = _parse_colormap(txt_files[0], reverse=True)
        assert cmap_fwd.colors[0] == cmap_rev.colors[-1]
        assert cmap_fwd.colors[-1] == cmap_rev.colors[0]

    def test_file_count_is_16(self) -> None:
        """asset/cmap/ should contain exactly 16 .txt files."""
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        assert len(txt_files) == 16, (
            f"Expected 16 .txt files, got {len(txt_files)}: "
            f"{sorted(f.name for f in txt_files)}"
        )
