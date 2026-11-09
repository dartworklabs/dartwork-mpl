"""The margin fit stops a true two-state cycle, and nothing else.

A tick locator can pick wider labels at one width than at the other, so the
fit alternates between two edge sets forever (A, B, A, B); the fit then
keeps the inner of the two, once a fresh measure shows its content fits.
A third return to A after one B is not yet a cycle, a slow monotone
approach is convergence, and a three-state round is not this case: neither
may stop early (review of #666). The solver step is replaced by a scripted
sequence of left edges; the oracle is which steps the fit asked for and
where it stopped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.layout import _simple_layout as sl
from dartwork_mpl.layout._margins import _Sides

if TYPE_CHECKING:
    from collections.abc import Sequence


def _fit(
    lefts: Sequence[float], monkeypatch: pytest.MonkeyPatch
) -> tuple[list[float], float, float]:
    """Run the fit on a stub solver that returns ``lefts`` in order (the
    last repeating); return the lefts it asked for, where it stopped and
    the last step's change in px."""
    fig, ax = plt.subplots()
    asked: list[float] = []

    def step(*_args: Any, **kwargs: Any) -> sl._LayoutStep:
        left = lefts[min(len(asked), len(lefts) - 1)]
        asked.append(left)
        edges = sl._GridEdges(left, 0.9, 0.1, 0.9)
        last = kwargs["last_edges"]
        return sl._LayoutStep(edges, 0.0 if edges == last else 10.0)

    monkeypatch.setattr(sl, "_solve_layout_step", step)
    got, last = sl._fit_margins(
        fig,
        ax.get_gridspec(),
        margins=_Sides(0, 0, 0, 0),
        scope=[ax],
        last_edges=None,
        adopt_orphan_tick_font=False,
        format_ticks=False,
        verbose=False,
    )
    plt.close(fig)
    assert got is not None and last is not None
    return asked, last.left, got.delta_px


def test_a_true_two_state_cycle_stops_on_the_inner_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A, B, A, B: the inner left (the larger, 0.2) is measured once more
    and, its content fitting, kept."""
    asked, left, delta = _fit([0.1, 0.2, 0.1, 0.2, 0.2], monkeypatch)
    assert asked == [0.1, 0.2, 0.1, 0.2, 0.2]
    assert left == 0.2
    assert delta == 0.0


def test_one_return_is_not_yet_a_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """A, B, A then C: the fit goes on to C and settles there."""
    asked, left, _delta = _fit([0.1, 0.2, 0.1, 0.3, 0.3], monkeypatch)
    assert asked[:5] == [0.1, 0.2, 0.1, 0.3, 0.3]
    assert left == 0.3


def test_a_slow_monotone_approach_is_not_a_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lefts = [0.1 + 2e-10 * k for k in range(sl._MAX_ITER)]
    asked, _left, _delta = _fit(lefts, monkeypatch)
    assert len(asked) == sl._MAX_ITER


def test_a_three_state_round_is_not_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked, _left, _delta = _fit([0.1, 0.2, 0.3] * sl._MAX_ITER, monkeypatch)
    assert len(asked) == sl._MAX_ITER


def test_inner_edges_that_do_not_fit_are_not_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A, B, A, B, then the fresh measure at the inner edges asks for more
    room (0.25): the fit goes on from there instead of stopping."""
    asked, left, _delta = _fit([0.1, 0.2, 0.1, 0.2, 0.25, 0.25], monkeypatch)
    assert asked[:6] == [0.1, 0.2, 0.1, 0.2, 0.25, 0.25]
    assert left == 0.25
