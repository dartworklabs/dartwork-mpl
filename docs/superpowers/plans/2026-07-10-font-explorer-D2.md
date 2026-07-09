# Fonts explorer overhaul (D2) — Implementation Plan

> Gate-driven plan (codex CLI worker, supervisor commits). Follows the
> categorical/colormap explorer conventions established in PRs #436/#438;
> where this plan is silent, mirror those two.

**Goal:** Replace the tab-based `fonts_picker` with a full **font explorer**
on the shared explorer framework — family rail, chart-context demo grid,
live Weight/Size controls, layout picker, replace-last selection, dark mode —
so a user can *see any bundled family working inside real chart situations*
before committing to it.

**Architecture:** One permanent builder
`docs/_static/scripts/build_font_explorer.py` →
`docs/_static/font_explorer.html` (HTML+JS fragment, zero `<style>`; all
widget CSS in the shared `#dm-cat-exp, #dm-cmap-exp, #dm-font-exp` layer of
`dartwork-design.css`). Font rendering rides the EXISTING webfont
infrastructure (`docs/_static/font-face.css`, `dm-<Family>-<Weight>` faces +
`docs/_static/fonts/*.ttf`) — demos are deterministic inline SVG/HTML whose
text nodes switch `font-family`/weight via CSS. No per-family raster assets.

**Spec:** `docs/superpowers/specs/2026-07-09-color-model-b-design.md` §6 (D2 row).

## Global Constraints

- Branch `feat/font-explorer-2026-07-10`, worktree `dartwork-mpl-colorsys`, `.venv`. Worker does not commit/push.
- Family/weight inventory derives from the PACKAGE SSOT (`dartwork_mpl.font.list_registered()` + font_manager entries), never hand-typed. The builder asserts the derived family count and bakes it.
- Existing `font-face.css` is the font source; if a bundled family/weight used by the explorer lacks a face rule, the builder FAILS loudly (report, don't silently skip).
- Keep `docs/fonts/_generated/*` showcases and `generate_html_specimens.py` (families.md still uses them). Only the picker is replaced.
- Fragment budget: `font_explorer.html` ≤ 350 KB.

## UI (parity with the two color explorers)

- **Rail** (left): one chip per matplotlib family name (~16), grouped
  `Sans` / `Mono` (+ `Korean` badge on Hangul-capable families). Chip shows
  the family name RENDERED IN ITS OWN FACE + a small weight-count badge.
  Single-select (a font explorer explores one family at a time); the active
  family drives all demo cards.
- **d-bar controls**: Demo picker chips + Layout `2×2 / 2×3 / 3×3`
  (default 3×3) — same markup/classes as the other explorers, CSS moved to
  the shared layer. Font-specific: **Weight** segmented control (only the
  weights that family actually bundles, from SSOT; default Regular/400) ·
  **Size** stepper (dm.fs offsets −2…+4, default 0) · **Italic** toggle
  (enabled only if the family bundles italics).
- **Selection behavior**: demo chips use the SAME replace-last capped-list
  logic as the other two explorers (shared JS shape, pinned by test).
- **Copy affordances**: clicking the stage header copies
  `plt.rcParams["font.family"] = "<Family>"`; a code chip under the grid
  shows and copies the full idiom:
  `dm.style.use("scientific")` + rcParams line + `fontsize=dm.fs(<n>)` /
  `fontweight=dm.fw(<w-offset>)` reflecting current controls.
- **Dark mode**: `html.dark` convention; demo cards use the card tokens.
- **Demo labels**: outline-text (variant C) exactly as the other explorers.

## Demo library (12; default 9 — worker may refine geometry, not scope)

1. **Title & axes** — chart frame with title, axis labels, tick labels.
2. **Tick numerals** — dense numeric axis; digits legibility/tabular feel.
3. **Value labels** — bar chart with on-bar value labels.
4. **Legend** — multi-series legend block inside a line-chart frame.
5. **Annotation** — callout text + leader line over a curve.
6. **Weights ladder** — every bundled weight of the family, one line each
   (this demo ignores the Weight control; it IS the weight sampler).
7. **Size ladder** — the same phrase at fs(−2)…fs(+4) with offset captions.
8. **Paragraph** — 3-4 line caption-length specimen (chart-caption context).
9. **Numerals & confusables** — `0O 1lI 3.1415 −+ ×` disambiguation row.
10. **Korean** — 한글 specimen (axis label + short phrase). Families without
    Hangul coverage show the fallback chain note instead of tofu (detect
    coverage from the font files at build time; never render tofu).
11. **Code / mono** — small code block (shines for the 4 mono families).
12. **Caps & tracking** — uppercase eyebrow label with letter-spacing.

All demos: full-bleed cards, deterministic geometry baked by the builder,
text nodes get `font-family: 'dm-<Family>-<Weight>', <fallback>` swapped by
JS. Colors use existing `--dm-*` tokens (and dc token hexes baked from the
package where a chart color is needed).

## Docs rewiring

- `docs/fonts/index.md`: replace the `fonts_picker.html` include with
  `font_explorer.html` + one intro paragraph; fix the stale counts by
  rendering them from the builder (families/file counts).
- Reconcile `fonts/index.md` (says 204/16) vs `fonts/families.md`
  (says 206/18) vs asset dir (207 files) — the builder computes the truth
  once and both pages state it consistently (families.md numbers updated in
  place; its long-form showcases stay).
- Delete `docs/_static/fonts_picker.html` + `scripts/build_fonts_picker.py`
  after the rewire (grep gate: zero remaining references).

## Tests (new `tests/test_font_explorer_taxonomy.py`, pinned like siblings)

- Fragment exists, zero `<style>` tags, single `<script>`, node-parses.
- Family chip count == SSOT-derived count (assert exact number the builder
  reports); Sans/Mono grouping matches the mono list.
- Weight segments per family ⊆ registered weights; every referenced
  `dm-<Family>-<Weight>` face exists in `font-face.css`.
- Demo library = the 12 ids; default-9 list pinned; replace-last logic
  string present and textually identical to the other two fragments' shared
  shape (same pin style as #438).
- Shared CSS layer: `#dm-font-exp` appears ONLY inside grouped selectors
  shared with the other explorers for the shared widgets (chips, demo grid,
  labels), plus its own block for font-specific controls.
- Fragment size gate ≤ 350 KB. Hangul-coverage matrix pinned (which
  families render demo 10).
- `test_docs_count_claims` / asset-inventory pins updated to the reconciled
  font numbers.

## Verify + report

Full pytest green · ruff clean · sphinx build exit 0 (`-D plot_gallery=0`) ·
node-parse · both color explorer fragments byte-identical (untouched) ·
grep gates (fonts_picker 0 refs) · fragment size + Hangul matrix + weight
inventory in the report · final `git status --porcelain`. No commit.
