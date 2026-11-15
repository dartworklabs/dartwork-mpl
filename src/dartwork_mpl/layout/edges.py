"""The layout's named special cases, applied after the ``decide`` functions.

Each decision has its own facts and plan types and its own registry:
``FIT_EDGES`` for what one step counts as content, ``TEXT_EDGES`` for the
text fitted once the margins hold; the loop fits the margins again after
those and undoes a round that crushed a plot.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace

from ..edge import Bottom, Edge, Left, Right, Top
from ..edgecase import EdgeCase
from . import decide
from .model import (
    ANGLES,
    EDGE_BAND,
    EDGE_BAND_TOL,
    MAX_GAP_FRACTION,
    MAX_NAME_LINES,
    MAX_TICK_LINES,
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
    Fit,
    Gap,
    Line,
    Piece,
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

# -- one step: what counts as content -----------------------------------------


def _each_axes(plan: Fit, change: Callable[[AxesContent], AxesContent]) -> Fit:
    return replace(plan, axes=tuple(change(a) for a in plan.axes))


def _has_3d(facts: ContentFacts, plan: Fit) -> bool:
    return any(a.tight is not None for a in facts.axes)


def _tight_3d(facts: ContentFacts, plan: Fit) -> Fit:
    return _each_axes(
        plan, lambda a: a if a.tight is None else replace(a, pieces=a.tight)
    )


def _along_plot(piece: Piece, plot: Box | None, canvas: Canvas) -> Piece:
    """Along its side an outside legend counts only past the plot and off
    the canvas (the legend slice keeps it on the canvas there)."""
    if piece.outside is None or plot is None:
        return piece
    x0, x1, y0, y1 = piece.box.x0, piece.box.x1, piece.box.y0, piece.box.y1
    if piece.outside.across:
        x0 = x0 if x0 < 0.0 else max(x0, plot.x0)
        x1 = x1 if x1 > canvas.width else min(x1, plot.x1)
    else:
        y0 = y0 if y0 < 0.0 else max(y0, plot.y0)
        y1 = y1 if y1 > canvas.height else min(y1, plot.y1)
    return replace(piece, box=Box(x0, x1, y0, y1))


def _has_outside_legend(facts: ContentFacts, plan: Fit) -> bool:
    return any(p.outside is not None for a in plan.axes for p in a.pieces)


def _cut_legend_to_plot(facts: ContentFacts, plan: Fit) -> Fit:
    canvas = facts.canvas
    return _each_axes(
        plan,
        lambda a: replace(
            a, pieces=tuple(_along_plot(p, a.plot, canvas) for p in a.pieces)
        ),
    )


def _band_edge(art: FigureArtist, canvas: Canvas) -> Edge | None:
    """The edge of the outer band a figure text sits in, by reading direction."""
    if art.vertical is None or decide.role_edge(art, canvas) is not None:
        return None
    box = art.box
    if art.vertical:
        centre = (box.x0 + box.x1) / 2 / canvas.width
    else:
        centre = (box.y0 + box.y1) / 2 / canvas.height
    if centre <= EDGE_BAND + EDGE_BAND_TOL:
        return Left() if art.vertical else Bottom()
    if centre >= 1.0 - EDGE_BAND - EDGE_BAND_TOL:
        return Right() if art.vertical else Top()
    return None


def _has_band_text(facts: ContentFacts, plan: Fit) -> bool:
    return any(
        _band_edge(art, facts.canvas) is not None for art in facts.artists
    )


def _reserve_by_reading(facts: ContentFacts, plan: Fit) -> Fit:
    pairs = zip(facts.artists, plan.reserves, strict=True)
    edges = tuple(_band_edge(art, facts.canvas) or e for art, e in pairs)
    return replace(plan, reserves=edges)


def _has_sided_legend(facts: ContentFacts, plan: Fit) -> bool:
    return any(a.side is not None for a in facts.artists)


def _reserve_legend_side(facts: ContentFacts, plan: Fit) -> Fit:
    pairs = zip(facts.artists, plan.reserves, strict=True)
    return replace(plan, reserves=tuple(art.side or e for art, e in pairs))


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


def smallest_angle(row: TickRow, start: Degrees) -> Degrees | None:
    """The smallest of ``ANGLES`` from ``start`` at which neighbours clear:
    labels ``spacing`` apart sit ``spacing * sin(angle)`` apart across."""
    spacing = min(row.gaps)
    for angle in ANGLES:
        across = spacing * math.sin(math.radians(angle))
        if angle >= start and across >= row.line_height + row.clearance:
            return angle
    return None


def turn_angle(row: TickRow) -> Degrees | None:
    """The angle ``row`` turns to now, or ``None`` (it stays)."""
    if row.turned is None and (row.authored or not row.crowded):
        return None
    angle = smallest_angle(row, row.turned or Degrees(0.0))
    if angle is None:
        # Upright only when it leaves neighbours overlapping less than flat.
        if row.line_height - min(row.gaps) >= row.worst_overlap:
            return None
        angle = Degrees(90.0)
    if row.turned is not None and angle <= row.turned:
        return None
    return angle


def gap_fraction(need: Px, total: Px, cells: Count) -> Share | None:
    """The ``wspace`` / ``hspace`` whose gaps are ``need`` wide (``None``:
    no room left): a cell is ``total / (n + gap (n - 1))``."""
    room = total - need * (cells - 1)
    return None if room <= 0 else Share(need * cells / room)


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


def _overlong(name: AxisName, facts: TextFacts) -> bool:
    """Longer than its side and past the canvas or into another panel."""
    if name.span <= 0 or name.width(name.text) <= name.span:
        return False
    b, c = name.box, facts.canvas
    off = max(-b.x0, b.x1 - c.width, -b.y0, b.y1 - c.height)
    return off > TOUCH_PX or any(b.overlap(o) > TOUCH_PX for o in name.others)


def _name_lines(name: AxisName) -> Line | None:
    most = Count(MAX_NAME_LINES)
    if wrapped := wrap_to(name.text, name.span, name.width, most):
        return wrapped
    words = tokens(name.text)
    if len(words) < 2:
        return None
    return Line("\n".join(balanced_lines(words, most, name.width)[0]))


def _has_overlong_name(facts: TextFacts, plan: TextPlan) -> bool:
    return any(_overlong(n, facts) for n in facts.names)


def _wrap_names(facts: TextFacts, plan: TextPlan) -> TextPlan:
    """The same name on the same axis of a grid takes the same lines."""
    names: dict[ArtistId, Line] = dict(plan.names)
    forms = dict(facts.wrapped_names)
    for name in facts.names:
        if _overlong(name, facts) and (lines := _name_lines(name)):
            names[name.label] = lines
            forms.setdefault((name.group, name.text), lines)
    for name in facts.names:
        form = forms.get((name.group, name.text))
        if form is not None:
            names.setdefault(name.label, form)
    return replace(plan, names=names)


def _parted(space: Spacing) -> Share | None:
    """The spacing that parts the panels by half an em, if it grows."""
    need = deepest_reach(space.reaches, space.gaps)
    if need <= 0:
        return None
    gap = gap_fraction(Px(need + 0.5 * space.em), space.total, space.cells)
    if gap is None or gap > MAX_GAP_FRACTION or gap <= space.now + 1e-6:
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
        or any(r.turned is not None or r.authored for r in rows)
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


FIT_EDGES: tuple[EdgeCase[ContentFacts, Fit], ...] = (
    EdgeCase(
        name="axes-3d",
        why="a 3-D plot's stale tick labels sit thousands of px off the "
        "canvas, so the margins squeezed the cube to a sliver",
        example="test_edges.py::test_axes_3d_counts_its_tight_boxes",
        applies=_has_3d,
        adjust=_tight_3d,
    ),
    EdgeCase(
        name="outside-legend-along-side",
        why="a legend above a polar plot, wider than the plot, pushed both "
        "side margins in though the legend slice keeps it on the canvas",
        example="test_edges.py::"
        "test_outside_legend_along_side_counts_past_the_canvas_only",
        applies=_has_outside_legend,
        adjust=_cut_legend_to_plot,
    ),
    EdgeCase(
        name="figure-text-edge-band",
        why="a dm.add_note source line in the bottom-left corner reserved "
        "the left edge it is nearer to and sat over the plot",
        example="test_edges.py::"
        "test_figure_text_edge_band_reserves_by_reading_direction",
        applies=_has_band_text,
        adjust=_reserve_by_reading,
    ),
    EdgeCase(
        name="figure-legend-side",
        why="a wide figure legend above the panels reserved a side edge it "
        "is nearer to, and the panels lost their width instead of a row",
        example="test_edges.py::test_figure_legend_side_reserves_its_side",
        applies=_has_sided_legend,
        adjust=_reserve_legend_side,
    ),
)

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
