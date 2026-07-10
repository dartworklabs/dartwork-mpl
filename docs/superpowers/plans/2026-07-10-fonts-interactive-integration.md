# Fonts page — interactive faceted browser, registry-backed integration

> **Status**: plan (advisory output, 2026-07-10). Worker executes literally.
> **Branch**: `feat/fonts-faceted-1col-design` (= current `origin/main` + 2 WIP
> commits that only ADD `docs/_static/poc_*.frag.html` + `docs/pocs_*.md`).
> **Decision (user-authorized)**: bring back the interactive **1-column faceted
> font browser** as the primary widget on `/fonts/` — overriding PR #449's
> "static page, no interactive widgets" call — while **preserving** #449's
> registry-truth concept, `font.py` fixes, and accurate corpus counts.
> **Read-only guardrails**: do NOT touch the color explorer fragments
> (`categorical_explorer.html`, `colormap_explorer.html` — SHA-pinned in
> `tests/test_colormap_explorer_taxonomy.py` / `test_palette_family_taxonomy.py`)
> and do NOT resurrect the 2-panel explorer or the realplots pipeline.

---

## 1. Findings (verified against the working tree, not doc claims)

### 1.1 Corpus ground truth (all verified by command)

| Fact | Value | How verified |
| --- | --- | --- |
| Bundled text font files | **220** (210 `.ttf` + 10 `.otf`) | `find src/dartwork_mpl/asset/font -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | wc -l` |
| Documented file groups (basename prefix before first `-`) | **20** | `Roboto, RobotoMono, Inter, InterDisplay, IBMPlexSans, IBMPlexMono, SourceSans3, SourceSerif4, SourceCodePro, JetBrainsMono, NotoSans, NotoSans_Condensed, NotoSans_SemiCondensed, NotoSansCJK, NotoSansMath, NotoSansSymbols, NotoSansSymbols2, Paperlogy, Pretendard, D2Coding` |
| Registered matplotlib family names | **18** | `python3 -c "from dartwork_mpl import font; print(len(font.list_registered()))"` — Noto Sans Condensed/SemiCondensed register as **"Noto Sans"** with width metadata (Noto Sans absorbs 54 files = 3 × 18) |
| License files | 13 in `src/dartwork_mpl/asset/font/licenses/` | covers all 20 groups (Inter covers Inter Display; NotoSans covers all Noto* except CJK which has its own; IBMPlex covers Sans+Mono) |
| Docs count claims | **already correct** (220/20/18 in `docs/fonts/index.md`, `families.md`, `utilities.md`) | grep — no count fixes needed, only a test to lock them (§5) |

### 1.2 Where registry truth lives

`src/dartwork_mpl/font.py` (post-#448/#449, current main):

- `FONTS: Mapping[str, FontFamily]` — **18 curated entries**, keys are the
  exact matplotlib family names. Order: Roboto, Inter, IBM Plex Sans,
  Source Sans 3, Noto Sans, Inter Display, Paperlogy, Pretendard,
  Noto Sans CJK KR, Source Serif 4, JetBrains Mono, IBM Plex Mono,
  Roboto Mono, Source Code Pro, D2Coding, Noto Sans Math,
  Noto Sans Symbols, Noto Sans Symbols 2.
- Each `FontFamily` has `role` (`body|display|kr-body|serif|mono|mono-kr|fallback-tail`),
  `job`, `alternates`, `quirks`, `weight_exceptions`, and **measured** lazy
  properties via `font._measure(name)`: `weights`, `italic`,
  `tnum_available`, `numeric_axes`, `mono` (fixed_pitch), `hangul`,
  `licenses`, `chart_glyphs`. Per-file facts in
  `FontMeasurement.files: tuple[FontFaceMeasurement, ...]`
  (`file, weight, italic, stretch, tnum_available, digit_widths_uniform,
  fixed_pitch, chart_glyphs, hangul, license`).
- `css_font_face_name(file) -> "dm-<stem>"` — the CSS `@font-face` naming rule.
- `list_registered()` — the 18 names; `_family_codepoints(family)` — cmap union
  (useful for sample-glyph honesty tests).
- `_promote_bundled_fonts()` — #449's registration fix (bundled entries win
  system-font ties). **Keep untouched.**

The `@font-face` substrate for browser rendering already exists and survived
#449: `docs/fonts/generate_html_specimens.py::build_html_specimens()` (called
from the `generate_gallery_assets` build hook in `docs/_ext/build_hooks.py`,
wired in `docs/conf.py`) copies **both** ttf+otf into `docs/_static/fonts/`
and writes `docs/_static/font-face.css` with one `dm-<stem>` face per file.
`font-face.css` is in `html_css_files` (conf.py) and is **gitignored**
(generated every build), as are `docs/_static/fonts/` and
`docs/fonts/_generated/`.

### 1.3 What PR #449 (merge `774c5ff6`, real commit `44689a01`) deleted/changed

Deleted (recoverable via `git show 44689a01~1:<path>`):

| Path | What it was |
| --- | --- |
| `docs/_static/fonts_explorer_data.js` (955 ln) | legacy data SSOT: `DM_FONT_DATA/ORDER/GROUPS`, **16 hand-curated families** (missing Source Serif 4, D2Coding, Noto Sans Symbols, Noto Sans Symbols 2; carried Condensed/SemiCondensed as fake separate families) |
| `docs/_static/scripts/build_fonts_explorer_data.py` (446 ln) | its generator — hand-baked `WEIGHT_SPEC` + editorial `META` (intent/application/pairing/personality copy — **worth reusing**) |
| `docs/_static/font_explorer.html` + `docs/_static/scripts/build_font_explorer.py` | the 2-panel registry-driven explorer (payload embedded in HTML) — **stays retired** |
| `docs/_static/scripts/build_font_realplots.py` (245 ln) | real-mpl PNG pipeline — **stays retired** |
| `tests/test_font_explorer_taxonomy.py` (363 ln) | 2-panel explorer parity + color-fragment SHA pins (pins moved elsewhere) |
| `tests/test_fonts_explorer_consistency.py` (146 ln) | legacy data parity: builder==committed byte-for-byte, every face token has a bundled file, unsurfaced-stem allowlist (fails loudly when a family is added) — **pattern to restore** |

Changed and **kept** (do not undo): `src/dartwork_mpl/font.py` registration
fixes + `numeric_axes` correction; `docs/_static/dartwork-design.css`
(`#dm-font-exp` selectors removed cleanly — grep confirms 0 leftovers);
`docs/fonts/index.md` static rewrite; `families.md`;
`docs/_static/typography_matrix.html` + builder;
`tests/test_font_invariants.py` (registry↔measured truth, matrix parity);
`.gitignore` (`docs/_static/realplots/` entry removed);
`docs/conf.py` (realplots hook unhooked).

Grep confirms **zero dead references** on main to the deleted stack (only our
POC files and old plan docs mention it).

### 1.4 Our POC (`docs/_static/poc_fonts_facets.frag.html`, 1625 ln) — state

Structure is good and embeddable: everything scoped under `#dm-fontfacets`,
styled exclusively with `--dm-*` tokens (theme-reactive), no
doctype/html/head/body. Left rail: search + facet chips
(Group/Script/Style/Italic/Weights) with live counts + zero-dimming; 1-column
result cards (name, desc, copyable mpl name, badges, own-face sample line);
detail drawer (hero, numerals, weight ladder, "why this face", rcParams
snippet with copy); toast; ESC/backdrop close; a11y focus discipline.

Defects to fix during integration:

1. **Stale inlined data** (lines ~321–1276): the old 16-family blob. Missing
   4 registry families; `"mpl": "Noto Sans SemiCondensed"/"Noto Sans Condensed"`
   are **wrong** (they register as "Noto Sans").
2. **Bogus API in the copy snippet**: `dm.set_theme()` does not exist (correct
   idiom: `dm.style.use("scientific")`); snippet also uses `plt` without import.
3. **Broken Italic facet**: `hasItalic` is derived from `/Italic/.test(w.face)`
   but the data's `weights[]` only ever contained upright faces → always
   "No italics". (Also Source Serif 4 italics use an `It` suffix.) Needs an
   explicit measured `italic` field.
4. Full-page shell: `.masthead` (own h1) + `.page{max-width:1220px}` assume a
   standalone preview page; must be trimmed for embedding under the docs H1.
5. `poc_fonts_r1/r2/r3.frag.html` are design refinements sharing the same
   stale blob + bogus snippet. `docs/pocs_fontb.md` / `pocs_fontb_refine.md`
   are orphan preview pages. Integration base = the **baseline**
   `poc_fonts_facets` (the named, authorized shape). r1–r3 disposition: §7 risk.

### 1.5 Pre-existing test baseline (this machine)

`python3 -m pytest tests/test_font_invariants.py -q` → **9 passed, 2 failed**.
The 2 failures (`test_mathtext_*`) are environment-caused, pre-existing on
main: matplotlib 3.10.8's SVG backend does
`fm.weight_dict[prop.get_weight()]` → `KeyError: 300` on numeric weights.
Not caused by (and not to be chased in) this work. "Done" = **no new
failures** beyond these two.

Docs build: `uv run sphinx-build` console script is broken — always use
`PLOT_GALLERY=0 python3 -m sphinx -b html -d docs/_build/doctrees docs docs/_build/html`.

---

## 2. Data/SSOT plan — registry-derived catalog, one source of truth

**Pattern**: follow `build_typography_matrix.py` + its parity test
(`test_typography_matrix_matches_builder`): a generator derives everything
from `dartwork_mpl.font`, writes a **committed** deterministic artifact, and a
test asserts byte-parity on regeneration. No hand-baked blob survives.
(We inline at *generation* time with test-enforced parity rather than at
sphinx-build time — same SSOT guarantee, no new build hook, and the committed
fragment stays reviewable. This is the repo's established convention for
committed generated artifacts.)

### Task 2.1 — new generator `docs/_static/scripts/build_fonts_browser_data.py`

Single script, deterministic output (sorted where order is not semantic, no
timestamps, `ensure_ascii=False`, trailing newline). CLI:

- `python3 docs/_static/scripts/build_fonts_browser_data.py` — splice payload
  into the fragment (in place).
- `--check` — exit 2 if a splice would change the committed fragment (used by
  the parity test and CI).

**Derivation (all from `dartwork_mpl.font` — no file lists in the script):**

```python
from dartwork_mpl import font
families = font.font_families()            # 18 registry entries — the SSOT
measurement = font._measure(name)          # per-family measured facts
face = font.css_font_face_name(f.file)     # "dm-<stem>" naming rule
```

Per family emit (payload keys the fragment JS consumes):

| Field | Source |
| --- | --- |
| `name`, `mpl` | registry key (identical — assert it) |
| `role` | `FontFamily.role` |
| `group` | curated display-group title (below) |
| `script`, `hero`, `sample`, `desc`, `intent`, `application`, `pairing`, `personality` | editorial `META` dict in the generator, **keyed by registry family name**; missing/extra key → `SystemExit` (fails loudly when a family is added/removed) |
| `weights` | ladder from `measurement.files` filtered `italic == False` and `stretch == "normal"`, sorted by `(weight, file)`. Each entry `{label, num, face}`: `num` = measured OS/2 weight (honest — Roboto/Paperlogy Thin shows 250), `label` = filename token after first `-`, digits stripped (`"4Regular"→"Regular"`, `"1Thin"→"Thin"`), normalized via `{"Semibold": "SemiBold"}` |
| `regular` | face of `font._default_numeric_face(...)` equivalent: min `abs(weight-400)` among ladder entries |
| `italic` | `measurement.italic` (fixes POC defect #3) |
| `mono` | `measurement.fixed_pitch` |
| `hangul`, `numeric_axes`, `tnum_available` | measured (`numeric_axes` = `families[name].numeric_axes`) |
| `chart_glyphs` | `"".join(measurement.chart_glyphs)` (drawer "Numerals & symbols" row) |
| `licenses` | `list(measurement.licenses)` |
| `chain` | copyable `font.family` list by role: `body/display/serif/kr-body` → `[name, "Noto Sans Math"]`; `mono` → `[name, "D2Coding"]`; `mono-kr` → `["JetBrains Mono", "D2Coding"]`; `fallback-tail` → `["Roboto", name]` |
| `width_variants` | **Noto Sans only**: `[{label, face}]` for the Regular cut of each stretch bucket (`normal`/`semi-condensed`/`condensed`), derived from `measurement.files` by `stretch`; label them `Normal / SemiCondensed / Condensed` |

Display groups (curated in the generator; union MUST equal the 18 registry
names — assert):

```python
GROUPS = [
    ("Workhorse",      ["Roboto", "Inter", "Source Sans 3"]),
    ("Display",        ["Inter Display"]),
    ("Technical",      ["IBM Plex Sans"]),
    ("Multilingual",   ["Noto Sans"]),
    ("Serif",          ["Source Serif 4"]),
    ("Korean & CJK",   ["Pretendard", "Paperlogy", "Noto Sans CJK KR"]),
    ("Monospace",      ["JetBrains Mono", "IBM Plex Mono", "Source Code Pro",
                        "Roboto Mono", "D2Coding"]),
    ("Symbols & Math", ["Noto Sans Math", "Noto Sans Symbols",
                        "Noto Sans Symbols 2"]),
]
ORDER = [slug(n) for _, names in GROUPS for n in names]   # 18 slugs
# slug(name) = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
```

**Editorial copy**: reuse the deleted generator's `META` verbatim for the 14
surviving families (`git show 44689a01~1:docs/_static/scripts/build_fonts_explorer_data.py`
— drop the `noto_semicondensed`/`noto_condensed` entries; their width story
moves into the Noto Sans card). Write 4 new entries — drafts to use (worker
may tighten wording, must keep every char of `hero`/`sample` honest per the
codepoint test in §5):

- **Source Serif 4** — group Serif, script `Latin`, hero `Aa Gg Rr 0123`,
  desc "Adobe's serif body face for journal- and book-matched figures.",
  intent "A contemporary serif with even color at text sizes — print gravitas
  for figures, opt-in only (never wired into a preset chain).",
  application "Journal, report, and book figures that need a serif voice.",
  pairing "Pairs with Source Sans 3 and Source Code Pro in the Source
  superfamily.", personality "Editorial · print-rooted".
- **D2Coding** — group Monospace, script `한글 + Latin (mono)`,
  hero `가나 012 {}`, sample `데이터 시각화 코드 정렬 0123456789`,
  desc "Naver's monospaced Hangul for code and aligned Korean tables.",
  intent "Fixed-pitch Hangul keeps mixed KR/EN code and tables
  column-perfect — the only bundled mono that speaks Korean.",
  application "Korean code blocks and aligned Korean tables.",
  pairing "Trails a Latin mono: font.family = ['JetBrains Mono', 'D2Coding'].",
  personality "Monospace · bilingual".
- **Noto Sans Symbols** — group Symbols & Math, script `Symbols`,
  desc "Symbol fallback for arrows, signs, and miscellaneous marks.",
  intent "Keeps arrows, stars, and signs from rendering as tofu — a
  fallback tail, not a body face.", application "End-of-chain fallback for
  annotation symbols.", pairing "Sits after Noto Sans Math in every preset
  chain.", personality "Fallback · coverage".
  `hero`/`sample`: pick 4–12 glyphs **verified present** via
  `python3 -c "from dartwork_mpl import font; cps = font._family_codepoints('Noto Sans Symbols'); print([c for c in '←↑→↓⇒⇔★☆✓✗♪−×°' if ord(c) in cps])"`.
- **Noto Sans Symbols 2** — same shape; desc "Final symbol fallback for
  dingbats, enclosed marks, and pictographic signs."; verify candidate glyphs
  (e.g. `⚠ ☑ ◐ ⬟ ⌚ ⏱`) the same way before baking them in.

**Splice format** (inside the fragment's `<script>` block, replacing the old
`var DM_FONT_DATA … var DM_FONT_GROUPS …;` region):

```
// DM_FONT_DATA:BEGIN — GENERATED, do not edit.
// Source: docs/_static/scripts/build_fonts_browser_data.py
// Regenerate: python3 docs/_static/scripts/build_fonts_browser_data.py
var DM_FONT_DATA = {…};
var DM_FONT_ORDER = […];
var DM_FONT_GROUPS = […];
// DM_FONT_DATA:END
```

The generator locates the marker pair with a regex, fails hard if absent or
duplicated, and rewrites only that region.

---

## 3. Integration plan — the browser as the primary `/fonts/` widget

### Task 3.1 — promote the POC to `docs/_static/fonts_browser.frag.html`

```bash
git mv docs/_static/poc_fonts_facets.frag.html docs/_static/fonts_browser.frag.html
```

Then edit the fragment:

1. Delete the line-1 HTML comment ("Recovered from built docs…"). Add a short
   header comment: hand-maintained embeddable fragment; data region generated
   (see markers); scoped `#dm-fontfacets`; consumed by `docs/fonts/index.md`
   via `{raw} html :file:`.
2. **Strip the page shell**: remove the `.masthead` markup and its CSS rules;
   change `.page` CSS to `max-width: 100%; padding: 0;` (keep `margin: 0
   auto` harmless or drop). The docs page supplies the heading; the fragment
   starts at the workbench (rail + results).
3. Replace lines ~321–1276 (the `var DM_FONT_DATA …` through
   `var DM_FONT_GROUPS …;` statements) with the marker pair from §2 (empty
   placeholders), then run the generator to splice real data.
4. **JS updates** (in the fragment's IIFE):
   - `FAMILIES` enrichment: `hasItalic: f.italic` (was face-regex),
     `isMono: f.mono` (was group-name comparison); add
     `style: f.mono ? "Mono" : (f.role === "serif" ? "Serif" : "Sans")`.
   - `facetSpecs`: Style values become `["Sans", "Serif", "Mono"]`;
     `famMatches` case `"style"` compares `f.style === value`. Group/Script/
     Italic/Weights facets unchanged (Italic now works).
   - Card badges: keep script + Mono + weight count; add a `Numeric axes`
     badge when `f.raw.numeric_axes` (measured truth from #448/#449 — this is
     the "registry truth" surfaced interactively).
   - Detail drawer:
     - "Numerals & symbols" section: render `0123456789` plus
       `f.raw.chart_glyphs` in the family's own `regular` face (drop the
       hardcoded `., $ %`).
     - **rcParams snippet** (fixes bogus API), built from `f.raw.chain`:

       ```
       import dartwork_mpl as dm
       import matplotlib.pyplot as plt

       dm.style.use("scientific")
       plt.rcParams["font.family"] = ["<chain[0]>", "<chain[1]>", …]
       ```

     - New "Width variants" section rendered only when
       `f.raw.width_variants` exists (Noto Sans): one row per variant, the
       same sample sentence in each variant's face, plus a one-line note:
       "Condensed and SemiCondensed register as Noto Sans (width metadata) —
       select via the bundled styles, not a separate family name."
   - No other behavior changes: facets, counts, search, copy, drawer,
     empty-state, toast all stay as-is.
5. Fragment hygiene (test-enforced in §5): no `<!doctype`, `<html`, `<head`,
   `<body`; no `dm.set_theme`; contains `id="dm-fontfacets"`;
   contains both markers exactly once.

### Task 3.2 — wire into `docs/fonts/index.md`

Current page (post-#449) order: intro → toctree → Overview → Quick Start →
Roles → Typography Matrix → Full Specimens. Edits:

1. Intro paragraph (lines 3–5): delete "The registry is static documentation:
   no interactive font widgets are shipped on this page." Replace with: the
   fonts page pairs the measured registry with an interactive browser backed
   by it.
2. Insert a new section **between Overview and Quick Start**:

   ````markdown
   ## Font browser

   Filter the 18 registered families by group, script, style, italics, and
   weight depth. Every sample renders in the family's own bundled cut; click
   a card for the weight ladder and a copyable `rcParams` snippet.

   ```{raw} html
   :file: ../_static/fonts_browser.frag.html
   ```
   ````

3. Keep Overview (counts paragraph — it is correct), Quick Start, Roles,
   Typography Matrix (`../_static/typography_matrix.html` raw include), and
   the Full Specimens pointer unchanged.

### Task 3.3 — POC cleanup

Delete: `docs/_static/poc_fonts_r1.frag.html`, `poc_fonts_r2.frag.html`,
`poc_fonts_r3.frag.html`, `docs/pocs_fontb.md`, `docs/pocs_fontb_refine.md`.
(Baseline was `git mv`'d in 3.1.) See §7 risk R3 before deleting r1–r3.

---

## 4. Polish plan (font assets on current main — discrete tasks)

| # | Task | File | Detail |
| --- | --- | --- | --- |
| P1 | Stale "font explorer" wording | `docs/fonts/families.md` (~line 13) | "use the [font explorer](index.md)" → "use the [font browser](index.md)". The link target becomes valid again with this integration. |
| P2 | `copy_fonts_to_static` misses `.otf` | `docs/_ext/build_hooks.py` (~line 357) | Loop `for pat in ("*.ttf", "*.otf"):` like `build_html_specimens` does. Today the hook is silently subsumed by `build_html_specimens` (which copies both), but in isolation it ships a fonts dir missing Pretendard + Noto Sans CJK. Two-line fix; do not restructure hooks. |
| P3 | Counts stay honest | (tests, §5) | 220/20/18 are correct **today**; lock them with `test_docs_font_counts_match_reality` instead of editing docs. |
| P4 | License coverage lock | (tests, §5) | 13 license files cover 20 groups via a known mapping; add the explicit map as a test so a future family add without a license file fails. |
| P5 | CSS | `docs/_static/dartwork-design.css` | **No change.** #449 removed `#dm-font-exp` cleanly (verified 0 leftovers). The browser keeps its scoped `<style>` inside the fragment — acceptable because the fragment is hand-maintained (the "no inline styles" rule in the CSS header applies to *builder-generated* fragments). Do not touch color-explorer selectors (SHA pins). |
| P6 | font.py | `src/dartwork_mpl/font.py` | **No change.** Registry + registration fixes are correct and fully consumed read-only by the generator. |

---

## 5. Tests plan

### Task 5.1 — new `tests/test_fonts_browser_consistency.py`

Model after the deleted `test_fonts_explorer_consistency.py` (see
`git show 44689a01~1:tests/test_fonts_explorer_consistency.py`) and the live
`test_typography_matrix_matches_builder`. Load the generator with
`importlib.util.spec_from_file_location` (scripts dir is not a package); parse
the committed fragment's payload by extracting the text between the
`DM_FONT_DATA:BEGIN/END` markers and `json.loads`-ing each
`var X = …;` statement.

Assertions:

1. **Byte parity**: running the generator's splice against the committed
   fragment is a no-op (equivalently: `--check` exits 0 via subprocess, or
   call the module's `build_payload()`/`splice()` and compare strings).
2. **Registry equality**: payload family `mpl` names set ==
   `set(font.list_registered())` == `set(font.FONTS)` (18). `name == mpl`
   for every entry; `DM_FONT_ORDER` length 18, no dupes; union of
   `DM_FONT_GROUPS` items == ORDER set.
3. **Face existence**: every `weights[].face` and `width_variants[].face`
   equals `font.css_font_face_name(<file>)` for a real file in
   `src/dartwork_mpl/asset/font/` (strip the `dm-` prefix → stem must exist
   with `.ttf`/`.otf`).
4. **Measured-flag parity**: for each family, payload `italic`, `mono`,
   `hangul`, `numeric_axes`, `tnum_available` equal the registry/measured
   values; ladder `num`s == sorted upright normal-stretch measured weights.
5. **Editorial completeness**: every family has non-empty `desc`, `intent`,
   `application`, `pairing`, `personality`, `hero`, `sample`, `chain`.
6. **Sample-glyph honesty** (kills the silent-fallback bug class): for every
   family, every non-ASCII char in `hero` and `sample` satisfies
   `ord(ch) in font._family_codepoints(family)`.
7. **Fragment hygiene**: committed fragment contains `id="dm-fontfacets"`,
   both markers exactly once, and none of `<!doctype`, `<html`, `<head`,
   `<body`, `dm.set_theme`.
8. **Chain validity**: every name in every `chain` is a registered family.

### Task 5.2 — counts + license locks (append to `tests/test_font_invariants.py`)

- `test_docs_font_counts_match_reality`: compute
  `n_files` (disk glob ttf+otf), `n_groups` (distinct `stem.split("-")[0]`),
  `n_families` (`len(font.list_registered())`); assert `(220, 20, 18)`
  equality is NOT hardcoded — instead regex-extract the bold claims from
  `docs/fonts/index.md`, `docs/fonts/families.md` (`**N text font files**`,
  `**N documented file groups**` / `**N documented file\ngroups**` — match
  across line breaks, `**N matplotlib family names**`) and the "all N bundled
  fonts" phrase in `docs/fonts/utilities.md`, and assert claims == computed.
- `test_every_family_has_license_file`: explicit map
  `{group_prefix: license_filename}` (Roboto→LICENSE-Roboto.txt,
  RobotoMono→LICENSE-RobotoMono.txt, Inter/InterDisplay→LICENSE-Inter.txt,
  IBMPlexSans/IBMPlexMono→LICENSE-IBMPlex.txt, SourceSans3→LICENSE-SourceSans3.txt,
  SourceSerif4→LICENSE-SourceSerif4.txt, SourceCodePro→LICENSE-SourceCodePro.txt,
  JetBrainsMono→LICENSE-JetBrainsMono.txt, NotoSans*→LICENSE-NotoSans.txt,
  NotoSansCJK→LICENSE-NotoSansCJK.txt, Paperlogy→LICENSE-Paperlogy.txt,
  Pretendard→LICENSE-Pretendard.txt, D2Coding→LICENSE-D2Coding.txt); assert
  every disk group prefix is in the map and every mapped file exists.

Do **not** modify `tests/test_colormap_explorer_taxonomy.py` /
`test_palette_family_taxonomy.py` (color SHA pins) or the existing
`test_font_invariants.py` assertions.

---

## 6. Verification (done-criteria)

Run from the repo root (`/Users/wonjun/Codes/company-analysis/dartwork-mpl`):

```bash
# 1. Generator determinism / parity
python3 docs/_static/scripts/build_fonts_browser_data.py          # splice
git diff --quiet docs/_static/fonts_browser.frag.html             # no drift after 2nd run
python3 docs/_static/scripts/build_fonts_browser_data.py --check  # exit 0

# 2. Tests — new + font suite (pytest)
python3 -m pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py -q
# Expected: all new tests pass; ONLY the 2 pre-existing mathtext failures remain
#   (KeyError: 300 in matplotlib 3.10.8 backend_svg — environmental, on main too).
python3 -m pytest -q   # no NEW failures repo-wide vs. the same baseline

# 3. Docs build (console script broken — use module form)
PLOT_GALLERY=0 python3 -m sphinx -b html -d docs/_build/doctrees docs docs/_build/html
# Expected: build succeeds; no new warnings referencing fonts_browser/pocs;
# no orphan warnings from the deleted pocs pages.

# 4. Visual confirmation (mandatory — serve, do not just claim success)
cd docs/_build/html && python3 -m http.server 8461   # fresh port each round
# Check http://localhost:8461/fonts/ in BOTH themes:
#   - browser renders under the page H1, 18 cards, facet counts sum correctly
#   - each card's sample renders in its own face (compare Paperlogy vs Roboto);
#     if all cards look identical, font-face.css/_static/fonts is broken
#   - Italic facet now partitions (e.g. Inter = Has italics, Paperlogy = No)
#   - Style facet: Serif shows exactly Source Serif 4
#   - drawer: ladder weights match typography matrix row; snippet copies the
#     dm.style.use(...) form; Noto Sans card shows the 3 width variants
#   - typography matrix + rest of the page unchanged below the browser
```

"Done" = all of: parity check green, new tests green, no new pytest failures,
docs build clean, visual checklist confirmed by the user via served URL.

---

## 7. Risks / human checks

- **R1 — direction reversal.** This deliberately overrides merged PR #449's
  breaking `refactor(docs)!` call ("no interactive widgets"). Authorized by
  the user, but the PR must say so explicitly. Suggested title:
  `feat(docs)!: restore interactive fonts browser on /fonts/ — registry-backed
  data SSOT (overrides #449 widget retirement, keeps registry truth)`.
  Merge only with explicit user approval.
- **R2 — concurrent sessions on fonts.** PRs #448/#449 merged *today* by the
  same user, and other sessions have been active in this clone. Before
  starting: `git fetch origin && git log --oneline origin/main -3` — if main
  moved beyond `774c5ff6`, rebase and re-verify §1 findings (especially
  font.py and index.md). Follow worktree/branch preflight discipline.
- **R3 — which POC variant.** Plan integrates the baseline
  (`poc_fonts_facets`, the named/authorized one). r1/r2/r3 are same-day
  refinements the user requested as design explorations; deleting them (Task
  3.3) discards that exploration. **Ask the user** (or keep the deletion in a
  separate final commit that is easy to revert). If the user later prefers an
  r-variant, only the fragment body swaps — the §2 data contract and markers
  are identical by construction.
- **R4 — width-variant presentation.** Decision here: Condensed/SemiCondensed
  live *inside* the Noto Sans card (matches #449's "file groups, not family
  names" truth). If the user wants them back as separate cards, they must be
  marked `registers as "Noto Sans"` — do not reintroduce fake `mpl` names.
- **R5 — pre-existing mathtext failures** (`KeyError: 300`, matplotlib
  3.10.8). Out of scope; do not "fix" in this PR. Flag to the user separately
  (likely needs a numeric-weight-safe assertion or an mpl version pin).
- **R6 — Symbols hero/sample glyphs.** Must be codepoint-verified (§2 drafts
  are candidates, not final). The §5 honesty test makes a bad pick fail CI,
  but pick sensible glyphs first to avoid churn.
- **R7 — embedding width.** The rail (244px) + 1-column cards were designed
  against ~800px docs content width; after removing the `.page` max-width,
  confirm the `@media` breakpoints in the fragment still stack the rail on
  narrow viewports (visual check in §6 step 4, resize the window).

---

## Task list (execution order)

1. **T1** Generator `docs/_static/scripts/build_fonts_browser_data.py`
   (registry-derived payload, META for 18 incl. 4 new entries, marker splice,
   `--check`). — §2
2. **T2** `git mv` POC → `docs/_static/fonts_browser.frag.html`; strip shell;
   insert markers; JS fixes (italic/mono/style facets, numeric-axes badge,
   chart-glyph numerals, chain-driven snippet, width-variants section); run
   generator. — §3.1
3. **T3** `docs/fonts/index.md`: intro rewrite + `## Font browser` raw
   include between Overview and Quick Start. — §3.2
4. **T4** Polish: families.md wording (P1), build_hooks otf glob (P2). — §4
5. **T5** Tests: new `tests/test_fonts_browser_consistency.py` + counts/license
   locks in `test_font_invariants.py`. — §5
6. **T6** Cleanup commit: delete r1–r3 fragments + both pocs pages (pending
   R3 confirmation). — §3.3
7. **T7** Verification battery + served visual check (§6); then PR per R1.

Atomic commits per task (T1+T2 may share one commit since the fragment is not
valid until first splice). All work stays on `feat/fonts-faceted-1col-design`;
PR targets `main`; no merge without user approval.
