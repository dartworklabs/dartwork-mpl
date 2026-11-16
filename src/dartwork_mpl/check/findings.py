"""What is wrong with a figure: each rule's findings, its fix, and the report."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import ClassVar

from .model import Text, panels_of

#: The usual remedy each rule names.
FIXES: dict[str, str] = {
    "OVERFLOW": "dm.simple_layout(fig) makes room for axis text; move a "
    "fig.text or annotation placed past the plot inward",
    "OVERLAP": "move or shorten one of them; dm.simple_layout(fig) spaces "
    "titles, axis labels and tick labels",
    "CROSS_AXES_OVERLAP": "dm.simple_layout(fig) spaces the panels; a "
    "spacing you set (hspace, wspace): raise it",
    "TEXT_CROWD": "put the value on the other side of its point "
    "(dm.annotate_value picks a free side) or a line apart",
    "VALUE_LABEL_DECIMAL": 'print whole numbers whole: fmt="%d" or "{:,.0f}"',
    "LEGEND_ON_DATA": "dm.place_legend(ax) moves it where it covers nothing, "
    "else outside; panels sharing series: dm.figure_legend(fig)",
    "MISSING_AXIS_LABEL": "name the quantity and its unit: "
    'ax.set_ylabel("Revenue (M USD)"); a colorbar: cbar.set_label(...)',
    "EMPTY_AXES": "ax.remove() the panel the data does not fill, or make "
    "the grid as large as the data",
    "VALUE_LABEL_ON_DATA": "move the label off the line: a padding past "
    "the error bar (ax.bar_label(bars, padding=...)), or dm.annotate_value "
    "for a point on a line",
    "TEXT_CONTRAST": "colour each label for what is behind it: "
    "color=dm.readable_text_color(bar_colour), or "
    "dm.ensure_contrast(colour, background)",
    "TICK_OVERLAP": "dm.simple_layout(fig) wraps, then turns, crowded "
    "labels (drop a rotation you set); many long names: horizontal bars; "
    "a y axis: a taller canvas",
}


@dataclass(frozen=True)
class Finding:
    """One defect: the rule that found it, what, and how to fix it."""

    #: How bad: every rule reports a defect that spoils the chart.
    severity: ClassVar[str] = "WARNING"

    rule: str
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

    def flag(
        self,
        rule: str,
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
        found = Finding(rule, message, FIXES[rule], artists, where)
        return Findings((*self.items, found), self.skipped)

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
