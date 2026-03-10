"""Colormap visualization functions.

Functions for classifying and plotting colormaps with category
badges and row-major layout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from matplotlib.colors import Colormap


# ---------------------------------------------------------------------------
# Category badge colors (background, text)
# ---------------------------------------------------------------------------
_CATEGORY_STYLE: dict[str, tuple[str, str]] = {
    "Sequential Single-Hue": ("#e3f2fd", "#1565c0"),
    "Sequential Multi-Hue": ("#e8f5e9", "#2e7d32"),
    "Diverging": ("#fff3e0", "#e65100"),
    "Cyclical": ("#f3e5f5", "#7b1fa2"),
    "Categorical": ("#fce4ec", "#c62828"),
}


# Override classification for standard dartwork customized maps
# 30+ maps mapped into 5 core types
_CLASSIFICATION_OVERRIDES: dict[str, str] = {
    # Sequential Single-Hue
    "dc.obsidian": "Sequential Single-Hue",
    "dc.sapphire": "Sequential Single-Hue",
    "dc.emerald": "Sequential Single-Hue",
    "dc.ruby": "Sequential Single-Hue",
    "dc.amethyst": "Sequential Single-Hue",
    "dc.topaz": "Sequential Single-Hue",
    "dc.graphite": "Sequential Single-Hue",
    "dc.coral": "Sequential Single-Hue",

    # Sequential Multi-Hue
    "dc.aurora": "Sequential Multi-Hue",
    "dc.sunset_glow": "Sequential Multi-Hue",
    "dc.plasma_arc": "Sequential Multi-Hue",
    "dc.spring_bloom": "Sequential Multi-Hue",
    "dc.deep_sea": "Sequential Multi-Hue",
    "dc.autumn_leaf": "Sequential Multi-Hue",
    "dc.nebula_dust": "Sequential Multi-Hue",
    "dc.tropical_fruit": "Sequential Multi-Hue",

    # Diverging
    "dc.ice_fire": "Diverging",
    "dc.earth_sky": "Diverging",
    "dc.teal_rose": "Diverging",
    "dc.purple_lime": "Diverging",
    "dc.navy_gold": "Diverging",
    "dc.forest_brick": "Diverging",
    "dc.magenta_cyan": "Diverging",
    "dc.slate_orange": "Diverging",
    "dc.cool_warm": "Diverging",
    "dc.arctic_heat": "Diverging",
    "dc.frost_flame": "Diverging",
    "dc.water_fire": "Diverging",
    "dc.spring_autumn": "Diverging",
    "dc.summer_winter": "Diverging",
    "dc.electric_surge": "Diverging",
    "dc.neon_pulse": "Diverging",

    # Cyclical
    "dc.twilight_oklch": "Cyclical",
    "dc.phase_wheel": "Cyclical",
    "dc.color_wheel": "Cyclical",
    "dc.seasons": "Cyclical",
    "dc.day_night": "Cyclical",
    "dc.rainbow_cycle": "Cyclical",
    "dc.neon_wheel": "Cyclical",
    "dc.electric_cycle": "Cyclical",

    # Discrete
    "dc.vivid": "Categorical",
    "dc.lucid": "Categorical",
    "dc.chalk": "Categorical",
    "dc.vibrant": "Categorical",
    "dc.pastel": "Categorical",
    "dc.candy": "Categorical",
    "dc.pop": "Categorical",
    "dc.macaron": "Categorical",
}

def classify_colormap(cmap: Colormap) -> str:
    """Classify a colormap into one of the following categories.

    Categories
    ----------
    - Categorical
    - Sequential Single-Hue
    - Sequential Multi-Hue
    - Diverging
    - Cyclical

    Parameters
    ----------
    cmap : matplotlib.colors.Colormap
        Colormap to classify.

    Returns
    -------
    str
        Category of the colormap.
    """
    if hasattr(cmap, "name") and cmap.name in _CLASSIFICATION_OVERRIDES:
        return _CLASSIFICATION_OVERRIDES[cmap.name]
        
    n_samples = 256
    samples = cmap(np.linspace(0, 1, n_samples))[:, :3]

    hsv_samples = np.array([mcolors.rgb_to_hsv(rgb) for rgb in samples])
    hues = hsv_samples[:, 0]
    saturations = hsv_samples[:, 1]
    values = hsv_samples[:, 2]

    hue_diffs = np.abs(np.diff(hues))
    hue_diffs = np.minimum(hue_diffs, 1 - hue_diffs)

    # Known categorical colormaps
    categorical_cmaps = [
        "Accent",
        "Dark2",
        "Paired",
        "Pastel1",
        "Pastel2",
        "Set1",
        "Set2",
        "Set3",
        "tab10",
        "tab20",
        "tab20b",
        "tab20c",
        "Spectral",
        "prism",
        "hsv",
        "gist_rainbow",
        "rainbow",
        "nipy_spectral",
    ]

    if hasattr(cmap, "name") and cmap.name in categorical_cmaps:
        return "Categorical"

    # Cyclical check
    start_end_diff = np.sqrt(np.sum((samples[0] - samples[-1]) ** 2))
    if start_end_diff < 0.01:
        mid_idx = n_samples // 2
        mid_diff = np.sqrt(np.sum((samples[0] - samples[mid_idx]) ** 2))
        if mid_diff > 0.3:
            return "Cyclical"

    # Categorical by plateau detection
    color_diffs = np.sqrt(np.sum(np.diff(samples, axis=0) ** 2, axis=1))
    plateau_mask = color_diffs < 0.001
    plateau_indices = np.where(plateau_mask)[0]

    if len(plateau_indices) > 0:
        plateau_runs = np.split(
            plateau_indices, np.where(np.diff(plateau_indices) != 1)[0] + 1
        )
        significant_plateaus = [run for run in plateau_runs if len(run) >= 3]
        if len(significant_plateaus) >= 3:
            plateau_positions = [np.mean(run) for run in significant_plateaus]
            position_range = max(plateau_positions) - min(plateau_positions)
            if position_range > n_samples * 0.3:
                return "Categorical"

    # Categorical by large jumps
    large_color_jumps = np.where(color_diffs > 0.1)[0]
    if len(large_color_jumps) > 3 and len(large_color_jumps) < n_samples // 8:
        jump_diffs = np.diff(large_color_jumps)
        if np.std(jump_diffs) < np.mean(jump_diffs) * 0.8:
            return "Categorical"

    # Diverging check
    mid_idx = n_samples // 2
    mid_value = values[mid_idx]
    start_value = values[0]
    end_value = values[-1]

    if (mid_value > start_value + 0.2 and mid_value > end_value + 0.2) or (
        mid_value < start_value - 0.2 and mid_value < end_value - 0.2
    ):
        start_hue = hues[0]
        end_hue = hues[-1]
        hue_diff = min(abs(end_hue - start_hue), 1 - abs(end_hue - start_hue))
        if hue_diff > 0.1:
            return "Diverging"

    # Sequential single vs multi-hue
    high_sat_indices = np.where(saturations > 0.3)[0]

    if len(high_sat_indices) > n_samples // 4:
        high_sat_hues = hues[high_sat_indices]

        if len(high_sat_hues) > 1:
            hue_min = np.min(high_sat_hues)
            hue_max = np.max(high_sat_hues)
            hue_range = hue_max - hue_min
            if hue_range > 0.5:
                hue_range = 1 - hue_range

            if hue_range < 0.01:
                return "Sequential Single-Hue"
            else:
                return "Sequential Multi-Hue"

    hue_min = np.min(hues)
    hue_max = np.max(hues)
    hue_range = hue_max - hue_min
    if hue_range > 0.5:
        hue_range = 1 - hue_range

    is_monotonic = np.all(
        np.diff(values[: n_samples // 2]) * np.diff(values[n_samples // 2 :])
        >= 0
    )

    if hue_range < 0.01 and is_monotonic:
        return "Sequential Single-Hue"
    elif hue_range > 0.01:
        return "Sequential Multi-Hue"
    else:
        if np.std(hue_diffs) < 0.02:
            return "Sequential Single-Hue"
        else:
            return "Sequential Multi-Hue"


def plot_colormaps(
    cmap_list: list[str] | list[Colormap] | None = None,
    ncols: int = 3,
    group_by_type: bool = True,
) -> list[Figure]:
    """Plot colormaps grouped by type.

    Returns a list of figures, one per category.  Does **not** call
    ``plt.show()`` — the caller decides when to display.

    Parameters
    ----------
    cmap_list : list, optional
        List of colormap names or objects.  Defaults to all registered
        colormaps (excluding ``_r`` reversed variants).
    ncols : int, optional
        Number of columns, default 3.
    group_by_type : bool, optional
        If True, group colormaps by their classified type and return
        one figure per category.  Otherwise return a single figure.

    Returns
    -------
    list of matplotlib.figure.Figure
        One figure per category (or a single-element list when
        *group_by_type* is False).
    """
    from ..cmap import ensure_loaded as ensure_cmaps_loaded

    ensure_cmaps_loaded()

    if cmap_list is None:
        cmap_list = list(mpl.colormaps.keys())
        cmap_list = [c for c in cmap_list if not c.endswith("_r")]

    cmap_list = [
        mpl.colormaps.get_cmap(c) if isinstance(c, str) else c
        for c in cmap_list
    ]

    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    if not group_by_type:
        return [_plot_flat(cmap_list, gradient, ncols)]

    # ----- Group by category -----
    category_order = [
        "Sequential Single-Hue",
        "Sequential Multi-Hue",
        "Diverging",
        "Cyclical",
        "Categorical",
    ]

    categories: dict[str, list] = {cat: [] for cat in category_order}
    for cmap in cmap_list:
        category = classify_colormap(cmap)
        categories[category].append(cmap)

    categories = {k: v for k, v in categories.items() if v}

    figures: list[Figure] = []

    for category in category_order:
        if category not in categories:
            continue

        cmaps = categories[category]
        cmaps.sort(key=lambda c: c.name.lower())

        fig = _plot_category(cmaps, category, gradient, ncols)
        figures.append(fig)

    return figures


# ---------------------------------------------------------------------------
# Internal drawing helpers
# ---------------------------------------------------------------------------


def _plot_category(
    cmaps: list, category: str, gradient: np.ndarray, ncols: int
) -> Figure:
    """Draw a single category figure with badge header."""
    nrows = (len(cmaps) + ncols - 1) // ncols

    figw = 6.4 * ncols / 1.5
    figh = 0.35 + 0.15 + (nrows + 1 + (nrows) * 0.1) * 0.44

    fig = plt.figure(figsize=(figw, figh))

    gs = plt.GridSpec(
        nrows + 1, ncols, figure=fig, height_ratios=[0.35] + [1] * nrows
    )

    # --- Category title with badge ---
    title_ax = fig.add_subplot(gs[0, :])
    bg_color, text_color = _CATEGORY_STYLE.get(category, ("#f5f5f5", "#333333"))

    title_ax.set_facecolor(bg_color)
    count_str = f"  ({len(cmaps)})"
    title_ax.text(
        0.5,
        0.5,
        category,
        fontsize=14,
        fontweight="bold",
        color=text_color,
        ha="center",
        va="center",
        transform=title_ax.transAxes,
    )
    title_ax.text(
        0.5 + len(category) * 0.012,
        0.5,
        count_str,
        fontsize=10,
        color=text_color,
        alpha=0.7,
        ha="left",
        va="center",
        transform=title_ax.transAxes,
    )
    title_ax.set_axis_off()

    # --- Colormap strips (row-major order) ---
    for i, cmap in enumerate(cmaps):
        row = i // ncols
        col = i % ncols
        ax = fig.add_subplot(gs[row + 1, col])
        ax.imshow(gradient, aspect="auto", cmap=cmap)

        ax.text(
            -0.01,
            0.5,
            cmap.name,
            va="center",
            ha="right",
            fontsize=10,
            color="#333333",
            transform=ax.transAxes,
        )
        ax.set_axis_off()

    # Hide empty cells
    total_subplots = (nrows + 1) * ncols
    used = 1 + len(cmaps)  # title + cmap axes
    for i in range(used, total_subplots):
        r = i // ncols
        c = i % ncols
        if r <= nrows and c < ncols:
            ax = fig.add_subplot(gs[r, c])
            ax.set_visible(False)

    fig.subplots_adjust(
        left=0.15 / ncols,
        right=0.99,
        top=1 - 0.2 / figh,
        bottom=0.1 / figh,
        hspace=0.15,
    )

    return fig


def _plot_flat(cmap_list: list, gradient: np.ndarray, ncols: int) -> Figure:
    """Draw all colormaps in a single figure without grouping."""
    cmap_list.sort(key=lambda c: c.name.lower())

    nrows = (len(cmap_list) + ncols - 1) // ncols

    figw = 6.4 * ncols / 1.5
    figh = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.44
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.subplots_adjust(
        top=1 - 0.35 / figh, bottom=0.15 / figh, left=0.2 / ncols, right=0.99
    )

    if nrows == 1 and ncols == 1:
        axs = np.array([axs])

    axs_flat = axs.flatten()

    # Row-major order
    for i, cmap in enumerate(cmap_list):
        row = i // ncols
        col = i % ncols
        ax_idx = row * ncols + col
        if ax_idx < len(axs_flat):
            ax = axs_flat[ax_idx]
            ax.imshow(gradient, aspect="auto", cmap=cmap)
            ax.text(
                -0.01,
                0.5,
                cmap.name,
                va="center",
                ha="right",
                fontsize=10,
                color="#333333",
                transform=ax.transAxes,
            )

    for ax in axs_flat:
        ax.set_axis_off()

    for i in range(len(cmap_list), len(axs_flat)):
        axs_flat[i].set_visible(False)

    fig.subplots_adjust(
        left=0.15 / ncols,
        right=0.99,
        top=1 - 0.2 / figh,
        bottom=0.1 / figh,
        hspace=0.15,
    )

    return fig
