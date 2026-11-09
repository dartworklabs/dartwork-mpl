"""A SubFigure's ``dm.figure_legend`` legend sits past its title, as on the root figure.

``figure_legend`` anchors a legend above a SubFigure under the SubFigure's
suptitle as it stands when called. ``simple_layout`` then puts a SubFigure
title the library places under the figure-level text above it (a root
suptitle), and a title added after the call was never seen: the legend lay
on the title (LEGEND_OVERLAP). Now each SubFigure's title is placed, then
its figure legends past it and past the texts above, then its panels: the
legend keeps the gap it keeps under a title it was called after
(``legend.borderaxespad``), and the panels keep clear of it.

A legend the caller placed (``subfig.legend``, with or without
``bbox_to_anchor``) stays where it is; LEGEND_OVERLAP reports what it
covers.
"""

from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

TITLE = "Measured load at site A in winter"
ROOT_TITLE = "Electric load at both sites, winter 2025"


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _lines(ax) -> None:
    x = np.linspace(0, 10, 40)
    for i in range(3):
        ax.plot(x, np.sin(x / 2 + i) + i, label=f"Series {chr(65 + i)}")
    ax.set(xlabel="Time [h]", ylabel="Load [kW]")


def _scene(name: str):
    """A 1x2 SubFigure figure; the left one holds the legend of ``name``."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    _lines(right.subplots())
    right.suptitle("Site B")
    holders = [left]
    if name == "nested":
        _lines(left.subplots())
        fig.suptitle(ROOT_TITLE)
        right.clear()
        holders = list(right.subfigures(2, 1))
        for k, inner in enumerate(holders):
            _lines(inner.subplots())
            inner.suptitle(f"Site B, feeder {k + 1}")
            dm.figure_legend(inner, loc="above")
        return fig, holders
    _lines(left.subplots())
    if name == "title_after":  # the title comes after the legend
        dm.figure_legend(left, loc="above")
        left.suptitle(TITLE)
    elif name == "under_root_title":  # the layout moves the title down
        left.suptitle(TITLE)
        fig.suptitle(ROOT_TITLE)
        dm.figure_legend(left, loc="above")
    elif name == "root_title_only":  # no title of its own, a root one over it
        fig.suptitle(ROOT_TITLE)
        dm.figure_legend(left, loc="above")
    elif name == "title_first":  # the control: called after its title
        left.suptitle(TITLE)
        dm.figure_legend(left, loc="above")
    return fig, holders


def _layout(fig) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dm.simple_layout(fig)


def _titles_above(holder):
    """The suptitles of ``holder`` and of every (Sub)Figure above it."""
    found = []
    while holder is not None:
        title = getattr(holder, "_suptitle", None)
        if title is not None and title.get_text().strip():
            found.append(title)
        parent = holder.get_figure(root=False)
        holder = None if parent is holder else parent
    return found


def _gap_px(fig, holder) -> float:
    """The legend's top below the lowest title over it (px; < 0 overlaps)."""
    renderer = drawn_renderer(fig)
    (legend,) = holder.legends
    box = legend.get_window_extent(renderer)
    over = [
        t.get_window_extent(renderer)
        for t in _titles_above(holder)
        if t.get_window_extent(renderer).x0 < box.x1
        and t.get_window_extent(renderer).x1 > box.x0
    ]
    return float(min(b.y0 for b in over) - box.y1)


def _pad_px(fig, holder) -> float:
    (legend,) = holder.legends
    return (
        float(legend.borderaxespad)
        * legend.prop.get_size_in_points()
        * fig.dpi
        / 72
    )


def _kinds(fig) -> list[str]:
    found = dm.validate_figure(fig, checks=("LEGEND_OVERLAP",), quiet=True)
    return [w.check_id for w in found]


@pytest.mark.parametrize(
    "name", ["title_after", "under_root_title", "root_title_only", "nested"]
)
def test_a_subfigure_legend_sits_under_its_title_as_on_the_root(
    name: str,
) -> None:
    fig, holders = _scene(name)
    _layout(fig)
    for holder in holders:
        # The gap a legend called after its title keeps (borderaxespad).
        assert _gap_px(fig, holder) == pytest.approx(
            _pad_px(fig, holder), abs=1.0
        )
    assert _kinds(fig) == []


@pytest.mark.parametrize(
    "name", ["title_after", "under_root_title", "root_title_only", "nested"]
)
def test_the_panels_keep_clear_of_the_moved_legend(name: str) -> None:
    fig, holders = _scene(name)
    _layout(fig)
    renderer = drawn_renderer(fig)
    for holder in holders:
        (legend,) = holder.legends
        box = legend.get_window_extent(renderer)
        for ax in fig.axes:
            plot = ax.get_window_extent(renderer)
            assert not (box.overlaps(plot) and box.y0 < plot.y1 - 0.5)


def test_a_legend_called_after_its_title_stays_where_it_was() -> None:
    fig, (left,) = _scene("title_first")
    (legend,) = left.legends
    before = legend.get_bbox_to_anchor().frozen()
    _layout(fig)
    assert np.allclose(
        legend.get_bbox_to_anchor().frozen().extents, before.extents
    )
    assert _gap_px(fig, left) == pytest.approx(_pad_px(fig, left), abs=1.0)


@pytest.mark.parametrize(
    "anchored", [False, True], ids=["loc", "bbox_to_anchor"]
)
def test_a_legend_the_caller_placed_stays_and_is_reported(
    anchored: bool,
) -> None:
    """``subfig.legend`` is the caller's: not moved; LEGEND_OVERLAP speaks."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    _lines(left.subplots())
    _lines(right.subplots())
    left.suptitle(TITLE)
    kw = {"bbox_to_anchor": (0.5, 0.99)} if anchored else {}
    legend = left.legend(
        *left.axes[0].get_legend_handles_labels(),
        loc="upper center",
        ncols=3,
        **kw,
    )
    fig.canvas.draw()
    before = legend.get_window_extent(drawn_renderer(fig)).frozen()
    _layout(fig)
    after = legend.get_window_extent(drawn_renderer(fig))
    assert np.allclose(after.extents, before.extents, atol=0.5)
    assert _gap_px(fig, left) < 0  # it lies on the title
    assert _kinds(fig) == ["LEGEND_OVERLAP"]
