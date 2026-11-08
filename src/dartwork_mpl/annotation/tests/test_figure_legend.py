"""``dm.figure_legend``: one legend for every panel, outside the panels.

The oracle is the drawn figure: which legends exist afterwards, their
entries, where the figure legend sits against the panels and the
suptitle once ``simple_layout`` has run, and what ``validate_figure``
reports.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer, legend_ncols

LEGEND_CHECKS = ("LEGEND_ON_DATA", "LEGEND_OVERLAP", "LEGEND_OVERFLOW")


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _lines(ax, n: int, prefix: str = "Region", shift: float = 0.0) -> None:
    x = np.linspace(0, 11, 60)
    for i in range(n):
        ax.plot(
            x,
            50 + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / n + shift),
            label=f"{prefix} {i + 1}",
        )


def _grid(nrows: int = 2, ncols: int = 2, size=("17cm", "12cm")):
    fig, axs = plt.subplots(nrows, ncols, figsize=dm.figsize(*size))
    return fig, np.atleast_1d(axs)


def _panels(fig, axs) -> Bbox:
    renderer = drawn_renderer(fig)
    return Bbox.union([ax.get_window_extent(renderer) for ax in axs.flat])


def test_one_legend_replaces_the_panel_legends() -> None:
    fig, axs = _grid()
    for k, ax in enumerate(axs.flat):
        _lines(ax, 6, shift=k)
        ax.legend()
    legend = dm.figure_legend(fig)
    assert legend is not None
    assert fig.legends == [legend]
    assert all(ax.get_legend() is None for ax in axs.flat)
    assert [t.get_text() for t in legend.get_texts()] == [
        f"Region {i + 1}" for i in range(6)
    ]
    dm.simple_layout(fig)
    assert dm.validate_figure(fig, checks=LEGEND_CHECKS, quiet=True) == []
    assert (
        legend.get_window_extent(drawn_renderer(fig)).y0 >= _panels(fig, axs).y1
    )


def test_entries_are_each_label_once_in_figure_order() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    axs[0].plot([0, 1], label="North")
    axs[0].plot([0, 1], label="South")
    axs[1].plot([0, 1], label="South")
    axs[1].plot([0, 1], label="East")
    legend = dm.figure_legend(fig)
    assert legend is not None
    assert [t.get_text() for t in legend.get_texts()] == [
        "North",
        "South",
        "East",
    ]


def test_a_legend_of_other_names_stays() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    _lines(axs[0], 2)
    _lines(axs[1], 2)
    own = axs[1].legend(["A note of my own"], loc="lower left")
    dm.figure_legend(fig)
    assert axs[1].get_legend() is own


def test_a_wrapped_place_legend_is_replaced_too() -> None:
    """A legend place_legend wrapped still holds the figure's entries."""
    dm.style.use("presentation")
    fig, axs = _grid(1, 2, ("15.4cm", "10.5cm"))
    long = " metropolitan region, seasonally adjusted (2019 = 100)"
    for ax in axs:
        _lines(ax, 2, prefix="Region" + long)
    wrapped = dm.place_legend(axs[0], loc="above")
    assert wrapped is not None and wrapped._dm_wrapped is True
    dm.figure_legend(fig)
    assert all(ax.get_legend() is None for ax in axs)


def test_the_side_that_costs_the_panels_less_wins() -> None:
    """One column of six is short beside the panels and tall above them."""
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for k, ax in enumerate(axs):
        _lines(ax, 6, shift=k)
    assert dm.figure_legend(fig)._dm_figure_side == "above"
    legend = dm.figure_legend(fig, ncols=1)
    assert legend is not None
    assert legend._dm_figure_side == "right"
    dm.simple_layout(fig)
    assert (
        legend.get_window_extent(drawn_renderer(fig)).x0 >= _panels(fig, axs).x1
    )


@pytest.mark.parametrize("side", ["above", "below", "right", "left"])
def test_a_named_side_is_used(side: str) -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 3)
    legend = dm.figure_legend(fig, loc=side)
    assert legend is not None
    dm.simple_layout(fig)
    box = legend.get_window_extent(drawn_renderer(fig))
    panels = _panels(fig, axs)
    match side:
        case "above":
            assert box.y0 >= panels.y1
        case "below":
            assert box.y1 <= panels.y0
        case "right":
            assert box.x0 >= panels.x1
        case "left":
            assert box.x1 <= panels.x0
    assert dm.validate_figure(fig, checks=LEGEND_CHECKS, quiet=True) == []


def test_a_right_figure_legend_may_be_taller_than_the_panels() -> None:
    """The rule of place_legend's outside legends: it fits when it stays on
    the figure, so one column taller than the panels is not split."""
    fig, axs = _grid(1, 2, ("17cm", "6cm"))
    for ax in axs:
        _lines(ax, 16)
    legend = dm.figure_legend(fig, loc="right")
    assert legend is not None
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    assert legend_ncols(legend) == 1
    assert box.height > _panels(fig, axs).height
    assert fig.bbox.y0 <= box.y0 and box.y1 <= fig.bbox.y1


def test_an_above_figure_legend_keeps_its_pad_from_the_figure_edges() -> None:
    """A figure as wide as the one-row legend and one pad: the row would
    come closer to an edge than its pad, so the legend takes two rows."""
    fig, axs = _grid(1, 2, ("30cm", "8cm"))
    for ax in axs:
        _lines(ax, 6)
    wide = dm.figure_legend(fig, loc="above")
    assert wide is not None and legend_ncols(wide) == 6
    width = wide.get_window_extent(drawn_renderer(fig)).width
    pad = wide.borderaxespad * wide.prop.get_size_in_points() * fig.dpi / 72.0
    fig.set_size_inches((width + pad) / fig.dpi, fig.get_size_inches()[1])
    legend = dm.figure_legend(fig, loc="above")
    assert legend is not None and legend_ncols(legend) < 6
    box = legend.get_window_extent(drawn_renderer(fig))
    assert box.x0 >= fig.bbox.x0 + pad - 0.5
    assert box.x1 <= fig.bbox.x1 - pad + 0.5


def test_a_matplotlib_loc_goes_to_fig_legend_unchanged() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 2)
    legend = dm.figure_legend(fig, loc="upper left", frameon=False)
    assert legend is not None
    assert legend.get_frame_on() is False
    assert fig.legends == [legend]


def test_an_asked_column_count_wins() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 6)
    legend = dm.figure_legend(fig, ncols=2)
    assert legend is not None
    assert legend_ncols(legend) == 2


def test_a_second_call_replaces_the_first() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 2)
    first = dm.figure_legend(fig)
    axs[1].plot([0, 1], label="Added")
    second = dm.figure_legend(fig, loc="below")
    assert fig.legends == [second]
    assert first is not second
    assert [t.get_text() for t in second.get_texts()][-1] == "Added"


def test_no_labelled_artist_gives_none() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    axs[0].plot([0, 1])
    assert dm.figure_legend(fig) is None
    assert fig.legends == []


@pytest.mark.parametrize("key", ["bbox_to_anchor", "bbox_transform"])
def test_a_side_sets_the_anchor_itself(key: str) -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    _lines(axs[0], 2)
    value = (0.5, 0.5) if key == "bbox_to_anchor" else fig.transFigure
    with pytest.raises(ValueError, match=key):
        dm.figure_legend(fig, **{key: value})


def test_a_failed_call_keeps_the_panel_legends() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 2)
    olds = [ax.legend() for ax in axs]
    with pytest.raises(ValueError, match="bbox_to_anchor"):
        dm.figure_legend(fig, bbox_to_anchor=(0.5, 1.0))
    assert [ax.get_legend() for ax in axs] == olds
    assert fig.legends == []


def test_a_failed_call_keeps_the_earlier_figure_legend() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 2)
    old = dm.figure_legend(fig)
    with pytest.raises(ValueError, match="bbox_to_anchor"):
        dm.figure_legend(fig, loc="below", bbox_to_anchor=(0.5, 0.0))
    assert fig.legends == [old]
    with pytest.raises(TypeError):  # matplotlib refuses the keyword
        dm.figure_legend(fig, loc="upper left", not_a_legend_keyword=1)
    assert fig.legends == [old]


def test_the_layout_keeps_the_legend_gap_from_the_panels() -> None:
    """Between the legend and the panels' titles: the preset's border pad."""
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 2)
        ax.set_title("Panel")
    legend = dm.figure_legend(fig)
    assert legend is not None
    dm.simple_layout(fig)
    renderer = drawn_renderer(fig)
    content_top = max(ax.get_tightbbox(renderer).y1 for ax in axs)
    gap_pt = legend.borderaxespad * legend.prop.get_size_in_points()
    gap = legend.get_window_extent(renderer).y0 - content_top
    assert gap == pytest.approx(gap_pt * fig.dpi / 72, abs=1.0)


def test_above_sits_under_a_suptitle() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 3)
    title = fig.suptitle("Regional index")
    legend = dm.figure_legend(fig)
    assert legend is not None
    dm.simple_layout(fig)
    renderer = drawn_renderer(fig)
    assert (
        legend.get_window_extent(renderer).y1
        <= title.get_window_extent(renderer).y0
    )
    assert dm.validate_figure(fig, checks=LEGEND_CHECKS, quiet=True) == []


def test_a_subfigure_gets_its_own_legend() -> None:
    fig = plt.figure(figsize=dm.figsize("17cm", "12cm"))
    top, bottom = fig.subfigures(2, 1)
    for sub in (top, bottom):
        for ax in sub.subplots(1, 2):
            _lines(ax, 2)
    legend = dm.figure_legend(top, loc="right")
    assert legend is not None
    assert top.legends == [legend] and bottom.legends == []
    assert fig.legends == []


def test_legend_on_data_names_the_figure_legend() -> None:
    fig, axs = _grid(1, 2, ("17cm", "8cm"))
    for ax in axs:
        _lines(ax, 4)
        ax.legend(loc="upper right")
    found = dm.validate_figure(fig, checks=("LEGEND_ON_DATA",), quiet=True)
    assert found
    suggestions = dm.validate_fixes.get_fix_suggestions(found[0])
    assert any("dm.figure_legend(fig)" in s for s in suggestions)
