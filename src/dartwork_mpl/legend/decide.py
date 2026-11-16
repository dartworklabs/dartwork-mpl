"""Pure legend decisions: facts in, plan out.

Inside, a legend takes the first spot that keeps the clearance from the
data and stays in its Axes, else the spot meeting the fewest artists.
Outside a side it takes the fewest rows (above, below) or columns (right,
left) that fit along its Axes, and sits past the labels beyond that side.
"""

from __future__ import annotations

from ..vocab import Box
from .model import (
    INSIDE,
    Clearance,
    Columns,
    InsideFacts,
    Side,
    SideFacts,
    Spot,
    TitleFacts,
)


def inside(facts: InsideFacts) -> Spot:
    """The first free inside spot, else the one meeting the fewest artists."""
    tried: list[tuple[int, bool, Spot]] = []
    for spot in INSIDE:
        box = facts.size.placed(spot, facts.parent, facts.pad)
        hits = facts.meets(box).n
        spills = box.outside_share(facts.axes) > 1e-3
        if hits == 0 and not spills:
            return spot
        tried.append((hits, spills, spot))
    return min(tried, key=lambda t: (t[0], t[1]))[2]


def columns(facts: SideFacts) -> Columns:
    """The first column count whose legend fits along the side, else the last."""
    if facts.asked is not None:
        return facts.asked
    n = max(facts.count, 1)
    if facts.side.across:  # fewest rows first
        steps = list(dict.fromkeys(-(-n // rows) for rows in range(1, n + 1)))
    else:  # fewest columns first
        steps = list(range(1, n + 1))
    for k in steps:
        if facts.size_of(Columns(k)).along(facts.side) <= facts.length + 0.5:
            return Columns(k)
    return Columns(steps[-1])


def clearance(axes: Box, side: Side, labels: tuple[Box, ...]) -> Clearance:
    """How far the labels whose centre lies past ``side`` reach beyond it."""
    across = side.across
    low, high = (axes.y0, axes.y1) if across else (axes.x0, axes.x1)
    reach = [0.0]
    for box in labels:
        b0, b1 = (box.y0, box.y1) if across else (box.x0, box.x1)
        centre = (b0 + b1) / 2
        if side.far and centre > high + 0.5:
            reach.append(b1 - high)
        elif not side.far and centre < low - 0.5:
            reach.append(low - b0)
    return Clearance(max(reach))


def title_lift(legend: Box, title: TitleFacts) -> Clearance | None:
    """How far above the Axes top the titles go to clear a legend above it.

    ``None`` when their own pad already clears it.
    """
    needed = legend.y1 + title.gap - title.base
    return Clearance(needed) if needed > title.pad + 0.5 else None
