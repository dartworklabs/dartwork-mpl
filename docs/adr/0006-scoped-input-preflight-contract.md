---
orphan: true
---

# ADR 0006: Scoped input preflight contract

| Item | Value |
| --- | --- |
| **상태** | Accepted (2026-10-29) |
| **Date** | 2026-10-29 |
| **Decider** | Project owner: “후속 고”, approving both recommended B/C exceptions and local implementation |
| **부분 대체** | ADR 0005 §1/§4 only: B nonfinite effective-margin ValueError; C invalid template return_format render_error reply |
| **Authority receipt** | `~/scratch/dartwork-local-input-preflight-2026-10-29/approval.json` |

## Context

Current source at local `33f51edda7762324b9fda0f262739a0b60dbc68f` admits
nonfinite effective margins into layout effects and treats non-`path` template
formats as base64 after executing the template. This can silently break layout
or perform unnecessary code execution and temporary-file/publication effects.
[ADR 0005 §1/§4](0005-capability-slices-and-test-colocation.md) freezes public
interfaces and edge replies. The owner separately approved precisely two
exceptions to that freeze. This record documents that approval; it does not
release a preceding lock on its own authority.

The owner approved the B/C decision and local implementation on 2026-10-29;
the integration owner reviewed this wording and authorized its acceptance.
Local B/C implementation and independent task reviews are recorded in the
[B plan](../superpowers/plans/2026-10-29-finite-margins.md) and
[C plan](../superpowers/plans/2026-10-29-template-format-preflight.md).
Decision approval is separate from runtime verification: combined verification,
final independent review and human PoC approval remain pending.

## Decision

1. **B:** On applicable figures, after complete existing margin parsing and
   resolution, reject any nonfinite effective side with exactly
   `ValueError("margin must resolve to finite figure fractions")` before any
   layout draw, font adoption, GridSpec update or Axes position change.
   Preserve no-op/GridSpec/parse precedence and finite behavior, including
   zero, negative, clamp and fully finite overrides of a nonfinite base.
2. **C:** After existing basic/advanced/fallback template selection, accept
   exactly `base64` and `path`. Any other string returns the existing
   `render_error` envelope with both PNG fields null and exactly
   `f"return_format must be 'base64' or 'path'; got {return_format!r}"` as stderr,
   before execution, render temporary-directory creation or publication.
   Advanced replies retain the selected tier; unknown selection still wins.

[Approved specification](../superpowers/specs/2026-10-29-input-preflight-design.md)
contains the complete precedence and verification requirements.

## Trade-off and alternatives

Earlier refusal prevents broken layouts and unnecessary effects, at the cost
of deliberately changing two invalid-input outcomes. Keeping silent admission
was rejected by the owner. Eagerly rejecting the base margin would break full
overrides and error precedence. Normalizing formats or introducing a new error
status/API would expand the approved scope. A shared validation framework adds
no value to these two independent owning boundaries.

## Consequences and limits

No signatures/static types, registered MCP names/order/schemas/docstrings,
19/10/9/2 discovery, artifact v1, shipped colors/presets, dependency or CI gate
changes. ADR 0001–0005 retain every unrelated lock; their files are untouched.
A/D/G remain deferred; E/F remain current behavior. No generalized admission,
recommendation ToolError or Text atomicity policy is introduced.

The [B plan](../superpowers/plans/2026-10-29-finite-margins.md) and
[C plan](../superpowers/plans/2026-10-29-template-format-preflight.md) own local
implementation. Independent patch review, combined local verification and
before/after rendered PoC precede any future public merge. Remote freshness
and CI remain unverified during the local-only suspension.
