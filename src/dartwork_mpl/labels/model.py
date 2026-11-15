"""The labels slice's types, and the one place a call's keywords become them.

Display measurements are pixels (:class:`Span`, :class:`Box`); offsets a
label keeps through a resize are points. ``label_bars``' keywords are parsed
once here (:func:`parse_bar_options`); a bad one raises ``ValueError`` naming
it.
"""

from __future__ import annotations

import math
import numbers
import string
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

import numpy as np

Where: TypeAlias = Literal["auto", "outside", "inside", "center"]
# Where one label sits once "auto" is resolved for its kind.
Placement: TypeAlias = Literal["outside", "inside", "center"]
# What a bar label labels: a plain bar, one stack segment, a stack's net.
Kind: TypeAlias = Literal["edge", "segment", "total"]
Total: TypeAlias = Literal["auto", "only", False]
Crowded: TypeAlias = Literal["rotate", "skip"]
Sign: TypeAlias = Literal["-", "+"]
Fmt: TypeAlias = str | Callable[[float], object] | None
Side: TypeAlias = Literal["above", "below", "right", "left"]
Corner: TypeAlias = Literal[
    "upper left", "upper right", "lower left", "lower right"
]
# +1: the bar grows towards higher display coordinates (up, right).
Toward: TypeAlias = Literal[1, -1]

SIDES: tuple[Side, ...] = ("above", "below", "right", "left")
CORNERS: tuple[Corner, ...] = (
    "upper left",
    "upper right",
    "lower left",
    "lower right",
)


# ------------------------------------------------------------ bar options
@dataclass(frozen=True)
class BarOptions:
    """The keywords of one ``label_bars`` call, validated."""

    where: Where = "auto"
    total: Total = "auto"
    crowded: Crowded = "rotate"
    decimals: int | None = None
    fmt: Fmt = None
    color: object = None
    sign: Sign = "-"

    @property
    def series(self) -> bool:
        """``color="series"``: a label off its bar takes the bar's colour."""
        return isinstance(self.color, str) and self.color == "series"


def template_fields(template: str) -> list[tuple[str, str, str]]:
    """``(literal, spec, conversion)`` of each ``{}`` field of ``template``."""
    return [
        (literal, spec or "", conversion or "")
        for literal, name, spec, conversion in string.Formatter().parse(
            template
        )
        if name is not None
    ]


def _choice(name: str, value: object, allowed: tuple[object, ...]) -> None:
    if not any(
        value is a or (isinstance(a, str) and value == a) for a in allowed
    ):
        names = ", ".join(repr(a) for a in allowed)
        raise ValueError(f"{name} must be one of {names} (got {value!r})")


def parse_bar_options(
    *,
    where: object,
    total: object,
    crowded: object,
    decimals: object,
    fmt: object,
    color: object,
    sign: object,
    is_color: Callable[[object], bool],
) -> BarOptions:
    """The call's keywords as :class:`BarOptions`; ``ValueError`` names a bad one.

    ``is_color`` says whether a value is a matplotlib colour (the shell
    passes matplotlib's own test, so this module stays pure).
    """
    _choice("where", where, ("auto", "outside", "inside", "center"))
    _choice("total", total, ("auto", "only", False))
    _choice("crowded", crowded, ("rotate", "skip"))
    _choice("sign", sign, ("-", "+"))
    if decimals is not None and (
        isinstance(decimals, bool)
        or not isinstance(decimals, numbers.Integral)
        or int(decimals) < 0
    ):
        raise ValueError(
            f"decimals must be None or an integer >= 0 (got {decimals!r})"
        )
    if isinstance(fmt, str):
        try:
            fields = template_fields(fmt)
            fmt.format(*([1.0] * len(fields)))
        except (ValueError, IndexError, KeyError) as error:
            raise ValueError(
                f"fmt must be a template with '{{}}' for the number, e.g. "
                f"fmt='${{}}B' ({error}; got {fmt!r})"
            ) from None
        if not fields:
            raise ValueError(
                f"fmt must hold a '{{}}' for the number (got {fmt!r})"
            )
    elif fmt is not None and not callable(fmt):
        raise ValueError(
            f"fmt must be None, a '{{}}' template or a callable (got {fmt!r})"
        )
    if not (color is None or color == "series" or is_color(color)):
        raise ValueError(
            f"color must be None, 'series' or a matplotlib colour (got {color!r})"
        )
    return BarOptions(
        where=where,  # type: ignore[arg-type]  # checked by _choice
        total=total,  # type: ignore[arg-type]
        crowded=crowded,  # type: ignore[arg-type]
        decimals=None if decimals is None else int(decimals),  # type: ignore[call-overload]
        fmt=fmt,  # type: ignore[arg-type]
        color=color,
        sign=sign,  # type: ignore[arg-type]
    )


def placement(kind: Kind, where: Where) -> Placement:
    """Where a label of ``kind`` sits for the call's ``where``.

    ``"auto"`` puts a plain bar's label beyond its end and a segment's at its
    middle; a total always sits beyond the stack's end.
    """
    if kind == "total":
        return "outside"
    if where == "auto":
        return "center" if kind == "segment" else "outside"
    return where


# ------------------------------------------------------------ value text
@dataclass(frozen=True)
class ValueFacts:
    """One label's value in its axis's tick unit, and how the call prints it."""

    scaled: float
    decimals: int
    fixed: bool
    sign: Sign


@dataclass(frozen=True)
class LabelText:
    """What a label prints: ``lead``, then ``value`` at ``decimals`` places.

    ``lead`` is ``""`` or ``"+"``; ``fixed`` keeps a zero's decimals (``0.00``).
    """

    value: float
    decimals: int
    fixed: bool = False
    lead: str = ""


def prints_zero(value: float, decimals: int) -> bool:
    """Whether ``value`` prints as zero at ``decimals`` places."""
    return float(format(abs(value), f".{decimals}f")) == 0


# ------------------------------------------------------------ bar geometry
@dataclass(frozen=True)
class Span:
    """A ``[low, high]`` extent along one display axis, pixels."""

    low: float
    high: float

    @property
    def width(self) -> float:
        """``high - low``."""
        return self.high - self.low


@dataclass(frozen=True)
class Pixels:
    """A display length in pixels."""

    px: float


@dataclass(frozen=True)
class Spot:
    """One drawn bar label: its bar's middle across the bars, and its own
    extent there (pixels)."""

    centre: float
    span: Span


@dataclass(frozen=True)
class Position:
    """The drawn labels at one bar position: middle, union of extents,
    widest label, and which spots."""

    centre: float
    span: Span
    widest: float
    members: tuple[int, ...]


# Two bar middles closer than this (display pixels) are one position.
SAME_PX = 0.5


@dataclass(frozen=True)
class CrowdFacts:
    """One call's drawn labels, every bar middle of the plot area, the gap."""

    spots: tuple[Spot, ...]
    bar_centres: tuple[float, ...]
    gap: Pixels

    def positions(self) -> tuple[Position, ...]:
        """The spots grouped by bar position, in screen order."""
        order = sorted(
            range(len(self.spots)), key=lambda i: self.spots[i].centre
        )
        out: list[Position] = []
        for i in order:
            spot = self.spots[i]
            if out and spot.centre - out[-1].centre <= SAME_PX:
                last = out[-1]
                out[-1] = Position(
                    last.centre,
                    Span(
                        min(last.span.low, spot.span.low),
                        max(last.span.high, spot.span.high),
                    ),
                    max(last.widest, spot.span.width),
                    (*last.members, i),
                )
            else:
                out.append(
                    Position(spot.centre, spot.span, spot.span.width, (i,))
                )
        return tuple(out)

    def pitch(self, centre: float) -> float:
        """The distance from ``centre`` to the nearest other bar middle."""
        away = np.abs(np.asarray(self.bar_centres, dtype=float) - centre)
        away = away[away > SAME_PX]  # NaN bars drop out too
        return float(away.min()) if away.size else math.inf


@dataclass(frozen=True)
class Shown:
    """Which of the spots handed in stay drawn, in the order given."""

    flags: tuple[bool, ...]


@dataclass(frozen=True)
class Room:
    """A label beyond its bar end: anchor, room it needs to the axes edge it
    points to (pixels), and which edge."""

    anchor: float
    need: float
    toward: Toward


@dataclass(frozen=True)
class HeadroomFacts:
    """An autoscaled value axis on screen and the labels that need room."""

    view: Span
    rooms: tuple[Room, ...]


@dataclass(frozen=True)
class Headroom:
    """The view widened so every label fits, or ``None``: it already does."""

    view: Span | None


# ------------------------------------------------------------ ink
@dataclass(frozen=True)
class Ink:
    """A colour as matplotlib takes it (hex, name), or ``None``: the
    preset's text colour."""

    color: object = None


@dataclass(frozen=True)
class InkFacts:
    """What a bar label's colour depends on.

    ``on_bar``: the label is drawn on its bar. ``readable`` is white or the
    text colour, whichever reads on the bar; ``series_ink`` the bar's colour
    darkened to text contrast (each ``None`` when not measured).
    """

    options: BarOptions
    kind: Kind
    on_bar: bool
    readable: Ink
    series_ink: Ink


# ------------------------------------------------------------ point labels
@dataclass(frozen=True)
class Try:
    """A candidate place, measured: how much of the label leaves the axes
    and how much it covers data or text (square pixels)."""

    outside: float
    collision: float

    @property
    def clear(self) -> bool:
        """Inside the axes and covering nothing."""
        return self.outside <= 0 and self.collision <= 0


@dataclass(frozen=True)
class Tries:
    """The candidates in the order the helper tries them."""

    tries: tuple[Try, ...]

    def pick(self, candidates: Sequence[int], *, inside_first: bool) -> int:
        """The first clear candidate; else (``inside_first``) the least
        covered one inside the axes; else the least outside and covered."""
        tries = self.tries
        first = next((i for i in candidates if tries[i].clear), None)
        if first is not None:
            return first
        inside = [i for i in candidates if tries[i].outside <= 0]
        if inside_first and inside:
            return min(inside, key=lambda i: tries[i].collision)
        return min(
            candidates, key=lambda i: tries[i].outside + tries[i].collision
        )


@dataclass(frozen=True)
class Choice:
    """The index of the candidate taken."""

    index: int


# ------------------------------------------------------------ panel letters
@dataclass(frozen=True)
class Title:
    """A shown title of a panel: its baseline (px)."""

    baseline: float


@dataclass(frozen=True)
class Panel:
    """What one panel draws around its top-left corner, in display pixels.

    ``cell`` is the (row, column) key of its own grid cell. ``ylabel_x0``
    is the outer edge of its left y-axis name, ``guess_x0`` where one would
    be. ``top``: its top decoration; ``decos``: y name and tick boxes as
    ``(x0, x1, y1)``.
    """

    corner: tuple[float, float]
    width: float
    descent: float
    cell: tuple[tuple[int, int], tuple[int, int]] | None
    ylabel_x0: float | None
    guess_x0: float
    titles: tuple[Title, ...]
    top: float
    decos: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class PanelsFacts:
    """The panels of one ``label_axes`` call, its scale and fixed ``y``."""

    panels: tuple[Panel, ...]
    px_per_pt: float
    fixed_y: bool

    def groups(self, axis: int) -> dict[tuple[int, int], list[int]]:
        """Panel indices by grid row (``axis`` 0) or column (1)."""
        out: dict[tuple[int, int], list[int]] = {}
        for i, panel in enumerate(self.panels):
            if panel.cell is not None:
                out.setdefault(panel.cell[axis], []).append(i)
        return out

    def mates(self, i: int, axis: int) -> list[int]:
        """The panels in the row (0) or column (1) of panel ``i``, or itself."""
        cell = self.panels[i].cell
        return [i] if cell is None else self.groups(axis)[cell[axis]]


@dataclass(frozen=True)
class Letters:
    """Each letter's left edge and baseline, display pixels."""

    lefts: tuple[float, ...]
    baselines: tuple[float, ...]


# ------------------------------------------------------------ line ends
@dataclass(frozen=True)
class Column:
    """Label centres along one display axis (points), and the spacing."""

    centres: tuple[float, ...]
    height: float
