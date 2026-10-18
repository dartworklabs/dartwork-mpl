# MCP Contract Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair bundled asset confinement, ordinary execution output, and incomplete validation in the existing MCP workflow.

**Architecture:** Put the MCP asset acceptance policy in one feature-local resolver. Preserve native validation lists with additive failure warnings, and separate snippet stdout from the MCP runner's JSON result.

**Tech Stack:** Python >=3.10, native Matplotlib/Agg, existing FastMCP, pytest, uv, Ruff and mypy; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-18-mcp-contract-stability-design.md`

## Global Constraints

- Python >=3.10; no new dependencies.
- Keep Matplotlib Figure/Axes native and `validate_figure` returning a list.
- Keep existing tool/resource names, successful template contents, and advanced-to-basic fallback.
- Keep trusted local execution semantics, inherited cwd, and snippet save side effects.
- Preserve hint-conditional `semantic_warnings` and existing execution failure statuses.
- Shipped color values and their pinned digests remain frozen; no UI/style change.

## Review Focus

1. JSON-looking or multiline prints and `dm.save_formats` logs must not corrupt results.
2. One failed check beside successful warnings must remain visible in quiet/native and MCP output.
3. Encoded traversal through an actual resource URI must never return an outside sentinel.
4. A valid-looking stem symlink outside its asset root must fail in resources and render/compose tools.
5. Errors before validation, including timeout and no figure, must never imply completed validation.

---

## Current authority and execution

No Handbook exists. Read `AGENTS.md`, `pyproject.toml`, `.github/workflows/ci.yml`,
and the source paths in each task; the spec's four authority sections apply here.
The user authorized the diagnosed first delivery and requested execution. Parent
orchestration owns review, dispatch and integration; workers own product edits.
Before product edits, confirm the fetched target still matches the checked base
(`e544273c` at planning); preserve other workers' changes and recheck before integration.
The two tasks have independent behaviors but both wire into `mcp/tools.py`;
apply their wiring sequentially or coordinate hunks explicitly.
Commit steps below are checkpoints, not authorization to commit during planning.
Tests stay under `tests/` because `pyproject.toml` sets `testpaths=["tests"]`.

### Task 1: Confine all bundled MCP asset access

**Files:**
- Create: `src/dartwork_mpl/mcp/_assets.py` — complete ID parsing and resolved-root checks.
- Modify: `src/dartwork_mpl/mcp/resources.py` — basic/advanced/style callbacks use the resolver.
- Modify: `src/dartwork_mpl/mcp/tools.py` — existing render/compose resolver delegates.
- Test: `tests/test_mcp.py` — registered callback contract and existing tool regressions.
- Create test: `tests/test_mcp_asset_boundary.py` — real URI decoding, files, symlinks and generated malformed IDs.

**Interfaces:**
- Consumes: bundled `asset/prompt/05-templates/` and `asset/mplstyle/`; existing callback response families.
- Produces: `_assets.resolve_template_path(plot_type: str, *, advanced: bool = False) -> Path | None` and `_assets.resolve_style_path(preset: str) -> Path | None`.
- Template IDs normalize lowercase and match `[a-z0-9_]+`; styles match `[A-Za-z0-9_-]+` with existing case semantics. Returned paths are resolved regular files under the selected resolved root.
- `_resolve_template_path` in tools may remain a shim; no duplicate policy. Advanced fallback invokes the same boundary twice.

- [ ] **Step 1: Write failing boundary tests.** `test_resource_rejects_path_escape` supplies literal, percent-encoded, double-encoded, backslash, absolute, empty and NUL IDs to basic/advanced/style routes; assert no outside sentinel is returned. `test_encoded_uri_cannot_escape` reads real registered FastMCP URIs. `test_asset_symlink_cannot_escape` builds real outside sentinel files and valid-looking symlinks; resources reject and render/compose return `unknown_template` without code/image content.
- [ ] **Step 2: Write compatibility and invariant tests.** `test_bundled_assets_remain_readable` compares basic/advanced/style results to their real files, including uppercase template IDs, hyphenated and underscored styles. `test_advanced_resource_falls_back_safely` uses a basic-only fixture. `test_generated_invalid_ids_never_escape` uses seeded generated IDs and asserts rejection or a real path under the designated root, never an outside read. Document the seed on assertion failure; use no new test dependency.
- [ ] **Step 3: Observe red.** Run `uv run --no-sync pytest tests/test_mcp_asset_boundary.py tests/test_mcp.py -k 'escape or encoded_uri or symlink or bundled_assets or falls_back or generated_invalid' --no-cov -q`. Expected: traversal/symlink assertions fail against current callbacks, not because of setup or imports.
- [ ] **Step 4: Implement the two resolver interfaces in `_assets.py`.** Parse complete stems, resolve and confine paths, require files, return `None` on invalid/missing candidates. Rewire resources and tool resolver; retain existing error families and fallback. Keep scope local to MCP; no unrelated capability relocation.
- [ ] **Step 5: Observe green.** Run `uv run --no-sync pytest tests/test_mcp_asset_boundary.py tests/test_mcp.py tests/test_mcp_heavy_tools.py tests/test_mcp_render_smoke.py --no-cov -q`. Expected: all collected tests pass, including real resource reads and existing bundled renders.
- [ ] **Step 6: Review/checkpoint.** Review no resource or template tool bypasses `_assets`; no outside sentinel appears in responses and no shipped asset changed. Suggested checkpoint: `fix: confine MCP bundled asset resolution` with only this task's files; parent decides whether to commit.

### Task 2: Preserve logs and expose incomplete validation

**Files:**
- Modify: `src/dartwork_mpl/validate/_orchestrator.py` — failed-check warnings in the existing list.
- Modify: `src/dartwork_mpl/mcp/tools.py` — isolated result framing and normalized envelope.
- Modify test: `tests/test_validate.py` — observable native quiet/nonquiet failure results.
- Create test: `tests/test_mcp_validation_contract.py` — real subprocess, save, fault and status integration.
- Modify docs: `docs/integrations/mcp_server.md` and relevant `tools.py`/native docstrings — additive fields and trusted local execution limits.

**Interfaces:**
- Consumes: `validate_figure(fig, *, checks: tuple[str, ...] | None = None, quiet: bool = False) -> list[VisualWarning]`; existing `VisualWarning` and registered checks.
- Produces: existing list plus `CHECK_FAILED` WARNING entries with `detail={"check_id": original_id}` for currently tolerated check exceptions; successful warnings are retained in registry order.
- MCP keeps its input signature; all responses add `stdout: str`, `validation_complete: bool`, `failed_checks: list[str]`. Known check failures produce `status="validation_incomplete"`, `false`, original IDs; completed runs produce `true`, `[]`. Pre-validation/error statuses produce `false`, `[]` unless failures are known. `stderr` and hint-conditional semantic fields persist.

- [ ] **Step 1: Write failing native report tests.** `test_failed_check_is_returned_quietly` injects one registered `BBOX_ERRORS` failure and asserts a list containing WARNING `CHECK_FAILED`, `detail["check_id"]` equal to its original ID, and no stdout. `test_failed_check_preserves_other_warnings` combines failure with a real successful warning and asserts both in deterministic order. `test_failed_check_never_prints_clean` asserts nonquiet failure output names the check and contains no success verdict. Keep unexpected native exceptions observable; do not assert private helper calls.
- [ ] **Step 2: Write failing subprocess workflow tests.** `test_validate_print_and_save_output` discovers a real template, builds a native figure with the required `dm` APIs, prints multiline/JSON-looking text, writes to stdout with `os.write`, saves a PNG to a test-owned temp dir, and asserts `ok`, a valid PNG, captured `stdout`, `validation_complete is True`, and `failed_checks == []`. `test_mcp_failed_check_is_incomplete` registers a fault inside the snippet so it exists in the child, then asserts the original ID and `CHECK_FAILED` survive with successful warnings and requested semantic fields.
- [ ] **Step 3: Pin all other statuses.** `test_validation_not_complete_on_early_exit` covers `lint_blocked`, `exec_error`, `no_figure` and a bounded real timeout; assert `false`, `[]`, string `stdout`, and semantic field presence iff hinted. A print-before-error case preserves logs. `test_unexpected_validation_exception_is_error` raises an unexpected fault during validation and asserts a visible error, never `ok`; no process-control exception suppression is added.
- [ ] **Step 4: Observe red.** Run `uv run --no-sync pytest tests/test_validate.py tests/test_mcp_validation_contract.py -k 'failed_check or print_and_save or validation_not_complete or unexpected_validation' --no-cov -q`. Expected: new returned-warning and envelope assertions fail against current behavior; preserve the failing output.
- [ ] **Step 5: Implement native failed-check entries.** Use the existing tolerated exception policy; represent failed selected checks in the returned warning list. Reuse the ordinary warning print path so quiet mode changes only output. Do not add a public report object or mutate check registration semantics.
- [ ] **Step 6: Implement runner/envelope changes.** Serialize the internal JSON result to a private temporary result file and read it independently of captured subprocess stdout. Clean up the private channel without changing cwd. Add normalized fields to all statuses; derive failed IDs from `CHECK_FAILED` detail. Catch runner validation errors into visible execution errors. Preserve real save effects, timeout, stderr, lint gate, figure fallback and semantic field shape. Update the owned docs/docstrings to match.
- [ ] **Step 7: Observe green.** Run `uv run --no-sync pytest tests/test_validate.py tests/test_validate_accessibility.py tests/test_validate_fixes.py tests/test_mcp_validation_contract.py tests/test_mcp.py tests/test_mcp_tool_hardening.py --no-cov -q`. Expected: all collected tests pass with real subprocess/save observations.
- [ ] **Step 8: Review/checkpoint.** Review every return path, quiet/nonquiet parity and mixed warnings; document hostile snippet limits without sandbox claims. Suggested checkpoint: `fix: preserve MCP logs and incomplete validation` with this task's files; parent decides whether to commit.

## Integration gate and handoff

- [ ] Run `uv run --no-sync ruff check src/ tests/`, `uv run --no-sync ruff format --check src/ tests/`, and `uv run --no-sync mypy src/dartwork_mpl/`; all must pass.
- [ ] Run `uv run --no-sync pytest tests/test_mcp_asset_boundary.py tests/test_mcp_validation_contract.py tests/test_mcp.py tests/test_mcp_heavy_tools.py tests/test_mcp_tool_hardening.py tests/test_mcp_render_smoke.py tests/test_mcp_validators_complete.py tests/test_cli.py tests/test_drift.py tests/test_shipped_colors_hash.py tests/test_docs_mcp_tools.py --no-cov -q`; all must pass with FastMCP installed and nonzero collection. Existing CI still owns the full matrix and pixel gate.
- [ ] Compare diff with the spec and five review cases, recheck target freshness, and preserve red/green commands/results in session evidence. Report checks not run and any remaining failures; do not regenerate frozen color hashes.
- [ ] Parent reviews both task deliverables and documentation; then reports actual behavior and verification to the user. No UI PoC is needed because chart appearance and interaction are unchanged.

The later artifact, data-repair and agent-evaluation milestones in the spec are
future work. The immediate baseline is deterministic workflow contract coverage;
do not present it as an LLM evaluation or implement those later systems here.
