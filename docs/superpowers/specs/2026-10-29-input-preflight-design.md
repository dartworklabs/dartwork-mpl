---
orphan: true
---

# Approved B/C input preflight design

**Scope approved; implementation pending.** The owner answered “후속 고” to
both recommended exceptions and local implementation. Approval receipt:
`~/scratch/dartwork-local-input-preflight-2026-10-29/approval.json`.
The approved research packet is
`~/scratch/dartwork-local-next-2026-10-29/input-decisions-repair-r1/decision-packet.md`,
SHA-256 `9343c1d4cf1b60102494967592a554fd471206851b93c94016fdf40fb8d6329a`.
Its historical UNAPPROVED heading predates the receipt; the receipt supplies
approval. Independent round-2 review passed decision readiness, not runtime
correctness. [ADR 0006](../../adr/0006-scoped-input-preflight-contract.md)
records the separately approved partial exception to ADR 0005 §1/§4.

## Current authority and state

- **architecture/public-contract role:** `AGENTS.md` and accepted
  `docs/adr/0005-capability-slices-and-test-colocation.md`; native Matplotlib,
  frozen public/discovery/edge interfaces except precisely approved B/C.
- **implementation role:** `src/dartwork_mpl/layout/__init__.py` owns margins;
  `src/dartwork_mpl/mcp/templates/render.py` owns template selection/render
  replies and existing `RenderOutcome` types. At local base
  `33f51edda7762324b9fda0f262739a0b60dbc68f`, B/C rejection is absent.
- **verification role:** current colocated tests, `tests/test_mcp_render_smoke.py`,
  and reviewed scratch `acceptance-after-approval.py` beside the packet.
  Recorded RED baseline: 15 preserved PASS, 20 expected new-policy FAIL.
  These are prior evidence, not tests rerun by this design worker.

## Current invariants

Native `Figure`/`Axes` stay native. Preserve finite margins (including zero,
negative and oversized values with existing `.001` clamp), parse/no-op and
GridSpec error precedence, unknown-template selection, successful base64/path
and advanced/basic-fallback behavior. Keep exact other edge errors.

Python >=3.10; no new dependency, CI gate or public API.
Keep signatures/static types, MCP names/order/schemas/registered docstrings and 19/10/9/2 discovery unchanged.
Keep artifact v1, shipped colors, presets and ADR 0001–0005 unrelated locks unchanged.
Work locally only; no fetch/network, remote writes, PR, messages, services or account workaround.

## Reasons and constraints

Stop silent broken layout and unnecessary template execution/temp/file effects
with the smallest contract delta. Keep checks in their existing capability
owners; no framework, cross-slice extraction or new status/type family is needed.
Existing typed outcomes and edge serialization remain the mechanism.

## B: finite effective margins

Complete current parsing (`margin`, `ml`, `mr`, `mt`, `mb`) and fraction resolution
before checking all four effective fractions. Horizontal lengths resolve against
width; vertical lengths against height. Reject NaN/+Inf/-Inf with exactly
`ValueError("margin must resolve to finite figure fractions")` before solving,
drawing, font adoption or any GridSpec/Axes mutation. Leave Length construction,
arithmetic, copying and units unchanged. Do not check the base eagerly.

Empty figures return None without parsing. No-GridSpec figures keep their exact
warning/no-op before parsing; existing GridSpec errors win. A malformed late
`mb="a%"` wins over earlier nonfinite inputs. Partial nonfinite-base overrides
reject; all four finite overrides succeed identically to a finite-base call.
No new positivity/range restriction or defaults.

Acceptance: nine NaN/±Inf × number/percent/arithmetic-Length base cases, each
individual nonfinite side, partial/full overrides, no-ops and late parse error.
On two-Axes figures with font adoption enabled, rejection has zero draws and
unchanged all-Axes bounds, full raw/resolved GridSpec edges and every existing
tick/offset font property. Compare finite bounds/edges/fonts and RGBA digests
with the pinned baseline under the same Matplotlib/font environment.

## C: selected-template format preflight

Select exactly as today (advanced first, then basic fallback). Unknown templates
retain complete existing diagnostics, sorted availability, null PNG fields and
advanced `tier="none"`, even with an invalid format. For a selected template,
only exact case-sensitive `base64`/`path` are valid; no trimming. Otherwise:

```python
{
    "status": "render_error", "plot_type": plot_type,
    "png_base64": None, "png_path": None,
    "stderr": f"return_format must be 'base64' or 'path'; got {return_format!r}",
}
```

Advanced additionally carries selected `tier="advanced"` or `tier="basic"`.
Basic has no tier. Fallback failure never has status/key `fell_back`.
MCP `isError=false`; text JSON and structured content encode the same dict.
Reject before renderer/child execution, render TemporaryDirectory or publication.

Acceptance: installed basic/advanced plus scratch basic-only fallback (empty
advanced directory); `bogus`, `""`, `PATH`, ` base64`; complete unknown+invalid
replies. Observe process and temporary/publication creation even if later
removed, alongside isolated temp-root inventories. Use real Client and real
files; redirect only owned listing/lookup roots and restore them. Replay valid
base64/path/actual fallback, actual short-timeout sleep templates, privacy and
publication-error fixtures on pinned baseline and changed source. Compare all
reply bytes and decoded PNG digests except fresh path names; paths must remain
unique private regular files with identical bytes/null-base64 semantics.

## Conflicts, exclusions and handoff

No Handbook exists; do not initialize one. Remote freshness/CI and implementation
GREEN/finite-layout/valid-reply comparisons are unverified. A/D/G deferred;
E arbitrary non-None find_template tier behavior and F native Text errors with
corrected guidance retained. Do not broaden their policies.

B owns layout source/colocated tests and any necessary narrow layout guide edit.
C owns template render source/colocated tests, narrow smoke-test additions and
any necessary narrow MCP guide edit. Parent alone owns shared CHANGELOG/bundles,
ADR status/index promotion and combined verification; workers do not regenerate
bundles. Review patches independently, then verify their combination locally.
No further user scope/execution confirmation is needed for this approved work.

Follow the parent exclusions, protected checkouts and read-only parent venv.
Use explicit target PYTHONPATH, no bytecode and scratch caches/temp/artifacts.
Do not overwrite the reviewed scratch baseline. Before any public merge, parent
shows actual before/after renders at equal scale (enlargements if needed), normal
output equality plus bad-input refusal; no aesthetic change is required. Local
image artifacts suffice under the current no-service instruction.

## Parent integration verification

After independent patch reviews, run in the combined owned checkout using the
same read-only interpreter and scratch environment as both plans:

```bash
"$PY" -m pytest src/dartwork_mpl/layout/tests src/dartwork_mpl/mcp/templates/tests tests/test_mcp_render_smoke.py tests/test_mcp_asset_boundary.py tests/mcp/artifacts/test_artifact_discovery.py tests/architecture/test_boundaries.py tests/test_shipped_colors_hash.py -q --no-cov -p no:cacheprovider
"$PY" -m mypy --cache-dir "$XDG_CACHE_HOME/mypy"
```

Expected: PASS and nonzero relevant collection; no skipped real-Client checks.
These reuse existing CI checks (`.github/workflows/ci.yml`), adding no gate.
Copy only the reviewed scratch oracle into a new worker-owned acceptance folder;
run it without `--baseline` on the combined source and compare its finite
snapshots with the preserved baseline. Expected: 15 preserved PASS and 20
new-policy PASS. Keep its historical mode label as history, not as authority.
Also require the plans' valid-render/fallback/timeout/publication comparisons,
which that oracle does not cover. Do not run broad documentation scans/builds.
