"""Plan a shared tab stop for every number in a row."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..vocab import AlignLeft, AlignRight, HAlign, NumericText

_MINUS = re.compile(r"(?<![^\s(\[{])-(?=\d|\.\d)")


def numeric_minus(text: str) -> str:
    """Use a mathematical minus for a leading number sign only."""
    return _MINUS.sub("\u2212", text)


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
    """Reserve the trailing runs, literal separators and next leading runs.

    A stop reserves the widest advance on each side of each joint, including
    the widest authored whitespace. An opener belongs to the leading run.
    Rows with different numeric shapes have no shared stops.
    """
    counts = {len(row.text.numbers) for row in rows}
    if len(counts) != 1 or 0 in counts:
        return ()
    plan: list[list[Piece]] = [[] for _ in rows]
    cursor = 0.0
    for runs in zip(*(row.text.numbers for row in rows), strict=True):
        measured = tuple(zip(runs, rows, plan, strict=True))
        cursor += max(row.width(run.space) for run, row, _ in measured)
        mark = cursor + max(
            row.width(numeric_minus(run.before)) for run, row, _ in measured
        )
        for run, _, pieces in measured:
            if run.before:
                pieces.append(
                    Piece(numeric_minus(run.before), mark, AlignRight())
                )
            if run.after:
                pieces.append(Piece(run.after, mark, AlignLeft()))
        cursor = mark + max(row.width(run.after) for run, row, _ in measured)
    return tuple(tuple(pieces) for pieces in plan)
