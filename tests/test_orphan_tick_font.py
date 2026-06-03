"""Tests for orphan tick-label axis-label font adoption."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.layout import (
    _adopt_axis_label_font_core,
    adopt_axis_label_font,
    simple_layout,
)


def _x_tick(ax):
    return next(
        t
        for t in ax.xaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


def _y_tick(ax):
    return next(
        t
        for t in ax.yaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


class TestAdoptCore:
    def test_unlabeled_x_adopts_axis_label_font(self) -> None:
        """x has no label -> x ticks take xaxis.label size+weight+family+style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # y labeled, x unlabeled
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        xt, lbl = _x_tick(ax), ax.xaxis.label
        assert xt.get_fontsize() == lbl.get_fontsize()
        assert xt.get_fontweight() == lbl.get_fontweight()
        assert list(xt.get_fontfamily()) == list(lbl.get_fontfamily())
        assert xt.get_fontstyle() == lbl.get_fontstyle()
        plt.close(fig)

    def test_labeled_axis_ticks_untouched(self) -> None:
        """y has a label -> y ticks keep their default (lighter) style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        yt, lbl = _y_tick(ax), ax.yaxis.label
        assert yt.get_fontweight() == before
        # default tick weight differs from axis-label weight in this preset
        assert lbl.get_fontweight() != before
        plt.close(fig)

    def test_x_and_y_independent(self) -> None:
        """y labeled, x not -> x adopts, y does not."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        y_before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        assert _y_tick(ax).get_fontweight() == y_before
        plt.close(fig)

    def test_offset_text_adopts(self) -> None:
        """Unlabeled axis -> ScalarFormatter offset text adopts label font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), [v * 1e9 for v in range(10)])  # forces 1e9 offset
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        ot = ax.yaxis.get_offset_text()
        assert ot.get_text().strip()  # offset present
        assert ot.get_fontweight() == ax.yaxis.label.get_fontweight()
        plt.close(fig)

    def test_idempotent(self) -> None:
        """Two applications produce identical font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)
        size1, w1 = _x_tick(ax).get_fontsize(), _x_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)
        assert _x_tick(ax).get_fontsize() == size1
        assert _x_tick(ax).get_fontweight() == w1
        plt.close(fig)

    def test_no_ticklabels_no_error(self) -> None:
        """Unlabeled axis with no tick labels -> no error, no-op."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_xticks([])
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)  # must not raise
        plt.close(fig)


class TestAdoptPublic:
    def test_public_draws_and_applies(self) -> None:
        """adopt_axis_label_font draws then applies (no manual draw needed)."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        adopt_axis_label_font(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_empty_figure_no_error(self) -> None:
        fig = plt.figure()
        adopt_axis_label_font(fig)  # no axes -> no-op
        plt.close(fig)


class TestSimpleLayoutIntegration:
    def test_simple_layout_applies_by_default(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x unlabeled
        simple_layout(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_simple_layout_toggle_off(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        default_weight = _x_tick(ax).get_fontweight()
        simple_layout(fig, adopt_orphan_tick_font=False)
        assert _x_tick(ax).get_fontweight() == default_weight
        plt.close(fig)

    def test_margin_reflects_enlarged_orphan_ticks(self) -> None:
        """A larger axis-label font on an unlabeled axis grows the bottom
        margin because simple_layout measures the restyled ticks."""
        dm.style.use("scientific")

        def build():
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
            ax.plot(range(10), range(10))
            ax.xaxis.label.set_fontsize(24)  # empty label, large font
            return fig, ax

        fig_on, ax_on = build()
        simple_layout(fig_on, adopt_orphan_tick_font=True)
        bottom_on = ax_on.get_gridspec().bottom

        fig_off, ax_off = build()
        simple_layout(fig_off, adopt_orphan_tick_font=False)
        bottom_off = ax_off.get_gridspec().bottom

        assert _x_tick(ax_on).get_fontsize() == 24
        # bigger ticks push the axes up -> larger bottom edge fraction
        assert bottom_on > bottom_off + 0.01
        plt.close(fig_on)
        plt.close(fig_off)


def test_exported_at_package_root() -> None:
    assert hasattr(dm, "adopt_axis_label_font")
    assert "adopt_axis_label_font" in dm.__all__


class TestSaveFormatsIntegration:
    """save_formats applies the adoption so the saved output always
    reflects it, even when simple_layout was never called."""

    def test_save_formats_applies_by_default(self, tmp_path) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x unlabeled; NOTE: no simple_layout call
        dm.save_formats(
            fig, str(tmp_path / "out"), formats=("png",), validate=False
        )
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_save_formats_toggle_off(self, tmp_path) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        fig.canvas.draw()
        default_weight = _x_tick(ax).get_fontweight()
        dm.save_formats(
            fig,
            str(tmp_path / "out"),
            formats=("png",),
            validate=False,
            adopt_orphan_tick_font=False,
        )
        assert _x_tick(ax).get_fontweight() == default_weight
        plt.close(fig)
