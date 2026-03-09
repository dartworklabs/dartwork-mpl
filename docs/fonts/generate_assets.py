"""
Generate high-resolution gallery assets for the fonts documentation.

The entrypoint `build_font_assets()` can be invoked from Sphinx (see docs/conf.py)
so that the gallery stays in sync with every build. You can also run this file
directly:

    python docs/fonts/generate_assets.py
"""

from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# Make sure the source tree is importable when running the script directly.
ROOT = Path(__file__).resolve().parents[2]  # docs/fonts -> docs -> project root
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# Font family metadata
FONT_FAMILIES = {
    "Inter": {
        "description": "Modern, highly legible sans-serif designed for computer screens",
        "use_case": "UI text, presentations, general purpose",
        "variants": 20,
    },
    "InterDisplay": {
        "description": "Display variant of Inter optimized for larger sizes",
        "use_case": "Headings, titles, large text",
        "variants": 20,
    },
    "NotoSans": {
        "description": "Google's versatile sans-serif with excellent language coverage",
        "use_case": "Multi-language documents, body text",
        "variants": 15,
    },
    "NotoSans_Condensed": {
        "description": "Condensed variant of Noto Sans for space-constrained layouts",
        "use_case": "Tables, dense layouts, annotations",
        "variants": 20,
    },
    "NotoSans_SemiCondensed": {
        "description": "Semi-condensed variant balancing readability and compactness",
        "use_case": "Labels, legends, compact text",
        "variants": 20,
    },
    "NotoSans_ExtraCondensed": {
        "description": "Extra condensed for maximum space efficiency",
        "use_case": "Very tight layouts, axis labels",
        "variants": 20,
    },
    "NotoSansMath": {
        "description": "Mathematical symbols and equations font",
        "use_case": "Scientific notation, mathematical expressions",
        "variants": 1,
    },
    "Paperlogy": {
        "description": "Clean, professional font designed for documents",
        "use_case": "Reports, academic papers, professional documents",
        "variants": 9,
    },
    "Roboto": {
        "description": "Google's flagship sans-serif, default font in dartwork-mpl",
        "use_case": "Default body text, general purpose (dartwork-mpl default)",
        "variants": 15,
    },
}

WEIGHT_ORDER = {
    "Thin": 1,
    "ExtraLight": 2,
    "Light": 3,
    "Regular": 4,
    "Medium": 5,
    "SemiBold": 6,
    "ExtraBold": 8,
    "Bold": 7,
    "Black": 9,
}


def _prepare_images_dir(base_dir: Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(__file__).parent
    images_dir = base / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def _get_font_dir() -> Path:
    return ROOT / "src" / "dartwork_mpl" / "asset" / "font"


def _collect_fonts() -> dict[str, list[str]]:
    """Collect and group font files by family."""
    font_dir = _get_font_dir()
    font_files = [f for f in os.listdir(font_dir) if f.endswith(".ttf")]

    font_families = defaultdict(list)
    for font in font_files:
        family = font.split("-")[0]
        font_families[family].append(font)

    return dict(sorted(font_families.items()))


def _sort_fonts(fonts: list[str]) -> list[str]:
    """Sort fonts by weight and style."""

    def get_weight_score(font):
        base_weight = 4  # Regular default
        italic_score = 0.5 if "Italic" in font else 0

        for weight, score in WEIGHT_ORDER.items():
            if weight in font:
                base_weight = score
                break

        return (base_weight, italic_score)

    return sorted(fonts, key=get_weight_score)


def _save_all_fonts_preview(images_dir: Path) -> Path:
    """Generate a comprehensive preview of all font families."""
    font_families = _collect_fonts()
    font_dir = _get_font_dir()

    # Calculate layout
    ncols = 3
    total_families = len(font_families)
    families_per_column = math.ceil(total_families / ncols)
    max_fonts_in_family = max(len(fonts) for fonts in font_families.values())

    family_spacing = 3
    total_height = families_per_column * (max_fonts_in_family + family_spacing)

    fig, ax = plt.subplots(figsize=(16, total_height * 0.32))
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#ffffff")

    ax.set_xlim(0, ncols * 7)
    ax.set_ylim(0, total_height)
    ax.axis("off")

    fig.suptitle(
        "All Available Font Families", fontsize=20, fontweight="bold", y=0.98
    )

    sorted_families = list(font_families.items())

    for family_idx, (family, fonts) in enumerate(sorted_families):
        column = family_idx // families_per_column
        family_row = family_idx % families_per_column

        x_pos = column * 7
        base_y_pos = family_row * (max_fonts_in_family + family_spacing)

        title_y = base_y_pos + max_fonts_in_family + 0.5
        ax.text(
            x_pos, title_y, f"{family}", size=13, weight="bold", color="#333"
        )
        ax.plot(
            [x_pos, x_pos + 5.5],
            [title_y - 0.3, title_y - 0.3],
            color="#e4e2dd",
            linestyle="-",
            linewidth=1,
        )

        sorted_fonts = _sort_fonts(fonts)
        for font_idx, font_file in enumerate(sorted_fonts):
            font_path = font_dir / font_file
            font_name = os.path.splitext(font_file)[0]

            font_prop = fm.FontProperties(fname=str(font_path))
            y_pos = base_y_pos + (max_fonts_in_family - font_idx - 1)

            # Extract variant name
            variant = font_name.split("-")[1] if "-" in font_name else "Regular"
            ax.text(
                x_pos,
                y_pos,
                f"{variant}",
                fontproperties=font_prop,
                size=11,
                color="#444",
            )

    path = images_dir / "fonts_all_families.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_family_preview(
    family: str, fonts: list[str], images_dir: Path
) -> Path:
    """Generate a detailed preview for a single font family."""
    font_dir = _get_font_dir()
    sorted_fonts = _sort_fonts(fonts)

    # Calculate figure size based on number of fonts
    n_fonts = len(sorted_fonts)
    fig_height = max(4, n_fonts * 0.6 + 2.5)

    fig, ax = plt.subplots(figsize=(12, fig_height))
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#ffffff")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, n_fonts + 1)
    ax.axis("off")

    # Title (left-aligned)
    meta = FONT_FAMILIES.get(family, {})
    fig.suptitle(
        f"{family}", fontsize=18, fontweight="bold", y=0.97, x=0.08, ha="left"
    )

    if meta.get("description"):
        fig.text(
            0.08,
            0.90,
            meta["description"],
            fontsize=11,
            color="#555",
            ha="left",
        )

    # Find Regular/Medium font for weight labels
    regular_font_prop = None
    for f in sorted_fonts:
        fname_lower = f.lower()
        if "-regular" in fname_lower or fname_lower.endswith("regular.ttf"):
            regular_font_prop = fm.FontProperties(fname=str(font_dir / f))
            break
    if regular_font_prop is None:
        for f in sorted_fonts:
            fname_lower = f.lower()
            if "-medium" in fname_lower or "4regular" in fname_lower:
                regular_font_prop = fm.FontProperties(fname=str(font_dir / f))
                break

    # Sample text — use math symbols for NotoSansMath, Korean for Paperlogy
    if family == "NotoSansMath":
        sample_text = "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃"
    elif family == "Paperlogy":
        sample_text = (
            "김도균 & 이주임 님이 만든 아름다운 페이퍼로지 폰트. 0123456789"
        )
    else:
        sample_text = "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)"
    # NotoSansMath: add extra LaTeX math expression lines (only 1 weight)
    if family == "NotoSansMath":
        math_expressions = [
            ("Symbols", "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃"),
            ("Quadratic", r"$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$"),
            ("Gaussian", r"$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$"),
            (
                "Green's Function",
                r"$G(\mathbf{r}, t) = \frac{1}{(4\pi \alpha t)^{3/2}} \exp\left( -\frac{x^2 + y^2 + z^2}{4 \alpha t} \right)$",
            ),
            ("Entropy", r"$H(X) = -\sum_{i} p(x_i) \log p(x_i)$"),
            (
                "Heat Equation",
                r"$\frac{\partial u}{\partial t} = \alpha \left( \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} + \frac{\partial^2 u}{\partial z^2} \right)$",
            ),
            (
                "Navier-Stokes",
                r"$\rho \left( \frac{\partial \mathbf{v}}{\partial t} + \mathbf{v} \cdot \nabla \mathbf{v} \right) = -\nabla p + \mu \nabla^2 \mathbf{v}$",
            ),
            (
                "Maxwell-Boltzmann",
                r"$f(v) = 4\pi \left( \frac{m}{2\pi k_B T} \right)^{3/2} v^2 \, e^{-mv^2 / 2k_B T}$",
            ),
            (
                "Planck",
                r"$B(\nu, T) = \frac{2 h \nu^3}{c^2} \cdot \frac{1}{e^{h\nu / k_B T} - 1}$",
            ),
        ]

        n_lines = len(math_expressions)
        fig_height = max(4, n_lines * 0.7 + 2.5)

        # Recreate figure with proper size for math lines
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(12, fig_height))
        fig.patch.set_facecolor("#fbfaf7")
        ax.set_facecolor("#ffffff")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, n_lines + 1)
        ax.axis("off")

        fig.suptitle(
            f"{family}",
            fontsize=18,
            fontweight="bold",
            y=0.97,
            x=0.08,
            ha="left",
        )
        if meta.get("description"):
            fig.text(
                0.08,
                0.90,
                meta["description"],
                fontsize=11,
                color="#555",
                ha="left",
            )

        font_path = font_dir / sorted_fonts[0]
        font_prop = fm.FontProperties(fname=str(font_path))

        for idx, (label, expr) in enumerate(math_expressions):
            y_pos = n_lines - idx - 0.3

            ax.text(
                0.1,
                y_pos,
                label,
                fontproperties=font_prop,
                size=15,
                color="#666",
                va="center",
            )

            if expr.startswith("$"):
                ax.text(2.2, y_pos, expr, size=15, color="#333", va="center")
            else:
                ax.text(
                    2.2,
                    y_pos,
                    expr,
                    fontproperties=font_prop,
                    size=15,
                    color="#333",
                    va="center",
                )

        path = images_dir / f"font_{family.lower()}.svg"
        fig.savefig(path, format="svg", bbox_inches="tight")
        plt.close(fig)
        return path

    for idx, font_file in enumerate(sorted_fonts):
        font_path = font_dir / font_file
        font_name = os.path.splitext(font_file)[0]
        variant = font_name.split("-")[1] if "-" in font_name else "Regular"
        variant = variant.lstrip("0123456789")  # strip numeric prefix

        font_prop = fm.FontProperties(fname=str(font_path))
        y_pos = n_fonts - idx - 0.5

        # Variant label — use family's own Regular font
        label_kwargs = {"size": 14, "color": "#666", "va": "center"}
        if regular_font_prop is not None:
            label_kwargs["fontproperties"] = regular_font_prop
        else:
            label_kwargs["weight"] = "bold"
        ax.text(0.1, y_pos, f"{variant}", **label_kwargs)

        # Sample text
        ax.text(
            2.2,
            y_pos,
            sample_text,
            fontproperties=font_prop,
            size=14,
            color="#333",
            va="center",
        )

    path = images_dir / f"font_{family.lower()}.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def build_font_assets(base_dir: Path | None = None) -> dict[str, list[Path]]:
    """Generate all font gallery assets and return their paths."""
    images_dir = _prepare_images_dir(base_dir)
    print(f"[fonts] generating assets to {images_dir}")

    # Generate all fonts preview
    all_fonts_path = _save_all_fonts_preview(images_dir)

    # Generate individual family previews
    font_families = _collect_fonts()
    family_paths = []
    for family, fonts in font_families.items():
        path = _save_family_preview(family, fonts, images_dir)
        family_paths.append(path)

    # Generate before/after comparison & chart context SVGs
    _build_comparison_assets()

    total = len(family_paths) + 1
    print(f"[fonts] wrote {total} font preview images")

    return {"all_fonts": [all_fonts_path], "families": family_paths}


def _build_comparison_assets() -> None:
    """Generate comparison SVGs and copy to _static/ for Sphinx serving."""
    import shutil

    try:
        from fonts.generate_comparison_assets import (
            generate_before_after,
            generate_chart_context,
        )
    except ModuleNotFoundError:
        try:
            from fonts.generate_comparison_assets import (
                generate_before_after,
                generate_chart_context,
            )
        except ModuleNotFoundError:
            from generate_comparison_assets import (
                generate_before_after,
                generate_chart_context,
            )

    generate_before_after()
    generate_chart_context()

    # Copy SVGs to _static/ (raw HTML img tags need _static/ path)
    gen_dir = Path(__file__).parent / "_generated"
    static_dir = Path(__file__).parent.parent / "_static"
    for svg in ("before_default.svg", "after_dartwork.svg"):
        src = gen_dir / svg
        if src.exists():
            shutil.copy2(src, static_dir / svg)


if __name__ == "__main__":
    build_font_assets()
