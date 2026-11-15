"""Each named layout edge case: when it fires and what it changes."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.edgecase import settle
from dartwork_mpl.layout import decide
from dartwork_mpl.layout.edges import FIT_EDGES, TEXT_EDGES
from dartwork_mpl.layout.model import (
    ArtistId,
    AxisName,
    Box,
    Count,
    Degrees,
    Edge,
    FigureArtist,
    Gap,
    Line,
    Piece,
    Px,
    Reach,
    Share,
    Spacing,
    TextFacts,
    TickGroup,
    Which,
)
from dartwork_mpl.layout.tests.test_decide import (
    CANVAS,
    axes,
    chars,
    content,
    row,
)

PLOT = Box(100.0, 900.0, 100.0, 400.0)


def fit_of(facts):
    result = settle(facts, decide.fit(facts), FIT_EDGES)
    return result.fired, result.plan


def text_plan(facts: TextFacts):
    result = settle(facts, decide.text_plan(facts), TEXT_EDGES)
    return result.fired, result.plan


def texts(groups=(), names=(), spacings=(), wrapped_names=None) -> TextFacts:
    return TextFacts(
        tuple(groups),
        tuple(names),
        wrapped_names or {},
        tuple(spacings),
        CANVAS,
    )


def test_axes_3d_counts_its_tight_boxes() -> None:
    tight = (Piece(Box(50.0, 950.0, 50.0, 450.0)),)
    a = replace(axes(PLOT), tight=tight)
    fired, plan = fit_of(content(a))
    assert fired == ("axes-3d",)
    assert plan.axes[0].pieces == tight


def test_outside_legend_along_side_counts_past_the_canvas_only() -> None:
    above = Piece(Box(50.0, 1020.0, 410.0, 450.0), outside=Edge.TOP)
    fired, plan = fit_of(content(axes(PLOT, above)))
    assert fired == ("outside-legend-along-side",)
    assert plan.axes[0].pieces[0].box == Box(100.0, 1020.0, 410.0, 450.0)


def test_figure_text_edge_band_reserves_by_reading_direction() -> None:
    # A source line in the bottom-left corner is nearer the left edge.
    note = FigureArtist(Box(5.0, 300.0, 5.0, 20.0), None, False, None, Px(0.0))
    fired, plan = fit_of(content(axes(PLOT), artists=[note]))
    assert fired == ("figure-text-edge-band",)
    assert plan.reserves == (Edge.BOTTOM,)


def test_figure_legend_side_reserves_its_side() -> None:
    wide = FigureArtist(
        Box(2.0, 998.0, 200.0, 300.0), None, None, Edge.TOP, Px(0.0)
    )
    fired, plan = fit_of(content(axes(PLOT), artists=[wide]))
    assert fired == ("figure-legend-side",)
    assert plan.reserves == (Edge.TOP,)


def name(label: int, text_: str, box: Box, span: float = 300.0) -> AxisName:
    group = (ArtistId(7), Which.Y)
    return AxisName(
        ArtistId(label),
        Line(text_),
        Px(span),
        box,
        group,
        (Box(0.0, 50.0, 100.0, 200.0),),
        chars,
    )


def test_overlong_axis_name_wraps_and_its_twin_follows() -> None:
    long = "x" * 200 + " " + "y" * 200  # 401 chars over a 300 px side
    blocked = name(1, long, Box(10.0, 30.0, 0.0, 600.0))  # past the top
    clear = name(2, long, Box(500.0, 520.0, 100.0, 400.0))
    fired, plan = text_plan(texts(names=[blocked, clear]))
    assert fired == ("overlong-axis-name",)
    wrapped = Line("x" * 200 + "\n" + "y" * 200)
    assert plan.names == {ArtistId(1): wrapped, ArtistId(2): wrapped}


def test_colliding_panels_part_by_half_an_em() -> None:
    reaches = (
        Reach((0, 1), (0, 1), Px(0.0), Px(40.0)),
        Reach((1, 2), (0, 1), Px(30.0), Px(0.0)),
    )
    space = Spacing(
        Gap.WSPACE,
        reaches,
        (Px(20.0),),
        Px(800.0),
        Count(2),
        Share(0.2),
        Px(10.0),
    )
    fired, plan = text_plan(texts(spacings=[space]))
    assert fired == ("colliding-panels",)
    assert plan.spacing[Gap.WSPACE] == 75.0 * 2 / (800.0 - 75.0)


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
