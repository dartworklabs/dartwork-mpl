# Fonts/color post-merge audit follow-ups (advisory plan)

> Branch: `fix/fonts-audit-followups-2026-07-11` (from origin/main @ 14c86ba6).
> Source: 4-lens post-merge audit of PR #453 (tests / artifacts / docs / design
> philosophy), judged by the orchestrator. Worker: codex (offline sandbox).
> Every commit must leave the full suite green: `uv run python3 -m pytest -q`.

## Judged decisions (do NOT re-litigate)

- **KEEP** `landing_hero_after/before.svg` and `docs/_static/compare_slider.html`
  — they are LIVE (raw-included at `docs/index.md:62`; hero slider). The audit
  flagged them as orphaned; that was verified wrong.
- **KEEP** the coverage badge in accent tint (deliberate 3-step ladder) and the
  coverage badge on vendor-named fonts (Noto Sans Math etc.) — document both
  with comments only.
- **NO EDIT** to `docs/superpowers/specs/2026-07-10-typography-principles-design.md`
  (historical snapshot; Roboto Apache mention stays as a dated record).

## Commit 1 — `fix(style): use named font weight in base preset`

`src/dartwork_mpl/asset/mplstyle/base.mplstyle:35` has `font.weight:  300`
(numeric). Under matplotlib 3.10.8 + `svg.fonttype: none` this raises
`KeyError: 300` in `backend_svg` (`weight_dict` is string-keyed); CI's 3.10.9
tolerates it, so local runs diverge from CI.

- Change to `font.weight:  light` ('light' == 300 in matplotlib's weight_dict —
  same font file resolution, same rendered weight).
- Sweep ALL `asset/mplstyle/*.mplstyle` for other numeric `font.weight` /
  `axes.titleweight` / `figure.titleweight` values and normalize the same way.
- Gate: `uv run python3 -m pytest tests/test_font_invariants.py -q` → the two
  mathtext SVG tests (`test_mathtext_scientific_matches_body_without_dejavu`,
  `test_mathtext_kr_stays_latin_without_dejavu`) now PASS locally. Full suite +
  visual tests green. If ANY visual baseline breaks, REVERT this commit and
  record the failure in the commit-1 section of this plan instead — do not
  regenerate baselines to force it through.

## Commit 2 — `fix(docs): restore live wipe/compare assets + reachability test`

PR #453 deleted SVGs still referenced by committed widget HTMLs that are
raw-included on live pages (broken images on recipes/tutorials/layout/quickstart).

Restore from `ef14d845` (pre-merge parent) into a new durable directory
`docs/_static/compare_assets/` with semantic names:

| restore from (ef14d845) | new path (docs/_static/compare_assets/) |
| --- | --- |
| `docs/_static/landing_pocs/poc_02_bar_after.svg` | `wipe_bar_after.svg` |
| `docs/_static/landing_pocs/poc_02_bar_before.svg` | `wipe_bar_before.svg` |
| `docs/_static/landing_pocs/poc_03_scatter_after.svg` | `wipe_scatter_after.svg` |
| `docs/_static/landing_pocs/poc_03_scatter_before.svg` | `wipe_scatter_before.svg` |
| `docs/_static/landing_pocs/poc_04_dual_after.svg` | `wipe_dual_after.svg` |
| `docs/_static/landing_pocs/poc_04_dual_before.svg` | `wipe_dual_before.svg` |
| `docs/_static/landing_pocs/poc_06_stacked_after.svg` | `wipe_stacked_after.svg` |
| `docs/_static/landing_pocs/poc_06_stacked_before.svg` | `wipe_stacked_before.svg` |
| `docs/_static/landing_pocs/poc_08_distribution_after.svg` | `wipe_violin_after.svg` |
| `docs/_static/landing_pocs/poc_08_distribution_before.svg` | `wipe_violin_before.svg` |
| `docs/_static/compare_after.svg` | `quickstart_compare_after.svg` |
| `docs/_static/compare_before.svg` | `quickstart_compare_before.svg` |

(`git show ef14d845:<path> > <newpath>` — exact bytes, no regeneration; these
inputs have no surviving generator.)

- Update `src=` paths in: `docs/_static/wipe_l2_bar.html`, `wipe_l3_scatter.html`,
  `wipe_l4_dual.html`, `wipe_l6_stacked.html`, `wipe_l8_violin.html`
  (`../_static/landing_pocs/poc_X` → `../_static/compare_assets/<new>`), and
  `docs/usage_guide/images/compare_slider.html`
  (`../_static/compare_{after,before}.svg` → `../_static/compare_assets/quickstart_compare_{after,before}.svg`).
- Update `scripts/build_compare_widgets.py` input entries to the new paths;
  DELETE nothing else from it (hero entry stays). Re-run it and confirm the
  regenerated widgets byte-match the committed ones (generator is the SSOT); if
  the generator output differs beyond the src paths, fix the generator until it
  reproduces the committed widgets exactly.
- New test `tests/test_docs_asset_references.py`:
  1. every ``{raw} html\n:file:`` target in `docs/**/*.md` exists;
  2. for every committed widget/fragment HTML under `docs/`, every relative
     `src="..."` (map `_static/X` and `../_static/X` → `docs/_static/X`,
     `images/X` relative to the including doc's dir) resolves to an existing file.
- Gate: `grep -rn 'landing_pocs\|compare_after\.svg\|compare_before\.svg' docs/ scripts/ --include='*.html' --include='*.py' --include='*.md'`
  returns ONLY hits under `docs/superpowers/` (historical plans); new test green.

## Commit 3 — `chore(docs): regenerate committed example images under new corpus`

24 committed example images (`docs/api/images/*`, `docs/usage_guide/images/*`,
`docs/_static/after_dartwork.svg`, `before_default.svg`,
`docs/usage_guide/images/preset_compare.html`) embed pre-#453 Roboto metrics;
rebuilding docs produces subpixel geometry diffs (verified: e.g. font_example.svg
height 269.530141 → 269.52686pt).

- Do this AFTER commit 1 (style change affects rendering).
- Find the generation mechanism (grep `docs/conf.py` + `docs/**/scripts` for the
  code that writes those images) and regenerate deterministically. If the only
  path is a full sphinx build and it needs network (intersphinx), STOP, leave a
  `SKIPPED-COMMIT-3` note in the final report, and let the orchestrator run it.
- Gate: regenerate twice → `git diff` empty between runs (byte-idempotent);
  diffs vs HEAD are geometry-level only (no width/height attribute changes
  > 0.5%); full suite green.

## Commit 4 — `fix(docs): defined tokens + type-scale completion in fragments`

Both `docs/_static/fonts_browser.frag.html` and `docs/_static/pocs/fonts_ux_b.frag.html`:

- Replace ALL 23 `var(--dm-text)` → `var(--dm-text-default)` (undefined token;
  currently renders via inheritance luck).
- `.numerals { font-size: 22px }` → `var(--fbx-fs-numerals)`;
  `.tnum-values { font-size: 17px }` → `var(--fbx-fs-tnum)`; define
  `--fbx-fs-numerals: 22px; --fbx-fs-tnum: 17px;` next to the other `--fbx-fs-*`
  vars and extend the S4 type-scale comment to enumerate them.
- Extend the badge-ladder comment with one line: coverage tint is
  non-interactive by design (`pointer-events: none`); accent here marks
  capability tier, not affordance.
- Add a comment in `docs/_static/scripts/build_fonts_browser_data.py` where
  coverage is emitted: the coverage badge intentionally repeats a word from
  vendor names (Noto Sans Math/Symbols/CJK) — uniform system + intra-group
  discrimination beats per-card suppression.
- Do NOT touch the `DM_FONT_DATA:BEGIN/END` region. Gate:
  `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check` exit 0;
  `grep -c 'var(--dm-text)' <both fragments>` → 0 (only `--dm-text-default` etc.).

## Commit 5 — `test: pin badge ladder, type scale, token defs, dedup regression`

In `tests/test_fonts_browser_consistency.py`:

- `test_badge_color_ladder_and_type_scale_are_pinned`: assert in BOTH fragments
  the six `--fbx-fs-*` value strings (sample 22 / specimen 26 / ladder 19 /
  tray 24 / numerals 22 / tnum 17), `.badge.default { background: var(--dm-accent-9)`,
  `.badge.coverage { background: var(--dm-accent-3)`, and negative guard: no
  `--dm-info-` / `--dm-warning-` token inside any badge rule.
- `test_fragment_css_uses_only_defined_tokens`: collect every `var(--dm-*)`
  referenced in both fragments; assert each is defined in
  `docs/_static/dartwork-design.css` (this permanently kills the `--dm-text`
  class of bug).

In `tests/test_font_invariants.py` (or `test_font.py`):

- `test_bundled_registration_is_idempotent`: call `font._add_fonts()` explicitly
  (forcing a second matplotlib registration), then assert
  `len(font._measure('Roboto').files) == 18`,
  `len(font._measure('Roboto Mono').files) == 14`, and the 262 total — self-
  contained, order-independent lock on the resolved-path dedup.

## Commit 6 — `docs: fonts card wording, Aligned digits header, CHANGELOG`

- `docs/design_system/index.md:61`: "262 publication-grade fonts from 22
  families" → "20 publication-ready fonts (262 files across 22 file groups)".
- `docs/_static/scripts/build_typography_matrix.py`: column header
  "Numeric axes" → "Aligned digits"; regenerate `docs/_static/typography_matrix.html`
  (deterministic builder; run twice, byte-identical).
- `CHANGELOG.md` `[Unreleased]` → `### Added`: "Font corpus expanded to 20
  families (262 files): Noto Serif and IBM Plex Serif added, Roboto/Roboto Mono
  completed with instanced weights + italics; registry-backed interactive font
  browser on the fonts page (faceted filters, specimen drawer, badge system)."
- Gate: `uv run python3 -m pytest tests/test_fonts_browser_consistency.py -q`
  (count-claim tests) green; grep "Numeric axes" → 0 outside superpowers/.

## Commit 7 — `feat(docs): fetch entries for D2Coding and Source Serif 4`

`docs/fonts/fetch_fonts.py` covers every family except D2Coding (2 files) and
Source Serif 4 (12 files) — 14/262 files unreproducible.

- Add entries following the existing source-kind patterns:
  - D2Coding: GitHub release zip `naver/d2codingfont` (D2Coding Ver 1.3.2,
    zip contains D2Coding/D2Coding-Ver1.3.2-20180524.ttf + Bold — map to the
    two shipped stems `D2Coding-Regular.ttf` / `D2Coding-Bold.ttf`).
  - Source Serif 4: GitHub release `adobe-fonts/source-serif` (4.005 TTF zip),
    map the 12 shipped `SourceSerif4-*.ttf` stems.
- Offline note: you cannot download to verify. Match the shipped stems exactly,
  keep URL construction consistent with existing entries, and state in the
  commit body that the orchestrator verifies the fetch online post-hoc.
- Gate: `uv run python3 -c "import ast; ast.parse(open('docs/fonts/fetch_fonts.py').read())"`;
  any registry/spec listing inside fetch_fonts.py now covers all 22 groups.

## Final verification (worker, before reporting)

1. `uv run python3 -m pytest -q` → 0 failures (the 2 previously-env-failing
   mathtext tests must now pass).
2. `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check` → 0.
3. `git log --oneline origin/main..HEAD` → 7 commits (or 6 + SKIPPED-COMMIT-3 note).
4. `git status -s` → clean.
