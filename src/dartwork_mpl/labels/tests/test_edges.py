"""Each named edge case of the labels: when it fires and what it changes."""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.labels import decide, edges
from dartwork_mpl.labels.bar_geometry import BeyondEnd, Segment
from dartwork_mpl.labels.stacks import BarRun, BarsFacts


def _run(starts, lengths, host="ax"):
    n = len(starts)
    return BarRun(
        tuple(range(n)),
        tuple(starts),
        tuple(lengths),
        tuple(lengths),
        (host, "vertical"),
    )


def _bars(*runs):
    facts = BarsFacts(runs)
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
        (1, 0, BeyondEnd(), 7),
        (1, 1, BeyondEnd(), 9),
    ]
    # Floating bars (a waterfall) and grouped bars stay plain.
    assert _bars(_run((0,), (5,)), _run((9,), (2,))).fired == ()
