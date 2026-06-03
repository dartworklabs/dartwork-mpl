"""Tests for orphan tick-label axis-label font adoption."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.layout import (
    _adopt_axis_label_font_core,
    adopt_axis_label_font,
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
