"""Tests for cmap module."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

from dartwork_mpl.cmap import _parse_colormap, ensure_loaded


class TestEnsureLoaded:
    """Tests for ensure_loaded()."""

    def test_does_not_crash(self) -> None:
        ensure_loaded()

    def test_idempotent(self) -> None:
        """Calling ensure_loaded() twice should not raise."""
        ensure_loaded()
        ensure_loaded()

    def test_registers_dm_colormaps(self) -> None:
        """After loading, dm.* colormaps should exist."""
        ensure_loaded()
        cmap_names = [
            name for name in mpl.colormaps if name.startswith("dm.")
        ]
        assert len(cmap_names) > 0


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
        assert cmap.name.startswith("dm.")
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
