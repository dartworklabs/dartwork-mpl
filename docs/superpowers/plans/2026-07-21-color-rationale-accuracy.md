# Color Rationale Accuracy Implementation Plan

> **Status: historical record — do not execute.**
> The unchecked steps, damaged-worktree assumptions, absolute paths, metric
> wording, and commit commands below describe the 2026-07-21 implementation
> session only. They are preserved for provenance; current source, approved
> specifications, tests, and the active goal govern current work.
>
> **Everything below—including the “For agentic workers” directive, all
> checkboxes, and every command block—is historical quotation only; do not
> follow or execute it.**

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public color-system rationale scientifically bounded,
designer-defensible, and faithful to the shipped compiler without changing a
single generated color, LUT entry, public API, or registration.

**Architecture:** Treat public claims as one of four evidence tiers: colorimetric
fact, project compatibility contract, design/art-direction choice, or measured
catalog result. Documentation contract tests mechanically pin counts, measured
floats, and prohibited overclaims. The theory-figure generator computes its
displayed statistics from the same live records that it plots, so prose and
figures cannot retain stale literals.

**Tech Stack:** MyST Markdown/Sphinx, Python 3.10+, pytest, NumPy, matplotlib,
dartwork-mpl's existing color kernels and documentation generators.

**Approved design:**
[`2026-07-21-color-rationale-accuracy-design.md`](../specs/2026-07-21-color-rationale-accuracy-design.md)

## Global constraints

- Work from `/private/tmp/dartwork-mpl-oklab` on
  `refactor/oklab-color-system`.
- The worktree's `.git` file and many tracked files were removed by external
  temporary-directory cleanup. Use the surviving metadata explicitly:

  ```bash
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab status --short --branch
  ```

- Do not restore all deleted paths, copy the dirty primary worktree over this
  worktree, or invent the missing untracked v6 authority/compiler files. If a
  command needs a missing file, report that verification lane as blocked while
  continuing independent source and prose work.
- Preserve existing user changes. Stage only paths named by the current task.
- Keep prose in English and introduce specialist terms in plain language before
  relying on them.
- Do not edit generated palette data, recipe authority, LUTs, public runtime
  APIs, registrations, or exported counts.
- Use `DeltaEOK x 100` in ASCII-only test identifiers and `ΔEOK×100` in rendered
  prose where absolute units are discussed. Plain `ΔEOK` remains acceptable
  when only ranking or coefficient of variation is discussed.
- Cite only primary sources for standards/scientific claims: Ottosson's Oklab
  definition, CSS Color 4, WCAG 2.2, CIE 142/Sharma et al., Machado et al.
  (2009), and Brettel–Viénot–Mollon (1997).
- Every task follows red → green → focused review. A task-level commit is made
  only after the user approves the exact staged diff, per the repository git
  workflow.

## Execution preflight

- [ ] Confirm the branch and capture the current generated-color hash before
  touching any in-scope source:

  ```bash
  cd /private/tmp/dartwork-mpl-oklab
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab branch --show-current
  shasum -a 256 src/dartwork_mpl/_colors/_generated.py \
      > /tmp/dartwork-rationale-generated.before.sha256
  ```

  Expected branch: `refactor/oklab-color-system`. The hash file is the
  task-local invariant for palette hex values and continuous LUT bytes.

- [ ] Classify dynamic verification availability without mutating the tree:

  ```bash
  for path in \
      src/dartwork_mpl/asset/color/color_v6_ssot.json \
      src/dartwork_mpl/_colors/_tone.py \
      src/dartwork_mpl/_colors/_ssot.py \
      docs/conf.py \
      .pre-commit-config.yaml
  do
      test -e "$path" || echo "DYNAMIC_VERIFICATION_BLOCKED: $path"
  done
  ```

  Expected in the currently damaged worktree: one or more
  `DYNAMIC_VERIFICATION_BLOCKED` lines. This is an environment limitation, not
  a product failure. It does not block static tests, prose edits, or independent
  arithmetic over surviving records.

---

## Task 1: Pin the evidence-tier and metric-language contract

**Files:**

- Modify: `tests/test_docs_beginner_color_language.py`
- Modify: `tests/test_docs_float_claims.py`
- Modify: `docs/color_system/design-rationale.md`

- [ ] Add a rationale-specific contract test that requires the four evidence
  tiers and rejects the strongest misleading phrases. Keep usage-guide tests
  outside this task unchanged because the approved scope is the rationale and
  its directly listed adjacent pages.

  Add this shape to `tests/test_docs_beginner_color_language.py`:

  ```python
  def test_rationale_separates_fact_contract_choice_evidence_and_limits() -> None:
      text = _page("docs/color_system/design-rationale.md")
      for phrase in (
          "Design choice",
          "Implementation",
          "Evidence",
          "Limits",
          "modeled relative CIE Y calculated from nominal D65 sRGB",
          "not a measurement of a particular display",
          "100 times the raw Euclidean distance in Oklab",
          "specified foreground/background pair",
          "model-specific regression diagnostic",
      ):
          assert phrase in text

      for phrase in (
          "physical light output",
          "independent oracles",
          "accessibility oracle",
          "CIEDE2000 correctly fails",
      ):
          assert phrase not in text
  ```

- [ ] Tighten the existing four-ruler test so it requires these relationships,
  without falsely describing catalog `relative_y` and WCAG relative luminance
  as unrelated physical quantities:

  ```python
  required = (
      "OKLab and OKLCH are two coordinate views",
      "ΔEOK×100",
      "closely related decoded-sRGB Y-like calculations",
      "separately pinned coefficient conventions",
      "WCAG adds a pairwise contrast ratio",
  )
  ```

  Remove rationale assertions that require the words `physical Y`,
  `physical relative Y`, `independent oracle`, or an unqualified accessibility
  conclusion. Rename tests whose names encode those old claims.

- [ ] Run the new contract test alone and confirm it fails against the existing
  rationale:

  ```bash
  uv run pytest tests/test_docs_beginner_color_language.py \
      -k 'rationale_separates or rationale_defines_the_four_rulers' -q
  ```

  Expected: assertion failures for missing bounded language or surviving
  prohibited phrases. If package import fails because of the damaged worktree,
  run the file directly with system pytest only if its collection remains
  hermetic; otherwise record the environment blocker and continue.

- [ ] Rewrite the opening, “Four rulers,” A1, metric-foundation, validation
  table, and limitations passages in `design-rationale.md` so that:

  - OKLab is a perceptually oriented working model, and OKLCH its cylindrical
    coordinate view—not a perfectly uniform law of vision.
  - `ΔEOK×100` is explicitly 100 times raw Euclidean Oklab distance; the scale
    changes displayed units, not ranking, equalized positions, or CV.
  - `relative_y` is modeled relative CIE Y computed from nominal D65 sRGB and
    is not a display measurement or universal perceived-brightness model.
  - Catalog `relative_y` and WCAG relative luminance are closely related
    decoded-sRGB Y-like calculations with separately pinned coefficient
    conventions; WCAG's software contract adds a foreground/background ratio.
  - CIELAB/CIEDE2000 and named CVD simulations are model-specific finished-output
    diagnostics, not construction coordinates, observer guarantees, or
    accessibility certifications.
  - The retained relative-Y target is clearly a compatibility decision. A new
    incompatible system could use direct OKLCH `L`; doing so here would change
    accepted output.

  Use short MyST admonitions for beginner explanations, but keep all valid
  formulas and compatibility details.

- [ ] Run the focused language and metric tests:

  ```bash
  uv run pytest \
      tests/test_docs_beginner_color_language.py \
      tests/test_docs_float_claims.py \
      -k 'rationale or color_metric_layers or cielab_construction' -q
  ```

  Expected: all collected focused tests pass. Any import failure caused by a
  preflight-missing module is recorded separately from assertion failures.

- [ ] Review `git diff --check` and the exact three-file diff. Request approval,
  then stage only those three paths and commit:

  ```bash
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab diff --check
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab add \
      tests/test_docs_beginner_color_language.py \
      tests/test_docs_float_claims.py \
      docs/color_system/design-rationale.md
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab commit \
      -m "docs(color): bound rationale metric claims"
  ```

---

## Task 2: Make recipe counts name what they count

**Files:**

- Modify: `tests/test_docs_count_claims.py`
- Modify: `docs/color_system/design-rationale.md`

- [ ] Rename `_n_recipe_inputs()` to `_n_recipe_bookkeeping_slots()` and add a
  scalar-leaf counter. The code must count composite constants recursively
  while excluding only the migration-only tone derivation grid:

  ```python
  def _numeric_leaves(value: object) -> int:
      if isinstance(value, bool):
          return 0
      if isinstance(value, (int, float)):
          return 1
      if isinstance(value, list):
          return sum(_numeric_leaves(item) for item in value)
      if isinstance(value, dict):
          return sum(_numeric_leaves(item) for item in value.values())
      return 0


  def _n_recipe_scalar_leaves() -> int:
      recipe = _color_authority()["recipe"]
      assert isinstance(recipe, dict)
      family_order = recipe["family_order"]
      fourier = recipe["fourier"]
      constants = recipe["constants"]
      assert isinstance(family_order, list)
      assert isinstance(fourier, dict)
      assert isinstance(constants, dict)
      family_free_inputs = len(family_order) * 4
      fourier_inputs = sum(len(values) for values in fourier.values())
      constant_leaves = sum(
          _numeric_leaves(value)
          for key, value in constants.items()
          if key != "TONE_DERIVATION_GRID"
      )
      return family_free_inputs + fourier_inputs + constant_leaves
  ```

- [ ] Replace the ambiguous count claim registrations with two live regexes:

  ```python
  (
      "docs/color_system/design-rationale.md",
      r"bookkeeping total is \*\*(\d+) named slots\*\*",
      _n_recipe_bookkeeping_slots,
  ),
  (
      "docs/color_system/design-rationale.md",
      r"corresponds to \*\*(\d+) scalar numeric leaves\*\*",
      _n_recipe_scalar_leaves,
  ),
  ```

  Update the exact inventory assertion to expose both
  `recipe_bookkeeping_slots: 107` and `recipe_scalar_leaves: 116`.

- [ ] Run the count tests and confirm the old prose fails the new regex/value
  contract:

  ```bash
  uv run pytest tests/test_docs_count_claims.py \
      -k 'count_claim or discovery_contract_counts' -q
  ```

  Expected before prose update: missing-claim failures. The authority file is
  known to be missing in the damaged worktree; if so, retain the red test and
  verify the 107/116 arithmetic against the approved spec rather than creating
  substitute authority data.

- [ ] Rewrite the recipe-anatomy passage to say exactly:

  - 19 families × four free authoring fields = 76 named slots;
  - four third-order Fourier series × six coefficients = 24 named slots;
  - seven named constants = seven slots;
  - total bookkeeping = 107 named slots;
  - `GRAY_C_PROFILE` contains ten numbers but counts as one named constant;
  - the same exclusions therefore contain 116 scalar numeric leaves;
  - `TONE_DERIVATION_GRID` is migration-only and excluded from both totals;
  - shipped family records store all eight operational values; four
    Fourier-derived fields are an extension prior/mechanism, not recomputed for
    every current row at runtime;
  - continuous maps carry additional topology-specific recipes, so 107 is not
    the input count for the entire continuous catalog.

- [ ] Re-run the focused count tests when the authority is available; otherwise
  run static regex checks and preserve the dynamic block in the handoff:

  ```bash
  rg -n '107 named slots|116 scalar numeric leaves|GRAY_C_PROFILE|TONE_DERIVATION_GRID' \
      docs/color_system/design-rationale.md tests/test_docs_count_claims.py
  ```

- [ ] Review, request staging approval, and commit only the two task files with
  message `docs(color): distinguish recipe slots from scalar leaves`.

---

## Task 3: Derive the chroma-fit figure from the plotted catalog

**Files:**

- Modify: `docs/color_system/generate_theory_figures.py`
- Modify: `docs/color_system/theory_figures/theory_4_chroma.svg`
- Modify: `docs/color_system/design-rationale.md`
- Modify: `tests/test_docs_float_claims.py`
- Modify: `tests/test_docs_theory_figures.py`

- [ ] Add an independent R² computation to `tests/test_docs_float_claims.py`.
  It must use the 19 observed `p.cmax` values and Fourier predictions at each
  family's `mid_hue`, then compare the prose claim at three decimal places:

  ```python
  def _chroma_r2() -> float:
      from dartwork_mpl._colors import _recipe as recipe

      observed = [params.cmax for params in recipe.FAMILY_PARAMS.values()]
      fitted = [
          recipe.fourier_eval(
              recipe.FOURIER["cmax_k3"], recipe.mid_hue(params)
          )
          for params in recipe.FAMILY_PARAMS.values()
      ]
      mean = sum(observed) / len(observed)
      residual = sum((actual - predicted) ** 2 for actual, predicted in zip(
          observed, fitted, strict=True
      ))
      total = sum((actual - mean) ** 2 for actual in observed)
      return 1.0 - residual / total
  ```

  Register a claim regex matching `in-sample R² of (\d\.\d{3})` and
  `_chroma_r2` at three decimal places. The expected current value is `0.997`,
  but the test must derive it rather than embed it as the oracle.

- [ ] Add generator-contract assertions in
  `tests/test_docs_theory_figures.py`:

  ```python
  source = _GENERATOR.read_text(encoding="utf-8")
  assert "R²=0.945" not in source
  assert "only {TP} varies" not in source
  assert "warp is opt-in" not in source
  ```

  Require normalized rendered labels to contain `in sample r²=0.997` and
  `family parameters vary`; do not use the generated SVG as the numeric oracle.

- [ ] Run the new tests and observe failures against the stale literal and
  labels:

  ```bash
  uv run pytest tests/test_docs_float_claims.py \
      tests/test_docs_theory_figures.py \
      -k 'chroma or stale or accepted_metric_split' -q
  ```

- [ ] Add a pure helper beside the generator's metric helpers:

  ```python
  def coefficient_of_determination(
      observed: Sequence[float], fitted: Sequence[float]
  ) -> float:
      """Return ordinary in-sample R² for paired observations and fits."""
      if len(observed) != len(fitted) or not observed:
          raise ValueError("observed and fitted must be equally sized and non-empty")
      mean = sum(observed) / len(observed)
      total = sum((value - mean) ** 2 for value in observed)
      if total == 0:
          raise ValueError("R² is undefined when observed values are constant")
      residual = sum(
          (actual - predicted) ** 2
          for actual, predicted in zip(observed, fitted, strict=True)
      )
      return 1.0 - residual / total
  ```

  In `fig_chroma`, compute `observed`, `fitted`, and `r_squared` from the same
  `PARAMS` and `FOURIER["cmax_k3"]` values used for the scatter and curve.
  Render `In-sample R²={r_squared:.3f}`.

- [ ] Replace “only t_p varies” with a truthful label such as
  `Shared functional form; family parameters vary`. The prose must say the
  functional form and exponents are shared while `C_max`, `t_p`, `c_0`, and
  `c_end` vary by family. Describe R² as an in-sample descriptive fit to the
  authored catalog, not predictive validation or proof of the sRGB boundary.

- [ ] Regenerate the affected figure when the live package imports:

  ```bash
  PYTHONPATH=src uv run python docs/color_system/generate_theory_figures.py \
      --output-dir docs/color_system/theory_figures
  ```

  Then run:

  ```bash
  uv run pytest tests/test_docs_float_claims.py \
      tests/test_docs_theory_figures.py -q
  ```

  Expected: R² rounds to `0.997`, the committed SVG is byte-current, and the
  generator check passes. If `_tone.py` or another preflight dependency is
  missing, update source/tests/prose but do not hand-edit the SVG and do not
  claim byte-current generation; leave regeneration explicitly blocked.

- [ ] Review, request staging approval, and commit only the five task files
  that were actually changed with message
  `docs(color): derive theory figure claims from catalog data`.

---

## Task 4: Rewrite A2–A8 as bounded design rules

**Files:**

- Modify: `docs/color_system/design-rationale.md`
- Modify: `docs/color_system/generate_theory_figures.py`
- Modify: `docs/color_system/theory_figures/theory_5_spacing.svg`
- Modify: `tests/test_docs_beginner_color_language.py`
- Modify: `tests/test_docs_theory_figures.py`
- Optional bug-fix within approved scope: `tests/test_color_v5_gates.py`

- [ ] Change “generation axioms” to “generation design rules.” Retain A2–A8
  navigation, but update the seven practical questions so A8 asks why colormap
  ranges are chosen per topology/scene rather than claiming one shared range.

- [ ] Add prose contract assertions for the following bounded statements:

  - A2 hue-specific dark endpoints and A4 warm-hue drift are catalog art
    direction, not psychophysical laws.
  - A3 shares a functional form, not all parameters.
  - A5's only shipped policy is fixed `ΔEOK` arc-length equalization; no public
    `ease`, `exp`, `log`, or warp option exists.
  - A6 gray is near-neutral with a deliberate cool tint, not perfectly
    achromatic.
  - A7 current gates are per-asset frozen-baseline non-regression checks; 10/8
    are historical Octave search criteria, not universal categorical minima.
  - WCAG remains outside the color-authority compile-gate table.
  - A8 ranges are palette-floor-independent but class-/scene-specific; broad
    ranges do not make separate panels comparable without shared normalization
    and preferably the same map.

  Add a prohibited-phrase tuple covering:

  ```python
  prohibited = (
      "ease/exp/log remain available",
      "left open as a warp option",
      "shared, wider output range",
      "universal hue identity",
      "WCAG/ΔE00/CVD-validated seven-color cycle",
  )
  ```

- [ ] Run the contract tests first and confirm the existing A2–A8 prose fails.

- [ ] Rewrite A2–A8 and the A7 table. In A7, name the actual metric-specific
  release contracts from `validation.md`; place WCAG in a separate explanatory
  paragraph rather than the hard-gate table. Describe the CVD pipeline at the
  documented level: nominal sRGB decode, named full-severity simulation,
  clamp/re-encode, catalog quantization convention, CIELAB conversion, and
  CIEDE2000 comparison.

- [ ] Correct the spacing figure title to
  `A5 — step spacing: fixed ΔEOK arc-length equalization` and remove every
  generator/prose reference to an opt-in warp. Mention alternative placement
  policies only as possible future incompatible designs requiring an explicit
  API and compatibility contract.

- [ ] If `tests/test_color_v5_gates.py` contains a probe whose unknown-asset
  failure masks the intended 10/8 assertion, repair the test fixture so it
  directly distinguishes historical search floors from present frozen
  baselines. Do not change runtime gate values merely to make the prose tidy.

- [ ] Regenerate `theory_5_spacing.svg` only through the generator, then run:

  ```bash
  uv run pytest \
      tests/test_docs_beginner_color_language.py \
      tests/test_docs_theory_figures.py \
      tests/test_color_v5_gates.py -q
  ```

  Apply the same dynamic-verification limitation from Task 3 if missing source
  modules prevent generation.

- [ ] Review, request staging approval, and commit only changed task files with
  message `docs(color): recast generation axioms as design rules`.

---

## Task 5: Correct gamut, topology, reversal, range, and hue-source claims

**Files:**

- Modify: `docs/color_system/design-rationale.md`
- Modify: `docs/color_system/colormaps.md`
- Modify: `docs/color_system/palettes.md`
- Modify: `docs/color_system/validation.md`
- Modify: `tests/test_docs_beginner_color_language.py`
- Modify: `tests/test_docs_float_claims.py`

- [ ] Add documentation tests that require the shipped gamut policy to be
  described as constant-OKLCH-`L`, constant-`h` chroma reduction by boundary
  bisection for in-range lightness. Reject `Local-MINDE`, `globally optimal`,
  and claims that the process preserves appearance exactly.

- [ ] Add topology/reversal tests that require these exact contracts:

  | Class | Defensible direction contract |
  |---|---|
  | single-hue sequential | low values light, high values dark |
  | multi-hue sequential | low values dark, high values light |
  | diverging | two poles around a light center; no one monotonic direction |
  | cyclic | no low/high direction; generating path closes |
  | qualitative | unordered |

  Require prose to distinguish the closed generating path from the
  endpoint-exclusive stored LUT, whose first and last entries differ by one
  ordinary wrap step. Require `_r` only for registered continuous maps and
  `dm.colors(..., reverse=True)` for qualitative reversal.

- [ ] Add assertions that the 19 `h_0` anchors describe palette identity and
  multi-hue scene waypoints, while diverging/cyclic recipes may use rendered
  poles or a full hue circle. Reject “the only hue vocabulary” and globally
  shared-range claims.

- [ ] Run those tests against current prose and confirm they fail before edits.

- [ ] Rewrite the corresponding rationale and `colormaps.md` passages. Preserve
  the measured aurora/viridis values, but call that comparison a bounded
  same-protocol benchmark. State that a broad range alone does not make maps
  cross-panel comparable; shared normalization and preferably the same map are
  still required.

- [ ] In `palettes.md` and `validation.md`, change only directly duplicated
  inaccurate terminology:

  - “physical Y/output” → first-use modeled relative CIE Y, then modeled
    relative Y;
  - CVD/CIEDE2000 → model-specific collision/regression diagnostics;
  - WCAG → pair-specific text contrast, not palette certification;
  - preserve the exact current per-asset baseline mechanics and quoted measured
    values.

- [ ] Bound three remaining examples in the rationale:

  - Yellow: no current shipped yellow token reaches 4.5:1 on white, but darker
    olive-yellow colors can; this is a selected-ramp/identity choice, not a
    structural impossibility of yellow.
  - Turbo: non-monotonic lightness is task-dependent and can create ambiguity
    or emphasize variation; do not claim all apparent detail is invented.
  - Typography: byte reproducibility is bounded to bundled glyph coverage and
    a pinned rendering environment.

- [ ] Run focused prose/count/float/topology tests:

  ```bash
  uv run pytest \
      tests/test_docs_beginner_color_language.py \
      tests/test_docs_float_claims.py \
      tests/test_docs_count_claims.py \
      tests/test_colormap_topology.py \
      tests/test_discrete_forms.py -q
  ```

  If a named test file does not exist in the surviving worktree, locate its
  current equivalent with `rg --files tests | rg 'topology|discrete'`; do not
  fabricate a new test filename solely to satisfy this plan.

- [ ] Review, request staging approval, and commit only changed task files with
  message `docs(color): correct colormap and validation contracts`.

---

## Task 6: Full integration, rendered review, and adversarial sign-off

**Files:**

- Verify all files changed in Tasks 1–5
- Modify only files with a concrete defect found by the checks below

- [ ] Confirm the generated-color byte invariant:

  ```bash
  shasum -a 256 -c /tmp/dartwork-rationale-generated.before.sha256
  ```

  Expected: `src/dartwork_mpl/_colors/_generated.py: OK`. A mismatch is a hard
  stop: inspect and revert only task-introduced changes after user approval.

- [ ] Check that no runtime/authority path entered the task diff:

  ```bash
  git --git-dir=/Users/lsw91/Workspace/dartwork-mpl/.git/worktrees/dartwork-mpl.wt-oklab \
      --work-tree=/private/tmp/dartwork-mpl-oklab diff --name-only 6be8cb56 -- \
      src/dartwork_mpl tests docs/color_system
  ```

  Expected source changes: only
  `docs/color_system/generate_theory_figures.py`; tests and listed docs/assets
  may change. No file under `src/dartwork_mpl/` should be newly modified by this
  rationale task.

- [ ] Run the complete relevant suite when dependencies exist:

  ```bash
  uv run pytest \
      tests/test_docs_beginner_color_language.py \
      tests/test_docs_count_claims.py \
      tests/test_docs_float_claims.py \
      tests/test_docs_theory_figures.py \
      tests/test_color_v5_recipe.py \
      tests/test_color_v5_gates.py -q
  ```

  Then run the repository's full test target if the restored configuration
  exposes one. Report passed, failed, skipped, and environment-blocked lanes
  separately.

- [ ] Run generator freshness and Sphinx warnings-as-errors when their
  preflight dependencies exist:

  ```bash
  PYTHONPATH=src uv run python docs/color_system/generate_theory_figures.py --check
  uv run sphinx-build -W --keep-going -b html docs docs/_build/html
  ```

  Expected: both exit zero. If `docs/conf.py` or live compiler modules remain
  missing, do not replace them with ad hoc stubs; report rendered verification
  as blocked.

- [ ] Inspect the rendered Design rationale in the browser at desktop and narrow
  width. Check callouts, formulas, tables, images, link targets, figure labels,
  and whether each specialist term is explained before use.

- [ ] Dispatch three independent adversarial reviews over the final diff:

  1. color science: standards scope, metric definitions, causal claims;
  2. visualization design: map semantics, art-direction rationale, practical
     usefulness;
  3. implementation contract: generator, authority, gates, API, counts, and
     tests.

  Each reviewer must report only evidence-backed findings with file/line,
  severity, and a proposed correction. Resolve high/medium findings; explain
  any rejected finding with source or implementation evidence.

- [ ] Run `git diff --check`, targeted tests after review fixes, and the hash
  invariant again. Present the final exact staged diff for user approval before
  any final corrective commit.

- [ ] Final handoff must state:

  - what scientific/design claims changed;
  - that valid prior content was preserved except where evidence showed it was
    false or misleading;
  - whether palette/LUT hashes remained identical;
  - exact verification results and any environment-blocked lanes;
  - the local Sphinx URL if the server is running.
