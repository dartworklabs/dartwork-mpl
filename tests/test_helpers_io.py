"""Behavioural tests for ``dartwork_mpl.helpers.io``.

Covers the previously-untested ``save_figure`` and
``create_figure_with_style`` helpers added in 0.3.x. Both are very
thin wrappers but exercise filesystem side-effects, multi-format
writing, and the dartwork style-application path.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from dartwork_mpl.helpers.io import create_figure_with_style, save_figure


def _simple_fig() -> Figure:
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 4])
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return fig


class TestSaveFigure:
    """``save_figure`` writes one or more formats to disk."""

    def test_writes_png_by_default(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fig = _simple_fig()
        out = tmp_path / "single"
        save_figure(fig, out, formats=("png",), dpi=100)
        plt.close(fig)
        # ``save_formats`` appends the extension.
        assert (tmp_path / "single.png").exists()
        # verbose=True prints a confirmation per format.
        captured = capsys.readouterr().out
        assert "single.png" in captured or "Saved" in captured

    def test_writes_multiple_formats(self, tmp_path: Path) -> None:
        fig = _simple_fig()
        out = tmp_path / "multi"
        save_figure(fig, out, formats=("png", "svg"), dpi=100, verbose=False)
        plt.close(fig)
        assert (tmp_path / "multi.png").exists()
        assert (tmp_path / "multi.svg").exists()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """``create_dir=True`` (default) should mkdir parents."""
        fig = _simple_fig()
        nested = tmp_path / "deeply" / "nested" / "out"
        save_figure(fig, nested, formats=("png",), dpi=100, verbose=False)
        plt.close(fig)
        assert nested.parent.is_dir()
        assert (nested.with_suffix(".png")).exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Filename may be a ``str`` rather than a ``Path``."""
        fig = _simple_fig()
        out = str(tmp_path / "as-str")
        save_figure(fig, out, formats=("png",), dpi=100, verbose=False)
        plt.close(fig)
        assert (tmp_path / "as-str.png").exists()

    def test_quiet_mode_no_print(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fig = _simple_fig()
        out = tmp_path / "quiet"
        save_figure(fig, out, formats=("png",), dpi=100, verbose=False)
        plt.close(fig)
        # ``verbose=False`` suppresses the ✓ Saved output.
        captured = capsys.readouterr().out
        assert "Saved" not in captured

    def test_dpi_propagates_to_savefig(self, tmp_path: Path) -> None:
        """A larger dpi yields a measurably larger PNG file."""
        fig_small = _simple_fig()
        fig_large = _simple_fig()
        small = tmp_path / "small"
        large = tmp_path / "large"
        save_figure(fig_small, small, formats=("png",), dpi=72, verbose=False)
        save_figure(fig_large, large, formats=("png",), dpi=200, verbose=False)
        plt.close(fig_small)
        plt.close(fig_large)
        small_size = (tmp_path / "small.png").stat().st_size
        large_size = (tmp_path / "large.png").stat().st_size
        # Higher DPI -> more pixels -> larger file (allow modest fudge).
        assert large_size > small_size


class TestCreateFigureWithStyle:
    """``create_figure_with_style`` applies a style and returns a Figure."""

    def test_returns_figure_with_default_size(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig = create_figure_with_style(style="report-kr")
        try:
            assert isinstance(fig, Figure)
            # Default width is the legacy DW = 17 cm; we do not pin the
            # exact value (cm() depends on rcParams), so just verify it's
            # set to a positive non-trivial size.
            w, h = fig.get_size_inches()
            assert w > 1.0 and h > 1.0
            # Height is roughly 60% of width (default heuristic).
            assert h < w
        finally:
            plt.close(fig)

    def test_custom_figsize_honoured(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig = create_figure_with_style(
                style="report-kr", figsize=(4.0, 3.0)
            )
        try:
            w, h = fig.get_size_inches()
            assert (round(w, 2), round(h, 2)) == (4.0, 3.0)
        finally:
            plt.close(fig)

    def test_dpi_applied(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig = create_figure_with_style(
                style="report-kr", figsize=(3.0, 2.0), dpi=150
            )
        try:
            assert fig.dpi == 150
        finally:
            plt.close(fig)

    def test_unknown_style_raises(self) -> None:
        """Style names that dartwork-mpl does not recognise should raise."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises((KeyError, ValueError, OSError)):
                create_figure_with_style(style="absolutely-not-a-style")

    def test_each_call_returns_new_figure(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            a = create_figure_with_style(style="report-kr", figsize=(3, 2))
            b = create_figure_with_style(style="report-kr", figsize=(3, 2))
        try:
            assert a is not b
        finally:
            plt.close(a)
            plt.close(b)


class TestPackageReexports:
    """The ``helpers`` package level should expose the io helpers."""

    def test_save_figure_reexported(self) -> None:
        from dartwork_mpl import helpers

        assert hasattr(helpers, "save_figure")
        assert helpers.save_figure is save_figure

    def test_create_figure_with_style_reexported(self) -> None:
        from dartwork_mpl import helpers

        assert hasattr(helpers, "create_figure_with_style")
        assert helpers.create_figure_with_style is create_figure_with_style

    def test_dunder_all_complete(self) -> None:
        """All public helpers appear in ``helpers.__all__``."""
        from dartwork_mpl import helpers

        for name in (
            "add_value_labels",
            "auto_select_colors",
            "check_figure_quality",
            "create_figure_with_style",
            "format_axis_labels",
            "optimize_legend",
            "save_figure",
            "suggest_chart_type",
            "validate_data",
        ):
            assert name in helpers.__all__, f"{name} missing from __all__"
