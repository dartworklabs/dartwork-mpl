"""Judge bars and dots against what belongs with them: a value label, a
band behind a row, the outline of a neighbour."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import combinations

from ..vocab import Box, Span, Which
from .findings import Findings
from .model import AXES, Bar, Facts, Text, quote

#: A value label further (em) from its bar than this no longer sits at it.
ADRIFT_EM = 1.0
#: Outlines and centres within this (pt) of each other are the same.
SAME_PT = 0.15
#: A row this far (pt) off the middle of its band, and this share of the
#: band's thickness, is visibly off it: the corpus' bands are centred to
#: 0.0 pt, the reported one sat 3.4 pt (8%) off.
OFF_CENTRE_PT = 1.5
OFF_CENTRE_SHARE = 0.04
#: A text this far (em) off the row is not printed on its marks.
ON_ROW_EM = 0.35
#: Outlines differing by this (pt) or more make one bar larger than the next.
UNEVEN_PT = 0.2


def span(box: Box, along: Which) -> Span:
    """The box's extent along one axis."""
    return along.pick(Span(box.x0, box.x1), Span(box.y0, box.y1))


def middle(box: Box, along: Which) -> float:
    """The box's centre along one axis."""
    s = span(box, along)
    return (s.low + s.high) / 2


def holds(s: Span, at: float) -> bool:
    """``at`` lies within the extent."""
    return s.low <= at <= s.high


def lane(text: Text, bar: Bar) -> Which | None:
    """The axis along which ``text`` stands beside ``bar``: X in the bar's
    row, Y in its column, ``None`` when it shares neither."""
    for along in AXES:
        across = along.other
        if holds(span(bar.box, across), middle(text.box, across)):
            return along
    return None


def owned(facts: Facts) -> Iterator[tuple[Text, Bar, Which]]:
    """Each value label with the bar whose length it prints, nearest pairs
    first, a bar and a label used once."""
    bars = [m for m in facts.bars if m.lengths]
    pairs = [
        (t.box.gap(bar.box), n, t, bar, along)
        for n, t in enumerate(facts.texts)
        if t.role.free and t.value
        for bar in bars
        if bar.panel == t.panel
        and (along := lane(t, bar)) is not None
        and bar.prints(t, along)
    ]
    used: set[int] = set()
    for _gap, _n, t, bar, along in sorted(pairs, key=lambda p: p[:2]):
        if id(t.handle) not in used and id(bar.handle) not in used:
            used |= {id(t.handle), id(bar.handle)}
            yield t, bar, along


def value_label_adrift(facts: Facts, found: Findings) -> Findings:
    """Value labels that stand between their own bar and another one of the
    same row or column, nearer the other."""
    bars = [m for m in facts.bars if m.lengths]
    adrift: dict[int, list[tuple[Text, float, float]]] = {}
    for t, own, along in owned(facts):
        far = t.box.gap(own.box)
        if far <= ADRIFT_EM * t.em or t.panel is None:
            continue
        here, across = span(t.box, along), middle(t.box, along.other)
        before = span(own.box, along).high <= here.low
        near = min(
            (
                t.box.gap(bar.box)
                for bar in bars
                if bar is not own
                and holds(span(bar.box, along.other), across)
                and (
                    span(bar.box, along).low >= here.high
                    if before
                    else span(bar.box, along).high <= here.low
                )
            ),
            default=far,
        )
        if near < far:
            adrift.setdefault(t.panel, []).append((t, far / t.em, near / t.em))
    for panel, group in adrift.items():
        t, far, near = max(group, key=lambda g: g[1] - g[2])
        found = found.flag(
            "VALUE_LABEL_ADRIFT",
            f"Axes[{panel}]: {len(group)} value label"
            f"{'s stand' if len(group) > 1 else ' stands'} nearer another "
            f"bar than {'their' if len(group) > 1 else 'its'} own: "
            f"{quote(g[0].short for g in group)} "
            f"({t.short!r} is {far:.1f} em from its bar, {near:.1f} em from "
            "the next)",
            [g[0] for g in group],
        )
    return found


def within(box: Box, outer: Box, touch: float) -> bool:
    """``box`` lies inside ``outer``, ``touch`` allowed past its edges."""
    return (
        box.x0 >= outer.x0 - touch
        and box.x1 <= outer.x1 + touch
        and box.y0 >= outer.y0 - touch
        and box.y1 <= outer.y1 + touch
    )


def row_in(band: Bar, facts: Facts, along: Which) -> float | None:
    """Where the one row of marks ``band`` holds stands along ``along``
    (Y: a row, X: a column); ``None`` when it holds no such row, or texts
    that are not printed on it."""
    inside = [
        m.box
        for m in (*facts.bars, *facts.dots)
        if m is not band
        and m.panel == band.panel
        and within(m.box, band.box, facts.touch)
    ]
    if len(inside) < 2:
        return None
    same = SAME_PT * facts.px_per_pt
    at = [middle(box, along) for box in inside]
    spread = [middle(box, along.other) for box in inside]
    if max(at) - min(at) > same or max(spread) - min(spread) <= same:
        return None
    labels = (
        t
        for t in facts.texts
        if t.panel == band.panel
        and t.role.free
        and within(t.box, band.box, 0.0)
    )
    if any(
        abs(middle(t.box, along) - at[0]) > ON_ROW_EM * t.em for t in labels
    ):
        return None
    return at[0]


def band_off_centre(facts: Facts, found: Findings) -> Findings:
    """Rectangles drawn behind one row or column of marks, and nothing
    else, whose middle is not that row's."""
    for band in facts.bars:
        for along in AXES:
            at = row_in(band, facts, along)
            if at is None:
                continue
            off = abs(at - middle(band.box, along)) / facts.px_per_pt
            thick = span(band.box, along).length / facts.px_per_pt
            if off > OFF_CENTRE_PT and off > OFF_CENTRE_SHARE * thick:
                found = found.flag(
                    "BAND_OFF_CENTRE",
                    f"Axes[{band.panel}]: the {along.pick('column', 'row')} "
                    f"of marks in a {thick:.0f} pt band stands {off:.1f} pt "
                    "off its middle",
                    handles=(band.handle,),
                    panels=(band.panel,),
                )
    return found


def touching(a: Box, b: Box, touch: float) -> bool:
    """Two boxes of one row or column that share an edge."""
    return any(
        abs(span(a, across).low - span(b, across).low) <= touch
        and abs(span(a, across).high - span(b, across).high) <= touch
        and min(
            abs(span(a, along).high - span(b, along).low),
            abs(span(b, along).high - span(a, along).low),
        )
        <= touch
        for along in AXES
        for across in (along.other,)
    )


def uneven_outline(facts: Facts, found: Findings) -> Findings:
    """Bars that touch a bar with a wider or narrower outline."""
    by_panel: dict[int, list[Bar]] = {}
    for m in facts.bars:
        if m.lengths:
            by_panel.setdefault(m.panel, []).append(m)
    for panel, bars in by_panel.items():
        if (
            max(b.outset for b in bars) - min(b.outset for b in bars)
            < UNEVEN_PT
        ):
            continue
        larger: dict[int, Bar] = {}
        step = 0.0
        for a, b in combinations(bars, 2):
            if abs(a.outset - b.outset) >= UNEVEN_PT and touching(
                a.box, b.box, facts.touch
            ):
                big = max(a, b, key=lambda m: m.outset)
                larger[id(big.handle)] = big
                step = max(step, abs(a.outset - b.outset))
        if larger:
            n = len(larger)
            found = found.flag(
                "UNEVEN_OUTLINE",
                f"Axes[{panel}]: {n} bar{'s' * (n != 1)} with a wider outline "
                f"than the bar{'s' * (n != 1)} "
                f"{'they touch' if n != 1 else 'it touches'}: an outline is "
                f"drawn half outside its bar, so {'each' if n != 1 else 'it'} "
                f"stands {step:.2g} pt past its neighbours",
                handles=tuple(m.handle for m in larger.values()),
                panels=(panel,),
            )
    return found
