"""The rules: what in the measured facts makes a chart ugly or unreadable.

Each rule reads :class:`Facts` and appends its findings (the fix each rule
names is ``findings.FIXES``). They are listed, named and ordered in
``edges.py``; nothing here touches a figure.
"""

from __future__ import annotations

from itertools import combinations

from ..colorspace import Ratio
from .findings import Findings
from .model import Facts, Hit, Inked, OnData, Text, margins, quote

#: A text further past the canvas edge than this (px) is cut off.
CUT_PX = 1.0
#: Two texts sharing this share of the smaller box overlap.
COVER = 0.05
#: A number and a name on one row closer than this (em) read as one phrase.
PHRASE_GAP_EM = 1.0
#: Text fainter than this on what is behind it disappears (WCAG large text).
MIN_CONTRAST = Ratio(3.0)


def overflow(facts: Facts, found: Findings) -> Findings:
    """Texts cut off by the canvas edge, grouped by edge."""
    cut: dict[str, list[tuple[Text, float]]] = {}
    for t in facts.all_texts:
        side, room = min(
            margins(t.box, facts.canvas).items(), key=lambda s: s[1]
        )
        if room < -CUT_PX:
            cut.setdefault(side, []).append((t, -room))
    for side, group in cut.items():
        found = found.flag(
            "OVERFLOW",
            f"Cut off at the {side} edge: {quote(t.short for t, _ in group)} "
            f"(up to {max(past for _, past in group):.1f}px past it)",
            [t for t, _ in group],
        )
    return found


def overlap(facts: Facts, found: Findings) -> Findings:
    """Texts of one Axes drawn over each other (tick pairs: TICK_OVERLAP)."""
    for panel, texts in facts.by_panel.items():
        for a, b in combinations(texts, 2):
            if a.role.tick and b.role.tick:
                continue
            share = a.box.cover(b.box)
            if share > COVER:
                found = found.flag(
                    "OVERLAP",
                    f"Axes[{panel}]: {a.role} {a.short!r} overlaps "
                    f"{b.role} {b.short!r} ({share:.0%} of the smaller)",
                    (a, b),
                )
    return found


def cross_axes(facts: Facts, found: Findings) -> Findings:
    """Titles, axis labels, letters and ticks of different Axes colliding."""
    texts = [
        t for group in facts.by_panel.values() for t in group if not t.role.free
    ]
    seen: set[tuple[object, ...]] = set()
    for a, b in combinations(texts, 2):
        if a.panel == b.panel or a.box.cover(b.box) < COVER:
            continue
        one, two = sorted((a, b), key=lambda t: (t.panel or 0, str(t.role)))
        key = (one.panel, two.panel, one.role, two.role)
        if key not in seen:
            seen.add(key)
            found = found.flag(
                "CROSS_AXES_OVERLAP",
                f"axes[{one.panel}] {one.role} {one.short!r} overlaps "
                f"axes[{two.panel}] {two.role} {two.short!r}",
                (one, two),
            )
    return found


def phrase(facts: Facts, found: Findings) -> Findings:
    """A value label beside a name on one row, near enough to read as one."""
    for panel, texts in facts.by_panel.items():
        free = [t for t in texts if t.role.free]
        for a, b in combinations(free, 2):
            if a.value == b.value:
                continue
            rows = min(a.box.y1, b.box.y1) - max(a.box.y0, b.box.y0)
            if rows < 0.5 * min(a.box.height, b.box.height):
                continue
            gap = max(a.box.x0, b.box.x0) - min(a.box.x1, b.box.x1)
            em = max(a.em, b.em)
            if -facts.touch <= gap < PHRASE_GAP_EM * em:
                found = found.flag(
                    "TEXT_CROWD",
                    f"Axes[{panel}]: {a.short!r} and {b.short!r} sit "
                    f"{gap / em:.2f} em apart on one row: they read as one",
                    (a, b),
                )
    return found


def value_label_decimal(facts: Facts, found: Findings) -> Findings:
    """An Axes whose value labels all print whole numbers as ``12.0``."""
    for panel, texts in facts.by_panel.items():
        values = [t for t in texts if t.role.free and t.value]
        if len(values) > 1 and all(t.needless_decimals for t in values):
            found = found.flag(
                "VALUE_LABEL_DECIMAL",
                f"Axes[{panel}]: whole numbers printed with decimals "
                f"({quote(t.short for t in values)})",
                values,
            )
    return found


def legend_on_data(facts: Facts, found: Findings) -> Findings:
    """A legend over data, a text or an earlier legend."""
    for i, leg in enumerate(facts.legends):
        covers = [
            *leg.covers,
            *(
                Hit(str(t.role), t.short)
                for t in facts.under_legends
                if leg.box.cover(t.box) > COVER
            ),
            *(
                Hit("legend", other.name)
                for other in facts.legends[:i]
                if leg.box.cover(other.box) > COVER
            ),
        ]
        if covers:
            kinds = sorted({h.kind for h in covers})
            found = found.flag(
                "LEGEND_ON_DATA",
                f"{leg.name} covers {', '.join(k + 's' for k in kinds)} "
                f"({quote(h.name for h in covers)})",
                handles=(leg.handle,),
                panels=leg.panels,
            )
    return found


def tick_overlap(facts: Facts, found: Findings) -> Findings:
    """Neighbouring tick labels of one axis drawn on each other."""
    for row in facts.ticks:
        if row.overlaps:
            found = found.flag(
                "TICK_OVERLAP",
                f"Axes[{row.panel}] {row.axis.letter} axis: {row.overlaps} "
                f"pair(s) of tick labels overlap (up to {row.deepest:.1f}px)",
                handles=(row.handle,),
                panels=(row.panel,),
            )
    return found


def empty_axes(facts: Facts, found: Findings) -> Findings:
    """A framed Axes that draws nothing: a grid larger than the data."""
    for p in facts.empty:
        found = found.flag(
            "EMPTY_AXES",
            f"Axes[{p.index}] draws nothing: an empty frame",
            handles=(p.handle,),
            panels=(p.index,),
        )
    return found


def missing_axis_label(facts: Facts, found: Findings) -> Findings:
    """An axis of numbers that nothing names, on a panel that draws."""
    empty = {p.index for p in facts.empty}
    for row in facts.ticks:
        if row.numbers and not row.named and row.panel not in empty:
            found = found.flag(
                "MISSING_AXIS_LABEL",
                f"Axes[{row.panel}]: the {row.axis.letter} axis prints "
                "numbers but nothing names them",
                handles=(row.handle,),
                panels=(row.panel,),
            )
    return found


def value_label_on_data(facts: Facts, found: Findings) -> Findings:
    """Value labels drawn on a line, a marker or an error bar, per Axes."""
    panels: dict[int | None, list[OnData]] = {}
    for v in facts.values:
        panels.setdefault(v.text.panel, []).append(v)
    for panel, on in panels.items():
        kinds = sorted({h.kind for v in on for h in v.covers})
        found = found.flag(
            "VALUE_LABEL_ON_DATA",
            f"Axes[{panel}]: {len(on)} value label(s) sit on "
            f"{', '.join(k + 's' for k in kinds)} (first {on[0].text.short!r})",
            [v.text for v in on],
        )
    return found


def text_contrast(facts: Facts, found: Findings) -> Findings:
    """Texts the user placed, fainter than 3:1 on what is behind them."""
    panels: dict[int | None, list[Inked]] = {}
    for c in facts.inks:
        if c.ratio.value < MIN_CONTRAST.value:
            panels.setdefault(c.text.panel, []).append(c)
    for panel, faint in panels.items():
        w = min(faint, key=lambda c: c.ratio.value)
        found = found.flag(
            "TEXT_CONTRAST",
            f"Axes[{panel}]: {len(faint)} text(s) under 3:1 on what is "
            f"behind them, worst {w.ink} on {w.paper} at "
            f"{w.ratio.value:.2f}:1 ({quote(c.text.short for c in faint)})",
            [c.text for c in faint],
        )
    return found
