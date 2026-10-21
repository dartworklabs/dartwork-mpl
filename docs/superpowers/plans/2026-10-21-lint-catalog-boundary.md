# LINT catalog boundary implementation plan

Adopted against the sibling spec and existing user scope approval; not a new human
approval record. Named Superpowers skills were unavailable and were not invoked.
Parent owns integration/base freshness and final rendered PoC presentation.

## Task 1 — preserve authority and reproduce

- [x] Read current authority, original diagnosis/fixtures and independent review.
- [x] Confirm parent-selected structural normalization and exact file ownership.
- [x] Capture original owned files and actual Sphinx API baseline before edits.
- [x] Prepare observable boundary tests in a private candidate, run assertion-red
  against original production code, and preserve raw output.

## Task 2 — repair the existing loader

- [x] Add severity, required-field/container and regex load-time rejection.
- [x] Preserve supported kinds/checks, original strings, MULTILINE, defaults,
  optional metadata, direct Rule construction, empty catalogs and native I/O/YAML errors.
- [x] Add finite Random(500) malformed inputs and valid controls in test_lint.py.
- [x] Document intentional invalid-input exception improvements in public Raises.
- [x] Run affected lint/migration tests and verify valid controls.
- [x] Compare original catalog bytes and all 27 ordered id/severity/kind tuples.

## Task 3 — repair public documentation

- [x] Use dm.lint_code/format_report; remove false CLI and obsolete fixed rule count.
- [x] Correct deprecated-width-token ID in the already-owned API page.
- [x] Build candidate real Sphinx/autodoc page with the same theme as baseline.
- [x] Capture same-scale before/after desktop/mobile artifacts for parent review.
- [ ] Parent shows rendered comparison to user before any merge.

## Task 4 — verification and handoff

- [x] Run existing tests/test_mcp.py -k lint during the exclusive source window.
- [x] Run changed-Python Ruff lint and formatting checks from source cwd.
- [x] Execute public example and dependency-blocked core probe (no clean-wheel claim).
- [x] Review exact owned diff, preserve red/green/hash receipts and freeze source.
- [ ] Parent runs final package mypy and reconciles any target movement before integration.

Existing CI owns pytest/mypy gates; required precommit owns Ruff/format.
No new dependencies, gates, source execution, global settings or persistent services.
Only lint.py, test_lint.py, docs/api/lint.rst and these bounded spec/plan records
belong to this worker. tools.py's column wording belongs to the MCP worker;
release-note integration belongs to the parent. No tests/test_mcp.py change.
