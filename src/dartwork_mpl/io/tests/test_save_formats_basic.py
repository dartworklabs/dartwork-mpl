"""save_formats writes one file per requested format."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from dartwork_mpl.io import save_formats


class TestSaveFormats:
    """Tests for save_formats()."""

    def test_creates_files(self, tmp_path: Path) -> None:
        """save_formats should create output files."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        out_path = tmp_path / "test_chart"
        save_formats(fig, str(out_path), formats=("png",), dpi=72)

        assert (tmp_path / "test_chart.png").exists()
        plt.close(fig)

    def test_multiple_formats(self, tmp_path: Path) -> None:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        out_path = tmp_path / "test_multi"
        save_formats(fig, str(out_path), formats=("png", "pdf"), dpi=72)

        assert (tmp_path / "test_multi.png").exists()
        assert (tmp_path / "test_multi.pdf").exists()
        plt.close(fig)
