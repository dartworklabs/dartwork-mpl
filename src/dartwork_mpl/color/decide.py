"""Pure colour decisions for the ordinary chart: domain types in, values out.

A family's ``n``-colour form is designed, never resampled at random: a
sequential ladder spreads ``n`` stops over its middle eight, a diverging row
keeps its outer stops and adds the colormap midpoint for odd ``n``, a
multi-hue map uses frozen indices, a cyclic map is sampled evenly and a
qualitative set is cut. A gradient runs the short way round the OKLCH hue
circle; a mix is linear in OKLab; contrast is WCAG 2.x. Special cases
(single and full ladders, curated diverging rows, grey gradient ends, the
Korean gain/loss colours...) are in ``edges.py``.
"""

from __future__ import annotations

import difflib
import math
from difflib import SequenceMatcher
from typing import assert_never

import numpy as np

from ..colorspace import Color, Hex, Oklab, Oklch, Rgb
from .family import (
    Count,
    Cyclic,
    Diverging,
    Family,
    MultiHue,
    Qualitative,
    Sequential,
)
from .model import (
    Catalog,
    Categorical,
    DivergingSource,
    Form,
    Gradient,
    InOklab,
    InOklch,
    InRgb,
    Lookup,
    Name,
    Ordered,
    PaletteRequest,
    Semantic,
    SemanticFacts,
    Space,
    Steps,
    Suggestions,
    TwoSided,
    Weight,
)

SUGGESTION_COUNT = 3
SUGGESTION_CUTOFF = 0.7


# -- discrete forms ------------------------------------------------------------


def sequential(family: Family, n: Count) -> tuple[Hex, ...]:
    """``n`` stops spread evenly over ladder stops 1..8 (rounded halves up)."""
    if n.n == 1:
        return (family.stops[5],)
    picks = (math.floor(1 + i * 7 / (n.n - 1) + 0.5) for i in range(n.n))
    return tuple(family.stops[i] for i in picks)


def diverging(family: Family, n: Count) -> tuple[Hex, ...]:
    """The outer ``n // 2`` stops of each side; odd ``n`` adds the midpoint."""
    row, k = family.stops, n.n // 2
    left, right = row[:k], row[len(row) - k :]
    middle = (family.cmap[128],) if n.n % 2 else ()
    return (*left, *middle, *right)


def discrete(form: Form) -> tuple[Hex, ...]:
    """The designed ``n``-colour form of a family, lightest or first first."""
    family, n = form.family, form.n
    match family.kind:
        case Sequential():
            colours = sequential(family, n)
        case Diverging():
            colours = diverging(family, n)
        case MultiHue():
            colours = tuple(family.cmap[i] for i in family.picks[n.n - 1])
        case Cyclic():
            size = len(family.cmap)
            colours = tuple(
                family.cmap[min(int(i * size / n.n), size - 1)]
                for i in range(n.n)
            )
        case Qualitative():
            colours = family.stops[: n.n]
        case _:
            assert_never(family.kind)
    return colours


def diverging_row(source: DivergingSource) -> tuple[Hex, ...]:
    """A diverging family's canonical row from its two ladders: stops
    7, 5, 3, 1 of the low side, then 1, 3, 5, 7 of the high side."""
    low = tuple(source.low[i] for i in (7, 5, 3, 1))
    return low + tuple(source.high[i] for i in (1, 3, 5, 7))


# -- gradients and mixes -------------------------------------------------------


def ends(start: Color, end: Color) -> Gradient:
    """The OKLCH ends of a gradient from ``start`` to ``end``."""
    return Gradient(start.lab.lch(), end.lab.lch())


def sample(gradient: Gradient, steps: Steps) -> tuple[Color, ...]:
    """``steps`` colours from end to end, the hue the short way round."""
    start, end = gradient.start, gradient.end
    end_h = end.h
    if end_h - start.h > 180:
        end_h -= 360
    elif end_h - start.h < -180:
        end_h += 360
    lightness = np.linspace(start.L, end.L, steps.n)
    chroma = np.linspace(start.C, end.C, steps.n)
    hue = np.linspace(start.h, end_h, steps.n) % 360.0
    return tuple(
        Color(Oklch(float(L), float(C), float(h)).lab())
        for L, C, h in zip(lightness, chroma, hue, strict=True)
    )


def gradient(
    start: Color, end: Color, steps: Steps, space: Space
) -> tuple[Color, ...]:
    """``steps`` colours from ``start`` to ``end`` in ``space``: OKLCH the
    hue the short way round, OKLab or sRGB the straight line."""
    match space:
        case InOklch():
            return sample(ends(start, end), steps)
        case InOklab():
            return oklab_line(start, end, steps)
        case InRgb():
            return rgb_line(start, end, steps)
        case _:
            assert_never(space)


def oklab_line(start: Color, end: Color, steps: Steps) -> tuple[Color, ...]:
    """``steps`` colours on the straight OKLab line between the ends."""
    a, b = start.to_oklab(), end.to_oklab()
    axes = [np.linspace(a[i], b[i], steps.n) for i in range(3)]
    return tuple(
        Color(Oklab(*(float(axis[k]) for axis in axes))) for k in range(steps.n)
    )


def rgb_line(start: Color, end: Color, steps: Steps) -> tuple[Color, ...]:
    """``steps`` colours on the straight sRGB line between the ends."""
    a, b = start.to_rgb(), end.to_rgb()
    axes = [np.linspace(a[i], b[i], steps.n) for i in range(3)]
    return tuple(
        Color(Rgb(*(float(axis[k]) for axis in axes)).oklab())
        for k in range(steps.n)
    )


def mix(first: Color, second: Color, weight: Weight) -> Color:
    """``weight`` of ``first`` and the rest of ``second``, linear in OKLab."""
    w, a, b = weight.value, first.lab, second.lab
    return Color(
        Oklab(
            w * a.L + (1.0 - w) * b.L,
            w * a.a + (1.0 - w) * b.a,
            w * a.b + (1.0 - w) * b.b,
        )
    )


# -- names ---------------------------------------------------------------------


def suggest(lookup: Lookup) -> Suggestions:
    """Registered names close to a rejected one, nearest first."""
    close = difflib.get_close_matches(
        lookup.name,
        lookup.registry,
        n=SUGGESTION_COUNT,
        cutoff=SUGGESTION_CUTOFF,
    )
    return Suggestions(tuple(Name(name) for name in close))


def nearest_families(name: Name, catalog: Catalog) -> Suggestions:
    """The three family names most like ``name``."""
    ranked = sorted(
        catalog.families,
        key=lambda c: (-SequenceMatcher(None, name, c).ratio(), c),
    )
    return Suggestions(tuple(Name(c) for c in ranked[:SUGGESTION_COUNT]))


def semantic(facts: SemanticFacts) -> Semantic:
    """The role colours: gains green, losses red, reference grey, violet
    highlight."""
    catalog = facts.catalog
    return Semantic(
        pos=catalog.ladder("green")[6],
        neg=catalog.ladder("red")[6],
        ref=catalog.ladder("gray")[6],
        hl=catalog.ladder("violet")[6],
    )


# -- make_palette --------------------------------------------------------------

CATEGORICAL = tuple(
    Name(f"oc.{hue}5")
    for hue in (
        "blue",
        "red",
        "green",
        "orange",
        "purple",
        "teal",
        "pink",
        "yellow",
    )
)
DIVERGING_FEW = tuple(
    Name(n) for n in ("oc.red6", "oc.red4", "oc.gray5", "oc.blue4", "oc.blue6")
)
DIVERGING_MANY = tuple(
    Name(n)
    for n in (
        "oc.red7",
        "oc.red5",
        "oc.red3",
        "oc.gray5",
        "oc.blue3",
        "oc.blue5",
        "oc.blue7",
    )
)


def palette(request: PaletteRequest) -> tuple[Name, ...]:
    """``n`` Open Color names for ``kind``, repeating the list when short.

    Up to five sequential or diverging series take the tighter list (blue
    3..7, or red 6/4, grey, blue 4/6); more take the wider one.
    """
    few = request.n <= 5
    match request.kind:
        case Categorical():
            base = CATEGORICAL
        case Ordered():
            shades = range(3, 8) if few else range(1, 10)
            base = tuple(Name(f"oc.blue{i}") for i in shades)
        case TwoSided():
            base = DIVERGING_FEW if few else DIVERGING_MANY
        case _:
            assert_never(request.kind)
    repeats = request.n // len(base) + 1
    return (base * repeats)[: request.n]
