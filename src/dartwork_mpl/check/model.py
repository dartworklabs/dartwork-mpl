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

from ..colorspace import Hex, Ratio
from ..vocab import Box, HAlign, Which, X, Y
from .roles import Role

#: Contact up to this (points) is a touch, not a cover.
TOUCH_PT = 0.5

#: Air (pt) a panel letter inside its plot keeps from the data.
LETTER_CLEARANCE_PT = 2.0

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
    """A value label or a panel letter and the data under it."""

    text: Text
    covers: tuple[Hit, ...]


@dataclass(frozen=True)
class Inked:
    """A text the user placed, its colour and what is drawn behind it."""

    text: Text
    ink: Hex
    paper: Hex
    ratio: Ratio


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
class TickOcclusion:
    """A drawn tick label and the mean opacity of the fill covering its box."""

    label: Text
    opacity: float


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
    inks: tuple[Inked, ...] = ()
    skipped: tuple[str, ...] = ()
    frames: tuple[Frame, ...] = ()
    insets: tuple[Inset, ...] = ()
    polar_theta: tuple[PolarTheta, ...] = ()
    minus_labels: tuple[Text, ...] = ()
    minus_tick: Text | None = None
    alignment: tuple[tuple[AlignmentSample, ...], ...] = ()
    occluded_ticks: tuple[TickOcclusion, ...] = ()

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
