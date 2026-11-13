"""``simple_layout(gutter=...)`` sets the gap between neighbouring panels' content.

In the insulation-aging figures the content gap between neighbouring panels
was 2.0, 18.1, 25.2 and 32.2 pt in four figures (the owner called the 18 pt
1 x 2 "b looks precarious"); the owner chose a fixed 28 pt, and on
2026-11-13 chose this public shape: ``simple_layout(gutter=...)`` with no
default (PoC 12-G to 16-G).
"""

from __future__ import annotations

import itertools

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

TOL_PT = 0.3


@pytest.fixture(autouse=True)
def _scientific():
    """Scientific preset; figures closed afterwards."""
    dm.style.use("scientific")
    yield
    plt.close("all")


def _gaps_pt(fig) -> tuple[float | None, float | None]:
    """Narrowest gap (pt) between the content of neighbouring top-level
    columns and rows, measured with ``ax.get_tightbbox``."""
    renderer = drawn_renderer(fig)
    cols: dict[int, list[Bbox]] = {}
    rows: dict[int, list[Bbox]] = {}
    for ax in fig.axes:
        top = ax.get_subplotspec().get_topmost_subplotspec()
        box = ax.get_tightbbox(renderer)
        cols.setdefault(top.colspan.start, []).append(box)
        rows.setdefault(top.rowspan.start, []).append(box)

    def gap(groups, horizontal):
        keys = sorted(groups)
        values = []
        for a, b in itertools.pairwise(keys):
            first, second = Bbox.union(groups[a]), Bbox.union(groups[b])
            values.append(
                second.x0 - first.x1 if horizontal else first.y0 - second.y1
            )
        return min(values) * 72.0 / fig.dpi if values else None

    return gap(cols, True), gap(rows, False)


def _colorbar_pair():
    """1 x 2 with a colour bar on each panel and panel letters."""
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
    for ax in axes:
        fig.colorbar(
            ax.imshow(rng.random((8, 8)), aspect="auto"), ax=ax, label="T [K]"
        )
        ax.set_ylabel("Depth [mm]")
        ax.set_title("Field")
    dm.label_axes(axes)
    return fig


def _grid():
    """2 x 2 with axis names, titles and panel letters."""
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "11cm"))
    for ax in axes.flat:
        ax.plot([0, 1], [0, 1000])
        ax.set_xlabel("Time [h]")
        ax.set_ylabel("Load [kW]")
        ax.set_title("Panel")
    dm.label_axes(axes)
    return fig


@pytest.mark.parametrize("gutter", ["28pt", dm.pt(28), 28, 28.0])
def test_columns_with_colour_bars_are_the_gutter_apart(gutter) -> None:
    """Colour bars count with their panel; every spelling is points."""
    fig = _colorbar_pair()
    dm.simple_layout(fig, gutter=gutter)
    column, row = _gaps_pt(fig)
    assert column == pytest.approx(28.0, abs=TOL_PT)
    assert row is None


@pytest.mark.parametrize("gutter", [12.0, 28.0, 40.0])
def test_columns_and_rows_are_the_gutter_apart(gutter: float) -> None:
    """Both directions, narrower and wider than the spacing the grid had."""
    fig = _grid()
    dm.simple_layout(fig, gutter=f"{gutter}pt")
    column, row = _gaps_pt(fig)
    assert column == pytest.approx(gutter, abs=TOL_PT)
    assert row == pytest.approx(gutter, abs=TOL_PT)


def test_default_leaves_the_spacing_alone() -> None:
    """Without ``gutter`` (and the ladder's ``space`` step off) the grid
    keeps matplotlib's spacing."""
    fig = _grid()
    dm.simple_layout(fig, fit_labels=False)
    gs = fig.axes[0].get_subplotspec().get_gridspec()
    assert gs.wspace is None
    assert gs.hspace is None


def test_a_later_call_without_it_puts_the_spacing_back() -> None:
    """The gutter is a layout setting: the next layout undoes it."""
    reference = _grid()
    dm.simple_layout(reference)
    fig = _grid()
    dm.simple_layout(fig, gutter="28pt")
    dm.simple_layout(fig)
    assert _gaps_pt(fig) == pytest.approx(_gaps_pt(reference), abs=0.05)


def test_it_replaces_spacing_set_by_hand() -> None:
    """``gridspec_kw`` spacing gives way to the gutter that was asked for."""
    fig, axes = plt.subplots(
        1, 2, figsize=dm.figsize("17cm", "7cm"), gridspec_kw={"wspace": 0.8}
    )
    for ax in axes:
        ax.set_ylabel("Value")
    dm.simple_layout(fig, gutter="20pt")
    assert _gaps_pt(fig)[0] == pytest.approx(20.0, abs=TOL_PT)


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (-1.0, ValueError),
        (float("nan"), ValueError),
        (True, TypeError),
        ([28], TypeError),
    ],
)
def test_bad_values_are_refused_before_the_figure_is_touched(
    value, error
) -> None:
    """A negative, non-finite or non-length gutter fails by name."""
    fig = _grid()
    before = [ax.get_position().bounds for ax in fig.axes]
    with pytest.raises(error, match="gutter"):
        dm.simple_layout(fig, gutter=value)
    assert [ax.get_position().bounds for ax in fig.axes] == before


def test_only_panels_sharing_a_row_face_each_other() -> None:
    """C (row 2) has a legend reaching under B (row 1, next column); only A
    and B share a row, so they alone are the gutter apart."""
    fig, axd = plt.subplot_mosaic(
        [["A", "B"], ["C", "."]], figsize=dm.figsize("17cm", "10cm")
    )
    for ax in axd.values():
        ax.plot([0, 1], [0, 1], label="A long series name")
        ax.set_ylabel("Value")
    axd["C"].legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    dm.simple_layout(fig, gutter="28pt")
    renderer = drawn_renderer(fig)
    a, b = (axd[k].get_tightbbox(renderer) for k in "AB")
    assert (b.x0 - a.x1) * 72.0 / fig.dpi == pytest.approx(28.0, abs=TOL_PT)
