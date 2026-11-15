"""The check slice's types: what a drawn figure shows, and what is wrong with it.

Geometry is in display pixels of the figure as drawn. The shell
(``measure.py``) reads every fact once; the rules in ``decide.py`` read only
these types. ``handle`` fields carry the matplotlib artist or Axes a fact
came from, opaque here, so a finding can name what to fix.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise

#: Contact up to this (points) is a touch, not a cover.
TOUCH_PT = 0.5


@dataclass(frozen=True)
class Box:
    """A display-px rectangle."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """The box's width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """The box's height."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Width times height, never negative."""
        return max(self.width, 0.0) * max(self.height, 0.0)

    def overlap(self, other: Box) -> Box:
        """The intersection (empty boxes have no area)."""
        return Box(
            max(self.x0, other.x0),
            max(self.y0, other.y0),
            min(self.x1, other.x1),
            min(self.y1, other.y1),
        )

    def cover(self, other: Box) -> float:
        """The shared area as a share of the smaller box's area."""
        inter = self.overlap(other)
        if inter.width <= 0 or inter.height <= 0:
            return 0.0
        return inter.area / max(min(self.area, other.area), 1e-9)

    def gap(self, other: Box) -> float:
        """How far apart the boxes are (negative: by how much they overlap)."""
        dx = max(self.x0, other.x0) - min(self.x1, other.x1)
        dy = max(self.y0, other.y0) - min(self.y1, other.y1)
        return max(dx, dy)

    def margins(self, outer: Box) -> dict[str, float]:
        """Room between this box and each edge of ``outer`` (negative: past it)."""
        return {
            "left": self.x0 - outer.x0,
            "right": outer.x1 - self.x1,
            "bottom": self.y0 - outer.y0,
            "top": outer.y1 - self.y1,
        }


class Severity(Enum):
    """How bad a finding is: a WARNING spoils the chart, an INFO may."""

    WARNING = "WARNING"
    INFO = "INFO"


class Role(Enum):
    """What a text is in its figure."""

    TITLE = "title"
    AXIS_LABEL = "axis label"
    TICK = "tick label"
    TEXT = "text"
    PANEL_LETTER = "panel letter"
    FIGURE_TEXT = "figure text"


class Axis(Enum):
    """An Axes' x or y axis."""

    X = "x"
    Y = "y"


_NUMBER = re.compile(r"[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?:\D|$))")
#: Longest prefix or suffix a value label may carry ("Total: ", " MWh").
MAX_AFFIX = 12


@dataclass(frozen=True)
class Number:
    """A short label that prints one number, split into its parts."""

    prefix: str
    digits: str
    suffix: str

    @property
    def value(self) -> float:
        """The printed number."""
        return float(self.digits)

    @property
    def decimals(self) -> int:
        """Decimal places printed."""
        mantissa = self.digits.lower().split("e", 1)[0]
        return len(mantissa.split(".", 1)[1]) if "." in mantissa else 0

    @property
    def whole(self) -> bool:
        """A whole number (float noise aside); a printed tiny value is not."""
        v, n = self.value, round(self.value)
        if abs(v - n) > 1e-9 * max(1.0, abs(v)):
            return False
        return not (n == 0 and v != 0 and "e" not in self.digits.lower())

    @property
    def bare_zero(self) -> bool:
        """A plain ``0``: no unit, no decimals."""
        return self.value == 0 and self.decimals == 0 and not self.suffix

    @classmethod
    def parse(cls, text: str) -> Number | None:
        """One number with optional affixes; ``None`` for prose, math, ``Q1``."""
        s = " ".join(text.strip().replace("\u2212", "-").split())
        s = _THOUSANDS.sub("", s)
        if not s or "\\" in s or "\n" in text.strip():
            return None
        if len(s) > 1 and s.startswith("$") and s.endswith("$"):
            return None
        found = list(_NUMBER.finditer(s))
        if len(found) != 1:
            return None
        m = found[0]
        prefix, digits, suffix = s[: m.start()], m.group(0), s[m.end() :]
        if prefix and prefix[-1].isalpha():
            return None  # "Q1", "v2.0": a token, not a value
        if len(prefix.strip()) > MAX_AFFIX or len(suffix.strip()) > MAX_AFFIX:
            return None
        return cls(prefix, digits, suffix.strip())


@dataclass(frozen=True)
class Text:
    """A drawn, non-blank text: its role, panel (``fig.axes`` index) and box."""

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
    def number(self) -> Number | None:
        """The number the text prints, when it is a short value label."""
        return Number.parse(self.text)


@dataclass(frozen=True)
class TickRow:
    """The drawn labels of one axis and what the layout measured of them.

    ``need`` is the length the labels need along the axis to clear each
    other (``None``: not measurable); ``closest`` the least gap between
    neighbours in ems; ``overlaps`` the neighbour pairs that collide and
    ``deepest`` the worst overlap in px. ``names`` when the labels belong
    to their positions (categories) rather than to a formatter.
    """

    handle: object
    panel: int
    axis: Axis
    labels: tuple[Text, ...]
    span: float
    need: float | None
    closest: float | None
    overlaps: int
    deepest: float
    names: bool
    labelled: bool
    labelled_elsewhere: bool


@dataclass(frozen=True)
class Corner:
    """x and y tick labels of one plot box that meet at a corner."""

    panel: int
    pairs: int
    depth: float
    x_label: Text
    y_label: Text
    corner: str


@dataclass(frozen=True)
class Hit:
    """One thing a box covers: its kind (bar, line, text ...) and name."""

    kind: str
    name: str


@dataclass(frozen=True)
class Legend:
    """A drawn legend: its box, owner Axes box and what its box covers.

    ``panel`` is ``None`` for a figure legend; ``plot`` is its Axes' plot
    box, or the summed panel area as a box of that area for a figure legend.
    """

    handle: object
    panel: int | None
    box: Box
    labels: tuple[str, ...]
    plot: Box | None
    panels_area: float
    covers: tuple[Hit, ...]

    @property
    def panels(self) -> tuple[int, ...]:
        """The legend's Axes, none for a figure legend."""
        return () if self.panel is None else (self.panel,)

    def spill(self, canvas: Box) -> float:
        """How far the legend runs past the canvas (negative: inside)."""
        return -min(self.box.margins(canvas).values())

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
class ValueLabel:
    """A value label inside an Axes and the data its ink covers."""

    text: Text
    covers: tuple[Hit, ...]


@dataclass(frozen=True)
class Contrast:
    """A text's ink against the background it is drawn on (WCAG ratio)."""

    text: Text
    ratio: float
    large: bool
    ink: str
    paper: str


@dataclass(frozen=True)
class Panel:
    """A drawn Axes: its plot box and whether it draws anything."""

    handle: object
    index: int
    box: Box
    empty: bool


@dataclass(frozen=True)
class Facts:
    """Everything the rules read from one drawn figure."""

    canvas: Box
    px_per_pt: float
    texts: tuple[Text, ...] = ()
    figure_texts: tuple[Text, ...] = ()
    ticks: tuple[TickRow, ...] = ()
    corners: tuple[Corner, ...] = ()
    legends: tuple[Legend, ...] = ()
    values: tuple[ValueLabel, ...] = ()
    contrast: tuple[Contrast, ...] = ()
    panels: tuple[Panel, ...] = ()
    content: Box | None = None
    skipped: tuple[str, ...] = ()

    @property
    def touch(self) -> float:
        """:data:`TOUCH_PT` in px."""
        return TOUCH_PT * self.px_per_pt

    def edge_groups(self, low: float, high: float) -> dict[str, list[Text]]:
        """Texts whose room to their nearest canvas edge is in [low, high)."""
        groups: dict[str, list[Text]] = {}
        for t in self.all_texts:
            side, room = min(
                t.box.margins(self.canvas).items(), key=lambda s: s[1]
            )
            if low <= room < high:
                groups.setdefault(side, []).append(t)
        return groups

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
        """Axes texts, tick labels and figure texts."""
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


def step_decimals(values: Iterable[float]) -> int:
    """Decimals the smallest step between the values needs, at most four."""
    finite = sorted({v for v in values if math.isfinite(v)})
    steps = [b - a for a, b in pairwise(finite) if b - a > 0]
    if not steps:
        return 0
    return min(4, max(0, math.ceil(-math.log10(min(steps)) - 1e-9)))


# ------------------------------------------------------------------ findings
#: The usual remedy each rule names.
FIXES: dict[str, str] = {
    "OVERFLOW": "dm.simple_layout(fig) makes room for axis text; move a "
    "fig.text or annotation placed past the plot inward",
    "TEXT_AT_EDGE": 'dm.simple_layout(fig, margin="1mm") leaves room between '
    "the text and the canvas edge",
    "OVERLAP": "move or shorten one of them; dm.simple_layout(fig) spaces "
    "titles, axis labels and tick labels",
    "CROSS_AXES_OVERLAP": "dm.simple_layout(fig) spaces the panels; a "
    "spacing you set (hspace, wspace): raise it",
    "TEXT_CROWD": "put the value on the other side of its point "
    "(dm.annotate_value picks a free side) or a line apart",
    "LEGEND_OVERFLOW": "many lines: dm.label_line_ends(ax); else shorter "
    "names or dm.place_legend(ax, loc='above')",
    "LEGEND_OVERLAP": "dm.place_legend(ax), then dm.simple_layout(fig) keeps "
    "titles and labels clear of it",
    "LEGEND_ON_DATA": "dm.place_legend(ax) moves it where it covers nothing, "
    "else outside; panels sharing series: dm.figure_legend(fig)",
    "VALUE_LABEL_ON_DATA": "bars: dm.label_bars(ax); a point's value: "
    "dm.annotate_value(ax, x, y, text) puts it on a free side",
    "VALUE_LABEL_DECIMAL": "print whole numbers bare: dm.label_bars(ax) "
    "does, or f'{value:,.0f}'",
    "TICK_OVERLAP": "dm.simple_layout(fig) wraps, then turns, crowded "
    "labels (drop a rotation you set); many long names: horizontal bars; "
    "a y axis: a taller canvas",
    "TICK_CROWD": "numbers: fewer ticks, ax.locator_params(nbins=5); "
    "names: fewer categories, a larger canvas or horizontal bars",
    "TICK_CORNER_OVERLAP": "dm.simple_layout(fig) moves one axis' labels "
    "out; pads you set: ax.tick_params(axis='x', pad=...)",
    "TICK_DECIMAL": "dm.set_decimal(ax, ...) with the decimals the tick step "
    "needs; dm.format_axis_* print whole numbers bare",
    "MISSING_AXIS_LABEL": "name the quantity and unit: "
    "ax.set_ylabel('Revenue (M USD)')",
    "TEXT_CONTRAST": "a darker ink, or dm.readable_text_color(background)",
    "EMPTY_AXES": "ax.remove(), or ax.set_visible(False) to keep the grid",
    "MARGIN_ASYMMETRY": "dm.simple_layout(fig) centres the content",
}


@dataclass(frozen=True)
class Finding:
    """One defect: the rule that found it, how bad, what, and how to fix it."""

    rule: str
    severity: Severity
    message: str
    fix: str
    artists: tuple[object, ...] = ()
    panels: tuple[int, ...] = ()

    def __str__(self) -> str:
        """``WARNING OVERLAP: message``."""
        return f"{self.severity.value} {self.rule}: {self.message}"


@dataclass(frozen=True)
class Findings:
    """Every finding of one check, and the rules that could not run."""

    items: tuple[Finding, ...] = ()
    skipped: tuple[str, ...] = field(default=())

    def __iter__(self) -> Iterator[Finding]:
        """The findings in rule order."""
        return iter(self.items)

    def __len__(self) -> int:
        """How many findings."""
        return len(self.items)

    def __bool__(self) -> bool:
        """True when anything was found or a rule could not run."""
        return bool(self.items or self.skipped)

    def add(self, *found: Finding) -> Findings:
        """These findings with ``found`` appended."""
        return Findings((*self.items, *found), self.skipped)

    def flag(
        self,
        rule: str,
        severity: Severity,
        message: str,
        texts: Iterable[Text] = (),
        *,
        handles: tuple[object, ...] = (),
        panels: tuple[int, ...] | None = None,
    ) -> Findings:
        """These findings and one more of ``rule``, with its fix.

        The finding names ``handles`` and the texts' artists; its panels
        are ``panels``, else the texts'.
        """
        texts = tuple(texts)
        artists = (*handles, *(t.handle for t in texts))
        where = panels_of(texts) if panels is None else panels
        return self.add(
            Finding(rule, severity, message, FIXES[rule], artists, where)
        )

    def of(self, rule: str) -> tuple[Finding, ...]:
        """The findings of one rule."""
        return tuple(f for f in self.items if f.rule == rule)

    @property
    def rules(self) -> tuple[str, ...]:
        """The rules that found something, once each, in order."""
        return tuple(dict.fromkeys(f.rule for f in self.items))

    def report(self) -> str:
        """A compact text report: one line per finding, its fix indented."""
        if not self:
            return "dm.check: no defects found."
        n = len(self.items)
        lines = [f"dm.check: {n} finding{'s' * (n != 1)}"]
        for f in self.items:
            lines.append(str(f))
            lines.append(f"  fix: {f.fix}")
        if self.skipped:
            lines.append(
                f"NOT RUN: {', '.join(self.skipped)} (could not measure; "
                "the figure is not proven clean)"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        """The text report."""
        return self.report()
