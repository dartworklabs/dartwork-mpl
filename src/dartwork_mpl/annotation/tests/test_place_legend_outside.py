"""``place_legend(loc="above" | "below" | "right" | "left")`` puts the legend outside (#523).

A request such as "legend above the plot" names the side only; the
distance, the row count and the clearance of tick and axis labels come
from the library, so every agent gets the same legend from one call.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.annotation import place_legend

PRESETS = ("report", "scientific", "presentation")
SIDES = ("above", "below", "right", "left")
TOL_PX = 0.5


def _renderer(fig):
    fig.canvas.draw()
    return fig.canvas.get_renderer()


def _chart(preset: str, n_series: int = 2, width: str = "12cm"):
    """A labelled line chart with ``n_series`` legend entries under ``preset``."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    x = np.arange(2012, 2024)
    for i in range(n_series):
        ax.plot(x, np.sin(x + i), label=f"Series {i + 1}")
    ax.set(xlabel="Year", ylabel="Growth (%)")
    return fig, ax


def _decorations(ax, renderer):
    """Union extent of the in-view tick labels and both axis labels."""
    boxes = [
        ax.xaxis.label.get_window_extent(renderer),
        ax.yaxis.label.get_window_extent(renderer),
    ]
    for axis, index in ((ax.xaxis, 0), (ax.yaxis, 1)):
        lo, hi = sorted(axis.get_view_interval())
        for tick in axis.get_ticklabels():
            if tick.get_text() and lo <= tick.get_position()[index] <= hi:
                boxes.append(tick.get_window_extent(renderer))
    return boxes


def _gap_px(fig, legend) -> float:
    """The preset gap: ``legend.borderaxespad`` in legend font units."""
    return legend.borderaxespad * legend._fontsize * fig.dpi / 72.0


def _assert_outside(fig, ax, legend, side: str) -> None:
    """``legend`` sits centred outside ``side`` of ``ax``, past its labels."""
    renderer = _renderer(fig)
    box = ax.get_window_extent(renderer)
    leg = legend.get_window_extent(renderer)
    decorations = _decorations(ax, renderer)
    if side == "above":
        assert leg.y0 >= box.y1 - TOL_PX
        assert (leg.x0 + leg.x1) / 2 == pytest.approx((box.x0 + box.x1) / 2)
    elif side == "below":
        lowest = min(d.y0 for d in decorations if d.y1 <= box.y0 + TOL_PX)
        assert leg.y1 <= lowest + TOL_PX
        assert (leg.x0 + leg.x1) / 2 == pytest.approx((box.x0 + box.x1) / 2)
    elif side == "right":
        assert leg.x0 >= box.x1 - TOL_PX
        assert (leg.y0 + leg.y1) / 2 == pytest.approx((box.y0 + box.y1) / 2)
    else:
        leftmost = min(d.x0 for d in decorations if d.x1 <= box.x0 + TOL_PX)
        assert leg.x1 <= leftmost + TOL_PX
        assert (leg.y0 + leg.y1) / 2 == pytest.approx((box.y0 + box.y1) / 2)
    for deco in decorations:
        assert not leg.overlaps(deco), (side, deco)


class TestOutsidePlacement:
    """Each side and preset: outside, centred, past the labels, gap from the preset."""

    @pytest.mark.parametrize("preset", PRESETS)
    @pytest.mark.parametrize("side", SIDES)
    def test_side_is_outside_and_centred(self, preset: str, side: str) -> None:
        fig, ax = _chart(preset)
        legend = place_legend(ax, loc=side)
        assert legend is ax.get_legend()
        _assert_outside(fig, ax, legend, side)
        plt.close(fig)

    @pytest.mark.parametrize("preset", PRESETS)
    @pytest.mark.parametrize("side", SIDES)
    def test_side_survives_simple_layout_without_findings(
        self, preset: str, side: str
    ) -> None:
        fig, ax = _chart(preset)
        ax.set_title("Real GDP growth by country")
        legend = place_legend(ax, loc=side)
        dm.simple_layout(fig)
        _assert_outside(fig, ax, legend, side)
        renderer = _renderer(fig)
        leg = legend.get_window_extent(renderer)
        assert fig.bbox.x0 - TOL_PX <= leg.x0 and leg.x1 <= fig.bbox.x1 + TOL_PX
        assert fig.bbox.y0 - TOL_PX <= leg.y0 and leg.y1 <= fig.bbox.y1 + TOL_PX
        ids = {
            w.check_id
            for w in dm.validate_figure(fig, quiet=True)
            if w.check_id in {"LEGEND_OVERLAP", "OVERLAP", "OVERFLOW"}
        }
        assert ids == set()
        plt.close(fig)

    @pytest.mark.parametrize("side", SIDES)
    def test_gap_is_the_presets_border_axes_pad(self, side: str) -> None:
        fig, ax = _chart("report")
        legend = place_legend(ax, loc=side)
        renderer = _renderer(fig)
        box = ax.get_window_extent(renderer)
        leg = legend.get_window_extent(renderer)
        decorations = _decorations(ax, renderer)
        if side == "above":
            gap = leg.y0 - box.y1
        elif side == "below":
            gap = min(d.y0 for d in decorations if d.y1 <= box.y0) - leg.y1
        elif side == "right":
            gap = leg.x0 - box.x1
        else:
            gap = min(d.x0 for d in decorations if d.x1 <= box.x0) - leg.x1
        assert gap == pytest.approx(_gap_px(fig, legend), abs=TOL_PX)
        plt.close(fig)


class TestOutsideColumns:
    """Above/below take the fewest rows that fit the axes; right/left one column."""

    @pytest.mark.parametrize("side", ("above", "below"))
    def test_one_row_when_it_fits(self, side: str) -> None:
        fig, ax = _chart("report", n_series=3)
        legend = place_legend(ax, loc=side)
        assert legend._ncols == 3
        plt.close(fig)

    @pytest.mark.parametrize("side", ("right", "left"))
    def test_one_column_at_the_sides(self, side: str) -> None:
        fig, ax = _chart("report", n_series=3)
        assert place_legend(ax, loc=side)._ncols == 1
        plt.close(fig)

    def test_fewest_rows_that_fit_a_narrow_axes(self) -> None:
        fig, ax = _chart("presentation", n_series=7, width="9cm")
        legend = place_legend(ax, loc="above")
        renderer = _renderer(fig)
        width = ax.get_window_extent(renderer).width
        ncols = legend._ncols
        assert 1 < ncols < 7
        assert legend.get_window_extent(renderer).width <= width
        rows = -(-7 // ncols)
        wider = -(-7 // (rows - 1))  # the next column count with one row fewer
        trial = ax.legend(ncols=wider, loc="lower center")
        assert trial.get_window_extent(renderer).width > width
        plt.close(fig)

    def test_explicit_ncols_wins(self) -> None:
        fig, ax = _chart("report", n_series=4)
        assert place_legend(ax, loc="above", ncols=1)._ncols == 1
        assert place_legend(ax, loc="right", ncol=2)._ncols == 2
        plt.close(fig)


class TestOutsideRobustness:
    """Labels added later, twin axes and conflicting arguments."""

    def test_labels_set_after_the_legend_are_cleared_by_simple_layout(
        self,
    ) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot([0, 1, 2], [1, 3, 2], label="a")
        ax.plot([0, 1, 2], [2, 1, 3], label="b")
        legend = place_legend(ax, loc="below")
        ax.set_xlabel("Added after the legend")
        dm.simple_layout(fig)
        _assert_outside(fig, ax, legend, "below")
        plt.close(fig)

    def test_right_legend_clears_a_twin_axes_labels(self) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        twin = ax.twinx()
        ax.plot([0, 1, 2], [1, 3, 2], label="left series")
        twin.plot([0, 1, 2], [200, 100, 300])
        twin.set_ylabel("Right axis (units)")
        legend = place_legend(ax, loc="right")
        dm.simple_layout(fig)
        renderer = _renderer(fig)
        leg = legend.get_window_extent(renderer)
        assert leg.x0 >= twin.yaxis.label.get_window_extent(renderer).x1
        for tick in twin.get_yticklabels():
            if tick.get_text():
                assert not leg.overlaps(tick.get_window_extent(renderer))
        plt.close(fig)

    @pytest.mark.parametrize("key", ("bbox_to_anchor", "bbox_transform"))
    def test_anchor_arguments_conflict_with_a_side(self, key: str) -> None:
        fig, ax = _chart("report")
        value = (0.5, 1.0) if key == "bbox_to_anchor" else ax.transAxes
        with pytest.raises(ValueError, match=key):
            place_legend(ax, loc="above", **{key: value})
        plt.close(fig)

    def test_matplotlib_locs_are_unchanged(self) -> None:
        fig, ax = _chart("report")
        legend = place_legend(ax, loc="lower right")
        assert legend._loc == 4
        assert legend.get_bbox_to_anchor().bounds == ax.bbox.bounds
        plt.close(fig)

    def test_legend_kwargs_pass_through(self) -> None:
        fig, ax = _chart("report")
        legend = place_legend(ax, loc="above", title="Country", frameon=True)
        assert legend.get_title().get_text() == "Country"
        assert legend.get_frame_on()
        plt.close(fig)


def _crowded_scatter(preset: str = "report"):
    """Three clouds that leave no in-axes corner free for a legend."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    rng = np.random.default_rng(3)
    for i, name in enumerate(("Alpine", "Coastal", "Desert")):
        xs = rng.uniform(0, 10, 120)
        ax.scatter(xs, rng.uniform(0, 10, 120) + i * 0.1, s=12, label=name)
    # No axes margins: the clouds reach every edge, so no corner is free.
    ax.set(
        xlabel="Length (cm)", ylabel="Width (cm)", xlim=(0, 10), ylim=(0, 10)
    )
    return fig, ax


class TestBestFallsBackOutside:
    """No side named: inside when a spot is free, otherwise above (#523).

    Agents asked for no side still picked one by taste (above, right), so the
    same request drew different legends; the library now decides.
    """

    @pytest.mark.parametrize("preset", PRESETS)
    def test_crowded_axes_put_the_legend_above(self, preset: str) -> None:
        fig, ax = _crowded_scatter(preset)
        try:
            legend = place_legend(ax)
            assert legend is not None
            assert legend._dm_outside_fallback is True
            assert legend._dm_collision_free is True
            _assert_outside(fig, ax, legend, "above")
        finally:
            plt.close(fig)

    def test_a_free_corner_keeps_the_legend_inside(self) -> None:
        fig, ax = _chart("report", n_series=5)
        try:
            ax.set_ylim(-1.2, 4.0)  # the top band is empty
            legend = place_legend(ax)
            assert legend is not None
            assert not getattr(legend, "_dm_outside_fallback", False)
            renderer = _renderer(fig)
            box = legend.get_window_extent(renderer)
            axes_box = ax.get_window_extent(renderer)
            assert box.y1 <= axes_box.y1 + TOL_PX
        finally:
            plt.close(fig)

    def test_a_caller_anchor_keeps_the_legend_where_asked(self) -> None:
        fig, ax = _crowded_scatter()
        try:
            legend = place_legend(ax, bbox_to_anchor=(0.0, 0.0, 1.0, 1.0))
            assert legend is not None
            assert not getattr(legend, "_dm_outside_fallback", False)
        finally:
            plt.close(fig)

    def test_fallback_then_simple_layout_has_no_findings(self) -> None:
        fig, ax = _crowded_scatter()
        try:
            ax.set_title("Leaf size by species")
            place_legend(ax)
            dm.simple_layout(fig)
            found = dm.validate_figure(
                fig,
                checks=("LEGEND_OVERLAP", "OVERLAP", "OVERFLOW"),
                quiet=True,
            )
            assert not found, [w.message for w in found]
        finally:
            plt.close(fig)


def _combo(preset: str = "report"):
    """Bars on the left axis, a line on its twin, each with its own legend."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    months = np.arange(1, 13)
    ax.bar(months, 40 + 30 * np.sin(months / 2), label="Sales")
    twin = ax.twinx()
    twin.plot(months, 5 + 3 * np.cos(months / 3), color="k", label="Margin")
    ax.legend(loc="upper left")
    twin.legend(loc="upper left")  # the draft's two stacked legends
    return fig, ax, twin


class TestTwinAxesOneLegend:
    """A twin pair gets one legend from one call, whichever twin is passed."""

    @pytest.mark.parametrize("which", ["host", "twin"])
    def test_one_legend_with_both_entries(self, which: str) -> None:
        fig, ax, twin = _combo()
        try:
            legend = place_legend(ax if which == "host" else twin)
            assert legend is not None
            assert [t.get_text() for t in legend.get_texts()] == [
                "Sales",
                "Margin",
            ]
            legends = [a.get_legend() for a in (ax, twin)]
            assert legends.count(None) == 1
            assert twin.get_legend() is legend  # drawn last: above the bars
        finally:
            plt.close(fig)

    def test_the_legend_clears_both_twins_data(self) -> None:
        fig, ax, twin = _combo()
        try:
            legend = place_legend(ax)
            dm.simple_layout(fig)
            found = dm.validate_figure(
                fig, checks=("LEGEND_OVERLAP", "OVERLAP"), quiet=True
            )
            assert not found, [w.message for w in found]
            assert legend._dm_collision_free is True
        finally:
            plt.close(fig)
