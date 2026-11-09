"""The root figure's ``dm.figure_legend`` legend sits past the figure's label set after it.

``figure_legend(fig)`` anchors a legend past the figure's own label on its
side (a suptitle above, a supxlabel below, a supylabel on the left) as it
stands when called. An agent that places the legend first and titles the
figure afterwards got the title under the legend (LEGEND_OVERLAP). Now
``simple_layout`` places the root's figure legends past its labels as they
are, as it does in each SubFigure: the label, then the legend, then the
panels, with the gap a legend called after its label keeps
(``legend.borderaxespad``).

A legend the caller placed (``fig.legend``) stays where it is; LEGEND_OVERLAP
reports what it covers. A legend called after its label does not move.
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

LABELS = {
    "above": ("suptitle", "Electric load at both sites, winter 2025"),
    "below": ("supxlabel", "Hours since midnight, both sites"),
    "left": ("supylabel", "Load at the feeder [kW]"),
}


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _figure():
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    x = np.linspace(0, 10, 40)
    for ax in axes:
        for i in range(3):
            ax.plot(x, np.sin(x / 2 + i) + i, label=f"Series {chr(65 + i)}")
        ax.set(xlabel="Time [h]", ylabel="Load [kW]")
    return fig


def _label(fig, side: str):
    method, text = LABELS[side]
    return getattr(fig, method)(text)


def _layout(fig) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dm.simple_layout(fig)


def _gap(fig, side: str, legend, label) -> float:
    """How far the legend stands past the label (px; < 0 overlaps)."""
    renderer = drawn_renderer(fig)
    lb, tb = (
        legend.get_window_extent(renderer),
        label.get_window_extent(renderer),
    )
    return float(
        {"above": tb.y0 - lb.y1, "below": lb.y0 - tb.y1, "left": lb.x0 - tb.x1}[
            side
        ]
    )


def _pad(fig, legend) -> float:
    return (
        float(legend.borderaxespad)
        * legend.prop.get_size_in_points()
        * fig.dpi
        / 72
    )


def _kinds(fig) -> list[str]:
    found = dm.validate_figure(fig, checks=("LEGEND_OVERLAP",), quiet=True)
    return [w.check_id for w in found]


@pytest.mark.parametrize("side", ["above", "below", "left"])
def test_a_label_set_after_the_legend_comes_before_it(side: str) -> None:
    fig = _figure()
    legend = dm.figure_legend(fig, loc=side)
    label = _label(fig, side)
    _layout(fig)
    assert _gap(fig, side, legend, label) == pytest.approx(
        _pad(fig, legend), abs=1.0
    )
    assert _kinds(fig) == []


@pytest.mark.parametrize("side", ["above", "below", "left"])
def test_the_panels_keep_clear_of_the_moved_legend(side: str) -> None:
    fig = _figure()
    legend = dm.figure_legend(fig, loc=side)
    _label(fig, side)
    _layout(fig)
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    for ax in fig.axes:
        plot = ax.get_window_extent(renderer)
        w = min(box.x1, plot.x1) - max(box.x0, plot.x0)
        h = min(box.y1, plot.y1) - max(box.y0, plot.y0)
        assert not (w > 0.5 and h > 0.5)


@pytest.mark.parametrize("side", ["above", "below", "left", "right"])
def test_a_legend_called_after_its_label_stays_where_it_was(side: str) -> None:
    fig = _figure()
    if side != "right":
        _label(fig, side)
    legend = dm.figure_legend(fig, loc=side)
    before = legend.get_bbox_to_anchor().frozen()
    _layout(fig)
    _layout(fig)  # and again: nothing moves
    assert np.allclose(
        legend.get_bbox_to_anchor().frozen().extents, before.extents
    )


def test_a_legend_the_caller_placed_stays_and_is_reported() -> None:
    fig = _figure()
    legend = fig.legend(
        *fig.axes[0].get_legend_handles_labels(), loc="upper center", ncols=3
    )
    label = _label(fig, "above")
    fig.canvas.draw()
    before = legend.get_window_extent(drawn_renderer(fig)).frozen()
    _layout(fig)
    after = legend.get_window_extent(drawn_renderer(fig))
    assert np.allclose(after.extents, before.extents, atol=0.5)
    assert _gap(fig, "above", legend, label) < 0
    assert _kinds(fig) == ["LEGEND_OVERLAP"]


def test_a_root_legend_over_subfigures_comes_after_a_title_set_later() -> None:
    """The same order when the root holds SubFigures (the SubFigure path)."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    x = np.linspace(0, 10, 40)
    for sub in fig.subfigures(1, 2):
        ax = sub.subplots()
        for i in range(3):
            ax.plot(x, np.sin(x / 2 + i) + i, label=f"Series {chr(65 + i)}")
    legend = dm.figure_legend(fig, loc="above")
    label = _label(fig, "above")
    _layout(fig)
    gap = _gap(fig, "above", legend, label)
    assert gap == pytest.approx(_pad(fig, legend), abs=1.0)
    assert _kinds(fig) == []


@pytest.mark.parametrize("edit", ["anchor", "loc"])
def test_a_figure_legend_the_caller_moved_stays_where_they_put_it(
    edit: str,
) -> None:
    """The ownership rule of #674 on the root: a legend moved through the
    returned Legend is the caller's, even with a label set after it."""
    fig = _figure()
    legend = dm.figure_legend(fig, loc="above")
    _label(fig, "above")
    if edit == "anchor":
        legend.set_bbox_to_anchor((0.6, 0.6), transform=fig.transSubfigure)
    else:
        legend.set_loc("lower left")
    fig.canvas.draw()
    before = legend.get_window_extent(drawn_renderer(fig)).frozen()
    _layout(fig)
    after = legend.get_window_extent(drawn_renderer(fig))
    assert np.allclose(after.extents, before.extents, atol=0.5)


# --------------------------------------------- the order of the calls
#: A label at the edge of the canvas, clear of the legend, and a centred one
#: that meets it (review of #675).
ORDER_CASES = {
    "above_edge": ("above", "suptitle", {"x": 0.01, "ha": "left"}),
    "below_edge": ("below", "supxlabel", {"x": 0.01, "ha": "left"}),
    "left_edge": ("left", "supylabel", {"y": 0.01, "va": "bottom"}),
    "above_centred": ("above", "suptitle", {}),
}


def _in_order(case: str, *, label_first: bool):
    """The legend's and the Axes' boxes once laid out, the label set
    before or after ``figure_legend``."""
    side, method, kw = ORDER_CASES[case]
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "wide"))
    for i in range(2):
        ax.plot([0, 1], [i, i + 1], label=f"Series {i}")
    if label_first:
        getattr(fig, method)("Title", **kw)
    legend = dm.figure_legend(fig, loc=side)
    if not label_first:
        getattr(fig, method)("Title", **kw)
    _layout(fig)
    renderer = drawn_renderer(fig)
    return (
        legend.get_window_extent(renderer).extents,
        ax.get_window_extent(renderer).extents,
    )


@pytest.mark.parametrize("case", list(ORDER_CASES))
def test_the_figure_does_not_depend_on_the_order_of_the_calls(
    case: str,
) -> None:
    """The contract: a ``figure_legend`` legend stacks past the figure's
    label on its side whichever was set first. Before, a label set first
    had the legend stacked past it even where the two did not meet (a short
    suptitle at the left end), while the same label set after left the
    legend where it was: the call order changed the figure. A label set
    after now moves the legend as a label set first does."""
    first_legend, first_axes = _in_order(case, label_first=True)
    after_legend, after_axes = _in_order(case, label_first=False)
    assert np.allclose(after_legend, first_legend, atol=1.0)
    assert np.allclose(after_axes, first_axes, atol=1.0)
