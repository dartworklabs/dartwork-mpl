# LINT catalog load boundary — #500 item 5

Status: adopted routine repair within the user's three-track restoration approval.
The user authorized that scope with “고”; this record does not claim separate human
approval of every implementation detail. Parent scope review selected the malformed
structure normalization below, and independent preimplementation review passed it.
Baseline: main d2b6d0b1ce8897d24398aa5a4de5d97f23ab2a05.

## Current authority

- `AGENTS.md`: native APIs, shipped assets and bounded executable acceptance.
- `src/dartwork_mpl/lint.py`: public Rule/Issue/load_rules/lint behavior.
- `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`: exact shipped rule values/order.
- `pyproject.toml` and existing CI: Python >=3.10, pytest, mypy, Ruff; no new gate.
- No Handbook exists. Named Superpowers brainstorming/writing-plans were unavailable;
  explicit diagnosis, parent scope review, independent review and this plan replace
  that workflow without claiming those skills executed.

## Problem and resulting behavior

The loader currently accepts invalid severities and defers regex validation until
scanning. Builtin detector IDs can bypass that validation entirely. Invalid catalog
shapes also leak incidental AttributeError, TypeError or KeyError exceptions.

Keep the repair in the existing loader. At load time reject:

- severity types/values outside critical, warning and info;
- unsupported detector kinds/AST checks;
- non-string regex patterns and invalid regex grammar, including builtin IDs;
- nonmapping root/entry/detector, nonlist rules, and missing or malformed required
  fields needed to construct a Rule, including string id/message/literal values.

These invalid-input cases raise contextual ValueError. Regex grammar errors retain
re.error as their cause. Filesystem and YAML syntax errors retain native exceptions.
Compile regexes with the scanner's re.MULTILINE semantics solely for validation;
keep each original detector string, with no cache or compiled value in Rule.

## Compatibility and non-goals

Preserve empty mapping/empty rules, omitted regex kind, all supported kinds/checks,
valid custom known-ID overrides, order, path/default rereads and prior-list snapshots.
Preserve direct Rule construction and optional/unknown metadata behavior. Preserve
all 27 ordered shipped id/severity/kind tuples and exact catalog bytes.
No duplicate-key/ID, version, nonempty-string, unknown-metadata or regex resource
policy is added. No API, CLI, schema, dependency, CI gate or static detector redesign.
Submitted Python source stays inert; safe YAML loading stays in place. This is a
local catalog boundary repair, with no new execution or authorization grant.

Correct the API page's nonexistent CLI, obsolete fixed count and width-token ID;
show dm.lint_code with format_report and the existing MCP path. The MCP owner
corrects the already-correct column output's description; no new MCP test is needed.

## Executable acceptance

Original receipts preserve 20 YAML cases, valid controls and the ordered 27-rule
snapshot. New public-boundary tests must show assertion-red before implementation,
then green. Finite stdlib Random(500) malformed-field cases exercise rejection
without a parser stress campaign or a copied-loader oracle.

Run lint/migration tests, existing MCP lint tests, changed-file Ruff/format and a
public API example with optional packages blocked. Parent runs final package mypy
once all source writers freeze. Recheck exact catalog bytes/order and review diff.
These use existing checks, not new merge gates; the reused complete venv is not a
clean-wheel installation or Python/OS matrix result.

Build the actual API page with real Sphinx autodoc before and after the edit.
Capture both at the same desktop/mobile scales. Parent must show the rendered
comparison to the user before merge; passing code checks do not waive that step.
