"""#812: text that forms columns beside a plot, aligned column by column.

A cell is cut where it has to line up (at each number's decimal mark, and
between a number and the words around it) and every piece is one native
``Annotation``: its y is the row's data value, its x the Axes edge plus an
offset in points. Two pieces that must meet share one anchor (the whole
part ends there, the fraction starts there), so alignment holds exactly
whatever the dpi or backend; only the room between columns is measured,
with the unhinted metrics the PDF and SVG backends use.
"""

from __future__ import annotations

import re
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import text_to_path

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.text import Annotation

Align = Literal["left", "right", "center", "decimal"]
Side = Literal["left", "right"]

MINUS = "\u2212"
#: A number as a table prints it: sign, digits with thousands commas, fraction.
NUMBER = re.compile(r"[+\-\u2212]?\d[\d,]*(?:\.\d+)?")
#: What closes a number and stays on it: up to the first space or opener.
CLOSING = re.compile(r"[^\s\[({]*")
#: Between columns, and between the Axes edge and the first, in em.
GAP_EM = 1.5
#: Spike switches, for the two looks the owner chooses between.
HUG_BRACKETS = True
BOLD_HEADER = False
#: Header baseline above the Axes top, in em.
HEADER_LIFT_EM = 0.6


@dataclass(frozen=True)
class Piece:
    """One run of a cell and where it sits: ``dx`` points from the column
    start, drawn ending (``right``) or starting (``left``) there."""

    text: str
    dx: float
    ha: Literal["left", "right", "center"]


@dataclass(frozen=True)
class Column:
    """A laid-out column: its width in points and every row's pieces."""

    width: float
    rows: tuple[tuple[Piece, ...], ...]
    header: Piece | None


@dataclass(frozen=True)
class Cell:
    """One drawn cell: its text as written and the pieces that draw it."""

    text: str
    pieces: tuple[Annotation, ...]


#: The cells ``text_columns`` drew on each figure, a table per call. The
#: check would read this to judge a cell as one text (see ``partial.py``).
TABLES: weakref.WeakKeyDictionary[Figure, list[list[Cell]]] = (
    weakref.WeakKeyDictionary()
)


def width(text: str, prop: FontProperties) -> float:
    """The advance of ``text`` in points, unhinted (as PDF and SVG set it)."""
    if not text:
        return 0.0
    w, _h, _d = text_to_path.get_text_width_height_descent(
        text, prop, ismath=False
    )
    return float(w)


def digit_height(prop: FontProperties) -> float:
    """The height of a digit in points: rows centre on it."""
    _w, h, d = text_to_path.get_text_width_height_descent(
        "0", prop, ismath=False
    )
    return float(h - d)


def typeset(number: str) -> str:
    """A number with a real minus sign, which is as wide as a digit."""
    return MINUS + number[1:] if number.startswith("-") else number


def parts(cell: str) -> tuple[list[str], list[str]]:
    """``cell`` as the words around its numbers and the numbers: ``n + 1``
    literals for ``n`` numbers."""
    literals: list[str] = []
    numbers: list[str] = []
    at = 0
    for m in NUMBER.finditer(cell):
        literals.append(cell[at : m.start()])
        numbers.append(typeset(m.group()))
        at = m.end()
    literals.append(cell[at:])
    return literals, numbers


def reads_as_numbers(cells: Sequence[str]) -> bool:
    """Every cell prints the same number of numbers, at least one."""
    counts = {len(parts(c)[1]) for c in cells}
    return len(counts) == 1 and counts != {0}


def plain_column(
    cells: Sequence[str],
    align: Literal["left", "right", "center"],
    header: str | None,
    prop: FontProperties,
    bold: FontProperties,
) -> Column:
    """Whole cells on one edge (or centre) of the column."""
    widths = [width(c, prop) for c in cells]
    head = width(header, bold) if header else 0.0
    total = max([*widths, head])
    dx = {"left": 0.0, "right": total, "center": total / 2}[align]
    rows = tuple((Piece(c, dx, align),) for c in cells)
    return Column(total, rows, Piece(header, dx, align) if header else None)


def decimal_column(
    cells: Sequence[str],
    header: str | None,
    prop: FontProperties,
    bold: FontProperties,
) -> Column:
    """Numbers on their decimal marks, the words between them in place.

    Number ``k`` of every row shares one mark: what is before its decimal
    point ends there (with an opening bracket, ``[-3``), what is after
    starts there (with what closes the number, ``.6,``).
    """
    split = [parts(c) for c in cells]
    n = len(split[0][1])
    cursor = 0.0
    rows: list[list[Piece]] = [[] for _ in cells]
    for k in range(n + 1):
        # What closes the number before (", " "%)" "]") stays on it; the
        # rest (a space, an opening bracket) starts this slot for every row.
        cut = [CLOSING.match(s[0][k]) if k else None for s in split]
        opens = [
            s[0][k][m.end() :] if m else s[0][k]
            for s, m in zip(split, cut, strict=True)
        ]
        if k == n:  # after the last number: words that trail the row
            for row, t in zip(rows, opens, strict=True):
                if t:
                    row.append(Piece(t, cursor, "left"))
            cursor += max(width(t, prop) for t in opens)
            break
        # An opening bracket goes with its number ("[-3.6"), so only the
        # space before it is room every row keeps.
        lead = [t[: len(t) - len(t.lstrip())] for t in opens]
        hug = [t.lstrip() for t in opens]
        cursor += max(width(t, prop) for t in lead)
        if not HUG_BRACKETS:  # the other look: brackets in a column
            for row, t in zip(rows, hug, strict=True):
                if t:
                    row.append(Piece(t, cursor, "left"))
            cursor += max(width(t, prop) for t in hug)
            hug = [""] * len(hug)
        closes = [
            CLOSING.match(s[0][k + 1]) for s in split
        ]  # what follows this number
        nums = [s[1][k].partition(".") for s in split]
        tails = [
            dot + f + (m.group() if m else "")
            for (_w, dot, f), m in zip(nums, closes, strict=True)
        ]
        heads = [h + w for h, (w, _dot, _f) in zip(hug, nums, strict=True)]
        mark = cursor + max(width(h, prop) for h in heads)
        for row, head, tail in zip(rows, heads, tails, strict=True):
            row.append(Piece(head, mark, "right"))
            if tail:
                row.append(Piece(tail, mark, "left"))
        cursor = mark + max(width(t, prop) for t in tails)
    head = width(header, bold) if header else 0.0
    total = max(cursor, head)
    shift = (total - cursor) / 2  # a wider header: the block under its middle
    placed = tuple(
        tuple(Piece(p.text, p.dx + shift, p.ha) for p in row) for row in rows
    )
    return Column(
        total, placed, Piece(header, total / 2, "center") if header else None
    )


def text_columns(
    ax: Axes,
    y: Sequence[float],
    columns: Sequence[Sequence[str]],
    *,
    side: Side = "right",
    align: Sequence[Align] | None = None,
    header: Sequence[str] | None = None,
) -> list[Annotation]:
    """Columns of text beside ``ax``, one row at each data ``y``.

    ``columns`` is a list of columns, each a list of one string per row.
    A column whose every cell prints numbers lines them up on their
    decimal marks (``"0.8 [-3.6, 5.2]"``: all three), any other starts at
    its left edge; ``align`` names another choice per column. ``header``
    is one line per column above the Axes, set like an axis label. On the left the columns
    take the place of the y tick labels, which are turned off.
    """
    size = FontProperties(size=mpl.rcParams["ytick.labelsize"])
    points = size.get_size_in_points()
    prop = FontProperties(size=points)
    bold = FontProperties(
        size=mpl.rcParams["axes.labelsize"],
        weight="bold" if BOLD_HEADER else mpl.rcParams["axes.labelweight"],
    )
    em = points
    chosen = list(align) if align is not None else [None] * len(columns)
    heads = list(header) if header is not None else [None] * len(columns)
    laid: list[Column] = []
    for cells, how, head in zip(columns, chosen, heads, strict=True):
        if how == "decimal" or (how is None and reads_as_numbers(cells)):
            laid.append(decimal_column(cells, head, prop, bold))
        else:
            laid.append(plain_column(cells, how or "left", head, prop, bold))

    gap = GAP_EM * em
    span = sum(c.width for c in laid) + gap * (len(laid) - 1)
    start = gap if side == "right" else -gap - span
    edge = 1.0 if side == "right" else 0.0
    drop = -digit_height(prop) / 2  # baseline below the row's y: digits centre
    colour = mpl.rcParams["ytick.color"]
    drawn: list[Annotation] = []
    table: list[Cell] = []

    def put(piece: Piece, x0: float, xy: tuple[float, float], bolded: bool):
        coords = ax.transAxes if bolded else ax.get_yaxis_transform()
        lift = HEADER_LIFT_EM * em if bolded else drop
        ann = ax.annotate(
            piece.text,
            xy=xy,
            xycoords=coords,
            xytext=(x0 + piece.dx, lift),
            textcoords="offset points",
            ha=piece.ha,
            va="baseline",
            annotation_clip=False,
            fontsize=bold.get_size_in_points() if bolded else points,
            fontweight=bold.get_weight() if bolded else None,
            color=mpl.rcParams["axes.labelcolor"] if bolded else colour,
        )
        drawn.append(ann)
        return ann

    x0 = start
    for column, cells, head in zip(laid, columns, heads, strict=True):
        if column.header is not None and head:
            ann = put(column.header, x0, (edge, 1.0), True)
            table.append(Cell(head, (ann,)))
        for row, yy, cell in zip(column.rows, y, cells, strict=True):
            anns = tuple(put(p, x0, (edge, float(yy)), False) for p in row)
            table.append(Cell(cell, anns))
        x0 += column.width + gap
    if side == "left":
        ax.tick_params(axis="y", left=False, labelleft=False)
    fig = ax.get_figure(root=True)
    if fig is not None:
        TABLES.setdefault(fig, []).append(table)
    return drawn
