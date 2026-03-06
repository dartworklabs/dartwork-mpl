"""Asset visualization functions for dartwork-mpl.

This module provides functions to visualize available colormaps, colors,
and fonts in the matplotlib/dartwork-mpl ecosystem.
"""

import math
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

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
    # Cyclical maps start and end with almost identical colors
    start_end_diff = np.sqrt(np.sum((samples[0] - samples[-1]) ** 2))
    if start_end_diff < 0.01:  # Stricter threshold
        # Also check if there's significant variation in the middle
        mid_idx = n_samples // 2
        mid_diff = np.sqrt(np.sum((samples[0] - samples[mid_idx]) ** 2))
        if mid_diff > 0.3:  # Ensure there's variation in the middle
            return "Cyclical"

    # 2. Improved check for categorical colormaps based on repeated colors
    # Calculate color differences (Euclidean distance in RGB space)
    color_diffs = np.sqrt(np.sum(np.diff(samples, axis=0) ** 2, axis=1))

    # Find regions where colors are very similar (plateaus)
    plateau_mask = color_diffs < 0.001
    plateau_indices = np.where(plateau_mask)[0]

    # Find consecutive plateaus (runs of similar colors)
    if len(plateau_indices) > 0:
        # Split into runs of consecutive indices
        plateau_runs = np.split(
            plateau_indices, np.where(np.diff(plateau_indices) != 1)[0] + 1
        )

        # Count significant plateaus (runs longer than a threshold)
        significant_plateaus = [run for run in plateau_runs if len(run) >= 3]

        # If we have multiple significant plateaus, it's likely categorical
        if len(significant_plateaus) >= 3:
            # Check if plateaus are distributed throughout the colormap
            plateau_positions = [np.mean(run) for run in significant_plateaus]
            position_range = max(plateau_positions) - min(plateau_positions)

            if (
                position_range > n_samples * 0.3
            ):  # Plateaus are well distributed
                return "Categorical"

    # Additional check for categorical: large jumps in color
    large_color_jumps = np.where(color_diffs > 0.1)[0]
    if len(large_color_jumps) > 3 and len(large_color_jumps) < n_samples // 8:
        # Check if jumps are distributed (not all clustered)
        jump_diffs = np.diff(large_color_jumps)
        if (
            np.std(jump_diffs) < np.mean(jump_diffs) * 0.8
        ):  # Relatively evenly spaced jumps
            return "Categorical"

    # 3. Check if colormap is diverging
    # Diverging maps have a distinct middle with different values at ends
    mid_idx = n_samples // 2
    mid_value = values[mid_idx]
    start_value = values[0]
    end_value = values[-1]

    # Check if the middle is significantly different from the ends
    if (mid_value > start_value + 0.2 and mid_value > end_value + 0.2) or (
        mid_value < start_value - 0.2 and mid_value < end_value - 0.2
    ):
        # Also check if the hue changes significantly from start to end
        start_hue = hues[0]
        end_hue = hues[-1]
        hue_diff = min(abs(end_hue - start_hue), 1 - abs(end_hue - start_hue))
        if hue_diff > 0.1:  # Significant hue change
            return "Diverging"

    # 4. Improved check for sequential single-hue vs multi-hue
    # Focus on high saturation regions for better hue analysis
    high_sat_indices = np.where(saturations > 0.3)[0]

    # If we have enough high saturation samples
    if len(high_sat_indices) > n_samples // 4:
        high_sat_hues = hues[high_sat_indices]

        # Calculate hue range for high saturation colors
        if len(high_sat_hues) > 1:
            # Get the circular range of hues
            hue_min = np.min(high_sat_hues)
            hue_max = np.max(high_sat_hues)
            hue_range = hue_max - hue_min
            if hue_range > 0.5:  # Account for circular hue
                hue_range = 1 - hue_range

            # Stricter criteria for single-hue: very narrow hue range
            if hue_range < 0.01:  # Much stricter threshold
                return "Sequential Single-Hue"
            else:
                return "Sequential Multi-Hue"

    # If we couldn't decide based on high saturation, look at overall pattern

    # Calculate overall hue variation, accounting for circularity
    hue_min = np.min(hues)
    hue_max = np.max(hues)
    hue_range = hue_max - hue_min
    if hue_range > 0.5:  # Account for circular hue
        hue_range = 1 - hue_range

    # Check for monotonic value change (typical for sequential)
    is_monotonic = np.all(
        np.diff(values[: n_samples // 2]) * np.diff(values[n_samples // 2 :])
        >= 0
    )

    if hue_range < 0.01 and is_monotonic:
        return "Sequential Single-Hue"
    elif hue_range > 0.01:
        return "Sequential Multi-Hue"
    else:
        # For borderline cases, check the standard deviation of hue differences
        if np.std(hue_diffs) < 0.02:  # Very consistent hue changes
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
    When group_by_type=True, creates separate figures for each category and
    displays them automatically.
    Original source code:
    https://matplotlib.org/stable/users/explain/colors/colormaps.html

    Parameters
    ----------
    cmap_list : list, optional(default=None)
        List of colormap names.
    ncols : int, optional(default=3)
        Number of columns to display colormaps.
    group_by_type : bool, optional(default=True)
        If True, group colormaps by their type and create separate figures
        for each category. Each figure is automatically displayed.
    group_spacing : float, optional(default=0.5)
        Spacing between groups in inches (unused when group_by_type=True).

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object. When group_by_type=True, returns the last category's
        figure.
    axs : numpy.ndarray of matplotlib.axes.Axes
        Array of Axes objects. When group_by_type=True, returns the last
        category's axes.

    Examples
    --------
    >>> fig, axs = plot_colormaps(['viridis', 'plasma', 'inferno'], ncols=3)
    >>> plt.show()
    >>> # Group by type - creates separate figures for each category
    >>> fig, axs = plot_colormaps(ncols=3, group_by_type=True)
    """
    from .cmap import ensure_loaded as ensure_cmaps_loaded

    ensure_cmaps_loaded()

    if cmap_list is None:
        cmap_list = list(mpl.colormaps.keys())
        cmap_list = [c for c in cmap_list if not c.endswith("_r")]

    # Convert colormaps to matplotlib colormaps if cmap is a string.
    cmap_list = [
        mpl.cm.get_cmap(c) if isinstance(c, str) else c for c in cmap_list
    ]

    if group_by_type:
        # Define category order
        category_order = [
            "Sequential Single-Hue",
            "Sequential Multi-Hue",
            "Diverging",
            "Cyclical",
            "Categorical",
        ]

        # Classify colormaps by type
        categories = {category: [] for category in category_order}

        for cmap in cmap_list:
            category = classify_colormap(cmap)
            categories[category].append(cmap)

        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v}

        # Create gradient for colormap display
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))

        # Sort categories according to the defined order
        sorted_categories = [cat for cat in category_order if cat in categories]

        # Create a separate figure for each category
        fig = None
        axs = None

        for category in sorted_categories:
            cmaps = categories[category]

            # Sort colormaps: dm prefix first, then alphabetical order
            cmaps.sort(
                key=lambda cmap: (
                    0 if cmap.name.startswith("dm.") else 1,
                    cmap.name.lower(),
                )
            )

            # Calculate number of rows needed for this category
            nrows = (len(cmaps) + ncols - 1) // ncols

            # Create figure with appropriate size for this category
            figw = 6.4 * ncols / 1.5  # Adjust width based on number of columns
            # Add extra height for category title
            figh = 0.35 + 0.15 + (nrows + 1 + (nrows + 1 - 1) * 0.1) * 0.44

            # Create a new figure for this category
            fig = plt.figure(figsize=(figw, figh))

            # Create GridSpec with one extra row for the title
            gs = plt.GridSpec(
                nrows + 1, ncols, figure=fig, height_ratios=[0.3] + [1] * nrows
            )

            axs = []

            # Add category title
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

            # Add colormaps for this category (column-major order: top to bottom)
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

            # Hide unused subplots
            total_subplots = (nrows + 1) * ncols
            for i in range(len(axs), total_subplots):
                ax = fig.add_subplot(gs[i // ncols, i % ncols])
                ax.set_visible(False)

            plt.tight_layout()

            # Automatically display each category figure
            plt.show()

        # Convert axs to numpy array for consistency with non-grouped version
        if axs is not None:
            axs = np.array(axs)

    else:
        # Original non-grouped implementation
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))

        # Sort colormaps: oc prefix first, then alphabetical order
        cmap_list.sort(
            key=lambda cmap: (
                0 if cmap.name.startswith("oc.") else 1,
                cmap.name.lower(),
            )
        )

        # Calculate number of rows based on number of colormaps and columns
        nrows = (len(cmap_list) + ncols - 1) // ncols

        # Create figure and adjust figure dimensions based on layout
        figw = 6.4 * ncols / 1.5  # Adjust width based on number of columns
        figh = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.44
        fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
        fig.subplots_adjust(
            top=1 - 0.35 / figh,
            bottom=0.15 / figh,
            left=0.2 / ncols,
            right=0.99,
        )

        # Handle case when axs is a single Axes object (when nrows=ncols=1)
        if nrows == 1 and ncols == 1:
            axs = np.array([axs])

        # Flatten axs array for easier iteration
        axs = axs.flatten()

        # Map colormaps to subplots in column-major order (top to bottom)
        for i, cmap in enumerate(cmap_list):
            if i < len(axs):
                # Calculate position in column-major order
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

        # Turn off all ticks & spines
        for ax in axs:
            ax.set_axis_off()

        # Hide unused subplots
        for i in range(len(cmap_list), len(axs)):
            axs[i].set_visible(False)

        plt.tight_layout()

    return fig, axs


def _load_color_library_names() -> set[str]:
    """
    Load color names from oc.txt file.

    Returns
    -------
    opencolor_names : set
        Set of opencolor color names (without prefix).
    """
    # Get the asset/color directory path
    asset_dir = Path(__file__).parent / "asset" / "color"

    opencolor_names = set()

    # Load opencolor colors
    opencolor_file = asset_dir / "oc.txt"
    if opencolor_file.exists():
        with open(opencolor_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if ":" in line:
                        name = line.split(":")[0].strip()
                        opencolor_names.add(name)

    return opencolor_names


# Cache the color library names
_OPENCOLOR_NAMES = _load_color_library_names()


def _classify_color_library(color_name: str) -> str:
    """
    Classify a color name into its library category.

    Parameters
    ----------
    color_name : str
        Color name to classify.

    Returns
    -------
    str
        Library category: 'opencolor', 'tw', 'md', 'ant', 'chakra',
        'primer', 'other'. Note: 'ad.', 'cu.', 'pr.' prefixes map to
        'ant', 'chakra', 'primer' categories respectively.
    """
    # Check for tw. prefix
    if color_name.startswith("tw."):
        return "tw"

    # Check for md. prefix (Material Design)
    if color_name.startswith("md."):
        return "md"

    # Check for ad. prefix (Ant Design)
    if color_name.startswith("ad."):
        return "ant"

    # Check for cu. prefix (Chakra UI)
    if color_name.startswith("cu."):
        return "chakra"

    # Check for pr. prefix (Primer)
    if color_name.startswith("pr."):
        return "primer"

    # Check for oc. prefix
    if color_name.startswith("oc."):
        return "opencolor"

    return "other"


def _detect_color_weight_system(color_names: list[str]) -> int | None:
    """
    Detect the weight system used in a group of color names.

    Parameters
    ----------
    color_names : list
        List of color names (may contain prefix like 'dm.', 'tw.', etc.)

    Returns
    -------
    int or None
        The minimum weight value (lightest color), or None if no numbers
        found.
    """
    weights = []
    for color_name in color_names:
        weight = _extract_number_from_color_name(color_name)
        if weight is not None:
            weights.append(weight)

    if weights:
        return min(weights)
    return None


def _detect_weight_range(color_names: list[str]) -> tuple[int, int] | None:
    """
    Detect the weight range used in a group of color names.

    Parameters
    ----------
    color_names : list
        List of color names (may contain prefix like 'dm.', 'tw.', etc.)

    Returns
    -------
    tuple or None
        Tuple of (min_weight, max_weight), or None if no weights found.
    """
    weights = []
    for color_name in color_names:
        weight = _extract_number_from_color_name(color_name)
        if weight is not None:
            weights.append(weight)

    if weights:
        return (min(weights), max(weights))
    return None


def _extract_base_color_name(color_name: str) -> str:
    """
    Extract base color name from color name.

    Parameters
    ----------
    color_name : str
        Color name (may contain prefix like 'dm.', 'tw.', etc.)

    Returns
    -------
    str
        Base color name (e.g., 'neutral', 'red', 'dark blue')
    """
    # Remove prefixes
    name = color_name
    for prefix in ["oc.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    # Pattern 1: format with number (tw.blue500, md.blue500, ad.blue5, etc.)
    # -> 'blue'
    # Extract base color name by removing trailing digits
    match = re.search(r"^([a-z]+)\d+$", name)
    if match:
        return match.group(1)

    # Pattern 2: other colors - keep full name
    return name


def _extract_number_from_color_name(color_name: str) -> int | None:
    """
    Extract number from color name if present.

    Parameters
    ----------
    color_name : str
        Color name (may contain prefix like 'dm.', 'tw.', etc.)

    Returns
    -------
    int or None
        Extracted number, or None if no number found.
    """
    # Remove prefixes
    name = color_name
    for prefix in ["dm.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    # Try to extract number from patterns like:
    # - gray0, red1 (opencolor)
    # - blue500, gray200 (tailwind, material design, chakra)
    # - blue5, red6 (ant design, primer)
    # - red5, blue2 (opencolor)

    # Extract trailing digits
    match = re.search(r"(\d+)$", name)
    if match:
        return int(match.group(1))

    return None


def _remove_duplicate_colors(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, str | tuple[float, float, float]]:
    """
    Remove duplicate colors based on RGB values.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specifications.

    Returns
    -------
    dict
        Dictionary with duplicate colors removed (keeps first occurrence).
    """
    seen_rgb = {}
    result = {}

    for color_name, color_spec in colors.items():
        try:
            rgb = mcolors.to_rgb(color_spec)
            # Convert RGB tuple to string for comparison
            rgb_key = tuple(
                round(c, 6) for c in rgb
            )  # Round to avoid floating point issues

            if rgb_key not in seen_rgb:
                seen_rgb[rgb_key] = color_name
                result[color_name] = color_spec
        except (ValueError, TypeError):
            # If color conversion fails, keep it
            result[color_name] = color_spec

    return result


def _separate_colors_by_library(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, dict[str, str | tuple[float, float, float]]]:
    """
    Separate colors by library.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specifications.

    Returns
    -------
    dict
        Dictionary mapping library names to color dictionaries.
    """
    library_groups = {
        "opencolor": {},
        "tw": {},
        "md": {},
        "ant": {},
        "chakra": {},
        "primer": {},
        "other": {},
    }

    for color_name, color_spec in colors.items():
        library = _classify_color_library(color_name)
        library_groups[library][color_name] = color_spec

    # Remove empty libraries
    return {
        lib: colors_dict
        for lib, colors_dict in library_groups.items()
        if colors_dict
    }


def _sort_colors_by_library(
    colors: dict[str, str | tuple[float, float, float]],
) -> list[tuple[str, str | tuple[float, float, float]]]:
    """
    Sort colors by library, then by base color name and number/brightness.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specifications.

    Returns
    -------
    list
        Sorted list of color names with library titles.
    """
    # Group colors by library
    library_groups = {
        "opencolor": [],
        "tw": [],
        "md": [],
        "ant": [],
        "chakra": [],
        "primer": [],
        "other": [],
    }

    for color_name in colors:
        library = _classify_color_library(color_name)
        library_groups[library].append(color_name)

    # Sort each library group
    sorted_names = []

    # Library order: opencolor -> tw -> md -> ant -> chakra -> primer -> other
    library_labels = {
        "opencolor": "OpenColor Colors",
        "tw": "Tailwind Colors",
        "md": "Material Design Colors",
        "ant": "Ant Design Colors",
        "chakra": "Chakra UI Colors",
        "primer": "Primer Colors",
        "other": "Other Colors",
    }

    for library in [
        "opencolor",
        "tw",
        "md",
        "ant",
        "chakra",
        "primer",
        "other",
    ]:
        color_list = library_groups[library]

        if not color_list:
            continue

        # Add library title
        sorted_names.append(("__TITLE__", library_labels[library]))

        # Group by base color name (e.g., 'neutral', 'red', 'blue')
        base_color_groups = defaultdict(list)
        for color_name in color_list:
            base_color = _extract_base_color_name(color_name)
            try:
                rgb = mcolors.to_rgb(colors[color_name])
                hsv = mcolors.rgb_to_hsv(rgb)
                base_color_groups[base_color].append((color_name, hsv))
            except (ValueError, TypeError):
                # If color conversion fails, put in a default group
                base_color_groups[base_color].append((color_name, (0, 0, 0)))

        # Sort base color groups alphabetically
        sorted_base_colors = sorted(base_color_groups.items())

        # Sort within each base color group
        for _, color_items in sorted_base_colors:
            # Sort by: number (if present), otherwise by HSV value (brightness)
            def sort_key(x):
                color_name, hsv = x
                number = _extract_number_from_color_name(color_name)
                if number is not None:
                    # If number exists, sort by number only (small -> large)
                    return (0, number)
                else:
                    # If no number, sort by HSV value (bright -> dark)
                    return (1, -hsv[2])  # Negative value for descending order

            color_items.sort(key=sort_key)

            sorted_names.extend(
                [(name, colors[name]) for name, _ in color_items]
            )

    return sorted_names


def _group_colors_by_hue(
    colors: dict[str, str | tuple[float, float, float]],
) -> list[
    dict[
        str,
        str | list[tuple[str, str | tuple[float, float, float]]] | None | float,
    ]
]:
    """
    Group colors by HSV hue ranges for better visual organization.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specifications.

    Returns
    -------
    list of dict
        List of color groups, each containing 'base_color', 'colors', and
        'min_weight'. Groups are sorted by average hue.
    """
    # Define hue ranges for color groups (in degrees, 0-360)
    # Hue wraps around, so we handle reds specially (0-30 and 330-360)
    hue_ranges = [
        ("red", [(0, 30), (330, 360)]),
        ("orange", [(30, 50)]),
        ("yellow", [(50, 90)]),
        ("green", [(90, 150)]),
        ("cyan", [(150, 180)]),
        ("blue", [(180, 240)]),
        ("purple", [(240, 270)]),
        ("pink", [(270, 330)]),
    ]

    # Also handle grayscale colors (low saturation)
    color_items = []
    for color_name, color_spec in colors.items():
        try:
            rgb = mcolors.to_rgb(color_spec)
            hsv = mcolors.rgb_to_hsv(rgb)
            color_items.append((color_name, color_spec, hsv))
        except (ValueError, TypeError):
            color_items.append((color_name, color_spec, (0, 0, 0)))

    # Separate grayscale colors (saturation < 0.1)
    grayscale = []
    colored = []
    for name, spec, hsv in color_items:
        if hsv[1] < 0.1:  # Low saturation = grayscale
            grayscale.append((name, spec, hsv))
        else:
            colored.append((name, spec, hsv))

    # Group colored items by hue ranges
    hue_groups = defaultdict(list)
    for name, spec, hsv in colored:
        hue = hsv[0] * 360  # Convert to degrees
        assigned = False
        for group_name, ranges in hue_ranges:
            for min_hue, max_hue in ranges:
                # Handle red group which spans 0-30 and 330-360
                if group_name == "red":
                    if (0 <= hue < 30) or (330 <= hue < 360):
                        hue_groups[group_name].append((name, spec, hsv))
                        assigned = True
                        break
                elif min_hue <= hue < max_hue:
                    hue_groups[group_name].append((name, spec, hsv))
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            # Fallback: assign to nearest group
            hue_groups["other"].append((name, spec, hsv))

    # Add grayscale group
    if grayscale:
        hue_groups["grayscale"] = grayscale

    # Sort groups by average hue, and colors within groups by brightness/value
    color_groups = []

    for group_name, items in hue_groups.items():
        if not items:
            continue

        # Calculate average hue for group (for sorting)
        if group_name == "grayscale":
            avg_hue = (
                -1
            )  # Grayscale goes first (negative to sort before others)
        elif group_name == "other":
            avg_hue = 1000  # Other goes last
        else:
            hues = [hsv[0] * 360 for _, _, hsv in items]
            # Normalize hues for red group (handle wrap-around)
            if group_name == "red":
                normalized_hues = [h if h < 180 else h - 360 for h in hues]
                avg_hue = sum(normalized_hues) / len(normalized_hues)
            else:
                avg_hue = sum(hues) / len(hues)

        # Sort within group by brightness/value (light to dark)
        items.sort(
            key=lambda x: -x[2][2]
        )  # Sort by value (brightness), descending

        color_groups.append(
            {
                "base_color": group_name,
                "colors": [(name, spec) for name, spec, _ in items],
                "min_weight": None,  # Not applicable for hue-based grouping
                "avg_hue": avg_hue,
            }
        )

    # Sort groups by average hue (grayscale first, then by hue order)
    color_groups.sort(key=lambda g: g["avg_hue"])

    return color_groups


def _plot_single_library(
    colors: dict[str, str | tuple[float, float, float]],
    library_name: str,
    ncols: int = 6,
    sort_colors: bool = True,
) -> Figure | None:
    """
    Plot colors for a single library.

    Parameters
    ----------
    colors : dict
        Dictionary mapping color names to color specifications.
    library_name : str
        Name of the library (for title).
    ncols : int, optional
        Number of columns in the color grid, default is 6.
    sort_colors : bool, optional
        If True, sorts colors by base color name and number/brightness.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure containing the color grid.
    """
    if not colors:
        return None

    cell_width = 212
    cell_height = 22
    swatch_width = 48
    margin = 12

    # Sort colors within library
    if sort_colors:
        # Group by base color name (for opencolor, tailwind, etc.)
        base_color_groups = defaultdict(list)
        for color_name in colors:
            base_color = _extract_base_color_name(color_name)
            try:
                rgb = mcolors.to_rgb(colors[color_name])
                hsv = mcolors.rgb_to_hsv(rgb)
                base_color_groups[base_color].append((color_name, hsv))
            except (ValueError, TypeError):
                base_color_groups[base_color].append((color_name, (0, 0, 0)))

        # Sort base color groups alphabetically
        sorted_base_colors = sorted(base_color_groups.items())

        # Sort within each base color group and create groups with lightest
        # color info
        color_groups = []
        for base_color, color_items in sorted_base_colors:

            def sort_key(x):
                color_name, hsv = x
                number = _extract_number_from_color_name(color_name)
                if number is not None:
                    return (0, number)
                else:
                    return (1, -hsv[2])

            color_items.sort(key=sort_key)
            sorted_names = [name for name, _ in color_items]

            # Detect weight system for this group
            min_weight = _detect_color_weight_system(sorted_names)
            weight_range = _detect_weight_range(sorted_names)

            color_groups.append(
                {
                    "base_color": base_color,
                    "colors": [(name, colors[name]) for name in sorted_names],
                    "min_weight": min_weight,
                    "weight_range": weight_range,
                }
            )
    else:
        # If not sorting, treat all colors as one group
        color_groups = [
            {
                "base_color": "all",
                "colors": [(name, colors[name]) for name in colors],
                "min_weight": None,
                "weight_range": None,
            }
        ]

    # Add space for title at the top with margin below title
    title_height = cell_height
    title_margin = 0.5  # Margin below title (in cell_height units)

    # Place colors group-by-group, ensuring each column starts with a group's
    # lightest color and ends with its darkest color. Each group must be
    # placed completely in one column.
    # Add spacing between groups with different weight ranges or different
    # base colors.
    color_grid = []  # List of (col, row, name, color_spec) tuples
    column_heights = [0] * ncols  # Track current height of each column
    prev_weight_range = None  # Track previous group's weight range
    prev_base_color_per_col = [
        None
    ] * ncols  # Track previous base_color for each column

    for _group_idx, group in enumerate(color_groups):
        group_colors = group["colors"]
        current_weight_range = group.get("weight_range")
        current_base_color = group.get("base_color")

        # Find the column with the least height to place this entire group
        # This ensures groups are not split across columns and each column
        # starts with a group's lightest color (weight 0) and ends with its
        # darkest color (weight 9)
        min_height_col = min(range(ncols), key=lambda c: column_heights[c])
        target_col = min_height_col

        # Add spacing row when:
        # 1. Transitioning between different weight ranges (in any column)
        # 2. Transitioning between different base colors (in the target column)
        should_add_spacing = False

        if prev_weight_range is not None and current_weight_range is not None:
            if prev_weight_range != current_weight_range:
                # Different weight ranges - add spacing in all columns
                should_add_spacing = True

        if prev_base_color_per_col[target_col] is not None:
            if prev_base_color_per_col[target_col] != current_base_color:
                # Different base color in the same column - add spacing in
                # target column
                column_heights[target_col] += 1

        if should_add_spacing:
            # Add empty row for spacing in all columns
            for col in range(ncols):
                column_heights[col] += 1

        # Place all colors from this group in the target column
        # The first color (lightest, weight 0) will be at the start of the
        # column
        # The last color (darkest, weight 9) will be at the end of the column
        for _color_idx, (name, color_spec) in enumerate(group_colors):
            row = column_heights[target_col]
            color_grid.append((target_col, row, name, color_spec))
            column_heights[target_col] += 1

        # Update previous values for next iteration
        prev_weight_range = current_weight_range
        prev_base_color_per_col[target_col] = current_base_color

    # Calculate actual number of rows needed based on column heights
    nrows = max(column_heights) if column_heights else 0

    width = cell_width * ncols + 2 * margin
    # Add title margin to total height
    total_title_height = title_height + title_margin * cell_height
    # Add extra space at bottom to ensure last row is fully visible
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
    # Adjust y-axis limits to account for title margin
    # Add extra space at bottom to ensure last row is fully visible
    bottom_extra_margin = 0.5 * cell_height
    ax.set_ylim(-total_title_height, cell_height * nrows + bottom_extra_margin)
    ax.invert_yaxis()  # Ensure smaller y-values render toward the top edge
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_axis_off()

    # Add library title at the top (no background, like plot_colormaps)
    library_labels = {
        "opencolor": "OpenColor Colors",
        "tw": "Tailwind Colors",
        "md": "Material Design Colors",
        "ant": "Ant Design Colors",
        "chakra": "Chakra UI Colors",
        "primer": "Primer Colors",
        "other": "Other Colors",
    }
    title_text = library_labels.get(library_name, library_name)
    title_y = -title_height / 2
    ax.text(
        cell_width * ncols / 2,
        title_y,
        title_text,
        fontsize=14,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
    )

    # Draw the grid using the group-aware placement
    # Colors start after title margin
    title_margin_offset = title_margin * cell_height
    for col, row, name, color_spec in color_grid:
        y = title_margin_offset + (row + 0.5) * cell_height
        swatch_start_x = cell_width * col
        text_pos_x = cell_width * col + swatch_width + 7

        ax.text(
            text_pos_x,
            y,
            name,
            fontsize=14,
            horizontalalignment="left",
            verticalalignment="center",
        )

        ax.add_patch(
            Rectangle(
                xy=(swatch_start_x, y - 9),
                width=swatch_width,
                height=18,
                facecolor=color_spec,
                edgecolor="0.7",
            )
        )

    return fig


def plot_colors(
    colors: dict[str, str | tuple[float, float, float]] | None = None,
    *,
    ncols: int = 4,
    sort_colors: bool = True,
) -> list[Figure]:
    """
    Plot a grid of named colors with their names.

    Creates separate plots for each color library (opencolor, tw/tailwind,
    other).

    Parameters
    ----------
    colors : dict, optional
        Dictionary mapping color names to color specifications.
        If None, uses all named colors from matplotlib except those
        starting with 'dartwork_mpl.'.
    ncols : int, optional
        Number of columns in the color grid, default is 6.
    sort_colors : bool, optional
        If True, sorts colors by base color name (e.g., 'neutral', 'red',
        'blue'), and finally by number (small -> large) or HSV value
        (bright -> dark). Duplicate colors (same RGB values) are
        automatically removed. If False, uses the order from the input
        dictionary.

    Returns
    -------
    list of matplotlib.figure.Figure
        List of figures, one for each color library.

    Examples
    --------
    >>> figs = plot_colors()
    >>> plt.show()
    >>> # Custom colors
    >>> custom_colors = {'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF'}
    >>> figs = plot_colors(custom_colors, ncols=3)
    >>> plt.show()
    """
    if colors is None:
        colors = {
            k: v
            for k, v in mcolors.get_named_colors_mapping().items()
            if not k.startswith("dartwork_mpl.") and not k.startswith("xkcd:")
        }

    # Separate colors by library first, then remove duplicates within each
    # library
    # This preserves colors from different libraries even if they have the
    # same RGB values
    library_colors = _separate_colors_by_library(colors)

    # Remove duplicates within each library separately
    # Note: For tailwind colors and similar systems, we don't remove
    # duplicates because different color names (e.g., zinc:50 and neutral:50)
    # may have the same RGB values but serve different purposes
    skip_duplicate_removal = {"tw", "md", "ant", "chakra", "primer"}
    for library_name in library_colors:
        if library_name not in skip_duplicate_removal:
            library_colors[library_name] = _remove_duplicate_colors(
                library_colors[library_name]
            )

    # Library order: opencolor -> tw -> md -> ant -> chakra -> primer -> other
    # (xkcd last)
    library_order = [
        "opencolor",
        "tw",
        "md",
        "ant",
        "chakra",
        "primer",
        "other",
    ]

    # Create a separate plot for each library
    figures = []
    for library_name in library_order:
        if library_name in library_colors:
            fig = _plot_single_library(
                library_colors[library_name],
                library_name,
                ncols=ncols,
                sort_colors=sort_colors,
            )
            if fig is not None:
                figures.append(fig)

    return figures


def plot_fonts(
    font_dir: str | None = None, ncols: int = 3, font_size: int = 11
) -> Figure:
    """
    Plot available fonts in the specified directory.

    Parameters
    ----------
    font_dir : str, optional
        Directory path containing font files. If None, defaults to the
        'asset/font' directory within the package.
    ncols : int, optional
        Number of columns to display font families, by default 3
    font_size : int, optional
        Font size for sample text, by default 11

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object
    """
    if font_dir is None:
        font_dir = os.path.join(os.path.dirname(__file__), "asset", "font")

    # 폰트 파일 리스트 가져오기
    font_files = [f for f in os.listdir(font_dir) if f.endswith(".ttf")]

    # 폰트 패밀리별로 그룹화
    font_families = defaultdict(list)
    for font in font_files:
        family = font.split("-")[0]
        font_families[family].append(font)

    # 각 패밀리 내에서 폰트 정렬 함수
    def sort_fonts(fonts):
        """
        Sort font files by weight and style within a font family.

        Parameters
        ----------
        fonts : list
            List of font file names to sort.

        Returns
        -------
        list
            Sorted list of font files, ordered by weight (Thin to Black)
            and then by style (regular before italic).
        """
        weight_order = {
            "Thin": 1,
            "ExtraLight": 2,
            "Light": 3,
            "Regular": 4,
            "Medium": 5,
            "SemiBold": 6,
            "Bold": 7,
            "ExtraBold": 8,
            "Black": 9,
        }

        def get_weight_score(font):
            base_weight = 4  # Regular 기본값
            italic_score = 0.5 if "Italic" in font else 0

            for weight, score in weight_order.items():
                if weight in font:
                    base_weight = score
                    break

            return (base_weight, italic_score)

        return sorted(fonts, key=get_weight_score)

    # 패밀리별로 정렬
    sorted_families = sorted(font_families.items())

    # 전체 폰트 개수와 열 수 설정
    total_families = len(sorted_families)
    families_per_column = math.ceil(total_families / ncols)

    # 패밀리 간 간격 설정
    family_spacing = 3  # 패밀리 간 간격
    max_fonts_in_family = max(len(fonts) for _, fonts in sorted_families)

    # 그래프 크기 설정 (패밀리 간 간격 포함)
    total_height = families_per_column * (max_fonts_in_family + family_spacing)
    fig, ax = plt.subplots(figsize=(14, total_height * 0.3))

    # 축 설정
    ax.set_xlim(0, ncols * 7)
    ax.set_ylim(0, total_height)
    ax.axis("off")

    # 각 열별로 폰트 패밀리 출력
    for family_idx, (family, fonts) in enumerate(sorted_families):
        # 열과 행 위치 계산
        column = family_idx // families_per_column
        family_row = family_idx % families_per_column

        # x 위치는 열 번호에 따라 조정
        x_pos = column * 7

        # y 위치 계산 (패밀리 간 간격 포함)
        base_y_pos = family_row * (max_fonts_in_family + family_spacing)

        # 패밀리 제목 출력 (밑줄 추가)
        title_y = base_y_pos + max_fonts_in_family + 0.5
        ax.text(
            x_pos, title_y, f"Font Family: {family}", size=12, weight="bold"
        )
        ax.plot(
            [x_pos, x_pos + 6],
            [title_y - 0.3, title_y - 0.3],
            color="lightgray",
            linestyle="-",
            linewidth=0.5,
        )

        # 정렬된 폰트 출력
        sorted_fonts = sort_fonts(fonts)
        for font_idx, font_file in enumerate(sorted_fonts):
            font_path = os.path.join(font_dir, font_file)
            font_name = os.path.splitext(font_file)[0]

            font_prop = fm.FontProperties(fname=font_path)

            y_pos = base_y_pos + (max_fonts_in_family - font_idx - 1)

            ax.text(
                x_pos,
                y_pos,
                f'This font is "{font_name}"',
                fontproperties=font_prop,
                size=font_size,
            )

    return fig
