# OKLab-Centered Color System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CIELAB-driven construction with an OKLab/OKLCH authoring
model plus explicit modeled-relative-CIE-Y output contracts, while preserving
every shipped color and providing a deterministic before/after comparison
space.

**Architecture:** A frozen v5 compatibility asset is the non-circular
baseline. A new tone kernel defines `NeutralTone = cbrt(RelativeY)` and solves
only chromatic OKLCH `L`; recipe, palette, colormap, and discrete construction
consume that kernel without importing CIELAB/CIEDE2000. Validation remains an
independent layer and emits strict JSON plus a human-readable HTML report.

**Tech Stack:** Python 3.10+, NumPy, matplotlib, pytest, Ruff, mypy, Sphinx,
standard-library JSON/HTML generation. No new runtime dependency.

## Global Constraints

- Accepted design:
  `docs/superpowers/specs/2026-07-14-oklab-centered-color-system-design.md`.
- Baseline commit: `12d16bac22dee790bd0696ca92a814a797dc728b`.
- Exact output: all 18 frozen public surfaces must remain value-identical:
  `palette`, `cycles`, `cmaps256` (43×256), `curated_rows`,
  `diverging_canonicals`, `semantic_coordinates`, `semantic_colors`,
  `dark_cycle_coordinates`, `dark_cycle`, `taxonomy`, `registrations`,
  `typing_literals`, `mcp_discovery`, `public_inventory`, `discrete_hex`,
  `reverse_discrete_hex`, `multi_hue_discrete_indices`, and `vendor_colors`
  (all 892 vendor token name → hex values).
- Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB;
  it is not a measurement of a particular display, print process, perceived
  brightness, or OKLab `L`. Its v5-compatible white-normalized coefficient row
  is:
  `SRGB_D65_Y = (0.21267287873271212, 0.7151521284847872,
  0.07217499278250072)`. The legacy raw XYZ row remains private to
  CIEDE2000 validation.
- Construction modules may use OKLab, OKLCH, sRGB gamut, modeled relative CIE
  Y, and OKLab ΔE. They may not import CIELAB, CIEDE2000, or CVD objectives.
- CIEDE2000 and Machado/BVM remain independent validation oracles.
- Existing gamut policy remains fixed-L/h chroma reduction, tolerance
  `1e-6`, 24 iterations, and final clamp.
- Candidate build must not regenerate its own baseline. Frozen literal
  arrays and hashes are read from the v5 compatibility asset.
- Every production-code change follows RED → verify RED → GREEN → verify
  GREEN. Generated files are emitted only after their generator tests pass.
- Use `uv run` for Python commands. Do not add or edit dependency lists by
  hand.
- Existing user changes in the main worktree are out of scope and must not be
  deleted, reformatted, or regenerated.
- Commit commands below are checkpoints only. Do not execute them until the
  user approves committing the reviewed diff.

## File Responsibility Map

```text
docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/
├── color_v5_compatibility.json  # immutable literal baseline
└── color_v5_quality.json        # independent oracle over frozen v5 literals
src/dartwork_mpl/asset/color/
└── color_v6_ssot.json           # packaged operational neutral-tone SSOT
src/dartwork_mpl/_colors/
├── _conversion.py               # sole sRGB/linear RGB/OKLab/OKLCH math
├── _gamut.py                    # named sRGB gamut mapping policy
├── _tone.py                     # RelativeY/NeutralTone and OKLCH-L solver
├── _ssot.py                     # single validated accessor for packaged v6 JSON
├── _catalog.py                  # immutable catalog snapshot/load/compile model
├── _metrics.py                  # validation metrics; imports conversion math
├── _recipe.py                   # v6 tone recipe
├── _generate.py                 # palette compiler, no CIE construction
├── _cmaps.py                    # continuous compiler, no CIE construction
├── _discrete.py                 # frozen shipped indices; OKLab future policy
├── _gates.py                    # OKLab/Y topology plus independent CVD gates
├── _compatibility_metrics.py    # frozen independent comparison oracle
├── _comparison.py               # pure report model and HTML renderer
└── _build.py                    # compile → gate → exact-compat → atomic emit
scripts/
├── freeze_color_v5_compatibility.py  # one-way release-fixture extractor
└── compare_color_systems.py           # thin CLI
tests/
├── test_color_v6_compatibility.py
├── test_color_v6_tone.py
├── test_color_v6_architecture.py
├── test_color_v6_comparison.py
└── existing color/docs/visual suites
```

---

### Task 1: Freeze the Non-Circular v5 Compatibility Contract

**Files:**
- Create: `tests/test_color_v6_compatibility.py`
- Create: `scripts/freeze_color_v5_compatibility.py`
- Create:
  `docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/color_v5_compatibility.json`

**Interfaces:**
- Consumes: git literal sources at baseline commit `12d16bac`.
- Produces: schema `dartwork-mpl.color-compatibility/v1` with all 18 exact
  surfaces listed under Global Constraints, including every valid discrete
  result (every multi-hue `(name, n=1..8)` LUT index and hex row) and all 892
  vendor token name → hex values.

- [x] **Step 1: Write the manifest contract test**

The test module defines its own `COMPAT_PATH`, JSON-loading `v5_compat`
fixture, and both completeness helpers below; no implicit `conftest.py` API is
assumed.

```python
def test_v5_manifest_is_complete(v5_compat: dict[str, object]) -> None:
    inventory = v5_compat["inventory"]
    assert inventory == {
        "palette_positions": 200,
        "cycle_positions": 16,
        "cmap_positions": 11008,
        "qualitative_families": 13,
        "families": 56,
        "registered_colormaps": 99,
        "dc_tokens": 380,
        "vendor_tokens": 892,
    }
    assert v5_compat["canonical_hashes"]["cmaps256"] == (
        "e026ce047dd8a186299b2857e3d8c81f2b2bc4b7249df37f35b7c0093c5240c1"
    )
    assert len(v5_compat["taxonomy"]) == 56
    assert len(v5_compat["registrations"]) == 99
    assert_all_exact_surfaces_have_canonical_hashes(v5_compat)
    assert_all_valid_discrete_forms_are_frozen(v5_compat)
```

- [x] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_color_v6_compatibility.py -q`

Expected: FAIL because the fixture asset does not exist.

- [x] **Step 3: Implement the extractor and frozen asset**

The extractor must use `git show <commit>:<path>`, `ast.parse`, and
`ast.literal_eval` for generated/curated literals. For values that v5 computes
at runtime (notably multi-hue discrete indices and discovery metadata), it
must export the pinned commit to a disposable `git archive` directory and run
that checkout in an isolated subprocess; it must never import modules from the
candidate worktree. It must serialize with:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    allow_nan=False,
    indent=2,
    sort_keys=True,
) + "\n"
```

It must reject any source whose raw SHA-256 differs from the accepted spec and
must require an explicit `--baseline-commit` argument. Run it once against
`12d16bac` to create the tracked asset.

- [x] **Step 4: Verify GREEN and immutability**

Run:
`uv run pytest tests/test_color_v6_compatibility.py -q`

Expected: PASS. A second extractor run produces byte-identical JSON.

- [x] **Step 5: Review checkpoint (commit deferred by policy)**

Review only the extractor, test, and asset. Commit checkpoint:
`git commit -m "test: freeze color v5 compatibility contract"`.

---

### Task 2: Build the Side-by-Side JSON/HTML Comparator Before Migration

**Files:**
- Create: `src/dartwork_mpl/_colors/_catalog.py`
- Create: `src/dartwork_mpl/_colors/_compatibility_metrics.py`
- Create: `src/dartwork_mpl/_colors/_comparison.py`
- Create: `scripts/compare_color_systems.py`
- Create: `tests/test_color_v6_comparison.py`
- Create: `docs/color_system/validation.md`
- Create:
  `docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/color_v5_quality.json`

**Interfaces:**
- `CatalogSnapshot` — frozen value object for every exact compatibility surface
- `load_v5_snapshot() -> CatalogSnapshot`
- `compile_candidate_snapshot() -> CatalogSnapshot`
- `compare_catalog(baseline: CatalogSnapshot, candidate: CatalogSnapshot)
  -> ComparisonReport`
- `ComparisonReport.to_json() -> str`
- `render_comparison_html(report: ComparisonReport) -> str`
- CLI: `scripts/compare_color_systems.py --output PATH [--check]`; `--check`
  still writes ignored JSON/HTML artifacts atomically so a clean CI runner can
  upload them, then exits `0` for `passed: true`, `1` for a completed failing
  comparison, and `2` for invalid reference vectors, serialization, or I/O
  failure.

The comparator process exit code is the authority for the current invocation.
`report.json` is a completed-run gate record and last-write evidence, not proof
of the current invocation from file presence alone. It is written last for
completed exit-`0` and exit-`1` runs; exit `2` produces no trustworthy new
record after argument parsing has selected and invalidated the old marker.

- [ ] **Step 1: Write failing exact and mutation tests**

```python
def test_current_catalog_matches_frozen_v5_exactly() -> None:
    report = compare_catalog(load_v5_snapshot(), compile_candidate_snapshot())
    assert report.passed is True
    assert report.total_hex_mismatches == 0


def test_comparator_reports_a_single_lut_mutation() -> None:
    candidate = compile_candidate_snapshot()
    aurora = list(candidate.cmaps_256["aurora"])
    aurora[127] = "#000000"
    mutated = dataclasses.replace(
        candidate,
        cmaps_256={**candidate.cmaps_256, "aurora": tuple(aurora)},
    )
    report = compare_catalog(load_v5_snapshot(), mutated)
    assert report.passed is False
    assert report.cmaps_256["aurora"].mismatch_count == 1
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_color_v6_comparison.py -q`

Expected: FAIL because `_comparison` does not exist.

- [ ] **Step 3: Implement immutable snapshot/report value objects**

Use frozen dataclasses with explicit typed fields. Put the independent
published-reference conversion/CIEDE/CVD implementation in
`_compatibility_metrics.py`; pin its source hash and passed reference vectors
in the separate `color_v5_quality.json`. Compute every raw per-asset quality
baseline by applying that oracle to the immutable v5 literal snapshot before
any compiler migration. Never add the later oracle hash to the already-frozen
Task 1 manifest. The comparison must record
inventory, old/new hex, mismatch indices, ΔEOK, ΔE00, ΔY, contrast, CVD
summaries, source hashes, and sorted violations. Numeric summaries include
`min`, `p05`, `p50`, `p95`, `max`, and `mean`; decisions use unrounded floats.
Exact comparison covers all 18 surfaces: palette, cycles, 43×256 LUTs,
curated/manual rows, diverging canonicals, semantic and dark-theme coordinates
and resolved colors, every frozen forward/reverse discrete result and
multi-hue index row, taxonomy, forward/reverse registration names, typing
literals, MCP discovery metadata, public inventory, and all 892 vendor token
name → hex values—not only the surfaces shown by the example mutation test.
`compile_candidate_snapshot()` must call `_generate.compile_palette()` and
`_cmaps.compile_cmaps()` from the live recipe. It must never read committed
`_generated.py`, otherwise a stale generated file could make the comparison
circular. It assembles all remaining surfaces explicitly: apply frozen v5/v6
indices to candidate LUTs for discrete forms; resolve semantic and dark tokens
against the candidate palette/cycles; derive taxonomy and forward/reverse
registration names from candidate names; and derive typing/MCP discovery
payloads from their live declarative sources. Curated/manual literals may be
read directly because they are not generated. No candidate surface may be
obtained by importing `_generated.py` through `_semantic`, `_families`,
`_discrete`, or `_register`.

For typing, `_catalog.py` provides a pure
`build_typing_payload(candidate, vendor_names)` that combines candidate `dc.*`
names with vendor names parsed from their stable literal sources and derives
candidate forward/reverse cmap literals. `scripts/generate_typing.py` is later
refactored to consume the same builder. MCP exactness means discovery identity
(tool/resource/template/prompt names and URIs), not prose returned by a tool;
derive it by AST/source scanning the decorator declarations without importing
the server or color registries. Store these two payloads as explicit
`CatalogSnapshot` fields.

The repository CLI must load this source-only compiler through a unique private
namespace alias rooted at `_colors/`, not through canonical `dartwork_mpl`
package initialization. The isolated audit process may load matplotlib's color
math dependency while the legacy compiler still uses `Color`, but it must not
load `_generated`, `_loader`, `_register`, `_semantic`, `_families`, or
`_discrete`, and it must not mutate named-color or colormap registries. Verify
this in a clean subprocess, not only through source-AST inspection.

Gate all 43 direct previews. Sequential/multi-hue rows use
`step_cv <= min(asset_v5, 0.08)` plus direction/Y/L monotonicity.
Diverging/cyclic previews use generic count and degeneracy checks with
`step_cv <= asset_v5`; two frozen diverging previews already exceed `0.08`, so
forcing the absolute target would make the exact-parity baseline fail itself.
Their structural topology comes from full LUTs.

- [ ] **Step 4: Implement deterministic HTML**

Render inline CSS and SVG only. Include old/new/difference palette chips, 43
old/new/grayscale/CVD strips, OKLab-L/Y/ΔE profiles, diverging mirror panels,
cyclic seam windows, and an explicit PASS/FAIL summary. Do not read matplotlib
registry names; render literal arrays from the two snapshots.

- [ ] **Step 5: Verify GREEN and CLI determinism**

Run:

```bash
uv run pytest tests/test_color_v6_comparison.py -q
uv run python scripts/compare_color_systems.py --output build/color-system-comparison --check
uv run python scripts/compare_color_systems.py --output build/color-system-comparison --check
```

Expected: tests PASS, `report.json` has `passed: true`, and `--check` exits 0
on both runs with byte-identical `report.json` and `index.html`. A single
candidate mutation produces both artifacts and exits 1; an invalid oracle
reference exits 2. These artifacts live under ignored `build/`, not in tracked
source.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "feat: add color system comparison report"`.

---

### Task 3: Establish the Sole Conversion and Relative-Y Kernel

**Files:**
- Modify: `src/dartwork_mpl/_colors/_conversion.py`
- Modify: `src/dartwork_mpl/_colors/_metrics.py`
- Modify: `src/dartwork_mpl/_luminance.py`
- Modify: `tests/test_color_conversion.py`
- Modify: `tests/test_color_v5_metrics.py`

**Interfaces:**
- `relative_y_srgb_d65(rgb: Rgb) -> float`
- one canonical set of sRGB gamma, hex, linear-RGB, OKLab, and OKLCH helpers
- separately named WCAG luminance function using its rounded coefficients

- [ ] **Step 1: Write reference and delegation tests**

Pin sRGB primaries to modeled relative CIE Y
`(0.21267287873271212, 0.7151521284847872, 0.07217499278250072)`, assert
white is exactly 1, published OKLab primary vectors, gamma
breakpoints on both sides, hex round trips, non-finite rejection, and parity
between `_metrics` compatibility names and `_conversion`. Add a gray-CVD test
that proves input and neutral output have the same modeled relative CIE Y.

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_color_conversion.py tests/test_color_v5_metrics.py -q`

Expected: new relative-Y/delegation tests FAIL because conversion math is still
duplicated and no modeled-relative-CIE-Y kernel exists.

- [ ] **Step 3: Consolidate conversion math**

Make `_conversion.py` the sole implementation. Have `_metrics.oklab_from_rgb`,
hex conversion, and gamma conversion delegate to it; keep CIELAB conversion
private to CIEDE2000 validation. Change `cvd_rgb(..., "gray")` to generate a
neutral sRGB value directly from input modeled relative CIE Y. Keep WCAG rounded
coefficients under a separately named function in top-level `_luminance.py`.
Preserve current arithmetic order wherever exact output depends on it.

- [ ] **Step 4: Verify GREEN and baseline report**

Run:

```bash
uv run pytest tests/test_color_conversion.py tests/test_color_v5_metrics.py -q
uv run python scripts/compare_color_systems.py --output build/color-system-comparison --check
```

Expected: tests PASS and total hex mismatch remains 0.

- [ ] **Step 5: Review checkpoint**

Commit checkpoint:
`git commit -m "refactor: centralize color conversion and relative y"`.

---

### Task 4: Centralize Gamut Policy and Add the Tone Solver

**Files:**
- Create: `src/dartwork_mpl/_colors/_gamut.py`
- Create: `src/dartwork_mpl/_colors/_tone.py`
- Modify: `src/dartwork_mpl/_colors/_color.py`
- Modify: `tests/test_color_eq_gamut.py`
- Create: `tests/test_color_v6_gamut.py`
- Create: `tests/test_color_v6_tone.py`

**Interfaces:**
- `SRGB_GAMUT_POLICY: GamutPolicy`
- `map_oklch_to_srgb(L, C, hue_deg, policy=SRGB_GAMUT_POLICY) -> MappedColor`
- `max_chroma_at_lightness(
  L, hue_deg, policy=SRGB_GAMUT_POLICY) -> float`
- `relative_y(value: float) -> RelativeY`
- `neutral_tone(value: float) -> NeutralTone`
- `tone_from_relative_y(value: float) -> NeutralTone`
- `relative_y_from_tone(value: NeutralTone) -> RelativeY`
- `solve_oklch_l_for_relative_y(hue_deg, chroma, target_y) -> SolvedColor`
- `render_oklch_at_tone(hue_deg, chroma, tone, luminance_lock) -> Rgb`
- `max_chroma_at_tone(hue_deg, tone) -> float`

- [ ] **Step 1: Write policy, boundary, grid, and solver tests**

Test fixed gamut values `iterations=24`, `tolerance=1e-6`,
`max_chroma_upper=0.40`, L/h preservation, non-increasing chroma, finite
output, and a hue×chroma×tone grid. Pin current boundary results for
representative red/yellow/blue/violet samples. Add:

```python
@pytest.mark.parametrize("value", [-math.inf, -0.1, 1.1, math.inf, math.nan])
def test_relative_y_rejects_non_finite_or_out_of_range(value: float) -> None:
    with pytest.raises(ValueError):
        relative_y(value)


def test_neutral_tone_round_trip() -> None:
    for value in (0.0, 0.05, 0.18, 0.5, 1.0):
        tone = tone_from_relative_y(value)
        assert relative_y_from_tone(tone) == pytest.approx(value, abs=1e-15)


def test_locked_oklch_solver_matches_target_y() -> None:
    solved = solve_oklch_l_for_relative_y(238.0, 0.165, relative_y(0.5**3))
    assert solved.achieved_y == pytest.approx(0.125, abs=5e-13)
    assert solved.residual == pytest.approx(0.0, abs=5e-13)
```

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_color_v6_gamut.py tests/test_color_v6_tone.py -q`

Expected: FAIL because `_gamut` and `_tone` do not exist.

- [ ] **Step 3: Move the existing gamut algorithm without arithmetic drift**

The new gamut module owns policy constants and raw conversion, and
`Color.to_rgb()` delegates to it. `max_chroma_at_lightness()` is only the
geometric boundary at an actual chromatic OKLCH L. All public internal hue
arguments use degrees; `_conversion` alone converts to radians. Pin the helper
search interval instead of leaving its result dependent on an implicit upper
bound:

```python
SRGB_GAMUT_POLICY = GamutPolicy(
    iterations=24,
    tolerance=1e-6,
    max_chroma_upper=0.40,
)
```

- [ ] **Step 4: Implement value types and the tone-level solver**

Use `NewType` for `RelativeY` and `NeutralTone`, validating constructor
functions, and a frozen `SolvedColor` with `rgb`, `oklab_l`, `mapped_chroma`,
`achieved_y`, and `residual`. The locked 40-step binary solve measures Y after
the named gamut mapping; unlocked rendering uses tone as actual OKLCH L. Pin:

```python
SHIPPED_TONE_POLICY = TonePolicy(
    luminance_search_iterations=40,
    max_chroma_tone_iterations=30,
    max_chroma_search_iterations=22,
    probe_chroma=0.04,
    max_chroma_upper=0.40,
    catalog_chroma_fraction=0.97,
)
```

`max_chroma_at_tone()` first performs the 30-step target-Y probe, then the
separate 22-step chroma search. Do not merge either with the 40-step luminance
solve; arithmetic drift can cross an 8-bit hex boundary.

- [ ] **Step 5: Verify GREEN and exact catalog parity**

Run:

```bash
uv run pytest tests/test_color_eq_gamut.py tests/test_color_v6_gamut.py \
  tests/test_color_v6_tone.py -q
uv run python scripts/compare_color_systems.py --output build/color-system-comparison --check
```

Expected: PASS, solver drift from the frozen solver stays within `5e-12` RGB
and `5e-13` achieved Y, and catalog mismatch remains 0. Absolute target-Y
residual must be no worse than the frozen residual rather than globally below
`5e-13`: the compatibility gamut boundary is slightly discontinuous and the
frozen dense family path already reaches about `1.05e-8`. Handle exact
`Y=0/1` as black/white with zero residual.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "refactor: add gamut and neutral-tone kernels"`.

---

### Task 5: Migrate the Recipe SSOT from L* to Neutral Tone

**Files:**
- Modify: `src/dartwork_mpl/_colors/_recipe.py`
- Create: `src/dartwork_mpl/_colors/_ssot.py`
- Create:
  `src/dartwork_mpl/asset/color/color_v6_ssot.json`
- Create: `scripts/build_color_v6_ssot.py`
- Modify: `tests/test_color_v5_recipe.py`
- Create: `tests/test_color_v6_architecture.py`

**Interfaces:**
- `FamilyParams.tone_floor: float`
- `TONE_TOP`, `GRAY_TONE_FLOOR`, `tone_floor_k3`
- v6 JSON values are already migrated 0–1 tone values; production code has
  no legacy-L* conversion helper.

- [ ] **Step 1: Write failing v6 SSOT and import-boundary tests**

Parse `_recipe.py` with AST and assert it contains `tone_floor` rather than
`floor`, `TONE_TOP` rather than `L_TOP`, and no CIELAB-named recipe field.
Assert every tone value is finite and in `[0, 1]`. Task 6 extends the same
parameterized architecture test to `_generate.py` and `_cmaps.py`; Task 7
extends it to `_discrete.py`.

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_color_v5_recipe.py tests/test_color_v6_architecture.py -q`

Expected: FAIL on the missing v6 asset and current L*-named recipe fields.

- [ ] **Step 3: Transform the recipe values**

For the shipped values, transform once with
`(legacy_Lstar + 16) / (116 * cbrt(1.0000001))`; the denominator compensates
the raw legacy XYZ row's white sum so the normalized-Y solver preserves the
existing float RGB target, not only the same quantized hex.
Let `D = 116 * cbrt(1.0000001)`. Transform the Fourier constant term with
`(a0 + 16) / D` and every harmonic coefficient with `ak / D`. Rename
fields/constants/docstrings and change the derive grid from one L* unit to
`1 / D` tone. Do not round migrated tone values through the legacy decimal
grid; use the full-double tone grid so float parity is preserved.

- [ ] **Step 4: Emit and validate v6 SSOT**

Store recipe, metric provenance, exact hashes, CVD model-by-deficiency, gamut
policy, discrete indices, and the hash plus raw per-asset values copied from
Task 2's independently computed `color_v5_quality.json`. Candidate metrics are
reports, never baselines. Keep both v5 JSON files immutable and mark them as
compatibility/quality sources, not the live recipe SSOT. The canonical v6 JSON
is a packaged asset so installed builds and repository builds read the same
bytes. `_ssot.py` is the only production accessor; `_recipe.py`, `_build.py`,
and candidate catalog compilation must not copy a second index/recipe literal.
Also store frozen per-row contracts for palette, direct-32, full-256, cycles,
curated rows, dark cycle, and every forward discrete form: canonical row hash,
count, unique count, adjacent-duplicate count, and maximum run length. Derive
these contracts only from pinned v5 literals. Existing quantized LUTs contain
intentional asset-specific duplicates, so there is no global all-unique rule.
The generator reads only raw-SHA-pinned v5 inputs, writes deterministic finite
JSON, and a second run must be byte-identical.

- [ ] **Step 5: Verify GREEN**

Run:
`uv run pytest tests/test_color_v5_recipe.py tests/test_color_v6_architecture.py -q`

Expected: all selected recipe/JSON/architecture tests PASS.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "refactor: migrate color recipe to neutral tone"`.

---

### Task 6: Migrate Palette and Continuous Colormap Construction

**Files:**
- Modify: `src/dartwork_mpl/_colors/_generate.py`
- Modify: `src/dartwork_mpl/_colors/_cmaps.py`
- Modify: `tests/test_color_v5_generate.py`
- Modify: `tests/test_color_v5_cmaps_single.py`
- Modify: `tests/test_color_v5_cmaps_catalog.py`
- Modify: `tests/test_color_v6_architecture.py`

**Interfaces:**
- `compile_palette(*, luminance_lock: bool = True)`
- `compile_cmaps(palette, n=256, *, luminance_lock: bool = True)`
- `max_chroma_at_tone(hue_deg, tone) -> float`

- [ ] **Step 1: Replace L* assertions with tone/Y assertions in tests**

Assert achieved-Y drift from the frozen solver `<=5e-13`, RGB drift from the
frozen solver `<=5e-12`, absolute target residual no worse than its frozen
value, exact compiled palette/cmap hashes, and direct-OKLCH unlocked output
being available only through an explicit keyword.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_color_v5_generate.py \
  tests/test_color_v5_cmaps_single.py tests/test_color_v5_cmaps_catalog.py -q
```

Expected: FAIL because the compiler still accepts L* endpoints.

- [ ] **Step 3: Route every swatch through `_tone`**

Use tone endpoints in family, gray, sequential, multi-hue, diverging, hue,
halo, and corona recipes. Preserve arithmetic order and dense OKLab arc-length
resampling. Replace the blue/red averaged L* endpoint with the mean of the two
endpoint neutral tones derived from relative Y.

- [ ] **Step 4: Verify exact GREEN**

Run:

```bash
uv run pytest tests/test_color_v5_generate.py \
  tests/test_color_v5_cmaps_single.py tests/test_color_v5_cmaps_catalog.py \
  tests/test_color_v6_architecture.py -q
uv run python scripts/compare_color_systems.py --output build/color-system-comparison --check
```

Expected: all tests PASS; palette mismatch 0; 43×256 mismatch 0;
modeled-relative-CIE-Y drift 0 at hex precision.

- [ ] **Step 5: Add unlocked explanatory output to comparison report**

Compile 32-stop direct-OKLCH variants with `luminance_lock=False`. Display
them as diagnostics, never as the shipped candidate, and record their
ΔE/Y/topology differences separately in JSON.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "refactor: compile colors from OKLab neutral tone"`.

---

### Task 7: Remove CIELAB/CIEDE2000 from Discrete Construction

**Files:**
- Modify: `src/dartwork_mpl/_colors/_discrete.py`
- Modify: `src/dartwork_mpl/_colors/_build.py`
- Regenerate: `src/dartwork_mpl/_colors/_generated.py`
- Modify: `tests/test_discrete_forms.py`
- Modify: `tests/test_colormap_explorer_taxonomy.py`
- Modify: `tests/test_color_v6_architecture.py`

**Interfaces:**
- `MULTI_HUE_DISCRETE_INDICES[name][n] -> tuple[int, ...]`
- CIEDE2000 floors remain validation constants, not selection objectives.

- [ ] **Step 1: Pin every shipped discrete index**

Write a parameterized test for nine multi-hue maps and every `n=1..8` that
asserts exact manifest indices and hex values. Add exact tests for sequential,
diverging, cyclic, qualitative, reverse, and max-n behavior. Also assert that
`_generated.py` exposes `MULTI_HUE_DISCRETE_INDICES` and extend the AST
architecture test to reject CIELAB/CIEDE2000/CVD imports and calls in
`_discrete.py`; these assertions provide RED even though the old optimizer
already happens to reproduce the frozen hex rows.

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_discrete_forms.py tests/test_color_v6_architecture.py -q`

Expected: exact rows may already pass, but the generated-table and architecture
assertions FAIL because runtime still optimizes with CIEDE2000.

- [ ] **Step 3: Replace runtime optimization with frozen indices**

Delete CIELAB candidate bands and ordered-clique selection from shipped paths.
Teach `_build.py` to emit the frozen choices as the literal
`MULTI_HUE_DISCRETE_INDICES` table in `_generated.py`; `_discrete.py` reads
that table and never recomputes shipped choices. Keep ΔE00/CVD computation only
in validation tests and gates. `_build.py` obtains indices through the single
packaged-v6-SSOT accessor, never a copied Python literal. Compute generic vivid
diagnostics with OKLCH C and neutral tone, but preserve the nine shipped
explorer cutoffs as explicit v6-SSOT presentation metadata; the natural OKLCH
rule changes seven of them. New families use the generic rule and independent
validation rather than inheriting those compatibility pins.

Update `_catalog.compile_candidate_snapshot()` to read the candidate v6 index
manifest through the same accessor. Its current temporary use of v5 baseline
indices must be removed, or a broken candidate manifest would be masked by the
comparison report. The baseline snapshot alone may read v5 indices.

- [ ] **Step 4: Verify GREEN and architecture boundary**

Run:

```bash
uv run pytest tests/test_discrete_forms.py \
  tests/test_colormap_explorer_taxonomy.py \
  tests/test_color_v6_architecture.py -q
```

Expected: PASS and no construction module imports CIELAB/CIEDE2000/CVD.

- [ ] **Step 5: Review checkpoint**

Commit checkpoint:
`git commit -m "refactor: freeze discrete color selections"`.

---

### Task 8: Promote Full-LUT and Non-Regression Gates into the Build

**Files:**
- Modify: `src/dartwork_mpl/_colors/_gates.py`
- Modify: `src/dartwork_mpl/_colors/_build.py`
- Modify: `tests/test_color_v5_gates.py`
- Modify: `tests/test_color_v5_build.py`
- Modify: `tests/test_family_invariants.py`

**Interfaces:**
- `evaluate_catalog(
  candidate: CatalogSnapshot,
  quality_baseline: Mapping[str, object]) -> GateReport`
- `GateViolation(asset, metric, observed, allowed, rule, message)` — frozen,
  sortable value object with finite raw numeric fields
- `GateReport.violations: tuple[GateViolation, ...]`
- build sequence: compile32/256 → full gate → frozen exact comparison → atomic
  `_generated.py` emit.
- `main(argv: Sequence[str] | None = None) -> int` with `--output PATH` for an
  injected generated-file target and optional `--check`; production default is
  the tracked `_generated.py`.

- [ ] **Step 1: Write mutation tests for each missing gate**

Mutate one sequential direction, one Y order, one diverging mirror, one arm,
one cyclic seam, one duplicate run, one cycle CVD floor, and one exact hex.
Each mutation must produce a named violation with observed and allowed values.

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_color_v5_gates.py tests/test_color_v5_build.py -q`

Expected: FAIL because current build checks only direct-32 weak gates.

- [ ] **Step 3: Implement OKLab/Y topology gates**

Palette gates actual OKLab L, Y, and per-family step CV. Sequential/multi-hue
gates expected direction, full-256 Y/OKLab topology, span, CV, uniqueness, and
CVD diagnostics. Diverging gates center, arm direction, mirror Y, endpoints,
arc ratio, and center duplicate. Cyclic gates full seam ΔEOK/ΔE00/ratio,
uniqueness, hue Y-spread, and twilight topology. Threshold on raw floats and
compare every asset with its frozen baseline.

Gate direct-32 and full-256 CV for all 43 continuous maps. Ordered
sequential/multi-hue direct rows use `min(asset_v5, 0.08)`; non-ordered direct
rows and every full-256 row use their asset baseline because frozen
`gray_blue`/`gray_red` direct previews already exceed the absolute target.
Direction, Y/L monotonicity, and span remain specific to
sequential/multi-hue; diverging/cyclic rows use their topology rules.

Use the per-row v6-SSOT contracts rather than a global uniqueness floor.
Require unique count and adjacent-duplicate behavior to be no worse than the
asset's frozen baseline, and maximum run length to be no larger. A matching
row hash may reuse its frozen metrics; changed rows must be recomputed through
the independent oracle. Compile the candidate snapshot exactly once. Promote
the raw gate decision implementation to `_gates.py` so the comparison report
adapts the same `GateViolation` results instead of duplicating policy.

- [ ] **Step 4: Make build non-circular and atomic**

Load the frozen v5 asset for exact comparison. Refuse emission on any mismatch
or gate violation. Render the complete expected file in memory before touching
the target. Write only through a unique sibling `mkstemp`, flush/fsync, and
`os.replace`, with unconditional temporary cleanup. Add a `--check` mode that
does not create directories, targets, or temporary files. Pin CLI exit
semantics: `0` means all gates, compatibility, and generated-file freshness
pass; `1` means a quality or exact compatibility failure; `2` means the
candidate is valid but the tracked generated file is missing or stale.

Add subprocess-level tests for all three exits using `--output` temporary
targets: valid+fresh → 0, contract failure → 1, valid+stale → 2. Snapshot the
temporary target before and after every `--check` case to prove it never writes.

- [ ] **Step 5: Verify GREEN and generated-file stability**

Run:

```bash
uv run pytest tests/test_color_v5_gates.py tests/test_color_v5_build.py \
  tests/test_family_invariants.py -q
uv run python -m dartwork_mpl._colors._build --check
cp src/dartwork_mpl/_colors/_generated.py /private/tmp/generated.before.py
uv run python -m dartwork_mpl._colors._build
cmp /private/tmp/generated.before.py src/dartwork_mpl/_colors/_generated.py
```

Expected: tests PASS, build gates green, `cmp` exits 0.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "feat: enforce full color catalog gates"`.

---

### Task 9: Update Current Documentation and Explorer Metrics

**Files:**
- Modify: `docs/color_system/design-rationale.md`
- Modify: `docs/color_system/color-class.md`
- Modify: `docs/color_system/colors.md`
- Modify: `docs/color_system/colormaps.md`
- Modify: `docs/color_system/palettes.md`
- Modify: `docs/usage_guide/colors.md`
- Modify: `docs/api/color.rst`
- Modify: `docs/index.md`
- Modify: `docs/design_system/index.md`
- Modify: `docs/_static/dartwork-discrete-palette-rationale.md`
- Modify: `docs/_static/custom.js`
- Modify: `docs/_static/custom.css`
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`, `llms.txt`
- Modify metadata comments only: `src/dartwork_mpl/_colors/_curated.py`
- Modify comment only:
  `src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle`
- Modify: `src/dartwork_mpl/validate/_checks/grayscale_safety.py`
- Modify naming only: `src/dartwork_mpl/diagnostics/_colors.py`
- Modify: `docs/_static/scripts/build_colormap_explorer.py`
- Modify: `docs/_static/scripts/build_categorical_explorer.py`
- Regenerate: `docs/_static/colormap_explorer.html`
- Regenerate: `docs/_static/categorical_explorer.html`
- Modify: related docs count/float/taxonomy tests.

- [ ] **Step 1: Write failing terminology and explorer tests**

Require primary metric keys `oklab_l`, `relative_y`, `delta_e_ok`; validation
keys `delta_e_00`, `cvd_model`; exact counts 19/20/43/13/56/107; correct
Machado protan/deutan and BVM tritan provenance; and no current-page claim
that gamut mapping preserves CIELAB L*. Pin grayscale-safety naming to
modeled-relative-CIE-Y ordering plus ΔEOK separation so UI labels cannot
silently retain the old CIELAB meaning. Preserve existing grayscale detail
keys as deprecated aliases while adding explicit `relative_y`, `delta_y`, and
`delta_e_ok` fields;
do not silently reinterpret a public key. Identify the diagnostics helper that
weights gamma-encoded channels as a text-brightness heuristic rather than
calling it physical or WCAG relative luminance; keep its behavior unchanged.

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_docs_float_claims.py tests/test_docs_count_claims.py \
  tests/test_colormap_explorer_taxonomy.py \
  tests/test_palette_family_taxonomy.py -q
```

Expected: FAIL on current hybrid terminology, wrong counts, and explorer
payload.

- [ ] **Step 3: Rewrite the live rationale and catalog prose**

Explain OKLab/OKLCH construction, the modeled-relative-CIE-Y output contract,
and independent validation exactly as the ADR.
Correct qualitative counts, CVD model provenance, overclaims of perfect
uniformity, the `dc.red0` green/teal/lime typo, stale repository tree, and
MCP counts from the current AGENTS contract. Update the color-class page,
discrete rationale, custom explorer labels/styles, curated metadata, and the
dark-theme cycle comment without changing any public/manual hex literal.
The actual dark asset is `asset/mplstyle/theme-dark.mplstyle`; there is no
`asset/theme/dark.yaml`.

- [ ] **Step 4: Update explorer builders**

Use OKLab ΔE for “Uniform”, actual OKLab L and relative Y profiles, classify
only `hue` as isoluminant when its gate passes, show halo/corona as dark-center
cyclic maps, and label ΔEOK vs ΔE00 explicitly. The categorical builder reads
model provenance from v6 SSOT instead of claiming all Brettel. Add `--check`
to both builders: render to memory/a temporary file, compare bytes with the
tracked HTML, never mutate the tracked output, and return nonzero on drift.

- [ ] **Step 5: Regenerate and verify GREEN**

Run:

```bash
uv run python docs/_static/scripts/build_categorical_explorer.py
uv run python docs/_static/scripts/build_colormap_explorer.py
uv run python docs/_static/scripts/build_categorical_explorer.py --check
uv run python docs/_static/scripts/build_colormap_explorer.py --check
uv run pytest tests/test_docs_float_claims.py tests/test_docs_count_claims.py \
  tests/test_colormap_explorer_taxonomy.py \
  tests/test_palette_family_taxonomy.py -q
```

Expected: generated HTML is byte-stable on a second run and tests PASS.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "docs: explain OKLab color construction"`.

---

### Task 10: Regenerate Theory Assets and Remove Stale Color Generators

**Files:**
- Modify: `docs/color_system/generate_theory_figures.py`
- Regenerate: `docs/color_system/theory_figures/theory_1_*.svg` through
  `theory_10_*.svg`
- Modify: `docs/color_system/generate_assets.py`
- Delete: `docs/_static/scripts/gen_palettes.py`
- Delete: `docs/_static/scripts/dm_palettes_gen.json`
- Modify dependency set with `uv remove --group dev colorspacious` after the
  repository search proves there is no remaining live consumer.
- Modify: `src/dartwork_mpl/asset/prompt/01-policy.md`
- Modify: `src/dartwork_mpl/asset/prompt/00-index.md`
- Modify: `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`
- Modify: `src/dartwork_mpl/mcp/prompts.py`
- Modify: `src/dartwork_mpl/mcp/resources.py`
- Modify: `src/dartwork_mpl/mcp/tools.py`
- Modify: `docs/integrations/mcp_server.md`
- Modify: `scripts/generate_typing.py`
- Verify/regenerate: `src/dartwork_mpl/_typing.py`
- Regenerate: `src/dartwork_mpl/asset/prompt/_index.json`, `llms-full.txt`
- Modify: applicable docs examples, prompt templates, and their mirrored
  advanced-gallery sources so copies remain byte-equivalent.
- Add superseded banners only: v5 design spec and v5 implementation plan.
- Add metric-model addendum only: Model B API spec; do not mark it superseded.
- Modify: theory/determinism/prompt parity tests.

- [ ] **Step 1: Write failing asset provenance and parity tests**

Require generator-relative output paths, no personal `/private/tmp` preview
path, all 20 single-hue and 13 qualitative families, neutral-tone/Y labels,
and byte equality between a temporary regeneration and tracked SVG/HTML.

- [ ] **Step 2: Verify RED**

Run:
`uv run pytest tests/test_docs_theory_figures.py tests/test_docs_asset_determinism.py tests/test_prompt.py -q`

Expected: FAIL on stale labels/counts or missing byte-parity checks.

- [ ] **Step 3: Rewrite theory figures around the accepted model**

Replace the “L* is logarithmic” figure with neutral tone vs modeled relative
CIE Y;
replace L* trajectory/mirror plots with actual OKLab L plus Y overlays; retain
CIEDE2000 only in independent CVD/compatibility panels. Use project figure
rules (`dm.style.use`, `dm.figsize`, `dm.simple_layout`, `dm.save_formats`).
Add generator-relative `--output-dir` and a non-writing `--check` that compares
temporary output bytes against every tracked theory asset.

- [ ] **Step 4: Retire stale generation and synchronize agent-facing prose**

Remove the disconnected colorspacious generator/JSON, delete unused duplicate
OKLab helper code from `generate_assets.py`, update prompts/examples without
changing public tool/resource/prompt counts, and update MCP resource/tool prose
without changing names or schemas. Regenerate mirrored prompt template metadata
through the existing Sphinx hook rather than hand-editing `_index.json`; run
`scripts/generate_typing.py --check` after implementing that non-writing mode,
and require `_typing.py` to remain byte-identical because no public name
changes. Regenerate `llms-full.txt` from
the repository generator, not by manual concatenation. Historical v5 design
documents receive only a superseded banner. The Model B spec remains current
for the public `Color` API and receives only a note about the new metric split.

- [ ] **Step 5: Regenerate and verify GREEN**

Run:

```bash
PYTHONPATH=src uv run python docs/color_system/generate_theory_figures.py
PYTHONPATH=src uv run python docs/color_system/generate_theory_figures.py --check
uv run python scripts/generate_typing.py --check
uv run pytest tests/test_docs_theory_figures.py \
  tests/test_docs_asset_determinism.py tests/test_prompt.py \
  tests/test_template_body_parity.py tests/test_mcp.py \
  tests/test_typing_parity.py -q
```

Expected: tests PASS and a second regeneration produces no diff.

- [ ] **Step 6: Review checkpoint**

Commit checkpoint:
`git commit -m "docs: regenerate OKLab color theory assets"`.

---

### Task 11: Wire Drift Checks into CI and Complete the Public Comparison Space

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/docs.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `docs/_ext/build_hooks.py`
- Modify: `tests/test_drift.py`
- Modify: `tests/test_docs_asset_inventory.py`
- Modify: `docs/color_system/validation.md`

- [ ] **Step 1: Write failing drift tests**

Assert that the build `--check`, comparator `--check`, explorer builders
`--check`, theory temporary parity, and v6 SSOT parity are all represented by
tests or CI commands across CI/docs/release paths. Assert that the obsolete
`dc_palettes.json` CI example is absent and the comparator report is uploaded
on success or failure.

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/test_drift.py tests/test_docs_asset_inventory.py -q`

Expected: FAIL because current CI does not cover these generated surfaces.

- [ ] **Step 3: Add check-only commands**

CI runs the compiler and comparator without mutating tracked files, then runs
the docs generators in check mode; release cannot publish a stale or
incompatible catalog. `validation.md` documents the current comparator process
exit code as invocation authority, `report.json` as the completed-run gate
record and last-write evidence, the exact local build command, and the CI
artifact name. Do not add a broken repository link into ignored `build/`; the
HTML is a local/CI build artifact unless a later task publishes it deliberately.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_drift.py tests/test_docs_asset_inventory.py -q
uv run python -m dartwork_mpl._colors._build --check
uv run python scripts/compare_color_systems.py \
  --output build/color-system-comparison --check
```

Expected: PASS with no tracked-file changes.

- [ ] **Step 5: Review checkpoint**

Commit checkpoint:
`git commit -m "ci: verify color system generated artifacts"`.

---

### Task 12: Full Verification, Handbook Guard, and Completion Audit

**Files:**
- Review all changed files; no new production behavior in this task.
- Produce: `build/color-system-comparison/index.html`
- Produce: `build/color-system-comparison/report.json`

- [ ] **Step 1: Run focused color and compatibility suites**

```bash
uv run pytest tests/test_color_* tests/test_family_invariants.py \
  tests/test_discrete_forms.py tests/test_theme_dark_cycle.py -q
```

Expected: all selected tests PASS.

- [ ] **Step 2: Run formatting, typing, and complete tests**

Use `coding:verify` to select the repository-native commands, including Ruff,
mypy, full `tests/`, docs build, and visual tests. The minimum full-suite
command is:

```bash
uv run pytest tests/ -q --no-cov
```

Expected: no regression from the baseline `2613 passed, 2 skipped` except
intentional new tests increasing the pass count.

- [ ] **Step 3: Verify generated and visual determinism**

Run every generator twice, confirm no second-run diff, run Sphinx with
warnings as errors, and inspect the comparison HTML plus palette/cmap visual
baselines. Confirm `report.json` has mismatch 0 and `passed: true`.

- [ ] **Step 4: Run architecture and spec coverage audits**

Use `architecting:handbook-guard` and `architecting:review`. Search production
construction modules for forbidden CIELAB/CIEDE/CVD imports and search current
public docs for superseded hybrid claims. Historical v5 documents may retain
old content only behind an explicit superseded banner.

- [ ] **Step 5: Inspect both worktrees**

Confirm the feature worktree contains only intended changes. Confirm the main
worktree retains every pre-existing user SVG/HTML and advanced PNG/PDF change.
Do not merge, cherry-pick, commit, or delete a worktree without user approval.

- [ ] **Step 6: Final review checkpoint**

Present the diff by subsystem, exact compatibility evidence, gate report,
comparison artifact paths, and any remaining risk. Commit checkpoint after
approval:
`git commit -m "refactor: center color system on OKLab"`.

## Plan Self-Review

- Spec §§1–14 map to Tasks 1–12; no accepted deliverable lacks a task.
- Construction/validation separation is enforced by Task 5/7 architecture
  tests and re-audited in Task 12.
- Exact manual/generated compatibility is established before migration in
  Task 1/2 and checked after every core task.
- Modeled-relative-CIE-Y conversion, solver equivalence, and hex parity are
  tested in Tasks 3/4/6 respectively.
- Side-by-side JSON/HTML exists before migration and is finalized in Task 11.
- Docs, explorers, theory assets, prompts, MCP prose, and stale generators are
  explicitly covered in Tasks 9–11.
- Type/interface names are consistent: `RelativeY`, `NeutralTone`,
  `SolvedColor`, `ComparisonReport`, and `GateReport` are defined once and
  consumed by later tasks.
- No task asks an implementer to invent an unspecified error policy, metric,
  threshold, artifact location, or verification command.
