"""The ordinary figure's layout: content-aware grid edges, nothing to refit.

Each step puts every edge of the root grid where the measured content of
the Axes sits ``margin`` from the canvas edge, past what figure-level text
and legends reserve there::

    left = reserved.left + margin.left + overhang.left

and so on, clamped into the canvas. The step is repeated until no edge moves
by half a pixel. Text fitting (wraps, turns, spacing) is only ever an edge
case: an ordinary figure has nothing to fit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import assert_never

from ..vocab import EDGES, Bottom, Edge, Left, Right, Top
from .model import (
    EDGE_EPSILON,
    MIN_PLOT_SHARE,
    Answer,
    ArtistId,
    AxesContent,
    Box,
    Canvas,
    ContentFacts,
    Edges,
    FigureArtist,
    Fit,
    Go,
    PlotSize,
    Px,
    Refuse,
    Request,
    Sides,
    Step,
    TextFacts,
    TextPlan,
)

NO_GRID = (
    "simple_layout: no GridSpec found (figure uses fig.add_axes or "
    "manually placed axes); layout unchanged. Build axes via "
    "plt.subplots / fig.add_gridspec to use content-aware margins."
)


def answer(request: Request) -> Answer:
    """Lay out a figure with Axes on a grid; leave anything else."""
    if not request.has_axes:
        return Refuse(None)
    if not request.has_grid:
        return Refuse(NO_GRID)
    return Go()


# -- one step -----------------------------------------------------------------


def on_half(edge: Edge, box: Box, canvas: Canvas) -> bool:
    """Whether the centre of ``box`` lies on the half of the canvas at ``edge``."""
    xc = (box.x0 + box.x1) / 2 / canvas.width
    yc = (box.y0 + box.y1) / 2 / canvas.height
    match edge:
        case Top():
            return yc >= 0.5
        case Bottom():
            return yc < 0.5
        case Left():
            return xc < 0.5
        case Right():
            return xc >= 0.5
        case _:
            assert_never(edge)


def role_edge(artist: FigureArtist, canvas: Canvas) -> Edge | None:
    """The edge a suptitle, supxlabel or supylabel holds on its half."""
    edge = artist.holds
    if edge is None or not on_half(edge, artist.box, canvas):
        return None
    return edge


def nearest_edge(artist: FigureArtist, canvas: Canvas) -> Edge:
    """The canvas edge nearest the artist."""
    box = artist.box
    distances = {
        Left(): box.x0 / canvas.width,
        Right(): 1.0 - box.x1 / canvas.width,
        Bottom(): box.y0 / canvas.height,
        Top(): 1.0 - box.y1 / canvas.height,
    }
    return min(distances, key=lambda e: distances[e])


def fit(facts: ContentFacts) -> Fit:
    """Each Axes' own pieces; each figure artist on its role's or nearest edge."""
    own = tuple(
        AxesContent(
            plot=a.plot, position=a.position, pieces=a.pieces, tight=a.tight
        )
        for a in facts.axes
    )
    reserves = tuple(
        role_edge(art, facts.canvas) or nearest_edge(art, facts.canvas)
        for art in facts.artists
    )
    return Fit(axes=own, reserves=reserves)


def content_box(axes: AxesContent) -> Box | None:
    """The union of the plot box and every piece (``None``: nothing drawn)."""
    boxes = [p.box for p in axes.pieces]
    if axes.plot is not None:
        boxes.append(axes.plot)
    if not boxes:
        return None
    return Box(
        min(b.x0 for b in boxes),
        max(b.x1 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.y1 for b in boxes),
    )


def reserved(facts: ContentFacts, fit: Fit) -> Sides:
    """The share of each edge figure-level artists keep, gap included."""
    width, height = facts.canvas.width, facts.canvas.height
    res = dict.fromkeys(EDGES, 0.0)
    for art, edge in zip(facts.artists, fit.reserves, strict=True):
        b = art.box
        gx, gy = art.gap / width, art.gap / height
        reach = {
            Left(): b.x1 / width + gx,
            Right(): 1.0 - b.x0 / width + gx,
            Bottom(): b.y1 / height + gy,
            Top(): 1.0 - b.y0 / height + gy,
        }[edge]
        res[edge] = max(res[edge], reach)
    return Sides(res[Left()], res[Right()], res[Bottom()], res[Top()])


def solve(facts: ContentFacts, fit: Fit) -> Step | None:
    """Edges that put the content ``margins`` from the canvas (``None``:
    no Axes has content)."""
    width, height = facts.canvas.width, facts.canvas.height
    hangs: list[Sides] = []
    for axes in fit.axes:
        box = content_box(axes)
        if box is None:
            continue
        pos = axes.position
        hangs.append(
            Sides(
                left=pos.left - box.x0 / width,
                right=box.x1 / width - pos.right,
                bottom=pos.bottom - box.y0 / height,
                top=box.y1 / height - pos.top,
            )
        )
    if not hangs:
        return None
    res, m = reserved(facts, fit), facts.margins
    left = res.left + m.left + max(h.left for h in hangs)
    right = (1.0 - res.right) - m.right - max(h.right for h in hangs)
    bottom = res.bottom + m.bottom + max(h.bottom for h in hangs)
    top = (1.0 - res.top) - m.top - max(h.top for h in hangs)
    left = max(0.0, min(left, 1.0 - EDGE_EPSILON))
    right = min(1.0, max(right, left + EDGE_EPSILON))
    bottom = max(0.0, min(bottom, 1.0 - EDGE_EPSILON))
    top = min(1.0, max(top, bottom + EDGE_EPSILON))
    edges = Edges(left, right, bottom, top)
    last = facts.last
    if last is None:
        return Step(edges, Px(float("inf")))
    delta = max(
        abs(left - last.left) * width,
        abs(right - last.right) * width,
        abs(bottom - last.bottom) * height,
        abs(top - last.top) * height,
    )
    return Step(edges, Px(delta))


# -- text ---------------------------------------------------------------------


def text_plan(facts: TextFacts) -> TextPlan:
    """Nothing: an ordinary figure's text fits once its margins do."""
    return TextPlan()


def crushed(
    before: Mapping[ArtistId, PlotSize], after: Mapping[ArtistId, PlotSize]
) -> bool:
    """Whether fitting text left a plot under ``MIN_PLOT_SHARE`` of a side."""
    for key, was in before.items():
        now = after.get(key, was)
        if (
            now.width < MIN_PLOT_SHARE * was.width
            or now.height < MIN_PLOT_SHARE * was.height
        ):
            return True
    return False
