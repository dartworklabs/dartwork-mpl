"""The labels slice's types, and the one place a call's keywords become them.

Display measurements are pixels (:class:`Span`, :class:`Box`); offsets a
label keeps through a resize are points. ``label_bars``' keywords are parsed
once here (:func:`parse_bar_options`); a bad one raises ``ValueError`` naming
it. The other helpers' keywords and matplotlib's alignment names become
variants here too; each variant carries the string matplotlib takes for it.
"""

from __future__ import annotations

import math
import numbers
import string
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import (
    ClassVar,
    Literal,
    SupportsFloat,
    SupportsIndex,
    TypeAlias,
    TypedDict,
    TypeVar,
)

import numpy as np

from ..align import (
    AlignCentre,
    AlignLeft,
    AlignRight,
    Bottom,
    HAlign,
    HAlignName,
    Top,
    VAlign,
    VAlignName,
    VCentre,
)

Rgba: TypeAlias = tuple[float, float, float, float]
Colour: TypeAlias = str | Rgba
"""A colour as matplotlib takes it: a name or hex, or an RGBA tuple."""

AnyColour: TypeAlias = str | tuple[float, float, float] | Rgba
"""A colour a caller passes: a name or hex, an RGB or an RGBA tuple."""

FontStyleName: TypeAlias = Literal["normal", "italic", "oblique"]


class LetterStyle(TypedDict, total=False):
    """The ``Text`` keywords the label helpers hand on to matplotlib.

    These are the properties a caller styles a label with; matplotlib
    still takes any other ``Text`` property it knows at run time, the
    checker only knows these. Size and weight are in :class:`TextStyle`;
    ``label_axes`` takes them as its own parameters.
    """

    color: AnyColour
    c: AnyColour
    alpha: float | None
    backgroundcolor: AnyColour
    fontfamily: str | Sequence[str]
    family: str | Sequence[str]
    fontname: str
    fontstyle: FontStyleName
    style: FontStyleName
    fontstretch: float | str
    fontvariant: Literal["normal", "small-caps"]
    horizontalalignment: HAlignName
    ha: HAlignName
    verticalalignment: VAlignName
    va: VAlignName
    multialignment: HAlignName
    ma: HAlignName
    rotation: float | Literal["vertical", "horizontal"] | None
    rotation_mode: Literal["default", "anchor"] | None
    linespacing: float | None
    wrap: bool
    usetex: bool | None
    parse_math: bool
    bbox: dict[str, object] | None
    zorder: float
    clip_on: bool
    visible: bool
    in_layout: bool
    label: str
    gid: str | None
    url: str | None
    path_effects: Sequence[object]


class NoteStyle(LetterStyle, total=False):
    """The keywords ``annotate_value`` / ``annotate_corner`` / ``label_hline``
    hand to ``ax.annotate``; their size is their own ``fontsize``."""

    fontweight: float | str
    weight: float | str
    arrowprops: dict[str, object] | None
    annotation_clip: bool | None


class TextStyle(LetterStyle, total=False):
    """The ``Text`` keywords ``add_note`` hands to ``fig.text``."""

    fontsize: float | str
    size: float | str
    fontweight: float | str
    weight: float | str


class AnnotateStyle(NoteStyle, total=False):
    """The keywords ``label_line_ends`` hands to ``ax.annotate``."""

    fontsize: float | str
    size: float | str


# ------------------------------------------------------------ bar ends
@dataclass(frozen=True)
class Higher:
    """Towards higher display coordinates (up, right): text beyond an
    anchor there stands on it or starts at it."""

    sign: ClassVar[float] = 1.0
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = Bottom()

    @property
    def flip(self) -> Lower:
        """The other way."""
        return Lower()

    def reach(self, low: float, high: float) -> float:
        """The end of ``[low, high]`` this way."""
        return high


@dataclass(frozen=True)
class Lower:
    """Towards lower display coordinates (down, left)."""

    sign: ClassVar[float] = -1.0
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = Top()

    @property
    def flip(self) -> Higher:
        """The other way."""
        return Higher()

    def reach(self, low: float, high: float) -> float:
        """The end of ``[low, high]`` this way."""
        return low


Toward: TypeAlias = Higher | Lower
"""The way a bar grows on screen, and so the way its end label points."""


# ------------------------------------------------------------ bar options
@dataclass(frozen=True)
class Outside:
    """Beyond the bar's end.

    ``centred``: at the bar's middle; ``inset``: inside the bar's end;
    ``rests_on_bar``: drawn on the bar, where it may lack room.
    """

    centred: ClassVar[bool] = False
    inset: ClassVar[bool] = False
    rests_on_bar: ClassVar[bool] = False

    def on_bar(self, off_bar: bool) -> bool:
        """Whether the label is drawn on its bar."""
        return False


@dataclass(frozen=True)
class Inside:
    """Inside the bar at its end, while the bar holds the label."""

    centred: ClassVar[bool] = False
    inset: ClassVar[bool] = True
    rests_on_bar: ClassVar[bool] = True

    def on_bar(self, off_bar: bool) -> bool:
        """On its bar unless the bar could not hold it (``off_bar``)."""
        return not off_bar


@dataclass(frozen=True)
class Center:
    """At the bar's middle."""

    centred: ClassVar[bool] = True
    inset: ClassVar[bool] = False
    rests_on_bar: ClassVar[bool] = True

    def on_bar(self, off_bar: bool) -> bool:
        """Always on its bar."""
        return True


Placement: TypeAlias = Outside | Inside | Center
"""Where one label sits once ``"auto"`` is resolved for its kind."""


@dataclass(frozen=True)
class ByKind:
    """``where="auto"``: a plain bar's label beyond its end, a segment's at
    its middle."""


Where: TypeAlias = ByKind | Placement


@dataclass(frozen=True)
class Edge:
    """The label of a plain bar.

    ``spills``: inside its bar's end, a label the bar cannot hold is drawn
    beyond the end instead; ``hides_unfit``: on its bar, a label the bar
    cannot hold is hidden; ``of_stack``: it labels a whole stack.
    """

    spills: ClassVar[bool] = True
    hides_unfit: ClassVar[bool] = False
    of_stack: ClassVar[bool] = False


@dataclass(frozen=True)
class Segment:
    """The label of one bar of a stack."""

    spills: ClassVar[bool] = False
    hides_unfit: ClassVar[bool] = True
    of_stack: ClassVar[bool] = False


@dataclass(frozen=True)
class StackTotal:
    """A stack's net, on the bar ending the stack."""

    spills: ClassVar[bool] = False
    hides_unfit: ClassVar[bool] = False
    of_stack: ClassVar[bool] = True


Kind: TypeAlias = Edge | Segment | StackTotal
"""What a bar label labels."""


@dataclass(frozen=True)
class TotalsToo:
    """``total="auto"``: stacks get their segments and their totals."""


@dataclass(frozen=True)
class TotalsOnly:
    """``total="only"``: stacks get only their totals."""


@dataclass(frozen=True)
class NoTotals:
    """``total=False``: stacks get only their segments."""


Total: TypeAlias = TotalsToo | TotalsOnly | NoTotals


@dataclass(frozen=True)
class Rotate:
    """``crowded="rotate"``: crowded labels on vertical bars turn."""


@dataclass(frozen=True)
class Skip:
    """``crowded="skip"``: crowded labels stay level; some are hidden."""


Crowded: TypeAlias = Rotate | Skip


@dataclass(frozen=True)
class TextInk:
    """The preset's text colour."""

    series: ClassVar[bool] = False


@dataclass(frozen=True)
class SeriesInk:
    """``color="series"``: a label off its bar takes the bar's colour."""

    series: ClassVar[bool] = True


@dataclass(frozen=True)
class OwnInk:
    """One colour the call gave."""

    rgba: Rgba
    series: ClassVar[bool] = False


LabelInk: TypeAlias = TextInk | SeriesInk | OwnInk


@dataclass(frozen=True)
class TickLike:
    """``fmt=None``: the value printed like the axis's ticks."""


@dataclass(frozen=True)
class Template:
    """``fmt="${}B"``: each ``{}`` field holds the number."""

    text: str


@dataclass(frozen=True)
class Call:
    """``fmt=f``: ``f`` of the value in the tick unit, as text."""

    write: Callable[[float], object]


Fmt: TypeAlias = TickLike | Template | Call


@dataclass(frozen=True)
class BarOptions:
    """The keywords of one ``label_bars`` call, validated.

    ``plus``: ``sign="+"``, rises are signed too (``+30``).
    """

    where: Where = ByKind()
    total: Total = TotalsToo()
    crowded: Crowded = Rotate()
    decimals: int | None = None
    fmt: Fmt = TickLike()
    color: LabelInk = TextInk()
    plus: bool = False

    @property
    def series(self) -> bool:
        """``color="series"``: a label off its bar takes the bar's colour."""
        return self.color.series


def template_fields(template: str) -> list[tuple[str, str, str]]:
    """``(literal, spec, conversion)`` of each ``{}`` field of ``template``."""
    return [
        (literal, spec or "", conversion or "")
        for literal, name, spec, conversion in string.Formatter().parse(
            template
        )
        if name is not None
    ]


T = TypeVar("T")


def _choice(name: str, value: object, table: Mapping[object, T]) -> T:
    """The entry ``value`` names; ``ValueError`` naming the keyword."""
    for key, choice in table.items():
        if value is key or (isinstance(key, str) and value == key):
            return choice
    names = ", ".join(repr(a) for a in table)
    raise ValueError(f"{name} must be one of {names} (got {value!r})")


WHERE: Mapping[object, Where] = {
    "auto": ByKind(),
    "outside": Outside(),
    "inside": Inside(),
    "center": Center(),
}
TOTAL: Mapping[object, Total] = {
    "auto": TotalsToo(),
    "only": TotalsOnly(),
    False: NoTotals(),
}
CROWDED: Mapping[object, Crowded] = {"rotate": Rotate(), "skip": Skip()}
PLUS: Mapping[object, bool] = {"-": False, "+": True}


def _fmt(fmt: object) -> Fmt:
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
        return Template(fmt)
    if fmt is None:
        return TickLike()
    if callable(fmt):
        return Call(fmt)
    raise ValueError(
        f"fmt must be None, a '{{}}' template or a callable (got {fmt!r})"
    )


C = TypeVar("C")
"""A colour as the shell's ``to_rgba`` reads it."""


def _ink(color: C | None, to_rgba: Callable[[C], Rgba]) -> LabelInk:
    if color is None:
        return TextInk()
    if isinstance(color, str) and color == "series":
        return SeriesInk()
    try:
        return OwnInk(to_rgba(color))
    except (ValueError, TypeError):
        raise ValueError(
            f"color must be None, 'series' or a matplotlib colour (got {color!r})"
        ) from None


def parse_bar_options(
    *,
    where: object,
    total: object,
    crowded: object,
    decimals: object,
    fmt: object,
    color: C | None,
    sign: object,
    to_rgba: Callable[[C], Rgba],
) -> BarOptions:
    """The call's keywords as :class:`BarOptions`; ``ValueError`` names a bad one.

    ``to_rgba`` reads a matplotlib colour, raising ``ValueError`` for
    anything else (the shell passes matplotlib's own, so this module stays
    pure).
    """
    parsed_where = _choice("where", where, WHERE)
    parsed_total = _choice("total", total, TOTAL)
    parsed_crowded = _choice("crowded", crowded, CROWDED)
    plus = _choice("sign", sign, PLUS)
    if decimals is not None and (
        isinstance(decimals, bool)
        or not isinstance(decimals, numbers.Integral)
        or int(decimals) < 0
    ):
        raise ValueError(
            f"decimals must be None or an integer >= 0 (got {decimals!r})"
        )
    return BarOptions(
        where=parsed_where,
        total=parsed_total,
        crowded=parsed_crowded,
        decimals=None if decimals is None else int(decimals),
        fmt=_fmt(fmt),
        color=_ink(color, to_rgba),
        plus=plus,
    )


def placement(kind: Kind, where: Where) -> Placement:
    """Where a label of ``kind`` sits for the call's ``where``.

    ``"auto"`` puts a plain bar's label beyond its end and a segment's at its
    middle; a total always sits beyond the stack's end.
    """
    auto: Placement
    match kind:
        case StackTotal():
            return Outside()
        case Segment():
            auto = Center()
        case Edge():
            auto = Outside()
    match where:
        case ByKind():
            return auto
        case Outside() | Inside() | Center():
            return where


# ------------------------------------------------------------ notes
@dataclass(frozen=True)
class Above:
    """Above the point (``side="above"``); for a line, above it."""

    offset: ClassVar[tuple[float, float]] = (0.0, 1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = Bottom()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Below:
    """Below the point; for a line, below it."""

    offset: ClassVar[tuple[float, float]] = (0.0, -1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = Top()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Right:
    """Right of the point."""

    offset: ClassVar[tuple[float, float]] = (1.0, 0.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = VCentre()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Left:
    """Left of the point."""

    offset: ClassVar[tuple[float, float]] = (-1.0, 0.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = VCentre()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


Side: TypeAlias = Above | Below | Right | Left
"""Where ``annotate_value`` puts a label from its point."""

SIDES: tuple[Side, ...] = (Above(), Below(), Right(), Left())


@dataclass(frozen=True)
class AnySide:
    """``side="auto"``: the first side that is free, in :data:`SIDES` order."""

    @property
    def tries(self) -> tuple[Side, ...]:
        """Every side, in the order tried."""
        return SIDES


SideChoice: TypeAlias = Side | AnySide


def parse_side(value: object) -> SideChoice:
    """``annotate_value``'s ``side``; ``ValueError`` otherwise."""
    names: dict[str, SideChoice] = {
        "auto": AnySide(),
        "above": Above(),
        "below": Below(),
        "right": Right(),
        "left": Left(),
    }
    if isinstance(value, str) and value in names:
        return names[value]
    raise ValueError(
        "side must be 'auto', 'above', 'below', 'left', or 'right'"
    )


@dataclass(frozen=True)
class UpperLeft:
    """An Axes' upper left corner; ``inward`` points into the Axes."""

    anchor: ClassVar[tuple[float, float]] = (0.0, 1.0)
    inward: ClassVar[tuple[float, float]] = (1.0, -1.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = Top()


@dataclass(frozen=True)
class UpperRight:
    """An Axes' upper right corner."""

    anchor: ClassVar[tuple[float, float]] = (1.0, 1.0)
    inward: ClassVar[tuple[float, float]] = (-1.0, -1.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = Top()


@dataclass(frozen=True)
class LowerLeft:
    """An Axes' lower left corner."""

    anchor: ClassVar[tuple[float, float]] = (0.0, 0.0)
    inward: ClassVar[tuple[float, float]] = (1.0, 1.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = Bottom()


@dataclass(frozen=True)
class LowerRight:
    """An Axes' lower right corner."""

    anchor: ClassVar[tuple[float, float]] = (1.0, 0.0)
    inward: ClassVar[tuple[float, float]] = (-1.0, 1.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = Bottom()


Corner: TypeAlias = UpperLeft | UpperRight | LowerLeft | LowerRight

CORNERS: tuple[Corner, ...] = (
    UpperLeft(),
    UpperRight(),
    LowerLeft(),
    LowerRight(),
)


def parse_corner(value: object) -> Corner:
    """``annotate_corner``'s ``loc``; ``ValueError`` otherwise."""
    names = dict(
        zip(
            ("upper left", "upper right", "lower left", "lower right"),
            CORNERS,
            strict=True,
        )
    )
    if isinstance(value, str) and value in names:
        return names[value]
    raise ValueError(
        "loc must be 'upper left', 'upper right', 'lower left', or "
        "'lower right'"
    )


def corner_order(first: Corner) -> tuple[Corner, ...]:
    """``first``, then the other corners in :data:`CORNERS` order."""
    return (first, *(c for c in CORNERS if c != first))


LineSide: TypeAlias = Above | Below
"""``label_hline``'s side of the line."""


def parse_line_side(value: object) -> LineSide:
    """``label_hline``'s ``side``; ``ValueError`` otherwise."""
    if value == "above":
        return Above()
    if value == "below":
        return Below()
    raise ValueError("side must be 'above' or 'below'")


@dataclass(frozen=True)
class LeftEnd:
    """The drawn line's left end; the label starts there."""

    ha: ClassVar[HAlign] = AlignLeft()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return left

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class LineMiddle:
    """The middle of the drawn line."""

    ha: ClassVar[HAlign] = AlignCentre()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return (left + right) / 2

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class RightEnd:
    """The drawn line's right end; the label ends there."""

    ha: ClassVar[HAlign] = AlignRight()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return right

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class AtFraction:
    """A fraction of the Axes' width, the label centred on it."""

    fraction: float
    ha: ClassVar[HAlign] = AlignCentre()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place in the Axes ``frame``."""
        return frame.low + frame.width * self.fraction

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


LinePlace: TypeAlias = LeftEnd | LineMiddle | RightEnd | AtFraction

LINE_ENDS: tuple[LinePlace, ...] = (RightEnd(), LeftEnd())


@dataclass(frozen=True)
class EitherEnd:
    """``x="auto"``: the clearer end of the drawn line, the right first."""

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """Both ends, in the order tried."""
        return LINE_ENDS


LineX: TypeAlias = LinePlace | EitherEnd


def parse_line_x(value: object) -> LineX:
    """``label_hline``'s ``x``: an end, the middle, a fraction or ``"auto"``."""
    if not isinstance(value, str):
        return AtFraction(_number(value))
    names: dict[str, LineX] = {
        "auto": EitherEnd(),
        "left": LeftEnd(),
        "center": LineMiddle(),
        "right": RightEnd(),
    }
    if value in names:
        return names[value]
    raise ValueError("x must be 'auto', 'left', 'center', 'right', or a float")


@dataclass(frozen=True)
class FromPanel:
    """``label_axes(x="auto")``: each letter placed from what its panel draws."""


@dataclass(frozen=True)
class AtLeft:
    """``label_axes(x=0.02)``: every letter's left edge at an Axes fraction."""

    x: float


LetterX: TypeAlias = FromPanel | AtLeft


def parse_letter_x(value: object) -> LetterX:
    """``label_axes``' ``x``: ``"auto"`` or an Axes-relative left edge."""
    if isinstance(value, str):
        return FromPanel() if value == "auto" else AtLeft(float(value))
    return AtLeft(_number(value))


def _number(value: object) -> float:
    if isinstance(value, SupportsFloat | SupportsIndex):
        return float(value)
    raise TypeError(f"expected a number, got {value!r}")


# ------------------------------------------------------------ value text
@dataclass(frozen=True)
class ValueFacts:
    """One label's value in its axis's tick unit, and how the call prints it."""

    scaled: float
    decimals: int
    fixed: bool
    plus: bool = False


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
    points to (pixels), and which way that edge is."""

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
    """A colour as matplotlib takes it, or ``None``: the preset's text
    colour."""

    color: Colour | None = None


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
