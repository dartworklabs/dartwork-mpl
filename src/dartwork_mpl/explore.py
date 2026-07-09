"""Color, palette, and colormap exploration tools.

Provides utility functions for listing and visualizing the discrete
palettes and colormaps available in dartwork-mpl.

Lightweight listing/preview helpers live here; the heavier
``plot_colormaps`` / ``plot_colors`` / ``plot_fonts`` /
``classify_colormap`` diagnostics are re-exported from
:mod:`dartwork_mpl.diagnostics` for backwards compatibility.
"""

from __future__ import annotations

import re

import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

# Re-export asset diagnostics so ``dm.explore.plot_colormaps`` etc.
# keep working after the v0.3.x ``asset_viz`` → ``diagnostics`` rename.
from .diagnostics import (
    classify_colormap,
    plot_colormaps,
    plot_colors,
    plot_fonts,
)

__all__ = [
    "classify_colormap",
    "list_colormaps",
    "list_palettes",
    "plot_colormaps",
    "plot_colors",
    "plot_fonts",
    "show_palette",
]


def _is_light(color: str) -> bool:
    """True when ``color`` is light enough to need dark (black) label text.

    Uses WCAG relative luminance on the linearized sRGB channels so the
    decision holds for any palette scale, not just Open Color's 0-9.
    """
    r, g, b = mcolors.to_rgb(color)

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    return luminance > 0.4


def _get_all_colors() -> list[str]:
    from .colors._loader import ensure_loaded

    ensure_loaded()
    return list(mcolors.get_named_colors_mapping().keys())


def list_palettes() -> list[str]:
    """List all available discrete color palettes.

    Returns
    -------
    list[str]
        Sorted list of palette names (e.g., 'dc.teal', 'oc.blue').
    """
    colors: list[str] = _get_all_colors()
    palettes: set[str] = set()
    # match prefix.name + digits
    pattern: re.Pattern[str] = re.compile(r"^([a-z]+)\.([a-z][a-z_]*)\d+$")
    for c in colors:
        match = pattern.match(c)
        if match:
            # Skip the deprecated ``dm.*`` back-compat aliases — they
            # duplicate every ``dc.*`` palette and are not part of the
            # typed colour vocabulary.
            if match.group(1) == "dm":
                continue
            palettes.add(f"{match.group(1)}.{match.group(2)}")
    return sorted(palettes)


def list_colormaps(include_reversed: bool = False) -> list[str]:
    """List all registered dartwork colormaps.

    Parameters
    ----------
    include_reversed : bool, optional
        Whether to include reversed colormaps (names ending with '_r').
        Default is False.

    Returns
    -------
    list[str]
        Sorted list of registered colormap names.
    """
    cmaps: list[str] = [c for c in plt.colormaps() if c.startswith("dc.")]
    if not include_reversed:
        cmaps = [c for c in cmaps if not c.endswith("_r")]
    return sorted(cmaps)


def show_palette(palette_name: str) -> None:
    """Visually display the colors of a specific discrete palette.

    Renders all shades in the specified palette as a row of color
    swatches. Useful for previewing colors in Jupyter notebooks.

    Parameters
    ----------
    palette_name : str
        Name of the palette to visualize (e.g., 'dc.blue', 'oc.gray').

    Raises
    ------
    ValueError
        If the palette name does not exist or contains no numbered
        color entries.
    """
    colors: list[str] = _get_all_colors()
    # find all colors that start with palette_name followed by a number
    pattern: re.Pattern[str] = re.compile(rf"^{re.escape(palette_name)}(\d+)$")

    palette_colors: list[tuple[int, str]] = []
    for c in colors:
        match = pattern.match(c)
        if match:
            palette_colors.append((int(match.group(1)), c))

    if not palette_colors:
        raise ValueError(
            f"Palette '{palette_name}' not found or has no numbered shades."
        )

    palette_colors.sort(key=lambda x: x[0])
    color_names: list[str] = [c[1] for c in palette_colors]

    n: int = len(color_names)
    # The swatch grows horizontally with the palette size, so width is
    # computed at runtime; ``dm.figsize`` accepts a unit-string width +
    # explicit height to keep the dartwork-mpl physical-width contract
    # without forcing a single fixed value.
    from .units import figsize, inch  # local import to avoid cycle

    _fig, ax = plt.subplots(figsize=figsize(inch(n * 0.8), inch(1.2)))

    for i, cname in enumerate(color_names):
        ax.add_patch(
            mpatches.Rectangle((i, 0), 1, 1, facecolor=cname, edgecolor="none")
        )

        # Choose label colour by the swatch's actual luminance, not the
        # shade index - index thresholds assume Open Color's 0-9 scale and
        # put white text on the near-white 50/100/200 swatches of the
        # Tailwind (50-950) / Material / Ant (1-10) families.
        shade_idx = palette_colors[i][0]
        text_color = "black" if _is_light(cname) else "white"

        ax.text(
            i + 0.5,
            0.5,
            str(shade_idx),
            color=text_color,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(palette_name, loc="left", pad=10, fontweight="bold")

    for spine in ax.spines.values():
        spine.set_visible(False)

    from .layout import simple_layout  # local import to avoid cycle

    simple_layout(_fig)
    plt.show()
