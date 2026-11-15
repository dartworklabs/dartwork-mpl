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

import colorsys
import difflib
import math
from difflib import SequenceMatcher

import numpy as np

from .model import (
    Catalog,
    ContrastFacts,
    Count,
    DivergingSource,
    Family,
    Form,
    Gradient,
    Ink,
    Kind,
    Lift,
    Lookup,
    Name,
    PaletteKind,
    PaletteRequest,
    Ratio,
    Semantic,
    SemanticFacts,
    Space,
    Steps,
    Suggestions,
    Weight,
)
from .space import Color, Hex, Oklab, Oklch, Rgb, Rgba

SUGGESTION_COUNT = 3
SUGGESTION_CUTOFF = 0.7
LIGHTNESS_STEPS = 32


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
        case Kind.SEQUENTIAL:
            colours = sequential(family, n)
        case Kind.DIVERGING:
            colours = diverging(family, n)
        case Kind.MULTI_HUE:
            colours = tuple(family.cmap[i] for i in family.picks[n.n - 1])
        case Kind.CYCLIC:
            size = len(family.cmap)
            colours = tuple(
                family.cmap[min(int(i * size / n.n), size - 1)]
                for i in range(n.n)
            )
        case Kind.QUALITATIVE:
            colours = family.stops[: n.n]
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


def straight(
    start: Color, end: Color, steps: Steps, space: Space
) -> tuple[Color, ...]:
    """``steps`` colours on the straight OKLab or sRGB line between the ends."""
    if space is Space.OKLAB:
        a, b = start.to_oklab(), end.to_oklab()
    else:
        a, b = start.to_rgb(), end.to_rgb()
    axes = [np.linspace(a[i], b[i], steps.n) for i in range(3)]
    points = [tuple(float(axis[k]) for axis in axes) for k in range(steps.n)]
    if space is Space.OKLAB:
        return tuple(Color(Oklab(*p)) for p in points)
    return tuple(Color(Rgb(*p).oklab()) for p in points)


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


def composite_over(top: Rgba, below: Rgb) -> Rgb:
    """``top`` painted over the opaque ``below``."""
    alpha = top.alpha
    r, g, b = (
        alpha * t + (1.0 - alpha) * u
        for t, u in zip(top.rgb.channels, below.channels, strict=True)
    )
    return Rgb(r, g, b)


def composite_layers(layers: tuple[Rgba, ...], below: Rgb) -> Rgb:
    """``layers`` painted in order, lowest first, over the opaque ``below``."""
    for layer in layers:
        below = composite_over(layer, below)
    return below


# -- contrast ------------------------------------------------------------------


def contrast(first: Rgb, second: Rgb) -> Ratio:
    """The WCAG contrast ratio of two colours, lighter over darker."""
    hi, lo = sorted(
        (first.wcag_luminance(), second.wcag_luminance()), reverse=True
    )
    return Ratio((hi + 0.05) / (lo + 0.05))


def passes(facts: ContrastFacts, color: Rgb) -> bool:
    """``color`` reaches the target ratio on the background."""
    return contrast(color, facts.background).value >= facts.target.value


def lift(facts: ContrastFacts) -> Lift | None:
    """The smallest HLS lightness move that reaches the target ratio.

    None when the colour already passes. Otherwise lightness moves toward
    whichever pole (white or black) contrasts more with the background, by
    bisection; an unreachable target ends at the pole.
    """
    if passes(facts, facts.color):
        return None
    hue, lightness, saturation = colorsys.rgb_to_hls(*facts.color.channels)
    white, black = Rgb(1.0, 1.0, 1.0), Rgb(0.0, 0.0, 0.0)
    up = (
        contrast(white, facts.background).value
        > contrast(black, facts.background).value
    )
    lo, hi = (lightness, 1.0) if up else (0.0, lightness)
    best = 1.0 if up else 0.0
    for _ in range(LIGHTNESS_STEPS):
        mid = (lo + hi) / 2.0
        if passes(facts, Lift(hue, mid, saturation, up).rgb()):
            best = mid
            hi, lo = (mid, lo) if up else (hi, mid)
        else:
            hi, lo = (hi, mid) if up else (mid, lo)
    return Lift(hue, best, saturation, up)


def readable(background: Rgb, light: Rgb, dark: Rgb) -> Ink:
    """The ink with the higher contrast on ``background``; light on a tie."""
    if contrast(light, background).value >= contrast(dark, background).value:
        return Ink.LIGHT
    return Ink.DARK


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
        case PaletteKind.CATEGORICAL:
            base = CATEGORICAL
        case PaletteKind.SEQUENTIAL:
            shades = range(3, 8) if few else range(1, 10)
            base = tuple(Name(f"oc.blue{i}") for i in shades)
        case PaletteKind.DIVERGING:
            base = DIVERGING_FEW if few else DIVERGING_MANY
    repeats = request.n // len(base) + 1
    return (base * repeats)[: request.n]
