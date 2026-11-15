"""Named edge cases a slice appends after its main decision.

A slice decides its plan for the ordinary figure in ``decide.py``. Whatever
only matters for an unusual figure (a hidden SubFigure, a polar axis, an empty
panel) does not go into that function as one more branch. It goes into the
slice's ``edges.py`` as one more :class:`EdgeCase` at the end of ``EDGES``::

    EDGES: tuple[EdgeCase[Facts, Plan], ...] = (
        EdgeCase(
            name="hidden-subfigure",
            why="a hidden SubFigure draws nothing, so it takes no margin",
            applies=has_hidden_subfigure,
            adjust=drop_hidden_subfigures,
        ),
    )

``settle(facts, plan, EDGES)`` applies them in order and reports which fired,
so the main path stays readable and every special case has a name, a reason
and a test that mentions the name.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = ["EdgeCase", "Settled", "settle"]

F = TypeVar("F")
P = TypeVar("P")


@dataclass(frozen=True)
class EdgeCase(Generic[F, P]):
    """One special case: when it applies and how it changes the plan."""

    name: str
    why: str
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
    return Settled(plan=plan, fired=tuple(fired))
