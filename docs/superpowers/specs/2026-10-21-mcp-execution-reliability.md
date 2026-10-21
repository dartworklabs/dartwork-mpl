# #498 local MCP execution reliability

Status: adopted for implementation under the user-authorized reliability restoration; parent adoption includes MCP-I1.
Original frozen design review: FAIL C0/I1; its newline contradiction is corrected below, not relabeled PASS.
Base: `d2b6d0b1ce8897d24398aa5a4de5d97f23ab2a05` (2026-10-21).
Authority: user approved the concrete repair proposal with 고; this records bounded implementation choices, not a new execution-approval gate.
Named brainstorming/writing-plans skills were unavailable in the parent's bounded search; neither is claimed invoked.

## Current authority and state

- role: architecture; path: `AGENTS.md`; invariant: native Figure/Axes, source compatibility, frozen shipped colors, designs <=200 lines.
- role: verification; paths: `pyproject.toml`, `.github/workflows/ci.yml`; invariant: Python>=3.10, existing pytest/Ruff/mypy and CI; no added dependency or gate.
- role: trust boundary; paths: `src/dartwork_mpl/mcp/execution.py`, `src/dartwork_mpl/mcp/tools.py`, `src/dartwork_mpl/mcp/artifacts/policy.py`; invariant: trusted local execution with inherited OS
  access/cwd and existing artifact limits.
- role: operator grant; path: `docs/integrations/mcp_server.md`; invariant: local clients share server OS-user authority; source 512 KiB, timeout(0,120],
  artifact 32 MiB, seven-day retrieval.
- role: task adoption; paths: this spec and paired checkbox plan; the user's concrete #498 restoration scope authorizes these bounded choices. The original draft/review hashes are
  `ccf5baccc22e84d422b4408432bf3eb7800cfd09289ed1ddb35822ca22902b97` / `129bef98b3f2bfb611e2287a1bbf7c312df4b998138038b674fa023335e3cf7a`.
- No Handbook exists; none is initialized. No excluded proposal or copy was consulted.

Frozen evidence names below refer to the parent handoff, outside the product tree; original receipts are preserved.

## Evidence and observed defects

1. `raw/input-boundaries.json`: registered validator callback raises TypeError/ValueError/OverflowError for malformed source/timeout; it accepts 524,289-byte source and 121-second
   timeout. Existing render parser rejects these.
2. `raw/finite-logs.json`: actual child returns 200,000 bytes on each channel without truncation; `execution.py` uses unbounded `subprocess.run(capture_output=True)`.
3. `raw/path-output.json`: each basic/advanced renderer reuses its fixed pathname; our pre-created symlink targets changed. Only fixture-owned files were affected.
4. `raw/ast-resource-failures.json`: bounded injected AST MemoryError escapes; RecursionError is swallowed by `lint._parse_source` and validator proceeds. No actual resource
   exhaustion was attempted.
5. `raw/fetch-boundaries.json`, `raw/urllib-real-redirect.json`: 2 MiB bodies are accepted; real urllib redirect machinery follows an off-host destination through our owned HTTPS
   stub. HTTPX currently rejects 302 without following.
6. `raw/client-summary.json`: real shipped stdio discovery is 19 tools/10 resources/9 resource templates/2 prompts, not the stale issue count 18.

## Principal, assets and boundaries

- Principal/grant: the operator who starts the local stdio server and its trusted clients, under that OS user's existing execution grant. A request id or artifact id is not new
  identity.
- Assets: parent process/diagnostic memory, private execution checkpoints, template output files, artifact bytes and outbound Raw GitHub fetch work.
- Inputs: source/options at registered callbacks; child stdout/stderr bytes; template copy destination; fetch URL, redirect Location, response encoding/body.
- Enforcement: existing `parse_render_request` source/timeout admission; MCP-owned preflight/runner collection; exclusive output-file descriptor; one fetch URL constructor and
  bounded adapter.
- Scope propagates through existing parsed render requests, inherited execution context and the existing artifact store. No new cross-user or hosted authority is introduced.
- No per-call approval, env stripping, cwd isolation, arbitrary repo allowlist, network sandbox, process-tree supervisor or hosted identity model.

## Request and AST handling

- Reuse existing `parse_render_request` admission for UTF-8 source<=524,288 bytes and actual numeric finite timeout in(0,120], default 20 seconds. Validator borrows only these two
  checks using neutral parser defaults for figure/hint.
- Validator maps InvalidRequest to existing `status="exec_error"`, empty lint/warnings/logs/checks, `validation_complete=false`, and bounded `stderr` containing field plus existing
  safe parser message.
- Semantic warnings retain existing presence iff a chart hint was supplied; no new status or wire field. Render retains existing `invalid_request` envelope.
- Preserve actual validator figure_var/chart_type_hint handling and named/last-pyplot fallback; do not import render's additional option restrictions into this source/timeout
  repair.
- Keep lint.py owned by the lint worker. Add a bounded MCP AST preflight before lint: catch only handleable MemoryError/RecursionError into `exec_error` with safe fixed diagnostics
  and exception class; do not echo source or infrastructure paths.
- Preserve existing SyntaxError/ValueError/UnicodeError handling rather than redefining malformed-source lint semantics; also catch resource errors escaping the lint call.
- Reason for preflight: outer lint catch alone cannot recognize its already-swallowed RecursionError. Cost: one additional AST parse of<=512 KiB; guarantee covers handleable
  failures, not recovery from interpreter termination or global OOM.

## Capture limits and compatibility split

- New legacy diagnostic choice: 64 KiB UTF-8 per stdout/stderr channel, including any visible truncation suffix and legacy timeout text. Template render errors keep their existing
  2,000-character presentation ceiling too, reserving the visible suffix inside that view.
- Marker: `\n[dartwork-mpl: stdout truncated; retained prefix only]\n` (stderr uses its own channel name). No count claims a discarded or partially observed total.
- Preserve stdout/stderr strings and all existing status/completion fields; add no flags, schema, tool or resource. Untruncated responses remain byte-for-byte equivalent after
  current decoding/newline/strip rules.
- Read at most 8 KiB raw chunks while polling/draining both pipes. Only finite submitted stdin framing uses a private temporary file, removed on every exit; stdout/stderr never
  spool. This adopted internal choice makes stdin seekable and avoids a blocking writer. POSIX selectors and Windows PeekNamedPipe retain platform-specific pipe handling.
- Windows read handles have one owner and no competing reads; the borrowed OS handle is never independently closed. Win32 documents blocking caveats for synchronous handles;
  Windows runtime/deadline behavior is not claimed verified on the available macOS host.
- MCP-I1: completed output keeps universal-newline translation; timeout output keeps original CRLF/lone CR after direct UTF-8 replacement. Legacy stderr strip and timeout suffix
  remain; artifact stderr whitespace stays exact. Independent bounded normal/timeout views choose truncation/refusal only from the actual outcome. One invalid byte may expand to3 UTF-8 bytes.
- At most8 KiB raw reads and24 KiB UTF-8 decoded chunks. Retained payload ceiling: legacy6*64 KiB across four prefixes/two pending-strip buffers; artifacts2*32 MiB across independent
  views. Marker/timeout decoration fit inside returned64 KiB. CRLF-heavy normal success must not be refused due to overflow of its unused timeout view.
- Artifact mode uses an independent **combined32 MiB UTF-8 log retention budget per outcome view**, supplied from existing `MAX_BUNDLE_BYTES`; successful bundles retain the exact original
  processed logs, including stderr whitespace.
- This is the minimal artifact split: log bytes alone over 32 MiB necessarily exceeded the prior serialized bundle budget. Below this budget, existing exact JSON/source/PNG/PDF
  total checks still decide publication, including JSON escaping expansion.
- On artifact log overrun, discard remaining excess, retain bounded 64 KiB/channel diagnostic prefixes plus markers, and return existing `artifact_too_large` error with incomplete
  report and no ID/image/links. Never publish a clipped successful artifact.
- Internal runner outcome can select the already-existing `artifact_too_large` transport category; no schema expansion. Do not call observed count the original output size.
- All subprocess/pipe/input-file resources are owned and cleaned on success, exception and timeout; preserve direct-child timeout/kill/wait behavior and private checkpoint
  cleanup. Cancellation remains owned/drained by current artifact lifecycle.
- Trusted code can still create native file effects and spawn processes. These log limits are not OS-memory, report-complexity, descendant-supervision or hostile-code guarantees.

## Template path publication

- Both basic and advanced path variants use `mkstemp` with random suffix and existing recognizable prefix, mode0600, then verify the open descriptor is a regular file and write
  through that descriptor.
- Return the existing absolute string `png_path` and existing success/tier fields only after successful close. Preserve base64 output and advanced fallback selection.
- Any copy/open/write/close failure removes only this newly created file and maps to existing `render_error` without private infrastructure paths. Do not unlink a pre-existing name
  or follow an existing symlink.
- Caller-readable output lifetime remains the current persistent temp-file convention; no cleanup service, artifact conversion or new retention promise.
- Exclusive creation protects against pre-existing collisions/symlinks; it does not promise immunity to a hostile local actor replacing a path after publication.

## Raw GitHub adapter

- Use one async HTTPX streaming adapter; `[mcp]` already declares `httpx>=0.27.0` for every supported FastMCP version. README lines 48/189 and MCP guide line 34 advertise that
  dependency, not urllib fallback.
- Remove the undocumented urllib fallback; convert private callback tests to await. MCP name/input schema/str result and ValueError failure shape stay unchanged; core-only import
  and CLI missing-extra hint stay intact.
- Parse into the exact `httpx.URL` passed to the request: HTTPS, exact canonical Raw GitHub host, no credentials, default HTTPS port only; preserve arbitrary
  owner/repo/ref/path/query. Fragments are not sent.
- Disable automatic redirects. Resolve each Location against the current parsed URL, re-run the same constructor **before** any next connection, close each response, and allow at
  most 5 hops (new bounded choice).
- Reuse current 10 seconds as a **total** request+redirect+body deadline using Python 3.10-compatible `asyncio.wait_for`; per-operation timeouts use the remaining budget. External
  cancellation propagates after response/client cleanup.
- New body limit 1 MiB: largest current bundled Raw document `llms-full.txt` is 76,102 bytes, giving>13x headroom. Count actual received body bytes; Content-Length is only an early
  reject, never the sole check.
- Request identity encoding and reject nonidentity Content-Encoding before body collection; stream raw chunks<=8 KiB, stop on the first excess chunk, close response/client on
  oversize/error/deadline. Accepted/retained body<=1 MiB; adapter-visible observed body<=1 MiB+8 KiB on refusal. HTTP/TLS internal buffers remain library-owned.
- Decode UTF-8 with replacement as normal Raw text; 1 MiB received can yield at most 3 MiB UTF-8 result with invalid-byte replacement. Do not describe the returned text as bounded
  to 1 MiB UTF-8.
- No external requests in diagnosis/tests: owned HTTPX transport/stream fixtures exercise normal Raw text, allowed/denied redirects, missing length, oversize chunks, encoding and
  slow streams.

## Changes, ownership and compatibility

- MCP owner: `src/dartwork_mpl/mcp/execution.py`, internal `_capture.py`, `tools.py`, narrow `artifacts/transport.py` error mapping, existing MCP boundary tests and MCP guide. No changes
  to storage/privacy/retention policy.
- Lint owner: `lint.py` and catalog remain untouched by this proposal. No private parse-result import or cross-slice authority graph is added.
- Keep validator policy reuse behind the MCP boundary; verify no import cycle or new core-only optional import. Existing `execution -> lint` public call remains; proposed validator
  request parsing uses the existing artifact policy parser surface. No new external dependency, runtime, package, public API or repository-wide graph gate.
- Docs must distinguish validator truncation from artifact exact-log refusal and document fetch limits, without changing discovery 19/10/9/2 or shipped color digests.
- Visible marker/refusal wording needs an actual rendered before/after PoC before merge. This diagnosis supplies no candidate implementation/PoC yet; plot image design itself is
  unchanged.

## Executable verification and stopping rule

- Mechanical decider: before/after captured envelopes, retained-buffer byte bounds during incremental writes, unchanged artifact source/log bytes for accepted cases, unique regular
  files and untouched owned symlink targets, bounded fetch traces and elapsed deadline checks.
- Seeded parser/collector properties: arbitrary bounded values yield a parsed request or existing refusal; every incremental chunk preserves prefix/retention bounds in both views. CRLF/loneCR/
  split-invalidUTF8/stderr-space real-child equality covers normal and timeout legacy/artifact paths; exact/first-excess scaled caps select the actual view. No added test
  dependency; valid controls and precise failure assertions required.
- Focused real-child checks: malformed/source boundaries; finite mixed stdout/stderr including invalid UTF-8 and CRLF; timeout; AST injected resource errors; basic/advanced
  concurrent path output and copy-failure cleanup.
- Preserve artifact accepted 200,000-byte logs exactly (`raw/artifact-finite-logs-summary.json` baseline); scaled-budget collector overrun proves refusal with no published bundle;
  retain existing exact bundle-size checks. Never allocate hostile exhaustion fixtures.
- Repeat shipped stdio journey: render named Figure and last-pyplot fallback, native cwd PNG equality, artifact requery and all five resources' sizes/digests/source/PDF, validator
  completion, namespace/SystemExit, discovery and existing safe errors; retain the nonidentifier/false hint control in `raw/legacy-option-control.json`.
- Run affected existing pytest modules, Ruff/mypy, existing docs checks if prose changes, then parent integration checks. Regression assertions must fail on baseline and pass after
  repair; no broad suite during diagnosis.
- Existing CI already gates tests across Python 3.10–3.13 and artifact contracts on FastMCP 2.13.3/3.4.2; host observation is Python 3.12.13/FastMCP 3.4.2 only. No-extras was
  simulated by denied optional imports, not a new bare installation.
- Parent releases the exclusive source window after CORE freeze, then reviews actual implementation and integration. Windows branch is static-only locally; Python3.10/other SDK runs
  remain CI coverage. No generic reapproval of the already-authorized trusted execution repair.
