---
orphan: true
---

# Anti-Pattern Coverage — Robustness Suite ↔ Lint Catalog

## Context

The 0.4 cycle landed two complementary systems for catching what AI
agents get wrong when generating dartwork-mpl plots:

- **Lint catalog** — `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`,
  the SSOT for the regex/substring rules the lint engine applies to
  Python source.
- **Robustness suite** — `tests/robustness/scenarios.py` (47
  scenarios), each a fully-built `Figure` that exercises a
  runtime/visual problem `validate_figure()` is supposed to catch.

T7 of the AI-readiness roadmap originally proposed converging these
into a single SSOT by adding ≥ 8 lint rules from the robustness suite
and tagging every scenario with the matching `rule_id`. After
implementing T6 we re-checked the assumption and concluded that the
two suites cover **different layers** of the failure space, not the
same layer at different fidelities:

| Layer | What it sees | Example |
|---|---|---|
| Lint catalog | Static source patterns | `figsize=(...)`, `tight_layout()`, `dm.SW` |
| Robustness suite | Runtime / rendering problems | Overflowing 25-char rotated tick labels, twinx parasite spine clipping, NaN-only y, log scale near zero |

A linter cannot see "this label overflows the canvas at this
particular figure size" without rendering the figure. The robustness
suite cannot see "the source uses `dm.cm2in` instead of `dm.cm`"
without the source. Forcing 1-to-1 mapping would dilute both suites.

T7 therefore re-scopes to: **make each scenario declare which SSOT it
belongs to, and verify that any scenario claiming a lint rule
references one that actually exists.**

## Decision

Each `RobustnessScenario` in `tests/robustness/scenarios.py` carries a
`category` field with one of two values:

- `"visual-only"` — the scenario tests a runtime/visual issue that
  has no static-source counterpart. Default for almost every
  scenario.
- `"rule:<rule-id>"` — the scenario tests behaviour adjacent to a
  static pattern in `02-anti-patterns.yaml` and the lint engine
  should be the first line of defence; the scenario is the fallback
  when an agent slips past the linter.

A meta-test (`tests/robustness/test_catalog_alignment.py`) runs in CI
and:

1. Asserts every scenario has a valid category string.
2. Asserts every `rule:<rule-id>` references an existing rule in the
   bundled catalog.
3. Prints a coverage summary so CI logs surface the visual / lint
   split.

## Current matrix (2026-05-02)

| Layer | Count | Notes |
|---|---|---|
| `visual-only` | 46 | The default. Every label-overflow, twinx, NaN, log, datetime, gridspec, inset, colorbar, pie, dark-mode, korean-font, axis-fraction, constrained-layout, tiny-figure, and squeeze scenario. |
| `rule:oversize-width` | 1 | `huge_figure_30cm`. Linter should flag the source first; the scenario verifies that 30 cm renders without breaking layout when the user does it anyway. |

The 1-to-1 mapping count will grow only when a scenario can be **both**
flagged by a regex and reproduced in a rendering test — a narrow
combination. We do **not** add lint rules merely to inflate the count;
each new rule has to fail the spec criteria
([`02-anti-patterns.yaml`](../../../src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml)
header) on its own merit.

## Future maintenance

- When adding a robustness scenario, set `category="visual-only"`
  unless the scenario also exercises a `02-anti-patterns.yaml` rule.
- When adding a lint rule that has a runtime echo, retrofit the
  matching scenario's `category` field. The alignment meta-test will
  flag any orphaned `rule:` reference automatically.
- When deleting a lint rule, the meta-test fails for any scenario
  still pointing at the deleted id; update or remove the
  `category="rule:<id>"` field as part of the same PR.

## References

- 0.5+ AI-readiness roadmap:
  [2026-05-01-ai-readiness-0.5-roadmap.md](2026-05-01-ai-readiness-0.5-roadmap.md)
- Lint catalog SSOT:
  [02-anti-patterns.yaml](../../../src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml)
- Robustness suite:
  [`tests/robustness/scenarios.py`](../../../tests/robustness/scenarios.py)
