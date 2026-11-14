"""``space`` keeps a wider panel gap only when the gap parted what collided.

Smoke round 5 (2026-11-14, s04 turn 4, #722): four panels in one row on a
slide. Text of neighbouring panels met on the title line, ``space`` grew
``wspace`` round after round to 1.44 (its cap is 1.5), the panels went from
4.56 to 2.37 cm wide, and the text still met: narrower panels push a
centred title further past its own panel, so the collision followed the
gap. The figure paid for a parting it did not get. The owner's standing
decision for the round (2026-11-14): a gap ``space`` grew stays only if the
collision is gone once the margins are fitted again, as a tick pad the
``pad`` step grew already does; otherwise it is put back and the collision
is left for ``CROSS_AXES_OVERLAP`` to report.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

CM = 2.54
NO_SPACE = ("axis_labels", "wrap", "rotate", "pad")
# Four of these side by side are wider than a 17 cm report page, so no
# spacing parts them.
LONG_TITLE = "Supply air temperature setpoint"


@pytest.fixture(autouse=True)
def _report():
    """Every figure here is a report figure, closed afterwards."""
    dm.style.use("report")
    yield
    plt.close("all")


def _title_row(title: str, *, fit_labels=True, ncols: int = 4):
    """One row of panels sharing y, each under the same centred title."""
    fig, axes = plt.subplots(
        1, ncols, figsize=dm.figsize("17cm", "5cm"), sharey=True
    )
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_title(title)
    dm.simple_layout(fig, fit_labels=fit_labels)
    return fig, axes


def _widths_cm(fig, axes) -> list[float]:
    """The width of every panel as drawn, in centimetres."""
    fig.canvas.draw()
    return [ax.get_position().width * fig.get_figwidth() * CM for ax in axes]


def _warnings(fig) -> set[str]:
    """The WARNING ids the validator reports for ``fig``."""
    return {
        w.check_id
        for w in dm.validate_figure(fig, quiet=True)
        if w.severity.value == "WARNING"
    }


def test_a_gap_that_cannot_part_the_titles_is_put_back() -> None:
    """Titles wider than the page: the panels are as wide as without the
    ``space`` step (they were halved, 3.49 to 1.70 cm, and still met)."""
    plain_fig, plain_axes = _title_row(LONG_TITLE, fit_labels=NO_SPACE)
    plain = _widths_cm(plain_fig, plain_axes)
    fig, axes = _title_row(LONG_TITLE)
    assert _widths_cm(fig, axes) == pytest.approx(plain, abs=0.01)
    assert axes[0].get_gridspec().wspace is None


def test_the_collision_left_is_reported() -> None:
    """Nothing is hidden: the titles that still meet are a finding."""
    fig, _axes = _title_row(LONG_TITLE)
    assert "CROSS_AXES_OVERLAP" in _warnings(fig)


def test_a_gap_that_parts_the_text_stays() -> None:
    """Two stacked panels, a title under an x-axis name: ``hspace`` grows,
    the collision is gone, and the wider gap is kept."""
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "9cm"))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_title("Zone temperature")
        ax.set_xlabel("Hour of day")
    dm.simple_layout(fig)
    grid = axes[0].get_gridspec()
    assert grid.hspace is not None
    assert grid.hspace > fig.subplotpars.hspace
    assert "CROSS_AXES_OVERLAP" not in _warnings(fig)


def test_a_second_layout_draws_the_same_figure() -> None:
    """``simple_layout`` twice on the row that cannot be parted: the same
    panels, and no gap left behind."""
    fig, axes = _title_row(LONG_TITLE)
    first = _widths_cm(fig, axes)
    dm.simple_layout(fig)
    assert _widths_cm(fig, axes) == pytest.approx(first, abs=1e-3)
    assert axes[0].get_gridspec().wspace is None
