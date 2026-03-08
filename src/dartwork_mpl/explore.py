"""Exploration tools for colors, palettes, and colormaps.

Provides utility functions to list and visualize available color palettes
and colormaps from the dartwork-mpl library.
"""

from __future__ import annotations

import re

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

__all__ = ["list_palettes", "list_colormaps", "show_palette"]


def _get_all_colors() -> list[str]:
    from .color._loader import ensure_loaded

    ensure_loaded()
    return list(mcolors.get_named_colors_mapping().keys())


def list_palettes() -> list[str]:
    """Retrieve a list of available discrete color palettes.

    Returns
    -------
    list[str]
        A sorted list of palette names (e.g. 'dc.vivid', 'oc.blue').
    """
    colors: list[str] = _get_all_colors()
    palettes: set[str] = set()
    # match prefix.name + digits
    pattern: re.Pattern[str] = re.compile(r"^([a-z]+)\.([a-z]+(?:\-[a-z]+)?)\d+$")
    for c in colors:
        match = pattern.match(c)
        if match:
            palettes.add(f"{match.group(1)}.{match.group(2)}")
    return sorted(palettes)


def list_colormaps(include_reversed: bool = False) -> list[str]:
    """Retrieve a list of available custom dartwork-mpl colormaps.

    Parameters
    ----------
    include_reversed : bool, default=False
        Whether to include the reverse colormaps (ending with '_r').

    Returns
    -------
    list[str]
        A sorted list of registered colormap names.
    """
    from .cmap import ensure_loaded

    ensure_loaded()
    cmaps: list[str] = [c for c in plt.colormaps() if c.startswith("dc.")]
    if not include_reversed:
        cmaps = [c for c in cmaps if not c.endswith("_r")]
    return sorted(cmaps)


def show_palette(palette_name: str) -> None:
    """Visualize a specific discrete palette.

    Plots a row of colored rectangles corresponding to the shades of
    the specified palette.

    Parameters
    ----------
    palette_name : str
        The name of the palette to visualize (e.g., 'dc.acid').

    Raises
    ------
    ValueError
        If the palette name is not found or has no numbered shades.
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
    fig, ax = plt.subplots(figsize=(n * 0.8, 1.2))

    for i, cname in enumerate(color_names):
        ax.add_patch(
            plt.Rectangle(
                (i, 0),
                1,
                1,
                facecolor=cname,
                edgecolor="none",
            )
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
