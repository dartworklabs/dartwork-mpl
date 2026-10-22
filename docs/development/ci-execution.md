---
orphan: true
---

# CI execution evidence

Existing test jobs own execution. Timing output must not create another suite
invocation, change the Python matrix, or weaken failures. The coverage 80
policy remains in `pyproject.toml`.

| Gate | Workflow and local command | Durable output |
| --- | --- | --- |
| Full suite, Python 3.10–3.13 | `.github/workflows/ci.yml`: `uv run pytest -v -n auto -m "not color_pipeline" --no-cov --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"`; 3.12 runs every test (no `-m`) with `--cov --cov-report=term-missing` instead of `--no-cov` | `pytest-python-<version>` artifact |
| Release full suite, Python 3.12 | `.github/workflows/release.yml`: `uv run pytest tests/ -q -rs --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"` | `release-pytest-python-3.12` artifact |
| All-extras module execution | Both workflows, after successful full pytest (CI 3.12): `uv run --no-sync python scripts/check_integration_junit.py "$RUNNER_TEMP/pytest-full.xml"` | Guard step log and same-run JUnit |
| FastMCP 2.13.3 / locked 3.4.2 artifact contracts, Python 3.12 | `test-mcp-artifacts` in `.github/workflows/ci.yml`: `uv run --no-sync --with "fastmcp==<version>" pytest tests/mcp/artifacts -q --no-cov --junitxml="$RUNNER_TEMP/pytest-artifacts.xml"`, then `uv run --no-sync python scripts/check_integration_junit.py "$RUNNER_TEMP/pytest-artifacts.xml" --scope artifacts` | `mcp-artifacts-<version>`: runtime JSON, same-run JUnit and raw pytest summary |
| Src typing | `.github/workflows/ci.yml`: `uv run mypy` (paths and strictness live in `[tool.mypy]`) | Step log |
| Isolated Ruff lint/format | `.github/workflows/pre-commit.yml`, `.pre-commit-config.yaml`: `SKIP=mypy pre-commit run --all-files` | Step log |

Each test artifact retains `pytest-full.xml` and `pytest-summary.txt` for seven
days. The latter contains pytest output, including its slowest 30 durations.
`-n auto` (pytest-xdist) runs one worker per vCPU; the workers' results are
merged into the one JUnit report with unchanged module/class names, so the
guard below reads it as before. `-n` lives on the CI command lines only, never
in `addopts`: local runs and `scripts/test_id_map.py` stay serial.
The `color_pipeline` marker (pyproject) selects the slow, interpreter-independent
colour build/byte-identity checks; only the 3.12 job runs them.
Release also includes `python-runtime.txt` (actual version and executable).
Uploads run with `always()`; bash `set -euo pipefail` keeps pytest or version
assertion failures visible through `tee`. Setup failures may leave no report;
the upload warns and the original failure still fails the job.
Step duration must come from the same GitHub run; local pytest timings do not
establish hosted speedup. JUnit supplies per-case durations without reruns.

Release test and build jobs set `UV_PYTHON=3.12`, overriding `.python-version`.
Each prints and asserts its actual interpreter. Build additionally passes
`--python "$UV_PYTHON"` to `uv build`. Existing tag, wheel/tree, sdist scope,
OIDC publish, and tag-only release conditions remain in force.

## Explicit all-extras inventory

`scripts/check_integration_junit.py:REQUIRED_MODULES` is the executable list.
`tests/test_check_integration_junit.py` independently pins that contract using
real CLI/temp-XML checks. Inventory review on 2026-10-20 used optional-extra
imports and `pytest.importorskip`, plus retained actual full-suite JUnit
collection, without another full-suite run.

| Protected group | Modules (prefix `tests.` unless otherwise shown) |
| --- | --- |
| Original integrations | `test_mcp`, `test_integration`, `test_cli`, `test_drift` |
| Agent loop | `mcp.agent_loop.test_oracle`, `mcp.agent_loop.test_capture` |
| Optional MCP consumers | `test_docs_mcp_tools`, `test_docstring_catalogs`, `test_mcp_asset_boundary`, `test_mcp_data_repair_contract`, `test_mcp_heavy_tools`, `test_mcp_render_smoke`, `test_mcp_tool_hardening`, `test_mcp_validation_contract` |
| Durable MCP artifacts | With prefix `tests.mcp.artifacts.`: `test_artifact_boundaries`, `test_artifact_discovery`, `test_artifact_entry_policies`, `test_artifact_execution`, `test_artifact_policy`, `test_artifact_protocol`, `test_artifact_store` |
| Retained input contracts | With prefix `tests.mcp.artifacts.`: `test_input_access`, `test_input_commit_observer`, `test_input_delivery`, `test_input_io`, `test_input_lifecycle`, `test_input_policy`, `test_input_recovery`, `test_input_stdio`, `test_input_store` |
| Plot-data validation and repair | With prefix `src.dartwork_mpl.mcp.plot_data.tests.`: `test_limits`, `test_properties`, `test_reports`, `test_validators` |
| MCP slice-owned tests | No prefix: `src.dartwork_mpl.mcp._platform.tests.test_process`, `src.dartwork_mpl.mcp.docs_fetch.tests.test_raw_github` |
| Optional UI consumers | `test_ui_boundary`, `test_ui_files`, `test_ui_http_security`, `test_ui_hardening`, `test_ui_init`, `test_ui_viewer_state`, `test_ui_render`, `test_ui_widget`, `test_ui_wire_golden` |

All 45 modules must contribute a passed executed case. Missing modules,
zero-test suites, and modules whose cases all skip fail. Any failure/error in
a protected module also fails, even alongside a passed case. Class-based
pytest names are accepted; similarly named sibling modules cannot count.
Pytest remains authoritative for every suite failure and collection error.
The checker proves module execution, not that every optional case executed.
In mixed modules, pytest skip reporting still identifies individual skips
(for example tomllib on Python 3.10).

The default guard scope protects all-extras full-suite jobs and remains the
primary repository execution proof. The closed `--scope artifacts` inventory
protects all 16 artifact modules in the focused two-major job, accepting no
skipped cases even alongside passes. It cannot select arbitrary module prefixes.
The focused job uses a frozen all-extras/dev sync followed by version overlays
without lock changes. It prints/asserts Python and FastMCP versions, executes
only artifact contracts and consumes that same run's JUnit; it never duplicates
the whole-repository major matrix. Missing optional extras cannot become a
passing focused gate. These are configured CI checks; local results alone do
not establish a hosted run or required branch-protection status.

The focused driver unsets `DARTWORK_MPL_INPUT_POLICY` and owns a disposable
artifact root with cleanup on exit. Tests supply their own private fixture
policies; no operator policy is loaded/deployed and HOME is not globally changed.
Normal stdio checks allow only the exact observed runpy server eager-import
RuntimeWarning and Authlib deprecation class/message/continuation. Additional
warnings, tracebacks, ClosedResourceError and ResourceWarning fail visibly.
Expected negative-refusal/disconnect logs remain separate qualified diagnostics;
this test allowlist neither suppresses them nor changes production imports.

Base/no-extras smoke intentionally checks absent optional dependencies and remains separate.
Add new optional contract modules to the explicit list and its CLI regression
inventory when that contract needs protection.
