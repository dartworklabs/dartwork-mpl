"""``simple_layout`` keeps titles off a legend above the axes (#523).

"Legend above the plot" plus a title used to draw the title on the legend:
matplotlib places the title ``axes.titlepad`` above the axes whatever sits
there. ``simple_layout`` now raises the title offset so the title sits that
pad above the legend, for ``dm.place_legend(ax, loc="above")`` and for a raw
``ax.legend(..., bbox_to_anchor=(x, 1.0))`` alike, without touching the
title's text, size or weight. A suptitle stays clear of both, and a bottom
source note written with ``fig.text`` stays clear of the x label.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

PRESETS = ("report", "scientific", "presentation")
ENTRY_PATHS = ("place_legend", "raw")
TOL_PX = 0.5


def _legend_above(ax, entry: str) -> None:
    """Put the legend of ``ax`` above it through ``entry``."""
    if entry == "place_legend":
        dm.place_legend(ax, loc="above")
    else:
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2)


def _chart(preset: str, nrows: int = 1):
    dm.style.use(preset)
    fig, axes = plt.subplots(
        nrows, 1, figsize=dm.figsize("12cm", "standard"), squeeze=False
    )
    x = np.arange(2012, 2024)
    for ax in axes[:, 0]:
        ax.plot(x, np.sin(x), label="Korea")
        ax.plot(x, np.cos(x), label="Japan")
        ax.set(xlabel="Year", ylabel="Growth (%)")
    return fig, axes[:, 0]


def _clear(a, b) -> bool:
    """True when two display boxes do not overlap by more than ``TOL_PX``."""
    width = min(a.x1, b.x1) - max(a.x0, b.x0)
    height = min(a.y1, b.y1) - max(a.y0, b.y0)
    return width <= TOL_PX or height <= TOL_PX


class TestTitleOverLegend:
    """The axes title ends up above a legend that sits above the axes."""

    @pytest.mark.parametrize("preset", PRESETS)
    @pytest.mark.parametrize("entry", ENTRY_PATHS)
    def test_title_clears_the_legend(self, preset: str, entry: str) -> None:
        fig, (ax,) = _chart(preset)
        title = ax.set_title("Real GDP growth by country")
        _legend_above(ax, entry)
        size, weight = title.get_fontsize(), title.get_fontweight()
        renderer = drawn_renderer(fig)
        assert not _clear(
            title.get_window_extent(renderer),
            ax.get_legend().get_window_extent(renderer),
        ), "the fixture must start with the collision"

        dm.simple_layout(fig)

        renderer = drawn_renderer(fig)
        title_box = title.get_window_extent(renderer)
        legend_box = ax.get_legend().get_window_extent(renderer)
        assert title_box.y0 >= legend_box.y1 - TOL_PX
        assert title.get_text() == "Real GDP growth by country"
        assert title.get_fontsize() == size
        assert title.get_fontweight() == weight
        assert fig.bbox.y1 + TOL_PX >= title_box.y1
        ids = {w.check_id for w in dm.validate_figure(fig, quiet=True)}
        assert not ids & {"LEGEND_OVERLAP", "OVERLAP", "OVERFLOW"}
        plt.close(fig)

    @pytest.mark.parametrize("entry", ENTRY_PATHS)
    def test_baseline_is_one_title_pad_above_the_legend(
        self, entry: str
    ) -> None:
        fig, (ax,) = _chart("report")
        title = ax.set_title("Real GDP growth by country")
        _legend_above(ax, entry)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        baseline = title.get_transform().transform(title.get_position())[1]
        legend_top = ax.get_legend().get_window_extent(renderer).y1
        pad_px = plt.rcParams["axes.titlepad"] * fig.dpi / 72.0
        assert baseline - legend_top == pytest.approx(pad_px, abs=TOL_PX)
        plt.close(fig)

    def test_all_three_title_slots_clear_and_share_a_baseline(self) -> None:
        fig, (ax,) = _chart("report")
        titles = [
            ax.set_title("Left headline", loc="left"),
            ax.set_title("Centre", loc="center"),
            ax.set_title("Right note", loc="right"),
        ]
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        legend_box = ax.get_legend().get_window_extent(renderer)
        baselines = set()
        for title in titles:
            assert _clear(title.get_window_extent(renderer), legend_box)
            baselines.add(
                round(title.get_transform().transform(title.get_position())[1])
            )
        assert len(baselines) == 1
        plt.close(fig)

    def test_layout_twice_keeps_the_title_in_place(self) -> None:
        fig, (ax,) = _chart("report")
        title = ax.set_title("Real GDP growth by country")
        dm.place_legend(ax, loc="above")
        dm.simple_layout(fig)
        first = title.get_window_extent(drawn_renderer(fig))
        dm.simple_layout(fig)
        second = title.get_window_extent(drawn_renderer(fig))
        assert second.y0 == pytest.approx(first.y0, abs=TOL_PX)
        assert second.y1 == pytest.approx(first.y1, abs=TOL_PX)
        plt.close(fig)

    def test_legend_inside_the_axes_leaves_the_title_alone(self) -> None:
        fig, (ax,) = _chart("report")
        title = ax.set_title("Real GDP growth by country")
        ax.legend(loc="upper right")
        dm.simple_layout(fig)
        drawn_renderer(fig)
        base = ax.transAxes.transform(title.get_position())[1]
        pad = title.get_transform().transform(title.get_position())[1] - base
        assert pad == pytest.approx(
            plt.rcParams["axes.titlepad"] * fig.dpi / 72.0, abs=TOL_PX
        )
        plt.close(fig)

    def test_a_title_beside_the_legend_keeps_its_pad(self) -> None:
        fig, (ax,) = _chart("report")
        title = ax.set_title("Left", loc="left")
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncols=2)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        assert _clear(
            title.get_window_extent(renderer),
            ax.get_legend().get_window_extent(renderer),
        )
        base = ax.transAxes.transform(title.get_position())[1]
        pad = title.get_transform().transform(title.get_position())[1] - base
        assert pad == pytest.approx(
            plt.rcParams["axes.titlepad"] * fig.dpi / 72.0, abs=TOL_PX
        )
        plt.close(fig)


class TestSuptitleOverLegend:
    """A suptitle stays clear of an above-legend (and title) on the top row."""

    @pytest.mark.parametrize("entry", ENTRY_PATHS)
    @pytest.mark.parametrize("with_title", (False, True))
    def test_suptitle_clears_the_top_row(
        self, entry: str, with_title: bool
    ) -> None:
        fig, axes = _chart("report", nrows=2)
        top = axes[0]
        if with_title:
            top.set_title("Panel title")
        _legend_above(top, entry)
        suptitle = fig.suptitle("Figure suptitle")
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        sup_box = suptitle.get_window_extent(renderer)
        legend_box = top.get_legend().get_window_extent(renderer)
        assert _clear(sup_box, legend_box)
        assert _clear(sup_box, top.title.get_window_extent(renderer))
        if with_title:
            assert _clear(top.title.get_window_extent(renderer), legend_box)
        ids = {w.check_id for w in dm.validate_figure(fig, quiet=True)}
        assert "LEGEND_OVERLAP" not in ids
        plt.close(fig)


class TestBottomSourceNote:
    """A ``fig.text`` source note at the bottom left stays clear of the x label."""

    @pytest.mark.parametrize("preset", PRESETS)
    @pytest.mark.parametrize("legend", (None, "below", "above"))
    def test_note_clears_the_x_label(
        self, preset: str, legend: str | None
    ) -> None:
        fig, (ax,) = _chart(preset)
        ax.set_title("Real GDP growth by country")
        if legend is not None:
            dm.place_legend(ax, loc=legend)
        note = fig.text(
            0.01,
            0.01,
            "Source: internal web logs",
            ha="left",
            va="bottom",
            fontsize=dm.fs(-1),
        )
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        note_box = note.get_window_extent(renderer)
        xlabel_box = ax.xaxis.label.get_window_extent(renderer)
        assert note_box.y1 <= xlabel_box.y0 + TOL_PX
        for tick in ax.get_xticklabels():
            if tick.get_text():
                assert _clear(note_box, tick.get_window_extent(renderer))
        if legend is not None:
            assert _clear(note_box, ax.get_legend().get_window_extent(renderer))
        ids = {w.check_id for w in dm.validate_figure(fig, quiet=True)}
        assert not ids & {"LEGEND_OVERLAP", "OVERLAP", "OVERFLOW"}
        plt.close(fig)
