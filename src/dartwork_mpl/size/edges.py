"""The default canvas's named special cases, applied after ``decide.canvas``.

Each one came from a chart that came out wrong without it; the ``why`` says
which.
"""

from __future__ import annotations

from itertools import pairwise

from ..edgecase import EdgeCase
from .decide import (
    BROAD,
    KINDS,
    MEDIUM,
    NARROW,
    REPORT_TIERS,
    SLIDE,
    SLIDE_BODY,
    SLIDE_HALF,
    SLIDE_TIERS,
    SLIDE_TWO_THIRDS,
    WIDEST,
    half_cm,
    scaled,
)
from .model import ASPECTS, Canvas, CanvasFacts, CanvasKind, Family, Length, cm

# Most grouped bars a width holds with every ``dm.label_bars`` value shown
# (three-digit values at the preset's sizes; measured over 2-8 groups of 2-5
# bars). Past the last, the widest width.
GROUPED_BARS = ((NARROW, 16), (MEDIUM, 24), (BROAD, 32))
GROUPED_BARS_SLIDE = ((SLIDE_HALF, 10), (SLIDE_TWO_THIRDS, 15))
# Room neighbouring flat names need, in ems of the tick font: the layout's
# own target, which wraps or turns names that come closer.
CLEARANCE_EM = 0.5
# The canvas a plot does not get (y tick labels, y name, pads), in ems of the
# tick font, and the share of the plot width over names one position gets.
# Measured on the shipped templates and the category stress corpus: the
# estimate agrees with the drawn charts in all 240 (median error 0.01 em).
OVERHEAD_EM = 4.5
SPACING_SHARE = 0.96


def has_value_labelled_bars(facts: CanvasFacts, plan: Canvas) -> bool:
    """A single grouped-bar panel with both counts known, off a journal."""
    request = facts.request
    return (
        request.kind is CanvasKind.GROUPED
        and request.grid.single
        and facts.page.family is not Family.PAPER
        and request.n_points is not None
        and request.n_series is not None
    )


def widen_for_bars(facts: CanvasFacts, plan: Canvas) -> Canvas:
    """The narrowest width that holds every bar's value label, if wider."""
    request, page = facts.request, facts.page
    bars = (request.n_points or 0) * max(request.n_series or 0, 1)
    slides = page.family is Family.SLIDES
    table = GROUPED_BARS_SLIDE if slides else GROUPED_BARS
    widest = SLIDE_BODY.width if slides else WIDEST
    need = next((width for width, most in table if bars <= most), widest)
    if not slides:
        need = scaled(need, page)
    return Canvas(max(plan.width, need), plan.height)


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
    if facts.page.family is Family.SLIDES:
        tiers = SLIDE_TIERS
    else:
        tiers = tuple(scaled(tier, facts.page) for tier in REPORT_TIERS)
    for tier in tiers:
        if tier.cm < plan.width.cm - 1e-9:
            continue
        plot = tier.pt - OVERHEAD_EM * size
        if SPACING_SHARE * plot / len(widths) >= need:
            return Canvas(tier, plan.height)
    return Canvas(max(plan.width, tiers[-1]), plan.height)


def is_one_column_stack(facts: CanvasFacts, plan: Canvas) -> bool:
    """Two or more panels stacked in one column, off a slide."""
    request = facts.request
    return (
        not request.grid.single
        and request.grid.ncols == 1
        and facts.page.family is not Family.SLIDES
        and not KINDS[request.kind].absolute
    )


def cap_stacked_rows(facts: CanvasFacts, plan: Canvas) -> Canvas:
    """Each stacked panel as tall as a row of a two-column 4:3 grid."""
    row = plan.width.cm / 2 * ASPECTS["standard"].ratio
    cap = half_cm(cm(row * facts.request.grid.nrows))
    height = plan.height
    if isinstance(height, Length) and cap < height:
        return Canvas(plan.width, cap)
    return plan


def is_slide_grid_of_rows(facts: CanvasFacts, plan: Canvas) -> bool:
    """Two or more panel rows on a slide."""
    request = facts.request
    return (
        facts.page.family is Family.SLIDES
        and request.grid.nrows >= 2
        and not KINDS[request.kind].absolute
    )


def take_the_whole_slide(facts: CanvasFacts, plan: Canvas) -> Canvas:
    """The whole 16:9 slide, with no slide title above it."""
    return SLIDE


EDGES: tuple[EdgeCase[CanvasFacts, Canvas], ...] = (
    EdgeCase(
        name="grouped-value-labels",
        why=(
            "each grouped bar carries a value label: 4 groups of 3 bars on a "
            "11.4 cm slide chart hid 4 of the 12 labels"
        ),
        applies=has_value_labelled_bars,
        adjust=widen_for_bars,
    ),
    EdgeCase(
        name="flat-category-names",
        why=(
            "named categories need room to stand flat: five country names on "
            "a slide stood 0.38 em apart and were turned 30 degrees, costing "
            "the plot a quarter of its height"
        ),
        applies=has_category_names,
        adjust=widen_for_names,
    ),
    EdgeCase(
        name="stacked-column",
        why=(
            "two full-width panels stacked in one column came out 17 x 24 cm, "
            "a whole A4 text block; a row of a two-column grid is enough"
        ),
        applies=is_one_column_stack,
        adjust=cap_stacked_rows,
    ),
    EdgeCase(
        name="slide-grid-rows",
        why=(
            "every panel row carries its own title, ticks and axis name, about "
            "2.6 cm on a slide: two rows in the 10.5 cm body left 2.4 cm plots"
        ),
        applies=is_slide_grid_of_rows,
        adjust=take_the_whole_slide,
    ),
)
