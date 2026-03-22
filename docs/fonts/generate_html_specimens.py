#!/usr/bin/env python3
"""Generate @font-face CSS and HTML specimens for font families.

Run: python docs/fonts/generate_html_specimens.py
Output: docs/fonts/_generated/ (CSS + HTML snippets)
"""

from __future__ import annotations

import os
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "src" / "dartwork_mpl" / "asset" / "font"
OUT_DIR = Path(__file__).parent / "_generated"
STATIC_FONTS = ROOT / "docs" / "_static" / "fonts"

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

# Key weights to feature in the compact showcase
KEY_WEIGHTS = {"Light", "Regular", "Medium", "Bold", "Black"}

FONT_META = {
    "Inter": {
        "description": "Modern, highly legible sans-serif designed for computer screens",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "InterDisplay": {
        "description": "Display variant of Inter optimized for larger sizes",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "NotoSans": {
        "description": "Google's versatile sans-serif with excellent language coverage",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "NotoSans_Condensed": {
        "description": "Condensed variant of Noto Sans for space-constrained layouts",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "NotoSans_SemiCondensed": {
        "description": "Semi-condensed variant balancing readability and compactness",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "NotoSans_ExtraCondensed": {
        "description": "Extra condensed for maximum space efficiency",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
    "Paperlogy": {
        "description": "Clean, professional font designed for documents · Korean (한글) support",
        "sample": "김도균 & 이주임 님이 만든 아름다운 페이퍼로지 폰트.",
    },
    "Roboto": {
        "description": "Google's flagship sans-serif, default font in dartwork-mpl",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
    },
}


def _collect_fonts() -> dict[str, list[str]]:
    """Collect and group font files by family."""
    font_files = [f for f in os.listdir(FONT_DIR) if f.endswith(".ttf")]
    families: dict[str, list[str]] = defaultdict(list)
    for font in font_files:
        family = font.split("-")[0]
        families[family].append(font)
    return dict(sorted(families.items()))


def _get_weight_score(font: str) -> tuple[int, float]:
    """Score for sorting by weight then italic."""
    italic_score = 0.5 if "Italic" in font else 0
    base = 4  # Regular default
    for weight, score in WEIGHT_ORDER.items():
        if weight in font:
            base = score
            break
    return (base, italic_score)


def _variant_label(filename: str) -> str:
    """Extract clean variant label from filename."""
    name = os.path.splitext(filename)[0]
    variant = name.split("-")[1] if "-" in name else "Regular"
    return variant.lstrip("0123456789")


def _font_face_name(filename: str) -> str:
    """Generate unique CSS font-family name: dm-{filename without ext}."""
    return f"dm-{os.path.splitext(filename)[0]}"


def _find_regular(fonts: list[str]) -> str | None:
    """Find the Regular/Medium variant for weight labels."""
    for f in fonts:
        lo = f.lower()
        if "-regular" in lo or lo.endswith("regular.ttf"):
            return f
    for f in fonts:
        lo = f.lower()
        if "-medium" in lo or "4regular" in lo:
            return f
    return fonts[0] if fonts else None


def _is_key_weight(filename: str) -> bool:
    """Check if a font file represents a key weight (non-italic)."""
    if "Italic" in filename:
        return False
    label = _variant_label(filename)
    return label in KEY_WEIGHTS


# ── Generators ───────────────────────────────────────────────────────────────


def generate_fontface_css() -> str:
    """Generate @font-face CSS for all bundled fonts."""
    families = _collect_fonts()
    lines = ["/* Auto-generated @font-face declarations */", ""]

    for family, fonts in families.items():
        lines.append(f"/* ── {family} ── */")
        for font in sorted(fonts):
            css_name = _font_face_name(font)
            lines.append("@font-face {")
            lines.append(f"  font-family: '{css_name}';")
            lines.append(f"  src: url('fonts/{font}') format('truetype');")
            lines.append("  font-display: swap;")
            lines.append("}")
            lines.append("")

    return "\n".join(lines)


def generate_family_html(family: str, fonts: list[str]) -> str:
    """Generate HTML specimen for one font family (all weights)."""
    meta = FONT_META.get(family, {})
    desc = meta.get("description", "")
    sample = meta.get(
        "sample",
        "The dartwork designs beautiful data artworks since 2021. 0123456789",
    )

    # Exclude italic variants — show only upright weights
    upright_fonts = [f for f in fonts if "Italic" not in f]
    sorted_fonts = sorted(upright_fonts, key=_get_weight_score)
    regular = _find_regular(sorted_fonts)
    regular_css = _font_face_name(regular) if regular else "sans-serif"

    rows = []
    for font in sorted_fonts:
        label = _variant_label(font)
        css_name = _font_face_name(font)
        rows.append(
            f'  <span class="label" style="font-family:\'{regular_css}\'">'
            f"{label}</span>\n"
            f'  <span class="sample" style="font-family:\'{css_name}\'">'
            f"{sample}</span>"
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>{family}</h3>\n"
        f'  <p class="desc">{desc}</p>\n'
        f'  <div class="dm-font-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def generate_family_showcase_html(family: str, fonts: list[str]) -> str:
    """Generate a compact showcase: hero text + key weights only."""
    meta = FONT_META.get(family, {})
    desc = meta.get("description", "")

    sorted_fonts = sorted(fonts, key=_get_weight_score)
    regular = _find_regular(sorted_fonts)
    regular_css = _font_face_name(regular) if regular else "sans-serif"

    # Find key weight fonts
    key_fonts = [f for f in sorted_fonts if _is_key_weight(f)]
    if not key_fonts:
        key_fonts = sorted_fonts[:5]

    # Hero line — large display text in Regular weight
    hero = (
        f'  <div class="dm-showcase-hero" '
        f"style=\"font-family:'{regular_css}'\">"
        f"Aa Bb Cc Dd Ee 0123456789</div>"
    )

    # Key weight rows
    weight_numeric = {
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

    rows = []
    for font in key_fonts:
        label = _variant_label(font)
        css_name = _font_face_name(font)
        num = weight_numeric.get(label, "")
        rows.append(
            f'  <div class="dm-showcase-row">\n'
            f'    <span class="dm-showcase-weight">{label}</span>\n'
            f'    <span class="dm-showcase-num">{num}</span>\n'
            f'    <span class="dm-showcase-sample" '
            f"style=\"font-family:'{css_name}'\">"
            f"The dartwork designs beautiful data artworks since 2021.</span>\n"
            f"  </div>"
        )

    weight_rows = "\n".join(rows)

    # Variant count summary
    total = len(fonts)
    italic_count = sum(1 for f in fonts if "Italic" in f)
    upright_count = total - italic_count
    variant_info = f"{upright_count} weights"
    if italic_count:
        variant_info += f" + {italic_count} italics"

    return (
        f'<div class="dm-font-showcase">\n'
        f"  <h3>{family}</h3>\n"
        f'  <p class="desc">{desc} · '
        f"<strong>{variant_info}</strong></p>\n"
        f"{hero}\n"
        f'  <div class="dm-showcase-grid">\n'
        f"{weight_rows}\n  </div>\n"
        f"</div>"
    )


def generate_condensed_comparison_html(families: dict[str, list[str]]) -> str:
    """Generate side-by-side comparison of condensed variants."""
    condensed_families = [
        ("NotoSans", "Regular"),
        ("NotoSans_SemiCondensed", "Semi Condensed"),
        ("NotoSans_Condensed", "Condensed"),
        ("NotoSans_ExtraCondensed", "Extra Condensed"),
    ]

    sample = "The dartwork designs beautiful data artworks since 2021."

    rows = []
    for family_key, display_name in condensed_families:
        fonts = families.get(family_key)
        if not fonts:
            continue
        regular = _find_regular(fonts)
        if not regular:
            continue
        css_name = _font_face_name(regular)
        rows.append(
            f'  <div class="dm-condensed-row">\n'
            f'    <span class="dm-condensed-label">'
            f"{display_name}</span>\n"
            f'    <span class="dm-condensed-sample" '
            f"style=\"font-family:'{css_name}'\">"
            f"{sample}</span>\n"
            f"  </div>"
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-showcase">\n'
        f"  <h3>Condensed Variants Comparison</h3>\n"
        f'  <p class="desc">Same text rendered at four widths '
        f"— choose based on available space</p>\n"
        f'  <div class="dm-condensed-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def generate_multilang_html() -> str:
    """Generate multi-language specimen HTML."""
    langs = [
        (
            "한국어",
            "데이터 시각화를 위한 전문 타이포그래피",
            "Paperlogy-4Regular.ttf",
            "Paperlogy",
        ),
        (
            "English",
            "Professional typography for data visualization",
            "NotoSans-Regular.ttf",
            "Noto Sans",
        ),
        (
            "日本語",
            "データ可視化のためのタイポグラフィ",
            "NotoSans-Regular.ttf",
            "Noto Sans CJK",
        ),
        (
            "中文",
            "用于数据可视化的专业排版",
            "NotoSans-Regular.ttf",
            "Noto Sans CJK",
        ),
        (
            "Math",
            "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃",
            "NotoSansMath-Regular.ttf",
            "Noto Sans Math",
        ),
    ]

    rows = []
    for label, sample, font_file, display_name in langs:
        css_name = _font_face_name(font_file)
        rows.append(
            f'  <span class="lang-label" '
            f"style=\"font-family:'{css_name}'\">"
            f"{label}</span>\n"
            f'  <span class="lang-sample" '
            f"style=\"font-family:'{css_name}'\">"
            f"{sample}</span>\n"
            f'  <span class="lang-font-name">'
            f"{display_name}</span>"
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>Multi-Language Support</h3>\n"
        f'  <p class="desc">All rendered with bundled fonts '
        f"— no system font installation required</p>\n"
        f'  <div class="dm-multilang-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def generate_math_html() -> str:
    """Generate NotoSansMath specimen HTML."""
    css_name = "dm-NotoSansMath-Regular"
    equations = [
        ("Symbols", "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃"),
        ("Arithmetic", "1 + 2 − 3 × 4 ÷ 5 = ± 6"),
        ("Inequalities", "x ≤ y ∧ y ≥ z ⇒ x ≈ z"),
        ("Set Theory", "A ∪ B = B ∩ A ⊂ ℝ"),
        ("Geometry", "α^2 + β^2 = γ^2"),
        ("Euler", "e^(iπ) + 1 = 0"),
        ("Logic", "∀x ∃y : P(x) ∨ ¬Q(y)"),
    ]

    rows = []
    for label, expr in equations:
        rows.append(
            f'  <span class="label" '
            f"style=\"font-family:'{css_name}'\">"
            f"{label}</span>\n"
            f'  <span class="expr" '
            f"style=\"font-family:'{css_name}'\">"
            f"{expr}</span>"
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>NotoSansMath</h3>\n"
        f'  <p class="desc">'
        f"Mathematical symbols and equations font</p>\n"
        f'  <div class="dm-math-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def build_html_specimens() -> None:
    """Generate all HTML specimen files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy fonts to _static/fonts/
    STATIC_FONTS.mkdir(parents=True, exist_ok=True)
    for ttf in FONT_DIR.glob("*.ttf"):
        shutil.copy2(ttf, STATIC_FONTS / ttf.name)
    print(f"[html-specimens] copied fonts to {STATIC_FONTS}")

    # 2. Generate @font-face CSS
    css = generate_fontface_css()
    css_path = ROOT / "docs" / "_static" / "font-face.css"
    css_path.write_text(css)
    print(f"[html-specimens] wrote {css_path}")

    # 3. Generate per-family HTML snippets (full weight grid)
    families = _collect_fonts()
    for family, fonts in families.items():
        if family == "NotoSansMath":
            html = generate_math_html()
        else:
            html = generate_family_html(family, fonts)
        out = OUT_DIR / f"{family.lower()}.html"
        out.write_text(html)

    # 4. Generate per-family showcase HTML (compact key weights)
    for family, fonts in families.items():
        if family == "NotoSansMath":
            continue
        html = generate_family_showcase_html(family, fonts)
        out = OUT_DIR / f"{family.lower()}_showcase.html"
        out.write_text(html)

    # 5. Generate condensed comparison HTML
    condensed_html = generate_condensed_comparison_html(families)
    (OUT_DIR / "condensed_comparison.html").write_text(condensed_html)

    # 6. Generate multi-language HTML
    ml_html = generate_multilang_html()
    (OUT_DIR / "multilang.html").write_text(ml_html)

    count = len(list(OUT_DIR.glob("*.html")))
    print(f"[html-specimens] wrote {count} HTML specimens to {OUT_DIR}")


if __name__ == "__main__":
    build_html_specimens()
