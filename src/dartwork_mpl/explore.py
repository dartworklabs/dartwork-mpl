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


def _get_all_colors() -> list[str]:
    from .colors._loader import ensure_loaded

    ensure_loaded()
    return list(mcolors.get_named_colors_mapping().keys())


def list_palettes() -> list[str]:
    """List all available discrete color palettes.

    Returns
    -------
    list[str]
        Sorted list of palette names (e.g., 'dc.vivid', 'oc.blue').
    """
    colors: list[str] = _get_all_colors()
    palettes: set[str] = set()
    # match prefix.name + digits
    pattern: re.Pattern[str] = re.compile(
        r"^([a-z]+)\.([a-z]+(?:\-[a-z]+)?)\d+$"
    )
    for c in colors:
        match = pattern.match(c)
        if match:
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
    from .cmap import ensure_loaded

    ensure_loaded()
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
        Name of the palette to visualize (e.g., 'dc.acid', 'oc.gray').

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
    _fig, ax = plt.subplots(figsize=(n * 0.8, 1.2))

    for i, cname in enumerate(color_names):
        ax.add_patch(
            mpatches.Rectangle((i, 0), 1, 1, facecolor=cname, edgecolor="none")
        )

        # Simple contrast heuristic: lighter text for darker shades (index >= 5 usually)
        shade_idx = palette_colors[i][0]
        text_color = "white" if shade_idx >= 5 else "black"

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

    plt.tight_layout()
    plt.show()
