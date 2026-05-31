"""Asset diagnostics — visualize registered colormaps, colors, and fonts.

This module houses the four visualization helpers that inspect the
available dartwork-mpl assets:

- :func:`classify_colormap` — categorize a matplotlib colormap.
- :func:`plot_colormaps` — render registered colormaps grouped by type.
- :func:`plot_colors` — render named color libraries (OpenColor,
  Tailwind, Material Design, etc.) as swatch grids.
- :func:`plot_fonts` — render registered font families with weight
  spectrum and pangram samples.

These functions used to live in the :mod:`dartwork_mpl.asset_viz`
subpackage. That import path still works but emits a
:class:`DeprecationWarning`; prefer importing from
:mod:`dartwork_mpl` directly or from this module.
"""

from __future__ import annotations

import math
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.colors import Colormap


__all__ = ["classify_colormap", "plot_colormaps", "plot_colors", "plot_fonts"]


# =============================================================================
# Colormaps
# =============================================================================


# ---------------------------------------------------------------------------
# Category badge colors (background, text)
# ---------------------------------------------------------------------------
_CATEGORY_STYLE: dict[str, tuple[str, str]] = {
    "Single-Hue": ("#e3f2fd", "#1565c0"),
    "Multi-Hue": ("#e8f5e9", "#2e7d32"),
    "Diverging": ("#fff3e0", "#e65100"),
    "Cyclical": ("#f3e5f5", "#7b1fa2"),
    "Categorical": ("#fce4ec", "#c62828"),
}


# Override classification for standard dartwork customized maps
# 30+ maps mapped into 5 core types
_CLASSIFICATION_OVERRIDES: dict[str, str] = {
    # Single-Hue
    "dc.obsidian": "Single-Hue",
    "dc.sapphire": "Single-Hue",
    "dc.emerald": "Single-Hue",
    "dc.ruby": "Single-Hue",
    "dc.amethyst": "Single-Hue",
    "dc.topaz": "Single-Hue",
    "dc.graphite": "Single-Hue",
    "dc.coral": "Single-Hue",
    # Multi-Hue
    "dc.aurora": "Multi-Hue",
    "dc.sunset_glow": "Multi-Hue",
    "dc.plasma_arc": "Multi-Hue",
    "dc.spring_bloom": "Multi-Hue",
    "dc.deep_sea": "Multi-Hue",
    "dc.autumn_leaf": "Multi-Hue",
    "dc.nebula_dust": "Multi-Hue",
    "dc.tropical_fruit": "Multi-Hue",
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
    - Single-Hue
    - Multi-Hue
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
                return "Single-Hue"
            return "Multi-Hue"

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
        return "Single-Hue"
    if hue_range > 0.01:
        return "Multi-Hue"
    if np.std(hue_diffs) < 0.02:
        return "Single-Hue"
    return "Multi-Hue"


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
    from .cmap import ensure_loaded as ensure_cmaps_loaded

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
        "Single-Hue",
        "Multi-Hue",
        "Diverging",
        "Cyclical",
        "Categorical",
    ]

    categories: dict[str, list[Any]] = {cat: [] for cat in category_order}
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
    cmaps: list[Any], category: str, gradient: np.ndarray[Any, Any], ncols: int
) -> Figure:
    """Draw a single category figure with badge header."""
    nrows = (len(cmaps) + ncols - 1) // ncols

    figw = 6.4 * ncols / 1.5
    figh = 0.35 + 0.15 + (nrows + 1 + (nrows) * 0.1) * 0.44

    fig = plt.figure(figsize=(figw, figh))

    gs = mpl.gridspec.GridSpec(
        nrows + 1, ncols, figure=fig, height_ratios=[0.35, *([1] * nrows)]
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


def _plot_flat(
    cmap_list: list[Any], gradient: np.ndarray[Any, Any], ncols: int
) -> Figure:
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


# =============================================================================
# Color libraries
# =============================================================================


def _load_color_library_names() -> set[str]:
    """Load color names from oc.txt file."""
    asset_dir = Path(__file__).parent / "asset" / "color"
    opencolor_names: set[str] = set()

    opencolor_file = asset_dir / "oc.txt"
    if opencolor_file.exists():
        with open(opencolor_file) as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and ":" in line:
                    name = line.split(":")[0].strip()
                    opencolor_names.add(name)

    return opencolor_names


# Cache the color library names
_OPENCOLOR_NAMES = _load_color_library_names()


def _classify_color_library(color_name: str) -> str | None:
    """Classify a color name into its library category."""
    if color_name.startswith("dc."):
        return "dc"
    if color_name.startswith("tw."):
        return "tw"
    if color_name.startswith("md."):
        return "md"
    if color_name.startswith("ad."):
        return "ant"
    if color_name.startswith("cu."):
        return "chakra"
    if color_name.startswith("pr."):
        return "primer"
    if color_name.startswith("oc."):
        return "opencolor"
    return None


def _extract_base_color_name(color_name: str) -> str:
    """Extract base color name from color name."""
    name = color_name
    for prefix in ["dc.", "oc.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    match = re.search(r"^([a-z]+)\d+$", name)
    if match:
        return match.group(1)

    return name


def _extract_number_from_color_name(color_name: str) -> int | None:
    """Extract number from color name if present."""
    name = color_name
    for prefix in ["dc.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    match = re.search(r"(\d+)$", name)
    if match:
        return int(match.group(1))

    return None


def _detect_weight_range(color_names: list[str]) -> tuple[int, int] | None:
    """Detect the weight range used in a group of color names."""
    weights = []
    for color_name in color_names:
        weight = _extract_number_from_color_name(color_name)
        if weight is not None:
            weights.append(weight)

    if weights:
        return (min(weights), max(weights))
    return None


def _remove_duplicate_colors(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, str | tuple[float, float, float]]:
    """Remove duplicate colors based on RGB values."""
    seen_rgb: dict[tuple[float, ...], str] = {}
    result: dict[str, str | tuple[float, float, float]] = {}

    def _try_rgb_key(
        spec: str | tuple[float, float, float],
    ) -> tuple[float, ...] | None:
        try:
            rgb = mcolors.to_rgb(spec)
        except (ValueError, TypeError):
            return None
        return tuple(round(c, 6) for c in rgb)

    for color_name, color_spec in colors.items():
        rgb_key = _try_rgb_key(color_spec)
        if rgb_key is None:
            result[color_name] = color_spec
            continue
        if rgb_key not in seen_rgb:
            seen_rgb[rgb_key] = color_name
            result[color_name] = color_spec

    return result


def _separate_colors_by_library(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, dict[str, str | tuple[float, float, float]]]:
    """Separate colors by library."""
    library_groups: dict[str, dict[str, str | tuple[float, float, float]]] = {
        "dc": {},
        "opencolor": {},
        "tw": {},
        "md": {},
        "ant": {},
        "chakra": {},
        "primer": {},
    }

    for color_name, color_spec in colors.items():
        library = _classify_color_library(color_name)
        if library is not None:
            library_groups[library][color_name] = color_spec

    return {
        lib: colors_dict
        for lib, colors_dict in library_groups.items()
        if colors_dict
    }


def _relative_luminance(color_spec: str | tuple[float, float, float]) -> float:
    """Compute relative luminance of a color (ITU-R BT.709).

    Parameters
    ----------
    color_spec : str or tuple
        Color specification accepted by matplotlib.

    Returns
    -------
    float
        Relative luminance in [0, 1].
    """
    r, g, b = mcolors.to_rgb(color_spec)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_text_color(color_spec: str | tuple[float, float, float]) -> str:
    """Return black or white text color for best contrast.

    Parameters
    ----------
    color_spec : str or tuple
        Background color.

    Returns
    -------
    str
        ``"white"`` or ``"#333333"`` depending on background
        luminance.
    """
    return "#333333" if _relative_luminance(color_spec) > 0.45 else "white"


def _color_to_hex(color_spec: str | tuple[float, float, float]) -> str:
    """Convert any color spec to uppercase hex string.

    Parameters
    ----------
    color_spec : str or tuple
        Color specification accepted by matplotlib.

    Returns
    -------
    str
        Uppercase hex string like ``"#3B82F6"``.
    """
    return mcolors.to_hex(color_spec).upper()


def _plot_single_library(
    colors: dict[str, str | tuple[float, float, float]],
    library_name: str,
    ncols: int = 6,
    sort_colors: bool = True,
    show_hex: bool = True,
) -> Figure | None:
    """Plot colors for a single library.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specs.
    library_name : str
        Library identifier key (e.g. ``"tw"``, ``"opencolor"``).
    ncols : int
        Number of columns.
    sort_colors : bool
        Sort by base color name and weight.
    show_hex : bool
        Show hex value beneath color name.

    Returns
    -------
    Figure or None
        The created figure, or *None* when *colors* is empty.
    """
    if not colors:
        return None

    cell_width = 220
    cell_height = 22 if not show_hex else 30
    swatch_width = 48
    swatch_height = 20
    margin = 12
    rounding = 3

    # ------------------------------------------------------------------
    # Group and sort
    # ------------------------------------------------------------------
    if sort_colors:
        base_color_groups: dict[str, list[Any]] = defaultdict(list)
        for color_name in colors:
            base_color = _extract_base_color_name(color_name)
            try:
                rgb = mcolors.to_rgb(colors[color_name])
                hsv = mcolors.rgb_to_hsv(rgb)
                base_color_groups[base_color].append((color_name, hsv))
            except (ValueError, TypeError):
                base_color_groups[base_color].append((color_name, (0, 0, 0)))

        sorted_base_colors = sorted(base_color_groups.items())

        color_groups: list[dict[str, Any]] = []
        for base_color, color_items in sorted_base_colors:

            def sort_key(x: tuple[str, Any]) -> tuple[int, float]:
                color_name, hsv = x
                number = _extract_number_from_color_name(color_name)
                if number is not None:
                    return (0, number)
                return (1, -hsv[2])

            color_items.sort(key=sort_key)
            sorted_names = [name for name, _ in color_items]

            weight_range = _detect_weight_range(sorted_names)

            color_groups.append(
                {
                    "base_color": base_color,
                    "colors": [(name, colors[name]) for name in sorted_names],
                    "weight_range": weight_range,
                }
            )
    else:
        color_groups = [
            {
                "base_color": "all",
                "colors": [(name, colors[name]) for name in colors],
                "weight_range": None,
            }
        ]

    # ------------------------------------------------------------------
    # Column bin-packing
    # ------------------------------------------------------------------
    title_height = cell_height + 4
    title_margin = 0.5

    color_grid: list[
        tuple[int, int, str, str | tuple[float, float, float]]
    ] = []
    column_heights = [0] * ncols
    prev_weight_range = None
    prev_base_color_per_col: list[str | None] = [None] * ncols

    for group in color_groups:
        group_colors = group["colors"]
        current_weight_range = group.get("weight_range")
        current_base_color = group.get("base_color")

        min_height_col = min(range(ncols), key=lambda c: column_heights[c])
        target_col = min_height_col

        should_add_spacing = False

        if (
            prev_weight_range is not None
            and current_weight_range is not None
            and prev_weight_range != current_weight_range
        ):
            should_add_spacing = True

        if (
            prev_base_color_per_col[target_col] is not None
            and prev_base_color_per_col[target_col] != current_base_color
        ):
            column_heights[target_col] += 1

        if should_add_spacing:
            for col in range(ncols):
                column_heights[col] += 1

        for _idx, (name, color_spec) in enumerate(group_colors):
            row = column_heights[target_col]
            color_grid.append((target_col, row, name, color_spec))
            column_heights[target_col] += 1

        prev_weight_range = current_weight_range
        prev_base_color_per_col[target_col] = current_base_color

    nrows = max(column_heights) if column_heights else 0

    # ------------------------------------------------------------------
    # Figure setup
    # ------------------------------------------------------------------
    width = cell_width * ncols + 2 * margin
    total_title_height = title_height + title_margin * cell_height
    bottom_extra_margin = 0.5 * cell_height
    height = (
        cell_height * nrows
        + 2 * margin
        + total_title_height
        + bottom_extra_margin
    )
    dpi = 72

    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    fig.subplots_adjust(
        margin / width,
        margin / height,
        (width - margin) / width,
        (height - margin) / height,
    )
    ax.set_xlim(0, cell_width * ncols)
    ax.set_ylim(-total_title_height, cell_height * nrows + bottom_extra_margin)
    ax.invert_yaxis()
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_axis_off()

    # ------------------------------------------------------------------
    # Title with divider
    # ------------------------------------------------------------------
    library_labels = {
        "opencolor": "Open Color",
        "tw": "Tailwind CSS",
        "md": "Material Design",
        "ant": "Ant Design",
        "chakra": "Chakra UI",
        "primer": "Primer",
    }
    title_text = library_labels.get(library_name, library_name)
    count_text = f"  ({len(colors)} colors)"
    title_y = -title_height / 2

    ax.text(
        cell_width * ncols / 2,
        title_y - 2,
        title_text,
        fontsize=15,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
        color="#1a1a2e",
    )
    ax.text(
        cell_width * ncols / 2 + len(title_text) * 4.5,
        title_y - 2,
        count_text,
        fontsize=10,
        horizontalalignment="left",
        verticalalignment="center",
        color="#888888",
    )

    # Divider line beneath title
    divider_y = title_y + title_height / 2 - 2
    ax.plot(
        [0, cell_width * ncols],
        [divider_y, divider_y],
        color="#e0e0e0",
        linewidth=0.8,
        zorder=0,
    )

    # ------------------------------------------------------------------
    # Draw color swatches
    # ------------------------------------------------------------------
    title_margin_offset = title_margin * cell_height
    for col, row, name, color_spec in color_grid:
        y = title_margin_offset + (row + 0.5) * cell_height
        swatch_start_x = cell_width * col
        text_pos_x = cell_width * col + swatch_width + 8

        # Rounded swatch
        try:
            patch = FancyBboxPatch(
                (swatch_start_x, y - swatch_height / 2),
                swatch_width,
                swatch_height,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                facecolor=color_spec,
                edgecolor="#d0d0d0",
                linewidth=0.5,
            )
            ax.add_patch(patch)
        except (ValueError, TypeError):
            # Fallback for invalid colors
            pass

        # Hex overlay on swatch
        if show_hex:
            try:
                hex_str = _color_to_hex(color_spec)
                text_color = _contrast_text_color(color_spec)
                ax.text(
                    swatch_start_x + swatch_width / 2,
                    y,
                    hex_str,
                    fontsize=6.5,
                    fontweight="bold",
                    horizontalalignment="center",
                    verticalalignment="center",
                    color=text_color,
                    alpha=0.85,
                )
            except (ValueError, TypeError):
                pass

        # Color name
        ax.text(
            text_pos_x,
            y - (3 if show_hex else 0),
            name,
            fontsize=11,
            horizontalalignment="left",
            verticalalignment="center",
            color="#1a1a2e",
        )

        # Hex label beneath name
        if show_hex:
            try:
                hex_str = _color_to_hex(color_spec)
                ax.text(
                    text_pos_x,
                    y + 8,
                    hex_str,
                    fontsize=8,
                    horizontalalignment="left",
                    verticalalignment="center",
                    color="#999999",
                )
            except (ValueError, TypeError):
                pass

    return fig


def plot_colors(
    colors: dict[str, str | tuple[float, float, float]] | None = None,
    *,
    ncols: int = 4,
    sort_colors: bool = True,
    show_hex: bool = True,
) -> list[Figure]:
    """Plot a grid of named colors with their names and hex values.

    Creates separate figures for each color library (Open Color,
    Tailwind, Material Design, Ant Design, Chakra UI, Primer, Other).

    Parameters
    ----------
    colors : dict, optional
        Dictionary mapping color names to color specifications.
        If None, uses all named colors from matplotlib except those
        starting with ``'dartwork_mpl.'`` or ``'xkcd:'``.
    ncols : int, optional
        Number of columns in the color grid, default is 4.
    sort_colors : bool, optional
        If True, sorts colors by base color name, then by weight or
        HSV value.
    show_hex : bool, optional
        If True, shows the hex color value beneath each color name
        and overlaid on the swatch.  Default True.

    Returns
    -------
    list of matplotlib.figure.Figure
        List of figures, one for each color library.
    """
    if colors is None:
        colors = {
            k: v  # type: ignore[misc]
            for k, v in mcolors.get_named_colors_mapping().items()
            if not k.startswith("dartwork_mpl.") and not k.startswith("xkcd:")
        }

    library_colors = _separate_colors_by_library(colors)

    skip_duplicate_removal = {"dc", "tw", "md", "ant", "chakra", "primer"}
    for library_name in library_colors:
        if library_name not in skip_duplicate_removal:
            library_colors[library_name] = _remove_duplicate_colors(
                library_colors[library_name]
            )

    library_order = ["dc", "opencolor", "tw", "md", "ant", "chakra", "primer"]

    figures = []
    for library_name in library_order:
        if library_name in library_colors:
            fig = _plot_single_library(
                library_colors[library_name],
                library_name,
                ncols=ncols,
                sort_colors=sort_colors,
                show_hex=show_hex,
            )
            if fig is not None:
                figures.append(fig)

    return figures


# =============================================================================
# Fonts
# =============================================================================


_WEIGHT_ORDER: dict[str, int] = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}

_PANGRAM = "The dartwork designs beautiful data artworks since 2021. 0123456789"


def _parse_font_weight(font_file: str) -> tuple[str, bool]:
    """Extract weight name and italic flag from a font filename.

    Parameters
    ----------
    font_file : str
        Font filename like ``"Inter-BoldItalic.ttf"``.

    Returns
    -------
    tuple[str, bool]
        ``(weight_name, is_italic)``
    """
    base = os.path.splitext(font_file)[0]
    # Handle Paperlogy naming: "Paperlogy-7Bold" etc.
    if "-" in base:
        parts = base.split("-", 1)
        style_part = parts[1] if len(parts) > 1 else ""
    else:
        style_part = base

    is_italic = "Italic" in style_part
    # Remove "Italic" to isolate weight
    weight_part = style_part.replace("Italic", "")

    # Strip leading digits (Paperlogy uses "1Thin", "7Bold", etc.)
    weight_part = re.sub(r"^\d+", "", weight_part)

    if not weight_part:
        weight_part = "Regular"

    return weight_part, is_italic


def _weight_sort_key(weight_name: str) -> int:
    """Return numeric sort key for a weight name."""
    return _WEIGHT_ORDER.get(weight_name, 400)


def plot_fonts(
    font_dir: str | None = None, ncols: int = 2, font_size: int = 11
) -> Figure:
    """Plot available font families with weight spectrum and samples.

    Each font family is displayed as a titled section showing:
    - Family header with file count
    - Each weight rendered with pangram sample text
    - Italic variants shown inline with lighter color

    Parameters
    ----------
    font_dir : str, optional
        Directory path containing font files. If None, defaults to the
        ``asset/font`` directory within the package.
    ncols : int, optional
        Number of columns to display font families, by default 2.
    font_size : int, optional
        Font size for sample text, by default 11.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object.
    """
    if font_dir is None:
        font_dir = os.path.join(os.path.dirname(__file__), "asset", "font")

    # Collect font files
    extensions = {".ttf", ".otf"}
    font_files = [
        f
        for f in os.listdir(font_dir)
        if os.path.splitext(f)[1].lower() in extensions
    ]

    # Group by family
    font_families: dict[str, list[str]] = defaultdict(list)
    for font in font_files:
        family = font.split("-")[0]
        font_families[family].append(font)

    # For each family, group by weight and separate italic
    family_data: list[dict[str, Any]] = []

    for family_name, files in sorted(font_families.items()):
        weight_groups: dict[str, dict[str, str | None]] = defaultdict(
            lambda: {"roman": None, "italic": None}
        )

        for f in files:
            weight_name, is_italic = _parse_font_weight(f)
            slot = "italic" if is_italic else "roman"
            weight_groups[weight_name][slot] = f

        # Sort by weight
        sorted_weights = sorted(
            weight_groups.items(), key=lambda x: _weight_sort_key(x[0])
        )

        weights = []
        for weight_name, variants in sorted_weights:
            weights.append(
                {
                    "name": weight_name,
                    "roman": variants["roman"],
                    "italic": variants["italic"],
                }
            )

        n_files = len(files)
        n_weights = len(weights)
        family_data.append(
            {
                "family": family_name,
                "n_files": n_files,
                "n_weights": n_weights,
                "weights": weights,
            }
        )

    # ------------------------------------------------------------------
    # Layout calculation
    # ------------------------------------------------------------------
    total_families = len(family_data)
    families_per_column = math.ceil(total_families / ncols)

    # Height per weight line + header
    header_line_height = 1.8
    weight_line_height = 1.3
    family_gap = 1.5

    # Calculate max height needed for any column
    col_heights = [0.0] * ncols
    family_col_map: list[int] = []

    for idx, fam in enumerate(family_data):
        col = idx // families_per_column
        if col >= ncols:
            col = ncols - 1
        family_col_map.append(col)
        n_lines = len(fam["weights"])
        col_heights[col] += (
            header_line_height + n_lines * weight_line_height + family_gap
        )

    total_height = max(col_heights) if col_heights else 10
    col_width = 7.5

    fig, ax = plt.subplots(
        figsize=(col_width * ncols, total_height * 0.32 + 0.5)
    )

    ax.set_xlim(0, col_width * ncols)
    ax.set_ylim(0, total_height + 0.5)
    ax.axis("off")

    # ------------------------------------------------------------------
    # Draw families
    # ------------------------------------------------------------------
    col_cursors = [total_height] * ncols

    for idx, fam in enumerate(family_data):
        col = family_col_map[idx]
        x_pos = col * col_width
        cursor = col_cursors[col]

        family_name = fam["family"]
        n_files = fam["n_files"]
        n_weights = fam["n_weights"]

        # --- Family header ---
        cursor -= 0.3
        header_text = f"{family_name}"
        meta_text = f"  {n_weights} weights · {n_files} files"

        ax.text(
            x_pos, cursor, header_text, size=13, weight="bold", color="#1a1a2e"
        )
        ax.text(
            x_pos + len(family_name) * 0.08 + 0.05,
            cursor,
            meta_text,
            size=9,
            color="#888888",
            verticalalignment="baseline",
        )

        # Divider
        cursor -= 0.35
        ax.plot(
            [x_pos, x_pos + col_width - 0.5],
            [cursor, cursor],
            color="#e0e0e0",
            linewidth=0.6,
        )
        cursor -= 0.2

        # --- Weight lines ---
        for w in fam["weights"]:
            cursor -= weight_line_height

            weight_name = w["name"]
            roman_file = w["roman"]
            italic_file = w["italic"]

            # Weight label
            weight_num = _WEIGHT_ORDER.get(weight_name, "")
            label = (
                f"{weight_name} ({weight_num})" if weight_num else weight_name
            )

            # Draw label
            ax.text(
                x_pos,
                cursor + 0.5,
                label,
                size=8,
                color="#999999",
                verticalalignment="center",
            )

            # Draw sample text with actual font
            sample_x = x_pos + 2.0

            if roman_file is not None:
                font_path = os.path.join(font_dir, roman_file)
                try:
                    font_prop = fm.FontProperties(fname=font_path)
                    ax.text(
                        sample_x,
                        cursor + 0.5,
                        _PANGRAM,
                        fontproperties=font_prop,
                        size=font_size,
                        color="#1a1a2e",
                        verticalalignment="center",
                        clip_on=True,
                    )
                except Exception:  # noqa: BLE001
                    ax.text(
                        sample_x,
                        cursor + 0.5,
                        f"({roman_file})",
                        size=font_size - 2,
                        color="#cccccc",
                        verticalalignment="center",
                    )

            # Italic indicator
            if italic_file is not None:
                ax.text(
                    x_pos + col_width - 0.8,
                    cursor + 0.5,
                    "I",
                    size=9,
                    color="#4a90d9",
                    fontstyle="italic",
                    fontweight="bold",
                    verticalalignment="center",
                    horizontalalignment="center",
                    alpha=0.7,
                )

        cursor -= family_gap
        col_cursors[col] = cursor

    return fig
