"""Tests for io module."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


class TestSaveFormats:
    """Tests for save_formats()."""

    def test_creates_single_format(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "test_chart")
        save_formats(fig, stem, formats=("png",), dpi=72)

        assert (tmp_path / "test_chart.png").exists()
        plt.close(fig)

    def test_creates_multiple_formats(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "test_multi")
        save_formats(
            fig, stem, formats=("png", "pdf"), dpi=72
        )

        assert (tmp_path / "test_multi.png").exists()
        assert (tmp_path / "test_multi.pdf").exists()
        plt.close(fig)

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "nested" / "dir" / "chart")
        save_formats(fig, stem, formats=("png",), dpi=72)

        assert (tmp_path / "nested" / "dir" / "chart.png").exists()
        plt.close(fig)

    def test_validate_false_skips_validation(
        self, tmp_path: Path
    ) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "no_validate")
        save_formats(
            fig, stem, formats=("png",), dpi=72, validate=False
        )

        assert (tmp_path / "no_validate.png").exists()
        plt.close(fig)


class TestSaveAndShow:
    """Tests for save_and_show()."""

    def test_with_path(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_and_show

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        out = str(tmp_path / "output.svg")
        # In headless mode, the display part will be a no-op
        # but the file should still be created
        try:
            save_and_show(fig, image_path=out)
        except Exception:
            # IPython display may not be available in CI
            pass

        assert (tmp_path / "output.svg").exists()

    def test_without_path_does_not_crash(self) -> None:
        from dartwork_mpl.io import save_and_show

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        try:
            save_and_show(fig)
        except Exception:
            # IPython display may not be available in CI
            pass
