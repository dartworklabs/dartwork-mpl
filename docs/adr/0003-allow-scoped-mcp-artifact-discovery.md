---
orphan: true
---

# ADR 0003: Allow scoped MCP artifact discovery

- 상태: Accepted — approved 2026-10-18; implementation pending
- 날짜: 2026-10-18
- 부분 대체: ADR 0001 A1의 `mcp_discovery` live 전체 exact 일치 범위만

## Context

The next roadmap milestone delivers an agent-generated plot's image, source and
validation report as a persistent MCP bundle. It needs dedicated tool/resource
registrations. ADR 0001 A1 makes `tests/test_color_v6_comparison.py::EXACT_FIELDS`
authoritative; that tuple includes `mcp_discovery`. The current live source scan
must equal frozen discovery exactly, including names/order. This is a binding
contract, not an incidental stale count assertion.

`AGENTS.md` says: “An ADR may not release a preceding ADR's lock.” Superseding
a frozen contract needs its own human approval. ADR 0002 remains Rejected;
ADR 0001 remains Accepted. Neither a request for follow-up work nor publication
of this proposal alone approves an exception. The separate approval below now
authorizes only the scoped change; current runtime behavior is still unchanged.

## Accepted decision — not yet implemented

Permit only the following additive discovery extension, while retaining every
existing discovery identity and its relative order:

1. Tools, appended in order: `render_plot`, `get_plot_artifact`.
2. Resource templates, appended in order under
   `dartwork-mpl://artifacts/{artifact_id}/`: `plot.png`, `plot.pdf`, `source.py`,
   `report.json`, `manifest.json`.
3. No new static resources or prompts; no removals, renames or other additions.

The resulting inventory is 18 tools, 10 static resources, 9 templates and 2
prompts. API details and MIME types are in the approved
[artifact design](../superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md).

Implement the frozen historical MCP core comparison against an explicit
legacy-core projection for the color compatibility report. Separately gate
actual FastMCP runtime discovery against that unchanged core plus exactly the
seven additions above, including category/order. Extend live source scanners and
`dartwork_mpl_info` so callers see the full inventory. A projection must never
hide registrations from runtime discovery or substitute for the full-live gate.

This is a compatibility-policy change, not a claim that today's lock already
permits additions. The exception covers only these identities; future additions
require their own decision. Baseline payloads, pinned digests, all shipped color
values/algorithms and every other exact surface remain unchanged. Do not modify
the historical baseline to make an extension pass.

## Trade-offs and alternatives

The split keeps historical color migration evidence reproducible while allowing
a small non-color delivery capability. It costs two explicit discovery checks
and documentation of their distinct scopes; the runtime check must prevent an
accidental unlisted addition or a removed core entry from escaping detection.

Retaining full-live exact equality would block this capability's registrations.
Reusing template render modes still needs resource templates and does not cover
general generated code. Regenerating the baseline would rewrite historical
evidence and weaken the color freeze. Hiding the new module from scanners would
make advertised discovery dishonest. None is proposed.

## Approval, consequences and application evidence

On 2026-10-18 the user explicitly selected **“이번 예외 승인 후 구현 진행 (권장)”**
in response to the separate approval request for exactly the two named tools and
five named resource templates, and the historical-core/full-live check split.
The user also authorized implementation of the complete artifact delivery design.
This is the human approval of this record's precise exception, separate from
ADR 0001 and the delivery design; it grants no wider discovery or color unlock.

This accepted decision partially supersedes only ADR 0001 A1's MCP discovery
comparison scope. ADR 0001's original text remains unedited; ADR 0002 remains
Rejected. Implementation is pending: the current live inventory is still
16 tools, 10 static resources, 4 templates and 2 prompts, with the old check.

Apply the projection at historical comparison/snapshot callers, keep full-live
scanners truthful, and add the independent runtime extension gate together with
the feature. Completion evidence must show passing frozen-color/exact-core and
real-server extension checks on supported FastMCP versions, unchanged baseline
bytes/digests and the 18/10/9/2 live inventory. Approval is not completion evidence.
