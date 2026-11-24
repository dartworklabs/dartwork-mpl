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
    "TEXT_AT_EDGE": "move the text inward by a millimetre or two, or give "
    "its annotation an inward offset in points",
    "OVERLAP": "move or shorten one of them; dm.simple_layout(fig) spaces "
    "titles, axis labels and tick labels",
    "CROSS_AXES_OVERLAP": "dm.simple_layout(fig) spaces the panels; a "
    "spacing you set (hspace, wspace): raise it",
    "TEXT_TOO_CLOSE": "give the texts some air: move one, or use "
    "ax.annotate(..., textcoords='offset points', xytext=(0, -8))",
    "TEXT_CROWD": "put the value on the other side of its point "
    "(dm.annotate_value picks a free side) or a line apart",
    "VALUE_LABEL_DECIMAL": 'print whole numbers whole: fmt="%d" or "{:,.0f}"',
    "LEGEND_ON_DATA": "dm.place_legend(ax) picks the place that covers "
    'least; no free place: dm.place_legend(ax, loc="above"); panels '
    "sharing series: dm.figure_legend(fig)",
    "EMPTY_AXES": "check the view limits, colour and alpha; for a line, "
    "give it a positive linewidth or a visible marker. An unused grid "
    "cell can be removed with ax.remove()",
    "MATPLOTLIB_COLORMAP": "pick a dc. map for the kind of data and the "
    "look you want; dm.list_colors(kind) lists them all. Ordered: one hue "
    '("sequential", 20 maps: dc.blue, dc.teal, dc.amber ...) or several '
    '("multi-hue": dc.aurora, dc.glacier, dc.lava ...); signed around a '
    'centre: "diverging" (dc.blue_red, dc.teal_amber, dc.purple_orange ...); '
    "cyclic: dc.hue, dc.halo, dc.corona. Keep a matplotlib map only when "
    "the user asked for it",
    "VALUE_LABEL_ON_DATA": "move the label off the line: a padding past "
    "the error bar (ax.bar_label(bars, padding=...)), or dm.annotate_value "
    "for a point on a line",
    "TEXT_ON_LINE": "move the text off the line: the other side of its "
    "point, or an offset in points (ax.annotate(..., xytext=(6, 6), "
    "textcoords='offset points')); a text that names the line can sit at "
    "its end",
    "LETTER_ON_DATA": "the letters went inside the plots because a letter "
    "and its title were wider than the plot: shorten the titles or widen "
    "the figure so each letter goes before its title; or leave room in "
    "that corner (ax.set_ylim)",
    "TEXT_CONTRAST": "move a text off a band too thin to hold it, or one "
    "that runs over several backgrounds onto one; else dm.legible(texts) "
    "after dm.simple_layout(fig) gives each the colour that reads there, "
    "an outline where no one colour does; labels you colour yourself: "
    "color=dm.readable_text_color(bar_colour)",
    "RADIAL_TICK_COVERED": "raise the radial labels above the fill with "
    "ax.set_axisbelow(False), or move them to a clear angle with ax.set_rlabel_position(...)",
    "POLAR_TICK_ON_PLOT": "dm.simple_layout(fig) aligns centred angle "
    "labels away from the plot; labels you aligned or turned yourself: "
    'more room with ax.tick_params(axis="x", pad=...)',
    "MIXED_MINUS": "format the numeric label with "
    'matplotlib.ticker.Formatter.fix_minus(...) or .replace("-", "\u2212")',
    "TICK_OVERLAP": "dm.simple_layout(fig) wraps, then turns, crowded "
    "labels (drop a rotation you set); many long names: horizontal bars; "
    "a y axis: a taller canvas",
    "UNDERUSED_CANVAS": "match the canvas to the content with dm.figsize(width, aspect), "
    "or use ax.set_aspect('auto') if the shapes can stretch, then rerun dm.simple_layout(fig)",
    "VALUE_LABEL_ADRIFT": "a label belongs to the mark it stands nearest: "
    "put each value at the end of its own bar (ax.bar_label(bars, "
    "padding=3)), or leave more room between the cells than between a bar "
    "and its value",
    "BAND_OFF_CENTRE": "centre the band on the marks: the same distance "
    "from their line to both of its edges (half the row pitch each way)",
    "UNEVEN_OUTLINE": "give the bars that touch the same outline (the same "
    "linewidth, each in its own colour: edgecolor=its facecolor), or drop "
    "the outline (linewidth=0)",
    "TEXT_BOX_ON_DATA": "a box hides the marks under it: draw the text "
    "without the box and check again. A text that then does not read is "
    "reported as TEXT_CONTRAST, and dm.legible(texts) gives it an outline, "
    "which hides less; or move the text onto one background",
    "CONNECTOR_SHORT": "draw the marks a line must meet without that "
    "outline (linewidth=0, a gap in the data to separate them) or outlined "
    "in their own colour (edgecolor=facecolor)",
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
