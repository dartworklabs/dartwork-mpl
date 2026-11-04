# Local revision guidance follow-up — post-spike record

Date: 2026-11-03. Status: bounded guidance implemented; human visual approval
and local integration review remain separate. User authorized proceeding after
the two measured issues. Base: `b5b0550464ae4ab0cd074d283c76cd7db6f816a0`.

## Scope and authority

This is the arch-design exploratory branch: scope → execute → factual record.
The scope was fixed before execution in the local evidence `scope.md`.
No Handbook exists; none was initialized. Native Matplotlib APIs, presets,
shipped colors, runtime code and dependencies remain unchanged. The changes
are agent instructions, not an automatic fixer or an agent benchmark.

Only two local revisions are covered: current x/y label sizes +1 pt after the
original layout, and a selected plain Line2D nominal dash change with its known
corresponding existing legend sample changed in place. The existing artist
handle and label establish the target; array position alone is insufficient.
Custom handlers/proxies require their original mapping to be resolved.

## Adopted instructions

Retained source runs its original layout with original kwargs before the local
label patch and report/export. In-memory edits use the existing artists/layout.
Do not reapply a preset, silently refit, rebuild a legend, or copy whole artist
properties/transforms. Keep nominal versus physical dash lengths distinct;
physical lengths require the existing local `scale_dashes=False` guidance.

Preserve active native layout engines and measure after actual draw/export;
setter-only edits do not guarantee position invariance. If a label does not fit
or bounds move, disclose the finding and ask about a needed layout change,
unless already requested. An authorized refit retains original margins/grid
kwargs unless explicitly changed. The top recipe, installed journey excerpt,
installed Python guide and MCP review loop now agree on this boundary.

## Execution evidence

Evidence root (outside datasets):
`/Users/wonjun/scratch/dartwork-local-revision-guidance-2026-11-03/implementation`.

The existing Nov2 evidence remains read-only. Original sources were hashed;
the old MCP pre-layout label edit and native stale-legend edit were replayed
into the new evidence root and rejected again. No expected control was read.
The unchanged prior preservation oracle was extended with actual legend-sample
dash/properties and draw/export geometry, not replaced by a prose-match test.

Two native executions and two real FastMCP Client in-process executions applied
the correction snippets. Before/after PNG/PDF, exact source, artist state,
complete MCP replies/resources, reports, logs and source diffs are retained.
Data/masks/order, colors, canvas, Axes and legend placement were compared.
Selected data-line and legend-sample nominal/rendered dashes were checked.
PNG dimensions/DPI and per-renderer export bounds were also compared.

Preservation checks pass for all four corrected pairs. Native labels with the
original 2 mm margin fit, and both dash edits update the original legend sample.
The MCP label baseline used zero margin: after-layout +1 pt preserves Axes but
both labels exceed the canvas by 0.423333 mm. This is a retained fit limitation,
not an accepted complete visual result. No margin/canvas change was made; it
requires a layout decision. Actual corrected PNGs and rasterized PDF pages
were inspected. `comparison.html` shows equal-scale real-render pairs/details.

Three harness findings are preserved separately: the first build was blocked
before an external bytecode write and succeeded with `python -B`; the first MCP
call was refused before source execution because its owned artifact root had
0755 instead of 0700; and an initial comparison incorrectly equated Agg/PDF
text metrics. One repair preserved initial evidence, fixed the owned directory,
and compared before/after within each renderer. Completed native candidates
were not rerun. No candidate was altered to improve its measured outcome.

## Distribution and checks

The explicit llms generator inputs were inspected before regenerating only
`llms-full.txt`; its non-writing check passes. Existing prompt tests: 23 passed.
No tests were changed or added, and no new mandatory CI gate was introduced.
Offline wheel-only build used existing cached PEP517 backend packages; local
target install used no dependencies. Against the Nov2 wheel, only recipes,
bundled llms-full and RECORD differ; every other payload member is identical.
Installed import origin, `get_prompt`, bundled llms text and the actual Client
recipes resource were verified against the final shipping source bytes.

See `qualified-outcomes.json`, `results.json`, `wheel-comparison.json`,
`candidate-source-and-artifact-hashes.json`, `original-source-hashes.json`,
`installed-guidance.json`, `mcp-recipes-resource-reply.json`, `pytest.log`,
`generator-final.log` and `commands.json` in the evidence root.

## Limits

This is one deterministic replay per corrected path/issue, with one bounded
harness repair, not a general autonomous-agent success rate. MCP transport was
in-process, not stdio. No remote CI, release, merge, deployment or human PoC
approval is claimed. Active autolayout/custom-handler variants are scoped by
the instructions and were not benchmarked. Parent review owns integration.
