"""Pure legend decisions for the ordinary figure: facts in, plan out.

``loc="best"``: the first inside spot, for one to three columns, that keeps
the clearance from the data (a one-column legend taller than 55 % of the
Axes last); none free, the first side of above / right / below that no
other panel sits beyond and the legend fits along; no such side, the inside
spot that meets the fewest artists. Placed again at the Axes' final size, a
legend only moves in: to a spot free now, or it keeps its side. A named
side takes the fewest rows (above, below) or columns (right, left) that fit
along it. Special cases are in ``edges.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import assert_never

from .model import (
    FALLBACK_SIDES,
    INSIDE_SPOTS,
    TALL_SHARE,
    Anchor,
    AnchorFacts,
    Box,
    Columns,
    Entries,
    EntryFacts,
    EntryPlan,
    FigureFacts,
    FigurePlan,
    Hits,
    Inside,
    LegendFacts,
    LegendPlan,
    Loc,
    Outside,
    Side,
    Size,
    Span,
    TitleFacts,
    TitlePad,
)


@dataclass(frozen=True)
class Spot:
    """An inside spot tried: the artists it meets, its overflow and height."""

    plan: Inside
    hits: int
    overflow: float
    tall: float

    @property
    def free(self) -> bool:
        """Meets no ink and stays inside the Axes."""
        return self.hits == 0 and self.overflow <= 1e-3


def column_steps(
    entries: Entries, side: Side, asked: Columns | None
) -> tuple[Columns, ...]:
    """Column counts to try: fewest rows first across, fewest columns along."""
    if asked is not None:
        return (asked,)
    n = max(entries.count, 1)
    if side.across:
        counts = dict.fromkeys(-(-n // rows) for rows in range(1, n + 1))
        return tuple(Columns(k) for k in counts)
    return tuple(Columns(k) for k in range(1, n + 1))


def fit_along(
    entries: Entries,
    side: Side,
    span: Span,
    asked: Columns | None,
    size_of: Callable[[Entries, Columns], Size],
) -> Outside:
    """The first column count whose legend fits along ``side`` (else the last)."""
    steps = column_steps(entries, side, asked)
    for columns in steps:
        size = size_of(entries, columns)
        if size.along(side) <= span.length + 0.5:
            return Outside(side, columns, entries, size, fits=True)
    last = steps[-1]
    return Outside(side, last, entries, size_of(entries, last), fits=False)


def outside(facts: LegendFacts, side: Side, entries: Entries) -> Outside:
    """The legend outside ``side`` of its Axes."""
    span = facts.span_of(side)
    return fit_along(entries, side, span, facts.request.columns, facts.size_of)


def inside_spots(
    facts: LegendFacts, meets: Callable[[Box], Hits]
) -> tuple[Spot, ...]:
    """Every inside spot for one to three columns, in the order tried."""
    asked = facts.request.columns
    most = min(3, max(facts.entries.count, 1))
    counts = (
        (asked,)
        if asked is not None
        else tuple(Columns(k) for k in range(1, most + 1))
    )
    spots: list[Spot] = []
    for columns in counts:
        size = facts.size_of(facts.entries, columns)
        if not size.finite:
            continue
        tall = 0.0
        if columns.n == 1:
            tall = max(
                0.0, size.height / max(facts.axes.height, 1.0) - TALL_SHARE
            )
        for loc in INSIDE_SPOTS:
            box = size.placed(loc, facts.parent, facts.pad)
            spots.append(
                Spot(
                    Inside(loc, columns),
                    meets(box).n,
                    box.outside_share(facts.axes),
                    tall,
                )
            )
    return tuple(spots)


def first_free(spots: tuple[Spot, ...]) -> Inside | None:
    """The first free spot, a tall one-column legend after the others."""
    free = [spot for spot in spots if spot.free]
    return min(free, key=lambda spot: spot.tall).plan if free else None


def least_covering(spots: tuple[Spot, ...]) -> Inside:
    """The spot meeting the fewest artists (then the least overflow)."""
    if not spots:
        return Inside(Loc.UPPER_RIGHT, Columns(1), free=False)
    best = min(spots, key=lambda spot: (spot.hits, spot.overflow, spot.tall))
    return Inside(best.plan.loc, best.plan.columns, free=False)


def place(facts: LegendFacts) -> LegendPlan:
    """Where the legend goes, or goes again at the size the Axes has now."""
    side = facts.request.side
    if side is not None:
        return outside(facts, side, facts.entries)
    spots = inside_spots(facts, facts.meets)
    free = first_free(spots)
    if free is not None:
        return free
    match facts.current:  # placed again: inwards only
        case Outside(side=side):
            return outside(facts, side, facts.entries)
        case Inside() as current:
            return current
        case None:
            pass
        case _:
            assert_never(facts.current)
    sides = [s for s in FALLBACK_SIDES if s in facts.free_sides]
    if not facts.request.anchored and sides:
        plans = [outside(facts, s, facts.entries) for s in sides]
        return next((plan for plan in plans if plan.fits), plans[0])
    return least_covering(spots)


def anchor(facts: AnchorFacts) -> Anchor:
    """Past the decorations beyond the side, centred on the Axes."""
    reach = [
        facts.axes.reach_past(facts.side, box) for box in facts.decorations
    ]
    return Anchor(clearance=max([0.0, *reach]))


def title_pad(facts: TitleFacts) -> TitlePad:
    """Titles keep their pad; a legend above them is an edge case."""
    return TitlePad()


def figure_place(facts: FigureFacts) -> FigurePlan:
    """The figure legend above (else right of) the panels, or the side named."""
    sides = (
        (facts.side,) if facts.side is not None else (Side.ABOVE, Side.RIGHT)
    )
    plans: list[Outside] = []
    for side in sides:
        length = facts.figure.width if side.across else facts.figure.height
        span = Span(0.0, length - 2 * facts.pad)
        plans.append(
            fit_along(facts.entries, side, span, facts.columns, facts.size_of)
        )
    plan = next((p for p in plans if p.fits), plans[0])
    return FigurePlan(plan.side, plan.columns)


def entries(facts: EntryFacts) -> EntryPlan:
    """The Axes' own labelled artists, each name once, on the Axes itself."""
    seen: set[str] = set()
    picks: list[tuple[int, int]] = []
    for index, label in enumerate(facts.owners[facts.focus].entries.labels):
        if label not in seen:
            seen.add(label)
            picks.append((facts.focus, index))
    return EntryPlan(host=facts.focus, picks=tuple(picks))
