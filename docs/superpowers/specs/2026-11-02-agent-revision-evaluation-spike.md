# Agent revision evaluation: post-spike record

Date: 2026-11-02. Status: bounded exploratory evidence recorded; no product
behavior or policy change approved. Work stayed local while GitHub was suspended.

## Scope and provenance

The user authorized a bounded evaluation of native-installed and MCP prompt
revisions. This record closes the exploratory `spike → results → record` branch
of arch-design(spec). It records observations and proposals for later approval.

- Repository HEAD: `72526b2a4578c7a70741fff74e7c4b8b50301a24`.
- Branch: `integration/local-agent-followups-20261029`.
- Evidence root: `/Users/wonjun/scratch/dartwork-agent-revision-spike-2026-11-02`.
- Both routes used the same installed wheel, SHA-256
  `d7539f204a0d8ae12ae1a464e0faaaf4f88c025db6eb6c8a0516d923c3936f39`.
- Runtime: Python 3.12, Matplotlib 3.10.9, FastMCP 3.4.2.

Every figure used the `report` preset, a 16 × 12 cm canvas, and the same five-row
CSV. Data arrays, row order, panel assignment, colors, legend text and placement,
canvas dimensions, and preset were preservation requirements except where the
explicit request authorized a change. No aggregation or imputation was requested.

## Execution protocol

Managed agents received bounded instructions for four baseline plots, followed
by a separate revision turn for each route. This measures execution under those
instructions; it is not an uncontrolled model benchmark or success-rate estimate.
The stop condition was one initial and one revision attempt per case and route,
with at most one preserved infrastructure correction; there was no retry until
success. All 16 plotted sources and their images remain in the evidence root.

The native route executed installed Python. The MCP route used the actual
FastMCP Client with in-process transport, not stdio. It reopened baseline source
through resources, rendered revisions with parent artifact provenance, then
reopened each bundle and read its five members. Returned source bytes and
resource hashes were checked. Agent reports and visual reviews were retained.

An independent evaluator replayed exact source copies in fresh children,
checked installed import origin, and compared native artist properties and
container allocations. Its expectations and controls were recorded separately
from candidate generation. These trusted executions were not a security sandbox.

## Observed outcomes

All eight baselines were valid. Strict revision preservation passed 7/8:
native 4/4 and MCP 3/4.

| Revision request | Native | MCP |
| --- | --- | --- |
| Increase only x/y axis-label sizes by 1 pt | Pass | Fail: extra Axes geometry change |
| Give only the treatment line dash pattern `(6, 2, 1, 2)` | Pass | Pass |
| Change vertical container heights from 50/50 to 70/30 | Pass | Pass |
| Keep rows 50/50; change top widths to 40/60 and bottom to 70/30 | Pass | Pass |

For the MCP label revision, both labels correctly changed from 8 to 9 pt.
The edit preceded the existing `dm.simple_layout(fig)` call. That recomputed
the Axes box: its left and bottom moved right and up by about 0.4233 mm each,
with corresponding width/height reductions. The legend stayed upper right and
anchored relative to the Axes; its absolute anchor rectangle followed that box.
The strict single-panel preservation comparison therefore rejected extra changes.
This supports an agent sequencing/unrequested-relayout finding. It does not
establish an MCP/server defect or a deliberate semantic legend relocation.

Both dash revisions reached the renderer graphics context with offset 0 and
pattern `(6, 2, 1, 2)` at linewidth 1. Requested layout allocations matched in
both routes. Agent reports nevertheless claimed success and zero failed
validation checks for the MCP label revision: the existing checks did not detect
the before/after scope violation.

## Independent checks and visual advisories

The evaluator's 34 controls all matched expectations. This total includes
acceptance/rejection checks and meta-checks; its expected-boolean counts should
not be interpreted as a simple acceptance/rejection split.

The parent supplement checked actual SubFigure bounds and Axes-relative legend
anchors for all eight pairs; all passed. Its measured-bound mutation, anchor
mutation, and unmodified controls passed. All 16 retained source-copy hashes
matched. These supplementary checks preserve the original strict result of 7/8;
they explain which geometry changed rather than relaxing the gate retroactively.

Visual review recorded two advisories outside the original hard gates:

- The native dash revision leaves the existing legend sample solid because its
  data-line edit occurs after legend construction.
- Vertical compression produces legend/data overlap in the bottom panel;
  narrower rowwise panels also retain overlap. Labels remain visible without new
  canvas-edge clipping in the reported MCP review.

These observations are not retroactive hard failures or evidence of aesthetic
improvement. Automatic legend relocation or color changes were not authorized.

## Limits and proposed next work

Coverage is finite: selected native artists, SubFigure hierarchy, and direct
per-owner GridSpec cells. It does not establish preservation for all Matplotlib
artists, nested GridSpec-only layouts, custom renderer features, or other inputs.
The spike establishes neither a CI gate nor a general model success rate, stdio
transport result, or full-suite result. No public contract change follows from it.

The next proposal should prioritize a semantic before/after scope audit over a
new DSL: preserve existing geometry for local cosmetic edits; if clipping makes
relayout necessary, surface that decision to the user. Explicitly identify the
target artists, keep legend handles consistent with edited lines without moving
the legend, extend evaluation with actual container bounding boxes and relative
anchors, and report overlap advisories for compressed panels. These are proposals
requiring subsequent design decisions, not adopted product behavior.

Primary evidence beneath the root: `scope.json`, `evaluator/README.md`,
`evaluator/assessments.json`, `evaluator/measurements.json`,
`evaluator/validation.json`, `parent-review.json`,
`native/revision-execution.json`, and `mcp/revision-review.md`.
