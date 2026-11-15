"""The ordinary legend decisions, on hand-made facts (no figure)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dartwork_mpl.legend import decide
from dartwork_mpl.legend.model import (
    AnchorFacts,
    Box,
    Columns,
    Entries,
    EntryFacts,
    FigureFacts,
    Hits,
    Inside,
    LegendFacts,
    Outside,
    Owner,
    Request,
    Size,
    Span,
)
from dartwork_mpl.legend.sides import (
    FALLBACK_SIDES,
    Above,
    Below,
    LowerLeft,
    Right,
    UpperCenter,
    UpperLeft,
    UpperRight,
)

AXES = Box(0, 0, 400, 300)


def size_of(entries: Entries, columns: Columns) -> Size:
    """Each entry 60 x 15 px; a legend is its columns wide, its rows tall."""
    rows = -(-entries.count // columns.n)
    return Size(60.0 * columns.n, 15.0 * rows)


BEST = Request(None)


def facts(n=3, ink=(), request=BEST, span=400.0, **kw) -> LegendFacts:
    def meets(box: Box) -> Hits:
        return Hits(sum(b.overlaps(box) for b in ink))

    base = LegendFacts(
        request=request,
        entries=Entries(tuple(f"S{i}" for i in range(n))),
        axes=AXES,
        parent=AXES,
        pad=5.0,
        free_sides=FALLBACK_SIDES,
        size_of=size_of,
        meets=meets,
        span_of=lambda side: Span(0.0, span),
    )
    return replace(base, **kw)


CORNER = {
    "upper right": Box(300, 250, 400, 300),
    "upper left": Box(0, 250, 100, 300),
    "lower left": Box(0, 0, 100, 50),
    "lower right": Box(300, 0, 400, 50),
}


@pytest.mark.parametrize(
    ("covered", "expected"),
    [
        ((), UpperRight()),
        (("upper right",), UpperLeft()),
        (("upper right", "upper left"), LowerLeft()),
        (tuple(CORNER), UpperCenter()),
    ],
)
def test_the_first_free_inside_spot_in_ladder_order(covered, expected):
    plan = decide.place(facts(ink=[CORNER[c] for c in covered]))
    assert plan == Inside(expected, Columns(1))


def test_a_tall_one_column_legend_goes_after_two_columns():
    plan = decide.place(facts(n=14))  # 210 px tall in one column: 70 %
    assert plan == Inside(UpperRight(), Columns(2))


def test_an_asked_column_count_is_the_only_one_tried():
    plan = decide.place(facts(request=Request(None, Columns(3))))
    assert plan == Inside(UpperRight(), Columns(3))


EVERYWHERE = (AXES,)


@pytest.mark.parametrize(
    ("free", "side"),
    [
        (FALLBACK_SIDES, Above()),
        ((Below(), Right()), Below()),
        ((Right(),), Right()),
    ],
)
def test_no_free_spot_goes_outside_the_first_free_side(free, side):
    plan = decide.place(facts(ink=EVERYWHERE, free_sides=free))
    assert isinstance(plan, Outside) and plan.side == side and plan.fits


@pytest.mark.parametrize(
    "kw", [{"free_sides": ()}, {"request": Request(None, anchored=True)}]
)
def test_no_side_allowed_keeps_the_least_covering_spot(kw):
    ink = (*EVERYWHERE, CORNER["upper left"])
    plan = decide.place(facts(ink=ink, **kw))
    assert plan == Inside(UpperRight(), Columns(1), free=False)


@pytest.mark.parametrize(
    ("span", "columns", "fits"),
    [(400, 3, True), (130, 2, True), (50, 1, False)],
)
def test_above_takes_the_fewest_rows_that_fit_across(span, columns, fits):
    plan = decide.place(facts(request=Request(Above()), span=span))
    assert isinstance(plan, Outside)
    assert (plan.columns, plan.fits) == (Columns(columns), fits)


def test_right_takes_the_fewest_columns_that_fit_along():
    plan = decide.place(facts(n=6, request=Request(Right()), span=50))
    assert isinstance(plan, Outside) and plan.columns == Columns(2)


def test_placed_again_a_legend_only_moves_inwards():
    inside = Inside(LowerLeft(), Columns(1), free=False)
    covered = facts(ink=EVERYWHERE, current=inside)
    assert decide.place(covered) == inside  # never sent out
    above = decide.place(facts(ink=EVERYWHERE))
    assert isinstance(above, Outside)
    stays = decide.place(facts(ink=EVERYWHERE, current=above))
    assert isinstance(stays, Outside) and stays.side == above.side
    assert decide.place(facts(current=above)) == Inside(
        UpperRight(), Columns(1)
    )


def test_the_anchor_clears_the_labels_beyond_its_side_only():
    labels = (Box(0, -20, 400, -2), Box(-40, 0, -5, 300))
    below = AnchorFacts(Below(), AXES, labels)
    above = replace(below, side=Above())
    assert decide.anchor(below).clearance == 20
    assert decide.anchor(above).clearance == 0


def test_a_figure_legend_goes_above_unless_it_does_not_fit():
    base = FigureFacts(
        None, None, Entries(("a", "b")), Box(0, 0, 500, 400), 5.0, size_of
    )
    assert decide.figure_place(base).side == Above()
    narrow = replace(base, figure=Box(0, 0, 40, 400))
    assert decide.figure_place(narrow).side == Right()


def test_entries_are_the_axes_own_each_name_once():
    own = Owner(Entries(("a", "b", "a")), (0.0, 0))
    plan = decide.entries(EntryFacts((own,)))
    assert plan.picks == ((0, 0), (0, 1)) and plan.host == 0
