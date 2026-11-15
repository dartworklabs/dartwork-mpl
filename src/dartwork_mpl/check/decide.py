"""The rules: what in the measured facts makes a chart ugly or unreadable.

Each rule reads :class:`Facts` and appends its findings (the fix each rule
names is ``findings.FIXES``). They are listed, named and ordered in
``edges.py``; nothing here touches a figure.
"""

from __future__ import annotations

import math
from itertools import combinations, pairwise

from .findings import Findings, Info, Warn
from .model import Facts, Number, Text, TickRow, margins, quote, step_decimals
from .roles import Role

WARN, INFO = Warn(), Info()

#: A text further past the canvas edge than this (px) is cut off.
CUT_PX = 1.0
#: A text nearer the canvas edge than this (pt) touches it: glyphs that
#: overhang their box (the arm of an ``r``) are cut.
EDGE_ROOM_PT = 1.0
#: Two texts sharing this share of the smaller box overlap.
COVER = 0.05
#: A number and a name on one row closer than this (em) read as one phrase.
PHRASE_GAP_EM = 1.0
LEGEND_SHARE = 0.30  # an inside legend covering more of its plot is too big
LEGEND_OUTSIDE = 0.50  # an outside legend bigger than this share of its plot
SPILL_PX = 2.0
CROWD_GAP = 0.15  # room the tick labels need beyond their own, share
CROWD_EM = 0.5  # neighbours closer than this crowd the axis
NORMAL_AA, LARGE_AA = 4.5, 3.0
MARGIN_RATIO, MARGIN_MIN_PX = 3.0, 30.0


# ---------------------------------------------------------------- canvas
def overflow(facts: Facts, found: Findings) -> Findings:
    """Texts cut off by the canvas edge, grouped by edge."""
    for side, cut in facts.edge_groups(-math.inf, -CUT_PX).items():
        worst = max(-min(margins(t.box, facts.canvas).values()) for t in cut)
        found = found.flag(
            "OVERFLOW",
            WARN,
            f"Cut off at the {side} edge: {quote(t.short for t in cut)} "
            f"(up to {worst:.1f}px past it)",
            cut,
        )
    return found


def at_edge(facts: Facts, found: Findings) -> Findings:
    """Texts flush against the canvas edge (not past it): one finding.

    An INFO: ``dm.simple_layout``'s default ``margin=0`` puts the outermost
    text of every figure flush, so this names the layout's default, which
    only a margin the user picks changes.
    """
    flush = facts.edge_groups(-CUT_PX, EDGE_ROOM_PT * facts.px_per_pt)
    if not flush:
        return found
    where = "; ".join(
        f"{s}: {quote(t.short for t in g)}" for s, g in flush.items()
    )
    return found.flag(
        "TEXT_AT_EDGE",
        INFO,
        f"Text flush against the canvas edge, glyphs that overhang are cut "
        f"({where})",
        [t for g in flush.values() for t in g],
    )


def margin_asymmetry(facts: Facts, found: Findings) -> Findings:
    """Whitespace on one side much larger than on the opposite side."""
    if facts.content is None:
        return found
    m = margins(facts.content, facts.canvas)
    for a, b in (("left", "right"), ("bottom", "top")):
        low, high = sorted((max(m[a], 0.0), max(m[b], 0.0)))
        if low > MARGIN_MIN_PX and high / low > MARGIN_RATIO:
            wide = a if m[a] > m[b] else b
            found = found.flag(
                "MARGIN_ASYMMETRY",
                WARN,
                f"The {wide} margin is {high / low:.1f}x the opposite one "
                f"({a}={m[a]:.0f}px, {b}={m[b]:.0f}px)",
            )
    return found


# ------------------------------------------------------------------ text
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
                    WARN,
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
        one, two = sorted((a, b), key=lambda t: (t.panel or 0, t.role.word))
        key = (one.panel, two.panel, one.role, two.role)
        if key not in seen:
            seen.add(key)
            found = found.flag(
                "CROSS_AXES_OVERLAP",
                WARN,
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
            if (a.number is None) == (b.number is None):
                continue
            rows = min(a.box.y1, b.box.y1) - max(a.box.y0, b.box.y0)
            if rows < 0.5 * min(a.box.height, b.box.height):
                continue
            gap = max(a.box.x0, b.box.x0) - min(a.box.x1, b.box.x1)
            em = max(a.em, b.em)
            if -facts.touch <= gap < PHRASE_GAP_EM * em:
                found = found.flag(
                    "TEXT_CROWD",
                    WARN,
                    f"Axes[{panel}]: {a.short!r} and {b.short!r} sit "
                    f"{gap / em:.2f} em apart on one row: they read as one",
                    (a, b),
                )
    return found


def missing_axis_label(facts: Facts, found: Findings) -> Findings:
    """A numeric axis whose numbers have no name or unit anywhere."""
    for row in facts.ticks:
        if not (row.names or row.labelled or row.labelled_elsewhere):
            found = found.flag(
                "MISSING_AXIS_LABEL",
                INFO,
                f"Axes[{row.panel}]: the {row.axis.letter} axis has numbers "
                "but no label naming them",
                handles=(row.handle,),
                panels=(row.panel,),
            )
    return found


def contrast(facts: Facts, found: Findings) -> Findings:
    """Text too faint on what it is drawn over (WCAG AA), by colour pair."""
    groups: dict[tuple[str, str, bool], list[Text]] = {}
    worst: dict[tuple[str, str, bool], float] = {}
    for c in facts.contrast:
        if c.ratio < (LARGE_AA if c.large else NORMAL_AA):
            key = (c.ink, c.paper, c.large)
            groups.setdefault(key, []).append(c.text)
            worst[key] = min(worst.get(key, math.inf), c.ratio)
    for (ink, paper, large), texts in list(groups.items())[:6]:
        ratio = worst[(ink, paper, large)]
        found = found.flag(
            "TEXT_CONTRAST",
            WARN if ratio < LARGE_AA else INFO,
            f"{ink} text on {paper} has contrast {ratio:.2f}:1, under "
            f"{LARGE_AA if large else NORMAL_AA:g}:1: "
            f"{quote(t.short for t in texts)}",
            texts,
        )
    return found


# ---------------------------------------------------------------- legend
def legend_overflow(facts: Facts, found: Findings) -> Findings:
    """A legend too big for its plot, or one running off the canvas."""
    for leg in facts.legends:
        spill = leg.spill(facts.canvas)
        area = leg.plot.area if leg.plot is not None else leg.panels_area
        inside = leg.box.overlap(leg.plot).area if leg.plot else 0.0
        if leg.panel is not None and area and inside / area > LEGEND_SHARE:
            message = f"{leg.name} covers {inside / area:.0%} of its plot"
        elif spill > SPILL_PX:
            message = f"{leg.name} runs {spill:.0f}px past the canvas edge"
        elif area and leg.box.area > LEGEND_OUTSIDE * area:
            message = (
                f"{leg.name} is {leg.box.area / area:.0%} the size of the "
                "plot it serves"
            )
        else:
            continue
        found = found.flag(
            "LEGEND_OVERFLOW",
            WARN,
            message,
            handles=(leg.handle,),
            panels=leg.panels,
        )
    return found


def legend_overlap(facts: Facts, found: Findings) -> Findings:
    """A legend over a title, axis label, tick label or figure text."""
    targets = [t for t in facts.all_texts if t.role.under_legend]
    for leg in facts.legends:
        hit: dict[tuple[int | None, Role], list[Text]] = {}
        for t in targets:
            inter = leg.box.overlap(t.box)
            if inter.width > 1.0 and inter.height > 1.0:
                hit.setdefault((t.panel, t.role), []).append(t)
        for (panel, role), texts in hit.items():
            owner = "the figure" if panel is None else f"axes[{panel}]"
            found = found.flag(
                "LEGEND_OVERLAP",
                WARN,
                f"{leg.name} covers {len(texts)} {role}(s) of {owner} "
                f"({quote(t.short for t in texts)})",
                texts,
                handles=(leg.handle,),
            )
    return found


def legend_on_data(facts: Facts, found: Findings) -> Findings:
    """A legend over data, a text, another legend or another panel."""
    for leg in facts.legends:
        if leg.covers:
            kinds = sorted({h.kind for h in leg.covers})
            found = found.flag(
                "LEGEND_ON_DATA",
                WARN,
                f"{leg.name} covers {', '.join(k + 's' for k in kinds)} "
                f"({quote(h.name for h in leg.covers)})",
                handles=(leg.handle,),
                panels=leg.panels,
            )
    return found


# ---------------------------------------------------------- value labels
def value_label_on_data(facts: Facts, found: Findings) -> Findings:
    """Value labels drawn over bars, lines or markers, per Axes."""
    for panel in sorted(
        {p for v in facts.values if (p := v.text.panel) is not None}
    ):
        labels = [v for v in facts.values if v.text.panel == panel]
        bad = [v for v in labels if v.covers]
        if bad:
            kinds = sorted({h.kind for v in bad for h in v.covers})
            found = found.flag(
                "VALUE_LABEL_ON_DATA",
                WARN,
                f"Axes[{panel}]: {len(bad)} of {len(labels)} value labels are "
                f"drawn over {', '.join(k + 's' for k in kinds)} "
                f"(first {bad[0].text.short!r})",
                [v.text for v in bad],
            )
    return found


def value_label_decimal(facts: Facts, found: Findings) -> Findings:
    """Whole-number value labels that print decimals (``120.0, 135.0``)."""
    for panel, texts in facts.by_panel.items():
        labels = [
            (t, n)
            for t in texts
            if t.role.free and (n := t.number) is not None and not n.scientific
        ]
        extra = [t for t, n in labels if n.decimals]
        if len(labels) >= 2 and extra and all(n.whole for _t, n in labels):
            found = found.flag(
                "VALUE_LABEL_DECIMAL",
                WARN,
                f"Axes[{panel}]: whole-number labels print decimals "
                f"({extra[0].short!r}, {len(extra)} of {len(labels)})",
                extra,
            )
    return found


# ----------------------------------------------------------------- ticks
def tick_overlap(facts: Facts, found: Findings) -> Findings:
    """Neighbouring tick labels of one axis drawn on each other."""
    for row in facts.ticks:
        if row.overlaps:
            found = found.flag(
                "TICK_OVERLAP",
                WARN,
                f"Axes[{row.panel}] {row.axis.letter} axis: {row.overlaps} "
                f"pair(s) of tick labels overlap (up to {row.deepest:.1f}px)",
                handles=(row.handle,),
                panels=(row.panel,),
            )
    return found


def tick_crowd(facts: Facts, found: Findings) -> Findings:
    """More tick labels than the axis holds with room between them."""
    for row in facts.ticks:
        if row.need is None or row.span <= 0 or len(row.labels) < 2:
            continue
        fill = row.need * (1 + CROWD_GAP) / row.span
        if fill > 1 and row.closest is not None and row.closest < CROWD_EM:
            found = found.flag(
                "TICK_CROWD",
                INFO,
                f"Axes[{row.panel}] {row.axis.letter} axis: {len(row.labels)} "
                f"labels fill {fill:.0%} of it, neighbours "
                f"{row.closest:.2f} em apart",
                handles=(row.handle,),
                panels=(row.panel,),
            )
    return found


def tick_corner(facts: Facts, found: Findings) -> Findings:
    """An x tick label on a y tick label at a corner of one plot."""
    for c in facts.corners:
        found = found.flag(
            "TICK_CORNER_OVERLAP",
            WARN,
            f"Axes[{c.panel}]: x tick {c.x_label.short!r} overlaps y tick "
            f"{c.y_label.short!r} at the {c.corner} corner ({c.pairs} "
            f"pair(s), {c.depth:.1f}px)",
            (c.x_label, c.y_label),
        )
    return found


def _decimal_problem(row: TickRow) -> Findings:
    """The first decimal problem of one axis' ticks, as a finding (or none)."""
    texts = [" ".join(t.text.split()) for t in row.labels]
    units: dict[str, list[Number]] = {}
    for t in row.labels:
        if (n := t.number) is not None and not n.bare_zero:
            units.setdefault(n.suffix, []).append(n)
    shared = [u for u in units.values() if len(u) >= 2]
    places = [sorted({n.decimals for n in u}) for u in shared]
    need = [step_decimals(n.value for n in u) for u in shared]
    problems = [
        *(f"neighbours both print {a!r}" for a, b in pairwise(texts) if a == b),
        *(f"ticks print {p} decimal places" for p in places if len(p) > 1),
        *(
            "every tick is a whole number but prints decimals"
            for u, p in zip(shared, places, strict=True)
            if p[-1] >= 1 and all(n.whole for n in u)
        ),
        *(
            f"ticks print {p[-1]} decimals where {k} do"
            for p, k in zip(places, need, strict=True)
            if p[-1] > k + 1
        ),
    ]
    if not problems:
        return Findings()
    return Findings().flag(
        "TICK_DECIMAL",
        WARN,
        f"Axes[{row.panel}] {row.axis.letter} axis: {problems[0]}",
        handles=(row.handle,),
        panels=(row.panel,),
    )


def tick_decimal(facts: Facts, found: Findings) -> Findings:
    """Tick numbers whose decimals mislead: twins, mixed, ``2.0``, excess."""
    for row in facts.ticks:
        if sum(t.number is not None for t in row.labels) >= 3:
            found = found.add(*_decimal_problem(row))
    return found


# ----------------------------------------------------------------- panels
def empty_axes(facts: Facts, found: Findings) -> Findings:
    """Axes that draw no data, text or legend."""
    for p in facts.panels:
        if p.empty:
            found = found.flag(
                "EMPTY_AXES",
                INFO,
                f"Axes[{p.index}] draws nothing",
                handles=(p.handle,),
                panels=(p.index,),
            )
    return found
