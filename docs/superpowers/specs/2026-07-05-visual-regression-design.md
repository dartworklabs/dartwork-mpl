# Visual Regression Testing — Design (P1)

> Program: "evolve dartwork-mpl into a systematic professional design-plot utility" (umbrella #411).
> Pillar EO1. Advisory/design by orchestrator; implementation by codex worker; baselines generated + verified by orchestrator.

## Problem

dartwork-mpl's core value is *rendered output looks right*, but nothing tests that.
The examples gallery was 100% broken (every example threw on removed 0.4.1 API) and
**survived three audits** — smoke tests catch "runs", determinism tests catch "bytes are
stable", but neither catches "the design regressed" (wrong palette, missing artist, tofu
glyph, broken layout). We need a visual regression layer.

## Constraint that shapes the design

Pixel-exact baselines are **environment-sensitive**: rendered text depends on the freetype
version, and glyph/marker path data depends on the matplotlib version. Local dev is macOS
(freetype 2.6.1, mpl 3.10.8); CI is ubuntu-latest with a different freetype. macOS-generated
PNG baselines will **not** pixel-match ubuntu CI. This is the classic pytest-mpl cross-platform
trap. Therefore the CI *gate* cannot be naive pixel diffing.

## Design: two complementary layers

### Layer 1 — Property/structural assertions (CI-gated, primary workhorse)

Environment-robust. Runs on the **full test matrix** (all Python versions). For each canonical
scenario, build the figure and assert on *semantic properties* of the artists — not pixels:

- figure has the expected number of axes; each data axes has ≥1 expected artist
  (`Line2D` / `Patch` / `QuadMesh` …) at the expected count
- colored artists resolve to the expected palette: compare `artist.get_*color()`
  (normalized to hex via `matplotlib.colors.to_hex`) against
  `dm.color(token).to_hex()` for the scenario's declared palette tokens
- declared text strings are present in the rendered `Text` artists (catches a KR label
  being dropped or a title going missing)
- every data axes has a non-empty y-label (repo rule: "Y축 라벨 필수")
- tick-label font family resolves to one of the **bundled** dartwork families
  (catches a tofu/fallback regression — the class the font work fixed)

This layer alone would have caught the broken gallery: the scenario builders exercise the
same code paths the examples do, so a removed-API exception fails the build immediately.

### Layer 2 — Pixel baselines (pytest-mpl, dedicated job + local opt-in)

The true "does it look right" gate, using **pytest-mpl** (`@pytest.mark.mpl_image_compare`).
Key property: without the `--mpl` flag the marked test still *executes the builder* (a smoke
run) but skips comparison — so these tests contribute matrix-wide smoke coverage and become a
pixel gate only in the dedicated job.

- `tolerance` (RMS) per test, generous enough to absorb anti-alias/minor-freetype jitter but
  tight enough to catch a real design change (wrong color, missing bar). Default ~20; raise
  case-by-case for text-heavy scenarios.
- Baselines are **generated on the CI runner (ubuntu, locked mpl)** — never committed from
  macOS — so they self-match subsequent CI runs (uv.lock pins mpl exactly). A
  `workflow_dispatch` workflow renders + uploads them; the orchestrator downloads and commits.
- Dedicated `visual` CI job (ubuntu, Python 3.12) runs `pytest tests/visual --mpl` and uploads
  the diff images as an artifact on failure.

## Scope (P1 PR)

**New files**
- `tests/visual/__init__.py`
- `tests/visual/scenarios.py` — the scenario registry (SSOT for both layers)
- `tests/visual/test_visual_properties.py` — Layer 1, parametrized over the registry
- `tests/visual/test_visual_pixels.py` — Layer 2, `@mpl_image_compare` per scenario
- `tests/visual/baseline/` — CI-generated PNG baselines (committed)
- `.github/workflows/visual-baselines.yml` — `workflow_dispatch` baseline generator
- `docs/development/visual-regression.md` — how to update baselines on an intentional design change

**Modified**
- `pyproject.toml` — add `pytest-mpl` to dev deps; register the `mpl_image_compare` marker
- `.github/workflows/ci.yml` — add the `visual` job

### Scenario corpus (14, SSOT = `scenarios.py`)

Each scenario is a `Scenario(name, build, expect)`:
- `build() -> matplotlib.figure.Figure` (Agg; applies its own `dm.style.use(...)`)
- `expect: Expectations` declaring `n_axes`, `min_lines`, `min_patches`, `texts_contain`,
  `palette` (tokens), `tolerance` (pixel RMS)

Corpus:
1. **Presets (4)** — one reference chart per preset to catch preset regressions:
   `preset_report_line`, `preset_report_kr_bars`, `preset_scientific_scatter`,
   `preset_scientific_kr_hist`.
2. **Archetypes (7)** — adapt the existing `examples/*.py` so the corpus exercises the real
   example code paths: `line_signals`, `bar_value_labels`, `scatter_fit`,
   `histogram_normal_fit`, `heatmap`, `donut_composition`, `dual_axis_timeseries`.
3. **Color (2)** — `palette_swatch` (a categorical palette as swatches),
   `colormap_strip` (a sequential + a diverging colormap gradient).
4. **Fonts (1)** — `kr_math_labels`: Korean text + a `$...$` mathtext expression + special
   chars (×, ±, →), to catch font/tofu regressions.

## Decisions (defaults; noted here, no user round-trip)

- **Tool**: pytest-mpl (industry standard for mpl visual regression) over hand-rolled
  `matplotlib.testing.compare_images` — cleaner baseline/tolerance/diff-artifact story.
- **CI gate** is Layer 1 (property, robust, all-matrix) + Layer 2 pixel job (ubuntu-native
  baselines). If CI-native baselines are not yet committed when the PR opens, the `visual`
  job runs `continue-on-error: true` (informational) until baselines land in the same PR.
- **Marker**: registered `mpl_image_compare` so `--strict-markers` (already on) stays clean.
- Baselines live in-repo (`tests/visual/baseline/`), git-tracked, updated only via the
  documented regenerate→visually-confirm→commit flow (ties into the serve-visual rule).

## Acceptance

- `pytest tests/visual/test_visual_properties.py` — all green on the local env.
- `pytest tests/visual/test_visual_pixels.py` (no `--mpl`) — all green (builders execute).
- `ruff check` / `ruff format --check` / `mypy` clean on the new files.
- Full suite still green (no regression); `test_drift` unaffected (no corpus-source edits).
- `visual` CI job present; `visual-baselines.yml` present; ubuntu-native baselines committed.
- `docs/development/visual-regression.md` documents the update flow; docs build (`-W`) clean.

## Non-goals (P1)

- No perceptual (SSIM) metric — RMS tolerance is sufficient and is pytest-mpl's native mode.
- No hash-based baseline library (stricter, more brittle across envs).
- No coverage of every example/template — a curated 14-scenario corpus; expand later (P6 cookbook).
