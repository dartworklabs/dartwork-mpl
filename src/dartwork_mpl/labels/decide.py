"""Pure label decisions for the ordinary figure: facts in, plan out.

A bar label prints its value like the ticks; a call whose labels are wider
than the bar pitch less 1.5 pt is crowded (vertical bars turn their labels),
and labels that still meet are hidden a position at a time from the last; an
autoscaled value axis grows just enough for the labels beyond the bar ends.
A point label takes the first free side, panel letters run into their
titles (or sit inside their plots when a run does not fit), line-end names spread one line apart. A text that
does not read on what is behind it takes the one colour that does, or an
outline where none does. Special cases are in ``edges.py``.
"""

from __future__ import annotations

import math

import numpy as np

from ..colorspace import LEGIBLE, Rgb, contrast
from ..vocab import Span
from .bar_geometry import (
    BeyondEnd,
    CrowdFacts,
    Headroom,
    HeadroomFacts,
    Higher,
    Lower,
    Shown,
)
from .model import (
    INSET_EM,
    TOUCH_PX,
    Choice,
    Column,
    DrawnOver,
    Halo,
    InkFacts,
    Inside,
    InTheWay,
    Leave,
    Letters,
    Mend,
    OwnAlpha,
    PanelsFacts,
    Placement,
    Recolour,
    Run,
    Tries,
)
from .stacks import BarsFacts, BarsPlan, Planned

# Above the top decoration of a panel without a title, and between a letter
# and a y name or tick label rising above the panel, in points.
TOP_GAP_PT, CLEARANCE_PT = 4.0, 2.0


#: Ink at this contrast reads without effort (WCAG's floor for body text):
#: ``dm.legible`` leaves such a text alone and aims for it when it mends.
#: A colour reads on everything behind a text when less than this share of
#: the ink is under the floor: antialiased edges and a crossing gridline.
CLEAN = 0.02
#: A colour with this much OKLCH chroma is an accent, not a grey.
ACCENT = 0.05
#: A text with this share of its ink under the floor is lost, not crossing.
MOSTLY = 0.5
#: A text this opaque or more paints its own colour.
OPAQUE = 0.99
#: A halo reaches this far beyond the glyphs (em of the text): far enough
#: to close the gaps between the strokes of a Hangul syllable, so the
#: glyphs stand on one plate. Half of it leaves a second outline between
#: the strokes. And at least this many points, so a small text's outline
#: does not thin to nothing.
HALO_EM, HALO_MIN_PT = 0.14, 0.6


# ------------------------------------------------------------ which bars
def plain_labels(facts: BarsFacts) -> BarsPlan:
    """One label per drawn bar (finite value), containers in order."""
    return BarsPlan(
        tuple(
            Planned(run, index, BeyondEnd(), value)
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


# ------------------------------------------------------------ point labels
def value_side(tries: Tries) -> Choice:
    """``annotate_value``'s side among above, below, right, left (in that
    order): the first free one; else the least covered one inside the axes;
    else the least outside and covered. A label that leaves the axes above
    its point moves sideways, never flips below."""
    t = tries.tries
    candidates = [0, 2, 3] if t[0].outside > 0 else [0, 1, 2, 3]
    first = next((i for i in candidates if t[i].clear), None)
    if first is not None:
        return Choice(first)
    inside = [i for i in candidates if t[i].outside <= 0]
    if inside:
        return Choice(min(inside, key=lambda i: t[i].collision))
    return Choice(min(candidates, key=lambda i: t[i].outside + t[i].collision))


# ------------------------------------------------------------ panel letters
def placement(facts: PanelsFacts) -> Placement:
    """A run in every panel while each run fits inside its plot; else every
    letter inside its plot (the first panel whose run did not fit)."""
    for i, p in enumerate(facts.panels):
        if p.run > p.plot_width + TOUCH_PX:
            return Inside(i)
    return Run()


def place_letters(facts: PanelsFacts, where: Placement) -> Letters:
    """Each letter where ``where`` puts it.

    A run: the letter on its spine, on its title's baseline (untitled: 4 pt
    above the top decoration raised to its row's highest, and 2 pt clear of
    a y name or tick label rising above the panel); the title starts half a
    letter size after it. Inside: the letter's top-left corner 0.4 letter
    sizes in from the plot's, a row on its lowest baseline.
    """
    panels = facts.panels
    match where:
        case Inside():
            inside = [
                p.corner[1] - INSET_EM * p.size - (p.height - p.descent)
                for p in panels
            ]
            for members in facts.groups(0).values():
                value = min(inside[i] for i in members)
                for i in members:
                    inside[i] = value
            return Letters(
                tuple(p.corner[0] + INSET_EM * p.size for p in panels),
                tuple(inside),
                tuple(None for _ in panels),
            )
        case Run():
            pass
    k = facts.px_per_pt
    baselines: list[float] = []
    for p in panels:
        left = p.corner[0]
        if p.titles:
            base = max(t.baseline for t in p.titles)
        else:
            base = p.top + TOP_GAP_PT * k
        for x0, x1, y1 in p.decos:
            if x0 < left + p.width and x1 > left:
                base = max(base, y1 + CLEARANCE_PT * k + p.descent)
        baselines.append(base)
    for members in facts.groups(0).values():
        value = max(baselines[i] for i in members)
        for i in members:
            if not panels[i].titles:
                baselines[i] = value
    return Letters(
        tuple(p.corner[0] for p in panels),
        tuple(baselines),
        tuple(
            p.corner[0] + p.width + p.gap if p.joined else None for p in panels
        ),
    )


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


# ------------------------------------------------------------ legible text
def mend(facts: InkFacts) -> Mend:
    """What makes a text read on what is drawn behind it, the least first.

    A text that reads is left: its colour is the author's. Else, among its
    own colour, the preset's text colour and the paper of its Axes, the
    one that reads on everything behind it with the most contrast is
    taken. Where no one colour reads everywhere, or the text is an accent
    colour lost only where it crosses onto something, it is outlined
    (:func:`plate`).
    """
    drawn, own = facts.drawn, facts.own
    if drawn.reads:
        return Leave()
    # A coloured note that reads on most of its length and is lost where it
    # runs onto something else keeps its colour: the colour says what it
    # belongs to, and the part that is lost is outlined instead.
    accent = own.colour.oklab().lch().C >= ACCENT
    crossing = drawn.low < MOSTLY
    clean = [
        ink
        for ink in facts.inks
        if ink.reading.reads and ink.reading.low < CLEAN
    ]
    if clean and not (accent and crossing):
        best = max(clean, key=lambda ink: ink.reading.lowest.value)
        return Recolour(best.colour)
    return Halo(plate(facts), max(HALO_EM * facts.size, HALO_MIN_PT))


def after(facts: InkFacts, tried: Mend) -> Mend:
    """What to try once ``tried`` was drawn and the text still did not
    read: an outline after a colour, and after an outline nothing, the
    text left as it was."""
    match tried:
        case Recolour():
            return Halo(plate(facts), max(HALO_EM * facts.size, HALO_MIN_PT))
        case Halo() | Leave():
            return Leave()


def in_the_way(facts: InkFacts) -> InTheWay:
    """Why neither a colour nor an outline made a text read. An outline
    always reads under opaque ink, so either the ink is not opaque or
    something is drawn over the text."""
    if facts.alpha < OPAQUE:
        return OwnAlpha(facts.alpha)
    return DrawnOver()


def plate(facts: InkFacts) -> Rgb:
    """The colour of a text's halo: that of the background it reads best
    on, so the outline disappears there and carries that background onto
    the others. When it reads on none (3:1), the colour furthest from its
    own among the inks it may take, white and black."""
    own = facts.own.colour
    if contrast(own, facts.home).value >= LEGIBLE.value:
        return facts.home
    poles = (Rgb(1.0, 1.0, 1.0), Rgb(0.0, 0.0, 0.0))
    return max(
        (*(ink.colour for ink in facts.inks), *poles),
        key=lambda colour: contrast(own, colour).value,
    )
