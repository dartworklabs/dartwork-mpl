---
orphan: true
---

# CI execution evidence

Existing test jobs own execution. Timing output must not create another suite
invocation, change the Python matrix, or weaken failures. The coverage 80
policy remains in `pyproject.toml`.

| Gate | Workflow and local command | Durable output |
| --- | --- | --- |
| Full suite, Python 3.11–3.13 | `.github/workflows/ci.yml`: `uv run pytest -v -n auto --dist worksteal -m "not color_pipeline" --no-cov --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"`; 3.12 runs every test (no `-m`) with `--cov --cov-report=term-missing` instead of `--no-cov` | `pytest-python-<version>` artifact |
| Release full suite, Python 3.12 | `.github/workflows/release.yml`: `uv run pytest -q -n 4 --dist worksteal -rs --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"` | `release-pytest-python-3.12` artifact |
| All-extras module execution | Both workflows, after successful full pytest (every CI full-suite job, 3.11–3.13): `uv run --no-sync python scripts/check_integration_junit.py "$RUNNER_TEMP/pytest-full.xml"` | Guard step log and same-run JUnit |
| FastMCP legacy 2.13.3 / secure 2.14.7 / locked 3.4.10 artifact contracts, Python 3.12 | `test-mcp-artifacts` in `.github/workflows/ci.yml`: secure cells install the project plus selected FastMCP, then `uv run --no-sync pytest tests/mcp/artifacts -q --no-cov --junitxml="$RUNNER_TEMP/pytest-artifacts.xml"` (legacy 2.13.3 uses the recorded Pydantic 2.14.1 overlay), then `uv run --no-sync python scripts/check_integration_junit.py "$RUNNER_TEMP/pytest-artifacts.xml" --scope artifacts` | `mcp-artifacts-<version>`: runtime JSON, same-run JUnit and raw pytest summary |
| Floor cell, Python 3.11 (`test-matplotlib (minimum)`) | `.github/workflows/ci.yml`: pins `matplotlib==3.11.2 numpy==1.26.0` (installed versions compared as exact strings), runs the pixel, colour-hash, font-invariant, gamma, font, IO and formatting tests, then a JUnit check that IPython is absent and `test_show_without_notebook_extra_names_the_install_command` ran (not skipped) | `matplotlib-minimum*.xml` artifact |
| Src typing | `.github/workflows/ci.yml`: `uv run mypy` (paths and strictness live in `[tool.mypy]`) | Step log |
| Isolated Ruff lint/format | `.github/workflows/pre-commit.yml`, `.pre-commit-config.yaml`: `SKIP=mypy pre-commit run --all-files` | Step log |

Each test artifact retains `pytest-full.xml` and `pytest-summary.txt` for seven
days. The latter contains pytest output, including its slowest 30 durations.
`-n auto` (pytest-xdist) runs one worker per vCPU on hosted PR runners. On
pushes to main, which run on the shared self-hosted ml-main, the `test` and
`test-matplotlib` jobs set `PYTEST_XDIST_AUTO_NUM_WORKERS=4`, so `-n auto`
starts four workers beside the other jobs (before 2026-11-07 the Matplotlib
cells took every core, 64 workers). Each job log prints
`created: N/N workers`. The workers' results are
merged into the one JUnit report with unchanged module/class names, so the
guard below reads it as before. `-n` lives on the CI command lines only, never
in `addopts`: local runs and `scripts/test_id_map.py` stay serial.
`--dist worksteal` sits next to `-n` on the same command lines (it needs
pytest-xdist, so it is not in `addopts` either; `-p no:xdist` keeps working):
idle workers take queued tests from busy ones, so a module's consecutive
30-60 s colour subprocess tests stop running back to back on one worker. Measured
locally on 2026-11-06 with paired concurrent runs, 4 workers: wall 445 s to
364 s, CPU 2465 s to 2410 s; 32 workers: wall about 20-30% lower for 5-8%
more CPU (module fixtures set up on more workers). Hosted speed is read from
the same GitHub run, as below.
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
`tests/tools/test_check_integration_junit.py` independently pins that contract using
real CLI/temp-XML checks. Inventory review on 2026-10-20 used optional-extra
imports and `pytest.importorskip`, plus retained actual full-suite JUnit
collection, without another full-suite run.

| Protected group | Modules (prefix `tests.` unless otherwise shown) |
| --- | --- |
| Original integrations | `contracts.test_mcp`, `contracts.test_integration`, `contracts.test_cli`, `architecture.test_drift` |
| Agent loop | `mcp.agent_loop.test_oracle`, `mcp.agent_loop.test_capture` |
| Optional MCP consumers | `docs.test_docs_mcp_tools`, `docs.test_docstring_catalogs`, `contracts.test_mcp_asset_boundary`, `contracts.test_mcp_data_repair_contract`, `contracts.test_mcp_heavy_tools`, `contracts.test_mcp_render_smoke`, `contracts.test_mcp_tool_hardening`, `contracts.test_mcp_validation_contract`, `contracts.test_safe_fs_contracts`, `contracts.test_patch_targets` |
| Durable MCP artifacts | With prefix `tests.mcp.artifacts.`: `test_artifact_boundaries`, `test_artifact_discovery`, `test_artifact_entry_policies`, `test_artifact_execution`, `test_artifact_policy`, `test_artifact_protocol`, `test_artifact_store` |
| Retained input contracts | With prefix `tests.mcp.artifacts.`: `test_input_access`, `test_input_commit_observer`, `test_input_delivery`, `test_input_io`, `test_input_lifecycle`, `test_input_policy`, `test_input_recovery`, `test_input_stdio`, `test_input_store` |
| Plot-data validation and repair | With prefix `src.dartwork_mpl.mcp.plot_data.tests.`: `test_limits`, `test_properties`, `test_reports`, `test_validators` |
| MCP slice-owned tests | No prefix: `src.dartwork_mpl.mcp._platform.tests.test_process`, `src.dartwork_mpl.mcp.docs_fetch.tests.test_raw_github`, `src.dartwork_mpl.mcp.recommend.tests.test_chart_type_transport` |
| Optional UI consumers | With prefix `src.dartwork_mpl.ui.`: `tests.test_ui_boundary`, `saving.tests.test_ui_files`, `tests.test_ui_http_security`, `render.tests.test_ui_hardening`, `tests.test_ui_init`, `state.tests.test_ui_viewer_state`, `render.tests.test_ui_render`, `params.tests.test_ui_widget`, `tests.test_ui_wire_golden` |

All 49 modules must contribute a passed executed case. Missing modules,
zero-test suites, and modules whose cases all skip fail. Any failure/error in
a protected module also fails, even alongside a passed case. Class-based
pytest names are accepted; similarly named sibling modules cannot count.
Pytest remains authoritative for every suite failure and collection error.
The default scope also fails when any case in the report, protected or not,
was skipped because an import failed: pytest's `importorskip` reason
`could not import`, at module level (a "collection skipped" case) or inside
one test. An all-extras run must import every optional dependency, so this
covers case-level importorskips in mixed modules such as `tests.contracts.test_cli`.
Option-gated skips (`--mpl`) and version-gated skips are not import failures.
`tests/tools/test_check_integration_junit.py` also requires every test module
that importorskips FastMCP or FastAPI to be in the explicit list.
The 0.6.0 owner decision (ADR 0007) removes only the Python 3.10 support cell.

The default guard scope protects all-extras full-suite jobs and remains the
primary repository execution proof. The closed `--scope artifacts` inventory
protects all 16 artifact modules in the focused secure-two-major / legacy job, accepting no
skipped cases even alongside passes. It cannot select arbitrary module prefixes.
The focused job begins with a frozen all-extras/dev sync. Secure 2.14.7 and
3.4.10 cells install the actual project with the selected FastMCP version,
check installed dependency consistency and assert MCP SDK >=1.30. Only the
explicit legacy 2.13.3 cell uses an overlay; its SDK <1.23 is vulnerable and
that cell establishes source/API compatibility, never a secure install.
No cell rewrites the repository lock. It prints/asserts Python and FastMCP versions, executes
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
