"""The legend's named special cases, applied after the ``decide`` functions.

Each decision has its own facts type; an edge case applies only to its own.
"""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from . import decide
from .model import (
    SIDE_WRAP_SHARE,
    WIDE_SHARE,
    Anchor,
    AnchorFacts,
    Box,
    EntryFacts,
    EntryPlan,
    Facts,
    FigureFacts,
    FigurePlan,
    Hits,
    LegendFacts,
    Outside,
    Plan,
    Span,
    TitleFacts,
    TitlePad,
    Width,
)


def is_polar(facts: Facts, plan: Plan) -> bool:
    """A ``best`` legend on an Axes that draws its frame inside its box."""
    return (
        isinstance(facts, LegendFacts)
        and facts.frame is not None
        and facts.request.side is None
    )


def count_the_frame(facts: Facts, plan: Plan) -> Plan:
    """Decide again with the frame and its tick labels counted as ink."""
    assert isinstance(facts, LegendFacts) and facts.frame is not None
    data, frame = facts.meets, facts.frame

    def both(box: Box) -> Hits:
        return Hits(data(box).n + frame(box).n)

    return decide.place(replace(facts, meets=both, frame=None))


def has_overlong_names(facts: Facts, plan: Plan) -> bool:
    """An outside legend that does not fit, or a named side one too wide."""
    if not (isinstance(facts, LegendFacts) and isinstance(plan, Outside)):
        return False
    named_side = facts.request.side is not None and not plan.side.across
    wide = named_side and plan.size.width > WIDE_SHARE * facts.axes.width
    return not plan.fits or wide


def break_names(facts: Facts, plan: Plan) -> Plan:
    """Break names at spaces to the side's length (right, left: a canvas share)."""
    assert isinstance(facts, LegendFacts) and isinstance(plan, Outside)
    if plan.side.across:
        room = facts.span_of(plan.side).length
    else:
        room = SIDE_WRAP_SHARE * facts.canvas_width
    width = room - facts.overhead
    if width <= 0:
        return plan
    wrapped = facts.wrap(facts.entries, Width(width))
    if wrapped == plan.entries:
        return plan
    return decide.outside(facts, plan.side, wrapped)


def has_twins(facts: Facts, plan: Plan) -> bool:
    """The Axes has twins drawn in its box."""
    return isinstance(facts, EntryFacts) and len(facts.owners) > 1


def merge_twins(facts: Facts, plan: Plan) -> Plan:
    """Every twin's entries once, on the twin drawn last; theirs removed."""
    assert isinstance(facts, EntryFacts)
    owners = facts.owners
    host = max(range(len(owners)), key=lambda i: owners[i].rank)
    seen: set[str] = set()
    picks: list[tuple[int, int]] = []
    for i in sorted(range(len(owners)), key=lambda i: owners[i].rank[1]):
        for j, label in enumerate(owners[i].entries.labels):
            if label not in seen:
                seen.add(label)
                picks.append((i, j))
    remove = tuple(
        i for i, o in enumerate(owners) if i != host and o.legend is not None
    )
    return EntryPlan(host=host, picks=tuple(picks), remove=remove)


def _left_alone(facts: EntryFacts, plan: EntryPlan) -> EntryPlan | None:
    """The plan that leaves a caller's legend as it is, if there is one."""
    shown = tuple(facts.owners[i].entries.labels[j] for i, j in plan.picks)
    for i, owner in enumerate(facts.owners):
        if owner.legend is None or owner.ours:
            continue
        if owner.legend.labels not in (shown, owner.entries.labels):
            return replace(plan, remove=(), leave=i)
    return None


def has_explicit_legend(facts: Facts, plan: Plan) -> bool:
    """A legend that is not what the Axes' labelled artists would draw."""
    return (
        isinstance(facts, EntryFacts)
        and isinstance(plan, EntryPlan)
        and _left_alone(facts, plan) is not None
    )


def keep_explicit_legend(facts: Facts, plan: Plan) -> Plan:
    """Leave the caller's legend as it is; remove nothing."""
    assert isinstance(facts, EntryFacts) and isinstance(plan, EntryPlan)
    return _left_alone(facts, plan) or plan


def _centred(facts: AnchorFacts) -> Span:
    """Where the legend lies along its side, centred on the Axes."""
    low, high = facts.axes.along(facts.side)
    half = facts.legend.along(facts.side) / 2
    return Span((low + high) / 2 - half, (low + high) / 2 + half)


def leaves_its_span(facts: Facts, plan: Plan) -> bool:
    """A legend longer than its Axes, or one that would leave its span."""
    if not isinstance(facts, AnchorFacts):
        return False
    own, (low, high) = _centred(facts), facts.axes.along(facts.side)
    span = facts.span
    return own.length > high - low or own.low < span.low or own.high > span.high


def stay_on_canvas(facts: Facts, plan: Plan) -> Plan:
    """Move the legend back into its span; clear the decorations it now spans."""
    assert isinstance(facts, AnchorFacts) and isinstance(plan, Anchor)
    own, span = _centred(facts), facts.span
    start, end = own.low, own.high
    shift = 0.0
    if end - start > span.length:
        shift = (span.low + span.high) / 2 - (start + end) / 2
    elif start < span.low:
        shift = span.low - start
    elif end > span.high:
        shift = span.high - end
    reach = [
        facts.axes.beyond(facts.side, box)
        for box in facts.decorations
        if min(box.along(facts.side)[1], end + shift)
        - max(box.along(facts.side)[0], start + shift)
        > 0.5
    ]
    return Anchor(clearance=max([plan.clearance, *reach]), shift=shift)


def has_legend_above(facts: Facts, plan: Plan) -> bool:
    """Axes titles with a legend above the Axes."""
    return isinstance(facts, TitleFacts) and bool(facts.legends_above)


def lift_titles(facts: Facts, plan: Plan) -> Plan:
    """Raise the titles so their baseline sits the title gap above the legend."""
    assert isinstance(facts, TitleFacts)
    pad = max(title.pad for title in facts.titles)
    needed = 0.0
    for title in facts.titles:
        for legend in facts.legends_above:
            beside = (
                title.box.x1 <= legend.x0 - facts.gap
                or title.box.x0 >= legend.x1 + facts.gap
            )
            if beside or title.box.y1 <= legend.y0:
                continue
            needed = max(needed, legend.y1 + facts.gap - title.base_y)
    return TitlePad(needed) if needed > pad + 0.5 else plan


def has_figure_label(facts: Facts, plan: Plan) -> bool:
    """A figure legend on a side the figure has its own label on."""
    return (
        isinstance(facts, FigureFacts)
        and isinstance(plan, FigurePlan)
        and plan.side in facts.label_edges
    )


def past_figure_label(facts: Facts, plan: Plan) -> Plan:
    """Anchor the legend at the edge of the figure's label on its side."""
    assert isinstance(facts, FigureFacts) and isinstance(plan, FigurePlan)
    edge = facts.label_edges[plan.side]
    x, y = plan.anchor
    return replace(plan, anchor=(x, edge) if plan.side.across else (edge, y))


EDGES: tuple[EdgeCase[Facts, Plan], ...] = (
    EdgeCase(
        name="polar-frame-ink",
        why=(
            "a polar Axes draws its circle and angle labels inside its box: "
            "the free upper-right corner of the box sat on the 45 degree label"
        ),
        applies=is_polar,
        adjust=count_the_frame,
    ),
    EdgeCase(
        name="overlong-entry-names",
        why=(
            "an entry name wider than the Axes ran a below legend off the "
            "canvas; broken at spaces, it fits in two lines"
        ),
        applies=has_overlong_names,
        adjust=break_names,
    ),
    EdgeCase(
        name="twin-merge",
        why=(
            "a twinx pair drew two legends, the left one under the right "
            "Axes' line; one legend on the twin drawn last covers nothing"
        ),
        applies=has_twins,
        adjust=merge_twins,
    ),
    EdgeCase(
        name="explicit-legend-kept",
        why=(
            "a legend built from tuple handles or explicit labels cannot be "
            "rebuilt from the artists without losing what the caller drew"
        ),
        applies=has_explicit_legend,
        adjust=keep_explicit_legend,
    ),
    EdgeCase(
        name="outside-on-canvas",
        why=(
            "a five-entry legend above a narrow left panel, centred on it, "
            "started 1 cm left of the canvas"
        ),
        applies=leaves_its_span,
        adjust=stay_on_canvas,
    ),
    EdgeCase(
        name="title-over-above-legend",
        why=(
            "a legend above the Axes sits where the title is drawn; the title "
            "goes above it, the preset's title gap apart"
        ),
        applies=has_legend_above,
        adjust=lift_titles,
    ),
    EdgeCase(
        name="figure-legend-past-suplabels",
        why=(
            "a figure legend above the panels was drawn over the suptitle; "
            "it goes under it, and over a supxlabel below"
        ),
        applies=has_figure_label,
        adjust=past_figure_label,
    ),
)
