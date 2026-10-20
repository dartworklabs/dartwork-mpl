---
orphan: true
---

# CI execution evidence

Existing test jobs own execution. Timing output must not create another suite
invocation, change the Python matrix, or weaken failures. The coverage 80
policy remains in `pyproject.toml`.

| Gate | Workflow and local command | Durable output |
| --- | --- | --- |
| Full suite, Python 3.10–3.13 | `.github/workflows/ci.yml`: `uv run pytest tests/ -v --no-cov --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"`; 3.12 uses `--cov --cov-report=term-missing` instead of `--no-cov` | `pytest-python-<version>` artifact |
| Release full suite, Python 3.12 | `.github/workflows/release.yml`: `uv run pytest tests/ -q -rs --durations=30 --junitxml="$RUNNER_TEMP/pytest-full.xml"` | `release-pytest-python-3.12` artifact |
| All-extras module execution | Both workflows, after successful full pytest (CI 3.12): `uv run --no-sync python scripts/check_integration_junit.py "$RUNNER_TEMP/pytest-full.xml"` | Guard step log and same-run JUnit |
| Src typing | `.github/workflows/ci.yml`: `uv run mypy src/dartwork_mpl/` | Step log |
| Isolated Ruff lint/format | `.github/workflows/pre-commit.yml`, `.pre-commit-config.yaml`: `SKIP=mypy pre-commit run --all-files` | Step log |

Each test artifact retains `pytest-full.xml` and `pytest-summary.txt` for seven
days. The latter contains pytest output, including its slowest 30 durations.
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
| Optional MCP consumers | `test_docs_mcp_tools`, `test_docstring_catalogs`, `test_mcp_asset_boundary`, `test_mcp_data_repair_contract`, `test_mcp_heavy_tools`, `test_mcp_render_smoke`, `test_mcp_tool_hardening`, `test_mcp_validation_contract`, `test_mcp_validators_complete` |
| Durable MCP artifacts | With prefix `tests.mcp.artifacts.`: `test_artifact_boundaries`, `test_artifact_discovery`, `test_artifact_entry_policies`, `test_artifact_execution`, `test_artifact_policy`, `test_artifact_protocol`, `test_artifact_store` |
| Data repair collection | With prefix `tests.mcp.data_repair.`: `test_limits`, `test_properties`, `test_reports` |
| Optional UI consumers | `test_ui_hardening`, `test_ui_init`, `test_ui_param`, `test_ui_security`, `test_ui_widget` |

All 30 modules must contribute a passed executed case. Missing modules,
zero-test suites, and modules whose cases all skip fail. Any failure/error in
a protected module also fails, even alongside a passed case. Class-based
pytest names are accepted; similarly named sibling modules cannot count.
Pytest remains authoritative for every suite failure and collection error.
The checker proves module execution, not that every optional case executed.
In mixed modules, pytest skip reporting still identifies individual skips
(for example tomllib on Python 3.10).

The guard applies only to all-extras full-suite jobs. Base/no-extras smoke
intentionally checks absent optional dependencies and remains separate.
Add new optional contract modules to the explicit list and its CLI regression
inventory when that contract needs protection.
