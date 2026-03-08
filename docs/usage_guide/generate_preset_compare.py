"""Generate a self-contained preset comparison HTML widget.

Renders the same plot with every dartwork-mpl preset, inlines the SVGs,
and wraps them in a tabbed HTML viewer with CSS fade transitions.

    python docs/usage_guide/generate_preset_compare.py
"""

from __future__ import annotations

import io
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

import dartwork_mpl as dm

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

# Fixed figure size so all presets align perfectly
FIG_WIDTH_CM = 9.0
FIG_HEIGHT_CM = 6.0


# ── Plot function ──────────────────────────────────────────────────────


def _render_preset_svg(preset: str) -> str:
    """Render a sample plot with *preset* and return SVG as string."""
    dm.style.use(preset)

    fig, ax = plt.subplots(
        figsize=(dm.cm2in(FIG_WIDTH_CM), dm.cm2in(FIG_HEIGHT_CM)),
        dpi=150,
    )

    # Sample data: thermal conductivity vs temperature
    temp = np.array([200, 300, 400, 500, 600, 700, 800])
    sample_a = np.array([13, 42, 31, 71, 61, 85, 90])
    sample_b = np.array([5, 21, 27, 43, 44, 51, 68])

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
    ax.set_ylabel("Thermal Conductivity (W/m·K)", fontsize=dm.fs(0))
    ax.legend(
        fontsize=dm.fs(-1),
        frameon=False,
        loc="upper left",
    )

    dm.simple_layout(fig)

    # Render SVG to string
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


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
  .dm-pc-info {{
    font-size: 11px;
    color: #888;
    margin-bottom: 8px;
    min-height: 1.4em;
  }}
  .dm-pc-stage {{
    position: relative;
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    /* Fixed aspect ratio container */
    width: 100%;
  }}
  .dm-pc-panel {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }}
  .dm-pc-panel.active {{
    position: relative;
    opacity: 1;
    pointer-events: auto;
  }}
  .dm-pc-panel svg {{
    display: block;
    width: 100%;
    height: auto;
  }}
</style>

<div class="dm-pc-widget">
  <div class="dm-pc-tabs" id="dm-pc-tabs">
{tabs_html}
  </div>
  <div class="dm-pc-info" id="dm-pc-info"></div>
  <div class="dm-pc-stage" id="dm-pc-stage">
{panels_html}
  </div>
</div>

<script>
(function() {{
  var meta = {meta_json};
  document.addEventListener("DOMContentLoaded", function() {{
    var tabs = document.querySelectorAll(".dm-pc-tab");
    var panels = document.querySelectorAll(".dm-pc-panel");
    var info = document.getElementById("dm-pc-info");

    function activate(preset) {{
      tabs.forEach(function(t) {{
        t.classList.toggle("active", t.dataset.preset === preset);
      }});
      panels.forEach(function(p) {{
        p.classList.toggle("active", p.dataset.preset === preset);
      }});
      if (meta[preset]) {{
        info.textContent = meta[preset].use + " — " + meta[preset].desc;
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


def build_preset_compare_html(
    output_path: Path | None = None,
) -> Path:
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
        output_path = (
            Path(__file__).parent / "images" / "preset_compare.html"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Render all presets ──
    svgs: dict[str, str] = {}
    for preset in PRESETS:
        print(f"  rendering '{preset}' ...")
        raw_svg = _render_preset_svg(preset)
        svgs[preset] = _strip_xml_declaration(raw_svg)

    # ── Build tabs HTML ──
    tabs_lines = []
    for preset in PRESETS:
        tabs_lines.append(
            f'    <button class="dm-pc-tab" data-preset="{preset}">'
            f"{preset}</button>"
        )
    tabs_html = "\n".join(tabs_lines)

    # ── Build panels HTML ──
    panels_lines = []
    for preset in PRESETS:
        panels_lines.append(
            f'    <div class="dm-pc-panel" data-preset="{preset}">'
        )
        panels_lines.append(f"      {svgs[preset]}")
        panels_lines.append("    </div>")
    panels_html = "\n".join(panels_lines)

    # ── Meta JSON for info line ──
    import json

    meta_json = json.dumps(PRESET_META, ensure_ascii=False)

    # ── Assemble ──
    html = _HTML_TEMPLATE.format(
        tabs_html=tabs_html,
        panels_html=panels_html,
        meta_json=meta_json,
        default_preset=PRESETS[0],
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"  ✓ preset_compare.html → {output_path}")
    return output_path


# ── Entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_preset_compare_html()
