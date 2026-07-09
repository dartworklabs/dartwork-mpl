# Typography principles (T) — Implementation Plan

> Gate-driven plan (codex CLI worker, supervisor commits). One PR, two
> logical halves: T1 lib truth, T2 docs truth. Spec:
> `docs/superpowers/specs/2026-07-10-typography-principles-design.md`.

**Goal:** Turn the bundled font system into a principled one — a roles/jobs
registry in code, measured CI gates (weight grid · tnum-or-mono · chart-glyph
resolution · license · Hangul truth · pinned fallback chain), corrected
JetBrains assets — and replace the D1 "Typography rationale (placeholder)"
with the real evidence page.

## Global Constraints

- Branch `feat/typography-principles-2026-07-10`, worktree
  `dartwork-mpl-colorsys`, `.venv`. Worker does not commit/push.
- **JetBrains Mono TTFs are ALREADY REPLACED in the working tree** by the
  supervisor (upstream v2.304 statics, same 16 filenames, weights now
  100–800). Build on that; do not fetch anything (no network).
- Measured values are derived from the bundled files (fontTools), never
  hand-typed; curated values (roles, jobs, alternates, quirk exceptions)
  live in code next to the registry.
- Color explorer fragments stay byte-identical. The FONT explorer WILL
  change (weight segments heal to the standard grid) — regenerate it and
  update its pins.

## Task 1 — Roles/jobs registry (`dartwork_mpl.font`)

`FontFamily` record + `FONTS` mapping for the 16 matplotlib families:
`role` (`body | display | kr-body | mono | fallback-tail`), `job` (one
sentence), `alternates` ordering, `numeric_axes: bool` (tnum-or-mono
recommendation), `quirks` (e.g. Roboto: "Thin ships as OS/2 250 —
upstream quirk"). Provide `font_families()` public accessor (returns the
records) — keep the surface tiny; measurements come from a private
`_measure(family)` helper (weights, italic, tnum, fixed-pitch, chart-glyph
coverage of − × ± → ° μ σ Δ, Hangul, license classification from the name
table) shared by tests and builders.

Roles per spec §3: body=Roboto (alt Inter · IBM Plex Sans · Source Sans 3 ·
Noto Sans) · display=Inter Display · kr-body=Paperlogy (alt Pretendard ·
Noto Sans CJK KR) · mono=JetBrains Mono (alt IBM Plex Mono · Roboto Mono ·
Source Code Pro) · fallback-tail=Noto Sans Math → Symbols → Symbols 2.
`numeric_axes=False` for IBM Plex Sans, Source Sans 3, Paperlogy, Noto Sans
CJK KR (measured: no tnum, not mono) — and any other family the measurement
says so for.

## Task 2 — Invariant gates (`tests/test_font_invariants.py`)

- (a) every file's OS/2 weight ∈ {100..900 step 100}, exceptions only from
  the registry's named quirks (expect: Roboto 250 only — JetBrains must now
  pass clean);
- (b) `numeric_axes=True` ⇒ tnum in GSUB or post.isFixedPitch;
- (c) chart-glyph resolution: for each of − × ± → ° μ σ Δ, digits 0-9, and
  '한', walk the base preset `font.family` chain and pin the FIRST family
  whose cmap resolves it (golden dict); assert no glyph falls through to
  matplotlib's DejaVu;
- (d) license of every file classifies as OFL-1.1 or Apache-2.0;
- (e) registry Hangul/italic/mono flags == cmap/post truth; registry family
  set == registered matplotlib family set (16);
- determinism: `_measure` twice → identical.

## Task 3 — Heal downstream of the JetBrains fix

Regenerate the font explorer (weight segments now standard); update
`tests/test_font_explorer_taxonomy.py` pins; check
`docs/_static/scripts/build_fonts_explorer_data.py` output and
`docs/fonts/_generated` specimens for stale weight mentions (regenerate
via their generators where applicable); confirm counts stay 206/18/16.

## Task 4 — T2 docs truth

- New permanent builder `docs/_static/scripts/build_typography_matrix.py`
  → `docs/_static/typography_matrix.html`: the measured matrix (family ×
  role · weights · tnum/mono · chart-glyph · Hangul · license), rendered
  from the registry + `_measure`, same visual language as the docs tables
  (no `<style>` tag; reuse existing table classes or minimal semantic
  markup).
- `docs/color_system/design-rationale.md`: REPLACE the
  "Typography rationale (placeholder)" section with the real one — axioms
  T1–T4 (from the spec, docs voice), the jobs/roles table, the matrix
  include, and a short "anatomy of the fallback chain" subsection
  explaining the pinned resolver order (body → kr → math → symbols) with
  the actual chain from the presets. Keep it tight (~1 screen + matrix).
- `docs/fonts/families.md`: reframe the top around the roles table
  (role → default + alternates + when-to-pick), keep the long-form
  showcases; drop any copy that contradicts the registry.
- `docs/fonts/index.md`: one sentence + link to the rationale's typography
  section ("why these fonts").

## Task 5 — Gates + report

Full pytest green · mypy · ruff · sphinx exit 0 (`-D plot_gallery=0`) ·
node-parse font fragment · color fragments byte-identical · grep gate:
"placeholder" gone from design-rationale.md typography section. Report:
registry summary, gate (c) golden resolver map, JetBrains before/after
weight sets, every doc edit, pytest/sphinx tails, porcelain. No commit.
