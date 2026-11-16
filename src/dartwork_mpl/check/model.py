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

from ..vocab import Box, Which, X, Y
from .roles import Role

#: Contact up to this (points) is a touch, not a cover.
TOUCH_PT = 0.5

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


def prints_a_value(text: str) -> bool:
    """A short label printing one number (``19.4 TWh``, ``$3.5``), not prose,
    math or a token like ``Q1``."""
    s = _THOUSANDS.sub(
        "", " ".join(text.strip().replace("\u2212", "-").split())
    )
    if not s or "\\" in s or "\n" in text.strip():
        return False
    if len(s) > 1 and s.startswith("$") and s.endswith("$"):
        return False
    found = list(_NUMBER.finditer(s))
    if len(found) != 1:
        return False
    prefix, suffix = s[: found[0].start()], s[found[0].end() :]
    if prefix and prefix[-1].isalpha():
        return False
    return len(prefix.strip()) <= MAX_AFFIX and len(suffix.strip()) <= MAX_AFFIX


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
    def value(self) -> bool:
        """The text prints one number: a value label."""
        return prints_a_value(self.text)


@dataclass(frozen=True)
class TickRow:
    """The drawn labels of one axis and how many neighbours collide.

    ``overlaps`` the neighbour pairs that collide and ``deepest`` the worst
    overlap in px.
    """

    handle: object
    panel: int
    axis: Which
    labels: tuple[Text, ...]
    overlaps: int
    deepest: float


@dataclass(frozen=True)
class Hit:
    """One thing a box covers: its kind (bar, line, text ...) and name."""

    kind: str
    name: str


@dataclass(frozen=True)
class Legend:
    """A drawn legend: its owner panel (``None``: a figure legend) and what
    its box covers."""

    handle: object
    panel: int | None
    labels: tuple[str, ...]
    covers: tuple[Hit, ...]

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
class Facts:
    """Everything the rules read from one drawn figure."""

    canvas: Box
    px_per_pt: float
    texts: tuple[Text, ...] = ()
    figure_texts: tuple[Text, ...] = ()
    ticks: tuple[TickRow, ...] = ()
    legends: tuple[Legend, ...] = ()
    skipped: tuple[str, ...] = ()

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
