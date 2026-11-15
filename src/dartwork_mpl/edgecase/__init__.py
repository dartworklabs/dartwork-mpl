"""Named edge cases a slice appends after its main decision.

A slice decides its plan for the ordinary figure in ``decide.py``. Whatever
only matters for an unusual figure (a hidden SubFigure, a polar axis, an empty
panel) does not go into that function as one more branch. It goes into the
slice's ``edges.py`` as one more :class:`EdgeCase` at the end of ``EDGES``::

    EDGES: tuple[EdgeCase[Facts, Plan], ...] = (
        EdgeCase(
            name="crowded-ticks-wrap",
            why="long category names ran into each other on a narrow axis",
            example="test_edges.py::test_crowded_ticks_wrap_at_spaces",
            applies=has_wrappable_ticks,
            adjust=wrap_ticks,
        ),
    )

``settle(facts, plan, EDGES)`` applies them in order and reports which fired,
so the main path stays readable. Every edge case has a name, a reason (what
goes wrong without it) and an example: the test in the slice's ``tests/``
that makes it fire. One that fires on no real figure is deleted.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = ["EdgeCase", "Settled", "settle", "tally"]

F = TypeVar("F")
P = TypeVar("P")

#: Set to a ``Counter`` to count every edge that fires; ``None`` (the default)
#: counts nothing. Measures which edge cases real figures use.
tally: Counter[str] | None = None


@dataclass(frozen=True)
class EdgeCase(Generic[F, P]):
    """One special case: when it applies and how it changes the plan."""

    name: str
    why: str
    example: str
    """``<test file>::<test function>`` in the slice's ``tests/``."""
    applies: Callable[[F, P], bool]
    adjust: Callable[[F, P], P]


@dataclass(frozen=True)
class Settled(Generic[P]):
    """The final plan and the names of the edge cases that changed it."""

    plan: P
    fired: tuple[str, ...]


def settle(facts: F, plan: P, edges: Sequence[EdgeCase[F, P]]) -> Settled[P]:
    """Apply each edge case that applies, in order, to the main-path plan."""
    fired: list[str] = []
    for edge in edges:
        if edge.applies(facts, plan):
            plan = edge.adjust(facts, plan)
            fired.append(edge.name)
    if tally is not None:
        tally.update(fired)
    return Settled(plan=plan, fired=tuple(fired))
