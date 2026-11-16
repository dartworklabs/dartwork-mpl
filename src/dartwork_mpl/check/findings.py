"""Where to look in a figure: each rule's findings, what to try, and the report."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import ClassVar

from .model import Text, panels_of

#: What usually helps, for each rule that does not name its own fix. A
#: finding may be what the author meant.
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
    "LEGEND_ON_DATA": "dm.place_legend(ax) picks the place that covers "
    'least; no free place: dm.place_legend(ax, loc="above"); panels '
    "sharing series: dm.figure_legend(fig)",
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
    "SMALL_PANEL": "fewer panels per figure (one row, or split it into "
    'figures); a grid on a slide: dm.figsize_for("full_slide") and one '
    "axis name per row or column (sharex=True, sharey=True)",
}


@dataclass(frozen=True)
class Finding:
    """One place to look: the rule that points at it, what it saw, and what
    usually helps (``fix``)."""

    #: Every rule points at something a reader would stumble on.
    severity: ClassVar[str] = "WARNING"

    rule: str
    message: str
    fix: str
    artists: tuple[object, ...] = ()
    panels: tuple[int, ...] = ()

    def __str__(self) -> str:
        """``OVERLAP: message``."""
        return f"{self.rule}: {self.message}"


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
        fix: str | None = None,
    ) -> Findings:
        """These findings and one more of ``rule``, with its fix.

        The finding names ``handles`` and the texts' artists; its panels
        are ``panels``, else the texts'; its fix is ``fix``, else the rule's
        in :data:`FIXES`.
        """
        texts = tuple(texts)
        artists = (*handles, *(t.handle for t in texts))
        where = panels_of(texts) if panels is None else panels
        tried = FIXES[rule] if fix is None else fix
        found = Finding(rule, message, tried, artists, where)
        return Findings((*self.items, found), self.skipped)

    @property
    def rules(self) -> tuple[str, ...]:
        """The rules that found something, once each, in order."""
        return tuple(dict.fromkeys(f.rule for f in self.items))

    def report(self) -> str:
        """A compact text report: one line per finding, what to try indented."""
        if not self:
            return "dm.check: nothing stands out."
        n = len(self.items)
        lines = [f"dm.check: {n} place{'s' * (n != 1)} to look at"]
        for f in self.items:
            lines.append(str(f))
            lines.append(f"  try: {f.fix}")
        if self.skipped:
            lines.append(
                f"NOT RUN: {', '.join(self.skipped)} (could not measure "
                "this figure, so look at it yourself)"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        """The text report."""
        return self.report()
