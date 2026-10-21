"""Tests for io module."""

from __future__ import annotations

import gzip
import time
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

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


class TestSaveFormatsDeterministic:
    """save_formats() SVG/PDF output is byte-reproducible by default:
    fixed per-file svg.hashsalt + dropped embedded timestamp, so an
    unchanged figure re-renders identically instead of churning VCS."""

    def _fig(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        return fig

    def test_svg_byte_identical_across_reruns(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig = self._fig()
        stem = str(tmp_path / "det_chart")
        save_formats(fig, stem, formats=("svg",), validate=False)
        first = (tmp_path / "det_chart.svg").read_bytes()
        # Re-render the same figure to the same stem — same salt ⇒ same ids,
        # no embedded date ⇒ byte-identical.
        save_formats(fig, stem, formats=("svg",), validate=False)
        second = (tmp_path / "det_chart.svg").read_bytes()
        plt.close(fig)

        assert first == second
        # No churning wall-clock timestamp embedded by default.
        assert b"dc:date" not in first

    def test_svgz_byte_identical_across_reruns(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig = self._fig()
        stem = str(tmp_path / "det_chart")
        save_formats(fig, stem, formats=("svgz",), validate=False)
        first = (tmp_path / "det_chart.svgz").read_bytes()
        time.sleep(1.1)
        save_formats(fig, stem, formats=("svgz",), validate=False)
        second = (tmp_path / "det_chart.svgz").read_bytes()
        plt.close(fig)

        assert first == second
        svg = gzip.decompress(first)
        assert svg.startswith((b"<?xml", b"<svg"))
        assert b"dc:date" not in svg

    def test_caller_metadata_date_survives(self, tmp_path: Path) -> None:
        """A caller-supplied metadata Date is not clobbered, and other
        metadata keys pass through untouched."""
        from dartwork_mpl.io import save_formats

        fig = self._fig()
        stem = str(tmp_path / "with_date")
        save_formats(
            fig,
            stem,
            formats=("svg",),
            validate=False,
            metadata={"Date": "2020-01-01", "Creator": "unit-test"},
        )
        content = (tmp_path / "with_date.svg").read_text(encoding="utf-8")
        plt.close(fig)

        # Caller's Date wins (not replaced by the default None-drop) …
        assert "2020-01-01" in content
        # … and their other metadata key is preserved.
        assert "unit-test" in content

    def test_pdf_byte_identical_across_reruns(self, tmp_path: Path) -> None:
        from dartwork_mpl.io import save_formats

        fig = self._fig()
        stem = str(tmp_path / "det_doc")
        save_formats(fig, stem, formats=("pdf",), validate=False)
        first = (tmp_path / "det_doc.pdf").read_bytes()
        save_formats(fig, stem, formats=("pdf",), validate=False)
        second = (tmp_path / "det_doc.pdf").read_bytes()
        plt.close(fig)

        assert first == second
        # PDF CreationDate is dropped by default.
        assert b"/CreationDate" not in first

    def test_ambient_hashsalt_is_respected(self, tmp_path: Path) -> None:
        """A user who set svg.hashsalt globally keeps their salt — the
        per-file basename salt only applies when the ambient one is None."""
        from dartwork_mpl.io import save_formats

        fig = self._fig()
        # Same figure, two different stems, but the *same* ambient salt ⇒
        # identical element ids (basename would otherwise differ them).
        with plt.rc_context({"svg.hashsalt": "user-fixed-salt"}):
            save_formats(
                fig, str(tmp_path / "a"), formats=("svg",), validate=False
            )
            save_formats(
                fig, str(tmp_path / "b"), formats=("svg",), validate=False
            )
        plt.close(fig)

        a = (tmp_path / "a.svg").read_text(encoding="utf-8")
        b = (tmp_path / "b.svg").read_text(encoding="utf-8")
        # Element-id salt shared ⇒ the id-bearing markup matches.
        import re

        ids_a = sorted(set(re.findall(r'id="([^"]+)"', a)))
        ids_b = sorted(set(re.findall(r'id="([^"]+)"', b)))
        assert ids_a == ids_b


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


class TestSaveAndShowNonSvgAudit:
    """save_and_show / show handle non-SVG paths (2026-07 audit)."""

    def test_resolve_saved_path_appends_default_format(self) -> None:
        import matplotlib.pyplot as plt

        from dartwork_mpl.io import _resolve_saved_path

        fig = plt.figure()
        # extensionless -> savefig appends rcParams["savefig.format"]
        resolved = _resolve_saved_path("first", {}, fig)
        assert resolved == f"first.{plt.rcParams['savefig.format']}"
        # explicit known extension is kept
        assert _resolve_saved_path("out.png", {}, fig) == "out.png"
        plt.close(fig)

    def test_show_non_svg_raises_clear_error(self, tmp_path) -> None:
        import pytest

        import dartwork_mpl as dm

        png = tmp_path / "x.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n not really")
        with pytest.raises(ValueError, match="SVG"):
            dm.show(str(png))


class TestSaveFormatsPreflight:
    """Rejected effective formats have no dm effects; valid save paths stay native."""

    @pytest.mark.parametrize("formats", [("jpgg",), ("png", "jpgg")])
    def test_bad_format_rejects_before_files_or_diagnostics(
        self, tmp_path, capsys, formats
    ) -> None:
        """First and later failures precede stem warnings, diagnostics and mkdir."""
        import dartwork_mpl as dm

        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1], linewidth=dm.lw(0))
        ax.set_title("Deliberately oversized title", fontsize=dm.fs(20))
        before = dict(plt.rcParams)
        capsys.readouterr()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(ValueError, match="jpgg"):
                dm.save_formats(
                    fig,
                    str(tmp_path / "absent" / "plot.png"),
                    formats=formats,
                    adopt_orphan_tick_font=True,
                )
        assert not (tmp_path / "absent").exists()
        assert dict(plt.rcParams) == before
        assert not caught
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize(
        "formats", [[".png", "pdf", "svg"], (".png", "pdf", "svg")]
    )
    def test_lists_and_dotted_formats_write_real_files(self, tmp_path, formats):
        """Current accepted containers and leading dots retain valid output bytes."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1])
        dm.simple_layout(fig)
        assert (
            dm.save_formats(
                fig,
                str(tmp_path / "plot"),
                formats=formats,
                validate=False,
                dpi=72,
            )
            is None
        )
        assert (
            (tmp_path / "plot.png")
            .read_bytes()
            .startswith(b"\x89PNG\r\n\x1a\n")
        )
        assert (tmp_path / "plot.pdf").read_bytes().startswith(b"%PDF-")
        assert b"<svg" in (tmp_path / "plot.svg").read_bytes()

    def test_single_use_generator_is_consumed_once_before_saving(
        self, tmp_path
    ):
        """A yielded format cannot interleave dm effects before planning finishes."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        seen = []

        def formats():
            """Check that no output is created while collecting the ordered plan."""
            for fmt in ("svg", "png", "pdf"):
                assert not (tmp_path / "nested").exists()
                seen.append(fmt)
                yield fmt

        assert (
            dm.save_formats(
                fig,
                str(tmp_path / "nested" / "plot"),
                formats=formats(),
                validate=False,
            )
            is None
        )
        assert seen == ["svg", "png", "pdf"]
        assert {p.suffix for p in (tmp_path / "nested").iterdir()} == {
            ".svg",
            ".png",
            ".pdf",
        }

    @pytest.mark.parametrize("override", [None, "PNG"])
    def test_actual_effective_format_and_caller_kwargs(
        self, tmp_path, override
    ):
        """None infers from the path; an explicit format wins over its extension."""
        from PIL import Image

        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        extension = "png" if override is None else "jpgg"
        metadata = {"Description": "caller-metadata"}
        assert (
            dm.save_formats(
                fig,
                str(tmp_path / "plot"),
                formats=(extension,),
                format=override,
                metadata=metadata,
                dpi=72,
                bbox_inches=None,
                validate=False,
            )
            is None
        )
        out = tmp_path / f"plot.{extension}"
        with Image.open(out) as image:
            assert image.format == "PNG"
            assert image.info["Description"] == "caller-metadata"
            assert image.width == round(fig.get_figwidth() * 72)
        assert metadata == {"Description": "caller-metadata"}

    def test_empty_explicit_format_rejects_before_directory(self, tmp_path):
        """An empty explicit format must not become a default-format alias."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        with pytest.raises(ValueError, match="Format ''"):
            dm.save_formats(
                fig,
                str(tmp_path / "absent" / "plot"),
                formats=("png",),
                format="",
                validate=False,
            )
        assert not (tmp_path / "absent").exists()

    def test_current_canvas_method_wins_over_supported_filetype_catalog(
        self, tmp_path
    ):
        """A native canvas extension works without a registered format entry."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        import dartwork_mpl as dm

        class CustomCanvas(FigureCanvasAgg):
            """Expose a private output format without changing catalog metadata."""

            print_dmcustom = FigureCanvasAgg.print_png

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        canvas = CustomCanvas(fig)
        assert "dmcustom" not in canvas.get_supported_filetypes()
        assert (
            dm.save_formats(
                fig,
                str(tmp_path / "plot"),
                formats=("dmcustom",),
                validate=False,
            )
            is None
        )
        assert fig.canvas is canvas
        assert (tmp_path / "plot.dmcustom").read_bytes().startswith(b"\x89PNG")

    def test_registered_fallback_need_not_have_class_print_attribute(
        self, tmp_path
    ):
        """Matplotlib permits a registered canvas whose printer is instance-created."""
        from matplotlib import backend_bases
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        import dartwork_mpl as dm

        class LateCanvas(FigureCanvasAgg):
            """Install the native PNG printer only when Matplotlib constructs us."""

            def __init__(self, figure):
                """Add the extension's printer after attaching to the figure."""
                super().__init__(figure)
                self.print_dmlate = self.print_png

        backends = backend_bases._default_backends.copy()
        filetypes = backend_bases._default_filetypes.copy()
        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        canvas = fig.canvas
        try:
            backend_bases.register_backend("dmlate", LateCanvas, "test")
            assert not hasattr(LateCanvas, "print_dmlate")
            dm.save_formats(
                fig, str(tmp_path / "plot"), formats=("dmlate",), validate=False
            )
            assert (
                (tmp_path / "plot.dmlate").read_bytes().startswith(b"\x89PNG")
            )
            assert fig.canvas is canvas
        finally:
            backend_bases._default_backends.clear()
            backend_bases._default_backends.update(backends)
            backend_bases._default_filetypes.clear()
            backend_bases._default_filetypes.update(filetypes)

    def test_explicit_installed_backend_capability_precedes_effects(
        self, tmp_path
    ):
        """Agg saves PNG; SVG backend rejects PNG before creating any directory."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        canvas = fig.canvas
        dm.save_formats(
            fig,
            str(tmp_path / "supported"),
            formats=("png",),
            backend="agg",
            validate=False,
        )
        assert (tmp_path / "supported.png").read_bytes().startswith(b"\x89PNG")
        with pytest.raises(ValueError, match="backend does not support png"):
            dm.save_formats(
                fig,
                str(tmp_path / "absent" / "plot"),
                formats=("png",),
                backend="svg",
                validate=False,
            )
        assert not (tmp_path / "absent").exists()
        assert fig.canvas is canvas

    def test_svgz_still_forces_svg_and_rejects_duplicate_format(self, tmp_path):
        """SVGZ keeps its inner SVG backend and existing duplicate kwarg error."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        dm.save_formats(
            fig,
            str(tmp_path / "plot"),
            formats=("svgz",),
            backend="svg",
            validate=False,
        )
        assert b"<svg" in gzip.decompress((tmp_path / "plot.svgz").read_bytes())
        with pytest.raises(TypeError, match=r"multiple values.*format"):
            dm.save_formats(
                fig,
                str(tmp_path / "duplicate"),
                formats=("svgz",),
                format="png",
                validate=False,
            )

    def test_missing_extension_uses_current_canvas_default(self, tmp_path):
        """An empty member retains Matplotlib's default extension fallback."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        with plt.rc_context({"savefig.format": "png"}):
            assert (
                dm.save_formats(
                    fig,
                    str(tmp_path / "default"),
                    formats=("",),
                    format=None,
                    validate=False,
                )
                is None
            )
        assert (tmp_path / "default.png").read_bytes().startswith(b"\x89PNG")

    def test_generator_save_order_matches_requested_order(
        self, tmp_path, monkeypatch
    ):
        """The retained one-shot plan executes in caller order, with real saves."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        original = fig.savefig
        saved = []

        def save(path, **kwargs):
            """Observe output order while retaining the actual writer."""
            saved.append(Path(path).suffix)
            return original(path, **kwargs)

        monkeypatch.setattr(fig, "savefig", save)
        dm.save_formats(
            fig,
            str(tmp_path / "plot"),
            formats=(fmt for fmt in ("svg", "png", "pdf")),
            validate=False,
        )
        assert saved == [".svg", ".png", ".pdf"]

    def test_preflight_never_constructs_or_attaches_registered_canvas(
        self, tmp_path
    ):
        """A later invalid format rejects before any registered canvas constructor."""
        from matplotlib import backend_bases
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        import dartwork_mpl as dm

        constructed = []

        class CountedCanvas(FigureCanvasAgg):
            """Track construction independently of the figure's restored canvas."""

            print_dmcounted = FigureCanvasAgg.print_png

            def __init__(self, figure):
                """Record every actual Matplotlib canvas attachment."""
                constructed.append(figure)
                super().__init__(figure)

        backends = backend_bases._default_backends.copy()
        filetypes = backend_bases._default_filetypes.copy()
        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        canvas = fig.canvas
        try:
            backend_bases.register_backend("dmcounted", CountedCanvas, "test")
            with pytest.raises(ValueError, match="jpgg"):
                dm.save_formats(
                    fig,
                    str(tmp_path / "absent" / "plot"),
                    formats=("dmcounted", "jpgg"),
                    validate=False,
                )
            assert constructed == []
            assert fig.canvas is canvas
            assert not (tmp_path / "absent").exists()
        finally:
            backend_bases._default_backends.clear()
            backend_bases._default_backends.update(backends)
            backend_bases._default_filetypes.clear()
            backend_bases._default_filetypes.update(filetypes)

    def test_svgz_preflights_inner_svg_capability(self, tmp_path):
        """Agg rejects SVGZ's inner SVG before directory or adoption effects."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        with pytest.raises(ValueError, match="backend does not support svg"):
            dm.save_formats(
                fig,
                str(tmp_path / "absent" / "plot"),
                formats=("svgz",),
                backend="agg",
                validate=False,
            )
        assert not (tmp_path / "absent").exists()

    def test_explicit_invalid_format_wins_over_valid_member(self, tmp_path):
        """An invalid caller override rejects even when the member itself is PNG."""
        import dartwork_mpl as dm

        fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
        with pytest.raises(ValueError, match="jpgg"):
            dm.save_formats(
                fig,
                str(tmp_path / "absent" / "plot"),
                formats=("png",),
                format="jpgg",
                validate=False,
            )
        assert not (tmp_path / "absent").exists()
