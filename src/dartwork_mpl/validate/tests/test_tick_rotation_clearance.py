"""TICK_ROTATION calls a turn unneeded only where flat labels would stand
half an em apart: the layout's own target for neighbouring bottom labels.

It compared the widest label plus 4 px with the axis width over the label
count, which is wider than the ticks' real spacing on a bar axis (its
margins) and, at 4 px, about a seventh of an em at 300 dpi. So it called
"unneeded" the turn the layout makes for labels 0.19 em apart flat, which
read as one name. Now it asks for half an em between every pair of flat
neighbours, the gaps the layout itself measures, so where the check calls
a turn unneeded the layout keeps the row flat too; and for each label,
with half an em, to fit the axis width over the label count, as the
warning's detail says.
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


def test_a_turn_of_uneven_ticks_with_room_flat_is_unneeded() -> None:
    """Ticks at 0, 1 and 10: the long name stands alone at 10, every flat
    pair is more than half an em apart and every label fits its share of
    the axis. The closest two ticks less the widest label ran negative
    and kept the check quiet about a turn nothing needs."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    ax.plot([0, 1, 10], [1, 2, 3])
    ax.set_xticks([0, 1, 10], ["A", "B", "A long region name"])
    dm.simple_layout(fig, fit_labels=False)
    assert _flat_gap_em(fig, ax) > 0.5  # precondition
    ax.tick_params(axis="x", labelrotation=30)
    assert _unneeded(fig)


def test_a_close_pair_among_uneven_ticks_keeps_its_turn() -> None:
    """Ticks at 0, 0.45 and 10: every label fits its share of the axis
    many times over, but 'Alpha' and 'Beta' would stand 0.19 em apart
    flat, apart yet under the half an em the layout turns for."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    ax.plot([0, 0.45, 10], [1, 2, 3])
    ax.set_xticks([0, 0.45, 10], ["Alpha", "Beta", "Gamma"])
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _flat_gap_em(fig, ax) < 0.5  # precondition
    ax.tick_params(axis="x", labelrotation=30)
    assert not _unneeded(fig)


def test_the_layouts_turn_of_close_codes_is_not_called_unneeded() -> None:
    """The stress corpus' 16 codes at 9 cm in ``scientific``, 0.16 em apart
    flat: the layout turns them, and the check agrees."""
    fig, ax = _bars("9cm", preset="scientific")
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _flat_gap_em(fig, ax) < 0.5  # precondition
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in ax.get_xticklabels()} != {0.0}
    assert not _unneeded(fig)


@pytest.mark.parametrize("preset", ["scientific", "report", "presentation"])
def test_a_long_name_between_short_ones_keeps_its_turn(preset: str) -> None:
    """``advanced/violin`` turns its region names. Flat, its short
    neighbours would leave 'North America' room in ``scientific`` and
    ``report``, but the name overruns its share of the axis (0.3 to
    2.6 em past it): the check keeps quiet, as on main."""
    from pathlib import Path

    source = (
        Path(dm.__file__).parent
        / "asset/prompt/05-templates/advanced/violin.py"
    ).read_text(encoding="utf-8")
    ends = ("dm.validate_with_fixes(fig)", "dm.save_formats(")
    source = source[: min(i for e in ends if (i := source.find(e)) >= 0)]
    source = source.replace(
        'dm.style.use("scientific")', f'dm.style.use("{preset}")'
    )
    namespace: dict = {}
    exec(compile(source, "violin", "exec"), namespace)
    assert not _unneeded(namespace["fig"])


def test_the_check_and_the_layout_share_the_clearance() -> None:
    from dartwork_mpl.layout._fit_labels import _TARGET_EM
    from dartwork_mpl.validate._checks import tick_rotation

    assert getattr(tick_rotation, "_FLAT_CLEARANCE_EM", None) == _TARGET_EM
