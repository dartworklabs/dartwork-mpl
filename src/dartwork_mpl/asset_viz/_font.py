"""Font visualization functions.

Functions for displaying available fonts registered with matplotlib,
with weight spectrum, pangram samples, and grouped italic variants.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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

_PANGRAM = "The quick brown fox jumps over the lazy dog. 0123456789"


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
    import re

    weight_part = re.sub(r"^\d+", "", weight_part)

    if not weight_part:
        weight_part = "Regular"

    return weight_part, is_italic


def _weight_sort_key(weight_name: str) -> int:
    """Return numeric sort key for a weight name."""
    return _WEIGHT_ORDER.get(weight_name, 400)


def plot_fonts(
    font_dir: str | None = None,
    ncols: int = 2,
    font_size: int = 11,
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
        font_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "asset",
            "font",
        )

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
    family_data: list[
        dict[str, str | int | list[dict]]
    ] = []

    for family_name, files in sorted(font_families.items()):
        weight_groups: dict[
            str, dict[str, str | None]
        ] = defaultdict(lambda: {"roman": None, "italic": None})

        for f in files:
            weight_name, is_italic = _parse_font_weight(f)
            slot = "italic" if is_italic else "roman"
            weight_groups[weight_name][slot] = f

        # Sort by weight
        sorted_weights = sorted(
            weight_groups.items(),
            key=lambda x: _weight_sort_key(x[0]),
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
        col_heights[col] += header_line_height + n_lines * weight_line_height + family_gap

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
        meta_text = (
            f"  {n_weights} weights · {n_files} files"
        )

        ax.text(
            x_pos,
            cursor,
            header_text,
            size=13,
            weight="bold",
            color="#1a1a2e",
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
                f"{weight_name} ({weight_num})"
                if weight_num
                else weight_name
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
                except Exception:
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
