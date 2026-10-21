# Checkbox plan — #498 MCP execution reliability

Prerequisite satisfied: parent implementation adoption corrects MCP-I1 from frozen review FAIL C0/I1; CORE/LINT source freeze released the MCP window.
Approved restoration scope: user's 고 to concrete code/timeout/output/tempfile/fetch repair; no new trusted-execution approval flow.
Unavailable named brainstorming/writing-plans skills are not claimed invoked. This is an explicit implementation draft for parent coordination.
Source: repository root, base `d2b6d0b1ce8897d24398aa5a4de5d97f23ab2a05`; frozen/final verification evidence retained in the parent handoff outside the product tree.
Runtime: read-only host venv; Python 3.12.13/FastMCP 3.4.2/httpx0.28.1. Keep -B/PYTHONDONTWRITEBYTECODE and task-owned cwd/cache/MPL/temp/artifact roots.

## Task 1 — reconcile authority and freeze narrow oracles

- [x] Step1: Parent compares base with current target using its authorized workflow; preserve host/index/main and the excluded proposal.
  Expected: actual source base known; conflicts resolved before implementation, no known-stale edit.
- [x] Step2: Read the task authority record, `AGENTS.md`, `pyproject.toml`, the MCP guide execution/artifact sections, execution/tools/policy and this draft's raw evidence.
  Expected: local OS-user grant, cwd/native save, namespace/fallback,19/10/9/2 discovery and original-artifact-log refusal retained.
- [x] Step3: Confirm 64 KiB legacy/channel, 32 MiB artifact/shared, 8 KiB reads, 10-second total fetch, 1 MiB identity body, 5 redirects and exact marker with parent scope review.
  Expected: concrete bounded implementation choices recorded; no new API/dependency/CI gate or generic user reapproval.
- [x] Step4: Assign MCP source/tests/guide to one worker; leave lint.py/catalog with lint owner; coordinate existing artifact budget caller only if needed.
  Expected: no simultaneous ownership of lint.py; no unrelated shared helper or public surface expansion.
Commit point: none; review gate only.

## Task 2 — source/timeout and handleable AST failure envelopes

- [x] Step1: Add focused failing cases in existing MCP validation/hardening tests, using actual registered callbacks and bounded inputs.
  Expected baseline red: nontext/invalid-UTF8/524,289-byte source, NaN/Inf/nonpositive/over120 timeout return existing exec_error envelope before side effects, rather than raising/launching.
- [x] Step2: Add legal boundary and seeded finite-value controls; preserve the validator's actual figure_var/hint behavior.
  Expected: 512 KiB valid UTF-8 and numeric timeout in(0,120] remain accepted; no accidental restriction of last-pyplot fallback.
- [x] Step3: Reuse existing render request source/timeout admission with neutral defaults for its unrelated fields; map refusal to legacy fields only.
  Expected: lint/warnings/checks/log strings/completion and optional semantic key remain compatible; render invalid_request unchanged.
- [x] Step4: Add MCP-owned AST preflight plus resource-error catch, preserving existing syntax fallback and source inertness.
  Expected baseline red then green: injected MemoryError and RecursionError become exec_error; no execution marker; no lint private imports or catalog edits.
- [x] Step5: Run focused validation/hardening cases; review extra parse cost on<=512 KiB and safe diagnostics.
  Expected: no new core optional import or cycle from parser reuse; raw failure/success runs saved; unexpected interpreter termination remains outside promise.
Commit point: one logical request/parser reliability change after review.

## Task 3 — bounded capture without clipping successful artifacts

- [x] Step1: Add collector saturation properties with seeded chunks, UTF-8 split sequences, invalid bytes and CRLF; observe retained budget after every append.
  Expected baseline red: current capture buffers exceed a small fixture budget; legal concatenation prefix/decoder semantics pinned without mirroring private collaborator calls.
- [x] Step2: Add real-child finite mixed-channel/timeout checks using modest output; retain original stdout/stderr strings below limits.
  Expected: selected-view UTF-8 legacy strings<=65,536 bytes each including markers/timeout text; normal normalizes CR/LF, timeout preserves CR/LF; low-level writes survive and excess never accumulates.
- [x] Step3: Implement owned bounded output polling and finite private stdin file, reads<=8 KiB, incremental replacement/newline normalization and bounded suffix reservation.
  Expected: neither output pipe blocks the other; input-file seekability is an adopted internal choice, not an output spool, no unbounded run(capture_output=True) or disk spool in affected paths; excess discarded during read.
- [x] Step4: Supply existing artifact 32 MiB shared log budget without copying this numerical policy into another independent owner.
  Expected: accepted 200,000-byte stdout/stderr artifact logs remain exact; existing serialized total 32 MiB check remains authoritative.
- [x] Step5: Exercise overrun through a scaled internal capture budget and existing artifact transport.
  Expected: existing artifact_too_large envelope, incomplete marked diagnostic prefixes, no ID/image/resource links/published bundle; never claim an original total from partial observations.
- [x] Step6: Verify success/error/timeout cleanup of child, owned pipe/writer/drain workers and checkpoint; retain current lifecycle cancellation/draining.
  Expected: no owned FD/temp leak; POSIX selector and Windows PeekNamedPipe close on all exits. Windows is static-only locally; no process-tree or hostile-code guarantee.
Commit point: one logical capture reliability change; do not include output-policy changes to successful artifact logs.

## Task 4 — unique regular template output paths

- [x] Step1: Add basic/advanced simultaneous path renders and an owned legacy-name symlink target fixture.
  Expected baseline red: two calls yield distinct readable regular nonsymlink files; owned target bytes unchanged. Keep tests' output under task-owned TMPDIR and unlink returned files.
- [x] Step2: Implement one internal exclusive mkstemp+descriptor write helper, regular-file fstat and success-only publication of existing png_path strings.
  Expected:0600, absolute unique names, same status/tier/base64 behavior and advanced fallback; no new retention promise.
- [x] Step3: Inject an adapter-owned copy/write failure against actual fixture-owned files and check cleanup/error envelope.
  Expected: only newly created file removed; existing render_error, safe bounded diagnostics and no leaked raw infrastructure path.
- [x] Step4: Run selected template smoke/asset-boundary tests and inspect actual returned PNG bytes.
  Expected: no renderer/template/catalog/color change; no orphan created files after tests.
Commit point: one logical template publication fix.

## Task 5 — one bounded Raw GitHub fetch path

- [x] Step1: Confirm `pyproject.toml` [mcp] declares HTTPX and current README/MCP guide advertise it; no public urllib fallback promise found.
  Expected: one async HTTPX adapter requires no dependency change; core import/CLI behavior preserved; private callback tests switch to await via asyncio.run.
- [x] Step2: Add owned HTTPX transport/async-stream cases before implementation: normal arbitrary repo, forbidden initial/redirect host/scheme/credentials, allowed redirect, loop/hop cap.
  Expected baseline red: every next destination validated before a request; no real network access; normal Raw text still returns str.
- [x] Step3: Add no-length/false-length/exact 1 MiB/over 1 MiB/raw invalid-UTF8/encoded-body cases and short injected deadline/cancellation streams.
  Expected baseline red: retained body<=1 MiB and adapter-visible read<=1 MiB+8 KiB before excess refusal, decoded UTF-8<=3 MiB, response/client closed on all exits; slow/trickling stream
  bounded by total deadline, not fresh per-chunk timeouts.
- [x] Step4: Implement parsed URL-to-request identity, manual5-hop redirects, identity encoding, raw<=8 KiB reads and10-second outer asyncio.wait_for with remaining per-operation timeout.
  Expected: no arbitrary repo allowlist, automatic redirect, unbounded read or fallback branch; external cancellation re-raised after cleanup.
- [x] Step5: Retain existing ValueError/str transport behavior and safe fixed limit messages; run fetch/hardening cases.
  Expected: raw transport traces prove denied destination never contacted and all content/time ceilings; no provider-payload/traceback expansion in errors.
Commit point: one logical fetch reliability change.

## Task 6 — compatibility, visible PoC and narrow completion

- [x] Step1: Update affected function docstrings and MCP guide only for changed behavior; retain artifact exact-log/refusal wording and discovery counts.
  Expected: changed function/type/helper docstrings state preconditions, result, effects and failures; documentation matches source limits/decoding/markers; no generated authority file
  altered implicitly.
- [x] Step2: Before merge, create an actual rendered before/after view for visible marker/refusal wording at equal zoom; parent presents it from a durable accessible artifact location.
  Expected: reviewable PoC for text changes; no new website/product flow or template visual redesign.
- [x] Step3: Repeat `client_probe.py` using shipped stdio with task-owned store/cwd.
  Expected: 19/10/9/2; named/fallback render PNG equals native cwd save; requery equal; five resource lengths/hashes/source/PDF; validator completion; namespace/SystemExit unchanged.
- [x] Step4: Repeat simulated missing optional imports and existing core-only CI contract review.
  Expected: base import/render/save works and CLI exits1 with existing install hint; report simulation versus real installation accurately.
- [x] Step5: Run affected existing tests, for example `python -B -m pytest -p no:cacheprovider tests/test_mcp_validation_contract.py tests/test_mcp_tool_hardening.py tests/test_mcp_render_smoke.py tests/mcp/artifacts/test_artifact_execution.py tests/mcp/artifacts/test_artifact_protocol.py --no-cov`.
  Expected: targeted pass with executed cases, baseline regression reds preserved. Add other affected cases only for changed concern.
- [ ] Step6: Run repository Ruff/mypy on changed Python and existing relevant doc-authority checks; parent runs required integration gates after target reconciliation.
  Expected: no new CI gate; current Python 3.10–3.13 and FastMCP 2.13.3/3.4.2 compatibility remains a CI requirement, not a falsely claimed local run.
- [ ] Step7: Parent reviews final source diff, byte/protocol oracles and real-client evidence; verify source-only boundaries, no artifact/privacy/retention/color/default/API expansion.
  Expected: complete repair against mechanical evidence; report any remaining runtime/cancellation paths not exercised.
Commit point: documentation/PoC evidence and integration record after independent review.

Worker handoff: local affected checks and actual candidate stdio proofs are complete; original failed/adapted-environment receipts are retained.
Step6 remains open for parent integration/CI and Step7 for independent final review. The rendered PoC must be presented before merge.
