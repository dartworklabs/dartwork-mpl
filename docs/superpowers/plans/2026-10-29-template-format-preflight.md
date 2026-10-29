# Template Format Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refuse invalid selected-template formats before execution/temp/publication with exact existing error envelopes.

**Architecture:** Keep selection and refusal in the existing template render boundary. Reuse `RenderFailed`/`_reply_fields` if useful; preserve all existing outcome variants and wrapper registration bytes.

**Tech Stack:** Python >=3.10, FastMCP real Client, pytest, existing Ruff/mypy.

**Spec:** [Approved B/C design](../specs/2026-10-29-input-preflight-design.md), especially current authority, invariants and C.

## Global Constraints

Python >=3.10; no new dependency, CI gate or public API.
Keep signatures/static types, MCP names/order/schemas/registered docstrings and 19/10/9/2 discovery unchanged.
Keep artifact v1, shipped colors, presets and ADR 0001–0005 unrelated locks unchanged.
Work locally only; no fetch/network, remote writes, PR, messages, services or account workaround.

Read the spec's four authority/invariant/reason/unverified sections; approved intent is not current runtime.
No Handbook initialization. No protected-checkout or excluded-document/copy access.
Parent venv is read-only; explicit target PYTHONPATH, no bytecode, scratch cache/temp roots.
C owns render.py/colocated tests and narrow additions to `tests/test_mcp_render_smoke.py`.
Necessary guide edits belong only in `docs/integrations/mcp_server.md`; parent owns shared CHANGELOG/bundles.

## Review Focus

1. Unknown+invalid must keep complete old reply before format checks; test both tools.
2. Installed basic IDs all have advanced peers; scratch basic-only fixture must prove actual fallback.
3. Fallback rejection carries tier basic and render_error with no fell_back key; compare exact dict.
4. Deleted temporary directories still count as effects; audit creation, not just final inventory.
5. Wire text and structured payload must agree with isError=false; use real Client.

---

### Task 1: Preflight after selection, before any render effects

**Files:**
- Modify: `src/dartwork_mpl/mcp/templates/render.py` (`render_basic`, `render_advanced`).
- Create/Test: `src/dartwork_mpl/mcp/templates/tests/test_format_preflight.py` (exact boundary replies/effects).
- Modify/Test: `tests/test_mcp_render_smoke.py` (real Client contract coverage only).
- Read/replay: `src/dartwork_mpl/mcp/templates/tests/test_outcomes.py`.
- Modify only if necessary: `docs/integrations/mcp_server.md` (exact supported format values).

**Interfaces:**
- Consumes: existing bundled selection and `RenderOutcome` variants; `_reply_fields(outcome: RenderOutcome) -> tuple[str, str | None, str | None, str]`.
- Produces unchanged: `render_basic(plot_type: str, return_format: str, timeout_seconds: float) -> dict[str, Any]` and `render_advanced(plot_type: str, return_format: str, timeout_seconds: float) -> dict[str, Any]`.
- Invalid-format result is precisely the spec dict; advanced adds only the selected tier, basic has none.

- [ ] **Step 1: Capture valid compatibility baseline before source edits.**

Under worker-owned scratch `c/baseline` and `c/changed`, save source SHA/import origin and installed FastMCP/Matplotlib versions.
Set `PY=/Users/wonjun/.t3/worktrees/dartwork-mpl/t3-0c3dff26/.venv/bin/python` (read-only);
set explicit target `PYTHONPATH="$PWD/src"`,
`PYTHONDONTWRITEBYTECODE=1`, `MPLBACKEND=Agg` and scratch `MPLCONFIGDIR`, `XDG_CACHE_HOME`, `TMPDIR`.
Use the real `fastmcp.Client(mcp)` with `dartwork_mpl.mcp.server.mcp`, not only `_tools_map()`.
Capture full text/structured replies and decoded PNG SHA-256 for both tools with bar/base64 and bar/path.
Create scratch basic-only assets with empty advanced directory and a deterministic real PNG-producing template;
redirect only `mcp._platform.assets._TEMPLATE_DIR` and `mcp.templates.bundled._TEMPLATE_DIR` in a restoring context.
Capture advanced valid base64/path fallback (status fell_back, tier basic).
Use a scratch sleep template and timeout_seconds=0.5 through each real tool; capture actual timeout envelopes.
Replay existing publication-failure and path/privacy/symlink fixtures named in Step 5 on this unchanged baseline.
Delete only worker-owned published files in finally; never edit installed assets or render behavior.
Expected: baseline saved on `33f51edd`; no baseline result is labeled changed-source GREEN.

- [ ] **Step 2: Write failing exact-reply and no-effect regressions.**

`test_selected_template_rejects_invalid_format_without_effects`: basic bar, advanced bar and actual basic-only fallback;
parameterize formats `bogus`, `""`, `PATH`, ` base64`. Assert exact dict from spec, selected tier only for advanced.
```python
assert reply == expected
assert reply["png_base64"] is reply["png_path"] is None
assert "fell_back" not in reply
assert creation_events == []
assert temp_tree_after == temp_tree_before
```
Observe real execution: run audit-hook observations in an isolated process (hooks cannot be removed), enabling only around calls;
record `subprocess.Popen`, `tempfile.mkdtemp`, `tempfile.mkstemp`, `os.mkdir`, plus isolated temp-root inventory.
Do not replace renderer/process functions; final inventory alone cannot prove no creation.
`test_unknown_selection_precedes_invalid_format`: both tools on installed and scratch roots, exact old unknown replies
including sorted basic/advanced availability, null PNGs and advanced tier none; require no creation events.
`test_invalid_format_wire_matches_structured_reply` in smoke tests: real Client, all selected tiers plus unknown,
`raise_on_error=False`; assert `response.structured_content == expected`, parsed text blocks equal `[expected]`,
and `response.is_error is False`. Share a small fixture only within the owning test module; restore lookup roots on failure.
Use seeded generated invalid strings (exclude exactly base64/path) at the direct boundary as a no-execution/reply property;
no dependency or broad validation API. Document tests/helpers and keep scratch fixture creation outside watched calls.

- [ ] **Step 3: Observe RED before implementing.**

Run: `"$PY" -m pytest src/dartwork_mpl/mcp/templates/tests/test_format_preflight.py tests/test_mcp_render_smoke.py -k 'invalid_format or format_wire or unknown_selection' -q --no-cov -p no:cacheprovider`.
Expected: selected invalid cases FAIL exact-reply/no-effect assertions on base; unknown cases retain old behavior.
Ensure named tests match the selector and collect nonzero cases. Preserve exit code/output; import errors/skips are not RED.

- [ ] **Step 4: Add the narrow preflight in render.py.**

Keep unknown branches and advanced/basic selection unchanged. After selection and before `_render`, reject every string
outside `('base64', 'path')` with exact approved stderr and existing render_error fields, selected advanced tier included.
Use the current outcome/reply machinery without new status/type family or public type narrowing.
Keep successful fallback conversion limited to successful render only. Document changed native/private functions;
leave `mcp/tools.py` registered wrappers, their signatures and docstrings byte-for-byte unchanged.

- [ ] **Step 5: Verify GREEN and compatibility replays.**

Run: `"$PY" -m pytest src/dartwork_mpl/mcp/templates/tests tests/test_mcp_render_smoke.py tests/test_mcp_asset_boundary.py -q --no-cov -p no:cacheprovider`.
This includes existing `TestRenderTemplate::test_renders_bar_to_base64_png`, `::test_path_format_writes_a_file`,
`TestRenderTemplateAdvanced::test_renders_or_falls_back`, `::test_unknown_template`,
`test_path_output_is_unique_regular_private_and_preserves_owned_symlink`,
`test_template_publication_failure_has_safe_existing_error` and outcome variant fixtures.
Run: `"$PY" -m ruff check src/dartwork_mpl/mcp/templates tests/test_mcp_render_smoke.py` and corresponding `ruff format --check`.
Expected: PASS; new real Client cases must execute, not skip for missing FastMCP.
Replay Step 1 on changed source; compare full text/structured keys/values and PNG digests exactly.
For fresh path names compare uniqueness, private regular-file permissions, PNG bytes and null base64, not filename equality.
Require actual fallback/timeout/publication-error equivalence; outcome-only fixtures do not prove actual timeout behavior.
Save normal before/after rendered PNGs and refusal evidence for parent PoC; no visual approval claimed here.

- [ ] **Step 6: Commit and hand off for independent patch review.**

Stage only owned source/tests/necessary guide files; local commit `fix: preflight template return formats before execution`.
Return SHA, RED/GREEN evidence, full compatibility results and limits. Parent independently reviews patch, then combines B/C.
Existing pytest CI collects these paths; no new CI/version matrix or supported-version wire guarantee is introduced.
