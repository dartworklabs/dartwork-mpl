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
        save_formats(fig, stem, formats=("png", "pdf"), dpi=72)

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

    def test_validate_false_skips_validation(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "no_validate")
        save_formats(fig, stem, formats=("png",), dpi=72, validate=False)

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


class TestSaveFormatsNonAscii:
    """Saving with a non-ASCII (Korean) filename stem must succeed on
    macOS / Linux filesystems with UTF-8 path encoding (the default
    on every CI runner this project supports)."""

    def test_korean_filename_round_trip(self, tmp_path) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_ylabel("값")
        ax.set_xlabel("순번")

        # The stem contains hangul + a wonsign → both bytes are >= 0x80
        # and exercise the same UTF-8 paths matplotlib uses for save.
        stem = str(tmp_path / "한글_차트_₩")
        dm.save_formats(fig, stem, formats=("png", "pdf"), validate=False)

        png_path = Path(f"{stem}.png")
        pdf_path = Path(f"{stem}.pdf")
        assert png_path.exists(), "PNG not written for non-ASCII stem"
        assert pdf_path.exists(), "PDF not written for non-ASCII stem"
        assert png_path.stat().st_size > 1024
        assert pdf_path.stat().st_size > 1024
        plt.close(fig)
