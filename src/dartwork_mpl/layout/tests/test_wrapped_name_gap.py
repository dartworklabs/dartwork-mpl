"""A name the layout wraps leaves the panel gap a hand-wrapped name leaves.

Smoke round 5 (2026-11-14, ``g21-grid-long-names``, both hosts): a 2 x 3
paper grid with panel letters and a y-axis name longer than its panel came
out with a 0.94 cm empty band between the rows. The same figure with the
name broken by hand at the same space had 0.14 cm. The ``space`` step
measured the panels in the round that wrapped the name, while each panel
letter still stood where the one-line name had pushed it: above the name's
top end, far over the panel.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

ONE_LINE = "Supply air volumetric flow rate (m³/h)"
BY_HAND = "Supply air volumetric\nflow rate (m³/h)"
TOL_PT = 1.0


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _grid(preset: str, nrows: int, ncols: int, ylabel: str, letters: bool):
    dm.style.use(preset)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=dm.figsize_for(nrows=nrows, ncols=ncols)
    )
    for i, ax in enumerate(axes.flat):
        ax.plot([100, 250, 400], [3000 + 500 * i, 5000, 6200 + 900 * i])
        ax.set(
            xlabel="Duct static pressure setpoint (Pa)",
            ylabel=ylabel,
            title=f"Unit {i + 1}",
        )
    if letters:
        dm.label_axes(axes)
    dm.simple_layout(fig)
    return fig, axes


def _row_gap_pt(fig, axes) -> float:
    """Empty height (pt) between the content of the first two rows."""
    renderer = drawn_renderer(fig)
    upper = min(ax.get_tightbbox(renderer).y0 for ax in axes[0])
    lower = max(ax.get_tightbbox(renderer).y1 for ax in axes[1])
    return float(upper - lower) * 72.0 / fig.dpi


@pytest.mark.parametrize("letters", [True, False])
def test_a_wrapped_name_leaves_the_gap_of_the_same_name_broken_by_hand(letters):
    """Same text on the page, same gap: with panel letters and without."""
    auto_fig, auto = _grid("scientific", 2, 3, ONE_LINE, letters)
    hand_fig, hand = _grid("scientific", 2, 3, BY_HAND, letters)

    assert auto[1, 0].get_ylabel() == BY_HAND  # the layout wrapped it
    assert _row_gap_pt(auto_fig, auto) == pytest.approx(
        _row_gap_pt(hand_fig, hand), abs=TOL_PT
    )
    assert auto[0, 0].get_position().height == pytest.approx(
        hand[0, 0].get_position().height, rel=0.01
    )


def test_panel_letters_cost_a_wrapped_grid_no_more_than_their_own_height():
    """The letters stand on the title line: a grid with them is not parted
    further than the same grid without them, give or take a letter."""
    with_fig, with_letters = _grid("scientific", 2, 3, ONE_LINE, True)
    without_fig, without = _grid("scientific", 2, 3, ONE_LINE, False)

    letter_pt = dm.fs(1)
    assert _row_gap_pt(with_fig, with_letters) <= (
        _row_gap_pt(without_fig, without) + letter_pt
    )
