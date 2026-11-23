"""The check slice's types: what a drawn figure shows, and what is wrong with it.

Geometry is in display pixels of the figure as drawn. The shell
(``measure.py``) reads every fact once; the rules in ``decide.py`` read only
these types. ``handle`` fields carry the matplotlib artist or Axes a fact
came from, opaque here, so a finding can name what to fix.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..colorspace import Hex, Legibility, Ratio
from ..vocab import Box, HAlign, Which, X, Y
from .roles import Role

#: Contact up to this (points) is a touch, not a cover.
TOUCH_PT = 0.5

#: Air (pt) a panel letter inside its plot keeps from the data.
LETTER_CLEARANCE_PT = 2.0

#: A line this far (em) inside a name's box runs through the name; one that
#: ends at the box (a leader to its label) only touches it.
THROUGH_EM = 0.15

#: A number counts as centred in its dot when their middles are within a
#: quarter of its type size. In the recorded sweeps every number set in a
#: dot (dot matrices, rank circles) was at 0.0 em, and every value label
#: reported on a marker stood at least 1.9 em off the marker's middle.
HELD_EM = 0.25

#: Fewer stacked texts than this are labels, not a column.
COLUMN_ROWS = 4

#: A column beside a grid of numbered cells continues the grid when it is
#: within this share of the cells' spacing of where the next cell's number
#: would be. In the sweeps of 2026-11-23 the totals columns set as one more
#: cell were 0.05 of the spacing off; the ones that read as floating were
#: 0.15 and 0.35 off.
IN_STEP = 0.1

#: Both axes, x first.
AXES: tuple[Which, ...] = (X(), Y())

_NUMBER = re.compile(r"[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?:\D|$))")
#: Longest prefix or suffix a value label may carry ("Total: ", " MWh").
MAX_AFFIX = 12


def margins(box: Box, outer: Box) -> dict[str, float]:
    """Room between ``box`` and each edge of ``outer`` (negative: past it)."""
    return {
        "left": box.x0 - outer.x0,
        "right": outer.x1 - box.x1,
        "bottom": box.y0 - outer.y0,
        "top": outer.y1 - box.y1,
    }


def printed_value(text: str) -> str | None:
    """The one number a short label prints (``19.4 TWh``, ``$3.5``); ``None``
    for prose, math or a token like ``Q1``."""
    s = _THOUSANDS.sub(
        "", " ".join(text.strip().replace("\u2212", "-").split())
    )
    if not s or "\\" in s or "\n" in text.strip():
        return None
    if len(s) > 1 and s.startswith("$") and s.endswith("$"):
        return None
    found = list(_NUMBER.finditer(s))
    if len(found) != 1:
        return None
    prefix, suffix = s[: found[0].start()], s[found[0].end() :]
    if prefix and prefix[-1].isalpha():
        return None
    short = (
        len(prefix.strip()) <= MAX_AFFIX and len(suffix.strip()) <= MAX_AFFIX
    )
    return found[0].group() if short else None


def ascii_minus_value(text: str) -> bool:
    """A standalone negative quantity printed with a hyphen-minus."""
    return bool(re.match(r"^-\d", text.lstrip()) and printed_value(text))


def unicode_minus_tick(text: str) -> bool:
    """A Unicode minus before a digit, including in formatted tick mathtext."""
    return bool(re.search(r"(?<!\w)\u2212(?=\d)", text))


@dataclass(frozen=True)
class Text:
    """A drawn, non-blank text: its role, panel index and box."""

    handle: object
    text: str
    role: Role
    panel: int | None
    box: Box
    em: float

    @property
    def short(self) -> str:
        """The text cut for a message."""
        return " ".join(self.text.split())[:30]

    @property
    def words(self) -> bool:
        """The text has a letter or a digit to read."""
        return any(ch.isalnum() for ch in self.text)

    @property
    def value(self) -> bool:
        """The text prints one number: a value label."""
        return printed_value(self.text) is not None

    @property
    def needless_decimals(self) -> bool:
        """A value label printing a whole number with decimals (``12.0``)."""
        n = printed_value(self.text) or ""
        return "." in n and "e" not in n.lower() and float(n).is_integer()


@dataclass(frozen=True)
class TextGap:
    """Room between two aligned texts, in em of the smaller type size."""

    em: float


@dataclass(frozen=True)
class TickValues:
    """Where an axis' drawn labels stand, in data units, and whether the
    axis maps them linearly (not log, symlog, logit ...)."""

    values: tuple[float, ...]
    linear: bool


@dataclass(frozen=True)
class TickRow:
    """The drawn labels of one axis and how many neighbours collide.

    ``overlaps`` the neighbour pairs that collide and ``deepest`` the worst
    overlap in px. ``numbers``: the labels print quantities (not names,
    categories or dates); ``named``: a label names the axis, on this panel,
    one sharing the axis, its grid row (y) or column (x), or the figure;
    ``at``: where the labels stand.
    """

    handle: object
    panel: int
    axis: Which
    labels: tuple[Text, ...]
    overlaps: int
    deepest: float
    numbers: bool
    named: bool
    at: TickValues = TickValues((), linear=True)


@dataclass(frozen=True)
class Hit:
    """One thing a box covers: its kind (bar, line, text ...) and name."""

    kind: str
    name: str

    @property
    def stroke(self) -> bool:
        """A line, an error bar or a marker: not a bar or an area's edge."""
        return self.kind in ("line", "marker")

    @property
    def line(self) -> bool:
        """A line's stroke, not its markers."""
        return self.kind == "line"


@dataclass(frozen=True)
class Legend:
    """A drawn legend: its owner panel (``None``: a figure legend), its box
    and the data that box covers."""

    handle: object
    panel: int | None
    labels: tuple[str, ...]
    covers: tuple[Hit, ...]
    box: Box

    @property
    def panels(self) -> tuple[int, ...]:
        """The legend's Axes, none for a figure legend."""
        return () if self.panel is None else (self.panel,)

    @property
    def name(self) -> str:
        """``Legend of axes[i] ('A', 'B', ...)`` or ``Figure legend``."""
        owner = (
            "Figure legend"
            if self.panel is None
            else f"Legend of axes[{self.panel}]"
        )
        if not self.labels:
            return owner
        more = ", ..." if len(self.labels) > 2 else ""
        return f"{owner} ({', '.join(repr(t) for t in self.labels[:2])}{more})"


@dataclass(frozen=True)
class OnData:
    """A value label, a panel letter or a name and the data under it."""

    text: Text
    covers: tuple[Hit, ...]


@dataclass(frozen=True)
class Connected:
    """An inset's tick or axis labels with a zoom connector through them."""

    inset: int
    labels: tuple[Text, ...]


@dataclass(frozen=True)
class Inked:
    """A text the user placed, and how much of its ink reads on what is
    drawn behind it, pixel by pixel."""

    text: Text
    reading: Legibility

    @property
    def ink(self) -> Hex:
        """The colour of its faintest ink, as drawn."""
        return self.reading.ink.hex()

    @property
    def paper(self) -> Hex:
        """The colour behind that ink."""
        return self.reading.paper.hex()

    @property
    def ratio(self) -> Ratio:
        """The contrast its faintest ink reaches."""
        return self.reading.lowest


@dataclass(frozen=True)
class Panel:
    """A drawn Axes: its handle and index."""

    handle: object
    index: int


@dataclass(frozen=True)
class Frame:
    """The plot area of an Axes that fills it (a frame, an image, a
    colorbar): its index and box."""

    handle: object
    index: int
    box: Box


@dataclass(frozen=True)
class Inset:
    """An inset's axis labels and the spines of the Axes it sits in."""

    parent: Panel
    index: int
    labels: tuple[Text, ...]
    spines: tuple[Box, ...]


@dataclass(frozen=True)
class PolarTheta:
    """Drawn angle tick labels around the bounding box of a full polar disc."""

    panel: Panel
    disc: Box
    labels: tuple[Text, ...]


@dataclass(frozen=True)
class AlignmentSample:
    """One eligible column label and its measured horizontal positions."""

    text: Text
    align: HAlign
    x: float
    y: float
    marks: tuple[float, ...]
    font_key: int


@dataclass(frozen=True)
class Placed:
    """The x a text was given, and the px one unit of it moves the text."""

    x: float
    px_per_unit: float


@dataclass(frozen=True)
class Step:
    """Where a text stands against the texts on the marks of its row (the
    numbers in a heatmap's cells): ``pitch`` is the px from one of them to
    the next, ``off`` the signed px the text would move to stand one pitch
    on from the last, as the next cell of the row would."""

    off: float
    pitch: float

    @property
    def kept(self) -> bool:
        """The text continues the row at its own spacing."""
        return abs(self.off) <= IN_STEP * self.pitch


@dataclass(frozen=True)
class Beside:
    """A text set beside a plot: marks on one side of it at its height.

    ``reach`` is the px from the text to the nearest thing on that side (a
    mark, a plot's edge or another text), negative when that side is its
    left; ``neighbour`` is that thing when it is a text. ``step`` is set
    when the marks of its row carry texts at an even spacing.
    """

    text: Text
    reach: float
    neighbour: Text | None
    placed: Placed | None
    step: Step | None = None


@dataclass(frozen=True)
class Gap:
    """The nearest text on one side of a text at its height, and the px to it."""

    px: float
    text: Text


@dataclass(frozen=True)
class Heading:
    """A text the user set with marks on neither side of it at its height,
    and the nearest text on its left and on its right."""

    text: Text
    left: Gap | None
    right: Gap | None


@dataclass(frozen=True)
class TickOcclusion:
    """A drawn tick label and the mean opacity of the fill covering its box."""

    label: Text
    opacity: float


@dataclass(frozen=True)
class CanvasUse:
    """The visible body of a panel, clipped to the canvas."""

    panel: Panel
    body: Box


@dataclass(frozen=True)
class BarCanvasUse:
    """Columns and their text, where x is used for placement."""

    panel: Panel
    body: Box


@dataclass(frozen=True)
class ColorbarSpace:
    """A plot and its colorbar, with the scale's full subplot slot."""

    panel: Panel
    scale: Panel
    body: Box
    plot: Box
    bar: Box
    slot: Box


@dataclass(frozen=True)
class Boxed:
    """A placed text on an opaque box of its own and the filled marks that
    box covers."""

    text: Text
    covers: tuple[Hit, ...]


@dataclass(frozen=True)
class LineEnd:
    """The end of a straight line on an outer corner of a mark whose
    outline is the colour of the paper: ``short`` (pt), half that
    outline's width, is how far the visible corner stands back from it."""

    handle: object
    mark: object
    short: float


@dataclass(frozen=True)
class Dot:
    """A drawn scatter point: the box around its disc."""

    handle: object
    panel: int
    box: Box


@dataclass(frozen=True)
class Bar:
    """A drawn upright rectangle of an Axes: its outline, where its clip
    lets it draw.

    ``lengths``: the width and height it spans in data units (none for a
    rectangle placed in other coordinates, like ``ax.axhspan``).
    ``outset``: how far (pt) its edge stroke reaches past the outline, half
    the stroke's width.
    """

    handle: object
    panel: int
    box: Box
    lengths: tuple[float, ...] = ()
    outset: float = 0.0

    def prints(self, text: Text, along: Which) -> bool:
        """``text`` prints this bar's length along ``along``, as rounded as
        the text shows it (``7.9`` for a bar 7.9 or -7.94 long)."""
        number = printed_value(text.text)
        if number is None or not self.lengths or "e" in number.lower():
            return False
        places = len(number.partition(".")[2])
        length = abs(along.pick(*self.lengths))
        return length > 0 and round(length, places) == abs(float(number))


@dataclass(frozen=True)
class Facts:
    """Everything the rules read from one drawn figure."""

    canvas: Box
    px_per_pt: float
    texts: tuple[Text, ...] = ()
    figure_texts: tuple[Text, ...] = ()
    legend_texts: tuple[Text, ...] = ()
    ticks: tuple[TickRow, ...] = ()
    legends: tuple[Legend, ...] = ()
    empty: tuple[Panel, ...] = ()
    values: tuple[OnData, ...] = ()
    letters: tuple[OnData, ...] = ()
    struck: tuple[OnData, ...] = ()
    connected: tuple[Connected, ...] = ()
    inks: tuple[Inked, ...] = ()
    skipped: tuple[str, ...] = ()
    frames: tuple[Frame, ...] = ()
    insets: tuple[Inset, ...] = ()
    polar_theta: tuple[PolarTheta, ...] = ()
    minus_labels: tuple[Text, ...] = ()
    minus_tick: Text | None = None
    alignment: tuple[tuple[AlignmentSample, ...], ...] = ()
    beside: tuple[Beside, ...] = ()
    headings: tuple[Heading, ...] = ()
    occluded_ticks: tuple[TickOcclusion, ...] = ()
    edge_texts: tuple[Text, ...] = ()
    edge_titles: tuple[Text, ...] = ()
    canvas_use: CanvasUse | BarCanvasUse | None = None
    colorbar_space: ColorbarSpace | None = None
    bars: tuple[Bar, ...] = ()
    dots: tuple[Dot, ...] = ()
    boxed: tuple[Boxed, ...] = ()
    line_ends: tuple[LineEnd, ...] = ()

    @property
    def touch(self) -> float:
        """:data:`TOUCH_PT` in px."""
        return TOUCH_PT * self.px_per_pt

    @property
    def by_panel(self) -> dict[int, list[Text]]:
        """Axes texts and tick labels, grouped by panel."""
        groups: dict[int, list[Text]] = {}
        for t in self.texts + tuple(x for r in self.ticks for x in r.labels):
            if t.panel is not None:
                groups.setdefault(t.panel, []).append(t)
        return groups

    @property
    def all_texts(self) -> tuple[Text, ...]:
        """Axes texts, tick labels, figure texts and legend entries."""
        return self.under_legends + self.legend_texts

    @property
    def under_legends(self) -> tuple[Text, ...]:
        """The texts a legend can cover: all but legend entries."""
        ticks = tuple(t for row in self.ticks for t in row.labels)
        return self.texts + ticks + self.figure_texts


def quote(texts: Iterable[str], most: int = 3) -> str:
    """The first ``most`` distinct texts, quoted and joined."""
    shown = list(dict.fromkeys(texts))
    more = ", ..." if len(shown) > most else ""
    return ", ".join(repr(t) for t in shown[:most]) + more


def panels_of(texts: Iterable[Text]) -> tuple[int, ...]:
    """The panels the texts belong to, sorted."""
    return tuple(sorted({t.panel for t in texts if t.panel is not None}))
