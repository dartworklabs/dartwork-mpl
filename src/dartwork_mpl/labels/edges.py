"""The labels' named special cases, applied after the decisions in ``decide.py``.

Each one came from a chart that came out wrong without it; the ``why`` says
which. ``EDGES`` holds them all, grouped by the decision they follow
(:data:`TEXT`, :data:`BARS`, :data:`INK`, :data:`HIDDEN`, :data:`CELLS`,
:data:`LEFTS`): keep each group's entries together and in order.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, cast

from ..edgecase import EdgeCase
from .model import (
    HiddenFacts,
    Ink,
    InkFacts,
    LabelText,
    Letters,
    Notice,
    PanelsFacts,
    Shown,
    ValueFacts,
    prints_zero,
)
from .stacks import BarsFacts, BarsPlan, Planned

# A letter this far (px) into what a neighbour draws has no room.
TOUCH_PX = 0.5


# ------------------------------------------------------------ text
def _rounds_to_zero(facts: ValueFacts, plan: LabelText) -> bool:
    """A non-zero value the label rule prints as zero (``0.03M`` at 0 places)."""
    value = facts.scaled
    return (
        not facts.precise
        and value != 0
        and math.isfinite(value)
        and prints_zero(value, plan.decimals)
    )


def _bound(facts: ValueFacts, plan: LabelText) -> LabelText:
    """The _bound it lies within, one last place: ``<0.1M``, ``>−0.1M``."""  # noqa: RUF002
    step = 10.0**-plan.decimals
    up = facts.scaled > 0
    return LabelText(
        step if up else -step, plan.decimals, lead="<" if up else ">"
    )


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


# ------------------------------------------------------------ hidden
def _some_hidden(facts: HiddenFacts, plan: Notice) -> bool:
    return facts.hidden_rows + facts.hidden_columns > 0


def _hidden_text(facts: HiddenFacts, plan: Notice) -> Notice:
    rows, columns = facts.hidden_rows > 0, facts.hidden_columns > 0
    if rows and columns:
        why, fix = "bars too close together for their text", "a larger figure"
    elif rows:
        why, fix = "barh rows thinner than the text", "a taller figure"
    else:
        why, fix = "bars closer together than their text", "a wider figure"
    hidden = facts.hidden_rows + facts.hidden_columns
    return Notice(
        f"dm.label_bars: {hidden} of {facts.labels} bar value labels are "
        f"hidden where they would overlap ({why}); {fix} brings them back, "
        "and crowded='skip' hides labels on purpose without this warning"
    )


# ------------------------------------------------------------ panel letters
def _nested_cells(facts: PanelsFacts, plan: PanelsFacts) -> bool:
    return any(p.cell != p.outer_cell for p in plan.panels)


def _outer_cells(facts: PanelsFacts, plan: PanelsFacts) -> PanelsFacts:
    return replace(
        plan, panels=tuple(replace(p, cell=p.outer_cell) for p in plan.panels)
    )


def _crowded_bare(facts: PanelsFacts, plan: Letters) -> Shown:
    """The bare panels whose letter would reach what their left neighbour
    draws."""
    return Shown(
        tuple(
            p.bare
            and p.ylabel_x0 is None
            and p.neighbour_x1 is not None
            and p.neighbour_x1 - left > TOUCH_PX
            for p, left in zip(facts.panels, plan.lefts, strict=True)
        )
    )


def _bare_reaches_neighbour(facts: PanelsFacts, plan: Letters) -> bool:
    return any(_crowded_bare(facts, plan).flags)


def _on_own_spine(facts: PanelsFacts, plan: Letters) -> Letters:
    """The bare panels of a column holding a crowded one start on their spine."""
    crowded = _crowded_bare(facts, plan).flags
    lefts = list(plan.lefts)
    for i, p in enumerate(facts.panels):
        column = facts.mates(i, 1)
        if p.bare and p.ylabel_x0 is None and any(crowded[j] for j in column):
            lefts[i] = p.corner[0]
    return replace(plan, lefts=tuple(lefts))


def _before_title(facts: PanelsFacts, plan: Letters) -> Letters:
    """Each letter's right edge half a letter size before a title it would
    reach; a left title always counts."""
    lefts: list[float] = []
    for p, left in zip(facts.panels, plan.lefts, strict=True):
        for t in p.titles:
            if t.loc == "left" or (
                left < t.x1 + p.gap and left + p.width + p.gap > t.x0
            ):
                left = min(left, t.x0 - p.gap - p.width)
        lefts.append(left)
    return replace(plan, lefts=tuple(lefts))


def _title_in_way(facts: PanelsFacts, plan: Letters) -> bool:
    return _before_title(facts, plan) != plan


EDGES: tuple[EdgeCase[Any, Any], ...] = (
    EdgeCase(
        name="tiny-value-bound",
        why="0.03M beside 12.5M printed '0M', a value that is not zero",
        applies=_rounds_to_zero,
        adjust=_bound,
    ),
    EdgeCase(
        name="signed-steps",
        why="a waterfall's steps read as changes: +30 and −15",  # noqa: RUF001
        applies=_wants_plus,
        adjust=_plus,
    ),
    EdgeCase(
        name="stacked-segments-totals",
        why="stacked bars labelled each bar's end, not the segments and the "
        "stack's total; a zero bar padding a split highlight got a '0'",
        applies=_shares_positions,
        adjust=_stack_labels,
    ),
    EdgeCase(
        name="inside-readable-ink",
        why="a label in the text colour vanished on a dark bar",
        applies=_on_bar,
        adjust=_readable,
    ),
    EdgeCase(
        name="series-colour",
        why="a waterfall colours its steps' labels like the steps",
        applies=_series_off_bar,
        adjust=_series,
    ),
    EdgeCase(
        name="warn-hidden-labels",
        why="labels hidden for room went missing without a word",
        applies=_some_hidden,
        adjust=_hidden_text,
    ),
    EdgeCase(
        name="panel-colorbar-column",
        why="a colour bar's nested grid made its panel a column of its own",
        applies=_nested_cells,
        adjust=_outer_cells,
    ),
    EdgeCase(
        name="panel-inner-shared-y",
        why="an inner shared-y panel's letter parted the panels to hold the "
        "spine distance (4.56 to 2.37 cm on a slide, #722)",
        applies=_bare_reaches_neighbour,
        adjust=_on_own_spine,
    ),
    EdgeCase(
        name="panel-left-title",
        why="a letter ran into a left title on its baseline",
        applies=_title_in_way,
        adjust=_before_title,
    ),
)


TEXT = cast("tuple[EdgeCase[ValueFacts, LabelText], ...]", EDGES[0:2])
BARS = cast("tuple[EdgeCase[BarsFacts, BarsPlan], ...]", EDGES[2:3])
INK = cast("tuple[EdgeCase[InkFacts, Ink], ...]", EDGES[3:5])
HIDDEN = cast("tuple[EdgeCase[HiddenFacts, Notice], ...]", EDGES[5:6])
CELLS = cast("tuple[EdgeCase[PanelsFacts, PanelsFacts], ...]", EDGES[6:7])
LEFTS = cast("tuple[EdgeCase[PanelsFacts, Letters], ...]", EDGES[7:9])
