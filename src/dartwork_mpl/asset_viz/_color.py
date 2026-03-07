"""Color library visualization functions.

Functions for plotting named color libraries (OpenColor, Tailwind,
Material Design, Ant Design, Chakra UI, Primer).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_color_library_names() -> set[str]:
    """Load color names from oc.txt file."""
    asset_dir = Path(__file__).parent.parent / "asset" / "color"
    opencolor_names: set[str] = set()

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
    """Classify a color name into its library category."""
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
    return "other"


def _detect_color_weight_system(
    color_names: list[str],
) -> int | None:
    """Detect the weight system used in a group of color names."""
    weights = []
    for color_name in color_names:
        weight = _extract_number_from_color_name(color_name)
        if weight is not None:
            weights.append(weight)

    if weights:
        return min(weights)
    return None


def _detect_weight_range(
    color_names: list[str],
) -> tuple[int, int] | None:
    """Detect the weight range used in a group of color names."""
    weights = []
    for color_name in color_names:
        weight = _extract_number_from_color_name(color_name)
        if weight is not None:
            weights.append(weight)

    if weights:
        return (min(weights), max(weights))
    return None


def _extract_base_color_name(color_name: str) -> str:
    """Extract base color name from color name."""
    name = color_name
    for prefix in ["oc.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    match = re.search(r"^([a-z]+)\d+$", name)
    if match:
        return match.group(1)

    return name


def _extract_number_from_color_name(
    color_name: str,
) -> int | None:
    """Extract number from color name if present."""
    name = color_name
    for prefix in ["dm.", "tw.", "md.", "ad.", "cu.", "pr."]:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    match = re.search(r"(\d+)$", name)
    if match:
        return int(match.group(1))

    return None


def _remove_duplicate_colors(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, str | tuple[float, float, float]]:
    """Remove duplicate colors based on RGB values."""
    seen_rgb: dict[tuple[float, ...], str] = {}
    result: dict[str, str | tuple[float, float, float]] = {}

    for color_name, color_spec in colors.items():
        try:
            rgb = mcolors.to_rgb(color_spec)
            rgb_key = tuple(round(c, 6) for c in rgb)

            if rgb_key not in seen_rgb:
                seen_rgb[rgb_key] = color_name
                result[color_name] = color_spec
        except (ValueError, TypeError):
            result[color_name] = color_spec

    return result


def _separate_colors_by_library(
    colors: dict[str, str | tuple[float, float, float]],
) -> dict[str, dict[str, str | tuple[float, float, float]]]:
    """Separate colors by library."""
    library_groups: dict[
        str, dict[str, str | tuple[float, float, float]]
    ] = {
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

    return {
        lib: colors_dict
        for lib, colors_dict in library_groups.items()
        if colors_dict
    }


def _sort_colors_by_library(
    colors: dict[str, str | tuple[float, float, float]],
) -> list[tuple[str, str | tuple[float, float, float]]]:
    """Sort colors by library, then by base color name and number."""
    library_groups: dict[str, list[str]] = {
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

    sorted_names: list[tuple[str, str | tuple[float, float, float]]] = []

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

        sorted_names.append(("__TITLE__", library_labels[library]))

        base_color_groups: dict[
            str, list[tuple[str, tuple[float, float, float]]]
        ] = defaultdict(list)
        for color_name in color_list:
            base_color = _extract_base_color_name(color_name)
            try:
                rgb = mcolors.to_rgb(colors[color_name])
                hsv = mcolors.rgb_to_hsv(rgb)
                base_color_groups[base_color].append((color_name, hsv))
            except (ValueError, TypeError):
                base_color_groups[base_color].append(
                    (color_name, (0, 0, 0))
                )

        sorted_base_colors = sorted(base_color_groups.items())

        for _, color_items in sorted_base_colors:

            def sort_key(
                x: tuple[str, tuple[float, float, float]],
            ) -> tuple[int, float]:
                color_name, hsv = x
                number = _extract_number_from_color_name(color_name)
                if number is not None:
                    return (0, number)
                else:
                    return (1, -hsv[2])

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
        str
        | list[tuple[str, str | tuple[float, float, float]]]
        | None
        | float,
    ]
]:
    """Group colors by HSV hue ranges for better visual organization."""
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

    color_items: list[
        tuple[str, str | tuple[float, float, float], tuple]
    ] = []
    for color_name, color_spec in colors.items():
        try:
            rgb = mcolors.to_rgb(color_spec)
            hsv = mcolors.rgb_to_hsv(rgb)
            color_items.append((color_name, color_spec, hsv))
        except (ValueError, TypeError):
            color_items.append((color_name, color_spec, (0, 0, 0)))

    grayscale = []
    colored = []
    for name, spec, hsv in color_items:
        if hsv[1] < 0.1:
            grayscale.append((name, spec, hsv))
        else:
            colored.append((name, spec, hsv))

    hue_groups: dict[str, list] = defaultdict(list)
    for name, spec, hsv in colored:
        hue = hsv[0] * 360
        assigned = False
        for group_name, ranges in hue_ranges:
            for min_hue, max_hue in ranges:
                if group_name == "red":
                    if (0 <= hue < 30) or (330 <= hue < 360):
                        hue_groups[group_name].append(
                            (name, spec, hsv)
                        )
                        assigned = True
                        break
                elif min_hue <= hue < max_hue:
                    hue_groups[group_name].append(
                        (name, spec, hsv)
                    )
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            hue_groups["other"].append((name, spec, hsv))

    if grayscale:
        hue_groups["grayscale"] = grayscale

    color_groups = []

    for group_name, items in hue_groups.items():
        if not items:
            continue

        if group_name == "grayscale":
            avg_hue = -1
        elif group_name == "other":
            avg_hue = 1000
        else:
            hues = [hsv[0] * 360 for _, _, hsv in items]
            if group_name == "red":
                normalized_hues = [
                    h if h < 180 else h - 360 for h in hues
                ]
                avg_hue = sum(normalized_hues) / len(
                    normalized_hues
                )
            else:
                avg_hue = sum(hues) / len(hues)

        items.sort(key=lambda x: -x[2][2])

        color_groups.append(
            {
                "base_color": group_name,
                "colors": [(name, spec) for name, spec, _ in items],
                "min_weight": None,
                "avg_hue": avg_hue,
            }
        )

    color_groups.sort(key=lambda g: g["avg_hue"])

    return color_groups


def _plot_single_library(
    colors: dict[str, str | tuple[float, float, float]],
    library_name: str,
    ncols: int = 6,
    sort_colors: bool = True,
) -> Figure | None:
    """Plot colors for a single library."""
    if not colors:
        return None

    cell_width = 212
    cell_height = 22
    swatch_width = 48
    margin = 12

    if sort_colors:
        base_color_groups: dict[str, list] = defaultdict(list)
        for color_name in colors:
            base_color = _extract_base_color_name(color_name)
            try:
                rgb = mcolors.to_rgb(colors[color_name])
                hsv = mcolors.rgb_to_hsv(rgb)
                base_color_groups[base_color].append(
                    (color_name, hsv)
                )
            except (ValueError, TypeError):
                base_color_groups[base_color].append(
                    (color_name, (0, 0, 0))
                )

        sorted_base_colors = sorted(base_color_groups.items())

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

            min_weight = _detect_color_weight_system(sorted_names)
            weight_range = _detect_weight_range(sorted_names)

            color_groups.append(
                {
                    "base_color": base_color,
                    "colors": [
                        (name, colors[name]) for name in sorted_names
                    ],
                    "min_weight": min_weight,
                    "weight_range": weight_range,
                }
            )
    else:
        color_groups = [
            {
                "base_color": "all",
                "colors": [
                    (name, colors[name]) for name in colors
                ],
                "min_weight": None,
                "weight_range": None,
            }
        ]

    title_height = cell_height
    title_margin = 0.5

    color_grid = []
    column_heights = [0] * ncols
    prev_weight_range = None
    prev_base_color_per_col = [None] * ncols

    for _group_idx, group in enumerate(color_groups):
        group_colors = group["colors"]
        current_weight_range = group.get("weight_range")
        current_base_color = group.get("base_color")

        min_height_col = min(
            range(ncols), key=lambda c: column_heights[c]
        )
        target_col = min_height_col

        should_add_spacing = False

        if (
            prev_weight_range is not None
            and current_weight_range is not None
        ):
            if prev_weight_range != current_weight_range:
                should_add_spacing = True

        if prev_base_color_per_col[target_col] is not None:
            if (
                prev_base_color_per_col[target_col]
                != current_base_color
            ):
                column_heights[target_col] += 1

        if should_add_spacing:
            for col in range(ncols):
                column_heights[col] += 1

        for _color_idx, (name, color_spec) in enumerate(
            group_colors
        ):
            row = column_heights[target_col]
            color_grid.append((target_col, row, name, color_spec))
            column_heights[target_col] += 1

        prev_weight_range = current_weight_range
        prev_base_color_per_col[target_col] = current_base_color

    nrows = max(column_heights) if column_heights else 0

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

    fig, ax = plt.subplots(
        figsize=(width / dpi, height / dpi), dpi=dpi
    )
    fig.subplots_adjust(
        margin / width,
        margin / height,
        (width - margin) / width,
        (height - margin) / height,
    )
    ax.set_xlim(0, cell_width * ncols)
    bottom_extra_margin = 0.5 * cell_height
    ax.set_ylim(
        -total_title_height,
        cell_height * nrows + bottom_extra_margin,
    )
    ax.invert_yaxis()
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_axis_off()

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plot_colors(
    colors: dict[str, str | tuple[float, float, float]]
    | None = None,
    *,
    ncols: int = 4,
    sort_colors: bool = True,
) -> list[Figure]:
    """
    Plot a grid of named colors with their names.

    Creates separate plots for each color library (opencolor,
    tw/tailwind, other).

    Parameters
    ----------
    colors : dict, optional
        Dictionary mapping color names to color specifications.
        If None, uses all named colors from matplotlib except those
        starting with 'dartwork_mpl.'.
    ncols : int, optional
        Number of columns in the color grid, default is 4.
    sort_colors : bool, optional
        If True, sorts colors by base color name, then by number or
        HSV value.

    Returns
    -------
    list of matplotlib.figure.Figure
        List of figures, one for each color library.
    """
    if colors is None:
        colors = {
            k: v
            for k, v in mcolors.get_named_colors_mapping().items()
            if not k.startswith("dartwork_mpl.")
            and not k.startswith("xkcd:")
        }

    library_colors = _separate_colors_by_library(colors)

    skip_duplicate_removal = {
        "tw",
        "md",
        "ant",
        "chakra",
        "primer",
    }
    for library_name in library_colors:
        if library_name not in skip_duplicate_removal:
            library_colors[library_name] = _remove_duplicate_colors(
                library_colors[library_name]
            )

    library_order = [
        "opencolor",
        "tw",
        "md",
        "ant",
        "chakra",
        "primer",
        "other",
    ]

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
