# `auto_layout` fraction-spine convergence + symmetry guard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the `triple_twinx_offset_spine` xfail (introduced in PR #116) by addressing the two root causes diagnosed below: (1) `auto_layout`'s post-convergence symmetry pass shrinks structurally-needed asymmetric margins back to the average and re-introduces overflow; (2) the harness has no per-scenario knob to request the extra inner padding needed for figures whose right-edge content tightly fills the `auto_layout` tolerance band.

**Architecture:** Two complementary fixes plus a registry-side update.
- *Fix 1 — conditional symmetry pass.* In `src/dartwork_mpl/layout.py:auto_layout`, save the pre-symmetry margins + overflow, apply the symmetry averaging, re-measure, and **revert** the symmetry pass if any side now exceeds the tolerance. Existing balanced figures (`test_extreme_left_squeeze_recovers`) keep their recovery; structurally asymmetric figures (offset spines, axes-fraction annotations on one side) keep the convergence margins.
- *Fix 2 — `auto_layout_padding` knob on `RobustnessScenario`.* Add a per-scenario `auto_layout_padding: float | tuple[float, ...] = 0.08` field. The harness threads it into `dm.auto_layout(fig, padding=scenario.auto_layout_padding, max_iter=scenario.auto_layout_max_iter)`. Scenarios that genuinely need a larger initial margin (e.g. axes-fraction-positioned spines) opt in.
- *Registry update.* Apply `auto_layout_padding=0.25` to `triple_twinx_offset_spine` and lift its `pytest.mark.xfail`. Remove the corresponding entry from `KNOWN_LIMITATIONS`.

**Why these two changes are inseparable:** Fix 1 alone gets the converged right margin from 0.119" → 0.145" (instead of 0.158" being symmetry-shrunk to 0.119"), which is still ~1.6 px residual overflow on the offset spine — short of the 4 px white-border invariant the pixel check enforces. Fix 2 lets the offset-spine scenario request enough initial padding so the iteration converges with a comfortable border. Both fixes need to ship together for the xfail to come off.

**Diagnosis (recorded for the implementer):** Empirically (probed via `/tmp/probe_fraction_spine.py` + `/tmp/probe_no_symmetry.py` during planning), `simple_layout`'s L-BFGS-B optimization for `triple_twinx_offset_spine`:
- pins the right-edge GridSpec coord at the lower bound `0.8` of `(0.8, 1.0)` because the offset spine's ylabel ("Series C") sits at `ax_left + 1.15 × ax_width + label_width`, and pulling the axes right edge inward (right < 0.8 is impossible due to `bound_margin=0.2`) is the only way to reduce the absolute label x-position;
- iter-1 with `padding=0.08` lands at right=0.080" (8 px), residual overflow 2.5 px;
- iter-2 with `padding=(0.08, 0.158)` lands at right=0.158", residual 1.4 px (within `tolerance=2.0`); converged;
- the symmetry pass then averages `(0.080, 0.158) → 0.119` and re-runs `simple_layout`, which produces 1.9 px residual (worse than iter-2's 1.4 px) but still inside tolerance, so `auto_layout` returns;
- with `padding=0.25` (Fix 2), iter-1 starts at 0.25" right margin which is already enough for `simple_layout` to satisfy `< 4 px white border` on the right side — pixel check passes.

**Tech Stack:** Python ≥ 3.10, matplotlib ≥ 3.10, scipy, pytest 8, dartwork-mpl `main`@`ed15230`. Branch `fix/auto-layout-fraction-spine` cut from `main`.

---

## File Structure

| Path | Change |
|------|--------|
| `src/dartwork_mpl/layout.py:415-433` | Replace the unconditional symmetry pass inside `auto_layout` with a save → apply → re-measure → conditional-revert sequence. |
| `tests/test_layout.py` | Append a new test method `test_symmetry_pass_does_not_degrade_overflow` to `TestAutoLayoutSymmetry` covering the regression where symmetry shrunk a structurally-needed asymmetric margin. |
| `tests/robustness/scenarios.py` | Add `auto_layout_padding: float | tuple[float, ...] = 0.08` to `RobustnessScenario`; remove the `pytest.mark.xfail(strict=True, reason=…)` wrapper from the `triple_twinx_offset_spine` entry; set `auto_layout_padding=0.25` on it; remove the corresponding `KNOWN_LIMITATIONS` tuple entry. |
| `tests/robustness/test_robustness_suite.py` | Update the harness call from `dm.auto_layout(fig, max_iter=scenario.auto_layout_max_iter)` to `dm.auto_layout(fig, padding=scenario.auto_layout_padding, max_iter=scenario.auto_layout_max_iter)`. |
| `CHANGELOG.md` | Append two new bullets under the existing `## [Unreleased] / ### Fixed` section: one for the symmetry-pass guard, one for the lifted xfail. |

Single-responsibility per file: `layout.py` change is purely the symmetry guard; `scenarios.py` change is purely the dataclass field + scenario registry update; harness gets a one-line keyword-argument addition; new tests cover both invariants in their natural homes.

---

## Tasks

### Task 1: Cut feature branch + baseline regression

**Files:** None modified (preconditions only).

- [ ] **Step 1: Verify clean state and baseline**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git status -sb && git log --oneline -1`
Expected: clean tree on `main`, HEAD = `ed15230 fix(formatting): millions/billions zero tick honour decimals (#117)`.

- [ ] **Step 2: Cut the branch (or confirm reuse)**

If branch `fix/auto-layout-fraction-spine` already exists from earlier scaffolding, switch to it: `git checkout fix/auto-layout-fraction-spine`. Otherwise: `git checkout -b fix/auto-layout-fraction-spine`.

- [ ] **Step 3: Baseline pytest count**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: `1041 passed, 2 skipped, 8 xfailed`. Capture exact summary line.

If `uv run pytest` hangs > 30s, fall back to `uv run python3 -m pytest -q --no-header`.

---

### Task 2: TDD — `auto_layout` symmetry pass must not degrade overflow

**Files:**
- Test: `tests/test_layout.py` (append a new method to existing `TestAutoLayoutSymmetry`).
- Modify: `src/dartwork_mpl/layout.py:415-433` (replace unconditional symmetry pass with conditional one).

- [ ] **Step 1: Write the failing regression test**

Open `tests/test_layout.py`. Locate `class TestAutoLayoutSymmetry:` (currently contains `test_extreme_left_squeeze_recovers`). Append:

```python
    def test_symmetry_pass_does_not_degrade_overflow(self) -> None:
        """A figure whose offset-spine ylabel structurally needs a large
        right margin must not have that margin shrunk back by the
        symmetry pass. Regression for the
        ``triple_twinx_offset_spine`` xfail diagnosed in PR #116:
        symmetry averaging (0.08, 0.158) → 0.119 re-introduced ~0.5 px
        of right-edge overflow because the offset spine's label sits at
        ``ax_left + 1.15 × ax_width + label_width``."""
        fig, ax1 = plt.subplots(figsize=(5.5, 4.0))
        ax1.plot([1, 2, 3, 4], [1, 4, 9, 16])
        ax1.set_ylabel("Series A")
        ax2 = ax1.twinx()
        ax2.plot([1, 2, 3, 4], [10, 20, 30, 40])
        ax2.set_ylabel("Series B")
        ax3 = ax1.twinx()
        ax3.spines["right"].set_position(("axes", 1.15))
        ax3.plot([1, 2, 3, 4], [100, 200, 150, 250])
        ax3.set_ylabel("Series C")

        auto_layout(fig)

        post = _measure_overflow(fig)
        # Pre-fix value at this geometry was ~1.9 px (symmetry pulled
        # the right margin back from the converged 0.158 to 0.119).
        # Post-fix the symmetry pass must revert when it would degrade
        # any side, so the right overflow stays at the pre-symmetry
        # ~1.4 px.
        assert post["right"] <= 1.6, (
            f"symmetry pass degraded right overflow: {post}"
        )
        plt.close(fig)
```

- [ ] **Step 2: Run new test and verify it FAILS**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutSymmetry::test_symmetry_pass_does_not_degrade_overflow -q`
Expected: FAILED with right overflow approximately 1.9 px (assertion threshold 1.6).

If the test PASSES out of the gate, your local matplotlib renders the figure differently than the diagnosis machine; raise the threshold by ~0.5 px to keep the test meaningful but DO NOT make it tautological — report DONE_WITH_CONCERNS so the controller can re-investigate.

- [ ] **Step 3: Patch the symmetry pass**

Open `src/dartwork_mpl/layout.py`. Locate the symmetry block (lines 415-433):

```python
        if max_overflow <= tolerance:
            # Final symmetry pass: average horizontal and vertical margin
            # pairs so asymmetrically-squeezed figures (e.g. user called
            # subplots_adjust before auto_layout) are centred without
            # expanding the canvas. Runs only on convergence so we don't
            # mask a genuine layout failure.
            avg_h = (margins[0] + margins[1]) / 2
            avg_v = (margins[2] + margins[3]) / 2
            if abs(margins[0] - avg_h) > 1e-6 or abs(margins[2] - avg_v) > 1e-6:
                margins[0] = avg_h
                margins[1] = avg_h
                margins[2] = avg_v
                margins[3] = avg_v
                simple_layout(fig, margins=tuple(margins))
                if verbose:
                    print(
                        f"[auto_layout] symmetry pass applied: "
                        f"avg_h={avg_h:.3f}, avg_v={avg_v:.3f}"
                    )
            if verbose:
                print(
                    f"[auto_layout] Converged in {iteration + 1} iteration(s)."
                )
            return
```

Replace with:

```python
        if max_overflow <= tolerance:
            # Final symmetry pass: average horizontal and vertical margin
            # pairs so asymmetrically-squeezed figures (e.g. user called
            # subplots_adjust before auto_layout) are centred without
            # expanding the canvas. Runs only on convergence so we don't
            # mask a genuine layout failure.
            #
            # Conditional revert: figures whose content structurally
            # needs an asymmetric margin (e.g. an offset spine via
            # ``ax.spines["right"].set_position(("axes", 1.15))``) would
            # have their structurally-needed right margin shrunk back to
            # the average and re-introduce overflow. Re-measure post-
            # symmetry; if any side now exceeds tolerance, restore the
            # pre-symmetry margins so the convergence isn't degraded.
            avg_h = (margins[0] + margins[1]) / 2
            avg_v = (margins[2] + margins[3]) / 2
            if abs(margins[0] - avg_h) > 1e-6 or abs(margins[2] - avg_v) > 1e-6:
                pre_margins = list(margins)
                margins[0] = avg_h
                margins[1] = avg_h
                margins[2] = avg_v
                margins[3] = avg_v
                simple_layout(fig, margins=tuple(margins))
                post_overflow = _measure_overflow(fig)
                if max(post_overflow.values()) > tolerance:
                    # Symmetry pass degraded overflow — revert.
                    margins = pre_margins
                    simple_layout(fig, margins=tuple(margins))
                    if verbose:
                        print(
                            f"[auto_layout] symmetry pass reverted "
                            f"(post-symmetry overflow {post_overflow} "
                            f"exceeded tolerance {tolerance})"
                        )
                elif verbose:
                    print(
                        f"[auto_layout] symmetry pass applied: "
                        f"avg_h={avg_h:.3f}, avg_v={avg_v:.3f}"
                    )
            if verbose:
                print(
                    f"[auto_layout] Converged in {iteration + 1} iteration(s)."
                )
            return
```

- [ ] **Step 4: Re-run new test — must PASS**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutSymmetry::test_symmetry_pass_does_not_degrade_overflow -q`
Expected: 1 PASSED.

- [ ] **Step 5: Run the rest of `TestAutoLayoutSymmetry` (and module) to confirm no regression**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_layout.py -q`
Expected: previous count + 1 new pass; zero failures. In particular `test_extreme_left_squeeze_recovers` (which depends on the symmetry pass APPLYING, not reverting) must still PASS — squeeze-recovery has 0 overflow before AND after symmetry, so the conditional revert never triggers.

- [ ] **Step 6: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add src/dartwork_mpl/layout.py tests/test_layout.py
git commit -m "fix(layout): auto_layout symmetry pass reverts if it degrades convergence"
```

---

### Task 3: Add `auto_layout_padding` field to `RobustnessScenario` and thread through harness

**Files:**
- Modify: `tests/robustness/scenarios.py` (extend the `RobustnessScenario` dataclass).
- Modify: `tests/robustness/test_robustness_suite.py` (pass the new field to `dm.auto_layout`).

- [ ] **Step 1: Extend the dataclass**

Open `tests/robustness/scenarios.py`. Locate the `RobustnessScenario` dataclass (around lines 24-55). Add a new field after `auto_layout_max_iter`:

```python
    auto_layout_padding: float | tuple[float, float, float, float] = 0.08
```

Update the docstring's Parameters section by adding immediately before the closing `"""`:

```
    auto_layout_padding
        Initial padding (inches) passed to ``dm.auto_layout``. Most
        scenarios accept the default 0.08. Scenarios with
        axes-fraction-positioned spines or other content that fills
        the canvas tightly may need a larger value (e.g. 0.25) so the
        iteration converges with a 4 px white-border invariant.
```

- [ ] **Step 2: Thread the field into the harness**

Open `tests/robustness/test_robustness_suite.py`. Find the `auto_layout` call inside `test_robustness_scenario`:

```python
    # Stage 2: layout convergence.
    dm.auto_layout(fig, max_iter=scenario.auto_layout_max_iter)
```

Replace with:

```python
    # Stage 2: layout convergence.
    dm.auto_layout(
        fig,
        padding=scenario.auto_layout_padding,
        max_iter=scenario.auto_layout_max_iter,
    )
```

- [ ] **Step 3: Run robustness suite to confirm no field-default regression**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/ -q`
Expected: 45 passed, 8 xfailed (default `auto_layout_padding=0.08` matches the previous default behaviour — no scenario should change outcome).

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/robustness/scenarios.py tests/robustness/test_robustness_suite.py
git commit -m "test(robustness): add auto_layout_padding field to RobustnessScenario"
```

---

### Task 4: Lift `triple_twinx_offset_spine` xfail with `auto_layout_padding=0.25`

**Files:**
- Modify: `tests/robustness/scenarios.py` (drop xfail wrapper, set padding, remove KNOWN_LIMITATIONS entry).

- [ ] **Step 1: Lift the xfail**

Open `tests/robustness/scenarios.py`. Locate the `triple_twinx_offset_spine` registry entry (currently wrapped via `pytest.param(... marks=pytest.mark.xfail(...))`). Replace the entire block with a plain `RobustnessScenario` — drop both the `pytest.param` wrapper and the `marks=...`. Set `auto_layout_padding=0.25` so the iteration starts from a margin that fits the offset spine's ylabel inside the 4 px white-border invariant.

The exact resulting block should look like:

```python
    RobustnessScenario(
        name="triple_twinx_offset_spine",
        build=_build_triple_twinx_offset_spine,
        # The offset spine pushes ax3's ylabel ~15% past the axes
        # right edge. We start auto_layout with extra horizontal
        # padding so simple_layout's first iteration already gives
        # the offset ylabel room — convergence then satisfies the
        # 4 px white-border invariant without relying on the per-
        # iteration BUFFER scaling reaching the necessary depth.
        auto_layout_padding=0.25,
        auto_layout_max_iter=8,
    ),
```

- [ ] **Step 2: Remove the matching `KNOWN_LIMITATIONS` entry**

In the same file, locate the `KNOWN_LIMITATIONS` tuple (around line 62). Remove the `triple_twinx_offset_spine` entry (added at the end of the tuple in commit `af5b3f9`). The remaining entries are unchanged.

- [ ] **Step 3: Run the scenario in isolation**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k triple_twinx_offset_spine -q`
Expected: 1 PASSED (no `xfailed`, no `xpassed`).

If the scenario still fails the pixel check, raise `auto_layout_padding` in 0.05 increments (0.30, 0.35, 0.40 …) until it passes; cap at 0.50. If 0.50 still fails, halt and report DONE_WITH_CONCERNS — that means the diagnosis missed something and the BUFFER scaling itself needs surgery (out of scope for this plan).

- [ ] **Step 4: Run the full robustness suite**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/ -q`
Expected: 46 passed, 7 xfailed (one fewer xfail, one more pass than Task 3 baseline).

- [ ] **Step 5: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): lift triple_twinx_offset_spine xfail with auto_layout_padding=0.25"
```

---

### Task 5: Final regression + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md` (append two new bullets under existing `## [Unreleased] / ### Fixed`).
- Stage: `docs/superpowers/plans/2026-05-02-auto-layout-fraction-spine.md` (currently untracked — include in the same commit so the branch carries its spec).

- [ ] **Step 1: Final regression run**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: `1043 passed, 2 skipped, 7 xfailed` (Task 1 baseline 1041 + 1 symmetry test + 1 lifted xfail-now-pass = 1043 passed; one xfail removed = 7).

If the count diverges by more than ±1, halt and report DONE_WITH_CONCERNS.

- [ ] **Step 2: Append the CHANGELOG bullets**

Open `CHANGELOG.md`. Find the existing `## [Unreleased] / ### Fixed` section. Below the existing bullets, add two new bullets at the same indentation:

```markdown
- `auto_layout` post-convergence symmetry pass now reverts itself
  when re-measurement detects that the averaging would re-introduce
  overflow on any side. Figures with structurally-needed asymmetric
  margins (e.g. axes-fraction-positioned right spines via
  `ax.spines["right"].set_position(("axes", 1.15))`) keep their
  iteration-converged margins; balanced figures (e.g. user called
  `subplots_adjust(left=0.05, right=0.30)`) still get re-centred.
- The `triple_twinx_offset_spine` robustness scenario is no longer
  `xfail` — combined with the symmetry-pass guard above and the new
  `auto_layout_padding` field on `RobustnessScenario`, the scenario
  now converges with a 4 px white-border invariant on the offset
  ylabel and is removed from `KNOWN_LIMITATIONS`.
```

Also update `### Added` (in the same `## [Unreleased]` block) by appending one bullet:

```markdown
- `RobustnessScenario.auto_layout_padding` field (default 0.08
  inches) lets per-scenario builders request extra initial padding
  for figures whose right-edge content (e.g. axes-fraction-
  positioned spines) tightly fills the `auto_layout` tolerance band.
```

- [ ] **Step 3: Commit (CHANGELOG + plan)**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add CHANGELOG.md docs/superpowers/plans/2026-05-02-auto-layout-fraction-spine.md
git commit -m "docs: changelog + plan for auto_layout fraction-spine convergence fix"
```

- [ ] **Step 4: Final pass-count audit**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: same `1043 passed, 2 skipped, 7 xfailed`.

- [ ] **Step 5: Sanity check the branch**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git log --oneline main..HEAD`
Expected: 4 commits (Task 2 + Task 3 + Task 4 + Task 5).

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git status`
Expected: clean working tree on `fix/auto-layout-fraction-spine`.

---

## Execution Notes

- **Branch hygiene.** Single feature branch `fix/auto-layout-fraction-spine`. Plan file is committed in Task 5 so the branch carries its spec.
- **Fix 1 + Fix 2 are inseparable.** Each on its own does not lift the `triple_twinx_offset_spine` xfail. Do not commit Fix 1 (Task 2) without proceeding to Tasks 3-4 in the same branch — a green CI run requires both to land together because Task 4's pass count assertions assume Fix 1 is in place.
- **No source-level fixes outside `auto_layout`'s symmetry block.** The diagnostic showed `simple_layout`'s L-BFGS-B optimization is functioning correctly (it pins the right edge at the lower bound `0.8` because the offset-spine geometry mathematically requires it). The bound itself is not the bug. Don't touch `simple_layout`, `_measure_overflow`, or the BUFFER scaling — out of scope.
- **`auto_layout_padding` default unchanged.** All existing scenarios keep `0.08` via the dataclass default. Only `triple_twinx_offset_spine` opts into `0.25`. If a future scenario also needs more padding, it can opt in similarly without touching the harness.
