"""TICK_ROTATION calls a turn unneeded only where flat labels would stand
half an em apart: the layout's own target for neighbouring bottom labels.

It compared the widest label plus 4 px with the axis width over the label
count, which is wider than the ticks' real spacing on a bar axis (its
margins) and, at 4 px, about a seventh of an em at 300 dpi. So it called
"unneeded" the turn the layout makes for labels 0.19 em apart flat, which
read as one name. Now it measures the flat gaps as the layout does (tick
centres less half of each unturned width) against half an em.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.validate import validate_figure

SHORT = [f"C{i}" for i in range(1, 17)]


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _bars(width: str, preset: str = "report"):
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    ax.bar(SHORT, np.arange(16) + 1.0)
    return fig, ax


def _flat_gap_em(fig, ax) -> float:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_xticklabels()]
    em = ax.get_xticklabels()[0].get_fontsize() * fig.dpi / 72
    return min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em


def _unneeded(fig) -> bool:
    return any(
        w.detail.get("recommended_rotation") == 0
        for w in validate_figure(fig, checks=["TICK_ROTATION"], quiet=True)
    )


def test_a_turn_for_labels_closer_than_half_an_em_is_not_unneeded() -> None:
    """At 12 cm the codes would stand 0.19 em apart flat: turning them is
    what the layout does, not a turn to take back."""
    fig, ax = _bars("12cm")
    assert 0 < _flat_gap_em(fig, ax) < 0.5  # precondition
    ax.tick_params(axis="x", labelrotation=30)
    assert not _unneeded(fig)


def test_a_turn_with_half_an_em_to_spare_is_unneeded() -> None:
    fig, ax = _bars("16cm")
    assert _flat_gap_em(fig, ax) >= 0.5  # precondition
    ax.tick_params(axis="x", labelrotation=30)
    assert _unneeded(fig)


def test_the_layouts_turn_of_close_codes_is_not_called_unneeded() -> None:
    """The stress corpus' 16 codes at 9 cm in ``scientific``, 0.16 em apart
    flat: the layout turns them, and the check agrees."""
    fig, ax = _bars("9cm", preset="scientific")
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _flat_gap_em(fig, ax) < 0.5  # precondition
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in ax.get_xticklabels()} != {0.0}
    assert not _unneeded(fig)


def test_the_check_and_the_layout_share_the_clearance() -> None:
    from dartwork_mpl.layout._fit_labels import _TARGET_EM
    from dartwork_mpl.validate._checks import tick_rotation

    assert getattr(tick_rotation, "_FLAT_CLEARANCE_EM", None) == _TARGET_EM
