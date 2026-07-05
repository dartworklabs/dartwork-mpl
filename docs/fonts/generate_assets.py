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


def _save_svg(fig: plt.Figure, path: Path, **savefig_kwargs) -> Path:
    """Write *fig* as a byte-stable SVG (fixed hashsalt, no wall-clock Date)."""
    with matplotlib.rc_context({"svg.hashsalt": path.stem}):
        fig.savefig(
            path, format="svg", metadata={"Date": None}, **savefig_kwargs
        )
    return path


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
    "NotoSansMath": {
        "description": "Mathematical symbols and equations font",
        "use_case": "Scientific notation, mathematical expressions",
        "variants": 1,
    },
    "Paperlogy": {
        "description": "Clean, professional font designed for documents",
        "use_case": "Reports, academic papers, professional documents",
        "variants": 4,
    },
    "Pretendard": {
        "description": "Modern geometric-humanist sans with full Korean (한글) coverage",
        "use_case": "Bilingual Korean–English reports, UI, body text",
        "variants": 9,
    },
    "Roboto": {
        "description": "Google's flagship sans-serif, default font in dartwork-mpl",
        "use_case": "Default body text, general purpose (dartwork-mpl default)",
        "variants": 4,
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
    """Collect and group font files by family.

    Both ``.ttf`` and ``.otf`` are collected — Pretendard and the
    Noto Sans CJK subset ship as OpenType (``.otf``), so a ``.ttf``-only
    filter would silently drop them from the generated all-families
    preview even though they count toward the advertised family count.
    Kept in sync with ``generate_html_specimens._collect_fonts``.
    """
    font_dir = _get_font_dir()
    font_files = [
        f for f in os.listdir(font_dir) if f.endswith((".ttf", ".otf"))
    ]

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
    """Generate a comprehensive preview of all font families.

    The output is embedded in ``fonts/utilities.md`` at body width
    (~760 px on a 1440 viewport). Earlier versions used a 16 in × 20 in
    canvas, which produced a 1210 × 1706 SVG that the browser had to
    shrink to 63 %; every glyph then rendered at 63 % of the matplotlib
    point size and looked blurry. We now target a 10 in × ~12 in canvas
    so the natural width matches the body and no browser scaling kicks
    in.
    """
    font_families = _collect_fonts()
    font_dir = _get_font_dir()

    # Calculate layout
    ncols = 3
    total_families = len(font_families)
    families_per_column = math.ceil(total_families / ncols)
    max_fonts_in_family = max(len(fonts) for fonts in font_families.values())

    family_spacing = 2
    total_height = families_per_column * (max_fonts_in_family + family_spacing)

    fig, ax = plt.subplots(figsize=(10, total_height * 0.22))
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#ffffff")

    ax.set_xlim(0, ncols * 4.5)
    ax.set_ylim(0, total_height)
    ax.axis("off")

    fig.suptitle(
        "All Available Font Families", fontsize=14, fontweight="bold", y=0.985
    )

    sorted_families = list(font_families.items())

    for family_idx, (family, fonts) in enumerate(sorted_families):
        column = family_idx // families_per_column
        family_row = family_idx % families_per_column

        x_pos = column * 4.5
        base_y_pos = family_row * (max_fonts_in_family + family_spacing)

        title_y = base_y_pos + max_fonts_in_family + 0.4
        ax.text(
            x_pos, title_y, f"{family}", size=9.5, weight="bold", color="#333"
        )
        ax.plot(
            [x_pos, x_pos + 3.6],
            [title_y - 0.25, title_y - 0.25],
            color="#e4e2dd",
            linestyle="-",
            linewidth=0.8,
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
                size=8.5,
                color="#444",
            )

    path = images_dir / "fonts_all_families.svg"
    _save_svg(fig, path, bbox_inches="tight")
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
            ("Arithmetic", "1 + 2 − 3 × 4 ÷ 5 = ± 6"),
            ("Inequalities", "x ≤ y ∧ y ≥ z ⇒ x ≈ z"),
            ("Set Theory", "A ∪ B = B ∩ A ⊂ ℝ"),
            ("Geometry", "α^2 + β^2 = γ^2"),
            ("Euler", "e^(iπ) + 1 = 0"),
            ("Logic", "∀x ∃y : P(x) ∨ ¬Q(y)"),
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
        _save_svg(fig, path, bbox_inches="tight")
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
    _save_svg(fig, path, bbox_inches="tight")
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
