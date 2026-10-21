# Core failure preservation — implementation tasks

Date: 2026-10-21. Status: archival pre-implementation task plan; checkboxes retain their original planned/pending state.
This historical plan is not the current completion tracker; execution evidence is recorded in the implementation PR.
Intended repository path: `docs/superpowers/plans/2026-10-21-core-failure-preservation.md`.
Evidence root (`E`): `/Users/wonjun/scratch/dartwork-mpl-agent-followthrough-2026-10-21`.
Sequence: accepted design → independent review → this plan → implementation → independent final review → parent integration.
Actual planning tools: file/source inspection, `rg`, shell and SHA256 receipts. Unavailable named brainstorming/writing-plans skills were not invoked.

## 현재 권위와 상태

- Accepted design: `E/core-design/2026-10-21-core-failure-preservation.md`, SHA256 `a8a5daf65d86760e8d016b8ebda8115c5c52e407f176eb7c79b74547db2a02b9`; adoption: `E/core-design/adoption.json`.
- Independent review: `E/core-design-review/review.md`, PASS, zero Important/Critical, SHA256 `beb39969481f619a08158938105ab88acd87fbc809123346359d174f042eea46`.
- Role/path: existing owners `src/dartwork_mpl/{io.py,style.py,lint.py}` and `src/dartwork_mpl/_colors/_views.py`; existing `tests/` mirrors them because `pyproject.toml` collects `testpaths=["tests"]`. No Handbook exists; none is initialized.
- Current user “고” authorizes these bounded restorations, including routine implementation choices. No private/old design adoption or repeated approval flow.

## 지켜야 할 현재 불변식

- Preserve APIs, existing exceptions except newly rejected nonfinite setters, Issue/Rule fields, IDs/severities, public character-offset columns, `(fixed_code, applied, unfixed)`, MCP discovery 19/10/9/2, presets, shipped colors/digests, dependencies and CI.
- Do not change C7 data/default policy, C8 override/history precedence, arbitrary kwargs/render/disk rollback, or unrelated historical issue claims. Never regenerate shipped-color digests.
- Protected host HEAD/index/worktree, `E/core-env`, old receipts and PR513 remain untouched. Parent alone owns Git/GitHub writes and integration.

## 설계 이유와 제약

- C4 proves partial files/figure mutation on rejected output; C5 proves nonfinite mutation; C6 proves rejected styles alter live state; C1–3 prove false diagnostics and unsafe source edits. Passing controls must survive each repair.
- Python >=3.10 and Matplotlib >=3.10.1 remain supported. Measured baseline is Python 3.12.13/Matplotlib 3.11.2; preserve the existing CI matrix.
- Keep each behavior in its current owning module; no new shared framework, parser library, dependencies or CI gates. Document changed helpers/setters/tests with behavioral docstrings.

## 충돌·미확인

- Reviewed-base receipt: `E/integration/snippet-fix-integration.json`, PR513 head `9e7a655d2b08f965f1377e5ca043a2ad2808b2ab`, tree `7767fb15ee8605ccfb1345574ebd4e279272dd62`; reviewed changed-file snapshots: `E/integration/final-after` (not a complete source/test export). Task 1 identifies the reused complete export and runner/overlay paths. Implementation may start there while unrelated docs CI runs; merge is not a source-edit prerequisite. Parent verifies eventual merged-main tree equality or reconciles actual overlaps before core Git integration.
- If a later PR513 fix touches a core owner, freeze that owner and coordinate; never overwrite concurrent changes. Core checks cannot inherit PR513's result.
- Optional/custom backends and arbitrary runtime/disk rollback are outside measured coverage. Target installed backends; record untested variants honestly.

## Execution and evidence rules

All commands below are proposed, not run by this plan. Run only in the parent-verified export (`SOURCE`), using the Task 1 runner; `uv run pytest <modules>` is the repository's existing command form.
Reuse `E/core-env/bin/python` read-only with `E/recipes/check-deps` and the existing private IPython overlay when needed and accurate; no new full clone/environment per patch or all-extras setup for normal core tests.
Each worker owns disjoint source/test paths, its cwd, `MPLCONFIGDIR` and log/output directory; set `PYTHONDONTWRITEBYTECODE=1` and Python `-B`. Shared-export updates use atomic staged files, with no import/test while another worker replaces the owner.
Implement sequentially: save → setters → style → lint. Parallelize only read-only review or known-disjoint work after parent coordination. No shared imports change while tests run.
For each task record source hashes, exact command/cwd/env, collected/pass/fail/skip counts, red assertion, green assertions and controls. A caught failure in a harness with exit 0 is not product success. Collection/import errors are not the required red.
Never retry until green, treat skips/zero tests as pass, weaken baseline controls to fit the parser, or rerun the full suite per patch. A new failure needs diagnosis before another run.
Each task ends at a logical parent-owned commit boundary; workers hand over whitelisted diffs/evidence without committing. Task 5–7 share `lint.py` and must use one coordinated owner.

## Task 1 — Lock accepted records, workspace, base and runner

- [ ] Step 1: Parent records reused complete `SOURCE`, upstream/target and reviewed PR513 head/tree from `E/integration/snippet-fix-integration.json`; apply reviewed `E/integration/final-after` snapshots only where appropriate, then verify runtime bodies/assets against `E/core-repro/source-manifest.json`, allowing only reviewed docstrings/annotations. Expected: explicit source receipt before production edits; no wait for PR513 merge and no host checkout changes.
- [ ] Step 2: Recheck the accepted design/review hashes and adoption above; copy only these accepted records into authorized staging. Expected: design → review → plan precedes source changes; excluded proposal and copies remain unread/unsearched/unhashed.
- [ ] Step 3: Verify the nine named test modules below plus `tests/conftest.py`, `pyproject.toml`, `.pre-commit-config.yaml` and current workflows in `SOURCE`; record any delta from inspected snapshots. Expected: existing test placement and support bounds are accurate.
- [ ] Step 4: Record runner/pytest/private-overlay provenance; import actual `dartwork_mpl`, `io`, `style`, `lint`, `_colors._views` and print/assert their expected `SOURCE/src` paths and versions under isolated env. Expected: no stale installed/wheel-overlay module supplies code; no mutation of core-env or old evidence.
- [ ] Step 5: Assign path ownership and fresh evidence directories; record baseline focused-control failures separately without changing expectations. Expected: Task 2 can immediately write regressions in its owned tests. Parent commit point: accepted records/plan only.

## Task 2 — Save format preflight (design §1)

Owner paths: `src/dartwork_mpl/io.py`, `tests/test_io.py`, `tests/test_orphan_tick_font.py`.
- [ ] Step 1: Add C4 regressions for bad first/later effective format with adoption enabled, snapshots before the call, absent destination and captured diagnostics/warnings. Run `uv run pytest tests/test_io.py tests/test_orphan_tick_font.py`; Expected red: ValueError occurs after forbidden file/tick/diagnostic effects on baseline, exposed by assertions.
- [ ] Step 2: Prepare/retain the ordered output plan once before adoption/draw/validation/stem warning/mkdir/save. Keep `lstrip`, list/generator support and empty effects. Resolve effective override/inference/default/lowercase and SVGZ's forced inner SVG exactly as accepted; retain existing SVGZ duplicate-format failure.
- [ ] Step 3: Check actual current-canvas print attribute first, then registered fallback; explicit backend uses registry-selected class/print attribute. No canvas construction/attachment, savefig or supported-filetype-only shortcut during preflight. Preserve module backend selection without executing untrusted fixtures.
- [ ] Step 4: Run focused tests green and perform actual PNG/PDF/SVG/SVGZ saves; inspect signatures/content, deterministic bytes, metadata and rc isolation. Include `plot.jpgg` containing PNG via `format="png"`, `format=None`, empty/leading-dot/list/single-use generator/order and caller kwargs controls. Expected: successful None returns and prior empty effects remain.
- [ ] Step 5: Exercise current canvas, registered fallback and installed explicit supported/unsupported backend pair; read Matplotlib 3.10.1 resolver source and run this focused I/O test on that minimum only if version-sensitive resolution requires it. Expected: rejection preservation plus successful real output; report optional backends untested. Parent commit point: save-only diff and red/green/live receipts.

## Task 3 — Nine finite setter guards (design §2)

Owner paths: `src/dartwork_mpl/_colors/_views.py`, `tests/test_color_view.py`; controls: `tests/test_color_conversion.py`, `tests/test_shipped_colors_hash.py` (do not modify digests).
- [ ] Step 1: Add all 9 × NaN/±Inf regressions and the Step 3 seeded property before implementation, using pre/post canonical OKLab tuples and ValueError. Run `uv run pytest tests/test_color_view.py`; Expected red: missing rejection/source mutation, including RGB clamps, fails an assertion; observe the property fail too.
- [ ] Step 2: Convert input as currently required, reject nonfinite before clamp/normalization/write, compute replacements before committing coordinates. Preserve nonnumeric rejection and negative chroma, finite RGB clamps, hue normalization, finite extreme L and out-of-gamut RGB no-op precision.
- [ ] Step 3: Verify `random.Random(271828)` property over 32 finite OKLab starts (L in [0,1], a/b in [-0.25,0.25]), all 9 setters and 3 nonfinite values: 864 bounded cases. Expected: ValueError and exact source tuple equality; report seed/input, use no conversion reimplementation or new dependency.
- [ ] Step 4: Run `uv run pytest tests/test_color_view.py tests/test_color_conversion.py tests/test_shipped_colors_hash.py` green; directly import repaired source and replay C5 setters/finite controls. Expected: exact tuples preserved on rejection and original shipped hashes unchanged. Parent commit point: setter-only diff and receipts.

## Task 4 — Style rejection preflight (design §3)

Owner paths: `src/dartwork_mpl/style.py`, `tests/test_style.py`; control: `tests/test_style_chain_parity.py`.
- [ ] Step 1: Add invalid option/value (valid-then-invalid kwargs), unknown name, invalid mixed list and integer cases. Snapshot full live rcParams/semantic tokens before/after and compare subsequent public style transitions with a fresh control. Run `uv run pytest tests/test_style.py tests/test_style_chain_parity.py`; Expected red: immediate C6 rc/semantic mutation; next-scientific alone is already passing and cannot prove repair.
- [ ] Step 2: Resolve complete ordered preset/list and dotted/underscore keys, validate values with isolated Matplotlib RcParams validators, then apply existing successful stack/override path. Expected: no font loading, live updates, semantic or managed-key changes before validation; no mutate-and-rollback strategy.
- [ ] Step 3: Run green with scientific, presentation-kr, valid ordered/empty lists, dotted/underscore aliases and kwargs precedence controls; preserve unknown KeyError and integer AttributeError. Replay source calls and compare immediate state plus subsequent public transition. Expected: managed-key history preserved without deciding C8 precedence. Parent commit point: style-only diff and state receipts.

## Task 5 — Static detection and binding proof (design §4)

Owner paths: `src/dartwork_mpl/lint.py`, `tests/test_lint.py`; catalog is read-only `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`.
- [ ] Step 1: Add C1 comments/strings/definition/local-method false-critical and p/d/ax2 alias regressions; pin no-import canonical plt/ax/fig/dm fragments from existing `TestExtendedRules` and literal-name tests. Run `uv run pytest tests/test_lint.py`; Expected red: false positives/missed alias, while existing fragment diagnostics remain collected and meaningful.
- [ ] Step 2: Build standard-library AST/token spans and small straight-line lexical facts: pyplot/dm/Figure imports; direct Figure/pyplot constructors and direct subplots tuple; scalar Axes only when statically single. Invalidate parameters, assignments/deletes/declarations/shadowing, ambiguous flow and relevant attribute writes; later unconditional imports/constructors may re-establish proof. No cross-scope fact inheritance, runtime execution, arbitrary attribute/alias inference or AST unparse.
- [ ] Step 3: Separate detection's unshadowed canonical snippet convention from autofix proof; suppress explicitly conflicting receivers, unknown attributes and malformed executable claims. Preserve actual string-valued color/name/cmap/hex/jet/width rules, deliberate `zero-resize-mention`, custom detector semantics and existing live registry controls. Expected: no blanket string exclusion; rule IDs/severities/public fields unchanged.
- [ ] Step 4: Run focused detection/fragment/custom/literal controls green, including existing untrusted-marker nonexecution test. Expected: p.style warning, proven ax2 advisory and canonical no-import diagnostics survive; no comment/string/local-method criticals. Parent commit point: detection-only coherent diff.

## Task 6 — Safe autofix and stable occurrence reconciliation

Owner paths remain `src/dartwork_mpl/lint.py`, `tests/test_lint.py`; depends on completed Task 5.
- [ ] Step 1: Add C2 canonical-success/nested-receiver/missing-name/ggplot regressions, invalid/tokenization failures and Step 3 identity cases before implementation. Run `uv run pytest tests/test_lint.py`; Expected red: source corruption/invented binding or false applied occurrence, not harness exit status.
- [ ] Step 2: Allow only complete no-arg proven simple-name Figure tight_layout plus existing unshadowed dm alias; style replacement needs proven pyplot/dm and one supported literal preset. Refuse args, pyplot-only layout, nested attributes, missing/unknown names, dynamic/list/unsupported presets. Malformed input returns exact original and no applied fixes; proven unfixable violations remain unfixed at existing severity.
- [ ] Step 3: Assign rule+original-span/ordinal identities before edits, use nonoverlapping edits and map survivors into result scan. Add mixed fixed/unfixed, repeated same-line, Unicode and CRLF cases; Expected: edited/removed violations alone count applied, original applied offsets and result unfixed offsets remain character based, internal identities disjoint.
- [ ] Step 4: Run `uv run pytest tests/test_lint.py` green; parse accepted outputs and run trusted fixed fixtures through actual dm layout/style source paths; reapply to prove idempotence. Narrowly update only unsafe old rewrite fixtures with explicit accepted refusal reasons. Expected: fragment diagnostics and safety assertions stay strong. Parent commit point: autofix-only coherent diff and actual-fixture receipts.

## Task 7 — Migration byte/literal preservation and seeded source properties

Owner paths remain `src/dartwork_mpl/lint.py`, `tests/test_migrate_legacy.py`, `tests/test_lint.py`; depends on Task 6.
- [ ] Step 1: Add C3 exact triple-string value preservation plus malformed migration refusal (new expectation), f-string text, comments, CRLF/newline/continuations, logical-statement hints and Step 4 properties before implementation. Run `uv run pytest tests/test_lint.py tests/test_migrate_legacy.py`; Expected red: changed literal or rewritten malformed input, including a property assertion; retain valid migration hints rather than deleting their coverage.
- [ ] Step 2: Reuse proven style replacement bounds; add hints only at executable logical-statement boundaries and defer unsafe insertion. Parse the complete proposed result before accepting; never regex-fallback on failed AST/tokenization. Expected: all bytes outside edits and every literal/comment value preserved; invalid proposal returns original.
- [ ] Step 3: Update only existing implicit-name/unsupported-preset/standalone-indented unsafe rewrite fixtures with explanation; use complete valid scopes to retain indentation/hint coverage. Keep standalone canonical diagnostic examples unchanged.
- [ ] Step 4: Verify `random.Random(314159)` with 48 bounded valid fixtures (aliases, comments/literals, Unicode, CRLF, continuations, repeated violations) and 24 deterministic malformed mutations. Assert exact refusal preservation, literal values, parseable accepted output, idempotence and stable occurrence mapping; no dependency or submitted-source execution by static functions.
- [ ] Step 5: Run `uv run pytest tests/test_lint.py tests/test_migrate_legacy.py` green; execute only trusted accepted fixtures against actual dm source. Expected: static functions never execute submitted source and migration does not mutate literal values. Parent commit point: migration/property diff and receipts.

## Task 8 — Independent integration and architecture review

- [ ] Step 1: Run all affected modules once together: `uv run pytest tests/test_io.py tests/test_orphan_tick_font.py tests/test_color_view.py tests/test_color_conversion.py tests/test_shipped_colors_hash.py tests/test_style.py tests/test_style_chain_parity.py tests/test_lint.py tests/test_migrate_legacy.py`. Expected: positive collection, no unexplained skips/failures; inspect actual saved files, state snapshots, returned sources and trusted-fixture runs.
- [ ] Step 2: Run focused Ruff lint/format and available typing using existing configuration; parent runs required locked-environment mypy/pre-commit through existing CI. Expected: tool availability is recorded; missing optional local tools are not claimed green and do not trigger all-extras recreation per patch.
- [ ] Step 3: Independent reviewer checks accepted design against final diff/receipts, security boundary (source remains inert), frozen public/color/discovery surfaces and ownership boundaries. No architecture reshaping is intended; if implementation adds cross-owner dependencies, stop for scope review. Expected: no unresolved Important/Critical finding and mechanical assertions remain the stopping oracle.
- [ ] Step 4: Compare normal successful render controls with baseline. If any visible change exists, provide actual before/after PoC at matching scale before merge, with project Tailnet rules for browser links. Expected: no forced cosmetic changes; artifact evidence is accessible. Parent commit point: reviewed integration candidate.

## Task 9 — Parent PR, required gates, merge and cleanup

- [ ] Step 1: Parent refreshes actual target, verifies merged PR513 tree/base or reconciles changed overlap, reruns affected checks for real changes, and stages only accepted records plus whitelisted core source/tests. Expected: unrelated PR513/protected-host work cannot leak into core commits.
- [ ] Step 2: Parent opens/updates core PR with per-repair failures, controls, actual behavior evidence and limits; obtain independent review and required checks from current branch protection/workflows. Existing `.github/workflows/ci.yml` and `pre-commit.yml` define CI; do not change their matrix or count a prior PR/head's green as core validation.
- [ ] Step 3: Parent resolves real review/CI findings, rechecks current final head and merges only with its own required gates passed. Expected: no full-suite retry loop, skip-as-pass, inherited PR513 result or unprobed whole-issue closure claim.
- [ ] Step 4: Preserve final logs/hashes and actual artifacts under `E`, remove task-created temporary staging/worktrees/services after handoff, and leave existing evidence/env intact. Expected: no retained evidence in `/tmp`, no clone per variant, no outstanding worker ownership; final report names checks and remaining unmeasured cases.
