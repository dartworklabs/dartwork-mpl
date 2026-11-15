"""Pure label decisions for the ordinary figure: facts in, plan out.

A bar label prints its value like the ticks; a call whose labels are wider
than the bar pitch less 1.5 pt is crowded (vertical bars turn their labels),
and labels that still meet are hidden a position at a time from the last; an
autoscaled value axis grows just enough for the labels beyond the bar ends.
A point label takes the first free side, a panel letter sits on its title's
baseline, line-end names spread one line apart. Special cases are in
``edges.py``.
"""

from __future__ import annotations

import math

import numpy as np

from .bar_geometry import CrowdFacts, Headroom, HeadroomFacts, Shown, Span
from .bar_options import (
    Edge,
    Higher,
    Ink,
    InkFacts,
    LabelText,
    Lower,
    OwnInk,
    SeriesInk,
    TextInk,
    ValueFacts,
)
from .panels import Column, Letters, PanelsFacts
from .places import Choice, Tries
from .stacks import BarsFacts, BarsPlan, Planned

# Above the top decoration of a panel without a title, and between a letter
# and a y name or tick label rising above the panel, in points.
TOP_GAP_PT, CLEARANCE_PT = 4.0, 2.0


# ------------------------------------------------------------ bar text
def bar_text(facts: ValueFacts) -> LabelText:
    """The value at the call's decimals, as the ticks print it."""
    return LabelText(facts.scaled, facts.decimals, fixed=facts.fixed)


# ------------------------------------------------------------ which bars
def plain_labels(facts: BarsFacts) -> BarsPlan:
    """One label per drawn bar (finite value), containers in order."""
    return BarsPlan(
        tuple(
            Planned(run, index, Edge(), value)
            for run, bars in enumerate(facts.runs)
            for index, value in enumerate(bars.values)
            if math.isfinite(value)
        )
    )


# ------------------------------------------------------------ crowding
def crowded(facts: CrowdFacts) -> bool:
    """Whether a label is wider than the distance from its bar to the
    nearest other bar of the plot area, less the gap."""
    return any(
        p.widest > facts.pitch(p.centre) - facts.gap.px
        for p in facts.positions()
    )


def keep_apart(facts: CrowdFacts) -> Shown:
    """Keep a position while it stays the gap clear of the last one kept,
    from the last position on screen (right end, ``barh`` top row)."""
    shown = [False] * len(facts.spots)
    last = math.inf
    for p in reversed(facts.positions()):
        if p.span.high + facts.gap.px <= last:
            last = p.span.low
            for i in p.members:
                shown[i] = True
    return Shown(tuple(shown))


def headroom(facts: HeadroomFacts) -> Headroom:
    """The least widening of the view that gives every label its room.

    Writing ``S`` for the new span, an anchor ``a`` needing ``n`` of the
    Axes' ``L`` px forces ``high' >= a + n S / L``: ``S`` is the least fixed
    point of a convex piecewise-linear map, found exactly by Newton steps
    over its pieces. ``None`` when the view already holds every label, or
    no widening can (labels longer than the Axes).
    """
    low, high = facts.view.low, facts.view.high
    length = high - low
    if not length > 0:
        return Headroom(None)
    tops: list[tuple[float, float]] = []
    downs: list[tuple[float, float]] = []
    for r in facts.rooms:
        if not r.need < length:
            continue
        match r.toward:
            case Higher():
                tops.append((r.anchor, r.need / length))
            case Lower():
                downs.append((r.anchor, r.need / length))
    top = np.array([(high, 0.0), *tops]).reshape(-1, 2)
    bottom = np.array([(low, 0.0), *downs]).reshape(-1, 2)
    span = length
    for _ in range(len(top) + len(bottom)):
        i = int(np.argmax(top[:, 0] + top[:, 1] * span))
        j = int(np.argmin(bottom[:, 0] - bottom[:, 1] * span))
        rest = 1.0 - top[i, 1] - bottom[j, 1]
        if rest <= 0:
            return Headroom(None)
        nxt = (top[i, 0] - bottom[j, 0]) / rest
        if nxt <= span:
            break
        span = nxt
    new_high = float(np.max(top[:, 0] + top[:, 1] * span))
    new_low = float(np.min(bottom[:, 0] - bottom[:, 1] * span))
    if new_high <= high and new_low >= low:
        return Headroom(None)
    return Headroom(Span(new_low, new_high))


# ------------------------------------------------------------ ink
def ink(facts: InkFacts) -> Ink:
    """The call's colour when it gave one, else the preset text colour."""
    match facts.options.color:
        case OwnInk(rgba=rgba):
            return Ink(rgba)
        case TextInk() | SeriesInk():
            return Ink()


# ------------------------------------------------------------ point labels
def value_side(tries: Tries) -> Choice:
    """``annotate_value``'s side among above, below, right, left (in that
    order): the first free one; else the least covered one inside the axes;
    else the least outside and covered. A label that leaves the axes above
    its point moves sideways, never flips below."""
    candidates = [0, 2, 3] if tries.tries[0].outside > 0 else [0, 1, 2, 3]
    return Choice(tries.pick(candidates, inside_first=True))


def first_free(tries: Tries) -> Choice:
    """The first free candidate, else the least outside and covered."""
    return Choice(tries.pick(range(len(tries.tries)), inside_first=False))


# ------------------------------------------------------------ panel letters
def letter_lefts(facts: PanelsFacts) -> Letters:
    """Each letter's left edge before columns align.

    On the outer edge of the panel's y-axis name, a grid column taking its
    leftmost; a panel with no name in its column keeps the spine distance
    of the named panels (the largest in its row, else in the call); with no
    name anywhere, where a name would be.
    """
    panels = facts.panels
    lefts: list[float | None] = [p.ylabel_x0 for p in panels]
    for members in facts.groups(1).values():
        known = [v for i in members if (v := lefts[i]) is not None]
        if known:
            for i in members:
                lefts[i] = min(known)
    reach = {
        i: panels[i].corner[0] - v for i, v in enumerate(lefts) if v is not None
    }
    out: list[float] = []
    for i, left in enumerate(lefts):
        panel = panels[i]
        if left is not None:
            out.append(left)
            continue
        row = [reach[j] for j in facts.mates(i, 0) if j in reach]
        if row or reach:
            out.append(panel.corner[0] - max(row or list(reach.values())))
        else:
            out.append(panel.guess_x0)
    return Letters(tuple(out), ())


def align_letters(facts: PanelsFacts, letters: Letters) -> Letters:
    """A column shares its leftmost edge; a letter sits on its title's
    baseline, or (untitled) 4 pt above the top decoration raised to its
    row's highest baseline, and 2 pt clear of a y name or tick label rising
    above the panel under it."""
    lefts = list(letters.lefts)
    for members in facts.groups(1).values():
        value = min(lefts[i] for i in members)
        for i in members:
            lefts[i] = value
    k = facts.px_per_pt
    baselines: list[float] = []
    for panel, left in zip(facts.panels, lefts, strict=True):
        if panel.titles:
            base = max(t.baseline for t in panel.titles)
        else:
            base = panel.top + TOP_GAP_PT * k
        for x0, x1, y1 in panel.decos:
            if x0 < left + panel.width and x1 > left:
                base = max(base, y1 + CLEARANCE_PT * k + panel.descent)
        baselines.append(base)
    for members in facts.groups(0).values():
        value = max(baselines[i] for i in members)
        for i in members:
            if not facts.panels[i].titles:
                baselines[i] = value
    return Letters(tuple(lefts), tuple(baselines))


# ------------------------------------------------------------ line ends
def spread(column: Column) -> Column:
    """Sorted centres moved apart to ``height`` spacing, as little as
    possible: labels that would overlap merge into a group centred on their
    mean, and groups that then touch merge again, keeping the order."""
    height = column.height
    groups: list[tuple[float, int, float]] = []  # first centre, count, mean
    for c in column.centres:
        groups.append((c, 1, c))
        while len(groups) > 1:
            first, n, mean = groups[-1]
            p_first, p_n, p_mean = groups[-2]
            if p_first + p_n * height <= first + 1e-9:
                break
            total = p_n + n
            merged = (p_mean * p_n + mean * n) / total
            groups[-2:] = [(merged - (total - 1) * height / 2, total, merged)]
    out = [first + k * height for first, n, _ in groups for k in range(n)]
    return Column(tuple(out), height)
