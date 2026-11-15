"""The child's named special cases for picking the figure, applied after ``decide.choose_figure``.

Agents name their figure differently (``f``, ``figure``) or never bind it
(``plt.subplots()`` result unpacked into axes only). When ``figure_var`` is
not a Figure but pyplot has figures open, the child saves the current one
and the report says so.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from .model import FigureChoice, FigureFacts, Pick


def one_unnamed(facts: FigureFacts, plan: FigureChoice) -> bool:
    """``figure_var`` is no Figure, and exactly one figure is open."""
    return plan.pick is Pick.NONE and facts.open == 1


def several_unnamed(facts: FigureFacts, plan: FigureChoice) -> bool:
    """``figure_var`` is no Figure, and several figures are open."""
    return plan.pick is Pick.NONE and facts.open > 1


def take_current(facts: FigureFacts, plan: FigureChoice) -> FigureChoice:
    """Save pyplot's current figure, with a note naming the guess."""
    note = "figure_var is not a Figure; saved pyplot's current figure"
    if facts.open > 1:
        note += f" (the last of {facts.open} open)"
    return FigureChoice(Pick.CURRENT, note)


EDGES: tuple[EdgeCase[FigureFacts, FigureChoice], ...] = (
    EdgeCase(
        name="figure-var-unbound",
        why="agents unpack plt.subplots() into other names or none; the one"
        " open figure is unambiguously the chart",
        applies=one_unnamed,
        adjust=take_current,
    ),
    EdgeCase(
        name="several-figures-unbound",
        why="a script that opens several figures without naming one most"
        " likely drew the chart last; the note tells the caller to name it",
        applies=several_unnamed,
        adjust=take_current,
    ),
)
