"""Each named layout edge case: when it fires and what it changes."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.edgecase import settle
from dartwork_mpl.layout import decide
from dartwork_mpl.layout.edges import EDGES, TEXT_EDGES, away_from_centre
from dartwork_mpl.layout.model import (
    AngleLabel,
    ArtistId,
    AxesContent,
    AxisName,
    Box,
    Canvas,
    ContentFacts,
    Count,
    Degrees,
    FigureArtist,
    HSpace,
    Line,
    Px,
    Reach,
    Rim,
    Share,
    Sides,
    Spacing,
    TextFacts,
    TickGroup,
    WSpace,
)
from dartwork_mpl.layout.tests.test_decide import chars, row
from dartwork_mpl.vocab import (
    AlignBottom,
    AlignCentre,
    AlignLeft,
    AlignRight,
    AlignTop,
    VCentre,
    Y,
)

NO_MARGIN = Sides(0.0, 0.0, 0.0, 0.0)
PLOT = Box(100.0, 100.0, 900.0, 400.0)
CANVAS = Canvas(Px(1000.0), Px(500.0))
CLEAR = Box(10.0, 100.0, 30.0, 400.0)  # a y name on the canvas, alone


def test_text_wider_than_the_room_keeps_the_plot() -> None:
    # A 1300 px title centred on an 800 px plot of a 1000 px canvas.
    plot = Box(100.0, 100.0, 900.0, 400.0)
    titled = Box(-150.0, 100.0, 1150.0, 450.0)
    axes = AxesContent(
        Sides(0.1, 0.9, 0.2, 0.8), titled, Px(1300.0), plot, True
    )
    facts = ContentFacts((axes,), (), CANVAS, NO_MARGIN, None, Px(0.0))
    plain = decide.solve(facts, decide.reserves(facts))
    settled = settle(facts, facts, EDGES)
    assert settled.fired == ("text-wider-than-the-room",)
    assert plain is not None and plain.edges.right - plain.edges.left < 0.6
    step = decide.solve(settled.plan, decide.reserves(settled.plan))
    assert step is not None
    assert (step.edges.left, step.edges.right) == (0.0, 1.0)


def test_name_taller_than_the_room_keeps_the_plot() -> None:
    # A 600 px y name centred on a 300 px plot of a 500 px canvas.
    plot = Box(100.0, 100.0, 900.0, 400.0)
    named = Box(60.0, -50.0, 900.0, 550.0)
    axes = AxesContent(Sides(0.1, 0.9, 0.2, 0.8), named, Px(80.0), plot, False)
    facts = ContentFacts((axes,), (), CANVAS, NO_MARGIN, None, Px(0.0))
    plain = decide.solve(facts, decide.reserves(facts))
    settled = settle(facts, facts, EDGES)
    assert settled.fired == ("name-taller-than-the-room",)
    assert plain is not None and plain.edges.top - plain.edges.bottom < 0.4
    step = decide.solve(settled.plan, decide.reserves(settled.plan))
    assert step is not None
    assert (step.edges.bottom, step.edges.top) == (0.0, 1.0)


def test_figure_title_on_panel_titles_keeps_the_pad() -> None:
    # A suptitle 20 px tall at the top of a 500 px canvas, panels titled.
    plot = Box(100.0, 100.0, 900.0, 400.0)
    titled = Box(100.0, 100.0, 900.0, 430.0)
    axes = AxesContent(Sides(0.1, 0.9, 0.2, 0.8), titled, Px(80.0), plot, True)
    title = FigureArtist(Box(400.0, 475.0, 600.0, 495.0), False, Px(0.0))
    facts = ContentFacts((axes,), (title,), CANVAS, NO_MARGIN, None, Px(8.0))
    settled = settle(facts, facts, EDGES)
    assert settled.fired == ("figure-title-on-panel-titles",)
    step = decide.solve(settled.plan, decide.reserves(settled.plan))
    assert step is not None
    # The panel titles end 8 px under the suptitle's 475 px bottom.
    assert step.edges.top * 500.0 + 30.0 == 475.0 - 8.0
    untitled = replace(facts, axes=(replace(axes, titled=False),))
    assert settle(untitled, untitled, EDGES).fired == ()


def text_plan(facts: TextFacts):
    result = settle(facts, decide.text_plan(facts), TEXT_EDGES)
    return result.fired, result.plan


def texts(groups=(), names=(), spacings=(), rims=()) -> TextFacts:
    return TextFacts(
        tuple(groups), tuple(names), tuple(spacings), CANVAS, tuple(rims)
    )


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


def test_panels_too_short_for_their_text_stay() -> None:
    # Parting by 400 px leaves 800 px cells 200 px, under two 120 px ems.
    reaches = (
        Reach((0, 1), (0, 1), Px(0.0), Px(340.0)),
        Reach((1, 2), (0, 1), Px(0.0), Px(0.0)),
    )
    space = Spacing(
        HSpace(),
        reaches,
        (Px(20.0),),
        Px(800.0),
        Count(2),
        Share(0.2),
        Px(120.0),
    )
    assert text_plan(texts(spacings=[space]))[0] == ()


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


DISC = Box(300.0, 100.0, 700.0, 500.0)  # centre (500, 300), radius 200


def angle_label(label: int, box: Box, angle: float) -> AngleLabel:
    return AngleLabel(ArtistId(label), box, Degrees(angle), Px(20.0))


def test_angle_labels_in_the_plot_are_aligned_away_from_it() -> None:
    # "Customer support", centred on its anchor left of the circle, reaches
    # 50 px into it; the short name on top is clear.
    long = angle_label(1, Box(150.0, 290.0, 350.0, 310.0), 180.0)
    top = angle_label(2, Box(480.0, 510.0, 520.0, 530.0), 90.0)
    fired, plan = text_plan(texts(rims=[Rim(DISC, (long, top), False)]))
    assert fired == ("angle-labels-in-the-plot",)
    # every label of that plot, so they stand at one distance from it
    assert plan.away == {
        ArtistId(1): (AlignRight(), VCentre()),
        ArtistId(2): (AlignCentre(), AlignBottom()),
    }
    # labels somebody placed stay, and so does a rim of names that clear it
    assert text_plan(texts(rims=[Rim(DISC, (long, top), True)]))[0] == ()
    clear = angle_label(1, Box(80.0, 290.0, 280.0, 310.0), 180.0)
    assert text_plan(texts(rims=[Rim(DISC, (clear, top), False)]))[0] == ()


def test_a_label_is_aligned_on_the_far_side_of_its_anchor() -> None:
    table = {
        0.0: (AlignLeft(), VCentre()),
        38.6: (AlignLeft(), AlignBottom()),  # a seven-axis radar
        67.5: (AlignCentre(), AlignBottom()),  # NNE: beside the top name
        90.0: (AlignCentre(), AlignBottom()),
        141.4: (AlignRight(), AlignBottom()),
        -90.0: (AlignCentre(), AlignTop()),
        -115.7: (AlignRight(), AlignTop()),
    }
    for angle, expected in table.items():
        assert away_from_centre(Degrees(angle)) == expected
