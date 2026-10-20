# CI execution repairs — #470

Approval basis: the user's 2026-10-20 “진행해” continues the declared
#499 / #470 priorities. Issue #470's current task list and acceptance criteria
bound this implementation. This is repair of existing execution contracts.
It does not approve lane removal, new dependencies, or a new gate framework.

## Current authority and constraints

No Handbook exists. Current authority is `AGENTS.md`, issue #470,
`.github/workflows/{ci,release,pre-commit}.yml`,
`scripts/check_integration_junit.py`, `tests/test_check_integration_junit.py`,
`tests/test_helpers_labels.py`, and `pyproject.toml`. The July frozen-mypy design explains why local hooks use `--frozen`;
#496 and current workflows now give src mypy to CI and isolated Ruff to
pre-commit. Preserve that division and all existing release/package gates.
HEAD is ae8ce249; fetched origin/main is 1e6add8b. The latter contains only
skills setup beyond the product baseline already incorporated by phase0.
Preserve this host-managed checkout and phase0 oracle/capture JUnit guards.

Preserve Python 3.10–3.13, coverage 80, shipped colours, 18-surface comparisons,
real MCP subprocess/artifacts, base smoke, visual/docs gates, and wheel parity.
No model calls, GitHub writes, releases, or extra full-suite run are needed here.

## Implementation and evidence

- [x] `scripts/check_integration_junit.py`, `tests/test_check_integration_junit.py`:
   Extend the existing explicit all-extras protected-module list from optional
   dependency imports and retained real JUnit collection. Keep the original six.
   First show the real CLI rejects absent/zero/all-skipped/error modules, even
   alongside passing siblings. Extend seeded order/noise properties.
- [x] `tests/test_helpers_labels.py`:
   Remove arbitrary legend ValueError-to-skip handling. Use a real scientific
   preset, registered colours, native axes, and direct helper calls. Preserve
   legend existence, columns, max_cols, and outside-anchor assertions. Prove a
   targeted ValueError mutation fails; production appearance is unchanged.
- [x] `.github/workflows/ci.yml`:
   Capture JUnit and a duration/log summary during each existing matrix execution;
   use pipefail and always-upload with the existing pinned artifact action and
   seven-day retention. Do not add a test job or rerun tests for timing.
- [x] `.github/workflows/release.yml`:
   Pin release test and build `UV_PYTHON=3.12`, record actual interpreter/version,
   and preserve existing package/release checks. Apply the same all-extras guard
   to its existing full-suite report. Upload that report and durations always.
- [x] `.github/workflows/pre-commit.yml`:
   Review official action tag/commit data, pin pre-commit's three actions, and
   set `contents: read`. Keep Ruff and src mypy ownership unchanged.

- [x] `docs/development/ci-execution.md`: record commands, output locations,
   explicit inventory, and optional skip policy.
- [x] Commit preparation: focused regressions, package/runtime checks, static
   checks, and diff review are complete. Logical commit point: the eight owned
   implementation/docs files together, before parent integration.

## Validation and gates

- CI matrix and release pytest retain their failure status and existing coverage
  policy. `scripts/check_integration_junit.py <full.xml>` gates all-extras runs
  (CI 3.12 and release); it is intentionally absent from base/no-extras smoke.
- Run `UV_PYTHON=3.12 uv run --no-sync pytest
  tests/test_check_integration_junit.py tests/test_helpers_labels.py
  tests/mcp/data_repair/test_limits.py tests/mcp/data_repair/test_properties.py
  --no-cov -q`; retain real JUnit and command receipts.
- Directly run release runtime selection and the two tomllib parity cases on 3.12;
  exercise the build command and packaging gates without publication.
- Check actual YAML/action references, Ruff lint/format, and existing src mypy.
- Audit expanded inventory against retained real full JUnit plus fresh focused
  JUnit; use the prior same-run timing report only for costly-check candidates.

Evidence lives in `~/scratch/dartwork-mpl-followups-2026-10-20/ci470/`.
- [ ] Hosted-run timing/JUnit collection remains an integration step for the parent;
local timing cannot establish hosted speedup. No lane adjustment follows here.

Local receipts: focused 263 passed/0 skips; parity 2 passed/0 skips; real
Python 3.12.13 test/build receipts; wheel/tree and sdist scope shell gates pass;
Ruff lint/format and src mypy pass. Current tests against the preserved old
checker produce 184 expected failures; legend ValueError mutation produces
6 failures and no skips. The CI pipefail path preserves exit 1 and artifacts.
