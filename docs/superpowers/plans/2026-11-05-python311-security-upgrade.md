# Python 3.11 and security dependency repair

The user explicitly approved Python 3.11+ from 0.6.0 and applying security
patches on 2026-11-05. Continue the approved transition plan; no new discovery
or approval is required. Version stays 0.6.0. No Handbook is present.

## Current authority and invariants

The package metadata, resolved lock and real wheel are the support/dependency
authorities. AGENTS.md preserves shipped colours, fonts, styles, pixel
baselines and native Figure/Axes. MCP names, order, input/output schemas and
docstrings stay unchanged. ADR 0007 records the approved support trade-off;
it supersedes none of ADR 0001–0006's freezes or locks.

## Task 1 — apply and verify the scoped repair

Files: pyproject.toml, uv.lock, .python-version, .github/workflows/{ci,docs}.yml;
README.md, CHANGELOG.md, docs/installation/index.md, docs/migration.md,
docs/integrations/mcp_server.md, docs/development/ci-execution.md,
llms-full.txt, docs/adr/{0007-python311-security-dependency-floor,index}.md;
tests/architecture/test_dependency_security.py,
tests/contracts/test_version.py, tests/mcp/data_repair/fixtures/legacy_calls.json,
tests/mcp/artifacts/test_input_stdio.py.

- [x] Step 1: Record the owner's support decision and ADR before runtime edits.
  Expected: Python >=3.11 target; prior numbered ADRs and freezes untouched.
- [x] Step 2: Exercise old built-wheel requirements before changing them.
  Expected: vulnerable pins/unsupported Python boundaries fail the new checks.
- [x] Step 3: Apply 25 advisory floors and forced collateral changes through uv.
  Expected: published core/MCP/UI bounds protect fresh consumers; Jupyter stays
  dev-only; Matplotlib 3.10.9 and HTTPX 0.28.1 remain unchanged. Ruff retains
  its prior py310 authoring baseline; runtime/mypy/CI support starts at 3.11.
- [x] Step 4: Preserve secure FastMCP 2.x/3.x installation and old wire evidence.
  Expected: 2.14.7/3.4.10 resolve SDK >=1.30; incompatible 2.13.3 remains only
  explicit disposable legacy source/API coverage with recorded Pydantic.
  New captures use hash-verified original tools source; old captures stay exact.
- [x] Step 5: Verify actual fresh wheel installations and captured advisory ranges.
  Expected: all 572 payload members and metadata match; pip check, rendering,
  runtime calls and negative resolver controls pass on supported environments.
- [x] Step 6: Classify the exact newly observed upstream HTTPX deprecation.
  Expected: new positives fail before the narrow helper addition, all previous
  unknown/resource-fault rejection controls remain, mutated context still fails,
  and six actual stdio workflows pass on secure 2.x and legacy 2.13.3.
- [ ] Step 7: Run final full pytest/coverage, frozen pixel checks, mypy and
  changed-file pre-commit. Expected: no failed or silently skipped required
  work, no removed test IDs; retain JUnit, timings, load and content identities.
- [ ] Step 8: Build and bind actual final distribution/receipts, migrate only
  required status context test (3.10), then publish the scoped repair PR.
  Expected: every other branch-protection setting unchanged; normal PR watch.

Commit point: one logical support/security repair after combined local gates.
Parent owns final integration, subsequent changed-main validation, original
registered 320+separate descriptive 80 and the authorized release. No evaluation
freeze or case execution occurs in this task.

## Evidence limits

Use the immutable 171-row advisory snapshot and actual PyJWT 2.15.1 controls,
not a general security claim. GHSA-gvp8-978c-rx2q still lacks upstream patched
version metadata; 36 runtime High paths were not individually assessed.
Dependency membership is not exploitability. Keep failed logs and provenance.
CA production and existing acceptance environments stay unchanged.
