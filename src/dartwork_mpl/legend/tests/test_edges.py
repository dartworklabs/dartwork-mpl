"""Each named legend edge case: when it fires and what it changes."""

from __future__ import annotations

from dataclasses import replace

from dartwork_mpl.edgecase import settle
from dartwork_mpl.legend import decide
from dartwork_mpl.legend.boxes import Box, Entries
from dartwork_mpl.legend.edges import ENTRY_EDGES, TITLE_EDGES
from dartwork_mpl.legend.plans import (
    EntryFacts,
    EntryPlan,
    Owner,
    TitleBox,
    TitleFacts,
    TitlePad,
)


def _settled(f, plan):
    edges = ENTRY_EDGES if isinstance(f, EntryFacts) else TITLE_EDGES
    return settle(f, plan, edges)


def _twins(**second) -> EntryFacts:
    bars = Owner(Entries(("Rain",)), (0.0, 0), legend=Entries(("Rain",)))
    line = Owner(Entries(("Temp", "Rain")), (0.0, 1), **second)
    return EntryFacts((bars, line))


def test_twin_merge_puts_every_entry_on_the_twin_drawn_last():
    f = _twins()
    result = _settled(f, decide.entries(f))
    assert result.fired == ("twin-merge",)
    assert result.plan == EntryPlan(host=1, picks=((0, 0), (1, 0)), remove=(0,))


def test_title_over_above_legend_lifts_the_titles_over_it():
    title = TitleBox(Box(150, 305, 250, 320), base_y=300.0, pad=5.0)
    f = TitleFacts((title,), (Box(100, 302, 300, 330),), gap=6.0)
    result = _settled(f, decide.title_pad(f))
    assert result.fired == ("title-over-above-legend",)
    assert result.plan == TitlePad(36.0)
    beside = replace(f, legends_above=(Box(260, 302, 400, 330),))
    assert _settled(beside, decide.title_pad(beside)).plan == TitlePad()
