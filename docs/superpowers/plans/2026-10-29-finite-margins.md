# Finite Effective Margins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refuse nonfinite effective margins before layout effects, preserving finite behavior and precedence.

**Architecture:** Keep parsing/resolution and the finite check inside the existing layout slice. Check resolved effective sides in `simple_layout` before entering the solver; keep the public signature and Length behavior unchanged.

**Tech Stack:** Python >=3.10, Matplotlib/Agg, pytest, existing Ruff/mypy.

**Spec:** [Approved B/C design](../specs/2026-10-29-input-preflight-design.md), especially current authority, invariants and B.

## Global Constraints

Python >=3.10; no new dependency, CI gate or public API.
Keep signatures/static types, MCP names/order/schemas/registered docstrings and 19/10/9/2 discovery unchanged.
Keep artifact v1, shipped colors, presets and ADR 0001–0005 unrelated locks unchanged.
Work locally only; no fetch/network, remote writes, PR, messages, services or account workaround.

Read the spec's four authority/invariant/reason/unverified sections; approved intent is not current runtime.
No Handbook initialization. No protected-checkout or excluded-document/copy access.
Parent venv is read-only; explicit target PYTHONPATH, no bytecode, scratch cache/temp roots.
B owns only layout source/tests and a necessary narrow `docs/usage_guide/layout.md` edit.
Parent owns shared CHANGELOG/bundles and integration; do not regenerate them.

## Review Focus

1. Fully overridden nonfinite base must succeed; test snapshot/RGBA equality to finite base.
2. Late malformed mb must keep its old parse error; test exact exception and no effects.
3. Empty/manual figures must retain no-op/warning precedence with malformed inputs.
4. Every individual side must reject independently; test each side on a finite base.
5. Font adoption must not run on rejection; snapshot all existing tick/offset font properties.

---

### Task 1: Preflight effective fractions without layout effects

**Files:**
- Modify: `src/dartwork_mpl/layout/__init__.py` (`simple_layout`, after `_parse_margins(...).fractions(...)`).
- Create/Test: `src/dartwork_mpl/layout/tests/test_margin_preflight.py` (public behavior; no relocation).
- Read/replay: `src/dartwork_mpl/layout/tests/test_margins.py`, `test_simple_layout_basic.py`, `test_layout.py` in the same directory.
- Modify only if needed: `docs/usage_guide/layout.md` (finite effective-margin requirement).

**Interfaces:**
- Consumes: `_parse_margins(margin, ml, mr, mt, mb) -> _MarginSpec`; `.fractions(fig_w_in: float, fig_h_in: float) -> _Sides`.
- Produces: unchanged `simple_layout(fig: Figure, gs: GridSpecBase | SubplotSpec | None = None, *, margin: Length | str | float = 0, ml: Length | str | float | None = None, mr: Length | str | float | None = None, mt: Length | str | float | None = None, mb: Length | str | float | None = None, use_all_axes: bool = True, adopt_orphan_tick_font: bool | None = None, verbose: bool = False) -> None`.
- New outcome: exact `ValueError("margin must resolve to finite figure fractions")` for nonfinite effective sides only.

- [ ] **Step 1: Record the baseline before changing source.**

Use the approved scratch oracle as evidence/design guidance, not a 215-line product-test transplant.
Run from this worker's clean pinned base, before edits; keep reviewed originals read-only.
Create worker-owned scratch `b/baseline` and `b/changed` under
`~/scratch/dartwork-local-input-preflight-2026-10-29/`; save source SHA/import origin/versions.
Render the seven finite packet cases (0, -.1, '0%', '-10%', zero/negative Length, .8) and full finite overrides.
Save all Axes bounds, raw/resolved GridSpec edges, tick/offset font properties and rendered RGBA SHA-256 per case.
Use `dm.style.use("scientific")`, `dm.figsize("13cm", "standard")`, two Axes and explicit font adoption.
Expected: finite snapshots recorded on base `33f51edd`; all-overrides equal finite-base equivalent.

- [ ] **Step 2: Write proportional failing public regressions.**

`test_nonfinite_effective_margin_rejects_without_effects`: parameterize nine NaN/±Inf × number/percent/`dm.cm(1)*value` bases;
add finite-base ml=NaN, mr='inf%', mt=negative-infinite Length, mb=Inf and partial base override.
Pre-draw the two-Axes fixture with orphan labels and unequal label/tick fonts, then observe real canvas draws.
Capture exception without early assertion; independently assert:
```python
assert (type(error), str(error)) == (ValueError, "margin must resolve to finite figure fractions")
assert draws == []
assert after_bounds == before_bounds
assert after_raw_and_resolved_edges == before_raw_and_resolved_edges
assert after_existing_tick_and_offset_fonts == before_existing_tick_and_offset_fonts
```
Snapshot existing major/minor ticks and offsets on x/y axes: size/weight/family/style/variant/stretch; close figures in finally.
`test_full_finite_overrides_preserve_layout`: assert full snapshot and RGBA digest equality against finite base.
`test_margin_preflight_preserves_parse_and_noop_precedence`: empty/manual inputs include NaN and `mb='a%'`;
assert None/no draws/no mutation; manual warning equals current source's complete warning.
For applicable figure with NaN base, Inf ml and `mb='a%'`, assert exact old ValueError
`"could not convert string to float: 'a'"`, not the new error, with no effects.
Also pass real `matplotlib.gridspec.GridSpecBase(1, 1)` as gs: preserve existing unsupported-GridSpec warning/no-op before malformed margins.
If a GridSpec-resolution error occurs, preserve it unchanged; do not move parsing ahead of resolution.
Add deterministic `random.Random(20261029)` finite fractions with mixed side overrides to compare a fully overridden NaN base
against the same finite-base call; assert bounds/edges/fonts/RGBA equality. No new property dependency.

- [ ] **Step 3: Run the new regressions RED.**

For all commands, set `PY=/Users/wonjun/.t3/worktrees/dartwork-mpl/t3-0c3dff26/.venv/bin/python` (read-only),
`PYTHONPATH="$PWD/src"`, `PYTHONDONTWRITEBYTECODE=1`, `MPLBACKEND=Agg`, and worker-owned
`MPLCONFIGDIR`, `XDG_CACHE_HOME`, `TMPDIR`; create those scratch directories first.
Run: `"$PY" -m pytest src/dartwork_mpl/layout/tests/test_margin_preflight.py -q --no-cov -p no:cacheprovider`.
Expected: new rejection assertions FAIL on base behavior; preserve passing precedence/full-override evidence.
Save output and exit code; a collection/import failure is not RED.

- [ ] **Step 4: Implement the finite check and document it.**

In `simple_layout`, after full existing parse/resolution, check all four `_Sides` values for finiteness,
raising the exact approved error before the solver and effects. Do not modify `_parse_margin`, Length or clamp policy.
Update the changed function docstring with finite effective-side rejection and preserved override/parse/no-op behavior.
No signature/static-type changes, cross-slice import or new outcome framework.

- [ ] **Step 5: Verify GREEN and unchanged finite renders.**

Run: `"$PY" -m pytest src/dartwork_mpl/layout/tests -q --no-cov -p no:cacheprovider`.
Run: `"$PY" -m ruff check src/dartwork_mpl/layout` and `"$PY" -m ruff format --check src/dartwork_mpl/layout`.
Expected: all pass; record pre-existing unrelated failures separately, never silently waive new failures.
Replay Step 1 into `b/changed`; compare per-case numeric/font snapshots and RGBA digests exactly.
Expected: no differences, including oversized `.001` clamp. Inspect any difference before claiming compatibility.
Save equal-scale before/after images and bad-input refusal evidence for parent PoC; this does not claim user visual review.

- [ ] **Step 6: Commit and hand off for independent patch review.**

Stage only owned source/test/necessary guide files; local commit `fix: reject nonfinite effective layout margins`.
Return SHA, RED/GREEN receipts, finite comparisons and limits. Parent reviews this patch independently, then combines with C.
Existing pytest CI collects colocated tests via `pyproject.toml` testpaths; no new CI gate.
