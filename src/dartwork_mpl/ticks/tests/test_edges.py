"""One test per named tick edge case, on the pure facts."""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.ticks.decide import axes_plan, ladder, thinning
from dartwork_mpl.ticks.edges import AXES_EDGES, LADDER_EDGES, THIN_EDGES
from dartwork_mpl.ticks.model import (
    MYRIAD,
    SI,
    Asked,
    AxesFacts,
    AxisFacts,
    ByFigure,
    Candidate,
    Crowding,
    DateAxis,
    Ems,
    NumberAxis,
    PeriodDates,
    QuarterDates,
    TickValues,
    TwinFacts,
    YearTicks,
)

TICKS = TickValues.of([0, 1, 2])


def _axes(
    x: AxisFacts | None = None, y: AxisFacts | None = None, **kw
) -> AxesFacts:
    x = x or AxisFacts(x=True, kind=NumberAxis(), ticks=TICKS)
    y = y or AxisFacts(x=False, kind=NumberAxis(), ticks=TICKS)
    return AxesFacts(x, y, **kw)


def _settle(facts: AxesFacts):
    return settle(facts, axes_plan(facts), AXES_EDGES)


def test_korean_myriad():
    korean = ByFigure(korean=True)
    settled = settle(korean, ladder(korean), LADDER_EDGES)
    assert (settled.plan, settled.fired) == (MYRIAD, ("korean-myriad",))
    for facts in (ByFigure(korean=False), Asked(SI)):
        assert settle(facts, ladder(facts), LADDER_EDGES).plan is SI


def test_year_axis_x():
    years = AxisFacts(
        x=True, kind=NumberAxis(years=True), ticks=TickValues.of([2016, 2020])
    )
    settled = _settle(_axes(years))
    assert settled.fired == ("year-axis-x",)
    assert settled.plan.x == YearTicks(2, locator=True, formatter=True)
    # a formatter someone set stays; only the ticks become whole years
    theirs = AxisFacts(
        x=True, kind=NumberAxis(years=True), ticks=TICKS, own_formatter=False
    )
    assert _settle(_axes(theirs)).plan.x == YearTicks(
        2, locator=True, formatter=False
    )


def test_quarterly_dates():
    dates = AxisFacts(x=True, kind=DateAxis(quarter_ends=True), ticks=TICKS)
    settled = _settle(_axes(dates, digits=4))
    assert settled.fired == ("quarterly-dates",)
    assert settled.plan.x == QuarterDates(4, ends=True)
    monthly = AxisFacts(x=True, kind=DateAxis(), ticks=TICKS)
    assert _settle(_axes(monthly)).plan.x == PeriodDates(2)


def test_twin_scale_spine():
    twin = TwinFacts(
        draws=frozenset({"right"}),
        hides_other=frozenset({"right", "top"}),
        twin_draws=frozenset({"right"}),
    )
    settled = _settle(_axes(twin=twin))
    assert settled.fired == ("twin-scale-spine",)
    assert settled.plan.spines == {"right"}
    # the twin's line first: a parent drawing there too keeps the preset's look
    parent = TwinFacts(
        draws=frozenset({"right"}), twin_draws=frozenset({"right"})
    )
    assert _settle(_axes(twin=parent)).plan.spines == frozenset()
    # once: a side settled by an earlier layout is not shown again
    again = TwinFacts(
        draws=frozenset({"right"}),
        hides_other=frozenset({"right"}),
        settled=frozenset({"right"}),
    )
    assert _settle(_axes(twin=again)).fired == ()


def test_crowded_dates_thin():
    near = (
        Candidate(0, Ems(0.4)),
        Candidate(1, Ems(1.3)),
        Candidate(2, Ems(2.0)),
    )
    crowded = Crowding(Ems(0.2), near)
    settled = settle(crowded, thinning(crowded), THIN_EDGES)
    assert settled.fired == ("crowded-dates-thin",)
    assert settled.plan.index == 1
    hopeless = Crowding(Ems(0.2), near[:1])
    assert settle(hopeless, thinning(hopeless), THIN_EDGES).plan.index is None
    apart = Crowding(Ems(1.5), ())
    assert settle(apart, thinning(apart), THIN_EDGES).fired == ()
