# Fonts browser — copy, convenience & page-refactor plan (advisory)

> **For agentic workers:** implement tasks in order on branch
> `feat/fonts-browser-ux-2026-07-10`. Commit each task atomically. The
> generator (`docs/_static/scripts/build_fonts_browser_data.py`) owns only the
> `DM_FONT_DATA:BEGIN/END` block inside `docs/_static/fonts_browser.frag.html`;
> everything outside it is hand-owned and safe to edit, but after ANY generator
> change you must regenerate and keep `--check` green (exit 0) and idempotent.

**Goal:** polish the merged interactive font browser (`/fonts/`, PR #450) in
three axes the user asked for — (1) microcopy, (2) convenience features,
(3) page structure — and produce **two POC interaction variants (A/B)**
embedded in the real docs for the user to choose from.

**Diagnosis summary (verified against the working tree):**
- Copy: page intro is insider-speak ("measured registry"); browser intro
  enumerates facets instead of selling actions; the mpl-name chip gives no
  visual hint that it copies; facet values read oddly (`<9`, "Has italics");
  group names (Workhorse/Display/…) are unexplained; snippet doesn't explain
  why the chain has 3 names.
- Convenience: no type-your-own preview; no size control tied to chart roles;
  no `/` shortcut to search; drawer can't step between families; weight-ladder
  rows aren't copyable; tabular-numeral capability is measured by the registry
  but never demonstrated; card role (Body/Display/…) not surfaced.
- Data gaps (generator): `role` emitted for only 11/18 families; `tnum` not
  emitted at all.
- Page structure: registry accounting (220/20/18 + width caveat) sits ABOVE
  the browser; Roles table disconnected from the browser; flow should be
  orient → explore → reference.

---

## Global constraints

- Branch: `feat/fonts-browser-ux-2026-07-10` (already created from origin/main).
- After every task: `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check`
  must exit 0, and `uv run pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py -q`
  must show no failures beyond the 2 pre-existing environmental mathtext
  `KeyError: 300` failures.
- Fragment rules stay in force: all CSS scoped under the root id, no page-theme
  mutation, no external `<script src=`, only `var(--dm-*)` colors (`#fff`/`#000`
  allowed), real `<button>`s, `:focus-visible` rings, `prefers-reduced-motion`
  guard, responsive under 820px.
- All prose in English (docs language). Use the exact copy strings below.

---

## Task 1 — generator: emit `role` for all 18 + `tnum`

**File:** `docs/_static/scripts/build_fonts_browser_data.py`

1. Emit a `role` string for every family, derived from the registry
   (`dartwork_mpl.font.FONTS` roles). Canonical values + display labels:

   | role value | badge label |
   | --- | --- |
   | `body` | `Body` |
   | `display` | `Display` |
   | `serif` | `Serif` |
   | `mono` | `Mono` |
   | `korean_body` (or the registry's Korean-role value) | `Korean body` |
   | `korean_mono` | `Korean mono` |
   | `symbols` / `math` / fallback-tail roles | `Symbols` |

   If the registry names differ, map faithfully from what
   `dartwork_mpl.font` exposes — do NOT invent roles; read the registry. Every
   one of the 18 families must end with a non-empty role.
2. Emit `tnum: true/false` per family from the registry's measured
   tabular-numerals flag (font.py `_measure()` measures it; expose it through
   whatever accessor exists — read font.py to find the field name).
3. Regenerate the fragment; `--check` green; run twice → byte-identical.
4. Extend `tests/test_fonts_browser_consistency.py` minimally: every family in
   the emitted data has a non-empty `role`, and `tnum` is a bool present on
   all families, and both equal the registry values.

Commit: `feat(docs): emit role + tnum for every family in fonts browser data`

## Task 2 — shared-core copy & convenience (edits to `fonts_browser.frag.html`)

These are unambiguous improvements applied to the REAL fragment (they ship with
whichever variant wins). Root id stays `dm-fontfacets`.

**2a. Microcopy (exact strings):**
- Search placeholder: `Search families — name, feel, or use case…`
- Facet relabels (values only, logic unchanged):
  - Italic: `Has italics` → `Italics available`; `No italics` → `Upright only`
  - Weights: `9+ weights` → `Deep (9+ weights)`; `<9` → `Compact (under 9)`
- Group chips get `title` tooltips:
  - Workhorse: `Everyday body faces — the safe defaults`
  - Display: `Large titles and poster-scale numbers`
  - Technical: `Interface and engineering voice`
  - Multilingual: `Broad script coverage in one family`
  - Serif: `Opt-in serif voice for journals and reports`
  - Korean & CJK: `Hangul-first and CJK coverage`
  - Monospace: `Fixed-width for code and aligned figures`
  - Symbols & Math: `Fallback tail — operators, arrows, symbols`
- Empty state: keep the kaomoji; body text →
  `Nothing matches that combination. Loosen a filter or clear the search.`
- Toast for mpl-name copy: `<b>{mpl}</b> copied — paste into font.family`
- Toast for snippet copy: `rcParams snippet copied`

**2b. Copy affordances:**
- mpl-name chip: add a small inline copy icon (SVG, `currentColor`) after the
  name + hover style (accent tint) so copyability is visible;
  `aria-label="Copy matplotlib family name"`.
- New per-card quick action: a small `Copy chain` ghost button next to the mpl
  chip that copies `plt.rcParams["font.family"] = <JSON chain>` directly (no
  drawer trip). Toast: `font.family chain copied`.
- Weight-ladder rows in the drawer become copy buttons: click copies
  `fontweight=<num>`; hover shows a subtle copy hint; toast
  `fontweight=<num> copied`.

**2c. Card content:**
- Add a role badge (from Task 1 `role`, labels per the table above) as the
  FIRST badge on each card. Roboto additionally shows `Default` (it is the
  preset default body face) — hardcode by `key === "roboto"` or a data flag if
  cleaner.
- If `tnum` is true, drawer's "Numerals & symbols" section appends a
  tabular-numeral proof line: two stacked rows `1,111,111.11` / `8,888,888.88`
  rendered in the regular face with a caption `Tabular numerals — digits align
  in columns.` If false, no line (do not fake it).

**2d. Keyboard & interaction polish:**
- `/` focuses the search input (unless typing in an input); `Escape` in the
  search clears it; document-level Escape still closes the drawer first if open.
- Drawer: add `‹ Prev` / `Next ›` buttons in the header + ArrowLeft/ArrowRight
  while the drawer is open — steps through the CURRENTLY VISIBLE (filtered)
  families in grid order, wrapping at the ends.
- Snippet gains one comment line above the rcParams assignment:
  `# ordered fallback: family → Latin fallback → math/symbols` (only when the
  chain has >1 entry; single-entry chains get no comment).

**2e. Fragment intro (in `docs/fonts/index.md`, see Task 3):** the `## Font
browser` lead paragraph becomes:

> Type your own preview text, narrow by script or style, and open any family
> for its weight ladder and a ready-to-paste `rcParams` snippet. Every sample
> is drawn by the family's own bundled file — what you see here is exactly
> what your chart will render.

Commit: `feat(docs): fonts browser shared-core copy + convenience polish`

## Task 3 — page refactor (`docs/fonts/index.md`)

New section order (keep all existing content, move/retitle):
1. H1 + 2-line orientation (replace current intro):
   > dartwork-mpl ships **18 publication-ready font families**, registered
   > with matplotlib the moment you `import dartwork_mpl`. Browse them below,
   > preview your own text, and copy a ready-to-paste `font.family` setup.
2. `## Font browser` (moved UP; new intro per Task 2e).
3. `## How registration works` (retitled from `## Overview`; same prose,
   tightened lead: start directly with "dartwork-mpl bundles **220 text font
   files**…").
4. `## Quick Start` (unchanged).
5. `## Roles` — add one lead-in line above the table:
   `The browser's role badges follow this table; use it as the print-friendly summary.`
6. `## Typography Matrix`, `## Full Specimens` (unchanged).

Commit: `refactor(docs): fonts page flow — orient, explore, then reference`

## Task 4 — variant A: "Preview workbench" (POC fragment)

**File:** `docs/_static/pocs/fonts_ux_a.frag.html` (new dir ok), root id
`dm-fbuxa`. Start from the Task-2 fragment (copy file, re-scope every
`#dm-fontfacets` → `#dm-fbuxa`, keep the inlined data block as-is — it is a
static copy for preview only, exempt from `--check`).

Add a slim PREVIEW TOOLBAR pinned above the results grid:
- Text input, label `Preview`, placeholder `Type to preview in every family…` —
  live re-renders every card's sample line (and the drawer hero + compare
  contexts) with the typed text; when empty, each family reverts to its own
  per-script default sample. Debounce ~120ms.
- Size segmented control labeled `Render at:` with three options mapped to
  chart roles: `Tick 9px` / `Label 13px` / `Title 22px` (default Label). Sets
  the card sample font-size (and drawer hero size) so users audition type at
  the sizes charts actually use.
- A thin caption under the toolbar: `Sizes mirror chart roles — ticks, axis
  labels, and titles.`

Commit: `feat(docs): POC A — preview workbench for the fonts browser`

## Task 5 — variant B: "Pin & compare" (POC fragment)

**File:** `docs/_static/pocs/fonts_ux_b.frag.html`, root id `dm-fbuxb`. Same
starting point as Task 4 (includes the preview TEXT input from A's toolbar —
shared core for a fair comparison — but NOT the size segmented control, and no
drawer prev/next beyond what Task 2 shipped).

Add PIN-TO-COMPARE:
- Each card gets a pin toggle (top-right, `☆/★`, `aria-pressed`), max 3 pins;
  attempting a 4th shows toast `Unpin one first — compare holds three.`
- A sticky COMPARE TRAY docks to the bottom of the fragment when ≥1 pin:
  each pinned family renders name + the current preview text (or its default
  sample) at one uniform size + its chain, with per-pin `Copy chain` and unpin
  buttons. Tray survives filtering (pinned families stay in the tray even when
  filtered out of the grid). `Clear pins` link.
- Caption in the tray header: `Finalists — same text, same size, side by side.`

Commit: `feat(docs): POC B — pin & compare tray for the fonts browser`

## Task 6 — POC comparison page

**File:** `docs/pocs_fonts_ux.md` (orphan). Korean banners (the reviewer is
Korean; page chrome only — the widgets stay English). Structure:

```markdown
---
orphan: true
---

# Fonts browser — UX 개선 A/B

공통 개선(문구·복사 편의·키보드·role 배지·tnum 증명·drawer 이동)은 이미
`/fonts/`에 적용되어 있습니다. 아래 두 변형은 그 위에 얹는 상호작용 방향입니다.

## A — Preview workbench (내 문장 + 차트 롤 크기)
[banner div: 시그니처 = 타이핑한 문장을 tick/label/title 실측 크기로 전 패밀리 오디션]
{raw include of _static/pocs/fonts_ux_a.frag.html}

## B — Pin & compare (후보 고정 + 나란히 비교)
[banner div: 시그니처 = 최대 3개 패밀리를 고정해 같은 문장·같은 크기로 비교]
{raw include of _static/pocs/fonts_ux_b.frag.html}
```

Use the same `.poc-banner`-style inline CSS as earlier preview pages (accent-2
background, accent-6 border, radius 14px).

Commit: `docs: A/B preview page for fonts browser UX variants`

## Task 7 — verification (report results verbatim)

1. `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check` → exit 0; run twice → byte-identical fragment.
2. `uv run pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py -q` → only the 2 pre-existing mathtext failures.
3. `PLOT_GALLERY=0 uv run python3 -m sphinx -b html -d docs/_build/doctrees docs docs/_build/html` → build succeeded; `docs/_build/html/fonts/index.html` contains `dm-fontfacets`; `docs/_build/html/pocs_fonts_ux.html` contains BOTH `dm-fbuxa` and `dm-fbuxb`.
4. Fragment hygiene greps on BOTH new POC files (shell tags 0, css links 0, theme mutation 0, script src 0).
5. No visual serve-check (dispatcher does it).

## Risks / notes

- The two POC fragments triple ~1700-line files; keep them as verbatim copies
  + deltas, do not "improve" unrelated parts, or the A/B comparison stops being
  controlled.
- The preview-text feature must not persist typed text into the drawer snippet
  (snippet stays code-only).
- Winner integration (post-decision) will fold the chosen variant into
  `fonts_browser.frag.html` and delete `docs/_static/pocs/` + the preview page —
  NOT part of this plan.
