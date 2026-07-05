#!/usr/bin/env python3
"""Build the v5 categorical-family explorer fragment.

The fragment is embedded by ``docs/color_system/categorical-palettes.md`` via
MyST ``{raw} html :file:``. It is intentionally static: the v5 source of truth
is ``src/dartwork_mpl/colors/_generated.py``.
"""

from __future__ import annotations

import html
import runpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "categorical_explorer.html"
GENERATED = ROOT / "src" / "dartwork_mpl" / "colors" / "_generated.py"

ORDER = [
    "amber",
    "blue",
    "cyan",
    "gray",
    "green",
    "indigo",
    "lime",
    "orange",
    "pink",
    "purple",
    "red",
    "rose",
    "sky",
    "teal",
    "violet",
    "yellow",
]

INTENT = {
    "amber": "warm thresholds and contextual bands",
    "blue": "primary analytical series",
    "cyan": "cool secondary series and dense marks",
    "gray": "reference, grid, and secondary context",
    "green": "positive states and growth",
    "indigo": "cool comparison series",
    "lime": "fresh/biological ordered data",
    "orange": "warm emphasis and warnings",
    "pink": "soft editorial accents",
    "purple": "qualitative accent groups",
    "red": "negative states and alerts",
    "rose": "warm editorial highlights",
    "sky": "light cool data and backgrounds",
    "teal": "house analytical color and ordered ramps",
    "violet": "premium/editorial qualitative groups",
    "yellow": "high-key warm highlights",
}


def _text_color(hex_color: str) -> str:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#fff" if lum < 0.48 else "#1f2933"


def main() -> None:
    palette: dict[str, tuple[str, ...]] = runpy.run_path(str(GENERATED))[
        "PALETTE"
    ]
    cards: list[str] = []
    for family in ORDER:
        swatches = []
        for i, hex_color in enumerate(palette[family]):
            token = f"dc.{family}{i}"
            swatches.append(
                '<button class="dm-v5-sw" '
                f'style="--c:{hex_color};--tc:{_text_color(hex_color)}" '
                f'data-token="{html.escape(token)}" '
                f'title="{html.escape(token)}">'
                f"<span>{i}</span></button>"
            )
        cards.append(
            '<article class="dm-v5-card">'
            f"<h3>dc.{html.escape(family)}</h3>"
            f"<p>{html.escape(INTENT[family])}</p>"
            '<div class="dm-v5-row">' + "\n".join(swatches) + "</div></article>"
        )

    OUT.write_text(
        """<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_categorical_explorer.py
     Regenerate: python3 docs/_static/scripts/build_categorical_explorer.py -->
<div class="dm-v5-explorer">
  <style>
    .dm-v5-explorer{container-type:inline-size}
    .dm-v5-head{display:flex;justify-content:space-between;gap:16px;align-items:end;margin:0 0 18px}
    .dm-v5-head h2{margin:0;font-size:1.05rem}
    .dm-v5-head p{margin:.25rem 0 0;color:var(--dm-text-muted,#667085);font-size:.9rem}
    .dm-v5-count{font:600 .8rem ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dm-text-muted,#667085);white-space:nowrap}
    .dm-v5-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    .dm-v5-card{border:1px solid var(--dm-border-faint,#e5e7eb);border-radius:8px;padding:12px;background:var(--dm-bg-page,#fff)}
    .dm-v5-card h3{margin:0;font:700 .9rem ui-monospace,SFMono-Regular,Menlo,monospace}
    .dm-v5-card p{margin:.25rem 0 .65rem;color:var(--dm-text-muted,#667085);font-size:.8rem;line-height:1.35}
    .dm-v5-row{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:3px}
    .dm-v5-sw{appearance:none;border:0;border-radius:5px;background:var(--c);color:var(--tc);min-height:38px;cursor:pointer}
    .dm-v5-sw span{font-weight:760;font-size:.75rem}
    .dm-v5-sw:hover{outline:2px solid var(--dm-gray-12,#1f2933);outline-offset:1px}
    @container (max-width: 760px){.dm-v5-grid{grid-template-columns:1fr}.dm-v5-head{display:block}.dm-v5-count{display:block;margin-top:6px}}
  </style>
  <div class="dm-v5-head">
    <div>
      <h2>v5 family palettes</h2>
      <p>Sixteen generated families, ten perceptually equalized steps each. Click a swatch to copy its token.</p>
    </div>
    <div class="dm-v5-count">16 families / 160 colors</div>
  </div>
  <div class="dm-v5-grid">
"""
        + "\n".join(cards)
        + """
  </div>
</div>
<script>
document.querySelectorAll('.dm-v5-sw').forEach((button) => {
  button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(button.dataset.token); } catch (_) {}
  });
});
</script>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
