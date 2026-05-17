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
    """Render a sample plot with *preset* and return SVG as string.

    The example is intentionally richer than a plain line chart: it
    combines a measured trajectory, a forecast band (``fill_between``),
    an annotated threshold marker, and a three-element legend so that
    the differences between presets \u2014 font weight, spine treatment,
    tick style, palette \u2014 are obvious at a glance.
    """
    dm.style.use(preset)

    fig, ax = plt.subplots(
        figsize=dm.figsize(f"{FIG_WIDTH_CM}cm", f"{FIG_HEIGHT_CM}cm"), dpi=150
    )

    # Sample data: battery capacity retention over charge/discharge
    # cycles. This example exercises annotations + uncertainty band +
    # dual series, all of which surface preset-level styling
    # differences much more clearly than a plain line chart.
    cycles = np.arange(0, 1001, 50)
    rng = np.random.default_rng(7)
    measured = 100 * np.exp(-cycles / 2400.0) + rng.normal(0, 0.4, cycles.size)
    forecast = 100 * np.exp(-cycles / 2200.0)
    lower = forecast - 1.5
    upper = forecast + 1.5

    ax.fill_between(
        cycles,
        lower,
        upper,
        color="dc.nordic2",
        alpha=0.35,
        label="Forecast 95% CI",
    )
    ax.plot(
        cycles,
        forecast,
        color="dc.nordic3",
        linestyle="--",
        lw=dm.lw(1),
        label="Forecast",
    )
    ax.plot(
        cycles,
        measured,
        marker="o",
        markersize=3.5,
        color="dc.forest3",
        lw=dm.lw(1),
        label="Measured",
    )

    # Annotate the 80% end-of-life threshold \u2014 a common battery KPI.
    ax.axhline(80, color="dc.vivid3", lw=dm.lw(0.5), linestyle=":")
    ax.annotate(
        "80% EoL\nthreshold",
        xy=(940, 80),
        xytext=(720, 86),
        fontsize=dm.fs(-1),
        color="dc.vivid4",
        arrowprops={"arrowstyle": "->", "color": "dc.vivid3", "lw": 0.6},
    )

    ax.set_title(
        "Battery capacity retention vs. cycles",
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
    )
    ax.set_xlabel("Charge / discharge cycles", fontsize=dm.fs(0))
    ax.set_ylabel("Capacity retention (%)", fontsize=dm.fs(0))
    ax.set_ylim(74, 102)
    ax.legend(fontsize=dm.fs(-1), frameon=False, loc="lower left")

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
  /* ── Top status bar (preset name + index, replaces the old 7-button row) ── */
  .dm-pc-statusbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    gap: 16px;
  }}
  .dm-pc-current {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    min-width: 0;
  }}
  .dm-pc-name {{
    font-size: 18px;
    font-weight: 600;
    color: #1a1a1a;
    letter-spacing: -0.01em;
  }}
  .dm-pc-desc {{
    font-size: 13px;
    color: #777;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .dm-pc-counter {{
    font-size: 12px;
    color: #999;
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }}
  /* ── Main layout: chart top, params bottom ── */
  .dm-pc-body {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  /* ── Chart stage (fixed size + nav arrows) ── */
  .dm-pc-stage-wrap {{
    position: relative;
  }}
  .dm-pc-stage {{
    position: relative;
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    width: 100%;
    aspect-ratio: {aspect_ratio};
  }}
  .dm-pc-panel {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    opacity: 0;
    transition: opacity 0.45s ease;
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
  /* Prev/Next arrows */
  .dm-pc-arrow {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1px solid #d0d0d0;
    background: rgba(255, 255, 255, 0.92);
    color: #333;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    transition: all 0.15s ease;
    user-select: none;
    z-index: 2;
  }}
  .dm-pc-arrow:hover {{
    background: #fff;
    border-color: #888;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  }}
  .dm-pc-arrow-prev {{ left: 8px; }}
  .dm-pc-arrow-next {{ right: 8px; }}
  /* Dot indicators */
  .dm-pc-dots {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
  }}
  .dm-pc-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ccc;
    border: none;
    padding: 0;
    cursor: pointer;
    transition: all 0.2s ease;
  }}
  .dm-pc-dot:hover {{
    background: #999;
    transform: scale(1.15);
  }}
  .dm-pc-dot.active {{
    background: #333;
    width: 22px;
    border-radius: 4px;
  }}
  /* Autoplay progress bar */
  .dm-pc-progress {{
    height: 2px;
    background: #eee;
    margin-top: 8px;
    border-radius: 1px;
    overflow: hidden;
  }}
  .dm-pc-progress-bar {{
    height: 100%;
    background: #333;
    width: 0%;
    transition: width 0.1s linear;
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
    gap: 10px 48px;
  }}
  .dm-pc-param-item {{
    display: flex;
    justify-content: flex-start;
    align-items: baseline;
    border-bottom: 1px solid #eee;
    padding-bottom: 6px;
  }}
  .dm-pc-param-key {{
    flex: 0 0 130px;
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
    grid-column: 1 / -1;
    border-bottom: none;
    padding-top: 4px;
    align-items: center;
  }}
  .dm-pc-param-special .dm-pc-param-key {{
    flex: 0 0 auto;
    margin-right: 12px;
  }}
</style>

<div class="dm-pc-widget" id="dm-pc-widget" role="region" aria-label="Preset comparison carousel">
  <div class="dm-pc-statusbar">
    <div class="dm-pc-current">
      <span class="dm-pc-name" id="dm-pc-name"></span>
      <span class="dm-pc-desc" id="dm-pc-desc"></span>
    </div>
    <span class="dm-pc-counter" id="dm-pc-counter"></span>
  </div>
  <div class="dm-pc-body">
    <div class="dm-pc-stage-wrap">
      <button class="dm-pc-arrow dm-pc-arrow-prev" id="dm-pc-prev" aria-label="Previous preset">&#10094;</button>
      <div class="dm-pc-stage" id="dm-pc-stage">
{panels_html}
      </div>
      <button class="dm-pc-arrow dm-pc-arrow-next" id="dm-pc-next" aria-label="Next preset">&#10095;</button>
    </div>
    <div class="dm-pc-dots" id="dm-pc-dots">
{dots_html}
    </div>
    <div class="dm-pc-progress" aria-hidden="true"><div class="dm-pc-progress-bar" id="dm-pc-progress-bar"></div></div>
    <div class="dm-pc-params" id="dm-pc-params">
      <div class="dm-pc-params-grid" id="dm-pc-params-grid"></div>
    </div>
  </div>
</div>

<script>
(function() {{
  var presets = {presets_json};
  var meta = {meta_json};
  var params = {params_json};
  var AUTOPLAY_MS = 5000;     // 5s per slide
  var PROGRESS_TICK_MS = 50;

  document.addEventListener("DOMContentLoaded", function() {{
    var widget   = document.getElementById("dm-pc-widget");
    var panels   = document.querySelectorAll(".dm-pc-panel");
    var dots     = document.querySelectorAll(".dm-pc-dot");
    var prevBtn  = document.getElementById("dm-pc-prev");
    var nextBtn  = document.getElementById("dm-pc-next");
    var nameEl   = document.getElementById("dm-pc-name");
    var descEl   = document.getElementById("dm-pc-desc");
    var ctrEl    = document.getElementById("dm-pc-counter");
    var progress = document.getElementById("dm-pc-progress-bar");
    var pgrid    = document.getElementById("dm-pc-params-grid");

    var idx = 0;
    var autoplayTimer = null;
    var progressTimer = null;
    var paused = false;

    function activate(newIdx) {{
      idx = (newIdx + presets.length) % presets.length;
      var preset = presets[idx];

      panels.forEach(function(p, i) {{
        p.classList.toggle("active", i === idx);
      }});
      dots.forEach(function(d, i) {{
        d.classList.toggle("active", i === idx);
      }});

      nameEl.textContent = preset;
      descEl.textContent = meta[preset] ? "— " + meta[preset].desc : "";
      ctrEl.textContent = (idx + 1) + " / " + presets.length;

      if (params[preset]) {{
        var html = "";
        var p = params[preset];
        Object.keys(p).forEach(function(k) {{
          if (k === "spines" || k === "best_for") return;
          html += "<div class='dm-pc-param-item'><span class='dm-pc-param-key'>"
                  + k + "</span><span class='dm-pc-param-val'>" + p[k] + "</span></div>";
        }});
        if (p["spines"]) {{
          html += "<div class='dm-pc-param-item'><span class='dm-pc-param-key'>spines</span><span class='dm-pc-param-val'>"
                  + p["spines"] + "</span></div>";
        }}
        if (meta[preset]) {{
          html += "<div class='dm-pc-param-item dm-pc-param-special'><span class='dm-pc-param-key'>best for</span><span class='dm-pc-param-val'>"
                  + meta[preset].use + "</span></div>";
        }}
        pgrid.innerHTML = html;
      }}
    }}

    function next() {{ activate(idx + 1); }}
    function prev() {{ activate(idx - 1); }}

    function startAutoplay() {{
      stopAutoplay();
      var elapsed = 0;
      progress.style.width = "0%";
      progressTimer = setInterval(function() {{
        if (paused) return;
        elapsed += PROGRESS_TICK_MS;
        progress.style.width = Math.min(100, (elapsed / AUTOPLAY_MS) * 100) + "%";
        if (elapsed >= AUTOPLAY_MS) {{
          elapsed = 0;
          next();
          progress.style.width = "0%";
        }}
      }}, PROGRESS_TICK_MS);
    }}
    function stopAutoplay() {{
      if (progressTimer) {{ clearInterval(progressTimer); progressTimer = null; }}
      progress.style.width = "0%";
    }}

    prevBtn.addEventListener("click", function() {{ prev(); startAutoplay(); }});
    nextBtn.addEventListener("click", function() {{ next(); startAutoplay(); }});
    dots.forEach(function(d, i) {{
      d.addEventListener("click", function() {{ activate(i); startAutoplay(); }});
    }});

    // Pause on hover or keyboard focus — accessibility-friendly
    widget.addEventListener("mouseenter", function() {{ paused = true;  }});
    widget.addEventListener("mouseleave", function() {{ paused = false; }});
    widget.addEventListener("focusin",    function() {{ paused = true;  }});
    widget.addEventListener("focusout",   function() {{ paused = false; }});

    // Keyboard navigation
    widget.tabIndex = 0;
    widget.addEventListener("keydown", function(e) {{
      if (e.key === "ArrowLeft")  {{ prev(); startAutoplay(); }}
      if (e.key === "ArrowRight") {{ next(); startAutoplay(); }}
    }});

    // Respect reduced-motion users — no autoplay, manual only
    var reduceMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    activate(0);
    if (!reduceMotion) startAutoplay();
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

    # ── Build dot-indicator HTML ──
    dots_lines = [
        f'      <button class="dm-pc-dot" data-preset="{preset}" '
        f'aria-label="Show {preset} preset"></button>'
        for preset in PRESETS
    ]
    dots_html = "\n".join(dots_lines)

    # ── Build panels HTML ──
    panels_lines = []
    for preset in PRESETS:
        panels_lines.append(
            f'        <div class="dm-pc-panel" data-preset="{preset}">'
        )
        panels_lines.append(f"          {svgs[preset]}")
        panels_lines.append("        </div>")
    panels_html = "\n".join(panels_lines)

    # ── JSON data ──
    presets_json = json.dumps(PRESETS, ensure_ascii=False)
    meta_json = json.dumps(PRESET_META, ensure_ascii=False)
    params_json = json.dumps(all_params, ensure_ascii=False)

    # ── Assemble ──
    html = _HTML_TEMPLATE.format(
        dots_html=dots_html,
        panels_html=panels_html,
        presets_json=presets_json,
        meta_json=meta_json,
        params_json=params_json,
        aspect_ratio=aspect_ratio,
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"  ✓ preset_compare.html → {output_path}")
    return output_path


# ── Entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_preset_compare_html()
