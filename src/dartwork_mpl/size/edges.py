"""The default canvas's named special cases, applied after ``decide.canvas``.

It came from a chart that came out wrong without it; the ``why`` says
which.
"""

from __future__ import annotations

from itertools import pairwise
from typing import assert_never

from ..edgecase import EdgeCase
from .decide import REPORT_TIERS, SLIDE_TIERS, scaled
from .model import Canvas, CanvasFacts, CanvasKind, Family

# Room neighbouring flat names need, in ems of the tick font: the layout's
# own target, which wraps or turns names that come closer.
CLEARANCE_EM = 0.5
# The canvas a plot does not get (y tick labels, y name, pads), in ems of the
# tick font, and the share of the plot width over names one position gets.
# Measured on the shipped templates and the category stress corpus: the
# estimate agrees with the drawn charts in all 240 (median error 0.01 em).
OVERHEAD_EM = 4.5
SPACING_SHARE = 0.96


def has_category_names(facts: CanvasFacts, plan: Canvas) -> bool:
    """Measured category names under a single default or grouped panel."""
    request = facts.request
    return (
        facts.names is not None
        and len(facts.names.widths_pt) >= 2
        and request.kind in (CanvasKind.DEFAULT, CanvasKind.GROUPED)
        and request.grid.single
        and facts.page.family is not Family.PAPER
    )


def widen_for_names(facts: CanvasFacts, plan: Canvas) -> Canvas:
    """The narrowest of the page's own widths, at least the plan's, at which
    neighbouring names stand flat half an em apart; past them, the widest."""
    assert facts.names is not None  # has_category_names
    widths, size = facts.names.widths_pt, facts.names.size_pt
    need = max((a + b) / 2 for a, b in pairwise(widths)) + CLEARANCE_EM * size
    match facts.page.family:
        case Family.SLIDES:
            tiers = SLIDE_TIERS
        case Family.REPORT | Family.PAPER | Family.POSTER:
            tiers = tuple(scaled(tier, facts.page) for tier in REPORT_TIERS)
        case _:
            assert_never(facts.page.family)
    for tier in tiers:
        if tier.cm < plan.width.cm - 1e-9:
            continue
        plot = tier.pt - OVERHEAD_EM * size
        if SPACING_SHARE * plot / len(widths) >= need:
            return Canvas(tier, plan.height)
    return Canvas(max(plan.width, tiers[-1]), plan.height)


EDGES: tuple[EdgeCase[CanvasFacts, Canvas], ...] = (
    EdgeCase(
        name="flat-category-names",
        why=(
            "five country names on a slide stood 0.38 em apart and were "
            "turned 30 degrees, costing the plot a quarter of its height"
        ),
        example="test_edges.py::TestFlatCategoryNames::"
        "test_long_names_take_the_next_tier_that_fits",
        applies=has_category_names,
        adjust=widen_for_names,
    ),
)
