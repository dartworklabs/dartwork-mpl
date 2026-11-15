"""The tick slice's named special cases, appended after the main decisions.

Each stage settles its own registry, typed by what it decides: the ladder
(:data:`LADDER_EDGES`), the format of an Axes nobody formatted
(:data:`AXES_EDGES`) and the date ticks after the fit (:data:`THIN_EDGES`).
"""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from .axis_plans import (
    AxesFacts,
    AxesPlan,
    AxisFacts,
    AxisPlan,
    Crowding,
    DateAxis,
    Leave,
    NumberAxis,
    Numbers,
    OtherAxis,
    PeriodDates,
    QuarterDates,
    Thinning,
    YearTicks,
)
from .model import MYRIAD, Asked, ByFigure, Ems, Ladder, Language, TwinSide

# Neighbouring date labels keep at least this many ems between them.
MIN_DATE_GAP = Ems(1.0)


def korean_auto(facts: Language, plan: Ladder) -> bool:
    """The ladder follows the figure, and its labels are Korean."""
    match facts:
        case ByFigure(korean=korean):
            return korean
        case Asked():
            return False


def myriad(facts: Language, plan: Ladder) -> Ladder:
    """만/억/조/경."""
    return MYRIAD


def has_year_data(facts: AxesFacts, plan: AxesPlan) -> bool:
    """x data that are integer years, with a default locator or formatter."""
    x = facts.x
    match x.kind:
        case NumberAxis(years=years):
            return (
                years
                and not x.fixed_texts
                and (x.own_locator or x.own_formatter)
            )
        case DateAxis() | OtherAxis():
            return False


def year_ticks(facts: AxesFacts, plan: AxesPlan) -> AxesPlan:
    """Whole-year ticks and two-digit years where the defaults still are."""
    x = facts.x
    return replace(
        plan, x=YearTicks(facts.digits, x.own_locator, x.own_formatter)
    )


def _quarter_ends(axis: AxisFacts) -> bool | None:
    match axis.kind:
        case DateAxis(quarter_ends=ends):
            return ends
        case NumberAxis() | OtherAxis():
            return None


def _quarters(axis: AxisFacts, plan: AxisPlan) -> AxisPlan:
    ends = _quarter_ends(axis)
    match plan:
        case PeriodDates(digits=digits) if ends is not None:
            return QuarterDates(digits, ends)
        case PeriodDates() | Leave() | Numbers() | QuarterDates() | YearTicks():
            return plan


def has_quarterly_dates(facts: AxesFacts, plan: AxesPlan) -> bool:
    """A period date axis whose plotted dates run a quarter apart."""
    return (_quarters(facts.x, plan.x), _quarters(facts.y, plan.y)) != (
        plan.x,
        plan.y,
    )


def quarter_ticks(facts: AxesFacts, plan: AxesPlan) -> AxesPlan:
    """Quarter ticks and words, which stay quarters when thinned."""
    return replace(
        plan, x=_quarters(facts.x, plan.x), y=_quarters(facts.y, plan.y)
    )


def _twin_spines(facts: AxesFacts) -> frozenset[TwinSide]:
    """Sides where the Axes draws a twin scale: the twin's line first."""
    twin = facts.twin
    return frozenset(
        side
        for side in twin.draws - twin.settled
        if side in twin.hides_other or side not in twin.twin_draws
    )


def draws_twin_scale(facts: AxesFacts, plan: AxesPlan) -> bool:
    """The Axes draws its own scale on the right or top of a shared box."""
    return bool(_twin_spines(facts))


def show_twin_spines(facts: AxesFacts, plan: AxesPlan) -> AxesPlan:
    """That side's spine, which the presets hide."""
    return replace(plan, spines=plan.spines | _twin_spines(facts))


def crowded(facts: Crowding, plan: Thinning) -> bool:
    """Neighbouring date labels closer than one em at the fitted size."""
    return facts.gap < MIN_DATE_GAP


def first_uncrowded(facts: Crowding, plan: Thinning) -> Thinning:
    """The first sparser tick set one em apart; with none, keep the ticks."""
    apart = [c.index for c in facts.candidates if c.gap >= MIN_DATE_GAP]
    return Thinning(apart[0] if apart else None)


LADDER_EDGES: tuple[EdgeCase[Language, Ladder], ...] = (
    EdgeCase(
        name="korean-myriad",
        why="a Korean figure read its large numbers in k/M/G, which Korean "
        "readers count in 만/억/조",
        example="test_edges.py::test_korean_myriad",
        applies=korean_auto,
        adjust=myriad,
    ),
)

AXES_EDGES: tuple[EdgeCase[AxesFacts, AxesPlan], ...] = (
    EdgeCase(
        name="year-axis-x",
        why="annual x data ticked by matplotlib read 2007.5 and 2,010",
        example="test_edges.py::test_year_axis_x",
        applies=has_year_data,
        adjust=year_ticks,
    ),
    EdgeCase(
        name="quarterly-dates",
        why="quarterly data on month ticks read 24.01, 24.04 and lost Q1",
        example="test_edges.py::test_quarterly_dates",
        applies=has_quarterly_dates,
        adjust=quarter_ticks,
    ),
    EdgeCase(
        name="twin-scale-spine",
        why="the presets hide the right and top spines, so a twin scale "
        "had no axis line",
        example="test_edges.py::test_twin_scale_spine",
        applies=draws_twin_scale,
        adjust=show_twin_spines,
    ),
)

THIN_EDGES: tuple[EdgeCase[Crowding, Thinning], ...] = (
    EdgeCase(
        name="crowded-dates-thin",
        why="matplotlib picks date ticks from the range alone, so labels on "
        "a narrow axis collided",
        example="test_edges.py::test_crowded_dates_thin",
        applies=crowded,
        adjust=first_uncrowded,
    ),
)
