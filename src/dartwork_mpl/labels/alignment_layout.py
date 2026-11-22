"""Plan a shared tab stop for every number in a row."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..vocab import AlignLeft, AlignRight, HAlign, NumericText


@dataclass(frozen=True)
class MeasuredRow:
    """A parsed row and its own font's advances in points."""

    text: NumericText
    width: Callable[[str], float]


@dataclass(frozen=True)
class Piece:
    """One line of text ending or starting at a tab stop."""

    text: str
    offset: float
    align: HAlign


def decimal_rows(rows: Sequence[MeasuredRow]) -> tuple[tuple[Piece, ...], ...]:
    """Pieces sharing stops, or no plan when the numeric shapes differ."""
    counts = {len(row.text.numbers) for row in rows}
    if len(counts) != 1 or 0 in counts:
        return ()
    plan: list[list[Piece]] = [[] for _ in rows]
    cursor = 0.0
    for runs in zip(*(row.text.numbers for row in rows), strict=True):
        measured = tuple(zip(runs, rows, plan, strict=True))
        cursor += max(row.width(run.space) for run, row, _ in measured)
        mark = cursor + max(row.width(run.before) for run, row, _ in measured)
        for run, _, pieces in measured:
            if run.before:
                pieces.append(Piece(run.before, mark, AlignRight()))
            if run.after:
                pieces.append(Piece(run.after, mark, AlignLeft()))
        cursor = mark + max(row.width(run.after) for run, row, _ in measured)
    for row, pieces in zip(rows, plan, strict=True):
        if row.text.tail.strip():
            pieces.append(Piece(row.text.tail, cursor, AlignLeft()))
    return tuple(tuple(pieces) for pieces in plan)
