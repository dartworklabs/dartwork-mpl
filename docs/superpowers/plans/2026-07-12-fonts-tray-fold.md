# Fold pin/compare tray (POC B) into the /fonts/ browser (advisory plan)

> Branch: `feat/fonts-tray-fold-2026-07-12` (from origin/main @ a8a7fbaa).
> User decision: the compare-tray variant (B) becomes THE fonts browser.
> Worker: codex. Every commit leaves `uv run python3 -m pytest -q` green.

## Verified ground truth (do not re-derive)

- `sed 's/dm-fbuxb/dm-fontfacets/g' docs/_static/pocs/fonts_ux_b.frag.html`
  vs `docs/_static/fonts_browser.frag.html` differs ONLY in:
  (a) one header-comment line (which page includes the fragment),
  (b) B-only additions: preview toolbar, `.pin-toggle`, compare tray
  (CSS + markup + JS), and
  (c) two JS render lines where B is the dynamic superset
  (`previewText.trim() ? previewText : f.raw.sample`) of core's static
  version — B's behavior is the one we want.
- The generated `DM_FONT_DATA:BEGIN/END` regions are byte-identical.
- Generator `--check` targets only `fonts_browser.frag.html`.

## Commit 1 — `feat(docs): fold pin/compare tray into the fonts browser`

- New `docs/_static/fonts_browser.frag.html` := the B fragment with
  `dm-fbuxb` → `dm-fontfacets` everywhere, and the header comment updated to
  say `docs/fonts/index.md includes this fragment` (keep the rest of the
  comment intact).
- Confirm no other `fbuxb` residue: `grep -c fbuxb docs/_static/fonts_browser.frag.html` → 0.
- Gate: `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check`
  exit 0 (generated region untouched); grep the new core for
  `preview-toolbar`, `pin-toggle`, `compare-tray` (all present).

## Commit 2 — `chore(docs): retire fonts POC page and fragment`

- Delete `docs/_static/pocs/` (entire directory) and `docs/pocs_fonts_ux.md`.
- Sweep references: `git grep -n 'pocs_fonts_ux\|fonts_ux_b\|dm-fbuxb\|_static/pocs'`
  → 0 hits outside `docs/superpowers/` (historical plans stay).
- If `docs/conf.py` or any toctree mentions the POC page, remove that mention.

## Commit 3 — `test: converge fonts browser tests on the single fragment`

`tests/test_fonts_browser_consistency.py`:

- Remove `_POC_B` / `_POC_B_PATH` and every test (or branch) that reads the
  POC fragment or `docs/pocs_fonts_ux.md` (e.g. `test_poc_b_is_resynced`,
  banner-copy assertions, `--fbx-fs-tray` POC-only assertion).
- Tests that iterated `(_FRAGMENT, _POC_B)` now assert on `_FRAGMENT` only.
- Move tray coverage INTO the core assertions: `--fbx-fs-tray: 24px`,
  `.pin-toggle`, `compare-tray`, the preview input, and the tray heading
  copy (`Finalists`) must be present in `_FRAGMENT`.
- Add a permanent lock: `docs/_static/pocs` path does not exist and
  `docs/pocs_fonts_ux.md` does not exist.
- Sweep other test files for POC references (`git grep -ln 'pocs' tests/`)
  and update the same way.

## Commit 4 — `docs: document the pin/compare workflow + changelog`

- `docs/fonts/index.md`, in the Font browser section copy: add 1–2 plain
  sentences (sentence case, active voice) explaining: star a card to pin it;
  pinned fonts stack in the bottom tray rendering the same sentence at the
  same size; type your own sentence in the preview field to test all cards
  and the tray with it.
- `CHANGELOG.md` `[Unreleased]` — extend the existing font-browser entry
  with: pin/compare tray and custom preview sentence now on the fonts page.
- Gate: `uv run python3 -m pytest tests/test_fonts_browser_consistency.py
  tests/test_docs_count_claims.py tests/test_docs_asset_references.py -q` green.

## Final verification (worker, before reporting)

1. `uv run python3 -m pytest -q` → 0 failures.
2. `uv run python3 docs/_static/scripts/build_fonts_browser_data.py --check` → 0,
   run twice → byte-identical fragment.
3. `git grep -c 'fbuxb' -- ':!docs/superpowers'` → 0.
4. `git status -s` clean; `git log --oneline origin/main..HEAD` → 5 commits
   (plan + 4).
