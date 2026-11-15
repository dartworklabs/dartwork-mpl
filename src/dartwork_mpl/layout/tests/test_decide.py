"""The ordinary figure's decisions and the pure text helpers, as tables."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl.layout import decide
from dartwork_mpl.layout.edges import (
    balanced_lines,
    deepest_reach,
    gap_fraction,
    turn_angle,
    wrap_limit,
    wrap_to,
)
from dartwork_mpl.layout.model import (
    ArtistId,
    AxesContent,
    Bottom,
    Box,
    Canvas,
    ContentFacts,
    Count,
    Degrees,
    Edge,
    Edges,
    FigureArtist,
    Go,
    Left,
    Line,
    Piece,
    PlotSize,
    Px,
    Reach,
    Refuse,
    Request,
    Right,
    Sides,
    TickRow,
    Top,
    parse_margins,
    tokens,
)
from dartwork_mpl.size import mm

CANVAS = Canvas(Px(1000.0), Px(500.0))
NONE = Sides(0.0, 0.0, 0.0, 0.0)


def axes(plot: Box, *pieces: Piece) -> AxesContent:
    pos = Sides(plot.x0 / 1000, plot.x1 / 1000, plot.y0 / 500, plot.y1 / 500)
    return AxesContent(plot, pos, pieces)


def text(x0: float, x1: float, y0: float, y1: float, **kw: object) -> Piece:
    return Piece(Box(x0, x1, y0, y1), **kw)  # type: ignore[arg-type]


def content(
    *a: AxesContent, artists=(), margins=NONE, last=None
) -> ContentFacts:
    return ContentFacts(tuple(a), tuple(artists), CANVAS, margins, last)


def solve(facts: ContentFacts):
    return decide.solve(facts, decide.fit(facts))


@pytest.mark.parametrize(
    ("request_", "expected"),
    [
        (Request(False, False), Refuse(None)),
        (Request(True, False), Refuse(decide.NO_GRID)),
        (Request(True, True), Go()),
    ],
)
def test_answer(request_: Request, expected: object) -> None:
    assert decide.answer(request_) == expected


@pytest.mark.parametrize(
    ("margin", "sides", "expected"),
    [
        (0, (None,) * 4, Sides(0.0, 0.0, 0.0, 0.0)),
        ("5%", (None,) * 4, Sides(0.05, 0.05, 0.05, 0.05)),
        (0.1, (None, "1in", None, None), Sides(0.1, 0.25, 0.1, 0.1)),
        (mm(25.4), (None, None, 0.0, None), Sides(0.25, 0.25, 0.5, 0.0)),
    ],
)
def test_margins_become_figure_fractions(margin, sides, expected) -> None:
    assert parse_margins(margin, sides, (4.0, 2.0)) == expected


@pytest.mark.parametrize(
    ("margin", "error"),
    [
        (float("nan"), ValueError),
        ("inf%", ValueError),
        ("5", ValueError),
        (None, TypeError),
        (True, TypeError),
    ],
)
def test_bad_margins_raise(margin: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        parse_margins(margin, (None,) * 4, (4.0, 2.0))  # type: ignore[arg-type]


def test_edges_put_the_content_at_the_margin() -> None:
    plot = Box(100.0, 900.0, 100.0, 400.0)
    label = text(60.0, 80.0, 150.0, 350.0)  # 40 px left of the plot
    step = solve(content(axes(plot, label), margins=Sides(0.01, 0.0, 0.0, 0.0)))
    assert step is not None
    e = step.edges
    assert (e.left, e.right, e.bottom, e.top) == pytest.approx(
        (0.05, 1.0, 0.0, 1.0)
    )
    assert step.delta == math.inf


def test_delta_is_the_largest_edge_move_in_pixels() -> None:
    plot = Box(0.0, 1000.0, 0.0, 500.0)
    last = Edges(0.0, 1.0, 0.0, 0.99)
    step = solve(content(axes(plot), last=last))
    assert step is not None and step.delta == pytest.approx(5.0)
    assert not step.converged


def test_edges_stay_a_valid_rectangle() -> None:
    huge = text(-5000.0, 6000.0, -5000.0, 6000.0)
    step = solve(content(axes(Box(100.0, 900.0, 100.0, 400.0), huge)))
    assert step is not None
    e = step.edges
    assert 0.0 <= e.left < e.right <= 1.0 and 0.0 <= e.bottom < e.top <= 1.0


def test_no_content_no_step() -> None:
    hollow = AxesContent(None, NONE, ())
    assert solve(content(hollow)) is None


@pytest.mark.parametrize(
    ("holds", "box", "edge"),
    [
        (Top(), Box(400, 600, 470, 495), Top()),  # suptitle
        (Top(), Box(0, 20, 100, 120), Left()),  # low: nearest
        (Bottom(), Box(400, 600, 5, 20), Bottom()),  # supxlabel
        (Left(), Box(5, 20, 200, 300), Left()),  # supylabel
        (None, Box(950, 990, 200, 300), Right()),  # a text
    ],
)
def test_figure_artist_reserves_its_role_edge_else_the_nearest(
    holds: Edge | None, box: Box, edge: Edge
) -> None:
    art = FigureArtist(box, holds, False, None, Px(0.0))
    facts = content(artists=[art])
    assert decide.fit(facts).reserves == (edge,)


def test_a_reservation_adds_its_reach_and_gap() -> None:
    title = FigureArtist(Box(400, 600, 450, 500), Top(), False, None, Px(10.0))
    plot = axes(Box(0.0, 1000.0, 0.0, 500.0))
    step = solve(content(plot, artists=[title]))
    assert step is not None and step.edges.top == pytest.approx(1 - 60 / 500)


def test_crushed_below_thirty_percent() -> None:
    before = {ArtistId(1): PlotSize(Px(100.0), Px(100.0))}
    assert not decide.crushed(
        before, {ArtistId(1): PlotSize(Px(31.0), Px(100.0))}
    )
    assert decide.crushed(before, {ArtistId(1): PlotSize(Px(100.0), Px(29.0))})


# -- text helpers -------------------------------------------------------------


def chars(line: Line) -> Px:
    return Px(float(len(line)))


def row(
    texts, gaps, turned=None, authored=False, clearance=2.0, height=10.0
) -> TickRow:
    return TickRow(
        axis=ArtistId(1),
        texts=tuple(Line(t) for t in texts),
        widths=tuple(chars(Line(t)) for t in texts),
        gaps=tuple(Px(g) for g in gaps),
        clearance=Px(clearance),
        line_height=Px(height),
        authored=authored,
        turned=turned,
        width=chars,
    )


def test_tokens_keep_a_bracketed_unit_whole() -> None:
    assert tokens(Line("Energy  use (MWh per year)")) == (
        "Energy",
        "use",
        "(MWh per year)",
    )


def test_balanced_lines_minimise_the_widest() -> None:
    words = tokens(Line("aaaa bb cc dddd"))
    assert balanced_lines(words, Count(2), chars) == (
        ("aaaa bb", "cc dddd"),
        7.0,
    )


@pytest.mark.parametrize(
    ("limit", "expected"),
    [(7.0, "aaaa bb\ncc dddd"), (5.0, "aaaa\nbb cc\ndddd"), (3.0, None)],
)
def test_wrap_to_takes_the_fewest_lines(
    limit: float, expected: str | None
) -> None:
    assert (
        wrap_to(Line("aaaa bb cc dddd"), Px(limit), chars, Count(3)) == expected
    )


def test_wrap_limit_lets_a_long_label_use_short_neighbours_room() -> None:
    r = row(["a", "long label", "b"], [10.0, 10.0])
    assert wrap_limit(Count(1), r) == pytest.approx(15.0)  # 2 * 8 - 1


@pytest.mark.parametrize(
    ("r", "angle"),
    [
        (row(["abcdefgh"] * 3, [6.0, 6.0], height=3.0), Degrees(90.0)),
        (row(["abcdefgh"] * 3, [6.0, 6.0], height=2.0), Degrees(45.0)),
        (row(["x" * 30] * 2, [10.0]), Degrees(90.0)),  # upright overlaps less
        (row(["ab", "cd"], [3.0]), None),  # upright overlaps more than flat
        (row(["ab", "cd"], [40.0]), None),  # not crowded
        (row(["ab", "cd"], [3.0], authored=True), None),
        (row(["abcdefgh"] * 3, [20.0, 20.0], turned=Degrees(45.0)), None),
    ],
)
def test_turn_angle(r: TickRow, angle: Degrees | None) -> None:
    assert turn_angle(r) == angle


def test_gap_fraction_and_deepest_reach() -> None:
    assert gap_fraction(Px(10.0), Px(110.0), Count(2)) == pytest.approx(0.2)
    assert gap_fraction(Px(200.0), Px(100.0), Count(2)) is None
    left = Reach((0, 1), (0, 1), Px(0.0), Px(30.0))
    right = Reach((1, 2), (0, 1), Px(25.0), Px(0.0))
    below = Reach((1, 2), (1, 2), Px(25.0), Px(0.0))  # another row: no pair
    assert deepest_reach([left, right, below], [Px(20.0)]) == 55.0
    assert deepest_reach([left, right], [Px(60.0)]) == 0.0
