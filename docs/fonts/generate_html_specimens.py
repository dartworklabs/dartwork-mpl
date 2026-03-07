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

FONT_META = {
    "Inter": {
        "description": "Modern, highly legible sans-serif designed for computer screens",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "InterDisplay": {
        "description": "Display variant of Inter optimized for larger sizes",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "NotoSans": {
        "description": "Google's versatile sans-serif with excellent language coverage",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "NotoSans_Condensed": {
        "description": "Condensed variant of Noto Sans for space-constrained layouts",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "NotoSans_SemiCondensed": {
        "description": "Semi-condensed variant balancing readability and compactness",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "NotoSans_ExtraCondensed": {
        "description": "Extra condensed for maximum space efficiency",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
    },
    "Paperlogy": {
        "description": "Clean, professional font designed for documents",
        "sample": "김도균 & 이주임 님이 만든 아름다운 페이퍼로지 폰트. 0123456789",
    },
    "Roboto": {
        "description": "Google's flagship sans-serif, default font in dartwork-mpl",
        "sample": "Sphinx of black quartz, judge my vow — designing beautiful charts & graphs since 2024. (0123456789)",
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
            lines.append(
                f"  src: url('fonts/{font}') format('truetype');"
            )
            lines.append("  font-display: swap;")
            lines.append("}")
            lines.append("")

    return "\n".join(lines)


def generate_family_html(family: str, fonts: list[str]) -> str:
    """Generate HTML specimen for one font family."""
    meta = FONT_META.get(family, {})
    desc = meta.get("description", "")
    sample = meta.get("sample", "The quick brown fox jumps over the lazy dog. 0123456789")

    sorted_fonts = sorted(fonts, key=_get_weight_score)
    regular = _find_regular(sorted_fonts)
    regular_css = _font_face_name(regular) if regular else "sans-serif"

    rows = []
    for font in sorted_fonts:
        label = _variant_label(font)
        css_name = _font_face_name(font)
        rows.append(
            f'  <span class="label" style="font-family:\'{regular_css}\'">{label}</span>\n'
            f'  <span class="sample" style="font-family:\'{css_name}\'">{sample}</span>'
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>{family}</h3>\n"
        f'  <p class="desc">{desc}</p>\n'
        f'  <div class="dm-font-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def generate_multilang_html() -> str:
    """Generate multi-language specimen HTML."""
    # Each entry: (label, sample_text, font_file, font_display_name)
    langs = [
        ("한국어", "데이터 시각화를 위한 전문 타이포그래피", "Paperlogy-4Regular.ttf", "Paperlogy"),
        ("English", "Professional typography for data visualization", "NotoSans-Regular.ttf", "Noto Sans"),
        ("日本語", "データ可視化のためのタイポグラフィ", "NotoSans-Regular.ttf", "Noto Sans CJK"),
        ("中文", "用于数据可视化的专业排版", "NotoSans-Regular.ttf", "Noto Sans CJK"),
        ("Math", "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃", "NotoSansMath-Regular.ttf", "Noto Sans Math"),
    ]

    rows = []
    for label, sample, font_file, display_name in langs:
        css_name = _font_face_name(font_file)
        rows.append(
            f'  <span class="lang-label" style="font-family:\'{css_name}\'">{label}</span>\n'
            f'  <span class="lang-sample" style="font-family:\'{css_name}\'">{sample}</span>\n'
            f'  <span class="lang-font-name">{display_name}</span>'
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>Multi-Language Support</h3>\n"
        f'  <p class="desc">All rendered with bundled fonts — no system font installation required</p>\n'
        f'  <div class="dm-multilang-grid">\n{grid}\n  </div>\n'
        f"</div>"
    )


def generate_math_html() -> str:
    """Generate NotoSansMath specimen HTML."""
    css_name = "dm-NotoSansMath-Regular"
    equations = [
        ("Symbols", "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∉ ⊂ ∪ ∩ ∀ ∃"),
        ("Quadratic", "x = (−b ± √(b² − 4ac)) / 2a"),
        ("Gaussian", "∫₋∞^∞ e^(−x²) dx = √π"),
        ("Green's Function", "G(r,t) = 1/(4παt)^(3/2) exp(−(x²+y²+z²)/(4αt))"),
        ("Entropy", "H(X) = −∑ᵢ p(xᵢ) log p(xᵢ)"),
        ("Heat Equation", "∂u/∂t = α(∂²u/∂x² + ∂²u/∂y² + ∂²u/∂z²)"),
        ("Navier-Stokes", "ρ(∂v/∂t + v·∇v) = −∇p + μ∇²v"),
    ]

    rows = []
    for label, expr in equations:
        rows.append(
            f'  <span class="label" style="font-family:\'{css_name}\'">{label}</span>\n'
            f'  <span class="expr" style="font-family:\'{css_name}\'">{expr}</span>'
        )

    grid = "\n".join(rows)
    return (
        f'<div class="dm-font-specimen">\n'
        f"  <h3>NotoSansMath</h3>\n"
        f'  <p class="desc">Mathematical symbols and equations font</p>\n'
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

    # 3. Generate per-family HTML snippets
    families = _collect_fonts()
    for family, fonts in families.items():
        if family == "NotoSansMath":
            html = generate_math_html()
        else:
            html = generate_family_html(family, fonts)
        out = OUT_DIR / f"{family.lower()}.html"
        out.write_text(html)

    # 4. Generate multi-language HTML
    ml_html = generate_multilang_html()
    (OUT_DIR / "multilang.html").write_text(ml_html)

    count = len(families) + 1  # +1 for multilang
    print(f"[html-specimens] wrote {count} HTML specimens to {OUT_DIR}")


if __name__ == "__main__":
    build_html_specimens()
