"""What ``label_bars`` is asked for, and what each of its labels is.

Where a label sits (outside, inside, at the middle), which bars get one (a
plain bar, a stack's segment, its net), whether totals print, what crowding
does, which ink a label takes and how its text is written: the options
``model.parse_bar_options`` reads from the call, and the facts and plans
the decisions about a label's text and ink take.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

from ..vocab import AlignBottom, AlignLeft, AlignRight, AlignTop, HAlign, VAlign

Rgba: TypeAlias = tuple[float, float, float, float]


Colour: TypeAlias = str | Rgba
"""A colour as matplotlib takes it: a name or hex, or an RGBA tuple."""


# ------------------------------------------------------------ bar ends
@dataclass(frozen=True)
class Higher:
    """Towards higher display coordinates (up, right): text beyond an
    anchor there stands on it or starts at it."""

    sign: ClassVar[float] = 1.0
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = AlignBottom()

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
    va: ClassVar[VAlign] = AlignTop()

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
