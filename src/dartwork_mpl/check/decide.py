"""The rules: what in the measured facts makes a chart ugly or unreadable.

Each rule reads :class:`Facts` and appends its findings (the fix each rule
names is ``findings.FIXES``). They are listed, named and ordered in
``edges.py``; nothing here touches a figure.
"""

from __future__ import annotations

from itertools import combinations
from math import hypot
from typing import assert_never

from ..vocab import Box, Which, X, Y
from .findings import Findings
from .model import (
    AXES,
    BarCanvasUse,
    CanvasUse,
    ColorbarSpace,
    Facts,
    Frame,
    Hit,
    Inked,
    Inset,
    OnData,
    Text,
    TextGap,
    TickRow,
    TickValues,
    margins,
    quote,
)

#: A text further past the canvas edge than this (px) is cut off.
CUT_PX = 1.0
#: Two texts sharing this share of the smaller box overlap.
COVER = 0.05
#: A number and a name on one row closer than this (em) read as one phrase.
PHRASE_GAP_EM = 1.0
#: Separation of placed text from a title or other axis text.
AXIS_TEXT_GAP_EM = 0.5
#: Placed texts may read as a group, as in a stack of line-end names.
FREE_TEXT_GAP_EM = 0.3
#: A text with this share of its ink under the floor is faint as a whole.
ALL_OF_IT = 0.9
#: Whole-number x ticks all within these years read as years, not a quantity.
YEARS = (1800.0, 2100.0)
#: A text this far (em) into another Axes' plot, both ways, is drawn on it.
INTO_EM = 0.5
#: A parent spine crossing this far into an inset label passes through it.
SPINE_INTO_EM = 0.15
#: A tick this close to a whole number is one (locator rounding).
WHOLE = 1e-9
#: A largest plot whose shorter side holds fewer tick labels (em) than this
#: is too small for its text: the corpus' good charts hold 13.1 or more, a
#: report grid moved to slide text 5.0.
MIN_PANEL_EM = 7.0
#: A centred title this close (mm) to the canvas edge stands at the layout's
#: margin: the layout keeps content 1 mm in.
TITLE_EDGE_MM = 1.25
#: A title at least this share of the canvas wide reads as the figure's.
TITLE_WIDE = 0.5
#: Room (em) on the title's other side that makes it visibly off-centre.
TITLE_ROOM_EM = 2.0
#: Ignore the edge of a text box just grazing the disc.
THETA_INTO_EM = 0.4
#: Above the 90th percentile of horizontal margin differences in two
#: independent 101-case sweeps (5.0 and 3.3 percentage points).
CANVAS_BLANK_WIDTH = 0.06


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
    inset_labels = {
        id(t.handle) for inset in facts.insets for t in inset.labels
    }
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
                    fix=(
                        "give the axis label more room with labelpad=..., "
                        "or move it to the opposite side"
                        if (a.role.tick and id(b.handle) in inset_labels)
                        or (b.role.tick and id(a.handle) in inset_labels)
                        else None
                    ),
                )
    return found


def cross_axes(facts: Facts, found: Findings) -> Findings:
    """Titles, axis labels, letters and ticks of different Axes colliding,
    with each other or with another Axes' plot (a colorbar beside it)."""
    texts = [
        t for group in facts.by_panel.values() for t in group if not t.role.free
    ]
    found = into_plots(texts, facts.frames, found)
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
    return across_parent_spines(facts.insets, found)


def across_parent_spines(
    insets: tuple[Inset, ...], found: Findings
) -> Findings:
    """An inset axis label crossing the frame of the plot that holds it."""
    for inset in insets:
        parent = inset.parent
        for label in inset.labels:
            inner = label.box.padded(-SPINE_INTO_EM * label.em)
            # A straight spine has zero width or height, even inside the box.
            if any(inner.gap(spine) <= 0 for spine in inset.spines):
                found = found.flag(
                    "CROSS_AXES_OVERLAP",
                    f"Axes[{inset.index}]: inset axis label {label.short!r} "
                    f"crosses a spine of Axes[{parent.index}]",
                    (label,),
                    handles=(parent.handle,),
                    panels=(parent.index, inset.index),
                    fix="move the inset inward or put its axis label on "
                    "the opposite side with axis.set_label_position(...)",
                )
    return found


def into_plots(
    texts: list[Text], frames: tuple[Frame, ...], found: Findings
) -> Findings:
    """Texts drawn into the plot of another Axes; not of a twin or an inset
    (a plot sharing area with the text's own)."""
    own = {f.index: f.box for f in frames}
    seen: set[tuple[object, ...]] = set()
    for t in texts:
        home = own.get(t.panel) if t.panel is not None else None
        for f in frames:
            if f.index == t.panel or (home and home.overlaps(f.box)):
                continue
            into = t.box.overlap(f.box)
            deep = INTO_EM * t.em
            key = (t.panel, f.index, t.role)
            if into.width < deep or into.height < deep or key in seen:
                continue
            seen.add(key)
            found = found.flag(
                "CROSS_AXES_OVERLAP",
                f"axes[{t.panel}] {t.role} {t.short!r} runs into the plot "
                f"of axes[{f.index}]",
                (t,),
                handles=(f.handle,),
                panels=tuple(sorted({f.index, t.panel or 0})),
                fix="shorten or wrap the text, or move the plots apart "
                "(a colorbar: fig.colorbar(..., pad=...))",
            )
    return found


def phrase(facts: Facts, found: Findings) -> Findings:
    """A value label beside a name on one row, near enough to read as one.
    A number in its dot is part of the mark the name stands beside."""
    in_dots = {id(t.handle) for t in facts.held}
    for panel, texts in facts.by_panel.items():
        free = [t for t in texts if t.role.free and id(t.handle) not in in_dots]
        for a, b in combinations(free, 2):
            if a.value == b.value:
                continue
            rows = min(a.box.y1, b.box.y1) - max(a.box.y0, b.box.y0)
            if rows < 0.5 * min(a.box.height, b.box.height):
                continue
            gap = max(a.box.x0, b.box.x0) - min(a.box.x1, b.box.x1)
            em = max(a.em, b.em)
            if (
                -facts.touch <= gap < PHRASE_GAP_EM * em
                and a.box.cover(b.box) <= COVER
            ):
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
    """A framed Axes with no data, or data that leaves no visible marks."""
    for p in facts.empty:
        found = found.flag(
            "EMPTY_AXES",
            f"Axes[{p.index}] has no visible data marks",
            handles=(p.handle,),
            panels=(p.index,),
        )
    return found


def reads_as_years(ticks: TickValues, axis: Which) -> bool:
    """A linear x axis whose ticks are all whole numbers within
    :data:`YEARS` (``2019, 2020, 2021``): its ticks name themselves.

    A y axis never does: years run along x, and a y axis of whole numbers
    near 2,000 is far more often a quantity than a year.
    """
    low, high = YEARS
    years = (
        ticks.linear
        and bool(ticks.values)
        and all(
            abs(v - round(v)) < WHOLE and low <= v <= high for v in ticks.values
        )
    )
    match axis:
        case X():
            return years
        case Y():
            return False
        case _:
            assert_never(axis)


def missing_axis_label(facts: Facts, found: Findings) -> Findings:
    """An axis of numbers that nothing names, on a panel that draws; an x
    axis of years names itself."""
    empty = {p.index for p in facts.empty}
    for row in facts.ticks:
        if (
            row.numbers
            and not row.named
            and row.panel not in empty
            and not reads_as_years(row.at, row.axis)
        ):
            found = found.flag(
                "MISSING_AXIS_LABEL",
                f"Axes[{row.panel}]: the {row.axis.letter} axis prints "
                "numbers but nothing names them",
                handles=(row.handle,),
                panels=(row.panel,),
                fix="name the quantity and its unit: "
                f'ax.set_{row.axis.letter}label("Revenue (M USD)"); '
                "a colorbar: cbar.set_label(...)",
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


def text_on_line(facts: Facts, found: Findings) -> Findings:
    """Names and notes with a line drawn through them, per Axes, and an
    inset's labels with its zoom connector through them."""
    panels: dict[int | None, list[OnData]] = {}
    for on in facts.struck:
        panels.setdefault(on.text.panel, []).append(on)
    for panel, on in panels.items():
        found = found.flag(
            "TEXT_ON_LINE",
            f"Axes[{panel}]: a line runs through {len(on)} text(s) "
            f"({quote(v.text.short for v in on)})",
            [v.text for v in on],
        )
    for inset in facts.connected:
        found = found.flag(
            "TEXT_ON_LINE",
            f"Axes[{inset.inset}]: the zoom connector runs through "
            f"{len(inset.labels)} label(s) of the inset "
            f"({quote(t.short for t in inset.labels)})",
            inset.labels,
            fix="the connectors leave the inset on the side its labels are "
            "on: put those labels on the far side (axins.xaxis.tick_top(), "
            'axins.xaxis.set_label_position("top")), move the inset, or keep '
            "the box alone (ind = ax.indicate_inset_zoom(axins); "
            "c.set_visible(False) for each of ind.connectors)",
        )
    return found


def letter_on_data(facts: Facts, found: Findings) -> Findings:
    """Panel letters drawn on data, per letter."""
    for on in facts.letters:
        kinds = sorted({h.kind for h in on.covers})
        found = found.flag(
            "LETTER_ON_DATA",
            f"Axes[{on.text.panel}]: the panel letter {on.text.short!r} sits "
            f"on {', '.join(k + 's' for k in kinds)}",
            [on.text],
        )
    return found


def text_contrast(facts: Facts, found: Findings) -> Findings:
    """Texts the user placed with ink under 3:1 on what is behind it: all
    of a text, or the part of it that runs onto another background."""
    panels: dict[int | None, list[Inked]] = {}
    for c in facts.inks:
        if not c.reading.reads:
            panels.setdefault(c.text.panel, []).append(c)
    for panel, faint in panels.items():
        w = max(faint, key=lambda c: (c.reading.low, -c.ratio.value))
        part = "all" if w.reading.low >= ALL_OF_IT else f"{w.reading.low:.0%}"
        others = [c.text.short for c in faint if c is not w]
        also = f"; also {quote(others)}" if others else ""
        found = found.flag(
            "TEXT_CONTRAST",
            f"Axes[{panel}]: {len(faint)} text(s) with ink under 3:1 on "
            f"what is behind it, worst {w.text.short!r}: {part} of its ink, "
            f"down to {w.ratio.value:.2f}:1 ({w.ink} on {w.paper}){also}",
            [c.text for c in faint],
        )
    return found


def small_panel(facts: Facts, found: Findings) -> Findings:
    """The largest plot is short for its tick labels: the text takes the
    canvas. A plot is a frame with tick labels on both axes (a colorbar
    has them on one); an inset or a side panel is never the largest."""
    rows: dict[int, list[TickRow]] = {}
    for row in facts.ticks:
        rows.setdefault(row.panel, []).append(row)
    plots: list[tuple[Frame, list[TickRow]]] = [
        (f, rows[f.index])
        for f in facts.frames
        if len({r.axis for r in rows.get(f.index, [])}) == len(AXES)
    ]
    if not plots:
        return found
    frame, ticks = max(plots, key=lambda p: p[0].box.area)
    em = max(t.em for r in ticks for t in r.labels)
    side = min(frame.box.width, frame.box.height)
    if side < MIN_PANEL_EM * em:
        cm = side / facts.px_per_pt / 72 * 2.54
        found = found.flag(
            "SMALL_PANEL",
            f"Axes[{frame.index}]: the largest plot is {cm:.1f} cm, "
            f"{side / em:.1f} tick labels, on its shorter side: the text "
            "takes the canvas",
            handles=(frame.handle,),
            panels=(frame.index,),
        )
    return found


def list_rows(a: Text, b: Text) -> bool:
    """Two free texts on separate rows of the same typographic column."""
    if not (a.role.free and b.role.free):
        return False
    em = min(a.em, b.em)
    left = a.box.x0 - b.box.x0
    right = a.box.x1 - b.box.x1
    pitch = abs(a.box.y0 + a.box.y1 - b.box.y0 - b.box.y1) / 2
    return (
        abs(a.em - b.em) <= 0.01 * em
        and min(abs(left), abs(right), abs(left + right) / 2) <= 0.1 * em
        and pitch >= 0.85 * em
    )


def close_gap(a: Text, b: Text) -> TextGap | None:
    """A small gap between aligned texts, in em of the smaller one."""
    if not (a.role.free or b.role.free):
        return None
    shared = a.box.overlap(b.box)
    if shared.width >= 0.5 * min(a.box.width, b.box.width):
        gap = -shared.height
        if gap >= 0 and list_rows(a, b):
            return None
    elif shared.height >= 0.5 * min(a.box.height, b.box.height):
        # The same-row value and name have a rule of their own. A short
        # inline unit or suffix can also belong to the value.
        if a.value or b.value:
            return None
        gap = -shared.width
    else:
        return None
    em = min(a.em, b.em)
    minimum = (
        FREE_TEXT_GAP_EM if a.role.free and b.role.free else AXIS_TEXT_GAP_EM
    )
    return TextGap(gap / em) if 0 <= gap < minimum * em else None


def text_too_close(facts: Facts, found: Findings) -> Findings:
    """Independently placed text with too little air between the boxes."""
    for panel, texts in facts.by_panel.items():
        for a, b in combinations(texts, 2):
            if (gap := close_gap(a, b)) is not None:
                found = found.flag(
                    "TEXT_TOO_CLOSE",
                    f"Axes[{panel}]: {a.role} {a.short!r} and "
                    f"{b.role} {b.short!r} sit {gap.em:.2f} em apart",
                    (a, b),
                )
    return found


def theta_intrudes(label: Text, disc: Box) -> bool:
    """Whether the closest point of a label box sits well inside the disc."""
    rx, ry = disc.width / 2, disc.height / 2
    cx, cy = disc.x0 + rx, disc.y0 + ry
    box = label.box
    dx = max(box.x0 - cx, cx - box.x1, 0.0) / rx
    dy = max(box.y0 - cy, cy - box.y1, 0.0) / ry
    return (1 - hypot(dx, dy)) * min(rx, ry) > THETA_INTO_EM * label.em


def polar_tick_on_plot(facts: Facts, found: Findings) -> Findings:
    """Angle tick labels crossing their own polar plot's outer circle."""
    for theta in facts.polar_theta:
        labels = [t for t in theta.labels if theta_intrudes(t, theta.disc)]
        if labels:
            found = found.flag(
                "POLAR_TICK_ON_PLOT",
                f"Axes[{theta.panel.index}]: angle tick labels run into the "
                f"polar plot ({quote((t.short for t in labels), most=6)})",
                labels,
            )
    return found


def mixed_minus(facts: Facts, found: Findings) -> Findings:
    """A negative quantity using a hyphen while the tick labels use a minus."""
    if facts.minus_tick is None:
        return found
    panels: dict[int | None, list[Text]] = {}
    for label in facts.minus_labels:
        panels.setdefault(label.panel, []).append(label)
    for panel, labels in panels.items():
        where = "Figure text" if panel is None else f"Axes[{panel}]"
        found = found.flag(
            "MIXED_MINUS",
            f"{where}: {len(labels)} numeric label(s) use a hyphen-minus "
            f"({quote(t.short for t in labels)}); ticks use the Unicode minus",
            labels,
        )
    return found


def radial_tick_covered(facts: Facts, found: Findings) -> Findings:
    """A substantial portion of a radial tick is under visible fill."""
    panels: dict[int | None, list[Text]] = {}
    for covered in facts.occluded_ticks:
        if covered.opacity >= 0.45:
            label = covered.label
            panels.setdefault(label.panel, []).append(label)
    for panel, labels in panels.items():
        found = found.flag(
            "RADIAL_TICK_COVERED",
            f"Axes[{panel}]: fill is drawn over radial tick labels "
            f"({quote(t.short for t in labels)})",
            labels,
        )
    return found


def text_at_edge(facts: Facts, found: Findings) -> Findings:
    """Manually placed Axes text within a quarter millimetre of the canvas,
    and a title the layout stopped at one canvas edge."""
    close_px = 0.25 * 72 / 25.4 * facts.px_per_pt
    groups: dict[tuple[int | None, str], list[Text]] = {}
    for t in facts.edge_texts:
        side, room = min(
            margins(t.box, facts.canvas).items(), key=lambda item: item[1]
        )
        if -CUT_PX <= room < close_px:
            groups.setdefault((t.panel, side), []).append(t)
    for (panel, side), labels in groups.items():
        found = found.flag(
            "TEXT_AT_EDGE",
            f"Axes[{panel}]: text sits at the {side} canvas edge "
            f"({quote(t.short for t in labels)})",
            labels,
        )
    return title_at_edge(facts, found)


def title_at_edge(facts: Facts, found: Findings) -> Findings:
    """A wide title centred on an off-centre plot: one end at the canvas
    edge, room to spare past the other."""
    mm = 72 / 25.4 * facts.px_per_pt
    for t in facts.edge_titles:
        rooms = margins(t.box, facts.canvas)
        (side, near), (_other, far) = sorted(
            ((s, rooms[s]) for s in ("left", "right")), key=lambda r: r[1]
        )
        if (
            -CUT_PX <= near < TITLE_EDGE_MM * mm
            and t.box.width >= TITLE_WIDE * facts.canvas.width
            and far >= TITLE_ROOM_EM * t.em
        ):
            found = found.flag(
                "TEXT_AT_EDGE",
                f"Axes[{t.panel}]: the title ends at the {side} canvas edge "
                f"with {far / mm:.0f} mm free past its other end: it is "
                f"centred on a plot that sits off the canvas centre "
                f"({t.short!r})",
                (t,),
                fix="centre it on the canvas with fig.suptitle(...), or "
                'break it into two lines with "\\n"',
            )
    return found


def underused_canvas(facts: Facts, found: Findings) -> Findings:
    """An axis-less panel or an oversized scale slot leaves a blank band."""
    if facts.colorbar_space is not None:
        return blank_beside_colorbar(facts, facts.colorbar_space, found)
    use, canvas = facts.canvas_use, facts.canvas
    match use:
        case BarCanvasUse():
            return blank_beside_columns(facts, use, found)
        case CanvasUse():
            pass
        case None:
            return found
        case _:
            assert_never(use)
    if min(canvas.width, canvas.height) < 80 * 72 / 25.4 * facts.px_per_pt:
        return found
    width, height = (
        use.body.width / canvas.width,
        use.body.height / canvas.height,
    )
    if max(width, height) < 0.75 or min(width, height) >= 2 / 3:
        return found
    dimension = "width" if width < height else "height"
    return found.flag(
        "UNDERUSED_CANVAS",
        f"Axes[{use.panel.index}]: the shapes and their labels use "
        f"{min(width, height):.0%} of the canvas {dimension}",
        handles=(use.panel.handle,),
        panels=(use.panel.index,),
    )


def blank_beside_colorbar(
    facts: Facts, space: ColorbarSpace, found: Findings
) -> Findings:
    """A narrow vertical scale uses only part of its allocated column."""
    canvas = facts.canvas
    left = space.body.x0 - canvas.x0
    right = canvas.x1 - space.body.x1
    if space.bar.x0 >= space.plot.x1:
        side, near, far = "right", right, left
        unused = space.slot.x1 - space.bar.x1
    elif space.bar.x1 <= space.plot.x0:
        side, near, far = "left", left, right
        unused = space.bar.x0 - space.slot.x0
    else:
        return found
    blank = CANVAS_BLANK_WIDTH * canvas.width
    if far < -CUT_PX or near - far < blank or unused < blank:
        return found
    return found.flag(
        "UNDERUSED_CANVAS",
        f"Axes[{space.scale.index}]: the colorbar leaves {near / canvas.width:.0%} "
        f"of the canvas blank on the {side}; the drawn scale is narrower than its slot",
        handles=(space.panel.handle, space.scale.handle),
        panels=(space.panel.index, space.scale.index),
        fix="reduce fraction= in fig.colorbar(..., ax=ax) to fit the scale's "
        "slot to its drawn width, then rerun dm.simple_layout(fig). For an "
        "exact width, give the scale its own GridSpec column with cax=",
    )


def blank_beside_columns(
    facts: Facts, use: BarCanvasUse, found: Findings
) -> Findings:
    """One large blank strip beside the columns, their axis and descriptions."""
    canvas = facts.canvas
    left = use.body.x0 - canvas.x0
    right = canvas.x1 - use.body.x1
    near, far = sorted((left, right))
    if far - near < CANVAS_BLANK_WIDTH * canvas.width or far < 2 * near:
        return found
    side = "right" if right > left else "left"
    limit = use.fit[1] if right > left else use.fit[0]
    fitted = (
        "fit the x limits to the columns and their labels with ax.set_xlim(...)"
        if limit is None
        else f"the labels end at the plot's edge with ax.set_xlim({side}="
        f"{limit:.3g}) (a text keeps its size when the limits move, so "
        "this is solved for you)"
    )
    return found.flag(
        "UNDERUSED_CANVAS",
        f"Axes[{use.panel.index}]: the columns and their labels leave "
        f"{far / canvas.width:.0%} of the canvas blank on the {side} "
        f"and {near / canvas.width:.0%} on the other side",
        handles=(use.panel.handle,),
        panels=(use.panel.index,),
        fix=f"{fitted}; or write the labels beside the plot (ax.text(1, y, "
        "s, transform=ax.get_yaxis_transform()), then dm.place_columns(ax, "
        "texts)) so no x range is spent on them; or use a narrower canvas. "
        "Then rerun dm.simple_layout(fig)",
    )
