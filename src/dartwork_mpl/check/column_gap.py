"""Judge a column of text that floats away from the plot it sits beside."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from math import copysign
from statistics import median

from ..vocab import BESIDE_PLOT, BESIDE_TEXT, Room
from .findings import Findings
from .model import COLUMN_ROWS, Beside, Facts, Heading, Text, quote


@dataclass(frozen=True)
class Reach:
    """One thing a column stands beside: how far (px, negative: on its
    left) the column's block is from it, the room that kind of neighbour
    asks for, and the text it is when it is one."""

    gap: float
    room: Room
    neighbour: Text | None


@dataclass(frozen=True)
class Block:
    """Stacked texts sharing an edge, the headings over them, and the x
    range (px) they take together."""

    rows: tuple[Beside, ...]
    em: float
    x0: float
    x1: float
    headings: tuple[Heading, ...]


@dataclass(frozen=True)
class Column:
    """Stacked texts sharing an edge, and everything the column (with the
    headings over it) stands beside."""

    rows: tuple[Beside, ...]
    em: float
    reaches: tuple[Reach, ...]

    @property
    def adrift(self) -> bool:
        """Further from every neighbour than that neighbour's room, and
        not the next column of a grid of numbered cells."""
        return not self.in_step and all(
            abs(r.gap) > r.room.far * self.em for r in self.reaches
        )

    @property
    def in_step(self) -> bool:
        """Every row continues the numbers on its marks at their spacing."""
        return all(row.step is not None and row.step.kept for row in self.rows)

    @property
    def to_step(self) -> float | None:
        """Signed px to where the rows would continue the numbers on their
        marks (``None``: the marks carry none)."""
        offs = [row.step.off for row in self.rows if row.step is not None]
        return median(offs) if len(offs) == len(self.rows) else None

    def slack(self, reach: Reach) -> float:
        """Signed px between where the column is and where it would be set."""
        return reach.gap - copysign(reach.room.near * self.em, reach.gap)

    @property
    def binding(self) -> Reach:
        """The neighbour that lets the column move least."""
        return min(self.reaches, key=lambda r: abs(self.slack(r)))


def left_edge(row: Beside) -> float:
    """Where a left-aligned row starts."""
    return row.text.box.x0


def right_edge(row: Beside) -> float:
    """Where a right-aligned row ends."""
    return row.text.box.x1


def centre(row: Beside) -> float:
    """The middle of a centred row."""
    return (row.text.box.x0 + row.text.box.x1) / 2


def stacks(
    rows: list[Beside], edge: Callable[[Beside], float]
) -> list[list[Beside]]:
    """Rows of one type size whose ``edge`` falls on one vertical line."""
    result: list[list[Beside]] = []
    stack: list[Beside] = []
    for row in sorted(rows, key=edge):
        first = stack[0] if stack else row
        if stack and (
            edge(row) - edge(first) > 0.35 * first.text.em
            or abs(row.text.em / first.text.em - 1) > 0.12
        ):
            result.append(stack)
            stack = []
        stack.append(row)
    return [*result, stack]


def over(heading: Heading, x0: float, x1: float) -> bool:
    """The heading stands over or under the span."""
    return heading.text.box.x0 < x1 and x0 < heading.text.box.x1


def blocks(
    rows: tuple[Beside, ...], headings: tuple[Heading, ...]
) -> list[Block]:
    """The columns the texts of one Axes form: rows one under another on a
    shared left edge, right edge or centre, all with the plot on one side.
    Texts over or under a longer column are its headings, not a column of
    their own, and widen the block the column takes."""
    found = sorted(
        (
            stack
            for edge in (left_edge, right_edge, centre)
            for stack in stacks(list(rows), edge)
            if len(stack) >= COLUMN_ROWS
        ),
        key=len,
        reverse=True,
    )
    spans: list[tuple[float, float]] = []
    result: list[Block] = []
    for stack in found:
        em = median(row.text.em for row in stack)
        heights = sorted(row.text.box.y0 for row in stack)
        x0 = min(row.text.box.x0 for row in stack)
        x1 = max(row.text.box.x1 for row in stack)
        if any(x0 < b and a < x1 for a, b in spans) or any(
            b - a < 0.85 * em for a, b in pairwise(heights)
        ):
            continue
        spans.append((x0, x1))
        if len({row.reach < 0 for row in stack}) > 1:
            continue
        over_it = tuple(h for h in headings if over(h, x0, x1))
        result.append(
            Block(
                tuple(stack),
                em,
                min([x0, *(h.text.box.x0 for h in over_it)]),
                max([x1, *(h.text.box.x1 for h in over_it)]),
                over_it,
            )
        )
    return result


def measured(block: Block, owner: dict[int, Block]) -> Column:
    """The block with the gap to each thing it stands beside: block to
    block where that is another column (its heading to that column's
    heading too), block to text, and its rows to a mark or a plot's edge."""
    leftward = block.rows[0].reach < 0
    rows_x0 = min(row.text.box.x0 for row in block.rows)
    rows_x1 = max(row.text.box.x1 for row in block.rows)
    reaches: list[Reach] = []
    for row in block.rows:
        other = row.neighbour
        theirs = owner.get(id(other))
        # Beside the plot the rows are measured: a heading wider than they
        # are may run on over the plot, and does not bring them nearer.
        x0, x1 = (rows_x0, rows_x1) if other is None else (block.x0, block.x1)
        if leftward:
            inset = row.text.box.x0 - x0
            if other is not None and theirs is not None:
                inset += theirs.x1 - other.box.x1
        else:
            inset = x1 - row.text.box.x1
            if other is not None and theirs is not None:
                inset += other.box.x0 - theirs.x0
        gap = max(abs(row.reach) - inset, 0.0)
        room = BESIDE_PLOT if other is None else BESIDE_TEXT
        reaches.append(Reach(copysign(gap, row.reach), room, other))
    for heading in block.headings:
        gap = heading.left if leftward else heading.right
        if gap is not None and id(gap.text) in owner:
            reaches.append(
                Reach(-gap.px if leftward else gap.px, BESIDE_TEXT, None)
            )
    return Column(block.rows, block.em, tuple(reaches))


def column_gap(facts: Facts, found: Findings) -> Findings:
    """A column of text farther from what it sits beside than a reader
    takes as belonging to it."""
    rows: dict[int | None, list[Beside]] = {}
    heads: dict[int | None, list[Heading]] = {}
    for row in facts.beside:
        rows.setdefault(row.text.panel, []).append(row)
    for heading in facts.headings:
        heads.setdefault(heading.text.panel, []).append(heading)
    found_blocks = [
        block
        for panel, members in rows.items()
        for block in blocks(tuple(members), tuple(heads.get(panel, ())))
    ]
    taken = {
        id(text): b
        for b in found_blocks
        for text in (
            *(row.text for row in b.rows),
            *(h.text for h in b.headings),
        )
    }
    drifting = [
        col for block in found_blocks if (col := measured(block, taken)).adrift
    ]
    owner = {id(row.text): col for col in drifting for row in col.rows}

    def move(column: Column) -> float:
        """Signed px toward what it sits beside, following a column
        between the two that moves the same way."""
        near = column.binding
        ahead = owner.get(id(near.neighbour))
        follow = (
            move(ahead)
            if ahead is not None and (ahead.binding.gap < 0) == (near.gap < 0)
            else 0.0
        )
        return column.slack(near) + follow

    for column in drifting:
        shift = move(column)
        side = "left" if shift < 0 else "right"
        xs = {row.placed for row in column.rows}
        where = grid = ""
        placed = next(iter(xs)) if len(xs) == 1 else None
        if placed is not None:
            new = placed.x + shift / placed.px_per_unit
            where = f" (the x they were given: {placed.x:.3g} to {new:.3g})"
        if (step := column.to_step) is not None:
            grid = (
                "; or set it as the next cell of the rows, at the spacing "
                f"of the numbers in them: {abs(step) / facts.px_per_pt:.0f} "
                f"pt to the {'left' if step < 0 else 'right'}"
            )
            if placed is not None:
                at = placed.x + step / placed.px_per_unit
                grid += f" (x {placed.x:.3g} to {at:.3g})"
        texts = [row.text for row in column.rows]
        found = found.flag(
            "TEXT_COLUMN_GAP",
            f"Axes[{texts[0].panel}]: a column of {len(texts)} texts "
            f"({quote(t.short for t in texts)}) sits "
            f"{abs(column.binding.gap) / column.em:.1f} em from what is "
            f"beside it on its {side}",
            texts,
            fix="dm.place_columns(ax, texts) sets a column (its heading "
            "with it) one text size from the plot ax; by "
            f"hand, move it {abs(shift) / facts.px_per_pt:.0f} pt to the "
            f"{side}{where}"
            f"{grid}",
        )
    return found
