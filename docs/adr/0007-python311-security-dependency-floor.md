# ADR 0007: Python 3.11 minimum and security dependency floors

Status: Accepted — owner approved the support change on 2026-11-05.
The decision is adopted; implementation requires merge and final validation.

## Context

Version 0.6.0 previously advertised Python >=3.10. The captured advisory set
contains 171 rows across 25 packages. Pillow 13, needed for the recorded core
security fixes, requires Python >=3.11. No maintained 3.10-compatible Pillow
backport covering the set was found in the bounded primary-source review.
Patched dnspython, filelock and Tornado also require 3.11.

The user explicitly selected “0.6.0부터 Python 3.11+로 올리고 보안 패치 적용”.
This record implements that approved support decision; it releases none of
ADR 0001–0006's freezes or locks.

## Decision

- Require Python >=3.11 from 0.6.0 and test 3.11, 3.12 and 3.13.
- Declare Pillow >=13 as a core security floor even though Matplotlib imports
  it transitively. A repository lock alone cannot protect fresh wheel users.
- Put affected MCP/UI transitive security floors in their respective extras.
  This includes urllib3 via jsonschema-path → requests in MCP; that route
  already existed before the upgrade. Keep Jupyter and other development
  dependencies in the dev group.
- Retain FastMCP >=2.14.7,<4, excluding vulnerable 3.0–3.4.9 releases using
  PEP 440 exclusions. FastMCP 2.13.3 itself is outside this advisory's
  affected range, but pins
  MCP SDK <1.23; all of that SDK range is vulnerable. The supported 2.x
  minimum therefore becomes 2.14.7, which permits patched SDK >=1.30,<2.
  Retain exact 2.13.3 only as legacy source/API compatibility coverage with
  an explicitly vulnerable disposable SDK, never a secure install claim.
  Lock FastMCP and its coupled slim package to 3.4.10.
- Apply the 25 advisory candidate floors and only resolver-forced collateral
  upgrades. Keep Matplotlib 3.10.9, HTTPX 0.28.1 and unrelated locks unchanged
  unless an observed resolver constraint requires otherwise.
- Use PyJWT >=2.15.1: the exact PyPI wheel passed six claim-options-reuse
  regressions that locked 2.13.0 failed. GHSA-gvp8-978c-rx2q still has no
  upstream patched-version field; retain that disagreement.

## Consequences and verification

Python 3.10 users need Python 3.11+ for 0.6.0. The 3.10 CI cell is removed by
this owner decision; no tests or other supported runtimes are removed.
The corresponding required branch-protection context `test (3.10)` must also
be removed by the parent, preserving every other required context and policy;
a stale context must not become a fake success alias. This operation is a
projection of the approved support change, not a general policy relaxation.
Notebook 7.6.3 forces JupyterLab >=4.6.4,<4.7 and jupyter-builder.
Virtualenv 21.14.9 admits filelock 4.2.1 and forces the recorded distlib,
packaging, platformdirs and python-discovery upgrades.

Executable checks cover built-wheel metadata (Python and dependency bounds),
supported 2.14.7 / patched 3.x acceptance, vulnerable 3.x rejection, a fresh installation,
recorded advisory ranges against the new lock, and existing affected runtime
contracts. Existing colour/pixel and MCP contract gates remain authoritative.
The implementation plan is
[2026-11-05-python311-security-upgrade](../superpowers/plans/2026-11-05-python311-security-upgrade.md).

This is a bounded repair against a captured advisory set, not proof of general
security. In particular 36 runtime High paths were not individually assessed.
Review completion does not itself establish evaluation, publication or release.
