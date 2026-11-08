"""Catalogue swatch labels pick their ink by WCAG contrast, not a second luminance."""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

from dartwork_mpl._colors.contrast import composite_over, contrast_ratio
from dartwork_mpl._colors.diagnostics import _colors

_INKS = ("white", "#333333")


def _oracle_luminance(color: str) -> float:
    """Independent WCAG 2.x relative luminance (sRGB linearised)."""

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in mcolors.to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _oracle_ratio(a: str, b: str) -> float:
    hi, lo = sorted((_oracle_luminance(a), _oracle_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize(
    ("background", "ink"),
    [
        ("#000000", "white"),
        ("#ffffff", "#333333"),
        # Mid-tones the retired gamma-weighted heuristic labelled #333333
        # although white contrasts more.
        ("#737373", "white"),
        ("#3b82f6", "white"),
        ("#1686e0", "white"),
        # Saturated mid-tones it labelled white although #333333 contrasts more.
        ("#ec4899", "#333333"),
        ("#f4511e", "#333333"),
        ("#00ff00", "#333333"),
        ("#ff0000", "white"),
    ],
)
def test_swatch_ink_is_the_higher_contrast_of_the_two_inks(
    background: str, ink: str
) -> None:
    other = _INKS[1] if ink == _INKS[0] else _INKS[0]
    assert _oracle_ratio(ink, background) >= _oracle_ratio(other, background)
    assert _colors._contrast_text_color(background) == ink


def test_every_registered_library_colour_gets_the_higher_contrast_ink() -> None:
    named = mcolors.get_named_colors_mapping()
    prefixes = tuple(lib.prefix for lib in _colors.COLOR_LIBRARIES)
    checked = 0
    for name, spec in named.items():
        if not name.startswith(prefixes):
            continue
        hexv = mcolors.to_hex(spec)
        chosen = _colors._contrast_text_color(spec)
        assert chosen in _INKS
        other = _INKS[1] if chosen == _INKS[0] else _INKS[0]
        assert _oracle_ratio(chosen, hexv) >= _oracle_ratio(other, hexv), name
        checked += 1
    assert checked > 1000


def test_no_second_brightness_kernel_remains() -> None:
    assert not hasattr(_colors, "_text_brightness")
    assert not hasattr(_colors, "_relative_luminance")


def test_catalogue_overlay_uses_the_picked_ink() -> None:
    colors = {"tw.blue500": "#3b82f6", "tw.pink500": "#ec4899"}
    figs = _colors.render_color_catalog(colors)
    try:
        overlays = {
            t.get_text(): t.get_color()
            for t in figs[0].axes[0].texts
            if t.get_fontsize() == 6.5
        }
    finally:
        for fig in figs:
            plt.close(fig)
    assert overlays == {"#3B82F6": "white", "#EC4899": "#333333"}


def test_catalogue_hex_overlays_are_opaque_and_read_at_three_to_one() -> None:
    """Every swatch's hex text is drawn opaque (D3, 2026-11-08: alpha 0.85
    left eight swatches below 3:1); what is seen, the ink composited at the
    text's alpha over the swatch, reads at 3:1 or more on every swatch."""
    figs = _colors.render_color_catalog()
    try:
        overlays = [
            t
            for fig in figs
            for t in fig.axes[0].texts
            if t.get_fontsize() == 6.5
        ]
        assert len(overlays) > 1000
        weakest = 21.0
        for t in overlays:
            assert t.get_alpha() in (None, 1.0), t.get_text()
            swatch = mcolors.to_rgb(t.get_text())
            alpha = 1.0 if t.get_alpha() is None else t.get_alpha()
            seen = composite_over(
                (*mcolors.to_rgb(t.get_color()), alpha), swatch
            )
            ratio = contrast_ratio(seen, swatch)
            assert ratio >= 3.0, (t.get_text(), ratio)
            weakest = min(weakest, ratio)
    finally:
        for fig in figs:
            plt.close(fig)
    # White and #333333 meet at 3.56:1 on the swatch where they tie.
    assert weakest == pytest.approx(3.556, abs=0.001)
