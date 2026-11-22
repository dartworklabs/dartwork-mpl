"""Pure decisions on colour values: compositing, WCAG contrast, a lift,
and how much of a text's ink reads on what is behind it.

A colour painted over another is mixed by its alpha; the contrast of two is
WCAG's ratio of their luminances; a foreground that misses a target ratio is
lifted (darkened or lightened in HLS lightness) by the least that reaches it.
A text reads while no window of it has lost half its ink to a background
under the floor ratio.
"""

from __future__ import annotations

import colorsys

import numpy as np

from .model import (
    Colours,
    ContrastFacts,
    DarkInk,
    Faint,
    Ink,
    Legibility,
    Lift,
    LightInk,
    Places,
    Ratio,
    Ratios,
    Rgb,
    Rgba,
)

LIGHTNESS_STEPS = 32
#: A window with fewer ink pixels than this share of the text's median
#: window (the gap between two words, a comma) is not judged on its own.
#: A window is one unit of a text's length and may start at any ink pixel,
#: so no band is missed for straddling the edge of a fixed one.
SPARSE = 0.25
#: The faintest ink is the one this share of the text's ink is fainter than:
#: a stray antialiased pixel is not the text.
FAINTEST = 0.02


def composite_over(top: Rgba, below: Rgb) -> Rgb:
    """``top`` painted over the opaque ``below``."""
    alpha = top.alpha
    r, g, b = (
        alpha * t + (1.0 - alpha) * u
        for t, u in zip(top.rgb.channels, below.channels, strict=True)
    )
    return Rgb(r, g, b)


# -- contrast ------------------------------------------------------------------


def contrast(first: Rgb, second: Rgb) -> Ratio:
    """The WCAG contrast ratio of two colours, lighter over darker."""
    hi, lo = sorted(
        (first.wcag_luminance(), second.wcag_luminance()), reverse=True
    )
    return Ratio((hi + 0.05) / (lo + 0.05))


def contrasts(first: Colours, second: Colours) -> Ratios:
    """The WCAG contrast ratio of each pair of colours, row by row.

    The same arithmetic as :func:`contrast`, on arrays: either argument
    may be one colour (three channels) against many rows.
    """

    def luminance(colours: Colours) -> Ratios:
        linear = np.where(
            colours <= 0.04045,
            colours / 12.92,
            ((colours + 0.055) / 1.055) ** 2.4,
        )
        return linear @ np.array([0.2126, 0.7152, 0.0722])

    one, two = luminance(first), luminance(second)
    return (np.maximum(one, two) + 0.05) / (np.minimum(one, two) + 0.05)


def _windows(low: Faint, places: Places) -> Ratios:
    """The share of faint ink in each window of the text that is judged.

    A window is 1.0 long, on one line, and slides. The share changes only
    where an ink pixel enters or leaves the window, so every whole window
    that starts at an ink pixel and every one that ends at one is tried; a
    line shorter than a window is one window. A window with too little ink
    to judge (:data:`SPARSE`) is left out.
    """
    counts: list[Ratios] = []
    faint: list[Ratios] = []
    for line in np.unique(places[:, 1]):
        on = places[:, 1] == line
        order = np.argsort(places[on, 0], kind="stable")
        along = places[on, 0][order]
        lost = np.concatenate([[0.0], np.cumsum(low[on][order])])
        starts = np.unique(along[along <= along[-1] - 1.0])
        ends = np.unique(along[along >= along[0] + 1.0])
        first = np.concatenate(
            [
                np.searchsorted(along, starts, side="left"),
                np.searchsorted(along, ends - 1.0, side="right"),
                [0],
            ]
        )
        end = np.concatenate(
            [
                np.searchsorted(along, starts + 1.0, side="left"),
                np.searchsorted(along, ends, side="right"),
                [len(along)],
            ]
        )
        whole = len(starts) + len(ends)
        first, end = (first[:-1], end[:-1]) if whole else (first, end)
        counts.append((end - first).astype(float))
        faint.append(lost[end] - lost[first])
    inked, lost_ink = np.concatenate(counts), np.concatenate(faint)
    judged = inked >= max(1.0, SPARSE * float(np.median(inked)))
    return lost_ink[judged] / inked[judged]


def legibility(
    ink: Colours, paper: Colours, places: Places, floor: Ratio
) -> Legibility:
    """How much of a text reads: its ink pixels against what is behind each.

    ``ink`` and ``paper`` hold one colour per ink pixel and ``places``
    where along the text each pixel lies. ``worst`` is the faintest window
    wherever it starts (:func:`_windows`). No pixels at all: a text that
    reads, at 21:1.
    """
    if not len(ink):
        white, black = Rgb(1.0, 1.0, 1.0), Rgb(0.0, 0.0, 0.0)
        return Legibility(0.0, 0.0, Ratio(21.0), black, white)
    ratios = contrasts(ink, paper)
    low = ratios < floor.value
    at = int(np.argsort(ratios)[int(FAINTEST * (len(ratios) - 1))])
    return Legibility(
        low=float(np.mean(low)),
        worst=float(np.max(_windows(low, places))),
        lowest=Ratio(float(ratios[at])),
        ink=Rgb(*(float(c) for c in ink[at])),
        paper=Rgb(*(float(c) for c in paper[at])),
    )


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
        return LightInk()
    return DarkInk()
