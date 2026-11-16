"""The rules: what in the measured facts makes a chart ugly or unreadable.

Each rule reads :class:`Facts` and appends its findings (the fix each rule
names is ``findings.FIXES``). They are listed, named and ordered in
``edges.py``; nothing here touches a figure.
"""

from __future__ import annotations

from itertools import combinations

from .findings import Findings
from .model import Facts, Text, margins, quote

#: A text further past the canvas edge than this (px) is cut off.
CUT_PX = 1.0
#: Two texts sharing this share of the smaller box overlap.
COVER = 0.05
#: A number and a name on one row closer than this (em) read as one phrase.
PHRASE_GAP_EM = 1.0


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


def legend_on_data(facts: Facts, found: Findings) -> Findings:
    """A legend over data, a text, another legend or another panel."""
    for leg in facts.legends:
        if leg.covers:
            kinds = sorted({h.kind for h in leg.covers})
            found = found.flag(
                "LEGEND_ON_DATA",
                f"{leg.name} covers {', '.join(k + 's' for k in kinds)} "
                f"({quote(h.name for h in leg.covers)})",
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
