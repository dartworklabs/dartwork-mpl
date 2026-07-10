# Fonts browser — variant-B refinement plan (advisory)

> Branch: `feat/fonts-browser-ux-2026-07-10` (continue on it). Two workers, in
> order: **W1 (network worker)** fetches font binaries; **W2 (codex, offline)**
> does everything else. W2 must not start until W1's commit is present.
> Generator contract unchanged: it owns only the `DM_FONT_DATA:BEGIN/END`
> block in `docs/_static/fonts_browser.frag.html`; after any corpus/generator
> change, regenerate → `--check` exit 0, idempotent.

User picked **variant B (pin & compare)** and gave 7 refinements. Verified
facts behind them:
- Compare tray boxes each pinned family side-by-side → boxes kill the
  comparison; wants a vertically stacked specimen list.
- Facet rail is too wide (244px + roomy chips).
- Drawer is `min(440px, 92vw)` → sentences/code clip; ladder rows show
  placeholder "Agile 24"; descenders ("g") clip and rows aren't vertically
  centered (tight line-height + 96px meta column).
- Card's mpl mono chip is redundant (name is the title) — remove; keep only
  Copy chain + pin.
- Card description wraps in a narrow sub-column (because it shares `.card-top`
  with the chip) and is too thin content-wise; data already has
  `desc` + `application` (+ `pairing`) to compose richer copy — full width.
- `Numeric axes` badge = registry's measured "digit widths uniform (or
  fixed-pitch)" gate — meaningless label without explanation.
- Roboto bundles the legacy `roboto-2` 6-weight static set (Thin measures 250);
  the current Google Fonts static family is 9 weights (100–900). Roboto Mono
  bundles 5 of 7 uprights (missing ExtraLight 200 / SemiBold 600).

---

## W1 (network worker) — complete the Roboto & Roboto Mono corpora

1. Download the current Google Fonts static families:
   - `https://fonts.google.com/download?family=Roboto` → zip contains
     `static/Roboto-{Thin,ExtraLight,Light,Regular,Medium,SemiBold,Bold,ExtraBold,Black}.ttf`
     + the 9 `Italic` counterparts.
   - `https://fonts.google.com/download?family=Roboto+Mono` → statics for
     uprights {Thin,ExtraLight,Light,Regular,Medium,SemiBold,Bold} + italics.
   - If the `download?family=` endpoint is unavailable, fall back to
     `github.com/google/fonts` `ofl/roboto*` variable TTFs +
     `fonttools varLib.instancer` (pin named instances; keep family name
     records intact). Prefer the zip statics.
2. REPLACE the existing `src/dartwork_mpl/asset/font/Roboto-*.ttf` (12 files)
   with the new 18, and `RobotoMono-*.ttf` (10) with the new 14. Filenames keep
   the `Roboto-<Weight>[Italic].ttf` pattern (matches `css_font_face_name`).
3. Verify with fonttools before committing: every file's family name is
   exactly `Roboto` / `Roboto Mono`, usWeightClass covers {100..900} uprights
   for Roboto and {100,200,300,400,500,600,700} for Roboto Mono, italics carry
   the italic bit. Print the table in your report.
4. Update `docs/fonts/fetch_fonts.py`: change the Roboto / Roboto Mono plan
   entries to the new reproducible source (gf zip URL or instancer fallback),
   so `fetch_fonts.py --only "Roboto,Roboto Mono"` reproduces the corpus.
5. Sanity: `uv run python3 -c "import dartwork_mpl"` still registers cleanly;
   `python3 -c` count of `asset/font/*.ttf|otf` = **230** (was 220).
6. Commit: `feat(fonts): complete Roboto (9w) and Roboto Mono (7w) static sets`
   — include the file count change in the body. Do NOT touch docs counts or
   tests (W2 does).

## W2 (codex) — design refinements

### T1 — corpus-count sync (after W1)
- Regenerate browser data (`build_fonts_browser_data.py`), `--check` green.
- Update every count the docs/tests lock: `docs/fonts/index.md` "220 text font
  files" → 230; `tests/test_font_invariants.py` count/license locks; any other
  literal 220/12/10 that the invariants pin. Roboto weight badge should now
  read 9 weights (Thin 100 … Black 900), Roboto Mono 7.
- Commit: `chore(fonts): sync docs + locks to the completed corpus (230 files)`

### T2 — facet rail: tighter (user item 2)
`docs/_static/fonts_browser.frag.html` (root `dm-fontfacets`):
- Rail column 244px → **184px**; chip font 12px→11.5px, padding tightened
  (≈3px 8px), chip gap 6px→4px; facet-head margins halved; search input
  height trimmed to match.
- The freed width goes to the results column automatically (grid template).
- Commit: `style(docs): tighten fonts browser facet rail`

### T3 — card redesign (user items 4, 5, 6)
- REMOVE the mpl mono chip (`.mono-name`) and its handlers/CSS. Card top-right
  actions: `Copy chain` ghost button (+ pin star in the B POC).
- Description: move out of the split `.card-top` column — full card width,
  composed as `desc + " " + application` (both already in the data; simple JS
  concat; no ellipsis clamp — allow 2 lines).
- `Numeric axes` badge → relabel **`Aligned digits`** with
  `title="Digits share one width, so numeric axis labels stay aligned (the registry's numeric-axes gate)."`
- Keep badges order: role · script · weights · Aligned digits · Mono.
- Commit: `feat(docs): fonts browser card redesign — full-width copy, fewer chrome`

### T4 — drawer redesign (user item 3)
- Width `min(440px, 92vw)` → **`min(640px, 94vw)`**.
- Ladder rows: replace `Agile 24` with the family's own `sample` sentence,
  one line, `text-overflow: ellipsis`; row layout `align-items: center`;
  sample `line-height: 1.4` and NO overflow-y clipping (descenders must
  render fully — check `overflow`, `max-height`, and line-height on
  `.ladder-sample`); meta column 96px → 112px (label + number don't wrap).
- Recompose the drawer body in this order (rethink, not just widen):
  1. `Specimen` — the family sample sentence in Regular at ~26px,
     descender-safe (replaces the old `Hero` section; drop the
     `Aa Gg Rr 0123` line — the ladder + numerals cover it).
  2. `Weight ladder` — per-weight sample rows as above; rows remain
     copy-buttons (`fontweight=N`).
  3. `Numerals & symbols` — digits + chart glyphs + tnum proof (unchanged).
  4. `Width variants` — Noto Sans only (unchanged).
  5. `Why this face` — richer: intent paragraph, then a second paragraph
     `application`, then `Pairs well: <pairing>` as a muted line (all three
     fields exist in the data).
  6. `rcParams snippet` — full width; `pre`-style block with
     `overflow-x: auto`, no line clipping; Copy button unchanged.
- Commit: `feat(docs): fonts browser drawer — wider, specimen-first, honest ladder`

### T5 — compare tray: stacked specimen list (user item 1)
`docs/_static/pocs/fonts_ux_b.frag.html` (root `dm-fbuxb`) — first re-sync it
with the refreshed core (re-copy the updated `fonts_browser.frag.html`,
re-scope ids to `dm-fbuxb`, re-apply the preview-input + pin deltas), then:
- Tray items: NO per-family boxes/cards. A single flat list: each pinned
  family = one row separated by hairlines only —
  `[tiny meta: family name (11px, muted) + unpin ×]` above/left,
  then the comparison sentence full-width at ONE uniform size (~24px),
  descender-safe. The sentence = the preview text if typed, else the standard
  Latin sample; all pinned rows use the SAME sentence so shapes compare
  directly. Per-row `Copy chain` ghost (small, right-aligned, on hover).
- Tray header: `Finalists — same sentence, same size.` + `Clear pins`.
- Tray max-height ~40vh with internal scroll if 3 pinned on a laptop.
- Commit: `feat(docs): POC B — stacked specimen compare tray`

### T6 — preview page + A retirement
- `docs/pocs_fonts_ux.md`: drop the A section (A was not chosen; delete
  `docs/_static/pocs/fonts_ux_a.frag.html`), retitle the page
  `Fonts browser — B 리파인`, banner explains: 공통 개선(rail·카드·드로어)은
  `/fonts/`에서, B의 핀 비교는 이 페이지에서 확인.
- Commit: `docs: refine preview page to the chosen B direction`

### T7 — verification (report verbatim)
1. generator `--check` exit 0 + run-twice byte-identical.
2. `uv run pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py -q`
   → only the 2 pre-existing environmental mathtext failures.
3. `PLOT_GALLERY=0 uv run python3 -m sphinx -b html -d docs/_build/doctrees docs docs/_build/html`
   → succeeds; `/fonts/` has `dm-fontfacets`; `pocs_fonts_ux.html` has
   `dm-fbuxb` and NOT `dm-fbuxa`.
4. Hygiene greps on the two fragments (shell/css-link/theme/src = 0).
5. Quick data spot-check: Roboto entry now lists 9 weights 100–900;
   Roboto Mono 7.

## Notes
- Fragment ground rules unchanged (scoped CSS, no theme mutation, tokens only,
  buttons, focus rings, reduced-motion, <820px responsive).
- Winner integration (fold B into the core fragment, delete `pocs/`) is a
  LATER step after user sign-off — not in this plan.
