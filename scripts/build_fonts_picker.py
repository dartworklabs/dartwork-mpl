"""Build self-contained fonts picker HTML for embedding via :file:.

Reads each `docs/fonts/_generated/*_showcase.html` (or fallback
`*.html`) and inlines them as hidden <template> elements inside
docs/_static/fonts_picker.html. The picker JS then clones the
template whose data-family matches the active tab — no network
fetch, no path-resolution gymnastics, no dependency on whether
sphinx copies `_generated/` into the build output.

Run after editing the families list:

    uv run python3 scripts/build_fonts_picker.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "fonts" / "_generated"
OUT = ROOT / "docs" / "_static" / "fonts_picker.html"

# Catalog of bundled families. Order = order in the tabs. `spec` is
# the filename under docs/fonts/_generated/. `note` shows under
# the stage when this family is active.
FAMILIES = [
    (
        "roboto",
        "Roboto",
        "roboto_showcase.html",
        "Default body font · 4 weights",
    ),
    ("inter", "Inter", "inter_showcase.html", "UI / dashboards · 20 weights"),
    (
        "interdisplay",
        "InterDisplay",
        "interdisplay_showcase.html",
        "Headings / titles · 20 weights",
    ),
    (
        "notosans",
        "Noto Sans",
        "notosans_showcase.html",
        "Multi-language · broadest Unicode coverage",
    ),
    (
        "notosans_cond",
        "Noto Sans Condensed",
        "notosans_condensed_showcase.html",
        "Dense tables / legends",
    ),
    (
        "notosans_semi",
        "Noto Sans SemiCondensed",
        "notosans_semicondensed_showcase.html",
        "Mid-density text",
    ),
    (
        "paperlogy",
        "Paperlogy",
        "paperlogy_showcase.html",
        "Korean (한글) · 9 weights",
    ),
    ("math", "Noto Sans Math", "notosansmath.html", "Math symbols · ∑ ∫ √ ∞ π"),
    (
        "multilang",
        "Multi-language",
        "multilang.html",
        "Roboto + CJK + Math combo",
    ),
]


CSS = """
<style>
  /* Reusable font specimen picker — self-contained: every specimen
     is inlined as a <template> below, so the picker works regardless
     of how Sphinx copies the _generated/ directory. */

  .dm-fp {
    max-width: 720px;
    margin: 1.6em auto 2em;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  .dm-fp-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    border-bottom: 1px solid #e7e4dd;
    margin-bottom: 14px;
  }
  html.dark .dm-fp-tabs,
  body[data-theme="dark"] .dm-fp-tabs {
    border-bottom-color: #2c2c38;
  }
  .dm-fp-tab {
    border: none;
    background: transparent;
    padding: 7px 12px;
    margin: 0 4px;
    font-size: 0.84em;
    color: #777;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.12s ease, border-color 0.12s ease;
  }
  html.dark .dm-fp-tab,
  body[data-theme="dark"] .dm-fp-tab {
    color: #aaa;
  }
  .dm-fp-tab:hover { color: #0d9488; }
  .dm-fp-tab.active {
    color: #0d9488;
    border-bottom-color: #0d9488;
    font-weight: 600;
  }

  .dm-fp-stage {
    min-height: 200px;
    padding: 22px 22px 18px;
    border: 1px solid #ebe9e2;
    border-radius: 10px;
    background: #fbfaf7;
  }
  html.dark .dm-fp-stage,
  body[data-theme="dark"] .dm-fp-stage {
    background: rgba(255, 255, 255, 0.02);
    border-color: #2a2a3e;
  }

  /* Showcase styles — match existing dm-font-showcase styling so the
     specimens look identical to the families page. */
  .dm-fp-stage h3 {
    margin: 0 0 4px;
    font-size: 1.4em;
    color: #1a1a1a;
  }
  html.dark .dm-fp-stage h3,
  body[data-theme="dark"] .dm-fp-stage h3 {
    color: #f0f0f0;
  }
  .dm-fp-stage .desc {
    margin: 0 0 14px;
    color: #777;
    font-size: 0.86em;
  }
  html.dark .dm-fp-stage .desc,
  body[data-theme="dark"] .dm-fp-stage .desc {
    color: #aaa;
  }
  .dm-fp-stage .dm-showcase-hero {
    font-size: 2.4em;
    line-height: 1.1;
    color: #222;
    margin: 6px 0 18px;
    letter-spacing: -0.01em;
  }
  html.dark .dm-fp-stage .dm-showcase-hero,
  body[data-theme="dark"] .dm-fp-stage .dm-showcase-hero {
    color: #f0f0f0;
  }
  .dm-fp-stage .dm-showcase-grid {
    display: grid;
    grid-template-columns: 90px 50px 1fr;
    column-gap: 16px;
    row-gap: 8px;
    align-items: baseline;
  }
  .dm-fp-stage .dm-font-grid,
  .dm-fp-stage .dm-math-grid {
    display: grid;
    grid-template-columns: 100px 1fr;
    column-gap: 16px;
    row-gap: 10px;
    align-items: baseline;
  }
  .dm-fp-stage .dm-showcase-row {
    display: contents;
  }
  .dm-fp-stage .dm-showcase-weight,
  .dm-fp-stage .label {
    font-size: 0.82em;
    color: #888;
    text-align: right;
  }
  .dm-fp-stage .dm-showcase-num {
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.78em;
    color: #999;
  }
  .dm-fp-stage .dm-showcase-sample,
  .dm-fp-stage .sample {
    font-size: 1.05em;
    color: #2a2a2a;
  }
  html.dark .dm-fp-stage .dm-showcase-sample,
  html.dark .dm-fp-stage .sample,
  body[data-theme="dark"] .dm-fp-stage .dm-showcase-sample,
  body[data-theme="dark"] .dm-fp-stage .sample {
    color: #e0e0e0;
  }
  .dm-fp-stage .expr {
    font-size: 1.2em;
    color: #2a2a2a;
  }
  html.dark .dm-fp-stage .expr,
  body[data-theme="dark"] .dm-fp-stage .expr {
    color: #e0e0e0;
  }

  .dm-fp-meta {
    margin-top: 12px;
    font-size: 0.8em;
    color: #888;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
  }
  html.dark .dm-fp-meta,
  body[data-theme="dark"] .dm-fp-meta {
    color: #999;
  }
  .dm-fp-meta code {
    background: rgba(13, 148, 136, 0.1);
    color: #0d9488;
    padding: 1px 6px;
    border-radius: 3px;
  }
</style>
""".strip()


JS = """
<script>
  (function () {
    var meta_by_id = {
%META_MAP%
    };

    var tabsHost = document.getElementById("dm-fp-tabs");
    var stage    = document.getElementById("dm-fp-stage");
    var metaHost = document.getElementById("dm-fp-meta");

    function activate(id) {
      var t = document.querySelector('template[data-family="' + id + '"]');
      if (!t) return;
      stage.innerHTML = "";
      stage.appendChild(t.content.cloneNode(true));
      tabsHost.querySelectorAll(".dm-fp-tab").forEach(function (b) {
        b.classList.toggle("active", b.dataset.id === id);
      });
      var m = meta_by_id[id] || {};
      metaHost.innerHTML = 'Family: <code>' + (m.label || id) + '</code> · '
        + (m.note || '');
    }

    Array.prototype.forEach.call(
      document.querySelectorAll(".dm-fp-tab"),
      function (b) {
        b.addEventListener("click", function () { activate(b.dataset.id); });
      }
    );

    // Initial render = first tab
    var first = document.querySelector(".dm-fp-tab");
    if (first) activate(first.dataset.id);
  })();
</script>
""".strip()


def main() -> None:
    parts: list[str] = [CSS]

    # Tabs
    tab_buttons = []
    for fam_id, label, _spec, _note in FAMILIES:
        tab_buttons.append(
            f'    <button class="dm-fp-tab" data-id="{fam_id}">{label}</button>'
        )
    parts.append(
        '<div class="dm-fp">\n'
        '  <div class="dm-fp-tabs" id="dm-fp-tabs">\n'
        + "\n".join(tab_buttons)
        + "\n  </div>\n"
        '  <div class="dm-fp-stage" id="dm-fp-stage"></div>\n'
        '  <p class="dm-fp-meta" id="dm-fp-meta"></p>\n'
        "</div>"
    )

    # Inline templates — one per family, each holding its specimen markup.
    missing = []
    for fam_id, _label, spec, _note in FAMILIES:
        src_path = SRC / spec
        if not src_path.exists():
            missing.append(str(src_path))
            continue
        html = src_path.read_text()
        parts.append(f'<template data-family="{fam_id}">\n{html}\n</template>')

    if missing:
        raise SystemExit(
            "Missing specimen sources (run docs/fonts/generate_html_specimens.py "
            "first):\n  - " + "\n  - ".join(missing)
        )

    # JS with embedded meta map
    meta_entries = []
    for fam_id, label, _spec, note in FAMILIES:
        # JS string escaping — labels/notes are ASCII-safe here, but
        # escape backslash + double-quote defensively.
        esc_label = label.replace("\\", "\\\\").replace('"', '\\"')
        esc_note = note.replace("\\", "\\\\").replace('"', '\\"')
        meta_entries.append(
            f'      "{fam_id}": {{ "label": "{esc_label}", "note": "{esc_note}" }}'
        )
    js_with_meta = JS.replace("%META_MAP%", ",\n".join(meta_entries))
    parts.append(js_with_meta)

    OUT.write_text("\n\n".join(parts) + "\n")
    print(f"Wrote {OUT}")
    print(f"Inlined {len(FAMILIES)} family specimens.")


if __name__ == "__main__":
    main()
