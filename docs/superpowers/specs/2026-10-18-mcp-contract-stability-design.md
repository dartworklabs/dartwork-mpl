# MCP contract stability

Date: 2026-10-18. Scope: the first delivery of the AI workflow diagnosis.
Authorization: the user accepted the diagnosed first scope and requested
“좋아 그러면 계획 세워서 진행해봐”. This document records that scope;
implementation details below are engineering choices, not additional user claims.

## Intent

Make the existing discover → template → execute → validate workflow dependable.
An ordinary print must not break execution results, a check that could not run
must not look clean, and a bundled-asset request must not read outside its root.
These are deterministic contract repairs, not a claim of measured LLM performance.

## Planning baseline and authority paths

No Handbook exists; none is initialized for this change. The following behavior
snapshot is from planning baseline `e544273c`, before the repairs. Paths remain
authorities; obsolete baseline behavior is not the delivered current behavior.

| role | path | Contract or observed implementation at planning baseline |
| --- | --- | --- |
| purpose | `AGENTS.md` | Native Matplotlib, preset-relative sizing, ≤200-line designs, frozen shipped colors. |
| execution | `src/dartwork_mpl/mcp/tools.py` | `validate_generated_plot` executes trusted local snippets in a fresh Agg subprocess and parses its entire stdout as JSON. |
| assets | `src/dartwork_mpl/mcp/resources.py` | Template/style resources interpolate IDs into paths; advanced resources fall back to basic. |
| assets | `src/dartwork_mpl/mcp/tools.py` | Render/compose tools already reject invalid template stems and resolved-root escapes. |
| validation | `src/dartwork_mpl/validate/_orchestrator.py` | `validate_figure(...) -> list[VisualWarning]`; caught check failures disappear from the returned list. |
| verification | `pyproject.toml`, `.github/workflows/ci.yml` | Python ≥3.10; pytest under `tests/`; Ruff, mypy, full tests and visual checks in CI. |

The diagnosis evidence is preserved in `/tmp/dartwork-mpl-ai-audit-mcp.txt`
and `/tmp/dartwork-mpl-ai-audit-workflow.txt`; these are session evidence,
not permanent runtime dependencies or substitutes for executable tests.

## 지켜야 할 현재 불변식

- Python >=3.10; no new dependencies.
- Keep Matplotlib Figure/Axes native and `validate_figure` returning a list.
- Keep existing tool/resource names, successful template contents, and advanced-to-basic fallback.
- Keep trusted local execution semantics, inherited cwd, and snippet save side effects.
- Preserve hint-conditional `semantic_warnings` and existing execution failure statuses.
- Shipped color values and their pinned digests remain frozen; no UI/style change.

## 설계 이유와 제약

The responsibility paths above remain the authorities. Two small repairs in the
existing MCP capability and one validation result repair avoid a broad new API.
The subprocess isolates Matplotlib state; it is not an OS security sandbox.
The package assets are public bundled data; a request ID grants no filesystem scope.
No verified user identity is added: trusted local MCP deployment remains the
existing execution boundary. Resource confinement does not harden arbitrary code.

## Adopted target: execution output

Keep `validate_generated_plot(code, figure_var="fig", timeout_seconds=20.0,
chart_type_hint=None) -> dict[str, Any]`. Capture subprocess stdout from snippet
execution and validation into additive `stdout: str`; write the internal JSON
result to a private temporary result file instead of stdout. Preserve subprocess
stderr in `stderr`. JSON-shaped logs,
multiline print output, and `dm.save_formats` output are data, never result framing.
Apply the same response normalization to every status, including early failures.
Do not change cwd, redirect user save destinations, or add artifact persistence.
The temporary channel is internal and cleaned up, not a delivered artifact.
Hostile mutation of the runner remains outside this trusted-snippet repair;
document that limit without claiming sandboxing.

## Adopted target: incomplete validation

Keep the native function signature and return type. For each registered check
whose currently tolerated `BBOX_ERRORS` exception prevents completion, append
`VisualWarning(Severity.WARNING, "CHECK_FAILED", ..., {"check_id": original_id})`.
Keep successful warnings alongside failures in deterministic registry order.
Quiet mode suppresses printing, never failure information in the returned list.
Nonquiet mode prints the failure warning and cannot print a clean verdict.
Unexpected exceptions may still propagate natively; MCP must expose an error,
never turn them into `ok` or a clean empty report. Do not broaden exception
suppression to process-control exceptions.

The MCP envelope gains `validation_complete: bool` and `failed_checks: list[str]`
on every return. A completed run has `true` and `[]`; caught failed checks produce
`status="validation_incomplete"`, `false`, and the original IDs in run order.
Other early/error statuses have `false` and `[]` unless a check failure is known.
`status="ok"` means validation completed, not that the figure has no warnings.
An incomplete report retains successful visual and requested semantic warnings.
No new public validation-report class or broad report API is required.

## Adopted target: one MCP asset boundary

`src/dartwork_mpl/mcp/_assets.py` owns ID parsing and path confinement.
Export `resolve_template_path(plot_type: str, *, advanced: bool = False)
-> Path | None` and `resolve_style_path(preset: str) -> Path | None` within MCP.
Both resource callbacks and template render/compose tools use these decisions.
Keep the existing private tools resolver as a delegating compatibility shim if
needed by current tests; it must not keep a second acceptance policy.

Template IDs accept ASCII `[a-z0-9_]+` after existing lowercase normalization;
style IDs accept ASCII `[A-Za-z0-9_-]+` without changing existing case semantics.
These are complete bare stems, not paths or percent-encoded paths. Reject empty,
absolute, dotted, separated, encoded and NUL-containing IDs. Resolve symlinks,
require a regular file, and require containment under the selected asset root
before returning a path. Return the resolved path that was checked. The package
asset installation is trusted and stable during reads; concurrent hostile asset
replacement is outside this boundary. Missing/invalid IDs retain the current
not-found/unknown-template response family without leaking outside file content.
Advanced-to-basic fallback runs through the same resolver for each candidate.

## Verification and completion

The mechanical oracle is observable values and real effects: real subprocess
results with print/save logs, real temporary assets and symlinks, returned native
warnings, and registered MCP resource reads including encoded URI traversal.
Test through FastMCP as well as callbacks where decoding changes input shape.
Seeded generated malformed IDs exercise the confinement invariant without deps.
Inject registered failing checks only as controlled fault stimuli; assert reports,
not private call counts. Use real save output inside test-owned temporary dirs.
Baseline workflow coverage includes discovery of an existing template, successful
validation with a saved PNG and logs, incomplete validation, and failure statuses.
Record red and green runs, then run relevant existing MCP/native/drift/color guards
and the repository's lint/type checks. No external model or service is needed.

## 충돌·미확인

No current contract grants arbitrary asset-path access. Existing execution trust,
cwd and save effects are deliberately retained for compatibility. Actual registered
FastMCP read tests confirmed URI-decoding behavior.
The design and plan were reviewed before dispatch; both task reviews approved
the implemented scope. Final whole-branch review remains pending.

## Delivered evidence and verification limits

Repairs landed in `0b6f83a7` and `3f0b7b2f`: one shared confined asset resolver,
private execution-result framing with captured logs, and returned failed-check
warnings plus explicit MCP completion fields. The adopted targets above describe
this delivered behavior; product usage is documented in `docs/integrations/mcp_server.md`.
Local Python 3.10 integration at `3f0b7b2f` passed 270 tests, Ruff check/format
(271 files) and mypy (99 files). Separate overlapping task suites and minimum
FastMCP 2.13.3 checks also passed; their counts are not additive.
The interrupted baseline run reached 305/4945 tests, not full-suite completion.
Full final tests, Python 3.11–3.13, Sphinx, pixel tests and remote CI were not run.
No PR, push or merge occurred. No dependency, UI or shipped-color change was made.
Deterministic contract coverage does not measure real agent task performance.

## Subsequent roadmap — not implemented here

1. Artifact delivery: durable image/code/report bundles and client-visible lifetime
   contracts, after choosing storage, cleanup and access semantics.
2. Data repair: extend shape errors into explicit, reviewable repairs while keeping
   user data changes observable; collect deterministic task fixtures first.
3. Agent evaluation: fresh-install task corpus, first-pass/repair/completion measures,
   pinned runs and cost tracking. Existing tests do not establish these metrics.

Input/output limits, OS sandboxing, a new render API and LLM evaluation tooling
belong to later designs; this delivery introduces none of them.
