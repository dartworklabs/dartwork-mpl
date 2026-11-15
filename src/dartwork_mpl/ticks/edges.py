"""The tick slice's named special cases, appended after the main decisions.

``EDGES`` holds them all; each stage settles its own slice of it, typed by
what it decides: the ladder (:data:`LADDER_EDGES`), the format of an Axes
nobody formatted (:data:`AXES_EDGES`), a number axis's text at draw time
(:data:`TEXT_EDGES`) and the date ticks after the fit (:data:`THIN_EDGES`).
"""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from .model import (
    MYRIAD,
    AxesFacts,
    AxesPlan,
    AxisFacts,
    AxisPlan,
    AxisText,
    Crowding,
    Ems,
    Kind,
    Ladder,
    LadderChoice,
    Language,
    PeriodDates,
    PinTicks,
    QuarterDates,
    Side,
    TextFacts,
    Thinning,
    YearTicks,
)

# Neighbouring date labels keep at least this many ems between them.
MIN_DATE_GAP = Ems(1.0)


def korean_auto(facts: Language, plan: Ladder) -> bool:
    """The ladder follows the figure, and its labels are Korean."""
    return facts.asked is LadderChoice.AUTO and facts.korean


def myriad(facts: Language, plan: Ladder) -> Ladder:
    """만/억/조/경."""
    return MYRIAD


def _pinnable(axis: AxisFacts) -> bool:
    return (
        axis.kind is Kind.NUMBERS
        and axis.fixed_texts
        and axis.pinnable
        and axis.own_locator
    )


def has_pinnable_texts(facts: AxesFacts, plan: AxesPlan) -> bool:
    """Texts someone fixed by order under matplotlib's own locator."""
    return _pinnable(facts.x) or _pinnable(facts.y)


def pin_ticks(facts: AxesFacts, plan: AxesPlan) -> AxesPlan:
    """The fixed texts' axes keep the ticks they were made for."""
    x: AxisPlan = PinTicks() if _pinnable(facts.x) else plan.x
    y: AxisPlan = PinTicks() if _pinnable(facts.y) else plan.y
    return replace(plan, x=x, y=y)


def has_year_data(facts: AxesFacts, plan: AxesPlan) -> bool:
    """x data that are integer years, with a default locator or formatter."""
    x = facts.x
    return (
        x.kind is Kind.NUMBERS
        and x.years
        and not x.fixed_texts
        and (x.own_locator or x.own_formatter)
    )


def year_ticks(facts: AxesFacts, plan: AxesPlan) -> AxesPlan:
    """Whole-year ticks and two-digit years where the defaults still are."""
    x = facts.x
    return replace(
        plan, x=YearTicks(facts.digits, x.own_locator, x.own_formatter)
    )


def _quarters(axis: AxisFacts, plan: AxisPlan) -> AxisPlan:
    if isinstance(plan, PeriodDates) and axis.quarter_ends is not None:
        return QuarterDates(plan.digits, axis.quarter_ends)
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


def _twin_spines(facts: AxesFacts) -> frozenset[Side]:
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


def nonlinear(facts: TextFacts, plan: AxisText) -> bool:
    """Log and other non-linear scales span decades."""
    return not facts.ticks.linear and bool(facts.ticks.values)


def per_tick(facts: TextFacts, plan: AxisText) -> AxisText:
    """Each tick its own unit and decimals, unless the style fixed them."""
    return AxisText(facts.style.unit, facts.style.decimals)


def crowded(facts: Crowding, plan: Thinning) -> bool:
    """Neighbouring date labels closer than one em at the fitted size."""
    return facts.gap < MIN_DATE_GAP


def first_uncrowded(facts: Crowding, plan: Thinning) -> Thinning:
    """The first sparser tick set one em apart; with none, keep the ticks."""
    apart = [c.index for c in facts.candidates if c.gap >= MIN_DATE_GAP]
    return Thinning(apart[0] if apart else None)


EDGES = (
    EdgeCase(
        name="korean-myriad",
        why="a Korean figure reads large numbers in 만/억/조, not k/M/G",
        applies=korean_auto,
        adjust=myriad,
    ),
    EdgeCase(
        name="year-axis-x",
        why="annual x data ticked by matplotlib reads 2007.5 and 2,010",
        applies=has_year_data,
        adjust=year_ticks,
    ),
    EdgeCase(
        name="quarterly-dates",
        why="quarterly data on month ticks reads 24.01, 24.04 and loses Q1",
        applies=has_quarterly_dates,
        adjust=quarter_ticks,
    ),
    EdgeCase(
        name="author-fixed-tick-texts",
        why="texts fixed by order land on other ticks once the refit moves them",
        applies=has_pinnable_texts,
        adjust=pin_ticks,
    ),
    EdgeCase(
        name="twin-scale-spine",
        why="the presets hide the right and top spines, so a twin scale has none",
        applies=draws_twin_scale,
        adjust=show_twin_spines,
    ),
    EdgeCase(
        name="log-per-tick-unit",
        why="ticks spanning decades cannot share one unit (0.000001k, 1,000k)",
        applies=nonlinear,
        adjust=per_tick,
    ),
    EdgeCase(
        name="crowded-dates-thin",
        why="matplotlib picks date ticks from the range alone, so narrow axes collide",
        applies=crowded,
        adjust=first_uncrowded,
    ),
)

LADDER_EDGES = EDGES[:1]
AXES_EDGES = EDGES[1:5]
TEXT_EDGES = EDGES[5:6]
THIN_EDGES = EDGES[6:]
