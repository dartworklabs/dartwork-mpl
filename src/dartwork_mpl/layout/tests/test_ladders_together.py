"""The label ladder (``fit_labels``) and place_legend's ladder in one layout.

Both resize the Axes from inside ``dm.simple_layout``: the label ladder
turns or wraps tick labels and fits the margins again; each margin fit
places ``place_legend``'s legends again at the size the Axes have then.
The oracle is the drawn figure: the layout ends, a second layout draws the
same pixels, a scoped layout (``use_all_axes=False``) leaves every other
Axes' legend and labels as they were, and edits the caller made to a
legend or to tick labels stay.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer
from dartwork_mpl.validate._checks.tick_overlap import check_tick_overlap

_ONE_WORD = [
    "Thermoregulation",
    "Electrification",
    "Decarbonisation",
    "Interconnection",
] * 2


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _lines_and_names(ax, n_series: int) -> None:
    """Crowded one-word ticks (they turn) under lines that fill the plot."""
    x = np.arange(len(_ONE_WORD))
    for i in range(n_series):
        ax.plot(x, 5 + 4 * np.sin(x / 1.3 + i), label=f"Scenario {i + 1}")
    ax.set_xticks(x, _ONE_WORD)


def _both(width: str, n_series: int):
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    _lines_and_names(ax, n_series)
    legend = dm.place_legend(ax)
    assert legend is not None
    return fig, ax, legend


def _pixels(fig) -> bytes:
    fig.canvas.draw()
    return bytes(fig.canvas.buffer_rgba())


def _ticks(ax) -> list[tuple[str, float]]:
    ax.get_figure().canvas.draw()
    return [(t.get_text(), t.get_rotation()) for t in ax.get_xticklabels()]


def _legend_state(ax) -> tuple:
    legend = ax.get_legend()
    return (
        id(legend),
        legend._ncols,
        [t.get_text() for t in legend.get_texts()],
    )


@pytest.mark.parametrize(("width", "n_series"), [("9cm", 6), ("12cm", 10)])
def test_turned_ticks_and_an_outside_legend_settle_together(
    width: str, n_series: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    fig, ax, _legend = _both(width, n_series)
    draws = {"n": 0}
    draw = FigureCanvasAgg.draw

    def counting(self, *args, **kwargs):
        draws["n"] += 1
        return draw(self, *args, **kwargs)

    monkeypatch.setattr(FigureCanvasAgg, "draw", counting)
    dm.simple_layout(fig)
    assert draws["n"] <= 12  # 6-7 measured; the two ladders do not trade
    assert {angle for _text, angle in _ticks(ax)} == {30.0}
    assert ax.get_legend()._dm_outside_fallback is True
    found = {w.check_id for w in dm.validate_figure(fig, quiet=True)}
    assert not {i for i in found if i.startswith("LEGEND")}
    fig.canvas.draw()
    assert check_tick_overlap(fig, get_renderer(fig)) == []


@pytest.mark.parametrize(("width", "n_series"), [("9cm", 6), ("12cm", 10)])
def test_a_second_layout_draws_the_same_figure(
    width: str, n_series: int
) -> None:
    fig, ax, _legend = _both(width, n_series)
    dm.simple_layout(fig)
    first, legend = _pixels(fig), ax.get_legend()
    dm.simple_layout(fig)
    assert ax.get_legend() is legend
    assert _pixels(fig) == first


def _two_grids(share: bool):
    """A plain left grid and a right grid whose panel turns its ticks and
    holds a place_legend legend; with ``share``, the right Axes shares x
    (one formatter) with the left one.

    The right legend is placed while its panel is flat and the panel is
    grown after, so a layout that reached it would place it again.
    """
    dm.style.use("report")
    fig = plt.figure(figsize=dm.figsize("17cm", "standard"))
    a = fig.add_gridspec(1, 1, left=0.06, right=0.4)
    b = fig.add_gridspec(1, 1, left=0.55, right=0.95)
    left = fig.add_subplot(a[0])
    right = fig.add_subplot(b[0], sharex=left if share else None)
    left.plot([0, 7], [0, 1])
    _lines_and_names(right, 6)
    right.set_position((0.55, 0.45, 0.4, 0.08))
    assert dm.place_legend(right) is not None
    right.set_position((0.55, 0.15, 0.4, 0.75))
    return fig, a, right


@pytest.mark.parametrize("share", [False, True], ids=["own_x", "shared_x"])
def test_a_scoped_layout_leaves_the_other_grids_legend_and_labels(
    share: bool,
) -> None:
    fig, a, right = _two_grids(share)
    before = (_legend_state(right), _ticks(right))
    dm.simple_layout(fig, gs=a, use_all_axes=False)
    assert (_legend_state(right), _ticks(right)) == before
    # The same figure laid out whole fits the right panel too.
    dm.simple_layout(fig)
    assert (_legend_state(right), _ticks(right)) != before


def test_a_scoped_layout_fits_its_margins_to_its_own_axes() -> None:
    """The other grid's panel hangs off the bottom of the figure; the
    margins of the grid laid out do not make room for it."""

    def left_box(hanging: bool) -> tuple[float, ...]:
        fig, a, right = _two_grids(share=False)
        if not hanging:
            right.set_xticks([])
        right.set_position((0.55, 0.02, 0.4, 0.9))
        dm.simple_layout(fig, gs=a, use_all_axes=False)
        box = tuple(round(v, 6) for v in fig.axes[0].get_position().bounds)
        plt.close(fig)
        return box

    assert left_box(hanging=True) == left_box(hanging=False)


def test_a_scoped_layout_keeps_a_nested_panels_legend_and_the_root_spacing() -> (
    None
):
    """Laid out alone, the root grid neither grows the spacing its nested
    panels share nor places again the legend of a nested panel."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("17cm", "standard"))
    root = fig.add_gridspec(1, 3)
    first, second = fig.add_subplot(root[0]), fig.add_subplot(root[1])
    inner = root[2].subgridspec(2, 1)
    nested = [fig.add_subplot(inner[0]), fig.add_subplot(inner[1])]
    for ax in (first, *nested):
        ax.plot([0, 1], [0, 1])
    second.barh([f"Category name {i}" for i in range(4)], [1, 2, 3, 4])
    _lines_and_names(nested[0], 6)
    assert dm.place_legend(nested[0]) is not None
    before = _legend_state(nested[0])
    dm.simple_layout(fig, gs=root, use_all_axes=False)
    assert root.wspace is None
    assert _legend_state(nested[0]) == before


def test_edits_to_a_legend_and_to_tick_labels_both_stay() -> None:
    fig, ax, _legend = _both("9cm", 6)
    dm.simple_layout(fig)
    legend = ax.get_legend()
    legend.legend_handles[0].set_color("red")
    for label in ax.get_xticklabels():
        label.set_rotation(60)
    dm.simple_layout(fig)
    assert ax.get_legend() is legend
    assert legend.legend_handles[0].get_color() == "red"
    assert {angle for _text, angle in _ticks(ax)} == {60.0}


# ── with what the label ladder keeps between calls (#655) ──────────────
#
# A layout starts the margins where the call before started them (the
# start edges it records) and keeps the y ticks an axis had before its
# names turned (the tick budget). Each margin fit places place_legend's
# legends again; together they still end, and draw the same each call.


def _dense(ax, n_series: int, suffix: str = "") -> None:
    x = np.linspace(0, 11, 60)
    for i in range(n_series):
        ax.plot(
            x,
            50 + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / n_series),
            label=f"Region {i + 1}{suffix}",
        )


def _grid_of_legends():
    """Four panels whose long-named legends the layout places again."""
    dm.style.use("report")
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "12cm"))
    for ax in axes.flat:
        _dense(ax, 6, " metropolitan region")
        dm.place_legend(ax)
    return fig


def _widened():
    """A legend planned above a 9 cm panel, laid out at 17 cm: the first
    fit plans it again for the wider plot."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    _dense(ax, 10)
    dm.place_legend(ax, loc="above")
    fig.set_size_inches(*dm.figsize("17cm", "standard"))
    return fig


def _grouped(width: str, top: float, legend: bool = True):
    """Grouped bars with crowded one-word names (they turn 45 degrees)
    and a value axis whose ticks matplotlib picks by its length."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    x = np.arange(len(_ONE_WORD))
    for i in range(4):
        ax.bar(
            x + 0.2 * (i - 1.5),
            top * (0.35 + 0.6 * np.abs(np.sin(x + i))),
            width=0.2,
            label=f"Scenario {i + 1}",
        )
    ax.set_xticks(x, _ONE_WORD)
    if legend:
        assert dm.place_legend(ax) is not None
    return fig, ax


def _overlaps(fig) -> set[str]:
    return {
        w.check_id
        for w in dm.validate_figure(fig, quiet=True)
        if w.check_id.startswith(("LEGEND", "TICK_OVERLAP", "OVERLAP", "CROSS"))
    }


@pytest.mark.parametrize(
    "build",
    [_grid_of_legends, _widened, lambda: _grouped("17cm", 13.0)[0]],
    ids=["grid", "widened", "turned_bars"],
)
def test_every_call_draws_the_same_figure_and_keeps_the_legends(build) -> None:
    fig = build()
    shots, legends = [], []
    for _call in range(3):
        dm.simple_layout(fig)
        shots.append(_pixels(fig))
        legends.append([ax.get_legend() for ax in fig.axes])
    assert shots[1] == shots[0]
    assert shots[2] == shots[0]
    assert all(a is b for a, b in zip(legends[0], legends[2], strict=True))
    assert not _overlaps(fig)


def test_a_widened_legend_is_planned_again_once_and_then_kept() -> None:
    """Planned in five columns at 9 cm, the legend takes all ten across
    the 17 cm plot on the first call; later calls start where the first
    did and keep that legend."""
    fig = _widened()
    ax = fig.axes[0]
    assert ax.get_legend()._ncols == 5
    dm.simple_layout(fig)
    legend = ax.get_legend()
    assert legend._ncols == 10
    dm.simple_layout(fig)
    dm.simple_layout(fig)
    assert ax.get_legend() is legend


@pytest.mark.parametrize(("width", "top"), [("14.5cm", 63.0), ("17cm", 13.0)])
def test_a_kept_tick_budget_and_an_outside_legend_end_together(
    width: str, top: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The names turn, the value axis keeps the ticks it had, and the
    legend goes above; the layout ends and finds no more overlaps than
    the same bars without the legend."""
    bare, bare_ax = _grouped(width, top, legend=False)
    dm.simple_layout(bare)
    fig, ax = _grouped(width, top)
    auto = ax.yaxis.get_major_locator()
    draws = {"n": 0}
    draw = FigureCanvasAgg.draw

    def counting(self, *args, **kwargs):
        draws["n"] += 1
        return draw(self, *args, **kwargs)

    monkeypatch.setattr(FigureCanvasAgg, "draw", counting)
    dm.simple_layout(fig)
    assert draws["n"] <= 20  # 8-15 measured
    assert ax.yaxis.get_major_locator() is not auto  # the budget is kept
    assert {angle for _text, angle in _ticks(ax)} == {45.0}
    assert ax.get_legend()._dm_outside_fallback is True
    assert _overlaps(fig) <= _overlaps(bare) == set()
    first = _pixels(fig)
    dm.simple_layout(fig)
    assert _pixels(fig) == first


def test_a_thinned_date_axis_under_an_outside_legend_settles_by_the_second_call() -> (
    None
):
    """The documented exception: the first call thins the crowded months
    and keeps the thinned locator, so the second can still move them;
    from the second on, each call draws the same and keeps the legend."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    first = np.datetime64("2021-01", "M")
    months = np.arange(first, first + np.timedelta64(36, "M"))
    for i in range(6):
        ax.plot(
            months.astype("datetime64[D]"),
            np.sin(np.arange(36) / 3 + i),
            label=f"Region {i + 1}",
        )
    dm.place_legend(ax)
    shots = []
    for _call in range(3):
        dm.simple_layout(fig)
        shots.append((_pixels(fig), ax.get_legend()))
    assert shots[2][0] == shots[1][0]
    assert shots[2][1] is shots[1][1]
    assert ax.get_legend()._dm_outside_fallback is True
    assert not _overlaps(fig)


def _stacked(placed: bool):
    """advanced/stacked_bar in presentation: three components over four
    periods, the legend in three columns either written by hand at the
    top left (wider than the plot the canvas leaves) or placed by
    place_legend."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=4, n_series=3))
    bottom = np.zeros(4)
    for name, values in (
        ("Solar", [82, 90, 101, 118]),
        ("Wind", [40, 45, 47, 55]),
        ("Gas", [28, 26, 22, 19]),
    ):
        ax.bar(np.arange(4), values, bottom=bottom, width=0.55, label=name)
        bottom += values
    ax.set_xticks(np.arange(4), ["P1", "P2", "P3", "P4"])
    ax.set_ylabel("Generation (MWh)")
    ax.set_xlabel("Period")
    if placed:
        dm.place_legend(ax, fontsize=dm.fs(-1), frameon=False)
    else:
        ax.legend(loc="upper left", fontsize=dm.fs(-1), frameon=False, ncol=3)
    return fig, ax


@pytest.mark.parametrize("placed", [True, False], ids=["placed", "by_hand"])
def test_the_ladder_climbs_only_once_the_legends_have_settled(
    placed: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The margin fit places the legend again on each step, so the step
    it settles on has the legend where it ends. A legend the layout
    places settles and the label ladder runs after it; one wider than
    the canvas leaves the plot moves the margins on every step, and the
    ladder is not climbed (#655)."""
    import dartwork_mpl.layout._simple_layout as simple

    deltas: list[float] = []
    climbs: list[bool] = []
    fit, climb = simple._fit_margins, simple.climb

    def fitted(*args, **kwargs):
        step, last = fit(*args, **kwargs)
        deltas.append(step.delta_px)
        return step, last

    def climbed(*args, **kwargs):
        climbs.append(True)
        return climb(*args, **kwargs)

    monkeypatch.setattr(simple, "_fit_margins", fitted)
    monkeypatch.setattr(simple, "climb", climbed)
    fig, ax = _stacked(placed)
    dm.simple_layout(fig, margin=dm.inch(0.08))
    assert bool(deltas[0] < simple._CONVERGE_TOL_PX) == placed  # settled
    assert bool(climbs) == placed
    fig.canvas.draw()
    box = ax.get_legend().get_window_extent(get_renderer(fig))
    assert bool(box.x0 >= -0.5 and box.x1 <= fig.bbox.x1 + 0.5) == placed
    if placed:
        assert not _overlaps(fig)


def test_closed_figures_with_placed_legends_are_collectible() -> None:
    """Legends the layout placed again keep their state on the legend and
    its Axes, not in a module record: a closed figure is collected."""
    import gc
    import weakref

    def inside():
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot([0, 1], [0, 1], label="Rising")
        dm.place_legend(ax)
        return fig

    refs = []
    for build in (
        _grid_of_legends,
        _widened,
        inside,
        lambda: _grouped("17cm", 13.0)[0],
    ):
        fig = build()
        dm.simple_layout(fig)
        dm.simple_layout(fig)
        dm.validate_figure(fig, quiet=True)
        refs.append(weakref.ref(fig))
        plt.close(fig)
    del fig
    gc.collect()
    assert [ref() is None for ref in refs] == [True] * len(refs)
