r"""Generate per-PoC wipe-slider HTML snippets for inline embedding.

For each (slug, anchor) pair below we emit
`docs/_static/wipe_<slug>.html`. Each snippet is a self-contained
wipe-slider (CSS + markup + JS, all id-scoped to `<slug>`) that
sphinx pages embed via:

```
\`\`\`{raw} html
:file: ../_static/wipe_<slug>.html
\`\`\`
```

We exclude L5 (already the landing hero) and L7 (cmap-driven, palette
override irrelevant).
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "_static"

SNIPPETS = [
    ("l2_bar", "02_bar", "Grouped bar with value labels"),
    ("l3_scatter", "03_scatter", "Scatter with OLS fit"),
    ("l4_dual", "04_dual", "Dual-axis revenue / margin dashboard"),
    ("l6_stacked", "06_stacked", "Stacked area composition"),
    ("l8_violin", "08_distribution", "Distribution comparison (violin)"),
]

TEMPLATE = """<style>
  /* Wipe slider — {label} (id-scoped to #{wid}) */
  #{wid} {{
    position: relative;
    width: 100%;
    max-width: 720px;
    margin: 1.5em auto 1.6em;
    overflow: hidden;
    border-radius: 6px;
    border: 1px solid #e4e2dd;
    cursor: col-resize;
    user-select: none;
    -webkit-user-select: none;
    touch-action: none;
    background: #fbfaf7;
  }}
  html.dark #{wid},
  body[data-theme="dark"] #{wid} {{
    background: #14141d;
    border-color: #2a2a36;
  }}
  #{wid} img {{
    display: block;
    width: 100%;
    height: auto;
    pointer-events: none;
  }}
  #{wid} .wipe-overlay {{
    position: absolute;
    inset: 0;
    overflow: hidden;
  }}
  #{wid} .wipe-overlay img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
  }}
  #{wid} .wipe-divider {{
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    background: #fff;
    box-shadow: 0 0 6px rgba(0, 0, 0, 0.35);
    z-index: 10;
    pointer-events: none;
  }}
  #{wid} .wipe-handle {{
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    z-index: 11;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }}
  #{wid} .wipe-handle svg {{
    width: 16px;
    height: 16px;
    fill: #555;
  }}
  #{wid} .wipe-tag {{
    position: absolute;
    bottom: 8px;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.7em;
    font-weight: 700;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    z-index: 5;
    pointer-events: none;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #fff;
  }}
  #{wid} .wipe-tag.before {{
    left: 8px;
    background: rgba(180, 65, 65, 0.85);
  }}
  #{wid} .wipe-tag.after {{
    right: 8px;
    background: rgba(13, 148, 136, 0.85);
  }}
</style>

<div id="{wid}">
  <!-- base layer = dartwork after -->
  <img id="{wid}-base" alt="dartwork-mpl — {label}" />
  <!-- overlay layer = vanilla before, clipped from the left -->
  <div class="wipe-overlay" id="{wid}-ov">
    <img id="{wid}-overimg" alt="vanilla matplotlib — {label}" />
  </div>
  <div class="wipe-divider" id="{wid}-div" style="left: 50%"></div>
  <div class="wipe-handle"  id="{wid}-handle" style="left: 50%">
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M8.5 5l-5 7 5 7V5zm7 0v14l5-7-5-7z"/>
    </svg>
  </div>
  <span class="wipe-tag before">vanilla</span>
  <span class="wipe-tag after">dartwork</span>
</div>

<script>
  (function () {{
    var here = window.location.pathname;
    var base = here.indexOf("/_static/") !== -1
      ? "landing_pocs/"
      : "_static/landing_pocs/";
    var slug = "{poc_slug}";
    document.getElementById("{wid}-base").src    = base + "poc_" + slug + "_after.svg";
    document.getElementById("{wid}-overimg").src = base + "poc_" + slug + "_before.svg";

    var slider  = document.getElementById("{wid}");
    var overlay = document.getElementById("{wid}-ov");
    var divider = document.getElementById("{wid}-div");
    var handle  = document.getElementById("{wid}-handle");
    overlay.style.clipPath = "inset(0 50% 0 0)";
    var dragging = false;

    function setPos(x) {{
      var r = slider.getBoundingClientRect();
      var pct = Math.max(0, Math.min(1, (x - r.left) / r.width));
      var rightPct = ((1 - pct) * 100).toFixed(2);
      overlay.style.clipPath = "inset(0 " + rightPct + "% 0 0)";
      divider.style.left = (pct * 100).toFixed(2) + "%";
      handle.style.left  = (pct * 100).toFixed(2) + "%";
    }}
    slider.addEventListener("pointerdown", function (e) {{
      dragging = true;
      try {{ slider.setPointerCapture(e.pointerId); }} catch (err) {{}}
      setPos(e.clientX);
    }});
    slider.addEventListener("pointermove", function (e) {{
      if (dragging) setPos(e.clientX);
    }});
    slider.addEventListener("pointerup",     function () {{ dragging = false; }});
    slider.addEventListener("pointercancel", function () {{ dragging = false; }});
  }})();
</script>
"""


def main():
    for name, poc_slug, label in SNIPPETS:
        wid = f"dm-wipe-{name}"
        html = TEMPLATE.format(wid=wid, poc_slug=poc_slug, label=label)
        path = OUT / f"wipe_{name}.html"
        path.write_text(html)
        print(f"  ✓ {path.name}")


if __name__ == "__main__":
    main()
