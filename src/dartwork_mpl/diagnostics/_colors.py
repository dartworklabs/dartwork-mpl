"""Color-library diagnostics — render named color libraries as swatch grids.

Part of the :mod:`dartwork_mpl.diagnostics` package; the public entry
points are re-exported from its ``__init__``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from ..colors._loader import COLOR_LIBRARIES

if TYPE_CHECKING:
    pass


# =============================================================================
# Color libraries
# =============================================================================


def _load_color_library_names() -> set[str]:
    """Load color names from oc.txt file."""
    asset_dir = Path(__file__).resolve().parent.parent / "asset" / "color"
    opencolor_names: set[str] = set()

    opencolor_file = asset_dir / "opencolor.txt"
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
    """Classify a color name into its library category (from the SSOT)."""
    for key, prefix, _fn, _label in COLOR_LIBRARIES:
        if color_name.startswith(prefix):
            return key
    return None


def _extract_base_color_name(color_name: str) -> str:
    """Extract base color name from color name."""
    name = color_name
    for _key, prefix, _fn, _label in COLOR_LIBRARIES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    match = re.search(r"^([a-z][a-z_]*)\d+$", name)
    if match:
        return match.group(1)

    return name


def _extract_number_from_color_name(color_name: str) -> int | None:
    """Extract number from color name if present."""
    name = color_name
    # Prefixes derive from the COLOR_LIBRARIES SSOT (like the other
    # consumers in this module) instead of a re-hardcoded list.
    from ..colors._loader import COLOR_LIBRARIES

    for prefix in [lib[1] for lib in COLOR_LIBRARIES]:
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

    library_order = [key for key, _prefix, _fn, _label in COLOR_LIBRARIES]

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
