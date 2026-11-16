"""Each named layout edge case: when it fires and what it changes."""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.layout import decide
from dartwork_mpl.layout.edges import TEXT_EDGES
from dartwork_mpl.layout.model import (
    ArtistId,
    AxisName,
    Box,
    Canvas,
    Count,
    Degrees,
    Line,
    Px,
    Reach,
    Share,
    Spacing,
    TextFacts,
    TickGroup,
    WSpace,
)
from dartwork_mpl.layout.tests.test_decide import chars, row
from dartwork_mpl.vocab import Y

PLOT = Box(100.0, 100.0, 900.0, 400.0)
CANVAS = Canvas(Px(1000.0), Px(500.0))
CLEAR = Box(10.0, 100.0, 30.0, 400.0)  # a y name on the canvas, alone


def text_plan(facts: TextFacts):
    result = settle(facts, decide.text_plan(facts), TEXT_EDGES)
    return result.fired, result.plan


def texts(groups=(), names=(), spacings=()) -> TextFacts:
    return TextFacts(tuple(groups), tuple(names), tuple(spacings), CANVAS)


def name(
    label: int,
    text_: str,
    span: float = 300.0,
    box: Box = CLEAR,
    others: tuple[Box, ...] = (),
) -> AxisName:
    return AxisName(
        ArtistId(label),
        Line(text_),
        Px(span),
        (ArtistId(7), Y()),
        chars,
        box,
        others,
    )


def test_overlong_axis_name_wraps_and_its_twin_follows() -> None:
    long = "x" * 200 + " " + "y" * 200  # 401 chars over a 300 px side
    off_canvas = Box(10.0, -50.0, 30.0, 551.0)
    short_side = name(1, long, box=off_canvas)
    twin = name(2, long, span=1000.0)  # fits its own side, takes the form
    fired, plan = text_plan(texts(names=[short_side, twin]))
    assert fired == ("overlong-axis-name",)
    wrapped = Line("x" * 200 + "\n" + "y" * 200)
    assert plan.names == {ArtistId(1): wrapped, ArtistId(2): wrapped}


def test_a_name_longer_than_its_side_that_meets_nothing_stays() -> None:
    long = "x" * 200 + " " + "y" * 200
    assert text_plan(texts(names=[name(1, long)]))[0] == ()
    into = name(1, long, others=(Box(20.0, 300.0, 200.0, 450.0),))
    assert text_plan(texts(names=[into]))[0] == ("overlong-axis-name",)


def test_colliding_panels_part_by_half_an_em() -> None:
    reaches = (
        Reach((0, 1), (0, 1), Px(0.0), Px(40.0)),
        Reach((1, 2), (0, 1), Px(30.0), Px(0.0)),
    )
    space = Spacing(
        WSpace(),
        reaches,
        (Px(20.0),),
        Px(800.0),
        Count(2),
        Share(0.2),
        Px(10.0),
    )
    fired, plan = text_plan(texts(spacings=[space]))
    assert fired == ("colliding-panels",)
    assert plan.spacing[WSpace()] == 75.0 * 2 / (800.0 - 75.0)


def test_crowded_ticks_wrap_at_spaces() -> None:
    labels = ["Customer Support", "Product Engineering", "Sales Operations"]
    group = TickGroup(ArtistId(1), (row(labels, [18.0, 18.0]),), {})
    fired, plan = text_plan(texts(groups=[group]))
    assert fired == ("crowded-ticks-wrap",)
    assert (
        plan.wraps[ArtistId(1)][Line("Product Engineering")]
        == "Product\nEngineering"
    )
    assert plan.turns == {}


def test_crowded_ticks_rotate_when_they_cannot_wrap() -> None:
    numbers = ["1,000,000", "2,000,000", "3,000,000"]
    group = TickGroup(ArtistId(1), (row(numbers, [8.0, 8.0], height=3.0),), {})
    fired, plan = text_plan(texts(groups=[group]))
    assert fired == ("crowded-ticks-rotate",)
    assert plan.turns == {ArtistId(1): Degrees(45.0)}
    assert plan.wraps == {}
