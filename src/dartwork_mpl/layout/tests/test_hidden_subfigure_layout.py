"""The layout neither measures nor avoids what a hidden SubFigure holds,
and reads a SubFigure's Axes on the canvas where the root grid measures it.

``SubFigure.set_visible(False)`` hides its Axes while their own flags stay
on. A hidden SubFigure's Axes still counted as a neighbour an axis name had
to clear (``_in_the_way``), as content ``tight_crop`` kept and as Axes a
root grid named by ``gs=`` measured. Each oracle is the same figure without
that hidden content: it draws the same pixels.

The root grid measuring a SubFigure's Axes reads its position as a fraction
of the canvas (``root_position``): the root grid's panel comes out as it
does when both panels sit on one grid (#666's surviving mutant).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.layout._fit_labels import _in_the_way

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


@pytest.fixture(autouse=True)
def _style() -> Iterator[None]:
    dm.style.use("report")
    yield
    plt.close("all")


def _small(ax: Axes) -> None:
    ax.plot([0, 1, 2], [3, 1, 2])
    ax.set(xlabel="Time [h]", ylabel="Load [kW]")


def _big(ax: Axes) -> None:
    """Content reaching far past its plot: long tick labels and names."""
    ax.plot([0, 1], [0, 123456789])
    ax.set_xticks([0, 0.5, 1], ["A long first tick", "middle", "a long last"])
    ax.set(xlabel="A long horizontal axis name [units]", ylabel="Big [units]")


def _in_the_way_of(other: str) -> bool:
    """Whether the axis name ladder finds a panel in the x name's way, a
    second SubFigure in the same cell holding ``other``: "none", a "shown"
    panel or a "hidden" one. The name is wider than its plot (the middle
    third), not than the canvas, so only another panel can be in its way."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    cell = fig.add_gridspec(1, 1)[0]
    mine, theirs = fig.add_subfigure(cell), fig.add_subfigure(cell)
    ax = mine.add_subplot(1, 3, 2)
    ax.plot([0, 1], [0, 1])
    ax.set(xlabel="An axis name a little wider than its own plot [units]")
    if other != "none":
        _big(theirs.subplots())
    if other == "hidden":
        theirs.set_visible(False)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return _in_the_way(ax.xaxis.label, ax, fig, renderer)


def test_an_axis_name_finds_no_hidden_subfigures_panel_in_its_way() -> None:
    assert not _in_the_way_of("none")
    assert _in_the_way_of("shown")  # the control: the panel is in its way
    assert not _in_the_way_of("hidden")


def _cropped(hidden_content: bool) -> tuple[float, float]:
    """The cropped size of a root grid's panel beside a hidden SubFigure
    (with content, or empty): every SubFigure hidden, the root's panels are
    cropped as on a figure without SubFigures."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    grid = fig.add_gridspec(1, 2)
    _small(fig.add_subplot(grid[0, 0]))
    sub = fig.add_subfigure(grid[0, 1])
    if hidden_content:
        _big(sub.subplots())
    sub.set_visible(False)
    return dm.tight_crop(fig)


def test_tight_crop_keeps_no_room_for_a_hidden_subfigure() -> None:
    assert _cropped(True) == pytest.approx(_cropped(False), abs=1e-6)


def _past_canvas(fig: Figure) -> float:
    """How far any drawn artist runs past the canvas after a draw (px)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w, h = fig.bbox.width, fig.bbox.height
    boxes = [
        ax.get_tightbbox(renderer)
        for ax in fig.axes
        if ax.get_figure(root=False).get_visible()  # type: ignore[union-attr]
    ]
    for holder in (
        fig,
        *fig.subfigs,
        *[s for f in fig.subfigs for s in f.subfigs],
    ):
        if not holder.get_visible():
            continue
        for art in (*holder.texts, *holder.legends):
            boxes.append(art.get_window_extent(renderer))
    return max(
        [0.0] + [max(0.0, -b.x0, b.x1 - w, -b.y0, b.y1 - h) for b in boxes if b]
    )


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("artist", ["suptitle", "supxlabel", "legend"])
@pytest.mark.parametrize("right", ["empty", "hidden", "shown"])
def test_tight_crop_cuts_no_visible_subfigure_artist(
    nested: bool, artist: str, right: str
) -> None:
    """A SubFigure is placed as a fraction of the figure, which a crop
    cannot move: its title, label or legend ran 135 px past the cropped
    canvas (review of #670). A figure with a shown SubFigure keeps its
    size, and every drawn artist stays on the canvas."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, other = fig.subfigures(1, 2)
    owner = left.subfigures(1, 1) if nested else left
    ax = owner.subplots()
    long = "Visible SubFigure title with a longer description"
    ax.plot([0, 1], [0, 1], label=long if artist == "legend" else "Series")
    ax.set(xlabel="Time", ylabel="Response")
    owner.suptitle(long if artist == "suptitle" else "Visible title")
    owner.supxlabel(long if artist == "supxlabel" else "Horizontal label")
    owner.legend(loc="upper center")
    if right != "empty":
        _big(other.subplots())
    if right == "hidden":
        other.set_visible(False)
    dm.simple_layout(fig)
    size = tuple(fig.get_size_inches())
    with pytest.warns(UserWarning, match="SubFigure"):
        assert dm.tight_crop(fig) == pytest.approx(size)
    assert _past_canvas(fig) <= 0.5


def _root_panel(hidden_content: bool) -> tuple[float, ...]:
    """The root grid's panel after ``gs=`` on it, a SubFigure beside it."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    grid = fig.add_gridspec(1, 2)
    ax = fig.add_subplot(grid[0, 0])
    _small(ax)
    sub = fig.add_subfigure(grid[0, 1])
    if hidden_content:
        _big(sub.subplots())
        sub.set_visible(False)
    dm.simple_layout(fig, gs=grid)
    return tuple(ax.get_position().bounds)


def test_a_root_grid_measures_no_hidden_subfigures_axes() -> None:
    assert _root_panel(True) == pytest.approx(_root_panel(False), abs=1e-9)


def _first_panel(fig: Figure) -> tuple[float, ...]:
    return tuple(fig.axes[0].get_window_extent().bounds)


def test_a_root_grid_reads_a_subfigures_axes_on_the_canvas() -> None:
    """Measured by the root grid, a panel in a SubFigure places the root
    grid's panel as it does when both are one grid's."""
    one = plt.figure(figsize=dm.figsize("17cm", "wide"))
    grid = one.add_gridspec(1, 2)
    _small(one.add_subplot(grid[0, 0]))
    _small(one.add_subplot(grid[0, 1]))
    dm.simple_layout(one, gs=grid)
    one.canvas.draw()
    split = plt.figure(figsize=dm.figsize("17cm", "wide"))
    grid = split.add_gridspec(1, 2)
    _small(split.add_subplot(grid[0, 0]))
    _small(split.add_subfigure(grid[0, 1]).subplots())
    dm.simple_layout(split, gs=grid)
    split.canvas.draw()
    assert _first_panel(split) == pytest.approx(_first_panel(one), abs=1.0)
