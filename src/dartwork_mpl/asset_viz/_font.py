"""Font visualization functions.

Functions for displaying available fonts registered with matplotlib.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


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
        font_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "asset",
            "font",
        )

    font_files = [f for f in os.listdir(font_dir) if f.endswith(".ttf")]

    font_families: dict[str, list[str]] = defaultdict(list)
    for font in font_files:
        family = font.split("-")[0]
        font_families[family].append(font)

    def sort_fonts(fonts: list[str]) -> list[str]:
        """Sort font files by weight and style within a family."""
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

        def get_weight_score(
            font: str,
        ) -> tuple[int, float]:
            base_weight = 4
            italic_score = 0.5 if "Italic" in font else 0

            for weight, score in weight_order.items():
                if weight in font:
                    base_weight = score
                    break

            return (base_weight, italic_score)

        return sorted(fonts, key=get_weight_score)

    sorted_families = sorted(font_families.items())

    total_families = len(sorted_families)
    families_per_column = math.ceil(total_families / ncols)

    family_spacing = 3
    max_fonts_in_family = max(len(fonts) for _, fonts in sorted_families)

    total_height = families_per_column * (
        max_fonts_in_family + family_spacing
    )
    fig, ax = plt.subplots(figsize=(14, total_height * 0.3))

    ax.set_xlim(0, ncols * 7)
    ax.set_ylim(0, total_height)
    ax.axis("off")

    for family_idx, (family, fonts) in enumerate(sorted_families):
        column = family_idx // families_per_column
        family_row = family_idx % families_per_column

        x_pos = column * 7
        base_y_pos = family_row * (max_fonts_in_family + family_spacing)

        title_y = base_y_pos + max_fonts_in_family + 0.5
        ax.text(
            x_pos,
            title_y,
            f"Font Family: {family}",
            size=12,
            weight="bold",
        )
        ax.plot(
            [x_pos, x_pos + 6],
            [title_y - 0.3, title_y - 0.3],
            color="lightgray",
            linestyle="-",
            linewidth=0.5,
        )

        sorted_fonts_list = sort_fonts(fonts)
        for font_idx, font_file in enumerate(sorted_fonts_list):
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
