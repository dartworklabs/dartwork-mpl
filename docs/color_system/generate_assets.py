"""
Generate high-resolution gallery assets for the color system docs.

The entrypoint `build_gallery_assets()` is invoked from Sphinx (see docs/conf.py)
so that the gallery stays in sync with every build. You can also run this file
directly:

    python docs/color_system/generate_assets.py
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable

# Make sure the source tree is importable when running the script directly.
ROOT = Path(__file__).resolve().parents[2]  # docs/color -> docs -> project root
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import dartwork_mpl as dm

# Sane defaults for how we display things.
CATEGORY_ORDER = [
    "Sequential Single-Hue",
    "Sequential Multi-Hue",
    "Diverging",
    "Cyclical",
    "Categorical",
]

CATEGORY_BLURBS: dict[str, str] = {
    "Sequential Single-Hue": "One hue that ramps value cleanly. Great for magnitude and density.",
    "Sequential Multi-Hue": "Colorful ramps that stay perceptually smooth. Ideal for heatmaps.",
    "Diverging": "Two anchored hues split around a midpoint. Perfect for anomalies or signed values.",
    "Cyclical": "Start equals end. Use for angles, phases, or anything periodic.",
    "Categorical": "Distinct steps with little interpolation. Use for discrete classes.",
}

COLOR_LIBRARY_ORDER = ["dc", "opencolor", "tw", "md", "ant", "chakra", "primer"]
COLOR_LIBRARY_LABELS = {
    "dc": "dartwork Color",
    "opencolor": "OpenColor",
    "tw": "Tailwind",
    "md": "Material Design",
    "ant": "Ant Design",
    "chakra": "Chakra UI",
    "primer": "Primer",
}


def _prepare_images_dir(base_dir: Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(__file__).parent
    images_dir = base / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def _collect_colormaps() -> dict[str, list[mpl.colors.Colormap]]:
    """Bucket colormaps by category."""
    from dartwork_mpl.cmap import ensure_loaded as cmap_ensure_loaded
    cmap_ensure_loaded()
    cmap_list: Iterable[str] = (
        name
        for name in mpl.colormaps
        if str(name).startswith("dc.") and not str(name).endswith("_r")
    )
    cmaps = [mpl.colormaps[name] for name in cmap_list]

    categories: dict[str, list[mpl.colors.Colormap]] = {
        category: [] for category in CATEGORY_ORDER
    }
    for cmap in cmaps:
        category = dm.classify_colormap(cmap)
        if category in categories:
            categories[category].append(cmap)

    for values in categories.values():
        values.sort(key=lambda cmap: cmap.name)

    return {k: v for k, v in categories.items() if v}


# ─── HTML/CSS native rendering ─────────────────────────────────────────


def _oklch_lightness(hex_str: str) -> float:
    """Compute OKLCH Lightness from a hex color string.

    Uses the OKLab intermediate: hex → linear sRGB → OKLab L.
    """
    r_srgb, g_srgb, b_srgb = _hex_to_rgb01(hex_str)

    # sRGB → linear RGB
    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = _lin(r_srgb), _lin(g_srgb), _lin(b_srgb)

    # linear RGB → LMS (via OKLab matrix)
    l_ = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
    m_ = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
    s_ = 0.0883024619 * r_lin + 0.2817188376 * g_lin + 0.6299787005 * b_lin

    # LMS → OKLab L (cube root)
    l_cr = l_ ** (1 / 3) if l_ >= 0 else 0.0
    m_cr = m_ ** (1 / 3) if m_ >= 0 else 0.0
    s_cr = s_ ** (1 / 3) if s_ >= 0 else 0.0

    L = 0.2104542553 * l_cr + 0.7936177850 * m_cr - 0.0040720468 * s_cr
    return L


def _relative_luminance_rgb(r: float, g: float, b: float) -> float:
    """ITU-R BT.709 relative luminance."""
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _hex_to_rgb01(hex_str: str) -> tuple[float, float, float]:
    """Convert hex color to (r,g,b) in 0-1 range."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _text_color_for_bg(hex_str: str) -> str:
    """Return white or dark text depending on background luminance."""
    r, g, b = _hex_to_rgb01(hex_str)
    return "#fff" if _relative_luminance_rgb(r, g, b) < 0.45 else "#333"


def _save_color_sheets_html(images_dir: Path) -> list[Path]:
    """Generate HTML fragment files for each color library."""
    from dartwork_mpl.color._loader import ensure_loaded

    ensure_loaded()
    mapping = mpl.colors.get_named_colors_mapping()

    # Prefix → library key mapping
    prefix_map = {
        "dc": "dc.",
        "opencolor": "oc.",
        "tw": "tw.",
        "md": "md.",
        "ant": "ad.",
        "chakra": "cu.",
        "primer": "pr.",
    }

    paths: list[Path] = []
    for library_key in COLOR_LIBRARY_ORDER:
        prefix = prefix_map.get(library_key, "")
        label = COLOR_LIBRARY_LABELS.get(library_key, library_key)

        # Collect colors for this library, grouped by base name
        lib_colors: dict[str, list[tuple[str, str, str]]] = {}
        for name, spec in mapping.items():
            if not name.startswith(prefix):
                continue
            suffix = name[len(prefix) :]
            # Split into alpha base + numeric/alphanumeric weight
            import re

            m = re.match(r"^([a-zA-Z_]+)(.*)", suffix)
            if not m:
                continue
            base = m.group(1)
            weight = m.group(2)  # e.g. "50", "500", "A100", "0"
            hex_val = spec if isinstance(spec, str) else mpl.colors.to_hex(spec)
            lib_colors.setdefault(base, []).append((name, weight, hex_val))

        if not lib_colors:
            continue

        # Sort groups alphabetically, weights numerically within each
        def _weight_sort_key(item: tuple[str, str, str]) -> tuple:
            """Sort key: pure digits first numerically, then alpha."""
            w = item[1]
            if w.isdigit():
                return (0, int(w), "")
            # Mixed alpha-numeric (e.g. "A100")
            m2 = re.match(r"([A-Za-z]*)(\d+)", w)
            if m2:
                return (1, int(m2.group(2)), m2.group(1))
            return (2, 0, w)

        # For dm palettes: sort by OKLCH lightness (light→dark)
        def _oklch_sort_key(item: tuple[str, str, str]) -> float:
            """Sort by OKLCH lightness descending (light first)."""
            return -_oklch_lightness(item[2])

        is_dc = library_key == "dc"

        html_parts = ['<div class="dm-color-sheet">']
        html_parts.append(f'<div class="dm-sheet-title">{label}</div>')

        for base in sorted(lib_colors.keys()):
            sort_fn = _oklch_sort_key if is_dc else _weight_sort_key
            colors_list = sorted(lib_colors[base], key=sort_fn)
            # Group label shows prefix+base (e.g. "tw.amber", "dc.vivid")
            group_label = f"{prefix}{base}"

            html_parts.append('<div class="dm-color-group">')
            html_parts.append(
                f'<span class="dm-group-label">{group_label}</span>'
            )
            html_parts.append('<div class="dm-swatch-row">')
            for _cname, weight, hex_val in colors_list:
                tc = _text_color_for_bg(hex_val)
                html_parts.append(
                    f'<div class="dm-swatch" style="background:{hex_val}"'
                    f' title="{_cname}">'
                    f'<span class="dm-swatch-name" style="color:{tc}">'
                    f"{weight}</span>"
                    f'<span class="dm-swatch-hex" style="color:{tc}">'
                    f"{hex_val}</span></div>"
                )
            html_parts.append("</div></div>")

        html_parts.append("</div>")

        path = images_dir / f"colors_{library_key}.html"
        path.write_text("\n".join(html_parts), encoding="utf-8")
        paths.append(path)

    # --- Assemble Tabbed Palette Explorer ---
    import textwrap

    _PE_TEMPLATE = textwrap.dedent("""\
    <div class="dm-pe-widget">
      <div class="dm-pc-tabs" id="dm-pe-tabs">
    {tabs_html}
      </div>
      <div class="dm-pe-body" id="dm-pe-stage">
    {panels_html}
      </div>
    </div>
    <script>
    (function() {{
      document.addEventListener("DOMContentLoaded", function() {{
        var tabs = document.querySelectorAll(".dm-pe-tab");
        var panels = document.querySelectorAll(".dm-pe-panel");
        function activate(preset) {{
          tabs.forEach(function(t) {{
            t.classList.toggle("active", t.dataset.preset === preset);
          }});
          panels.forEach(function(p) {{
            p.classList.toggle("active", p.dataset.preset === preset);
            if (p.dataset.preset === preset) {{
              p.style.display = "block";
            }} else {{
              p.style.display = "none";
            }}
          }});
        }}
        tabs.forEach(function(t) {{
          t.addEventListener("click", function() {{ activate(t.dataset.preset); }});
        }});
        if (tabs.length > 0) {{ activate(tabs[0].dataset.preset); }}
      }});
    }})();
    </script>
    """)

    tabs_html = []
    panels_html = []
    for i, library_key in enumerate(COLOR_LIBRARY_ORDER):
        label = COLOR_LIBRARY_LABELS.get(library_key, library_key)
        # Tab
        tabs_html.append(f'    <button class="dm-pc-tab dm-pe-tab" data-preset="{library_key}">{label}</button>')
        # Panel content - read from the file we just wrote
        sheet_path = images_dir / f"colors_{library_key}.html"
        if sheet_path.exists():
            content = sheet_path.read_text(encoding="utf-8")
            display_style = "block" if i == 0 else "none"
            panels_html.append(f'    <div class="dm-pe-panel" data-preset="{library_key}" style="display: {display_style};">')
            panels_html.append(content)
            panels_html.append('    </div>')

    pe_html = _PE_TEMPLATE.format(
        tabs_html="\n".join(tabs_html),
        panels_html="\n".join(panels_html)
    )
    pe_path = images_dir / "palette_explorer.html"
    pe_path.write_text(pe_html, encoding="utf-8")
    paths.append(pe_path)

    return paths


def _save_colormap_panels_html(images_dir: Path) -> list[Path]:
    """Generate HTML fragment files for each colormap category."""
    categories = _collect_colormaps()
    n_samples = 32  # gradient stops
    
    # We maintain a list of known custom OKLCH colormap roots to label them
    oklch_cmaps = {"ocean", "sunset", "emerald", "berry", "balance", "earth", "twilight_oklch", "nebula", "marine", "neon", "steel", "flame", "lavender", "ash"}

    paths: list[Path] = []
    
    # We skip generating the "Categorical" panel which just had standard matplotlib maps
    display_categories = [c for c in CATEGORY_ORDER if c != "Categorical"]
    
    for category in display_categories:
        cmaps = categories.get(category)
        if not cmaps:
            continue

        blurb = CATEGORY_BLURBS.get(category, "")
        html_parts = ['<div class="dm-cmap-panel">']
        html_parts.append(f'<div class="dm-cmap-panel-title">{category}</div>')
        if blurb:
            html_parts.append(f'<div class="dm-cmap-panel-desc">{blurb}</div>')
        html_parts.append('<div class="dm-cmap-grid">')

        for cmap in cmaps:
            # Sample colormap to CSS gradient stops
            stops = []
            for i in range(n_samples):
                t = i / (n_samples - 1)
                rgba = cmap(t)
                hex_c = mpl.colors.to_hex(rgba[:3])
                pct = round(t * 100, 1)
                stops.append(f"{hex_c} {pct}%")
            gradient = f"linear-gradient(to right, {', '.join(stops)})"
            
            base_name = cmap.name.replace("dc.", "")
            origin_badge = '<span class="dm-cmap-origin-oklch" style="font-size: 0.65em; padding: 2px 4px; border-radius: 4px; background: #e3f2fd; color: #1565c0; margin-left: 6px;">OKLCH</span>' if base_name in oklch_cmaps else '<span class="dm-cmap-origin-crameri" style="font-size: 0.65em; padding: 2px 4px; border-radius: 4px; background: #f5f5f5; color: #666; margin-left: 6px;">Crameri</span>'

            html_parts.append(
                f'<div class="dm-cmap-item">'
                f'<div><span class="dm-cmap-name">{cmap.name}</span>{origin_badge}'
                f"</div>"
                f'<div class="dm-cmap-bar" style="background:{gradient}">'
                f"</div></div>"
            )

        html_parts.append("</div></div>")

        slug = category.lower().replace(" ", "_").replace("-", "_")
        path = images_dir / f"colormaps_{slug}.html"
        path.write_text("\n".join(html_parts), encoding="utf-8")
        paths.append(path)
    return paths


def _save_color_space_creation(images_dir: Path) -> Path:
    """Generate example showing different ways to create Color objects."""
    dm.style.use("scientific")

    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(13)), dpi=300)
    fig.patch.set_facecolor("#fbfaf7")

    gs = fig.add_gridspec(
        nrows=4,
        ncols=2,
        left=0.05,
        right=0.98,
        top=0.95,
        bottom=0.05,
        hspace=0.5,
        wspace=0.25,
        height_ratios=[0.08, 0.31, 0.31, 0.31],
    )

    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        "Creating Color Objects",
        fontsize=16,
        fontweight="bold",
        ha="center",
        va="center",
        transform=ax_title.transAxes,
    )

    examples = [
        ("OKLab", dm.oklab(0.7, 0.1, 0.2), "dm.oklab(0.7, 0.1, 0.2)"),
        ("OKLCH", dm.oklch(0.7, 0.2, 120), "dm.oklch(0.7, 0.2, 120)"),
        ("RGB", dm.rgb(0.8, 0.2, 0.3), "dm.rgb(0.8, 0.2, 0.3)"),
        ("Hex", dm.hex("#ff5733"), "dm.hex('#ff5733')"),
        ("Named", dm.named("oc.blue5"), "dm.named('oc.blue5')"),
        ("RGB 255", dm.rgb(200, 50, 75), "dm.rgb(200, 50, 75)"),
    ]

    for idx, (label, color, code) in enumerate(examples):
        row = idx // 2 + 1  # rows 1, 2, 3
        col = idx % 2  # cols 0, 1
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor("#ffffff")
        rgb_val = color.to_rgb()
        ax.add_patch(
            plt.Rectangle(
                (0, 0.35),
                1,
                0.65,
                facecolor=rgb_val,
                edgecolor="#e4e2dd",
                linewidth=1.5,
            )
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        ax.text(
            0.5,
            0.22,
            label,
            ha="center",
            va="top",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
        )
        ax.text(
            0.5,
            0.08,
            code,
            ha="center",
            va="top",
            transform=ax.transAxes,
            fontsize=8,
            family="monospace",
            color="#555",
        )

    dm.simple_layout(fig, gs=gs)
    path = images_dir / "color_space_creation.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_conversion(images_dir: Path) -> Path:
    """Generate example showing color space conversions."""
    dm.style.use("scientific")

    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(6.5)), dpi=300)
    fig.patch.set_facecolor("#fbfaf7")

    # GridSpec: title + 2×(label row + box row)
    gs = fig.add_gridspec(
        nrows=5,
        ncols=2,
        left=0.05,
        right=0.98,
        top=0.95,
        bottom=0.05,
        hspace=0.08,
        wspace=0.18,
        height_ratios=[0.14, 0.10, 0.38, 0.10, 0.38],
    )

    # Title
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        "Color Space Conversion",
        fontsize=16,
        fontweight="bold",
        ha="center",
        va="bottom",
        transform=ax_title.transAxes,
    )

    color = dm.named("tw.blue600")
    L, a, b = color.to_oklab()
    L_ch, C, h = color.to_oklch()
    r, g, b_rgb = color.to_rgb()
    hex_str = color.to_hex()

    conversions = [
        ("OKLab", f"L = {L: .3f}\na = {a: .3f}\nb = {b: .3f}", "center"),
        ("OKLCH", f"L = {L_ch:.3f}\nC = {C:.3f}\nh = {h:.1f}°", "left"),
        ("RGB", f"r = {r:.3f}\ng = {g:.3f}\nb = {b_rgb:.3f}", "center"),
        ("Hex", hex_str, "center"),
    ]

    text_color = "white" if L < 0.6 else "#333333"

    for idx, (label, values, align) in enumerate(conversions):
        grid_row = idx // 2  # 0 or 1
        grid_col = idx % 2  # 0 or 1
        label_row = 1 + grid_row * 2  # rows 1, 3
        box_row = 2 + grid_row * 2  # rows 2, 4

        ax_label = fig.add_subplot(gs[label_row, grid_col])
        ax_label.axis("off")
        ax_label.text(
            0.5,
            0.5,
            label,
            ha="center",
            va="center",
            transform=ax_label.transAxes,
            fontsize=11,
            fontweight="bold",
        )

        ax = fig.add_subplot(gs[box_row, grid_col])
        rgb_val = color.to_rgb()
        ax.add_patch(
            plt.Rectangle(
                (0, 0),
                1,
                1,
                facecolor=rgb_val,
                edgecolor="#e4e2dd",
                linewidth=1.5,
            )
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        ax.text(
            0.5,
            0.5,
            values,
            ha="center",
            va="center",
            multialignment=align,
            transform=ax.transAxes,
            fontsize=9,
            family="monospace",
            color=text_color,
        )

    dm.simple_layout(fig, gs=gs)
    path = images_dir / "color_space_conversion.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_interpolation(images_dir: Path) -> Path:
    """Generate example comparing interpolation in different color spaces."""
    dm.style.use("scientific")

    # Figure 생성
    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    fig.patch.set_facecolor("#fbfaf7")

    # GridSpec 구성: title + 3x(gradient + Lightness) = 7행
    # 그룹 내 간격(hspace)은 좁게, 그룹 간 간격은 height_ratios로 조절
    gs = fig.add_gridspec(
        nrows=7,
        ncols=2,
        left=0.15,
        right=0.98,
        top=0.92,
        bottom=0.05,
        hspace=0.05,
        wspace=0.02,
        height_ratios=[0.08, 0.18, 0.06, 0.18, 0.06, 0.18, 0.06],
        width_ratios=[0.10, 0.9],
    )

    # Title axes (첫 행 전체 사용)
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        "Color Interpolation Comparison",
        fontsize=16,
        fontweight="bold",
        ha="center",
        va="center",
        transform=ax_title.transAxes,
    )

    # RGB에서 보간 문제가 잘 보이는 색상 (보라-노랑, 보색 관계)
    start_color = dm.hex("#7c3aed")  # 보라색
    end_color = dm.hex("#fbbf24")  # 노란색
    n = 20

    spaces = [("OKLCH", "oklch"), ("OKLab", "oklab"), ("RGB", "rgb")]

    for space_idx, (label, space) in enumerate(spaces):
        # gradient 행 인덱스: 1, 3, 5
        # Lightness 행 인덱스: 2, 4, 6
        grad_row = 1 + space_idx * 2
        lval_row = 2 + space_idx * 2

        # 라벨 axes (왼쪽 열, gradient 행에만)
        ax_label = fig.add_subplot(gs[grad_row, 0])
        ax_label.axis("off")
        ax_label.text(
            0.95,
            0.5,
            label,
            ha="right",
            va="center",
            transform=ax_label.transAxes,
            fontsize=11,
            fontweight="bold",
        )

        # Gradient axes (오른쪽 열)
        ax = fig.add_subplot(gs[grad_row, 1])
        colors = dm.cspace(start_color, end_color, n=n, space=space)
        gradient = np.array([c.to_rgb() for c in colors])
        gradient = gradient[np.newaxis, :, :]

        ax.set_facecolor("#ffffff")
        ax.imshow(gradient, aspect="auto", extent=[0, 1, 0, 1])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)

        # Lightness 라벨 axes (왼쪽 열)
        ax_l_label = fig.add_subplot(gs[lval_row, 0])
        ax_l_label.axis("off")
        ax_l_label.text(
            0.95,
            0.5,
            "Lightness",
            ha="right",
            va="center",
            transform=ax_l_label.transAxes,
            fontsize=8,
            style="italic",
            color="#666",
        )

        # Lightness 박스 axes (오른쪽 열)
        ax_l = fig.add_subplot(gs[lval_row, 1])
        # 각 색상의 L값을 grayscale로 시각화
        l_values = np.array([c.oklab.L for c in colors])
        l_gradient = np.stack([l_values, l_values, l_values], axis=1)
        l_gradient = l_gradient[np.newaxis, :, :]

        ax_l.imshow(l_gradient, aspect="auto", extent=[0, 1, 0, 1])
        ax_l.set_xticks([])
        ax_l.set_yticks([])
        ax_l.set_frame_on(False)

    # 레이아웃 최적화 (GridSpec 지정)
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "color_space_interpolation.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_colormap(images_dir: Path) -> Path:
    """Generate example showing custom colormap creation."""
    dm.style.use("scientific")

    # Figure 생성
    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    fig.patch.set_facecolor("#fbfaf7")

    # GridSpec 구성: title 행 + 2x2 (이미지 행 + 코드 행)
    # height_ratios: title 10%, 이미지 45%, 코드 45%
    gs = fig.add_gridspec(
        nrows=3,
        ncols=2,
        left=0.08,
        right=0.92,
        top=0.95,
        bottom=0.08,
        hspace=0.35,
        wspace=0.30,
        height_ratios=[0.10, 0.45, 0.45],
    )

    # Title axes (첫 행 전체 사용)
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        "Custom Colormaps with cspace()",
        fontsize=16,
        fontweight="bold",
        ha="center",
        va="center",
        transform=ax_title.transAxes,
    )

    # Sequential colormap
    colors_seq = dm.cspace("#1a237e", "#ff6f00", n=256, space="oklch")
    cmap_seq = mpl.colors.ListedColormap([c.to_rgb() for c in colors_seq])

    # Diverging colormap
    colors1 = dm.cspace("#1a237e", "#ffffff", n=128, space="oklch")
    colors2 = dm.cspace("#ffffff", "#c62828", n=128, space="oklch")
    colors_div = colors1[:-1] + colors2
    cmap_div = mpl.colors.ListedColormap([c.to_rgb() for c in colors_div])

    # Generate sample data
    data = np.random.randn(100, 100)

    # Sequential example
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.set_facecolor("#ffffff")
    im1 = ax1.imshow(data, cmap=cmap_seq, aspect="auto")
    ax1.set_title("Sequential Colormap", fontsize=12, fontweight="bold", pad=10)
    ax1.set_xticks([])
    ax1.set_yticks([])

    # Colorbar using axes_divider (axes에 상대적 위치)
    divider1 = make_axes_locatable(ax1)
    cax1 = divider1.append_axes("right", size="5%", pad=0.08)
    cbar1 = fig.colorbar(im1, cax=cax1)
    cbar1.set_label("Value", fontsize=9)
    cbar1.ax.tick_params(labelsize=8)

    # Diverging example
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.set_facecolor("#ffffff")
    im2 = ax2.imshow(data, cmap=cmap_div, aspect="auto", vmin=-3, vmax=3)
    ax2.set_title("Diverging Colormap", fontsize=12, fontweight="bold", pad=10)
    ax2.set_xticks([])
    ax2.set_yticks([])

    # Colorbar using axes_divider (axes에 상대적 위치)
    divider2 = make_axes_locatable(ax2)
    cax2 = divider2.append_axes("right", size="5%", pad=0.08)
    cbar2 = fig.colorbar(im2, cax=cax2)
    cbar2.set_label("Value", fontsize=9)
    cbar2.ax.tick_params(labelsize=8)

    # Code examples
    code1 = """# Sequential
colors = dm.cspace(
    "#1a237e", "#ff6f00",
    n=256, space="oklch"
)
cmap = mpl.colors.ListedColormap(
    [c.to_rgb() for c in colors]
)"""

    code2 = """# Diverging
colors1 = dm.cspace(
    "#1a237e", "#ffffff",
    n=128, space="oklch"
)
colors2 = dm.cspace(
    "#ffffff", "#c62828",
    n=128, space="oklch"
)
colors = colors1[:-1] + colors2
cmap = mpl.colors.ListedColormap(
    [c.to_rgb() for c in colors]
)"""

    ax3 = fig.add_subplot(gs[2, 0])
    ax3.set_facecolor("#ffffff")
    ax3.text(
        0.05,
        0.95,
        code1,
        transform=ax3.transAxes,
        fontsize=8,
        family="monospace",
        va="top",
        ha="left",
        bbox={
            "boxstyle": "round",
            "facecolor": "#f8f8f8",
            "edgecolor": "#e4e2dd",
        },
    )
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.set_frame_on(False)

    ax4 = fig.add_subplot(gs[2, 1])
    ax4.set_facecolor("#ffffff")
    ax4.text(
        0.05,
        0.95,
        code2,
        transform=ax4.transAxes,
        fontsize=8,
        family="monospace",
        va="top",
        ha="left",
        bbox={
            "boxstyle": "round",
            "facecolor": "#f8f8f8",
            "edgecolor": "#e4e2dd",
        },
    )
    ax4.set_xlim(0, 1)
    ax4.set_ylim(0, 1)
    ax4.set_xticks([])
    ax4.set_yticks([])
    ax4.set_frame_on(False)

    # 레이아웃 최적화 (GridSpec 지정)
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "color_space_colormap.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_examples(images_dir: Path) -> list[Path]:
    """Generate all Color Space example images."""
    paths = [
        _save_color_space_creation(images_dir),
        _save_color_space_conversion(images_dir),
        _save_color_space_interpolation(images_dir),
        _save_color_space_colormap(images_dir),
    ]
    return paths


def build_gallery_assets(base_dir: Path | None = None) -> dict[str, list[Path]]:
    """Generate all gallery assets and return their paths."""
    images_dir = _prepare_images_dir(base_dir)
    print(f"[gallery] generating assets to {images_dir}")

    # HTML-native rendering (color sheets + colormaps)
    color_html_paths = _save_color_sheets_html(images_dir)
    cmap_html_paths = _save_colormap_panels_html(images_dir)

    # Color space examples (must remain SVG)
    color_space_paths = _save_color_space_examples(images_dir)

    print(
        f"[gallery] wrote {len(color_html_paths)} color HTML sheets, "
        f"{len(cmap_html_paths)} colormap HTML panels, "
        f"{len(color_space_paths)} color space examples"
    )
    return {
        "colors_html": color_html_paths,
        "colormaps_html": cmap_html_paths,
        "color_space": color_space_paths,
    }


if __name__ == "__main__":
    build_gallery_assets()
