"""The ``place_legend`` ladder: inside by the drawn ink, then the side that costs least, then the least covering spot.

Each group pins one rung and the conditions that move a legend to the next
one: the drawn ink and its clearance, the outside side chosen by plot loss
among the sides no panel sits beyond, long names wrapped only to fit, the
second look ``simple_layout`` takes at the size it settles on, the knobs
that turn each rung off, what the caller fixes, and the draw budget. The
oracle is the drawn figure: legend and Axes extents, entry texts and
``LEGEND_ON_DATA``.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl.annotation import place_legend, settle_legends
from dartwork_mpl.annotation._legend_fit import (
    CLEARANCE_PT,
    free_sides,
    measure_ink,
)
from dartwork_mpl.annotation._legend_outside import (
    _wrapped_variants,
    side_plans,
)
from dartwork_mpl.annotation._place_legend import inside_spots
from tests.support.mpl_observe import drawn_renderer, legend_ncols

LONG = " metropolitan region, seasonally adjusted (2019 = 100)"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _dense(ax, n: int, suffix: str = "") -> None:
    """``n`` sine lines through the whole plot: no corner is free."""
    x = np.linspace(0, 11, 60)
    for i in range(n):
        ax.plot(
            x,
            50 + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / n),
            label=f"Region {i + 1}{suffix}",
        )


def _covers(fig) -> list:
    return dm.validate_figure(fig, checks=("LEGEND_ON_DATA",), quiet=True)


def _boxes(fig, legend, ax) -> tuple[Bbox, Bbox]:
    renderer = drawn_renderer(fig)
    return legend.get_window_extent(renderer), ax.get_window_extent(renderer)


def _report(width: str = "12cm"):
    dm.style.use("report")
    return plt.subplots(figsize=dm.figsize(width, "standard"))


# -------------------------------------------------------- rung 1: inside
def test_a_diagonal_leaves_two_corners_free() -> None:
    """A line's drawn path, not its segment boxes, decides what is taken."""
    fig, ax = _report()
    ax.plot([0, 1], [0, 1], label="Rising")
    ax.plot([0, 1], [0.05, 1.05], label="Rising too")
    legend = place_legend(ax)
    assert legend is not None
    assert legend._dm_collision_free is True
    assert not getattr(legend, "_dm_outside_fallback", False)
    leg, box = _boxes(fig, legend, ax)
    assert box.x0 <= leg.x0 and leg.x1 <= box.x1
    assert box.y0 <= leg.y0 and leg.y1 <= box.y1
    dm.simple_layout(fig)
    assert _covers(fig) == []


def test_place_legend_never_lands_on_data() -> None:
    fig, ax = _report()
    _dense(ax, 5)
    place_legend(ax)
    dm.simple_layout(fig)
    assert _covers(fig) == []


def _line_below_spot(gap_pt: float, width_pt: float = 1.0):
    """One-column upper-right spot, and a flat line ``gap_pt`` below its box.

    The other spots are taken by a filled band, so only the clearance
    decides whether the upper right is free.
    """
    fig, ax = _report()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.fill_between([0, 10], 0, 6, color="oc.gray2", label="Band")
    renderer = drawn_renderer(fig)
    handles, labels = ax.get_legend_handles_labels()
    spot = next(
        s
        for s in inside_spots(ax, handles, labels, {}, renderer)
        if (s.loc, s.ncol) == ("upper right", 1)
    )
    assert spot.free
    legend = ax.legend(loc="upper right")
    top = legend.get_window_extent(renderer)
    legend.remove()
    half = width_pt / 2 * fig.dpi / 72
    y_px = top.y0 - gap_pt * fig.dpi / 72 - half
    ((_x, y),) = ax.transData.inverted().transform([(top.x0, y_px)])
    # No legend entry: the legend measured above keeps its size.
    ax.plot([0, 10], [y, y], lw=width_pt, color="oc.red5", label="_edge")
    spots = inside_spots(ax, handles, labels, {}, renderer)
    return next(s for s in spots if (s.loc, s.ncol) == ("upper right", 1))


def test_ink_within_the_clearance_takes_the_spot() -> None:
    assert CLEARANCE_PT == 2.0
    assert not _line_below_spot(1.0).free
    assert _line_below_spot(3.0).free


def test_a_thick_line_reaches_by_its_half_width() -> None:
    """A 6 pt line 4 pt below the box reaches it: 3 pt of stroke, 2 pt of room."""
    assert not _line_below_spot(1.5, width_pt=6.0).free


def test_ink_counts_lines_markers_patches_fills_and_texts() -> None:
    fig, ax = _report()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    line = ax.plot([1, 2], [1, 2], marker="o", linestyle="none")[0]
    bar = ax.bar([5], [2], width=0.5)[0]
    fill = ax.fill_between([7, 9], 1, 2)
    dots = ax.scatter([3], [8])
    text = ax.text(8, 8, "Peak")
    renderer = drawn_renderer(fig)
    ink = measure_ink(ax, renderer)

    def at(x, y) -> Bbox:
        cx, cy = ax.transData.transform((x, y))
        return Bbox.from_bounds(cx - 1, cy - 1, 2, 2)

    assert ink.met(at(1, 1), 0) == {id(line)}
    assert ink.met(at(5, 1), 0) == {id(bar)}
    assert ink.met(at(8, 1.5), 0) == {id(fill)}
    assert ink.met(at(3, 8), 0) == {id(dots)}
    assert id(text) in ink.met(text.get_window_extent(renderer), 0)
    assert ink.met(at(5, 6), 0) == set()


def test_a_legend_larger_than_the_axes_is_not_free_inside() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set_position((0.4, 0.4, 0.15, 0.15))
    for i in range(6):
        ax.plot([0], [0], label=f"Series {i + 1}")
    legend = place_legend(ax)
    assert legend is not None
    assert legend._dm_outside_fallback is True


# -------------------------------------------------------- rung 2: outside
def test_a_few_entries_still_go_above() -> None:
    """Above is the default when no side is clearly cheaper."""
    fig, ax = _report()
    rng = np.random.default_rng(3)
    for name in ("Alpine", "Coastal", "Desert"):
        ax.scatter(rng.uniform(0, 10, 120), rng.uniform(0, 10, 120), label=name)
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = place_legend(ax)
    assert legend is not None and legend._dm_outside_fallback is True
    leg, box = _boxes(fig, legend, ax)
    assert leg.y0 >= box.y1


def test_many_short_entries_go_right_when_it_costs_less() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("15.4cm", "10.5cm"))
    _dense(ax, 10)
    legend = place_legend(ax)
    assert legend is not None
    assert legend._dm_outside_fallback is True
    dm.simple_layout(fig)
    leg, box = _boxes(fig, legend, ax)
    assert leg.x0 >= box.x1
    assert (
        dm.validate_figure(
            fig, checks=("LEGEND_ON_DATA", "LEGEND_OVERLAP"), quiet=True
        )
        == []
    )


def test_a_caller_anchor_keeps_a_covering_legend_inside() -> None:
    fig, ax = _report()
    _dense(ax, 8)
    legend = place_legend(ax, bbox_to_anchor=(0, 0, 1, 1))
    assert legend is not None
    assert not getattr(legend, "_dm_outside_fallback", False)
    assert legend._dm_collision_free is False


def test_bottom_panels_do_not_put_the_legend_on_the_panel_above() -> None:
    dm.style.use("report")
    fig, axs = plt.subplots(2, 2, figsize=dm.figsize("17cm", "12cm"))
    for ax in axs.flat:
        _dense(ax, 6, " metropolitan region")
    assert free_sides(axs[0, 0]) == ["above"]
    assert free_sides(axs[0, 1]) == ["above", "right"]
    assert free_sides(axs[1, 0]) == ["below"]
    assert free_sides(axs[1, 1]) == ["right", "below"]
    for ax in axs.flat:
        place_legend(ax)
    dm.simple_layout(fig)
    assert (
        dm.validate_figure(
            fig, checks=("LEGEND_ON_DATA", "LEGEND_OVERLAP"), quiet=True
        )
        == []
    )


def test_twins_and_hidden_panels_do_not_block_a_side() -> None:
    dm.style.use("report")
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    left.twinx()
    assert "right" not in free_sides(left)
    right.set_visible(False)
    assert free_sides(left) == ["above", "right", "below"]


def test_panels_of_one_figure_agree_on_the_side() -> None:
    """The second panel takes the side the first panel's legend took.

    Alone, the right panel's ten short names would go right (clearly
    cheaper on this 30 cm slide); its neighbour, which has no right side,
    went above, and above fits as well.
    """
    dm.style.use("presentation")
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("30cm", "10.5cm"))
    for ax in axs:
        _dense(ax, 10)
    alone = place_legend(axs[1])
    assert alone is not None
    leg, box = _boxes(fig, alone, axs[1])
    assert leg.x0 >= box.x1  # by itself: right
    alone.remove()
    first = place_legend(axs[0])
    second = place_legend(axs[1])
    assert first is not None and second is not None
    assert free_sides(axs[0]) == ["above", "below"]
    assert "right" in free_sides(axs[1])
    leg0, box0 = _boxes(fig, first, axs[0])
    leg1, box1 = _boxes(fig, second, axs[1])
    assert leg0.y0 >= box0.y1 and leg1.y0 >= box1.y1


@pytest.mark.parametrize(
    ("mode", "outside"),
    [("inside", False), ("above", True), ("right", True), ("below", True)],
)
def test_the_fallback_knob(mode: str, outside: bool) -> None:
    fig, ax = _report()
    _dense(ax, 8)
    with dm.config.override(legend_fallback=mode):
        legend = place_legend(ax)
    assert legend is not None
    assert bool(getattr(legend, "_dm_outside_fallback", False)) is outside
    leg, box = _boxes(fig, legend, ax)
    if mode == "inside":
        assert legend._dm_collision_free is False
        assert _covers(fig)
    elif mode == "above":
        assert leg.y0 >= box.y1
    elif mode == "right":
        assert leg.x0 >= box.x1
    else:
        assert leg.y1 <= box.y0


def test_an_unknown_fallback_raises_where_it_is_read() -> None:
    fig, ax = _report()
    _dense(ax, 8)
    with dm.config.override(legend_fallback="left"):
        with pytest.raises(ValueError, match="legend_fallback"):
            place_legend(ax)


# -------------------------------------------------------- rung 3: wrapping
def test_names_wider_than_the_axes_are_wrapped_to_fit() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("15.4cm", "10.5cm"))
    _dense(ax, 2, LONG)
    legend = place_legend(ax, loc="above")
    assert legend is not None
    texts = [t.get_text() for t in legend.get_texts()]
    names = [f"Region {i + 1}{LONG}" for i in range(2)]
    # Broken only at spaces: joining the lines gives the name back.
    assert [t.replace("\n", " ") for t in texts] == names
    assert all(len(t.split("\n")) >= 2 for t in texts)
    # The unit is whole on one line.
    assert all(
        sum("(2019 = 100)" in line for line in t.split("\n")) == 1
        for t in texts
    )
    assert legend._dm_wrapped is True
    dm.simple_layout(fig)
    assert (
        dm.validate_figure(
            fig, checks=("LEGEND_OVERFLOW", "OVERFLOW"), quiet=True
        )
        == []
    )


def test_a_bracketed_unit_stays_one_piece() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("15.4cm", "10.5cm"))
    _dense(ax, 2, LONG)
    legend = place_legend(ax, loc="above")
    assert legend is not None
    for text in legend.get_texts():
        lines = text.get_text().split("\n")
        assert len(lines) > 1
        # The unit is on one line, whatever else shares it.
        assert sum("(2019 = 100)" in line for line in lines) == 1
        assert not any(line.endswith("(2019") for line in lines)


def test_names_that_fit_stay_on_one_line() -> None:
    fig, ax = _report("17cm")
    _dense(ax, 3, " region")
    legend = place_legend(ax, loc="above")
    assert legend is not None
    assert not any("\n" in t.get_text() for t in legend.get_texts())
    assert legend._dm_wrapped is False


def test_a_fitting_legend_is_planned_with_its_names_as_given() -> None:
    """Wrapped names are not even tried for a legend that fits above.

    The long name would break at the width of two or three columns, and a
    wrapped plan would be a little shorter; the legend fits, so it stays.
    """
    fig, ax = _report()
    for name in (
        "Seoul metropolitan region, seasonally adjusted and smoothed",
        "Busan",
        "Incheon",
        "Daegu",
    ):
        ax.plot([0, 1], [0, 1], label=name)
    renderer = drawn_renderer(fig)
    handles, labels = ax.get_legend_handles_labels()
    assert _wrapped_variants(
        ax, handles, labels, "above", {}, None, renderer, {}
    )
    plans = side_plans(ax, handles, labels, "above", {}, renderer, named=True)
    assert [plan.labels for plan in plans] == [tuple(labels)]
    assert plans[0].level == 2


@pytest.mark.parametrize(
    ("tail", "wrapped"),
    [
        (" metropolitan region, seasonally adjusted", True),  # 52 % wide
        (" metropolitan region index", False),  # 38 % wide
    ],
)
def test_a_right_legend_wraps_past_40_percent_of_the_axes(
    tail: str, wrapped: bool
) -> None:
    """A side named right or left wraps names wider than 40 % of the Axes.

    Both legends fit beside the plot (taller than none, under 60 % of it),
    so only the width rule decides.
    """
    fig, ax = _report()
    for city in ("Seoul", "Busan"):
        ax.plot([0, 1], [0, 1], label=city + tail)
    legend = place_legend(ax, loc="right")
    assert legend is not None
    assert legend._dm_wrapped is wrapped
    assert all(("\n" in t.get_text()) is wrapped for t in legend.get_texts())


def test_wrap_off_keeps_one_line() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("15.4cm", "10.5cm"))
    _dense(ax, 2, LONG)
    with dm.config.override(legend_wrap=False):
        legend = place_legend(ax, loc="above")
    assert legend is not None
    assert not any("\n" in t.get_text() for t in legend.get_texts())


def test_mathtext_and_broken_names_are_not_rewrapped() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    names = [
        r"$\alpha$ coefficient of the very long regional model run",
        "Already broken\nby the caller into two lines of text here",
    ]
    for name in names:
        ax.plot([0, 1], [0, 1], label=name)
    legend = place_legend(ax, loc="above")
    assert legend is not None
    assert [t.get_text() for t in legend.get_texts()] == names


# -------------------------------------------- rung 4: the layout's second look
CITIES = (
    "Seoul", "Busan", "Incheon", "Daegu", "Daejeon",
    "Gwangju", "Ulsan", "Suwon", "Sejong", "Jeju",
)  # fmt: skip


def test_a_wrapped_legend_above_settles_in_the_layout() -> None:
    """The layout ends where placing the legend again changes nothing.

    Ten long names above a 12 cm plot fit only wrapped while the plot is
    short; judged against the plot height of the moment, the wrapped
    legend gave the plot room, unwrapped there, took it back and wrapped
    again until the layout's step limit.
    """
    fig, ax = _report()
    x = np.arange(12)
    rng = np.random.default_rng(17)
    for i, city in enumerate(CITIES):
        ax.plot(
            x,
            50
            + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / 10)
            + rng.normal(0, 2, x.size),
            label=f"{city} metropolitan region, seasonally adjusted (2019 = 100)",
        )
    ax.set(xlabel="Month", ylabel="Index")
    legend = place_legend(ax)
    assert legend is not None and legend._dm_outside_fallback is True
    dm.simple_layout(fig)
    assert settle_legends(fig, drawn_renderer(fig)) is False


def test_layout_replans_rows_for_the_fitted_width() -> None:
    """Rows are chosen again once simple_layout has widened the Axes."""
    dm.style.use("report")
    fig, axs = plt.subplots(2, 2, figsize=dm.figsize("17cm", "12cm"))
    for ax in axs.flat:
        _dense(ax, 6, " metropolitan region")
        place_legend(ax)
    before = [legend_ncols(ax.get_legend()) for ax in axs.flat]
    dm.simple_layout(fig)
    renderer = drawn_renderer(fig)
    after = []
    for ax in axs.flat:
        legend = ax.get_legend()
        assert legend is not None
        assert not any("\n" in t.get_text() for t in legend.get_texts())
        width = legend.get_window_extent(renderer).width
        assert width <= ax.get_window_extent(renderer).width + 0.5
        after.append(legend_ncols(legend))
    assert after != before  # more columns fit the laid-out width
    assert (
        dm.validate_figure(
            fig, checks=("LEGEND_ON_DATA", "LEGEND_OVERLAP"), quiet=True
        )
        == []
    )


def _top_free_lines(ax) -> None:
    """Two lines in the lower 60 % of the plot: the top band is free if tall enough."""
    ax.set(xlim=(0, 10), ylim=(0, 10))
    x = np.linspace(0, 10, 40)
    ax.plot(x, 3 + 3 * np.sin(x), label="North")
    ax.plot(x, 3 + 3 * np.cos(x), label="South")


def test_an_outside_legend_comes_in_once_the_axes_has_room() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    _top_free_lines(ax)
    ax.set_position((0.1, 0.45, 0.8, 0.1))  # too short for the band
    legend = place_legend(ax)
    assert legend is not None and legend._dm_outside_fallback is True
    ax.set_position((0.1, 0.1, 0.8, 0.8))
    renderer = drawn_renderer(fig)
    assert settle_legends(fig, renderer) is True
    moved = ax.get_legend()
    assert moved is not None and moved is not legend
    assert moved._dm_collision_free is True
    assert not getattr(moved, "_dm_outside_fallback", False)
    assert _covers(fig) == []


def test_an_inside_legend_is_never_sent_out_by_the_layout() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    _top_free_lines(ax)
    ax.set_position((0.1, 0.1, 0.8, 0.8))
    legend = place_legend(ax)
    assert legend is not None and legend._dm_collision_free is True
    ax.set_position((0.1, 0.45, 0.8, 0.1))
    assert settle_legends(fig, drawn_renderer(fig)) is False
    assert ax.get_legend() is legend


@pytest.mark.parametrize(
    "names",
    # "swapped" keeps the legend's size and look: only its entries tell.
    [("Renamed", "South"), ("South", "North")],
    ids=["renamed", "swapped"],
)
def test_the_layout_leaves_a_legend_edited_since_alone(
    names: tuple[str, str],
) -> None:
    fig, ax = _report()
    _top_free_lines(ax)
    ax.set_position((0.1, 0.45, 0.8, 0.1))
    legend = place_legend(ax)
    assert legend is not None
    for text, name in zip(legend.get_texts(), names, strict=True):
        text.set_text(name)
    ax.set_position((0.1, 0.1, 0.8, 0.8))
    assert settle_legends(fig, drawn_renderer(fig)) is False
    assert ax.get_legend() is legend


def test_a_raw_legend_is_not_moved_by_the_layout() -> None:
    fig, ax = _report()
    _dense(ax, 5)
    legend = ax.legend(loc="upper right")
    dm.simple_layout(fig)
    assert ax.get_legend() is legend
    assert [w.detail["covered"] for w in _covers(fig)] == [["line"]]


def test_two_long_names_wrap_onto_fewer_lines_when_more_gain_little() -> None:
    """Capture 10: one column of two lines, not two columns of four.

    Two columns would leave the plot 2 % of the canvas more; a name
    broken into more lines needs 5 % (LINES_GAIN).
    """
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("15.4cm", "10.5cm"))
    x = np.arange(12)
    rng = np.random.default_rng(9)
    for i, city in enumerate(("Seoul", "Busan")):
        y = 10 + 1.5 * i + (4 + 0.25 * i) * x + rng.normal(0, 0.6, x.size)
        ax.plot(x, y, label=f"{city}{LONG}")
    ax.set(xlabel="Month", ylabel="Index")
    place_legend(ax)
    dm.simple_layout(fig)
    legend = ax.get_legend()
    assert legend is not None
    assert legend_ncols(legend) == 1
    assert [t.get_text().count("\n") + 1 for t in legend.get_texts()] == [2, 2]
    assert settle_legends(fig, drawn_renderer(fig)) is False


# ------------------------------------- the layout's scope and the caller's edits
def _short_legend_panel(ax) -> None:
    """Lines in the lower 60 % of a plot: the legend fits in once it is tall."""
    ax.set(xlim=(0, 10), ylim=(0, 10))
    x = np.linspace(0, 10, 40)
    ax.plot(x, 3 + 3 * np.sin(x), label="North")
    ax.plot(x, 3 + 3 * np.cos(x), label="South")


def _scoped(case: str):
    """A figure whose ``other`` panel is outside the GridSpec laid out.

    ``other``'s legend went outside while the panel was flat; the panel is
    then grown, so a layout that reached it would bring the legend in.
    """
    dm.style.use("report")
    fig = plt.figure(figsize=dm.figsize("17cm", "12cm"))
    gs = fig.add_gridspec(1, 1, left=0.1, right=0.45)
    fig.add_subplot(gs[0]).plot([0, 1], [0, 1])
    match case:
        case "add_axes":
            other = fig.add_axes((0.6, 0.45, 0.3, 0.05))
        case "gridspec":
            other = fig.add_subplot(fig.add_gridspec(1, 1, left=0.6)[0])
            other.set_position((0.6, 0.45, 0.3, 0.05))
        case _:  # nested in the laid-out GridSpec's neighbour cell
            outer = fig.add_gridspec(1, 2, left=0.55)
            other = fig.add_subplot(outer[0, 1].subgridspec(2, 1)[0])
            other.set_position((0.6, 0.45, 0.3, 0.05))
    _short_legend_panel(other)
    legend = place_legend(other)
    assert legend is not None and legend._dm_outside_fallback is True
    other.set_position((0.6, 0.1, 0.3, 0.8))
    return fig, gs, other, legend


@pytest.mark.parametrize("case", ["add_axes", "gridspec", "nested"])
def test_the_layout_places_again_only_the_legends_it_lays_out(
    case: str,
) -> None:
    fig, gs, other, legend = _scoped(case)
    dm.simple_layout(fig, gs=gs, use_all_axes=False)
    assert other.get_legend() is legend
    # The same figure laid out whole brings the legend in.
    dm.simple_layout(fig)
    assert other.get_legend() is not legend
    assert not getattr(other.get_legend(), "_dm_outside_fallback", False)


def _above_ten(**kw):
    fig, ax = _report()
    _dense(ax, 10)
    legend = place_legend(ax, loc="above", **kw)
    assert legend is not None
    return fig, ax, legend


def _font(legend) -> None:
    for text in legend.get_texts():
        text.set_fontsize(15)


def _frame_off(legend) -> None:
    legend.set_frame_on(False)


def _frame_alpha(legend) -> None:
    legend.get_frame().set_alpha(0.2)


def _moved(legend) -> None:
    legend.set_loc("lower left")


# Legend.set_ncols on a built legend redraws nothing (matplotlib 3.11 only
# stores the count), so it is not an edit a reader sees.
@pytest.mark.parametrize("edit", [_font, _frame_off, _frame_alpha, _moved])
def test_an_edited_legend_is_the_callers(edit) -> None:
    """A legend restyled or moved through the returned Legend stays as edited."""
    fig, ax, legend = _above_ten(fontsize=9, frameon=True)
    edit(legend)
    before = (
        [t.get_fontsize() for t in legend.get_texts()],
        legend.get_frame_on(),
        legend.get_frame().get_alpha(),
        legend_ncols(legend),
    )
    dm.simple_layout(fig)
    assert ax.get_legend() is legend
    after = (
        [t.get_fontsize() for t in legend.get_texts()],
        legend.get_frame_on(),
        legend.get_frame().get_alpha(),
        legend_ncols(legend),
    )
    assert after == before


def test_an_unedited_legend_is_placed_again() -> None:
    """The control for the edits above: the same legend left alone is rebuilt."""
    fig, ax, legend = _above_ten(fontsize=9, frameon=True)
    dm.simple_layout(fig)
    assert ax.get_legend() is not legend
    assert legend_ncols(ax.get_legend()) != legend_ncols(legend)


def test_an_inside_legend_anchored_elsewhere_is_the_callers() -> None:
    fig, ax = _report()
    _top_free_lines(ax)
    ax.set_position((0.1, 0.45, 0.8, 0.1))
    legend = place_legend(ax)
    assert legend is not None
    legend.set_bbox_to_anchor((0.0, 0.0, 0.5, 1.0), transform=ax.transAxes)
    ax.set_position((0.1, 0.1, 0.8, 0.8))
    assert settle_legends(fig, drawn_renderer(fig)) is False
    assert ax.get_legend() is legend


# -------------------------------------------------- what the caller fixes
def test_an_asked_column_count_is_the_only_one_tried() -> None:
    fig, ax = _report("17cm")
    ax.plot([0, 10], [0, 1], label="Low")
    ax.plot([0, 10], [0.5, 1.5], label="Lower")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = place_legend(ax, ncols=2)
    assert legend is not None
    assert legend_ncols(legend) == 2
    dm.simple_layout(fig)
    assert legend_ncols(ax.get_legend()) == 2


def test_a_matplotlib_loc_is_used_as_given() -> None:
    fig, ax = _report()
    _dense(ax, 5)
    legend = place_legend(ax, loc="lower left")
    assert legend is not None
    assert not hasattr(legend, "_dm_best_source")
    dm.simple_layout(fig)
    assert ax.get_legend() is legend


# ------------------------------------------------------------- the budget
def test_one_draw_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    fig, ax = _report()
    _dense(ax, 20, LONG)
    calls = {"n": 0}
    draw = FigureCanvasAgg.draw

    def counting(self, *a, **k):
        calls["n"] += 1
        return draw(self, *a, **k)

    monkeypatch.setattr(FigureCanvasAgg, "draw", counting)
    place_legend(ax)
    assert calls["n"] == 1


def test_trial_legends_never_search_the_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trial is measured where it sits; matplotlib's "best" search is not run."""
    from matplotlib.legend import Legend

    fig, ax = _report()
    _dense(ax, 10, LONG)
    searches = {"n": 0}
    find = Legend._find_best_position

    def counting(self, *a, **k):
        searches["n"] += 1
        return find(self, *a, **k)

    monkeypatch.setattr(Legend, "_find_best_position", counting)
    legend = place_legend(ax)
    dm.simple_layout(fig)
    assert legend is not None and legend._dm_outside_fallback is True
    assert searches["n"] == 0
