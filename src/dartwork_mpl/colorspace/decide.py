"""Pure decisions on colour values: compositing, WCAG contrast, a lift.

A colour painted over another is mixed by its alpha; the contrast of two is
WCAG's ratio of their luminances; a foreground that misses a target ratio is
lifted (darkened or lightened in HLS lightness) by the least that reaches it.
"""

from __future__ import annotations

import colorsys

from .model import ContrastFacts, DarkInk, Ink, Lift, LightInk, Ratio, Rgb, Rgba

LIGHTNESS_STEPS = 32


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
        return LightInk()
    return DarkInk()
