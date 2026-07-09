# Color Model B — D1 "docs IA" Implementation Plan

> Gate-driven plan (codex CLI worker, supervisor commits). Pinned structure
> is non-negotiable; prose quality within a page is the worker's judgment,
> matching each page's existing voice.

**Goal:** Restructure the Design System docs to the confirmed flat IA —
`Overview / Colors / Palettes / Colormaps / Color class / Fonts / Design
rationale` — with every fact living on exactly one page, zero legacy
widgets/POC cruft, and `Design rationale` reframed as the *system-wide*
evidence page with a Typography placeholder.

**Spec:** `docs/superpowers/specs/2026-07-09-color-model-b-design.md` §6 (D1 row, decisions resolved 2026-07-09).

## Global Constraints

- Branch `feat/color-docs-ia-2026-07-09` (off merged #440 main), worktree
  `dartwork-mpl-colorsys`, `.venv`. No commit/push by worker.
- The two interactive explorers' *fragments and builders are frozen* in this
  PR (already Model B-true) — only the prose around their `{raw}` includes
  moves.
- URL preservation NOT required (zero-user window) — file renames are
  allowed and internal links are swept instead.
- Docs build `-D plot_gallery=0`; sphinx-noise restore before commit-point.

## Pinned target structure

```
docs/design_system/index.md        → "Overview" (rewritten, 7 cards = toctree 1:1)
docs/color_system/colors.md        → "Colors"          (tokens; keeps filename)
docs/color_system/palettes.md      → "Palettes"        (git mv categorical-palettes.md)
docs/color_system/colormaps.md     → "Colormaps"       (keeps filename)
docs/color_system/color-class.md   → "Color class"     (git mv space.md)
docs/fonts/index.md                → "Fonts"           (untouched; D2)
docs/color_system/design-rationale.md → "Design rationale" (git mv design.md)
```

Sidebar toctree (design_system/index.md) exactly in that order with those
titles. Root `index.md` orphan-comment updated to the new filenames.

## Task 1: Overview page rewrite (`design_system/index.md`)

Replace the 4-card landing with:
1. A short lede: the one rule — *the name is a family, `n` picks the form.*
2. **The four entry points table** (this is the page's centerpiece):

| you want to | you write | catalog |
|---|---|---|
| color one thing | `color="dc.blue6"` | Colors |
| color N series | `dm.set_colors("vivid")` / `dm.colors("vivid", n=6)` | Palettes |
| color a field | `cmap="dc.aurora"` | Colormaps |
| build your own | `dm.color()`, `dm.oklch()`, `dm.cspace()` | Color class |

3. The five kinds × two forms model in 3–4 sentences (sequential /
   multi-hue / diverging / cyclic / qualitative; continuous + designed
   discrete; counts rendered truthfully: 56 families).
4. Seven `grid-item-card`s matching the toctree 1:1 (Overview itself
   excluded → 6 cards + the toctree; or 6 cards, worker's judgment, but
   card set ↔ toctree entries must correspond exactly).
5. Delete the "Why one nav entry for four catalogs?" section (stale).

## Task 2: File renames + link sweep

- `git mv docs/color_system/categorical-palettes.md docs/color_system/palettes.md`
- `git mv docs/color_system/space.md docs/color_system/color-class.md`
- `git mv docs/color_system/design.md docs/color_system/design-rationale.md`
- Sweep ALL references (12 files found outside _build/superpowers: docs
  pages, root index.md comment, tests, llms.txt, CLAUDE.md/AGENTS.md if
  present) to the new paths/titles. Grep gate below.

## Task 3: Page reframes (SSOT — each fact once)

- **Colors** (`colors.md`): tokens only. Retitle intro accordingly; heading
  "dartwork Color — families" (no "v5" anywhere); REMOVE the curated
  categorical summary section (its content lives on Palettes) and replace
  the band-aid note with one forward link sentence. Third-party sheets stay.
- **Palettes** (`palettes.md`): H1 "Palettes"; frame as *discrete forms:
  qualitative sets + cycles + diverging/sequential discrete via
  `dm.colors(name, n)`*; keep the explorer include + `dm.set_colors` /
  `dm.colors` snippets (already Model B); mention `octave` as the default
  cycle. Cross-note to Colors rewritten as one sentence.
- **Colormaps**: H1 unchanged; update "See also" links to new titles/paths;
  ensure the custom-colormaps pointer targets `color-class.md`.
- **Color class** (`color-class.md`): H1 "Color class"; intro reframed as
  the programmatic 4th entry point (engine); content otherwise intact.
- **Design rationale** (`design-rationale.md`): H1 "Design rationale";
  reframe the lede as *the design system's evidence page* (why the colors —
  and eventually the typography — are built and gated this way). Add a new
  short final section:

```markdown
## Typography rationale (placeholder)

The same principled treatment — selection criteria, registration rules,
measured gates, preset wiring — is planned for the font system. It lands
with the fonts overhaul; until then this section is intentionally a stub
so the page's scope (the whole design system, not just color) is explicit.
```

- Kill every remaining "This page is X / for Y see Z" note-box in the five
  color pages in favor of single-sentence contextual links.

## Task 4: Legacy widget + POC cruft deletion

- Delete pages: `docs/colormap_poc.md`, `docs/landing_pocs.md`,
  `docs/pocs_preview.md` (if present), `docs/internals/diagrams_poc.md`.
- Delete `docs/_static` cruft: every `*poc*.html`, `palette_picker.html`,
  `palette_showcase.html`, `_overhaul_review.html`, `evolution_widget.html`
  (~15 files), plus `docs/color_system/images/palette_explorer.html` if it
  exists as a generated orphan — UNLESS a surviving page still includes it
  (grep first; the goal is zero dangling includes AND zero dead files).
- `docs/usage_guide/colors.md`: remove the two dead widget includes
  (lines ~53, ~65) and their surrounding prose; replace with a short
  pointer to the Palettes explorer. (Full usage-guide rewrite is D3.)
- Remove any builder scripts that ONLY produced deleted widgets (e.g.
  `scripts/build_palette_demos.py` if its outputs are all gone — verify by
  output path before deleting).

## Task 5: Gates + report

- Toctree gate: `design_system/index.md` toctree == the pinned 7-entry
  structure (titles and order exact).
- Grep gates (0 hits in docs/ + src/ + tests/ + llms*.txt, excluding
  docs/superpowers + docs/_build + CHANGELOG + migration.md where historical
  mention is allowed):
  `categorical-palettes` · `color_system/space` · `color_system/design[^-]`
  · `Color system design` · `Color Space` (as a title) · `v5 famil` ·
  `palette_picker` · `palette_explorer` · `Categorical palettes` (as title)
- `Typography rationale` present in design-rationale.md.
- Full pytest green (docs count/snippet/asset-inventory tests re-pinned as
  needed); ruff clean; sphinx build exit 0 with **zero unknown-document /
  dangling-include warnings** for the touched pages; node-parse untouched
  explorer fragments still pass (they must be byte-identical).
- Report: file moves, every link re-pin (file: old → new), deleted file
  list, toctree final form, grep gate outputs, pytest/sphinx tails,
  `git status --porcelain` condensed.

## Self-review notes

- Spec D1 row fully covered: flat IA (T1/T2), system-wide rationale +
  fonts placeholder (T3), legacy widgets + POC files (T4), builder-rendered
  numbers already true since L1/L2 (gates re-verify).
- Deferred: usage_guide full rewrite, landing/llms polish (D3); fonts pages
  (D2); explorer/lib vivid-cutoff dedup (noted L2 follow-up).
