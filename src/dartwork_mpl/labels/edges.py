"""The labels' named special cases, applied after the decisions in ``decide.py``.

Each one came from a chart that came out wrong without it; the ``why`` says
which.
"""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from .bar_geometry import Segment
from .stacks import BarsFacts, BarsPlan, Planned


def _shares_positions(facts: BarsFacts, plan: BarsPlan) -> bool:
    """Two containers piled at the same positions."""
    return any(len(p.members) > 1 for p in facts.piles())


def _stack_labels(facts: BarsFacts, plan: BarsPlan) -> BarsPlan:
    """Segments labelled at their middles and each stack's net beyond its
    end; a zero bar that pads a position (one bar highlighted by drawing it
    as a second container) gets no ``0``."""
    piles = facts.piles()
    padding = {pair for pile in piles for pair in pile.padding()}
    stacks = [p.members for p in piles if p.stacked]
    stacked = {i for members in stacks for i in members}
    labels: list[Planned] = [
        replace(label, kind=Segment()) if label.run in stacked else label
        for label in plan.labels
        if (label.run, label.index) not in padding
    ]
    for members in stacks:
        for index in range(len(facts.runs[members[0]].values)):
            total = facts.total_at(members, index)
            if total is not None:
                labels.append(total)
    return BarsPlan(tuple(labels))


BARS_EDGES: tuple[EdgeCase[BarsFacts, BarsPlan], ...] = (
    EdgeCase(
        name="stacked-segments-totals",
        why="stacked bars labelled each bar's end, not the segments and the "
        "stack's total",
        example="test_edges.py::test_stacked_segments_totals",
        applies=_shares_positions,
        adjust=_stack_labels,
    ),
)
