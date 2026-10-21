# CORE #501 items 4–6 — adopted checkbox plan

Status: adopted implementation plan; checkboxes record execution in this source worktree.
Precondition satisfied: parent adopted the CORE-I1 corrected design within user-go-approved #501 items 4–6.
Original independent review covers its original bytes; corrected context lifetime policy was separately adopted.
Base: detached d2b6d0b1ce8897d24398aa5a4de5d97f23ab2a05; parent refreshed origin/main at same identity.
Do not read the excluded proposal/copies, alter protected host state, or initialize a Handbook.
No new dependencies, CI gates or broad tests. Use existing pytest tests tree and existing environment.
Inherit all four authority sections and their roles/paths from the sibling adopted spec.
Raw red/green and PoC evidence is retained in the external task directory; registration/decimal/type-error policies remain unchanged.

## Task 1 — registration retry and preflight (one logical commit)

- [x] Step 1: Reopen `_colors/_register.py`, existing register tests and current color-freeze expectations; confirm ordered map names, exact colors and loaded fast path unchanged.
  Expected: authority paths/invariants in design remain true; stop for source movement requiring reconciliation.
- [x] Step 2: Add focused real-registry subprocess regressions in `tests/test_color_v5_register.py` using the baseline receipts.
  Expected red: reload/retry fails at assertion; middle collision leaves additions; retain exact red output outside /tmp.
- [x] Step 3: Cover same-LUT external collision, extremes/metadata mismatch, unrelated-map preservation and removal-then-retry in subprocesses.
  Expected: cases inspect actual public registry; only deliberately created external probes are unregistered; no private registry patching.
- [x] Step 4: Implement private provenance convention, ordered full conflict preflight and exact equality reuse in `_colors/_register.py` only.
  Expected: unloaded/reload/retry succeeds for identical own maps; static conflicts add zero maps; loaded fast path, None return and map data unchanged.
- [x] Step 5: Run affected register/API tests and fixed shipped-color oracle; repeat normal import→reload→native cmap access manually.
  Expected: all pinned counts/digests identical; no force registration; targeted generated operation sequences preserve the invariant.
  Commit point: registration behavior + focused tests + concise release note, after parent review of this logical diff.

## Task 2 — style ownership and context lifetime (one logical commit)

- [x] Step 1: Reopen `style.py`, `tests/test_style.py`, `tests/conftest.py` and design authority; compare fresh/dark receipts.
  Expected: scientific is silent about axes.edgecolor; incoming font.size wins; kwargs are last; native context restores rcParams/semantics but does not yet integrate new ownership.
- [x] Step 2: Before implementation, write/run the native identical-edgecolor regression from fresh and dark states and both context/control traces below in `tests/test_style.py`.
  Expected red: dark-history edit is lost (#a1b2c3 becomes black); retain exact assertion failure before repair. Record actual status per context guard; a baseline-green guard is not a reproduced failure.
- [x] Step 3: Pin within-body scientific→context(dark)→use(scientific) against ordinary dark→scientific from identical isolated state.
  Expected: complete resulting public rcParams/semantics match; axes.edgecolor is native black, not #555555. Establish a meaningful new assertion-red before changing product behavior.
- [x] Step 4: Pin dark→context(report){use(scientific)}→exit→scientific against identical no-context control; parameterize normal exit, body exception and nested contexts.
  Expected: after every exit, all public rcParams/semantic tokens equal saved outer state; next scientific equals control (black edge). Nested exit restores its immediate outer state; include a KR nested context so semantic rollback is observable.
- [x] Step 5: Cover inherited outer dark-owned axes.edgecolor through a report context, a detectable outer user override #a1b2c3 surviving rollback/next silent-key switch, and context/use kwargs-last controls.
  Expected: context-silent owned residue resets; genuine detectable overrides survive; incoming-declared keys win; kwargs are never preset-owned, including explicit same-value kwargs (native same-value writes remain residue).
- [x] Step 6: Add narrowly generated preset/edit sequences and mutable-list edit coverage with seed501; compare public behavior to declared precedence.
  Expected: no assertion on new bookkeeping representation; controls/branches start with identical isolated state.
- [x] Step 7: After meaningful red, replace historical exclusion with copied last-stack normalized preset values, retaining existing rejected-use preflight and short mutation locks.
  Expected: differing current values detect edits; residue resets; incoming keys win; kwargs apply afterward; failed validation leaves state/bookkeeping unchanged.
- [x] Step 8: Integrate context entry/exit: deep-copy outer ownership; after native temporary application merge normalized preset-only writes, retain inherited silent-key tracking, and preserve known kwargs intent.
  Expected: finally restores outer ownership with existing semantic/native rollback for normal, exception and nested paths; no lock across yield, assignment observer, new thread/global framework or native context-semantic change.
- [x] Step 9: Update `_style_state`, `_restore_style_test_state` and `isolated_style_state` to deep-copy/save/restore new bookkeeping; align affected setup/cleanup with conftest rcdefaults.
  Expected: state created solely for this bugfix cannot outlive its test/context; snapshot helpers may handle private data, but public-state regression assertions stay representation-independent.
- [x] Step 10: Run focused new regressions to green, then affected existing style/context/semantic tests and shipped-color freeze; retain red→green commands/results and reproduce real normal-path plots.
  Expected: both context/control traces, restored public state/next transitions, valid presets and all frozen colors pass; rejected style preserves immediate/subsequent state.
  Commit point: style ownership/context behavior + focused tests/isolation + precise docs/release note for detectable edits and same-value limit; parent reviews diff and actual same-scale PoC before merge.

## Task 3 — dynamic decimal formatting (one logical commit)

- [x] Step 1: Reopen `util.py` and `tests/test_util.py`; use `decimals.json` and actual baseline PNG/PDF as red evidence.
  Expected: current function replaces dynamic locators and leaves all ticks outside the new data view.
- [x] Step 2: Add real native plotting regression: line.set_data→relim→autoscale_view→draw; compare actual ticks and formatted labels.
  Expected red: formatted axes lack current in-view ticks while the native control follows new limits.
- [x] Step 3: Cover exact ±half ties/negative zero, finite seeded values/precisions, custom locator, None axis, return and immediate invalid precision.
  Expected: Python formatting is the independent rounding oracle; no data-cleaning policy or precision-domain expansion.
- [x] Step 4: Replace tick/label freezing with native dynamic formatters preserving Python fixed-point formatting and locator/view limits.
  Expected: requested axes format new current ticks; no changes to signatures, return or untouched axes.
- [x] Step 5: Run affected util tests; repeat actual PNG/PDF data-change rendering and read saved outputs plus numeric ticks.
  Expected: selected new-range ticks visible; existing before-data formatting matches Python; no claimed fix based only on formatter class.
  Commit point: decimal behavior + focused tests + release note, with visible-result PoC reviewed before merge.

## Task 4 — proven name type errors (one logical commit)

- [x] Step 1: Reopen `style.py`, `_colors/_api.py` and baseline `boundaries.json`; enumerate only proven leaks.
  Expected: type guards cover use scalar/list names, context/style_path/load_style_dict, colors and show_colors members.
- [x] Step 2: Add regressions for descriptive TypeError and unknown-string/valid-call controls; deliberately update two existing malformed-style AttributeError expectations.
  Expected red: current code raises AttributeError; error tests preserve semantic and subsequent style state checks.
- [x] Step 3: Add smallest guards at owning name boundaries before string methods/state changes; document changed failures.
  Expected: no string coercion or protocol expansion; unknown valid-type names retain existing KeyError/ValueError suggestions.
- [x] Step 4: Run targeted style and Model B API tests; replay real failing/valid calls and state comparisons.
  Expected: only intended error class/message changes; prior valid shapes/None returns and color digests remain.
  Commit point: narrow boundary guards + focused tests + public error/release notes, after review.

## Task 5 — integration and visible review (no new gate)

- [x] Step 1: Recheck current upstream and ownership/diff; reconcile movement through existing parent workflow before final checks.
  Expected: no unrelated source, preset/asset/digest edits or dependencies; only authorized logical commits remain.
- [x] Step 2: Run existing affected pytest files, immutable shipped-color suite, Ruff check/format check and mypy; retain exact commands/results.
  Commands: existing environment `python -B -m pytest tests/test_color_v5_register.py tests/test_color_model_b_api.py tests/test_style.py tests/test_util.py tests/test_shipped_colors_hash.py --no-cov`;
  `ruff check` / `ruff format --check` on touched files; scoped mypy of four owned source files passed. Parent runs the full-package integration check after all tracks freeze.
  Expected: new meaningful regression red precedes implementation and green; existing CI owns Python3.10–3.13; report unrun runtimes. Reuse recorded successful checks unless changes/failures justify rerun; no repeated whole-suite gates.
- [ ] Step 3: Build actual same-scale before/after PoC for style color preservation and changed-data decimal; inspect full images and useful tick/spine crops.
  Expected: show candidate beside current source at equal physical size/DPI before merge; preserve data/style except requested correction.
- [x] Step 4: Run normal import/reload, preset→manual edit→preset, both context transition paths, and native changed-data save path directly; inspect PNG/PDF, public restored state and actual tick text.
  Expected: user-facing behavior verified directly, no waiting on CI/next scheduled run as substitute; local image links or verified Tailnet HTTPS.
- [ ] Step 5: Parent reviews raw evidence/diff, existing-contract compatibility and scope before any integration action.
  Expected: concrete reviewable result; no automatic merge/publication authorization inferred from this draft.

Execution receipt: 156 affected/color-freeze tests passed on Python3.12.13/matplotlib3.10.9; Ruff/format and four-file mypy passed.
Meaningful original red: manual override/context A/static collision/dynamic ticks/name types. Same-value kwargs clarification also observed red then green.
Original no-override context B guards were green; seed501 report font oracle corrected to shipped report8.0/scientific7.5 before final green.
No Git/GitHub mutation by this worker; parent review/PoC presentation and supported-runtime CI remain pending.
