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
