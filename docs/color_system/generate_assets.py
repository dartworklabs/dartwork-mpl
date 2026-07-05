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
from dartwork_mpl.colors._loader import COLOR_LIBRARIES

# Sane defaults for how we display things.
CATEGORY_ORDER = [
    "Single-Hue",
    "Multi-Hue",
    "Diverging",
    "Cyclical",
    "Categorical",
]

CATEGORY_BLURBS: dict[str, str] = {
    "Single-Hue": "One hue that ramps value cleanly. Great for magnitude and density.",
    "Multi-Hue": "Colorful ramps that stay perceptually smooth. Ideal for heatmaps.",
    "Diverging": "Two anchored hues split around a midpoint. Perfect for anomalies or signed values.",
    "Cyclical": "Start equals end. Use for angles, phases, or anything periodic.",
    "Categorical": "Distinct steps with little interpolation. Use for discrete classes.",
}

# Derived from the colour-library SSOT (dartwork_mpl.colors._loader).
COLOR_LIBRARY_ORDER = [key for key, _p, _f, _lbl in COLOR_LIBRARIES]
COLOR_LIBRARY_LABELS = {key: label for key, _p, _f, label in COLOR_LIBRARIES}


def _prepare_images_dir(base_dir: Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(__file__).parent
    images_dir = base / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def _save_svg(fig, path: Path, **savefig_kwargs) -> Path:
    """Write *fig* as a byte-stable SVG.

    A fixed per-file ``svg.hashsalt`` (the output basename) pins the
    element ids and ``metadata={"Date": None}`` drops the embedded
    timestamp, so re-rendering an unchanged figure is byte-identical
    instead of churning the tracked asset. Mirrors the ``save`` helper in
    docs/color_system/generate_theory_figures.py.
    """
    with matplotlib.rc_context({"svg.hashsalt": path.stem}):
        fig.savefig(
            path, format="svg", metadata={"Date": None}, **savefig_kwargs
        )
    return path


def _collect_colormaps() -> dict[str, list[mpl.colors.Colormap]]:
    """Bucket the v5 colormap catalog by category.

    Sources the names from the authoritative v5 catalog
    (``dartwork_mpl.colors._generated.CMAPS_256`` + the two registered
    cycles), *not* from a raw ``dc.``-prefix scan — the legacy
    ``dartwork_mpl.cmap`` loader can also register backward-compat maps
    (``dc.obsidian``, ``dc.legacy_aurora``, …) into the same registry, and
    the docs explorer must show only the default v5 surface.
    """
    from dartwork_mpl.colors._generated import CMAPS_256

    v5_names = {f"dc.{n}" for n in CMAPS_256} | {"dc.cycle", "dc.cycle_print"}
    cmap_list: Iterable[str] = (
        name for name in mpl.colormaps if str(name) in v5_names
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

    return 0.2104542553 * l_cr + 0.7936177850 * m_cr - 0.0040720468 * s_cr


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


def _write_dc_sheet(images_dir: Path, label: str, mapping: dict) -> Path:
    """Build the dc v5 sheet: one row per generated family, slots in
    numeric step order. Swatches are interactive (hover → name+hex).
    """
    from dartwork_mpl.colors._generated import PALETTE
    from dartwork_mpl.colors._recipe import FAMILIES

    order = [*FAMILIES, "gray"]

    html = [
        '<div class="dm-color-sheet">',
        f'<div class="dm-sheet-title">{label}</div>',
    ]
    for key in order:
        if key not in PALETTE:
            continue
        base = key.lower()
        glabel = f"dc.{base}"
        html.append('<div class="dm-color-group">')
        html.append(f'<span class="dm-group-label">{glabel}</span>')
        html.append('<div class="dm-swatch-row">')
        for i, fallback in enumerate(PALETTE[key]):
            cname = f"dc.{base}{i}"
            spec = mapping.get(cname)
            if spec is None:
                spec = fallback
            hex_val = spec if isinstance(spec, str) else mpl.colors.to_hex(spec)
            tc = _text_color_for_bg(hex_val)
            html.append(
                f'<div class="dm-swatch" style="background:{hex_val}"'
                f' title="{cname}">'
                f'<span class="dm-swatch-name" style="color:{tc}">{i}</span>'
                f'<span class="dm-swatch-hex" style="color:{tc}">'
                f"{hex_val}</span></div>"
            )
        html.append("</div></div>")
    html.append("</div>")

    path = images_dir / "colors_dc.html"
    path.write_text("\n".join(html), encoding="utf-8")
    return path


def _write_dc_family_sheet(images_dir: Path) -> Path:
    """Build the v5 generative-family sheet: 16 single-hue families, ten
    perceptually-equalized steps each, straight from the shipped palette SSOT
    (``dartwork_mpl.colors._generated.PALETTE``). Ordered by hue so the sheet
    reads as one continuous system. Swatches are interactive (hover → name).
    """
    from dartwork_mpl.colors._generated import PALETTE
    from dartwork_mpl.colors._recipe import FAMILIES

    order = [*FAMILIES, "gray"]  # hue order, achromatic last

    html = [
        '<div class="dm-color-sheet">',
        '<div class="dm-sheet-title">dartwork Color — v5 families</div>',
    ]
    for fam in order:
        rows = PALETTE.get(fam)
        if not rows:
            continue
        html.append('<div class="dm-color-group">')
        html.append(f'<span class="dm-group-label">dc.{fam}</span>')
        html.append('<div class="dm-swatch-row">')
        for i, hex_val in enumerate(rows):
            cname = f"dc.{fam}{i}"
            tc = _text_color_for_bg(hex_val)
            html.append(
                f'<div class="dm-swatch" style="background:{hex_val}"'
                f' title="{cname}">'
                f'<span class="dm-swatch-name" style="color:{tc}">{i}</span>'
                f'<span class="dm-swatch-hex" style="color:{tc}">'
                f"{hex_val}</span></div>"
            )
        html.append("</div></div>")
    html.append("</div>")

    path = images_dir / "colors_dc_families.html"
    path.write_text("\n".join(html), encoding="utf-8")
    return path


def _save_color_sheets_html(images_dir: Path) -> list[Path]:
    """Generate HTML fragment files for each color library."""
    from dartwork_mpl.colors._loader import ensure_loaded

    ensure_loaded()
    mapping = mpl.colors.get_named_colors_mapping()

    # Prefix → library key mapping (derived from the colour-library SSOT).
    prefix_map = {key: prefix for key, prefix, _f, _lbl in COLOR_LIBRARIES}

    paths: list[Path] = []
    for library_key in COLOR_LIBRARY_ORDER:
        prefix = prefix_map.get(library_key, "")
        label = COLOR_LIBRARY_LABELS.get(library_key, library_key)

        # dc uses dedicated v5 builders so family steps stay in numeric order.
        if library_key == "dc":
            paths.append(_write_dc_family_sheet(images_dir))
            paths.append(_write_dc_sheet(images_dir, label, mapping))
            continue

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

        html_parts = ['<div class="dm-color-sheet">']
        html_parts.append(f'<div class="dm-sheet-title">{label}</div>')

        for base in sorted(lib_colors.keys()):
            colors_list = sorted(lib_colors[base], key=_weight_sort_key)
            # Group label shows prefix+base (e.g. "tw.amber", "dc.red")
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
        tabs_html.append(
            f'    <button class="dm-pc-tab dm-pe-tab" data-preset="{library_key}">{label}</button>'
        )
        # Panel content - read from the file we just wrote
        sheet_path = images_dir / f"colors_{library_key}.html"
        if sheet_path.exists():
            content = sheet_path.read_text(encoding="utf-8")
            display_style = "block" if i == 0 else "none"
            panels_html.append(
                f'    <div class="dm-pe-panel" data-preset="{library_key}" style="display: {display_style};">'
            )
            panels_html.append(content)
            panels_html.append("    </div>")

    pe_html = _PE_TEMPLATE.format(
        tabs_html="\n".join(tabs_html), panels_html="\n".join(panels_html)
    )
    pe_path = images_dir / "palette_explorer.html"
    pe_path.write_text(pe_html, encoding="utf-8")
    paths.append(pe_path)

    return paths


def _save_colormap_panels_html(images_dir: Path) -> list[Path]:
    """Generate HTML fragment files for each colormap category."""
    categories = _collect_colormaps()
    n_samples = 32  # gradient stops

    paths: list[Path] = []

    import textwrap

    # Hybrid explorer: Option A's underline tabs (one category at a time)
    # + Option B's sticky top bar holding the Color / Mono toggle once.
    # No outer card, no fills, no shadows — Linear / Stripe / Vercel
    # docs visual language.
    _CE_TEMPLATE = textwrap.dedent("""\
    <div class="dm-ce">
    <style>
      .dm-ce {{
        font-family: var(--sy-f-sys, system-ui), sans-serif;
        color: var(--rx-gray-12, #1c2024);
        margin: 1rem 0 1.5rem;
      }}
      .dm-ce-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 0;
        border-bottom: 1px solid var(--dm-border-faint, #e8e8ec);
        margin-bottom: 1.4rem;
        position: sticky;
        top: 56px;
        background: var(--dm-bg-page, #ffffff);
        z-index: 5;
        flex-wrap: wrap;
      }}
      .dm-ce-tabs {{
        display: inline-flex;
        gap: 0;
        flex-wrap: wrap;
      }}
      .dm-ce-tab {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: var(--rx-gray-11, #60646c);
        padding: 8px 14px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: color 0.12s, border-color 0.12s;
        margin-bottom: -1px;
        font-family: inherit;
        letter-spacing: 0;
      }}
      .dm-ce-tab:hover {{ color: var(--rx-gray-12, #1c2024); }}
      .dm-ce-tab.active {{
        color: var(--rx-gray-12, #1c2024);
        border-bottom-color: var(--rx-accent-9, #12a594);
      }}
      .dm-ce-tone {{
        display: inline-flex;
        gap: 2px;
        padding-right: 2px;
      }}
      .dm-ce-tone-btn {{
        background: transparent;
        border: none;
        color: var(--rx-gray-11, #60646c);
        padding: 5px 12px;
        font-size: 12.5px;
        font-weight: 500;
        cursor: pointer;
        border-radius: 4px;
        transition: color 0.12s, background 0.12s;
        font-family: inherit;
      }}
      .dm-ce-tone-btn:hover {{
        color: var(--rx-gray-12, #1c2024);
        background: var(--rx-gray-a3, rgba(0,8,60,0.059));
      }}
      .dm-ce-tone-btn.active {{
        color: var(--rx-gray-12, #1c2024);
        background: var(--rx-gray-a4, rgba(0,0,39,0.09));
      }}
      .dm-ce-panel {{ display: none; }}
      .dm-ce-panel.active {{ display: block; }}
      .dm-ce-panel-title {{
        font-size: 16px;
        font-weight: 600;
        color: var(--rx-gray-12, #1c2024);
        letter-spacing: -0.005em;
        margin: 0 0 4px;
      }}
      .dm-ce-panel-desc {{
        color: var(--rx-gray-11, #60646c);
        font-size: 13.5px;
        line-height: 1.5;
        margin: 0 0 18px;
        max-width: 60ch;
      }}
      .dm-cmap-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 14px 32px;
      }}
      .dm-cmap-item {{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}
      .dm-cmap-name {{
        font-family: var(--sy-f-mono, monospace);
        font-size: 12.5px;
        color: var(--rx-gray-12, #1c2024);
        font-weight: 500;
      }}
      .dm-cmap-bar {{
        width: 100%;
        height: 18px;
        border-radius: 2px;
        transition: filter 0.2s;
      }}
      .dm-ce.mono .dm-cmap-bar {{ filter: grayscale(100%); }}
    </style>

    <div class="dm-ce-bar">
      <div class="dm-ce-tabs">
    {tabs_html}
      </div>
      <div class="dm-ce-tone" role="group" aria-label="Tone toggle">
        <button class="dm-ce-tone-btn active" data-tone="color">Color</button>
        <button class="dm-ce-tone-btn" data-tone="mono">Mono</button>
      </div>
    </div>

    <div class="dm-ce-stage">
    {panels_html}
    </div>

    <script>
    (function() {{
      var root = document.currentScript.parentNode;
      var tabs = root.querySelectorAll(".dm-ce-tab");
      var panels = root.querySelectorAll(".dm-ce-panel");
      function activate(preset) {{
        tabs.forEach(function(t) {{ t.classList.toggle("active", t.dataset.preset === preset); }});
        panels.forEach(function(p) {{ p.classList.toggle("active", p.dataset.preset === preset); }});
      }}
      tabs.forEach(function(t) {{
        t.addEventListener("click", function() {{ activate(t.dataset.preset); }});
      }});
      if (tabs.length > 0) {{ activate(tabs[0].dataset.preset); }}

      var toneBtns = root.querySelectorAll(".dm-ce-tone-btn");
      toneBtns.forEach(function(btn) {{
        btn.addEventListener("click", function() {{
          toneBtns.forEach(function(b) {{ b.classList.remove("active"); }});
          btn.classList.add("active");
          if (btn.dataset.tone === "mono") {{ root.classList.add("mono"); }}
          else {{ root.classList.remove("mono"); }}
        }});
      }});
    }})();
    </script>
    </div>
    """)

    tabs_html = []
    panels_html = []

    # We include Categorical now because we have dc.red, dc.cyan, dc.gray, dc.pink
    display_categories = CATEGORY_ORDER

    for category in display_categories:
        cmaps = categories.get(category)
        if not cmaps:
            continue

        slug = category.lower().replace(" ", "_").replace("-", "_")
        blurb = CATEGORY_BLURBS.get(category, "")

        # Per-category fragment (also written as a standalone file so
        # markdown pages can embed a single category directly).
        frag_parts = ['<div class="dm-ce-panel-title">' + category + "</div>"]
        if blurb:
            frag_parts.append(f'<div class="dm-ce-panel-desc">{blurb}</div>')
        frag_parts.append('<div class="dm-cmap-grid">')

        for cmap in cmaps:
            is_categorical = hasattr(cmap, "colors") and len(cmap.colors) < 15

            if is_categorical:
                stops = []
                num_colors = len(cmap.colors)
                step = 100.0 / num_colors
                for j, color in enumerate(cmap.colors):
                    # to_hex handles hex strings AND (r,g,b[,a]) tuples and
                    # drops alpha itself — do not pre-slice `color[:3]`, which
                    # truncates a hex string ("#2d99f0" -> "#2d").
                    hex_c = mpl.colors.to_hex(color)
                    start = j * step
                    end = (j + 1) * step
                    stops.append(f"{hex_c} {start}%")
                    stops.append(f"{hex_c} {end}%")
                gradient = f"linear-gradient(to right, {', '.join(stops)})"
            else:
                stops = []
                for j in range(n_samples):
                    t = j / (n_samples - 1)
                    rgba = cmap(t)
                    hex_c = mpl.colors.to_hex(rgba[:3])
                    pct = round(t * 100, 1)
                    stops.append(f"{hex_c} {pct}%")
                gradient = f"linear-gradient(to right, {', '.join(stops)})"

            frag_parts.append(
                f'<div class="dm-cmap-item">'
                f'<span class="dm-cmap-name">{cmap.name}</span>'
                f'<div class="dm-cmap-bar" style="background:{gradient}"></div>'
                f"</div>"
            )

        frag_parts.append("</div>")
        frag_html = "\n".join(frag_parts)

        path = images_dir / f"colormaps_{slug}.html"
        path.write_text(frag_html, encoding="utf-8")
        paths.append(path)

        # Tab + panel for the unified explorer
        tabs_html.append(
            f'    <button class="dm-ce-tab" data-preset="{slug}">{category}</button>'
        )
        panels_html.append(
            f'    <div class="dm-ce-panel" data-preset="{slug}">{frag_html}</div>'
        )

    ce_html = _CE_TEMPLATE.format(
        tabs_html="\n".join(tabs_html), panels_html="\n".join(panels_html)
    )
    ce_path = images_dir / "colormap_explorer.html"
    ce_path.write_text(ce_html, encoding="utf-8")
    paths.append(ce_path)

    return paths


def _save_color_space_creation(images_dir: Path) -> Path:
    """Generate example showing different ways to create Color objects."""
    dm.style.use("scientific")

    fig = plt.figure(figsize=dm.figsize("15cm", "13cm"), dpi=300)
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
        ("Color", dm.color("dc.teal2"), "dm.color('dc.teal2')"),
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
    _save_svg(fig, path, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_conversion(images_dir: Path) -> Path:
    """Generate example showing color space conversions."""
    dm.style.use("scientific")

    fig = plt.figure(figsize=dm.figsize("15cm", "6.5cm"), dpi=300)
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

    color = dm.color("tw.blue600")
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
    _save_svg(fig, path, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_interpolation(images_dir: Path) -> Path:
    """Generate example comparing interpolation in different color spaces."""
    dm.style.use("scientific")

    # Create figure
    fig = plt.figure(figsize=dm.figsize("15cm", "10cm"), dpi=300)
    fig.patch.set_facecolor("#fbfaf7")

    # GridSpec layout: title + 3x(gradient + Lightness) = 7 rows
    # Keep hspace tight within groups; control between-group spacing via height_ratios
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

    # Title axes (spans entire first row)
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

    # Colors where RGB interpolation artifacts are visible (purple-yellow, complementary pair)
    start_color = dm.hex("#7c3aed")  # purple
    end_color = dm.hex("#fbbf24")  # yellow
    n = 20

    spaces = [("OKLCH", "oklch"), ("OKLab", "oklab"), ("RGB", "rgb")]

    for space_idx, (label, space) in enumerate(spaces):
        # gradient row indices: 1, 3, 5
        # Lightness row indices: 2, 4, 6
        grad_row = 1 + space_idx * 2
        lval_row = 2 + space_idx * 2

        # Label axes (left column, gradient rows only)
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

        # Gradient axes (right column)
        ax = fig.add_subplot(gs[grad_row, 1])
        colors = dm.cspace(start_color, end_color, n=n, space=space)
        gradient = np.array([c.to_rgb() for c in colors])
        gradient = gradient[np.newaxis, :, :]

        ax.set_facecolor("#ffffff")
        ax.imshow(gradient, aspect="auto", extent=[0, 1, 0, 1])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)

        # Lightness label axes (left column)
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

        # Lightness box axes (right column)
        ax_l = fig.add_subplot(gs[lval_row, 1])
        # Visualize each color's L value as grayscale
        l_values = np.array([c.oklab.L for c in colors])
        l_gradient = np.stack([l_values, l_values, l_values], axis=1)
        l_gradient = l_gradient[np.newaxis, :, :]

        ax_l.imshow(l_gradient, aspect="auto", extent=[0, 1, 0, 1])
        ax_l.set_xticks([])
        ax_l.set_yticks([])
        ax_l.set_frame_on(False)

    # Optimize layout (GridSpec-specific)
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "color_space_interpolation.svg"
    _save_svg(fig, path, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_smooth_gradient_2d(size: int = 240) -> np.ndarray:
    """Return a single-peak 2D gaussian that reads naturally under both
    sequential (low-to-high) and diverging (center-pivot) colormaps.

    Random noise hides the ramp entirely — under a sequential map it
    looks like static; under a diverging map you cannot tell the pivot
    from the tails. A smooth peak shows both ramps doing their job in
    one frame.
    """
    grid = np.linspace(-3.0, 3.0, size)
    xx, yy = np.meshgrid(grid, grid)
    return (
        np.exp(-(xx**2 + yy**2) / 2.0) * 2.0 - 1.0
    )  # values in roughly [-1, +1]


def _save_cspace_swatch(
    images_dir: Path,
    *,
    kind: str,
    cmap: mpl.colors.Colormap,
    data: np.ndarray,
    vmin: float,
    vmax: float,
) -> Path:
    """One small SVG per kind ("sequential" / "diverging"). Each panel
    shows the cmap applied to the same smooth 2D Gaussian so the reader
    can compare both ramps at a glance. Native Markdown wraps two of
    these in a 2-column grid, which is more responsive than baking
    everything into one wide figure.
    """
    dm.style.use("scientific")

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=200)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("#ffffff")

    im = ax.imshow(data, cmap=cmap, aspect="equal", vmin=vmin, vmax=vmax)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "bottom", "left", "right"):
        ax.spines[side].set_visible(False)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.08)
    cbar = fig.colorbar(im, cax=cax)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(labelsize=dm.fs(-2))

    dm.simple_layout(fig)
    path = images_dir / f"color_space_colormap_{kind}.svg"
    _save_svg(fig, path, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_color_space_colormap(images_dir: Path) -> Path:
    """Generate two small swatches — sequential and diverging — that the
    colormaps page composes side-by-side via a native ``{grid}`` block.

    The previous incarnation baked both swatches, both colorbars, *and*
    pseudo "code blocks" rendered as ``ax.text`` into one 15 cm SVG.
    That picture didn't fill the body width on a 1440 viewport, the
    code wasn't selectable / copyable / themed, and the underlying data
    was ``np.random.randn`` noise — so neither colormap had anything
    interesting to show. We now emit two real swatches and let
    Markdown handle the code blocks and the responsive grid.

    Returns the *sequential* swatch path for backward-compat with the
    aggregating ``_save_color_space_examples`` (which returns ``list``).
    """
    data = _make_smooth_gradient_2d()

    # Sequential — single-hue ramp on OKLCH
    seq_colors = dm.cspace("#1a237e", "#ff6f00", n=256, space="oklch")
    seq_cmap = mpl.colors.ListedColormap([c.to_rgb() for c in seq_colors])
    seq_path = _save_cspace_swatch(
        images_dir,
        kind="sequential",
        cmap=seq_cmap,
        data=data,
        vmin=float(data.min()),
        vmax=float(data.max()),
    )

    # Diverging — symmetric pivot at zero
    half1 = dm.cspace("#1a237e", "#ffffff", n=128, space="oklch")
    half2 = dm.cspace("#ffffff", "#c62828", n=128, space="oklch")
    div_colors = half1[:-1] + half2
    div_cmap = mpl.colors.ListedColormap([c.to_rgb() for c in div_colors])
    _save_cspace_swatch(
        images_dir,
        kind="diverging",
        cmap=div_cmap,
        data=data,
        vmin=-1.0,
        vmax=1.0,
    )

    return seq_path


def _save_color_space_examples(images_dir: Path) -> list[Path]:
    """Generate all Color Space example images."""
    return [
        _save_color_space_creation(images_dir),
        _save_color_space_conversion(images_dir),
        _save_color_space_interpolation(images_dir),
        _save_color_space_colormap(images_dir),
    ]


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
