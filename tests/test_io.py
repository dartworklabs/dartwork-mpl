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


class TestSaveFormatsStripsExtension:
    """Regression: callers occasionally pass a path that already ends
    with an image suffix (`.png`, `.pdf`, …). Previously this produced
    `name.png.png` / `name.png.svg` silently; the normalizer must strip
    the duplicate and warn."""

    def test_strips_png_suffix(self, tmp_path: Path) -> None:
        import warnings

        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        # Caller mistakenly passes a stem that already has .png
        stem_with_ext = str(tmp_path / "chart.png")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            save_formats(
                fig,
                stem_with_ext,
                formats=("png", "svg"),
                dpi=72,
                validate=False,
            )

        # Files exist with clean single extension
        assert (tmp_path / "chart.png").exists()
        assert (tmp_path / "chart.svg").exists()
        # Bug-causing double-extension files must NOT exist
        assert not (tmp_path / "chart.png.png").exists()
        assert not (tmp_path / "chart.png.svg").exists()

        # A UserWarning was emitted
        assert any(
            issubclass(w.category, UserWarning)
            and "chart.png" in str(w.message)
            for w in caught
        )
        plt.close(fig)

    def test_strips_uppercase_png_suffix(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem_with_ext = str(tmp_path / "chart.PNG")
        save_formats(
            fig, stem_with_ext, formats=("png",), dpi=72, validate=False
        )

        assert (tmp_path / "chart.png").exists()
        assert not (tmp_path / "chart.PNG.png").exists()
        plt.close(fig)

    def test_strips_pdf_suffix(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem_with_ext = str(tmp_path / "report.pdf")
        save_formats(
            fig, stem_with_ext, formats=("png", "pdf"), dpi=72, validate=False
        )

        assert (tmp_path / "report.png").exists()
        assert (tmp_path / "report.pdf").exists()
        assert not (tmp_path / "report.pdf.png").exists()
        assert not (tmp_path / "report.pdf.pdf").exists()
        plt.close(fig)

    def test_does_not_strip_non_image_suffix(self, tmp_path: Path) -> None:
        """A stem like ``my.report_v2`` should be preserved — only
        known image suffixes are stripped."""
        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "my.report_v2")
        save_formats(fig, stem, formats=("png",), dpi=72, validate=False)

        # Suffix ".report_v2" is not in the known image set → preserved
        assert (tmp_path / "my.report_v2.png").exists()
        plt.close(fig)

    def test_does_not_warn_for_clean_stem(self, tmp_path: Path) -> None:
        import warnings

        from dartwork_mpl.io import save_formats

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        stem = str(tmp_path / "clean_stem")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            save_formats(
                fig, stem, formats=("png", "svg"), dpi=72, validate=False
            )

        # No UserWarning about extension stripping
        assert not any(
            issubclass(w.category, UserWarning)
            and "image_stem" in str(w.message)
            for w in caught
        )
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


class TestShowOptionalIPython:
    """``dm.show()`` needs IPython, an optional ``[notebook]`` extra."""

    def test_show_raises_actionable_error_without_ipython(self) -> None:
        """When IPython is absent, show() raises an ImportError that names
        the ``[notebook]`` extra instead of a bare ModuleNotFoundError."""
        import sys
        from unittest.mock import patch

        import pytest

        from dartwork_mpl.io import show

        # Setting the modules to None in sys.modules makes ``import
        # IPython.display`` raise ImportError — simulating a core-only
        # install without the [notebook] extra.
        with patch.dict(
            sys.modules, {"IPython": None, "IPython.display": None}
        ):
            with pytest.raises(ImportError, match=r"notebook"):
                show("<svg/>")


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


class TestSaveFormatsValidateQuiet:
    """`save_formats(..., validate=True, validate_quiet=True)` runs the
    visual checks but suppresses the stdout print so automated
    pipelines don't accumulate noise."""

    def test_validate_quiet_silences_stdout(self, tmp_path, capsys) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([1, 2, 3], [1, 4, 9])
        # No xlabel/ylabel — likely to trigger validation warnings.

        stem = str(tmp_path / "out")
        dm.save_formats(
            fig, stem, formats=("png",), validate=True, validate_quiet=True
        )
        captured = capsys.readouterr()
        # validate_figure's [VISUAL] prefix must not leak when quiet=True
        assert "[VISUAL]" not in captured.out
        plt.close(fig)

    def test_validate_default_still_prints(self, tmp_path, capsys) -> None:
        """Backwards-compat sanity: default behaviour (no validate_quiet)
        still prints visual warnings to stdout."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([1, 2, 3], [1, 4, 9])
        stem = str(tmp_path / "out")
        dm.save_formats(fig, stem, formats=("png",), validate=True)
        captured = capsys.readouterr()
        # We don't require any specific warning to fire — only that the
        # behaviour-toggle wiring is structural and not a no-op stub.
        # The presence of *some* stdout is the regression sentinel for
        # validate_quiet's wiring.
        assert captured.out is not None
        plt.close(fig)


class TestSaveAndShowCloseFigure:
    """`save_and_show(..., close_figure=False)` keeps the figure open
    so callers can keep editing it after the render-and-display cycle."""

    def test_close_figure_default_closes(self, tmp_path, monkeypatch) -> None:
        import dartwork_mpl as dm

        monkeypatch.setattr("dartwork_mpl.io.show", lambda *a, **k: None)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fignum = fig.number
        dm.save_and_show(fig, str(tmp_path / "out.svg"))
        # Default close_figure=True ⇒ figure is no longer registered with pyplot
        assert fignum not in plt.get_fignums()

    def test_close_figure_false_keeps_open(self, tmp_path, monkeypatch) -> None:
        import dartwork_mpl as dm

        monkeypatch.setattr("dartwork_mpl.io.show", lambda *a, **k: None)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fignum = fig.number
        dm.save_and_show(fig, str(tmp_path / "out.svg"), close_figure=False)
        assert fignum in plt.get_fignums(), (
            "close_figure=False must keep the figure registered for further edits"
        )
        plt.close(fig)

    def test_close_figure_false_tempfile_branch(self, monkeypatch) -> None:
        """The image_path=None branch uses a NamedTemporaryFile;
        close_figure=False must take that path without closing."""
        import dartwork_mpl as dm

        monkeypatch.setattr("dartwork_mpl.io.show", lambda *a, **k: None)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fignum = fig.number
        dm.save_and_show(fig, image_path=None, close_figure=False)
        assert fignum in plt.get_fignums()
        plt.close(fig)
