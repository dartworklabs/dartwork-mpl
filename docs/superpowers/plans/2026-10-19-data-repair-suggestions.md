# Plot-data Repair Suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in, reviewable numeric representation proposals to the existing data-validation tool without changing legacy responses or applying changes.

**Architecture:** A pure MCP data-validation module owns bounded parsing, typed outcomes, scoped checks and strict JSON encoding. The existing tool selects legacy or report behavior and supplies catalog membership from its existing dispatch. Reports preserve original input and produce detached candidates only for the five approved plot types.

**Tech Stack:** Python >=3.10, standard-library decimal/JSON, pytest, seeded generated properties, real FastMCP Client.

**Spec:** `docs/superpowers/specs/2026-10-19-data-repair-suggestions-design.md`; approved by “이 설계로 구현 진행 (권장)” on 2026-10-19. Chain: approved brainstorming/spec → this writing-plans plan → delegated execution; no further approval gate is needed.

**Status:** Implemented; local acceptance and whole-branch review passed through `6172a212`. M1/M2 fixes passed focused local checks; fix-wave re-review, updated docs build/PoC and remote CI pending; no merge or remote-CI success claimed.

## Global Constraints

- Python >=3.10, FastMCP >=2.13.3,<4; installed evidence is 3.4.2. Add no dependencies or CI jobs.
- Public signature: `validate_plot_data(plot_type: str, data_json: str, report: bool = False) -> str`; omitted calls retain exact legacy behavior; false selects that same parser/dispatch/string path with the framework-boundary clarification below.
- Framework compatibility: prechange explicit false was always an unexpected keyword. All 62 omitted requests remain exact; 60 new false calls containing both required fields match old omitted exactly. Two missing-required false calls match the same error category/location and full envelope after removing only the echoed `report:False` input flag. Existing frameworks own argument validation; no override.
- Only `scatter`, `bar`, `bar_horizontal`, `histogram`, `heatmap` have report coverage; remaining recognized types return `unsupported`. Normalize using `.lower()` only.
- Admission limits: 65,536 UTF-8 bytes, nesting depth 16, 10,000 value/key tokens, 100 issue records total across `issues` plus `candidate.remaining_issues`, 100 changes, 1,048,576 serialized report bytes. No silent truncation. If normalized `plot_type` alone cannot fit a refusal, return `plot_type:""`, false membership/coverage and bounded issue metadata `{field:"plot_type",bytes:...}` or lower bound; normal names remain exact.
- Report fields, presence rules, issue codes, ordering and numeric grammar/range policy are exactly the spec's “Report contract v1”, “Proposal and manual-action policy” and “Parsing, limits and responsibility”.
- Preserve exact raw text and mathematical number values, including `1e309`, with decimal/token-aware parsing and strict serialization; binary64 checks must not rewrite unchanged input numbers.
- Invalid-UTF8 Python strings fail byte admission with typed `rejected` / `invalid_json`, omitting `original`: JSON escaping could recombine literal paired surrogates and misstate raw preservation. Valid UTF-8 syntax errors within budgets retain exact raw text.
- All candidates require review; no apply/render/store/execute path, payload logging, transport registration, color/baseline changes, Handbook initialization or ADR changes.
- Pure module imports no transport, artifact, plotting, filesystem or network code; this extends the existing data-validation capability and creates no shared slice.
- Tests live under `tests/` because `pyproject.toml` excludes source tests; reuse existing CI pytest and formatting/type checks.

## Review Focus

- Extreme original numbers and unknown fields retain mathematical values; `1e309` yields a numeric-range issue only in declared numeric fields. Task 1 pins this with Decimal-based decoding.
- Escaped pointer keys and multibyte/invalid Unicode cannot bypass byte limits or create ambiguous diagnostics. Task 1 covers lexical unknown-path order and safe rejection.
- Mixed safe strings and manual shape/type errors produce a partial candidate with `valid:false`; Task 1 proves revalidation and idempotence.
- Duplicate histogram edges are valid; decreasing edges need manual input. Scalar bins require positive JSON integer tokens (`10` accepted; `10.0`, `1e1`, `"10"` manual), with no scalar coercion; array edges may be floating point. Task 1 covers these boundaries.
- A malformed request for an unknown plot retains legacy parser precedence with `report=False`; Task 2 compares actual Client captures on both supported runtime versions.

## Preserved Handbook Context

No Handbook exists; the following current source/test authority remains distinct from the approved target behavior.

### 현재 권위와 상태

- role: purpose; path: `AGENTS.md`, `README.md`; native matplotlib design system; MCP validation is advisory; templates are examples.
- role: runtime-data-validation; path: `src/dartwork_mpl/mcp/tools.py` (`validate_plot_data`, `_validate_*`); two required strings, JSON parsing, 18-validator dispatch; many legacy checks are permissive.
- role: wire-contract; path: `src/dartwork_mpl/mcp/server.py`, `tests/test_mcp_tool_hardening.py`, `tests/test_mcp_validators_complete.py`, `.superpowers/data-repair-2026-10-19/contract-audit/actual-tools.json`; actual discovery is 18 tools / 10 resources / 9 templates / 2 prompts; installed FastMCP 3.4.2 wraps string output as `{result:string}`.

### 지켜야 할 현재 불변식

- role: frozen-color; path: `tests/test_shipped_colors_hash.py`, `tests/test_color_v6_comparison.py`, `src/dartwork_mpl/_colors/_catalog.py`; shipped values, digests, historical baseline, exact legacy discovery projection and full runtime identities/order stay fixed.
- role: accepted-decision; path: `docs/adr/0001-oklab-centered-color-construction.md`, `docs/adr/0003-allow-scoped-mcp-artifact-discovery.md`; ADR 0003 permits exactly its two tools/five artifact templates; another identity requires separate approval. Optional arguments on an existing identity do not alter this frozen surface.
- role: docs-policy; path: `AGENTS.md`; design <=200 lines; executable completion criteria; use a mechanical decider before adversarial review.

### 설계 이유와 제약

- role: compatibility-evidence; path: `.superpowers/data-repair-2026-10-19/contract-audit/report.md`; optional `report: bool` with `-> str` preserves old framing/output schema; native structured union broadens published output schema.
- role: dependency-and-CI; path: `pyproject.toml`, `.github/workflows/ci.yml`; Python >=3.10, FastMCP >=2.13.3,<4; installed evidence is 3.4.2. User requested light tests/CI; add no dependency or redundant pipeline.

### 충돌·미확인

- role: missing-handbook; path: none; no initialization authorized; source/tests and accepted scoped ADRs govern.
- role: contract-gaps; path: `.superpowers/data-repair-2026-10-19/case-audit/recommendation.txt`, `current-behavior.json`, `proposed-cases.json`, `src/dartwork_mpl/mcp/tools.py`; metadata/validators differ; a legacy checkmark cannot establish new validity. Line/category/time ambiguity, grouped aliases and contour meshes are deferred.

## File Ownership and Shared Interface

- Task 1 owns `src/dartwork_mpl/mcp/data_repair.py`, private `src/dartwork_mpl/mcp/_data_repair_json.py`, `tests/mcp/data_repair/test_reports.py`, `tests/mcp/data_repair/test_limits.py`, `tests/mcp/data_repair/test_properties.py`, `tests/mcp/data_repair/fixtures/reports.json`.
- Task 2 owns `src/dartwork_mpl/mcp/tools.py`, `tests/test_mcp_data_repair_contract.py`, `tests/mcp/data_repair/fixtures/legacy_calls.json` and its reproducible capture script `.superpowers/data-repair-2026-10-19/implementation/capture_legacy.py`.
- Task 3 owns `docs/integrations/mcp_server.md`, `docs/ai/index.md`; final orchestrator runs integration checks. Task 3 prose may proceed alongside Task 1 without editing Task 2's tool docstring.
- Export exactly `DataRepairReport`, `build_data_repair_report`, `serialize_data_repair_report` from the pure module with `__all__`.
- The public report module imports private pure token parsing/encoding one-way from `_data_repair_json.py` inside the same capability; no new slice or public surface.
- `build_data_repair_report(plot_type: str, data_json: str, *, recognized: bool) -> DataRepairReport` accepts normalized name and caller-supplied membership, semantically parses once, and returns typed outcomes.
- `serialize_data_repair_report(report: DataRepairReport) -> str` returns strict deterministic JSON and enforces final output budget with a small typed refusal if necessary.
- `DataRepairReport` is a closed typed union of explicit admitted, syntax-rejected, encoding-rejected and limit-rejected outcomes, carrying only applicable fields; exact private type names are worker-owned. Do not expose dict-or-string unions or exception-derived fallback outcomes.

### Task 1: Pure bounded parser and report engine

**Files:** Task 1 ownership above. **Consumes:** approved spec and supplied `recognized`. **Produces:** the three exported names and signatures above; no duplicated 18-name catalog.

- [x] **Step 1: Pin independent observable report fixtures before implementation.** In `fixtures/reports.json`, encode both spec examples and clean/candidate/manual cases for every supported shape. In `test_reports.py`, assert exact selected report members, stable issue/action paths, ordering, original preservation, scoped validity and `effects == "none"`; fixtures are the review decider, not output copied from implementation.
- [x] **Step 2: Observe the first red run.** Run `uv run pytest tests/mcp/data_repair/test_reports.py -q`; expected FAIL because the module/behavior is absent. Save output in `.superpowers/data-repair-2026-10-19/implementation/`.
- [x] **Step 3: Implement the pure exported interface.** In `data_repair.py` and private `_data_repair_json.py`, preflight bytes/depth/value-and-key token counts before one semantic JSON decode; reject duplicates, nonstandard constants and trailing content. Distinguish invalid-UTF8 encoding refusal without `original` from syntax rejection retaining valid-UTF8 raw text. Use Decimal or preserved numeric lexemes and an explicit strict encoder so unknown/unchanged numbers never pass through float. Refusals are typed results, not broad exception catches.
- [x] **Step 4: Implement only declared-field checks and safe proposals.** Match the spec's exact grammar and decimal equality after shortest binary64 serialization; preserve negative zero by rejecting negative-zero strings, reject unsafe integer-valued results beyond `±(2**53-1)`, overflow/nonzero underflow and lossy strings. Deep-copy admitted input for candidates, never mutate observations or unknown fields, and revalidate the full scoped candidate with the same rules.
- [x] **Step 5: Add edge assertions to `test_reports.py`.** Assert unchanged categories `['01','02']`, `numeric_range` for original `1e309`, exact decoded Decimal preservation in both payloads, rejected strings `'-0'`, `' 1'`, `'01'`, `'1e309'`, `'1e-400'`, `'9007199254740992'`; bool/null yield manual issues. Assert mixed repair/unequal lengths yields `proposal` and candidate `valid:false`, ragged related-row lengths, duplicate bins accepted, decreasing bins rejected, scalar JSON `10` bins accepted but `10.0`/`1e1`/`"10"` manual and never changed, unknown names distinct from unsupported recognized names.
- [x] **Step 6: Add budget and parser tests in `test_limits.py`.** Exercise each exact limit and one over, including nested valid input at depth 16 versus 17, 100 versus 101 total original-plus-remaining issue records and changes, multibyte byte counts, malformed/trailing input, duplicate decoded keys, escaped `~`/`/` unknown paths, NaN/Infinity and invalid surrogates (including literal pairs). Force output-size refusal with admitted repeated raw/candidate data; test giant, escaped and lone-surrogate plot names. Assert strict JSON, bounded refusal count/limit metadata, omitted payload/candidate for limits and omitted original for encoding refusals, no silent truncation, and the spec's empty-name fallback only when echoing the name cannot fit.
- [x] **Step 7: Add seeded properties in `test_properties.py`.** Generate bounded admitted structures and arbitrary text; assert no uncaught exception, deterministic text, exact raw input, Decimal-equivalent unchanged values/order/lengths/unknown fields, detached candidate mutation leaves original intact, clean candidate resubmission has no changes, and successful strict serialization. Generate mixed manual/proposal cases rather than only valid examples.
- [x] **Step 8: Verify and challenge the oracle.** Run `uv run pytest tests/mcp/data_repair -q`; expected PASS. Temporarily bypass candidate revalidation, loosen one conversion guard and disable one predecode budget, one mutation at a time; the corresponding focused assertion must fail. Restore immediately; save red/green/mutation evidence without cloning a repository for each mutation.
- [x] **Step 9: Commit point.** After worker review and restored passing checks, stage only Task 1 files; logical commit `feat(mcp): add bounded reviewable data repair reports`. Parent controls commits/integration; worker must not commit unless delegated.

### Task 2: Existing-tool opt-in and real wire compatibility

**Files:** Task 2 ownership above. **Consumes:** Task 1's exact exports. **Produces:** `validate_plot_data(plot_type: str, data_json: str, report: bool = False) -> str` with unchanged registration identity and output schema.

- [x] **Step 1: Capture prechange behavior before editing `tools.py`.** Extend existing reproducible Client audit patterns to all 18 plot types plus malformed JSON, unknown names, unknown+malformed precedence, wrong containers and wrong argument types. Save request, raw text, structured result/error and discovery schema in `legacy_calls.json`, with baseline SHA/runtime. If another task has edited tools, capture the untouched `origin/main` module in one temporary detached worktree and clean it on exit.
- [x] **Step 2: Add red contract tests.** In `test_mcp_data_repair_contract.py`, use real FastMCP Client to assert omitted/false calls equal captures under the framework-boundary rule above, true returns a string containing a version-1 report, optional `report` defaults false, required string fields/output schema stay fixed, and discovery remains 18/10/9/2 with exact identities/order. Assert supported uppercase lowercases while whitespace is not stripped. Run `uv run pytest tests/test_mcp_data_repair_contract.py -q`; new opt-in/schema assertions must FAIL first.
- [x] **Step 3: Wire the existing function.** Reuse the existing validators mapping for membership, branch into Task 1 builder/serializer only when `report` is true, and leave legacy parse-before-unknown behavior and validators unchanged. Do not parse `data_json` before selecting the opt-in branch. Update only this function's docstring to describe the JSON-string report; no server registration/type union is added.
- [x] **Step 4: Verify both actual runtimes without altering shared dependencies.** Run the contract file plus `tests/test_mcp_tool_hardening.py` and `tests/test_mcp_validators_complete.py` through real Clients on installed FastMCP 3.4.2 and isolated FastMCP 2.13.3. Create one temporary venv per version if required, install this checkout editable with pytest, and pin the runtime there; use cleanup on every exit. Save versions/commands/call evidence under `.superpowers/data-repair-2026-10-19/implementation/`, never reference temporary paths in handoff. Expected: omitted/false captures match under the framework-boundary rule above; opt-in retains version-specific string framing/output schema.
- [x] **Step 5: Commit point.** After worker review, stage only Task 2 files; logical commit `feat(mcp): expose opt-in data repair reports`. Parent controls commits/integration; worker must not commit unless delegated.

### Task 3: Public contract documentation and integrated acceptance

**Files:** Task 3 ownership above. **Consumes:** exact signatures and fixture contract from Tasks 1–2. **Produces:** public usage documentation and recorded integrated verification.

- [x] **Step 1: Document a concrete opt-in call.** Update `docs/integrations/mcp_server.md` and its existing AI overview in `docs/ai/index.md` with the optional false default, JSON string inside MCP result and second decoding, five named types, review-required before/after example, partial candidate possibility, unknown fields/declared-field validity, numeric/manual boundaries, all limit values and `effects:none`. State the caller chooses what data to use; templates remain standalone Python examples. This is prose/API documentation, no visual template redesign.
- [x] **Step 2: Review documentation against fixtures and live tool schema.** Verify names, exact fields and example numbers against `fixtures/reports.json`, `data_repair.py` exports and the real Client schema. Expected: no claimed automatic repair, whole-renderer validity or extra registered identity. Pin examples by meaningful behavioral tests from Tasks 1–2; do not add tests that assert prose wording.
- [x] **Step 3: Run the integrated affected gate once after final changes.** Run `uv run pytest tests/mcp/data_repair tests/test_mcp_data_repair_contract.py tests/test_mcp_tool_hardening.py tests/test_mcp_validators_complete.py tests/test_color_v6_comparison.py tests/test_shipped_colors_hash.py -q`; expected PASS with nonzero collection, untouched color/discovery baselines. Run `uv run ruff check` and `uv run ruff format --check` on changed Python files, then `uv run mypy src/dartwork_mpl/` as configured in existing CI. Broaden/repeat only for new failures or changes.
- [x] **Step 4: Review local scope and record acceptance evidence.** All eight executable spec criteria, independent fixtures, import purity, entry-point policy/known gaps, unchanged dependencies/jobs/artifact/logging/baselines and targeted mutation evidence checked; scoped reviewers approved. Tested versions, first-red evidence, limits and commands recorded in `.superpowers/data-repair-2026-10-19/implementation/summary.md`; final whole-branch review remains separate below.
- [x] **Step 5: Public documentation commit point.** Parent committed reviewed Task 3 public docs as `226cddc5` (`docs(mcp): explain reviewable data repair reports`). Parent retains the final acceptance-record commit and integration; worker performs no git mutation.
- [x] **Final integration review:** whole branch through `6172a212` approved with no Critical/Important findings; M1/M2 addressed in a focused diagnostic/docs fix wave, M3 dependency warnings deferred.
- [ ] **Final fix-wave re-review and delivery:** parent reviews the M1/M2 diff and refreshes affected docs build/PoC before integration. PR/remote CI and merge remain pending.

## Evidence and Handoff

Existing `contract-audit/actual-default-calls.json` covers eight default calls and `existing-contract-checks.txt` reports 17 passing checks; neither proves this feature or all 18 defaults. Task 2 closes those gaps. All durable evidence stays under `.superpowers/data-repair-2026-10-19/`, outside datasets and temporary directories.

Plan self-review: all eight acceptance criteria map to Tasks 1–3; public helper names/types agree; each Review Focus item has an owning test step; limits and role/path context are preserved. Execution is already authorized and delegated by the orchestrator; proceed without another plan/method approval question.

(local-validation-ledger)=
## Local validation ledger (2026-10-19)

- Task 1 committed through `b9dacd95`: 102 engine tests, independent fixtures/properties and three assertion-killed mutations with restoration; scoped review approved. Local worker report: `.superpowers/sdd/2026-10-19-data-repair-suggestions/task-1-report.md`.
- Task 2 committed `7e83a153`: 199 tests per actual FastMCP 2.13.3/3.4.2, 62 exact omitted and 60 exact false calls, two missing-required errors under the echoed-flag rule; scoped review approved by parent. Local runtime/capture evidence: `.superpowers/sdd/2026-10-19-data-repair-suggestions/task-2-report.md`.
- Integrated gate: 409 passed; Ruff lint/format on seven changed Python files and mypy on 107 source files clean; existing OpenTelemetry/Authlib deprecations disclosed. Local acceptance evidence and commands: `.superpowers/data-repair-2026-10-19/implementation/summary.md`.
- Sphinx `-W` and actual public docs Client snippet passed; same-scale desktop/mobile rendered PoC and all eight images verified over persistent Tailnet HTTPS. Local rendered evidence: `.superpowers/data-repair-2026-10-19/docs-preview/`. Local operational reference outside the product repo: `~/scratch/dartwork-mpl-data-repair-preview-2026-10-19/delivery-report.md`.
- Whole-branch review through `6172a212` approved; M1 now explicitly rejects unaudited FastMCP captures, M2 documents integer/float Decimal decoding and decoder limits. Fix-wave checks: 153 contract tests passed with one existing OpenTelemetry warning, Ruff lint/format, existing docs-example helper and focused decoder/runtime-diagnostic probes passed. M3 dependency deprecations remain deferred and visible.
- No new dependency, CI job, registration or color/discovery baseline edit. Fix-wave re-review, updated docs build/PoC and remote CI remain pending; these local results do not establish merge readiness.
