"""Tests for cmap module."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

from dartwork_mpl.cmap import _parse_colormap, ensure_loaded

# The 16 curated colormaps (no _r variants).
EXPECTED_CMAPS: set[str] = {
    # Sequential Single-Hue
    "dc.steel", "dc.flame", "dc.monochrome", "dc.lajolla",
    # Sequential Multi-Hue
    "dc.ocean", "dc.sunset", "dc.thermal", "dc.batlow",
    # Diverging
    "dc.balance", "dc.earth", "dc.delta", "dc.berlin",
    # Cyclical
    "dc.twilight_oklch",
    # Discrete / Categorical
    "dc.bold", "dc.muted", "dc.pastel",
}


class TestEnsureLoaded:
    """Tests for ensure_loaded()."""

    def test_does_not_crash(self) -> None:
        ensure_loaded()

    def test_idempotent(self) -> None:
        """Calling ensure_loaded() twice should not raise."""
        ensure_loaded()
        ensure_loaded()

    def test_registers_exactly_16_dc_colormaps(self) -> None:
        """After loading, exactly 16 dc.* colormaps should exist."""
        ensure_loaded()
        dc_names = {
            name for name in mpl.colormaps
            if name.startswith("dc.") and not name.endswith("_r")
        }
        assert dc_names == EXPECTED_CMAPS, (
            f"Missing: {EXPECTED_CMAPS - dc_names}, "
            f"Extra: {dc_names - EXPECTED_CMAPS}"
        )

    def test_reversed_variants_exist(self) -> None:
        """Every dc.* cmap should have a dc.*_r reversed variant."""
        ensure_loaded()
        for name in EXPECTED_CMAPS:
            assert f"{name}_r" in mpl.colormaps, (
                f"Reversed variant {name}_r not found"
            )

    def test_total_dc_count_is_32(self) -> None:
        """16 normal + 16 reversed = 32 total dc.* colormaps."""
        ensure_loaded()
        dc_all = [
            name for name in mpl.colormaps
            if name.startswith("dc.")
        ]
        assert len(dc_all) == 32


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
