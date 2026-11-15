"""The labels' named special cases, applied after the decisions in ``decide.py``.

Each one came from a chart that came out wrong without it; the ``why`` says
which. ``EDGES`` holds them all, grouped by the decision they follow
(:data:`TEXT`, :data:`BARS`, :data:`INK`): keep each group's entries
together and in order.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from ..edgecase import EdgeCase
from .model import Ink, InkFacts, LabelText, ValueFacts, prints_zero
from .stacks import BarsFacts, BarsPlan, Planned


# ------------------------------------------------------------ text
def _wants_plus(facts: ValueFacts, plan: LabelText) -> bool:
    """``sign="+"`` and a positive value that does not print as zero."""
    return (
        facts.sign == "+"
        and plan.lead == ""
        and plan.value > 0
        and not prints_zero(plan.value, plan.decimals)
    )


def _plus(facts: ValueFacts, plan: LabelText) -> LabelText:
    return replace(plan, lead="+")


# ------------------------------------------------------------ stacks
def _shares_positions(facts: BarsFacts, plan: BarsPlan) -> bool:
    """Two containers piled at the same positions."""
    return any(len(p.members) > 1 for p in facts.piles())


def _stack_labels(facts: BarsFacts, plan: BarsPlan) -> BarsPlan:
    """Segments labelled at their middles and each stack's net beyond its
    end; zero bars that pad a position get no label."""
    piles = facts.piles()
    padding: set[tuple[int, int]] = set()
    for pile in piles:
        padding |= pile.padding()
    stacks = [p.members for p in piles if p.stacked]
    stack_of = {i: k for k, members in enumerate(stacks) for i in members}
    labels: list[Planned] = []
    for label in plan.labels:
        if (label.run, label.index) in padding:
            continue
        k = stack_of.get(label.run)
        if k is None:
            labels.append(label)
        elif facts.total != "only":
            labels.append(replace(label, kind="segment", stack=k))
    if facts.total is not False:
        for k, members in enumerate(stacks):
            for index in range(len(facts.runs[members[0]].values)):
                total = facts.total_at(members, index, k)
                if total is not None:
                    labels.append(total)
    return BarsPlan(tuple(labels))


# ------------------------------------------------------------ ink
def _own_colour(facts: InkFacts) -> bool:
    return facts.options.color is not None and not facts.options.series


def _on_bar(facts: InkFacts, plan: Ink) -> bool:
    return facts.on_bar and not _own_colour(facts)


def _readable(facts: InkFacts, plan: Ink) -> Ink:
    return facts.readable


def _series_off_bar(facts: InkFacts, plan: Ink) -> bool:
    return not facts.on_bar and facts.options.series and facts.kind != "total"


def _series(facts: InkFacts, plan: Ink) -> Ink:
    return facts.series_ink


EDGES: tuple[EdgeCase[Any, Any], ...] = (
    EdgeCase(
        name="signed-steps",
        why="a waterfall's rises printed bare beside its falls (30 and "
        "−15), so they did not read as changes",  # noqa: RUF001
        example="test_edges.py::test_signed_steps",
        applies=_wants_plus,
        adjust=_plus,
    ),
    EdgeCase(
        name="stacked-segments-totals",
        why="stacked bars labelled each bar's end, not the segments and the "
        "stack's total; a zero bar padding a split highlight got a '0'",
        example="test_edges.py::test_stacked_segments_totals",
        applies=_shares_positions,
        adjust=_stack_labels,
    ),
    EdgeCase(
        name="inside-readable-ink",
        why="a label in the text colour vanished on a dark bar",
        example="test_edges.py::test_inside_readable_ink",
        applies=_on_bar,
        adjust=_readable,
    ),
    EdgeCase(
        name="series-colour",
        why="a waterfall's step labels in the text colour did not say which "
        "steps rose and which fell, as the bars' colours do",
        example="test_edges.py::test_series_colour",
        applies=_series_off_bar,
        adjust=_series,
    ),
)


TEXT = cast("tuple[EdgeCase[ValueFacts, LabelText], ...]", EDGES[0:1])
BARS = cast("tuple[EdgeCase[BarsFacts, BarsPlan], ...]", EDGES[1:2])
INK = cast("tuple[EdgeCase[InkFacts, Ink], ...]", EDGES[2:4])
