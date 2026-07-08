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
        "pretendard",
        "Pretendard",
        "pretendard_showcase.html",
        "Korean & Latin workhorse · 9 weights",
    ),
    (
        "notosanscjk",
        "Noto Sans CJK KR",
        "notosanscjk_showcase.html",
        "Korean fallback · 1 weights",
    ),
    (
        "sourcesans3",
        "Source Sans 3",
        "sourcesans3_showcase.html",
        "Editorial body text · 7 weights",
    ),
    (
        "ibmplexsans",
        "IBM Plex Sans",
        "ibmplexsans_showcase.html",
        "Technical / corporate · 7 weights",
    ),
    (
        "ibmplexmono",
        "IBM Plex Mono",
        "ibmplexmono_showcase.html",
        "Monospace · code annotations · 7 weights",
    ),
    (
        "jetbrainsmono",
        "JetBrains Mono",
        "jetbrainsmono_showcase.html",
        "Monospace · high-legibility code · 8 weights",
    ),
    (
        "sourcecodepro",
        "Source Code Pro",
        "sourcecodepro_showcase.html",
        "Monospace · editorial code · 7 weights",
    ),
    (
        "robotomono",
        "Roboto Mono",
        "robotomono_showcase.html",
        "Monospace · Roboto companion · 5 weights",
    ),
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
    width: 100%;
    max-width: 100%;
    margin: 1.6em auto 2em;
    font-family: var(--dm-f-sys);
  }

  .dm-fp-tabs.dm-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: var(--dm-space-1);
    border-bottom: 1px solid var(--dm-border-faint);
    margin-bottom: 14px;
  }
  .dm-fp-tab.dm-tab {
    border: none;
    background: transparent;
    padding: 7px 12px;
    margin: 0 4px;
    font-size: var(--dm-type-label-size);
    color: var(--dm-text-muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.12s ease, border-color 0.12s ease;
  }
  .dm-fp-tab.dm-tab:hover { color: var(--dm-i-active-text); }
  .dm-fp-tab.dm-tab.is-active,
  .dm-fp-tab.dm-tab[aria-selected="true"] {
    color: var(--dm-i-active-text);
    border-bottom-color: var(--dm-i-active-line);
    font-weight: 600;
  }

  .dm-fp-stage {
    min-height: 200px;
    padding: 22px 22px 18px;
    border: 1px solid var(--dm-border-faint);
    border-radius: var(--dm-radius-5);
    background: var(--dm-bg-panel);
  }

  /* Showcase styles — match existing dm-font-showcase styling so the
     specimens look identical to the families page. */
  .dm-fp-stage h3 {
    margin: 0 0 4px;
    font-size: 1.4em;
    color: var(--dm-text-strong);
  }
  .dm-fp-stage .desc {
    margin: 0 0 14px;
    color: var(--dm-text-muted);
    font-size: 0.86em;
  }
  .dm-fp-stage .dm-showcase-hero {
    font-size: 2.4em;
    line-height: 1.1;
    color: var(--dm-text-strong);
    margin: 6px 0 18px;
    letter-spacing: 0;
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
    color: var(--dm-text-muted);
    text-align: right;
  }
  .dm-fp-stage .dm-showcase-num {
    font-family: var(--dm-f-mono);
    font-size: 0.78em;
    color: var(--dm-text-faint);
  }
  .dm-fp-stage .dm-showcase-sample,
  .dm-fp-stage .sample {
    font-size: 1.05em;
    color: var(--dm-text);
  }
  .dm-fp-stage .expr {
    font-size: 1.2em;
    color: var(--dm-text);
  }

  .dm-fp-meta {
    margin-top: 12px;
    font-size: var(--dm-type-caption-size);
    color: var(--dm-text-muted);
    font-family: var(--dm-f-mono);
  }
  .dm-fp-meta code {
    background: var(--dm-i-code-surface, #f0f0f3);
    color: var(--dm-i-active-text, #008573);
    padding: 1px 6px;
    border-radius: var(--dm-radius-2);
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
        var selected = b.dataset.id === id;
        b.classList.toggle("is-active", selected);
        b.setAttribute("aria-selected", selected ? "true" : "false");
        b.tabIndex = selected ? 0 : -1;
      });
      var m = meta_by_id[id] || {};
      metaHost.innerHTML = 'Family: <code>' + (m.label || id) + '</code> · '
        + (m.note || '');
    }

    Array.prototype.forEach.call(
      document.querySelectorAll(".dm-fp-tab"),
      function (b) {
        b.addEventListener("click", function () { activate(b.dataset.id); });
        b.addEventListener("keydown", function (ev) {
          var tabs = Array.prototype.slice.call(tabsHost.querySelectorAll(".dm-fp-tab"));
          var pos = tabs.indexOf(b);
          if (ev.key === "ArrowRight") { ev.preventDefault(); tabs[(pos + 1) % tabs.length].click(); tabs[(pos + 1) % tabs.length].focus(); }
          if (ev.key === "ArrowLeft") { ev.preventDefault(); tabs[(pos - 1 + tabs.length) % tabs.length].click(); tabs[(pos - 1 + tabs.length) % tabs.length].focus(); }
          if (ev.key === "Home") { ev.preventDefault(); tabs[0].click(); tabs[0].focus(); }
          if (ev.key === "End") { ev.preventDefault(); tabs[tabs.length - 1].click(); tabs[tabs.length - 1].focus(); }
        });
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
    for idx, (fam_id, label, _spec, _note) in enumerate(FAMILIES):
        selected = idx == 0
        tab_buttons.append(
            f'    <button class="dm-fp-tab dm-tab{" is-active" if selected else ""}" '
            f'role="tab" aria-selected="{str(selected).lower()}" '
            f'tabindex="{0 if selected else -1}" type="button" '
            f'data-id="{fam_id}">{label}</button>'
        )
    parts.append(
        '<div class="dm-fp">\n'
        '  <div class="dm-fp-tabs dm-tabs" id="dm-fp-tabs" '
        'role="tablist" aria-label="Font family">\n'
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
