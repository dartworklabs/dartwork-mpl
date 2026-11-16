"""The layout's named special cases, applied after the ``decide`` functions.

``EDGES`` amends one step of the margin fit; ``TEXT_EDGES`` fits the text
that still collides once the margins hold; the loop fits the margins again
after each round of those.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import replace

from ..edgecase import EdgeCase
from ..vocab import Top, Which
from . import decide
from .model import (
    ANGLES,
    MAX_NAME_LINES,
    MAX_TICK_LINES,
    MIN_CELL_EM,
    TOUCH_PX,
    ArtistId,
    AxesContent,
    AxisName,
    Box,
    Canvas,
    ContentFacts,
    Count,
    Degrees,
    FigureArtist,
    Gap,
    Line,
    Px,
    Reach,
    Share,
    Spacing,
    TextFacts,
    TextPlan,
    TickGroup,
    TickRow,
    Width,
    tokens,
)

# -- the margin fit ------------------------------------------------------------


def _room(facts: ContentFacts) -> Px:
    """The width (px) between the margins and what figure artists keep."""
    res, m = decide.reserved(facts, decide.reserves(facts)), facts.margins
    share = 1.0 - res.left - res.right - m.left - m.right
    return Px(share * facts.canvas.width)


def _too_wide(axes: AxesContent, room: Px) -> bool:
    return axes.widest > room


def _has_text_wider_than_the_room(
    facts: ContentFacts, counted: ContentFacts
) -> bool:
    room = _room(counted)
    return any(_too_wide(a, room) for a in counted.axes)


def _let_it_pass(facts: ContentFacts, counted: ContentFacts) -> ContentFacts:
    """Count such an Axes' titles and x name one pixel wide: no plot width
    takes them in, since they are centred on the plot."""
    room = _room(counted)
    axes = tuple(
        replace(a, box=Box(a.narrow.x0, a.box.y0, a.narrow.x1, a.box.y1))
        if _too_wide(a, room)
        else a
        for a in counted.axes
    )
    return replace(counted, axes=axes)


def _over_panel_titles(art: FigureArtist, counted: ContentFacts) -> bool:
    """A figure title (a text across the top band) over titled panels."""
    return (
        art.vertical is False
        and decide.band_edge(art, counted.canvas) == Top()
        and any(a.titled for a in counted.axes)
        and art.gap < counted.title_pad
    )


def _has_figure_title_on_panel_titles(
    facts: ContentFacts, counted: ContentFacts
) -> bool:
    return any(_over_panel_titles(a, counted) for a in counted.artists)


def _part_the_titles(
    facts: ContentFacts, counted: ContentFacts
) -> ContentFacts:
    """The figure title keeps the title pad from the panels' titles, as
    each of those keeps it from its plot."""
    artists = tuple(
        replace(a, gap=counted.title_pad)
        if _over_panel_titles(a, counted)
        else a
        for a in counted.artists
    )
    return replace(counted, artists=artists)


#: What one step of the margin fit counts: each edge case amends the facts
#: ``decide.solve`` reads.
EDGES: tuple[EdgeCase[ContentFacts, ContentFacts], ...] = (
    EdgeCase(
        name="text-wider-than-the-room",
        why="a title wider than the canvas shrank its plot by its excess "
        "at every step until the plot was gone",
        example="test_edges.py::test_text_wider_than_the_room_keeps_the_plot",
        applies=_has_text_wider_than_the_room,
        adjust=_let_it_pass,
    ),
    EdgeCase(
        name="figure-title-on-panel-titles",
        why="a figure title sat flush on the first row's panel titles and "
        "the two read as one two-line title",
        example="test_edges.py::test_figure_title_on_panel_titles_keeps_the_pad",
        applies=_has_figure_title_on_panel_titles,
        adjust=_part_the_titles,
    ),
)


# -- text: pure helpers -------------------------------------------------------


def balanced_lines(
    words: Sequence[Line], lines: Count, width: Width
) -> tuple[tuple[Line, ...], Px]:
    """``words`` in ``lines`` lines, the widest as narrow as it can be, and
    its width. Ties keep the earlier break; fewer words give one a line."""
    n = len(words)
    memo: dict[tuple[int, int], tuple[Px, tuple[Line, ...]]] = {}

    def best(i: Count, left: Count) -> tuple[Px, tuple[Line, ...]]:
        if (i, left) in memo:
            return memo[(i, left)]
        if left == 1:
            line = Line(" ".join(words[i:]))
            result: tuple[Px, tuple[Line, ...]] = (width(line), (line,))
        else:
            result = (Px(math.inf), ())
            for j in range(i + 1, n - left + 2):
                head = Line(" ".join(words[i:j]))
                w_head = width(head)
                if w_head >= result[0]:
                    break  # a longer first line only gets wider
                w_rest, rest = best(Count(j), Count(left - 1))
                w = Px(max(w_head, w_rest))
                if w < result[0]:
                    result = (w, (head, *rest))
        memo[(i, left)] = result
        return result

    w, out = best(Count(0), Count(min(lines, n)))
    return out, w


def wrap_to(text: Line, limit: Px, width: Width, most: Count) -> Line | None:
    """``text`` in the fewest lines (2 .. ``most``) no wider than ``limit``."""
    words = tokens(text)
    for n in range(2, min(most, len(words)) + 1):
        lines, w = balanced_lines(words, Count(n), width)
        if w <= limit:
            return Line("\n".join(lines))
    return None


def wrap_limit(i: Count, row: TickRow) -> Px:
    """Widest label ``i`` may be and still clear both neighbours, counting
    on each to take no more than its fair share or its width."""
    limit = math.inf
    for j, k in ((i - 1, i - 1), (i + 1, i)):
        if not 0 <= k < len(row.gaps):
            continue
        share = row.gaps[k] - row.clearance
        limit = min(limit, 2 * share - min(row.widths[j], share))
    return Px(limit)


def smallest_angle(row: TickRow) -> Degrees | None:
    """The smallest of ``ANGLES`` at which neighbours clear: labels
    ``spacing`` apart sit ``spacing * sin(angle)`` apart across."""
    spacing = min(row.gaps)
    for angle in ANGLES:
        across = spacing * math.sin(math.radians(angle))
        if across >= row.line_height + row.clearance:
            return angle
    return None


def turn_angle(row: TickRow) -> Degrees | None:
    """The angle a crowded ``row`` turns to, or ``None`` (it stays)."""
    if row.authored or not row.crowded:
        return None
    angle = smallest_angle(row)
    if angle is not None:
        return angle
    # Upright only when it leaves neighbours overlapping less than flat.
    if row.line_height - min(row.gaps) >= row.worst_overlap:
        return None
    return Degrees(90.0)


def gap_fraction(need: Px, total: Px, cells: Count) -> Share | None:
    """The ``wspace`` / ``hspace`` whose gaps are ``need`` wide (``None``:
    no room left): a cell is ``total / (n + gap (n - 1))``."""
    room = total - need * (cells - 1)
    return None if room <= 0 else Share(need * cells / room)


def cell_after(gap: Share, total: Px, cells: Count) -> Px:
    """A cell's side once the spacing is ``gap``."""
    return Px(total / (cells + gap * (cells - 1)))


def deepest_reach(reaches: Sequence[Reach], gaps: Sequence[Px]) -> Px:
    """The widest gap two facing panels' content asks for (0: none meet)."""
    need = 0.0
    for k, gap in enumerate(gaps):
        for a in (r for r in reaches if r.along[1] - 1 == k):
            for b in (r for r in reaches if r.along[0] == k + 1):
                low = max(a.across[0], b.across[0])
                if min(a.across[1], b.across[1]) <= low:
                    continue  # not side by side
                reach = max(a.ahead, 0.0) + max(b.back, 0.0)
                if reach - gap > TOUCH_PX:
                    need = max(need, reach)
    return Px(need)


# -- text: the edge cases -----------------------------------------------------


def _overlong(name: AxisName, canvas: Canvas) -> bool:
    """Longer than its side and past the canvas or into another panel."""
    if name.span <= 0 or name.width(name.text) <= name.span:
        return False
    b = name.box
    off = max(-b.x0, b.x1 - canvas.width, -b.y0, b.y1 - canvas.height)
    return off > TOUCH_PX or any(-b.gap(o) > TOUCH_PX for o in name.others)


def _name_lines(name: AxisName) -> Line | None:
    most = Count(MAX_NAME_LINES)
    if wrapped := wrap_to(name.text, name.span, name.width, most):
        return wrapped
    words = tokens(name.text)
    if len(words) < 2:
        return None
    return Line("\n".join(balanced_lines(words, most, name.width)[0]))


def _has_overlong_name(facts: TextFacts, plan: TextPlan) -> bool:
    return any(_overlong(n, facts.canvas) for n in facts.names)


def _wrap_names(facts: TextFacts, plan: TextPlan) -> TextPlan:
    """The same name on the same axis of a grid takes the same lines."""
    names: dict[ArtistId, Line] = dict(plan.names)
    forms: dict[tuple[tuple[ArtistId, Which], Line], Line] = {}
    for name in facts.names:
        if _overlong(name, facts.canvas) and (lines := _name_lines(name)):
            names[name.label] = lines
            forms.setdefault((name.group, name.text), lines)
    for name in facts.names:
        form = forms.get((name.group, name.text))
        if form is not None:
            names.setdefault(name.label, form)
    return replace(plan, names=names)


def _parted(space: Spacing) -> Share | None:
    """The spacing that parts the panels by half an em, if it grows and
    each panel keeps ``MIN_CELL_EM``: past that the canvas is too small for
    its text, and parting would only take the plots away."""
    need = deepest_reach(space.reaches, space.gaps)
    if need <= 0:
        return None
    gap = gap_fraction(Px(need + 0.5 * space.em), space.total, space.cells)
    if gap is None or gap <= space.now + 1e-6:
        return None
    if cell_after(gap, space.total, space.cells) < MIN_CELL_EM * space.em:
        return None
    return gap


def _has_colliding_panels(facts: TextFacts, plan: TextPlan) -> bool:
    """Not in a round that wraps a name: what stands on it has not moved."""
    return not plan.names and any(
        _parted(s) is not None for s in facts.spacings
    )


def _part_panels(facts: TextFacts, plan: TextPlan) -> TextPlan:
    spacing: dict[Gap, Share] = dict(plan.spacing)
    for space in facts.spacings:
        if (gap := _parted(space)) is not None:
            spacing[space.key] = gap
    return replace(plan, spacing=spacing)


def _wrap_lines(rows: Sequence[TickRow]) -> Mapping[Line, Line] | None:
    """Each label that needs it, wrapped to the tightest limit any Axes of
    the shared axis sets it; ``None`` when one cannot wrap."""
    limits: dict[Line, Px] = {}
    for row in rows:
        for i, text in enumerate(row.texts):
            limit = wrap_limit(Count(i), row)
            limits[text] = min(limits.get(text, Px(math.inf)), limit)
    width = rows[0].width
    lines: dict[Line, Line] = {}
    for text, limit in limits.items():
        if width(text) <= limit:
            continue
        if not any(ch.isalpha() for ch in text):
            return None  # a number turns rather than breaks
        wrapped = wrap_to(text, limit, width, Count(MAX_TICK_LINES))
        if wrapped is None:
            return None
        lines[text] = wrapped
    return lines


def _wraps(group: TickGroup) -> Mapping[Line, Line] | None:
    """The group's wrap now (``None``: it does not wrap)."""
    rows = group.rows
    if (
        not rows
        or any(r.authored for r in rows)
        or not (group.wrapped or any(r.crowded for r in rows))
    ):
        return None
    return _wrap_lines(rows)


def _new_wraps(facts: TextFacts) -> Mapping[ArtistId, Mapping[Line, Line]]:
    found: dict[ArtistId, Mapping[Line, Line]] = {}
    for group in facts.groups:
        lines = _wraps(group)
        if lines is not None and lines != group.wrapped:
            found[group.axis] = lines
    return found


def _has_wrappable_ticks(facts: TextFacts, plan: TextPlan) -> bool:
    return bool(_new_wraps(facts))


def _wrap_ticks(facts: TextFacts, plan: TextPlan) -> TextPlan:
    return replace(plan, wraps={**plan.wraps, **_new_wraps(facts)})


def _turnable(facts: TextFacts) -> list[TickGroup]:
    """Groups that do not wrap (a wrap, kept or new, stays flat) and have
    a row to turn."""
    return [
        g
        for g in facts.groups
        if _wraps(g) is None and any(turn_angle(r) is not None for r in g.rows)
    ]


def _has_unwrappable_ticks(facts: TextFacts, plan: TextPlan) -> bool:
    return bool(_turnable(facts))


def _turn_ticks(facts: TextFacts, plan: TextPlan) -> TextPlan:
    wraps: dict[ArtistId, Mapping[Line, Line]] = dict(plan.wraps)
    turns: dict[ArtistId, Degrees] = dict(plan.turns)
    for group in _turnable(facts):
        if group.wrapped:
            wraps[group.axis] = {}  # turned labels are one line
        for row in group.rows:
            if (angle := turn_angle(row)) is not None:
                turns[row.axis] = angle
    return replace(plan, wraps=wraps, turns=turns)


TEXT_EDGES: tuple[EdgeCase[TextFacts, TextPlan], ...] = (
    EdgeCase(
        name="overlong-axis-name",
        why="an axis name longer than its panel ran into the next panel or "
        "off the canvas",
        example="test_edges.py::"
        "test_overlong_axis_name_wraps_and_its_twin_follows",
        applies=_has_overlong_name,
        adjust=_wrap_names,
    ),
    EdgeCase(
        name="colliding-panels",
        why="tick labels of neighbouring panels ran into each other at "
        "matplotlib's default spacing",
        example="test_edges.py::test_colliding_panels_part_by_half_an_em",
        applies=_has_colliding_panels,
        adjust=_part_panels,
    ),
    EdgeCase(
        name="crowded-ticks-wrap",
        why="long category names ran into each other on a narrow axis",
        example="test_edges.py::test_crowded_ticks_wrap_at_spaces",
        applies=_has_wrappable_ticks,
        adjust=_wrap_ticks,
    ),
    EdgeCase(
        name="crowded-ticks-rotate",
        why="crowded numbers or names with no space to break overlapped "
        "flat, since they cannot wrap",
        example="test_edges.py::test_crowded_ticks_rotate_when_they_cannot_wrap",
        applies=_has_unwrappable_ticks,
        adjust=_turn_ticks,
    ),
)
