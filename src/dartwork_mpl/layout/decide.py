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

from ..vocab import EDGES, Bottom, Edge, Left, Right, Top
from .model import (
    EDGE_BAND,
    EDGE_BAND_TOL,
    EDGE_EPSILON,
    Canvas,
    ContentFacts,
    FigureArtist,
    Px,
    Reserves,
    Sides,
    Step,
    TextFacts,
    TextPlan,
)


def band_edge(artist: FigureArtist, canvas: Canvas) -> Edge | None:
    """The edge whose outer band a figure text sits in, by its reading
    direction: a suptitle the top, a source line the bottom, a supylabel
    the left (``None``: a legend, or text in the middle)."""
    if artist.vertical is None:
        return None
    box = artist.box
    if artist.vertical:
        centre = (box.x0 + box.x1) / 2 / canvas.width
    else:
        centre = (box.y0 + box.y1) / 2 / canvas.height
    if centre <= EDGE_BAND + EDGE_BAND_TOL:
        return Left() if artist.vertical else Bottom()
    if centre >= 1.0 - EDGE_BAND - EDGE_BAND_TOL:
        return Right() if artist.vertical else Top()
    return None


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


def reserves(facts: ContentFacts) -> Reserves:
    """Each figure artist on its band's edge, else the nearest."""
    return tuple(
        band_edge(art, facts.canvas) or nearest_edge(art, facts.canvas)
        for art in facts.artists
    )


def reserved(facts: ContentFacts, edges: Reserves) -> Sides:
    """The share of each edge figure-level artists keep, gap included."""
    width, height = facts.canvas.width, facts.canvas.height
    res = dict.fromkeys(EDGES, 0.0)
    for art, edge in zip(facts.artists, edges, strict=True):
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


def solve(facts: ContentFacts, edges: Reserves) -> Step | None:
    """Sides that put the content ``margins`` from the canvas (``None``:
    no Axes has content)."""
    if not facts.axes:
        return None
    width, height = facts.canvas.width, facts.canvas.height
    hangs = [
        Sides(
            left=a.position.left - a.box.x0 / width,
            right=a.box.x1 / width - a.position.right,
            bottom=a.position.bottom - a.box.y0 / height,
            top=a.box.y1 / height - a.position.top,
        )
        for a in facts.axes
    ]
    res, m = reserved(facts, edges), facts.margins
    left = res.left + m.left + max(h.left for h in hangs)
    right = (1.0 - res.right) - m.right - max(h.right for h in hangs)
    bottom = res.bottom + m.bottom + max(h.bottom for h in hangs)
    top = (1.0 - res.top) - m.top - max(h.top for h in hangs)
    left = max(0.0, min(left, 1.0 - EDGE_EPSILON))
    right = min(1.0, max(right, left + EDGE_EPSILON))
    bottom = max(0.0, min(bottom, 1.0 - EDGE_EPSILON))
    top = min(1.0, max(top, bottom + EDGE_EPSILON))
    new = Sides(left, right, bottom, top)
    last = facts.last
    if last is None:
        return Step(new, Px(float("inf")))
    delta = max(
        abs(left - last.left) * width,
        abs(right - last.right) * width,
        abs(bottom - last.bottom) * height,
        abs(top - last.top) * height,
    )
    return Step(new, Px(delta))


def text_plan(facts: TextFacts) -> TextPlan:
    """Nothing: an ordinary figure's text fits once its margins do."""
    return TextPlan()
