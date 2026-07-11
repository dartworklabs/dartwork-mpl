# Fonts browser — round-3 refinement plan (advisory)

> Branch: `feat/fonts-browser-ux-2026-07-10` (continue). Two workers in order:
> **W1b (network)** fetches the two new serif families; **W2b (codex, offline)**
> implements everything else and must not start before W1b's commit exists.
> Generator contract unchanged (`DM_FONT_DATA:BEGIN/END` splice, `--check`
> green + idempotent after every corpus/generator change).

User feedback (10 items) → verified diagnoses:
1. Double clear-X in search: `type="search"` renders the WebKit native cancel
   button beside our custom `.search-clear`.
2. Placeholder should read `Search fonts` (drop everything after).
3. Badge placement: wants POC options for badges beside the title.
4. Badge sufficiency: add user-helpful capability badges (italics), keep
   Aligned digits/Mono/weights; provenance (license/foundry) belongs in drawer.
5. `Korean body` role badge + `한글 + Latin` script badge feel duplicated —
   two axes (role vs script) with overlapping labels.
6. Per-font description/provenance needs systematic structure.
7. Card order has hidden logic (registry group order) — make it visible.
8. Noto Sans Symbols vs Symbols 2: block split — Symbols = arrows/music/misc
   signs (← ↑ ♪), Symbols 2 = dingbats/enclosed/pictographs (⚠ ☑ ◐ ⏱).
   Descriptions must show the difference with real glyph examples.
9. UI terminology: `families` → `fonts` (keep "family name" only in
   matplotlib-API prose).
10. Only one serif is deliberate (sans-first, serif opt-in, KR serif excluded
    by design per registry quirks) — but expand to THREE quality serifs:
    add **Noto Serif** and **IBM Plex Serif** (both OFL).

---

## W1b (network worker) — add Noto Serif + IBM Plex Serif

1. **Noto Serif**: same route as Roboto (gf statics clamp risk → prefer
   `fonttools varLib.instancer` on google/fonts `ofl/notoserif`
   `NotoSerif[wdth,wght].ttf` + italic VF, pin `wdth=100`,
   `updateFontNames=True`, `recalcTimestamp=False`): uprights
   {100..900} + 9 italics = **18 files**, family name exactly `Noto Serif`,
   filenames `NotoSerif-<Weight>[Italic].ttf`.
2. **IBM Plex Serif**: same source style as the existing Plex entries
   (`IBM/plex` repo, `packages/plex-serif/fonts/complete/ttf`): 7 uprights
   {100,200,300,400,500,600,700} + 7 italics = **14 files**,
   `IBMPlexSerif-<Weight>[Italic].ttf`, family `IBM Plex Serif`.
   (Skip the `Text` cut if present — match the 7-weight pattern of the
   bundled Plex Sans/Mono.)
3. Licenses: Noto Serif → add `LICENSE-NotoSerif.txt` (OFL from
   ofl/notoserif/OFL.txt)… BUT check first whether the existing bundled Noto
   license file covers all Noto families (there may be a shared
   `LICENSE-NotoSans*.txt` convention — follow whatever per-family convention
   `asset/font/licenses/` currently uses). IBM Plex Serif is covered by the
   existing `LICENSE-IBMPlex.txt` if that is the shared Plex license — verify
   the zip/repo license text matches; if identical, reuse, else add
   `LICENSE-IBMPlexSerif.txt`.
4. fonttools verification table (family name records, usWeightClass sets,
   italic bits) — print in report. `import dartwork_mpl` clean.
   Corpus count 230 → **262**.
5. Update `docs/fonts/fetch_fonts.py` with both entries (reproducible).
6. ONE atomic commit: `feat(fonts): add Noto Serif (9w) and IBM Plex Serif
   (7w) static sets`. No docs/test/registry edits (W2b does).

## W2b (codex) — registry, UI, taxonomy, systematization

### T0 — registry entries for the two serifs (`src/dartwork_mpl/font.py`)
Model on the `Source Serif 4` FontFamily record:
- `"Noto Serif"`: role="serif", job="Serif sibling of Noto Sans for
  journal-matched multilingual figures.", quirks noting opt-in (not in preset
  chains) and pan-script metrics matched to Noto Sans; alternates wiring per
  the file's existing `_alternates` conventions for the serif role.
- `"IBM Plex Serif"`: role="serif", job="Completes the Plex superfamily —
  serif voice that pairs with IBM Plex Sans and IBM Plex Mono.", quirks
  noting opt-in.
- Update the Serif role alternates so Source Serif 4 / Noto Serif /
  IBM Plex Serif reference each other. Registry family-name count 18 → **20**.
- Any registry-level constants/tests that pin 18 families must move to 20.

### T1 — search box (items 1, 2)
- Suppress the native clear: `#dm-fontfacets .search-wrap input[type="search"]::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; }`
  (scoped; keep our `.search-clear`).
- Placeholder → `Search fonts`; aria-label → `Search fonts`.

### T2 — terminology sweep (item 9)
UI copy in BOTH fragments + `docs/fonts/index.md` + `docs/pocs_fonts_ux.md`:
`N of 20 fonts` (results head + rail count line), empty-state text, page
orientation intro (`20 publication-ready fonts`), browser section intro.
KEEP “family name” wording ONLY in the matplotlib-API prose (Quick Start,
How registration works, Roles lead-in) where it is the precise API term.

### T3 — badge taxonomy (items 4, 5)
- Role values collapse to five: `Body / Display / Serif / Mono / Symbols`
  (generator maps korean_body→Body, korean_mono→Mono, math/symbols→Symbols).
  The `한글 + Latin` script badge alone carries Korean-ness — overlap gone.
- Card badges (final set): script · `N weights` · `Italics` (only when true)
  · `Aligned digits` (tooltip kept) · `Mono` (only when mono) · `Default`
  (Roboto). Weights/script stay; role moves ONTO the title line (see T4).
- The page's Roles table is guidance and keeps its Korean body/Korean mono
  rows — no change there.

### T4 — badge-placement POC switcher (item 3)
In the POC page fragment (`docs/_static/pocs/fonts_ux_b.frag.html`) add a
small preview-only control `Badge layout: [A 제목 옆] [B 제목 아래] [C 분리]`
that toggles a class on the root and re-lays the SAME cards three ways:
- **A inline-with-title**: role chip + all badges flow right of the font name
  on one line (wrap allowed).
- **B under-title**: a tight badge row directly beneath the name, above the
  description.
- **C split**: role chip (+Default) beside the title; capability badges
  (script/weights/Italics/Aligned digits/Mono) as a muted meta line at the
  card foot (closest to current).
Default = C. Pure CSS/DOM re-slotting — data identical. The core
`/fonts/` fragment stays on C until the user picks.

### T5 — systematic per-font info (item 6)
- Generator META gains two curated fields per family: `foundry` (e.g. Google ·
  Adobe · IBM · JetBrains · 길형진(orioncactus) · Freesentation · Naver) and
  `source` (upstream project name, e.g. "Google Fonts", "IBM Plex",
  "orioncactus/pretendard"). Emit `license` from the registry's measured
  licenses (already available) — one license string per family.
- Drawer gains a final structured section **About** (replaces the loose
  pairing line): rows `Foundry · License · Source · Pairs well` — same order
  for every font. "Why this face" keeps intent+application paragraphs only.
- Card structure locked as: title(+role) → description (desc+application,
  full width) → badges/meta (per T4 layout).

### T6 — visible ordering (item 7)
Results column shows GROUP SUBHEADERS (the same titles as the rail Group
facet, in registry order: Workhorse → Display → Technical → Multilingual →
Serif → Korean & CJK → Monospace → Symbols & Math). A group header renders
only when it has visible cards under the current filters/search. This makes
the existing registry ordering legible; no sort control.

### T7 — Symbols differentiation (item 8)
META desc updates (show the split with real glyphs):
- Noto Sans Symbols: `Arrows, music, and miscellaneous signs — the first
  symbol fallback (← ↑ ♪ ✓).`
- Noto Sans Symbols 2: `Dingbats, enclosed marks, and pictographs — the final
  symbol fallback (⚠ ☑ ◐ ⏱).`
Confirm every glyph in these descs is covered by the respective face (the
generator's coverage check) — swap any uncovered glyph for a covered one.

### T8 — counts/locks sync
Docs numbers: 230→**262** files, 18→**20** family names, Serif group 1→3
members; `docs/fonts/index.md` Overview + Roles serif row alternates
(`Noto Serif, IBM Plex Serif`); test locks in `test_font_invariants.py`
(counts, license coverage incl. any new license file) and
`test_fonts_browser_consistency.py` (20 families, new fields foundry/source/
license non-empty for all).

### T9 — verification (report verbatim)
1. generator `--check` exit 0 + twice byte-identical.
2. `uv run pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py -q`
   → only the 2 pre-existing environmental mathtext failures.
3. Clean build (`rm -rf docs/_build/html docs/_build/doctrees` first;
   `PLOT_GALLERY=0 uv run python3 -m sphinx -b html -d docs/_build/doctrees
   docs docs/_build/html`) → succeeds; `/fonts/` shows 20 cards with group
   subheaders; POC page has the badge-layout switcher.
4. Hygiene greps on both fragments (shell/css-link/theme-mutation/src = 0).
5. Spot: search shows ONE clear button (no native), placeholder `Search
   fonts`, Pretendard card shows `Body` + `한글 + Latin` (no Korean body),
   Serif group has 3 cards.

## Commit subjects (atomic, in order)
- W1b: `feat(fonts): add Noto Serif (9w) and IBM Plex Serif (7w) static sets`
- T0: `feat(fonts): register Noto Serif + IBM Plex Serif (20 families)`
- T1+T2: `fix(docs): single search clear + fonts terminology sweep`
- T3+T5: `feat(docs): five-role badge taxonomy + About provenance section`
- T4: `feat(docs): badge-layout POC switcher (A/B/C)`
- T6+T7: `feat(docs): visible group ordering + symbols descriptions`
- T8: `chore(fonts): sync docs + locks (262 files, 20 fonts)`

## Notes
- Fragment ground rules unchanged.
- KR serif stays out of scope (registry quirk: legible Hangul serif adds
  several MB by design) — mention in the Serif group's context if natural.
