"""What is wrong with a figure: each rule's findings, its fix, and the report."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import ClassVar

from .model import Text, panels_of


@dataclass(frozen=True)
class Warn:
    """A finding that spoils the chart."""

    word: ClassVar[str] = "WARNING"

    def __str__(self) -> str:
        """The word a report prints."""
        return self.word


@dataclass(frozen=True)
class Info:
    """A finding that may spoil the chart."""

    word: ClassVar[str] = "INFO"

    def __str__(self) -> str:
        """The word a report prints."""
        return self.word


#: How bad a finding is: a WARNING spoils the chart, an INFO may.
Severity = Warn | Info

#: The usual remedy each rule names.
FIXES: dict[str, str] = {
    "OVERFLOW": "dm.simple_layout(fig) makes room for axis text; move a "
    "fig.text or annotation placed past the plot inward",
    "TEXT_AT_EDGE": "dm.simple_layout(fig) keeps 1 mm by default; a margin of 0 was asked for, or the text was added after the layout: leave room between "
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
        return f"{self.severity} {self.rule}: {self.message}"


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
