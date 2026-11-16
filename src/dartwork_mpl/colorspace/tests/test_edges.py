"""The contrast lift's named edge case: it fires where it should, and only
there."""

from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl  # noqa: F401  (registers the dc.* names read below)
from dartwork_mpl.colorspace import ContrastFacts, Ratio, Rgb, decide, edges
from dartwork_mpl.edgecase import settle


def fired(facts, plan, edge):
    return settle(facts, plan, (edge,))


def test_hex_rounding_shortfall():
    # dc.amber5's bisected lightness on white rounds to #ab6700, a hair
    # under 4.5:1; one 8-bit step further (#a96600) passes.
    white, target = Rgb(1.0, 1.0, 1.0), Ratio(4.5)
    amber = ContrastFacts(Rgb.of(mcolors.to_rgb("dc.amber5")), white, target)
    lift = decide.lift(amber)
    assert lift is not None and lift.rgb().hex() == "#ab6700"
    settled = fired(amber, lift, edges.LIFT_EDGES[0])
    assert settled.fired == ("hex-rounding-shortfall",)
    assert settled.plan is not None and settled.plan.rgb().hex() == "#a96600"
    teal = ContrastFacts(Rgb.of(mcolors.to_rgb("dc.teal4")), white, target)
    assert not fired(teal, decide.lift(teal), edges.LIFT_EDGES[0]).fired
