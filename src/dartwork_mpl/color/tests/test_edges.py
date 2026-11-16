"""One test per named colour edge case: it fires where it should, and only
there."""

from __future__ import annotations

from dartwork_mpl.color import decide, edges
from dartwork_mpl.color.catalog import CATALOG
from dartwork_mpl.color.family import Count
from dartwork_mpl.color.model import DivergingSource, Form, SemanticFacts
from dartwork_mpl.edgecase import settle
from dartwork_mpl.vocab import DefaultLocale, KoreanLocale


def fired(facts, plan, edge):
    return settle(facts, plan, (edge,))


def test_sequential_full_ladder():
    family = CATALOG.families["teal"]
    nine = Form(family, Count(9))
    settled = fired(nine, decide.discrete(nine), edges.FULL_LADDER)
    assert settled.fired == ("sequential-full-ladder",)
    assert settled.plan == family.stops[:9]
    eight = Form(family, Count(8))
    assert not fired(eight, decide.discrete(eight), edges.FULL_LADDER).fired


def test_curated_diverging_row():
    blue, red = CATALOG.ladder("blue"), CATALOG.ladder("red")
    hand = CATALOG.families["blue_red"].stops
    curated = DivergingSource(blue, red, hand)
    settled = fired(curated, decide.diverging_row(curated), edges.CURATED_ROW)
    assert settled.fired == ("curated-diverging-row",)
    assert settled.plan == hand
    derived = DivergingSource(blue, red, None)
    plan = decide.diverging_row(derived)
    assert plan == (
        blue[7],
        blue[5],
        blue[3],
        blue[1],
        red[1],
        red[3],
        red[5],
        red[7],
    )
    assert not fired(derived, plan, edges.CURATED_ROW).fired


def test_kr_semantic_tokens():
    kr = SemanticFacts(KoreanLocale(), CATALOG)
    settled = fired(kr, decide.semantic(kr), edges.KR_TOKENS)
    assert settled.fired == ("kr-semantic-tokens",)
    assert settled.plan.pos == CATALOG.ladder("red")[5]
    assert settled.plan.neg == CATALOG.ladder("blue")[6]
    default = SemanticFacts(DefaultLocale(), CATALOG)
    plan = decide.semantic(default)
    assert plan.pos == CATALOG.ladder("green")[6]
    assert not fired(default, plan, edges.KR_TOKENS).fired
