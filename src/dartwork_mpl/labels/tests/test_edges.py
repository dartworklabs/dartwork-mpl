"""Each named edge case of the labels: when it fires and what it changes."""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.labels import decide, edges
from dartwork_mpl.labels.model import (
    BarOptions,
    Edge,
    Ink,
    InkFacts,
    OwnInk,
    Segment,
    SeriesInk,
    StackTotal,
    TotalsOnly,
    TotalsToo,
    ValueFacts,
)
from dartwork_mpl.labels.stacks import BarRun, BarsFacts


def _text(value: float, decimals: int, *, plus=False):
    facts = ValueFacts(value, decimals, False, plus)
    return settle(facts, decide.bar_text(facts), edges.TEXT_EDGES)


def test_signed_steps():
    assert _text(30, 0, plus=True).plan.lead == "+"
    assert _text(30, 0, plus=True).fired == ("signed-steps",)
    assert _text(-15, 0, plus=True).fired == ()
    assert _text(0.0, 0, plus=True).fired == ()  # zero takes no sign


def _run(starts, lengths, host="ax"):
    n = len(starts)
    return BarRun(
        tuple(range(n)),
        tuple(starts),
        tuple(lengths),
        tuple(lengths),
        (host, "vertical"),
    )


TOTALS_TOO = TotalsToo()


def _bars(*runs, total=TOTALS_TOO):
    facts = BarsFacts(runs, total)
    return settle(facts, decide.plain_labels(facts), edges.BARS_EDGES)


def test_stacked_segments_totals():
    settled = _bars(_run((0, 0), (5, 6)), _run((5, 6), (2, 3)))
    assert settled.fired == ("stacked-segments-totals",)
    kinds = [(p.run, p.index, p.kind, p.value) for p in settled.plan.labels]
    assert kinds == [
        (0, 0, Segment(), 5),
        (0, 1, Segment(), 6),
        (1, 0, Segment(), 2),
        (1, 1, Segment(), 3),
        (1, 0, StackTotal(), 7),
        (1, 1, StackTotal(), 9),
    ]
    only = _bars(_run((0, 0), (5, 6)), _run((5, 6), (2, 3)), total=TotalsOnly())
    assert {p.kind for p in only.plan.labels} == {StackTotal()}
    # A highlight split into two containers: no stack, no '0' on the padding.
    split = _bars(_run((0, 0, 0), (5, 0, 7)), _run((0, 0, 0), (0, 6, 0)))
    assert [(p.run, p.index) for p in split.plan.labels] == [
        (0, 0),
        (0, 2),
        (1, 1),
    ]
    # Floating bars (a waterfall) and grouped bars stay plain.
    assert _bars(_run((0,), (5,)), _run((9,), (2,))).fired == ()


RED = (1.0, 0.0, 0.0, 1.0)


EDGE = Edge()


def _ink(on_bar: bool, kind=EDGE, **options):
    facts = InkFacts(
        BarOptions(**options), kind, on_bar, Ink("white"), Ink("#123456")
    )
    return settle(facts, decide.ink(facts), edges.INK_EDGES)


def test_inside_readable_ink():
    assert _ink(True).plan == Ink("white")
    assert _ink(True).fired == ("inside-readable-ink",)
    # the caller's colour wins
    assert _ink(True, color=OwnInk(RED)).plan == Ink(RED)
    assert _ink(False).plan == Ink()


def test_series_colour():
    assert _ink(False, color=SeriesInk()).plan == Ink("#123456")
    assert _ink(False, color=SeriesInk()).fired == ("series-colour",)
    assert _ink(False, kind=StackTotal(), color=SeriesInk()).plan == Ink()
    assert _ink(True, color=SeriesInk()).plan == Ink("white")
