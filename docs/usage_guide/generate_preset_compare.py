"""Generate a self-contained preset comparison HTML widget.

Renders the same plot with every dartwork-mpl preset, inlines the SVGs,
and wraps them in a tabbed HTML viewer with CSS fade transitions and
a parameter info panel.

    python docs/usage_guide/generate_preset_compare.py
"""

from __future__ import annotations

import io
import json
import re
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import dartwork_mpl as dm  # noqa: E402

# ── Configuration ──────────────────────────────────────────────────────

PRESETS = [
    "scientific",
    "report",
    "presentation",
    "poster",
    "web",
    "minimal",
    "dark",
]

PRESET_META: dict[str, dict[str, str]] = {
    "scientific": {
        "use": "papers & journals",
        "desc": "Compact fonts, all four spines",
    },
    "report": {
        "use": "reports & dashboards",
        "desc": "Slightly larger, top/right spines hidden",
    },
    "presentation": {
        "use": "slides & talks",
        "desc": "Large fonts for projection",
    },
    "poster": {
        "use": "conference posters",
        "desc": "Largest fonts, thick lines",
    },
    "web": {
        "use": "web & documentation",
        "desc": "Screen-optimized, spine-light",
    },
    "minimal": {
        "use": "data-ink focus (Tufte)",
        "desc": "No spines, no ticks — data only",
    },
    "dark": {
        "use": "dark mode",
        "desc": "Inverted colors for dark backgrounds",
    },
}

# Key rcParams to show in the info panel
_PANEL_PARAMS = [
    ("font.size", "pt"),
    ("axes.titlesize", "pt"),
    ("axes.labelsize", "pt"),
    ("xtick.labelsize", "pt"),
    ("ytick.labelsize", "pt"),
    ("legend.fontsize", "pt"),
    ("lines.linewidth", "pt"),
    ("axes.linewidth", ""),
]

# Fixed figure size so all presets align perfectly
FIG_WIDTH_CM = 9.0
FIG_HEIGHT_CM = 6.0


# ── Plot function ──────────────────────────────────────────────────────


def _get_spine_desc(preset: str) -> str:
    """Return a human-readable spine description for *preset*."""
    dm.style.use(preset)
    rc = plt.rcParams
    top = rc.get("axes.spines.top", True)
    right = rc.get("axes.spines.right", True)
    bottom = rc.get("axes.spines.bottom", True)
    left = rc.get("axes.spines.left", True)

    if not any([top, right, bottom, left]):
        return "all hidden"
    if all([top, right, bottom, left]):
        return "all visible"
    hidden = []
    if not top:
        hidden.append("top")
    if not right:
        hidden.append("right")
    if not bottom:
        hidden.append("bottom")
    if not left:
        hidden.append("left")
    return f"{'/'.join(hidden)} hidden"


def _collect_preset_params(preset: str) -> dict[str, str]:
    """Collect rcParam values for the info panel."""
    dm.style.use(preset)
    rc = plt.rcParams
    params: dict[str, str] = {}
    for key, unit in _PANEL_PARAMS:
        val = rc.get(key, "—")
        if isinstance(val, float):
            if val == int(val):
                params[key] = f"{int(val)}"
            else:
                params[key] = f"{val:.1f}"
            if unit:
                params[key] += f" {unit}"
        else:
            params[key] = str(val)
    params["spines"] = _get_spine_desc(preset)
    return params


def _render_preset_svg(preset: str) -> str:
    """Render a sample plot with *preset* and return SVG as string."""
    dm.style.use(preset)

    fig, ax = plt.subplots(
        figsize=(dm.cm(FIG_WIDTH_CM), dm.cm(FIG_HEIGHT_CM)), dpi=150
    )

    # Sample data: thermal conductivity vs temperature
    temp = np.array([200, 400, 600, 800, 1000, 1200])
    sample_a = np.array([13, 42, 31, 71, 61, 90])
    sample_b = np.array([5, 21, 27, 43, 44, 68])

    ax.plot(
        temp,
        sample_a,
        marker="o",
        label="Sample A",
        color="oc.teal7",
        lw=dm.lw(1),
    )
    ax.plot(
        temp,
        sample_b,
        marker="s",
        linestyle="--",
        label="Sample B",
        color="oc.orange7",
        lw=dm.lw(1),
    )

    ax.set_title(
        "Thermal Conductivity vs. Temperature",
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
    )
    ax.set_xlabel("Temperature (K)", fontsize=dm.fs(0))
    ax.set_ylabel("Thermal Conductivity (W/m\u00b7K)", fontsize=dm.fs(0))
    ax.legend(fontsize=dm.fs(-1), frameon=False, loc="upper left")

    dm.simple_layout(fig)

    # Render SVG to string — NO bbox_inches='tight' for uniform size
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    plt.close(fig)
    return buf.getvalue()


def _normalize_svg_viewbox(svg: str, target_vb: str) -> str:
    """Force a uniform viewBox on an SVG so all presets occupy
    the exact same pixel footprint."""
    svg = re.sub(r'viewBox="[^"]*"', f'viewBox="{target_vb}"', svg, count=1)
    svg = re.sub(r'width="[^"]*"', 'width="100%"', svg, count=1)
    return re.sub(r'height="[^"]*"', 'height="100%"', svg, count=1)


def _strip_xml_declaration(svg: str) -> str:
    """Remove the <?xml ...?> line so inline embedding works."""
    lines = svg.split("\n")
    return "\n".join(
        line for line in lines if not line.strip().startswith("<?xml")
    )


# ── HTML assembly ──────────────────────────────────────────────────────

_HTML_TEMPLATE = textwrap.dedent("""\
<meta charset="utf-8" />
<style>
  .dm-pc-widget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      sans-serif;
    max-width: 100%;
    margin: 0 auto;
  }}
  .dm-pc-tabs {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
  }}
  .dm-pc-tab {{
    padding: 5px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: #f8f8f8;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: #555;
    transition: all 0.15s ease;
    user-select: none;
  }}
  .dm-pc-tab:hover {{
    background: #e8e8e8;
    border-color: #999;
  }}
  .dm-pc-tab.active {{
    background: #333;
    color: #fff;
    border-color: #333;
  }}
  /* ── Main layout: chart top, params bottom ── */
  .dm-pc-body {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  /* ── Chart stage (fixed size) ── */
  .dm-pc-stage {{
    position: relative;
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    width: 100%;
    /* Fixed aspect ratio via padding-bottom */
    aspect-ratio: {aspect_ratio};
  }}
  .dm-pc-panel {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }}
  .dm-pc-panel.active {{
    opacity: 1;
    pointer-events: auto;
  }}
  .dm-pc-panel svg {{
    display: block;
    width: 100%;
    height: 100%;
  }}
  /* ── Parameter info panel (multi-column grid) ── */
  .dm-pc-params {{
    font-size: 13px;
    background: #fdfdfd;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 16px;
  }}
  .dm-pc-params-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px 48px; /* wider gap between columns */
  }}
  .dm-pc-param-item {{
    display: flex;
    justify-content: flex-start;
    align-items: baseline;
    border-bottom: 1px solid #eee;
    padding-bottom: 6px;
  }}
  .dm-pc-param-key {{
    flex: 0 0 130px; /* fixed width for alignment */
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    color: #555;
    white-space: nowrap;
  }}
  .dm-pc-param-val {{
    font-weight: 600;
    color: #333;
    white-space: nowrap;
  }}
  .dm-pc-param-special {{
    grid-column: 1 / -1; /* Make 'best for' span full width if needed, or just let it flow */
    border-bottom: none;
    padding-top: 4px;
    align-items: center;
  }}
  .dm-pc-param-special .dm-pc-param-key {{
    flex: 0 0 auto;
    margin-right: 12px;
</style>

<div class="dm-pc-widget">
  <div class="dm-pc-tabs" id="dm-pc-tabs">
{tabs_html}
  </div>
  <div class="dm-pc-body">
    <div class="dm-pc-stage" id="dm-pc-stage">
{panels_html}
    </div>
    <div class="dm-pc-params" id="dm-pc-params">
      <div class="dm-pc-params-grid" id="dm-pc-params-grid"></div>
    </div>
  </div>
</div>

<script>
(function() {{
  var meta = {meta_json};
  var params = {params_json};
  document.addEventListener("DOMContentLoaded", function() {{
    var tabs = document.querySelectorAll(".dm-pc-tab");
    var panels = document.querySelectorAll(".dm-pc-panel");
    var pgrid = document.getElementById("dm-pc-params-grid");

    function activate(preset) {{
      tabs.forEach(function(t) {{
        t.classList.toggle("active", t.dataset.preset === preset);
      }});
      panels.forEach(function(p) {{
        p.classList.toggle("active", p.dataset.preset === preset);
      }});
      // Update params grid
      if (params[preset]) {{
        var html = "";
        var p = params[preset];
        var keys = Object.keys(p);
        for (var i = 0; i < keys.length; i++) {{
          var k = keys[i];
          if (k === "spines" || k === "best_for") continue;
          html += "<div class='dm-pc-param-item'><span class='dm-pc-param-key'>" + k + "</span><span class='dm-pc-param-val'>" + p[k] + "</span></div>";
        }}
        if (p["spines"]) {{
          html += "<div class='dm-pc-param-item'><span class='dm-pc-param-key'>spines</span><span class='dm-pc-param-val'>" + p["spines"] + "</span></div>";
        }}
        if (meta[preset]) {{
          html += "<div class='dm-pc-param-item dm-pc-param-special'><span class='dm-pc-param-key'>best for</span><span class='dm-pc-param-val'>" + meta[preset].use + "</span></div>";
        }}
        pgrid.innerHTML = html;
      }}
    }}

    tabs.forEach(function(t) {{
      t.addEventListener("click", function() {{
        activate(t.dataset.preset);
      }});
    }});

    // Default: activate first preset
    activate("{default_preset}");
  }});
}})();
</script>
""")


def build_preset_compare_html(output_path: Path | None = None) -> Path:
    """Generate the preset comparison widget.

    Parameters
    ----------
    output_path : Path | None
        Where to write the HTML. Defaults to
        ``docs/usage_guide/images/preset_compare.html``.

    Returns
    -------
    Path
        Path to the generated file.
    """
    if output_path is None:
        output_path = Path(__file__).parent / "images" / "preset_compare.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Render all presets ──
    svgs: dict[str, str] = {}
    all_params: dict[str, dict[str, str]] = {}
    for preset in PRESETS:
        print(f"  rendering '{preset}' ...")
        raw_svg = _render_preset_svg(preset)
        svgs[preset] = _strip_xml_declaration(raw_svg)
        all_params[preset] = _collect_preset_params(preset)

    # ── Extract the largest viewBox to use as common base ──
    max_w, max_h = 0.0, 0.0
    for svg in svgs.values():
        m = re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', svg)
        if m:
            w, h = float(m.group(1)), float(m.group(2))
            max_w = max(max_w, w)
            max_h = max(max_h, h)

    target_vb = f"0 0 {max_w:.6f} {max_h:.6f}"
    aspect_ratio = f"{max_w:.2f} / {max_h:.2f}"

    # Normalize all SVGs to the same viewBox
    for preset in PRESETS:
        svgs[preset] = _normalize_svg_viewbox(svgs[preset], target_vb)

    # ── Build tabs HTML ──
    tabs_lines = [
        f'    <button class="dm-pc-tab" data-preset="{preset}">{preset}</button>'
        for preset in PRESETS
    ]
    tabs_html = "\n".join(tabs_lines)

    # ── Build panels HTML ──
    panels_lines = []
    for preset in PRESETS:
        panels_lines.append(
            f'      <div class="dm-pc-panel" data-preset="{preset}">'
        )
        panels_lines.append(f"        {svgs[preset]}")
        panels_lines.append("      </div>")
    panels_html = "\n".join(panels_lines)

    # ── JSON data ──
    meta_json = json.dumps(PRESET_META, ensure_ascii=False)
    params_json = json.dumps(all_params, ensure_ascii=False)

    # ── Assemble ──
    html = _HTML_TEMPLATE.format(
        tabs_html=tabs_html,
        panels_html=panels_html,
        meta_json=meta_json,
        params_json=params_json,
        default_preset=PRESETS[0],
        aspect_ratio=aspect_ratio,
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"  ✓ preset_compare.html → {output_path}")
    return output_path


# ── Entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_preset_compare_html()
