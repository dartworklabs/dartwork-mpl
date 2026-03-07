"""Colormap visualization functions.

Functions for classifying and plotting colormaps.
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


def classify_colormap(cmap: "Colormap") -> str:
    """
    Classify a colormap into one of the following categories:
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
    # Get colormap samples
    n_samples = 256
    samples = cmap(np.linspace(0, 1, n_samples))[:, :3]  # Ignore alpha

    # Convert to HSV for easier analysis
    hsv_samples = np.array([mcolors.rgb_to_hsv(rgb) for rgb in samples])
    hues = hsv_samples[:, 0]
    saturations = hsv_samples[:, 1]
    values = hsv_samples[:, 2]

    # Calculate differences between consecutive samples
    hue_diffs = np.abs(np.diff(hues))
    # Handle circular nature of hue
    hue_diffs = np.minimum(hue_diffs, 1 - hue_diffs)

    # Known categorical colormaps (hardcoded for better accuracy)
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

    # 1. Check if colormap is cyclical - stricter criteria
    start_end_diff = np.sqrt(np.sum((samples[0] - samples[-1]) ** 2))
    if start_end_diff < 0.01:
        mid_idx = n_samples // 2
        mid_diff = np.sqrt(np.sum((samples[0] - samples[mid_idx]) ** 2))
        if mid_diff > 0.3:
            return "Cyclical"

    # 2. Improved check for categorical colormaps based on repeated colors
    color_diffs = np.sqrt(np.sum(np.diff(samples, axis=0) ** 2, axis=1))

    # Find regions where colors are very similar (plateaus)
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

    # Additional check for categorical: large jumps in color
    large_color_jumps = np.where(color_diffs > 0.1)[0]
    if len(large_color_jumps) > 3 and len(large_color_jumps) < n_samples // 8:
        jump_diffs = np.diff(large_color_jumps)
        if np.std(jump_diffs) < np.mean(jump_diffs) * 0.8:
            return "Categorical"

    # 3. Check if colormap is diverging
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

    # 4. Improved check for sequential single-hue vs multi-hue
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
    cmap_list: list[str] | list["Colormap"] | None = None,
    ncols: int = 3,
    group_by_type: bool = True,
    group_spacing: float = 0.5,
) -> tuple[Figure, np.ndarray]:
    """Plot a list of colormaps.

    When group_by_type=True, creates separate figures for each category
    and displays them automatically.

    Parameters
    ----------
    cmap_list : list, optional(default=None)
        List of colormap names.
    ncols : int, optional(default=3)
        Number of columns to display colormaps.
    group_by_type : bool, optional(default=True)
        If True, group colormaps by their type and create separate
        figures for each category.
    group_spacing : float, optional(default=0.5)
        Spacing between groups in inches (unused when
        group_by_type=True).

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object. When group_by_type=True, returns the last
        category's figure.
    axs : numpy.ndarray of matplotlib.axes.Axes
        Array of Axes objects.
    """
    from ..cmap import ensure_loaded as ensure_cmaps_loaded

    ensure_cmaps_loaded()

    if cmap_list is None:
        cmap_list = list(mpl.colormaps.keys())
        cmap_list = [c for c in cmap_list if not c.endswith("_r")]

    cmap_list = [
        mpl.cm.get_cmap(c) if isinstance(c, str) else c for c in cmap_list
    ]

    if group_by_type:
        category_order = [
            "Sequential Single-Hue",
            "Sequential Multi-Hue",
            "Diverging",
            "Cyclical",
            "Categorical",
        ]

        categories = {category: [] for category in category_order}

        for cmap in cmap_list:
            category = classify_colormap(cmap)
            categories[category].append(cmap)

        categories = {k: v for k, v in categories.items() if v}

        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))

        sorted_categories = [
            cat for cat in category_order if cat in categories
        ]

        fig = None
        axs = None

        for category in sorted_categories:
            cmaps = categories[category]

            cmaps.sort(
                key=lambda cmap: (
                    0 if cmap.name.startswith("dm.") else 1,
                    cmap.name.lower(),
                )
            )

            nrows = (len(cmaps) + ncols - 1) // ncols

            figw = 6.4 * ncols / 1.5
            figh = 0.35 + 0.15 + (nrows + 1 + (nrows + 1 - 1) * 0.1) * 0.44

            fig = plt.figure(figsize=(figw, figh))

            gs = plt.GridSpec(
                nrows + 1,
                ncols,
                figure=fig,
                height_ratios=[0.3] + [1] * nrows,
            )

            axs = []

            title_ax = fig.add_subplot(gs[0, :])
            title_ax.text(
                0.5,
                0.5,
                category,
                fontsize=14,
                fontweight="bold",
                ha="center",
                va="center",
                transform=title_ax.transAxes,
            )
            title_ax.set_axis_off()
            axs.append(title_ax)

            for i, cmap in enumerate(cmaps):
                row = i % nrows
                col = i // nrows
                ax = fig.add_subplot(gs[row + 1, col])
                ax.imshow(gradient, aspect="auto", cmap=cmap)
                ax.text(
                    -0.01,
                    0.5,
                    cmap.name,
                    va="center",
                    ha="right",
                    fontsize=10,
                    transform=ax.transAxes,
                )
                ax.set_axis_off()
                axs.append(ax)

            total_subplots = (nrows + 1) * ncols
            for i in range(len(axs), total_subplots):
                ax = fig.add_subplot(gs[i // ncols, i % ncols])
                ax.set_visible(False)

            plt.tight_layout()
            plt.show()

        if axs is not None:
            axs = np.array(axs)

    else:
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))

        cmap_list.sort(
            key=lambda cmap: (
                0 if cmap.name.startswith("oc.") else 1,
                cmap.name.lower(),
            )
        )

        nrows = (len(cmap_list) + ncols - 1) // ncols

        figw = 6.4 * ncols / 1.5
        figh = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.44
        fig, axs = plt.subplots(
            nrows=nrows, ncols=ncols, figsize=(figw, figh)
        )
        fig.subplots_adjust(
            top=1 - 0.35 / figh,
            bottom=0.15 / figh,
            left=0.2 / ncols,
            right=0.99,
        )

        if nrows == 1 and ncols == 1:
            axs = np.array([axs])

        axs = axs.flatten()

        for i, cmap in enumerate(cmap_list):
            if i < len(axs):
                row = i % nrows
                col = i // nrows
                ax_idx = row * ncols + col
                if ax_idx < len(axs):
                    ax = axs[ax_idx]
                    ax.imshow(gradient, aspect="auto", cmap=cmap)
                    ax.text(
                        -0.01,
                        0.5,
                        cmap.name,
                        va="center",
                        ha="right",
                        fontsize=10,
                        transform=ax.transAxes,
                    )

        for ax in axs:
            ax.set_axis_off()

        for i in range(len(cmap_list), len(axs)):
            axs[i].set_visible(False)

        plt.tight_layout()

    return fig, axs
