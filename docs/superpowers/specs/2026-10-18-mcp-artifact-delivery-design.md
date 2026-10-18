# MCP artifact delivery

Date: 2026-10-18. Status: Approved and implemented; final integration review pending.
The user approved the complete design and separately selected
“이번 예외 승인 후 구현 진행 (권장)” for the precise discovery exception in
[ADR 0003](../../adr/0003-allow-scoped-mcp-artifact-discovery.md).
API names, storage limits and retention below are accepted engineering choices.
Implementation evidence is recorded below; no merge, release or deployment is claimed.

## Intent and scope

An agent submits plotting code once and receives the selected figure's PNG,
PDF, exact submitted source, validation report and manifest. MCP clients can
reopen the bundle after the call and after server restart, until expiry.
This milestone adds delivery, not data repairs, agent evaluation, chart styling,
HTTP hosting, authentication, an OS sandbox or a new native Matplotlib API.

## 현재 권위와 상태

No Handbook exists; this design does not initialize one. Current authorities:

| role | path | Current contract or observed state |
| --- | --- | --- |
| purpose | `AGENTS.md` | Native Figure/Axes, preset-relative drawing, ≤200-line designs; prior locks require separate approval. |
| execution | `src/dartwork_mpl/mcp/execution.py`, `tools.py`, `artifacts/` | Shared validation/export runner executes trusted snippets once with Agg, inherited cwd/save effects, private result framing and explicit incomplete checks. Existing template renderers return base64 or a local path. |
| export | `src/dartwork_mpl/io.py` | Public `save_formats` supports PNG/PDF and `validate=False`. |
| discovery | `src/dartwork_mpl/mcp/server.py`, `tools.py`, `resources.py`, `prompts.py` | Live server has 18 tools, 10 static resources, 9 templates, 2 prompts; scanners include `artifacts/transport.py`. |
| compatibility | `tests/test_color_v6_comparison.py::EXACT_FIELDS`, `src/dartwork_mpl/_colors/_catalog.py` | Historical projection preserves frozen discovery; full live discovery separately pins exactly the seven approved additions. |
| verification | `pyproject.toml`, `.github/workflows/ci.yml` | Python ≥3.10, FastMCP ≥2.13.3,<4; pytest collects `tests/`; CI runs Ruff, mypy and tests on Python 3.10–3.13. |

## 지켜야 할 현재 불변식

- Preserve existing tools, resources, prompts, defaults, status envelopes,
  figure selection, semantic-hint behavior, cwd and real snippet side effects.
- Preserve native validation behavior, failed-check IDs and incomplete status.
- Never regenerate color baseline payloads or shipped-color digests for this work;
  no color algorithms, registrations, values or rendering styles change.
- Add no runtime or test dependencies. Keep the core importable without MCP.
- Apply only ADR 0003's approved discovery exception; all other exact surfaces remain frozen.

## 설계 이유와 제약

The execution and export authorities above already implement the necessary
mechanics. A dedicated artifact capability gives new callers a uniform contract
without changing old render returns. A second execution could produce a different
random figure, so validation and export must share one execution and one Figure.
FastMCP resource references provide transport, not lifetime or storage policy.

Alternatives: an artifact mode on existing template renderers still needs the
discovery exception and does not cover agent-generated code; inline-only images
avoid storage but cannot provide durable source/PDF/report retrieval. The proposed
dedicated tools incur a small disk lifecycle and seven explicit discovery additions.

## Approved API and delivery schema

Add `render_plot(code: str, figure_var: str = "fig", timeout_seconds: float = 20.0,
chart_type_hint: str | None = None)` and `get_plot_artifact(artifact_id: str)`.
The first validates its request, executes once and publishes; the second only
reads a published bundle. Neither accepts paths, output names or storage roots.

Each successful call returns a native `ToolResult` containing one PNG
`ImageContent`, five `resource_link` blocks, and JSON `TextContent`. Identical
metadata is supplied as `structuredContent`; no image base64 belongs in JSON.
Metadata version 1 has `schema_version`, `delivery_status="ready"`, `artifact_id`,
`created_at`, `expires_at`, `files` and `validation` (report status, completion and
failed-check IDs). Each file entry has name, URI, MIME, byte size and SHA-256,
except the manifest's own hash, which is omitted to avoid recursive self-hashing.
Text and structured metadata must be JSON-equivalent, with a tested output schema.

Register exactly these five templates, in this order, with static MIME types:

| URI (prefix `dartwork-mpl://artifacts/{artifact_id}/`) | MIME |
| --- | --- |
| `plot.png` | `image/png` |
| `plot.pdf` | `application/pdf` |
| `source.py` | `text/x-python` |
| `report.json` | `application/json` |
| `manifest.json` | `application/json` |

`source.py` is UTF-8 encoding of the exact submitted string. `report.json` is the
complete execution/validation report, including lint, visual warnings, optional
semantic warnings, status, completion, failed IDs and stdout/stderr. Preserve
original logs; oversize output rejects publication rather than silently clipping.
Manifest v1 stores identity, timestamps, validation summary and the four data-file
entries with hashes; it does not list itself. Tool metadata adds the manifest's
URI, MIME and size without a digest. JSON is UTF-8; times are UTC RFC3339 with `Z`.

## One execution and explicit outcomes

Extract the existing validator's MCP-local execution shell into a declared surface
shared by validation and artifact delivery. Existing validator inputs/results stay
unchanged. An artifact request adds an export step inside that same child after
lint, execution, figure selection, visual and requested semantic validation.
Use the existing named-figure/last-pyplot fallback; reject a non-Figure selection.
Export only that Figure through `dm.save_formats(..., formats=("png", "pdf"),
validate=False)` to private fixed names. Do not apply extra style or layout.
The parent combines the child checkpoint with its captured logs and writes the
report; it never reruns the snippet. No success is published until all five files
are complete. Warnings and `validation_incomplete` can accompany a ready bundle;
they never become a clean validation result. Export failure retains known check IDs.

New-tool failures return `isError=true`, JSON text and structured metadata with
`schema_version=1`, `delivery_status="error"`, a stable `error_code` and safe message;
execution failures also carry the available report. No image, links or artifact ID
are returned on failure. Codes distinguish `invalid_request`, `configuration_error`,
`not_found`, `expired`, `corrupt`, `artifact_too_large`, `publication_error` and
existing execution outcomes (`lint_blocked`, `exec_error`, `no_figure`, `timeout`).
Infrastructure errors reveal no filesystem paths. Resource failures use the same
stable categories through MCP resource errors. Retrying render creates a new ID.

## Storage, limits and trust

Resolve `DARTWORK_MPL_ARTIFACT_DIR` once from server configuration: a nonempty
absolute path, otherwise `~/.cache/dartwork-mpl/artifacts`. Invalid configuration
fails the new capability explicitly; existing tools remain usable. This is runtime
data, not a user config file, and is never stored in the product repository.
Initialize lazily; directories are owner-only and files owner-readable/writable.
Create a server-bound store handle only in configuration wiring; all operations
require it. Requests cannot mint a handle or override its root.

Accept only full lowercase UUID4 hex IDs and the five literal members above.
Parse once into internal values; reject malformed IDs, separators, encodings,
symlinks and nonregular files. Open under the bound trusted root and verify the
opened object, not an earlier pathname check. Bound manifest parsing by bytes,
depth, field counts and exact v1 shape; reject duplicate keys and invalid sizes,
timestamps, hashes or members. Verify requested bytes against size/hash before
returning them; the manifest's shape/read bound is checked without a self-digest.

Reserve a fresh ID exclusively; no call may overwrite another bundle. Write in
private staging, then publish a complete manifest atomically as the commit marker.
Readers never serve an unpublished directory; failures/cancellation clean the
operation's staged files. Crash leftovers are unavailable and may be removed by
the owner. No restart depends on an in-memory ID registry.

Accepted limits: source ≤512 KiB UTF-8; finite timeout in `(0, 120]` seconds;
exactly five files, ≤32 MiB combined (including source/report/manifest). Bound
resource reads accordingly. These are request/publication bounds, not a child
memory/disk sandbox, global storage quota or concurrency guarantee.
Keep artifacts for seven days from publication; store immutable expiry metadata.
At `now >= expires_at`, bytes are unavailable. Access and new publication lazily
clean only validated expired bundles belonging to this store, never unknown or
corrupt directories. No scheduler or MCP deletion tool is added; the local owner
can remove the artifact directory. Retrieval does not extend expiry.

The principal remains the same trusted OS user of the existing local MCP server.
All clients attached to that server share access; IDs are references, not auth.
There is no verified tenant identity to propagate and no new remote hosting.
Source/log/export bytes remain local unless requested through MCP. This preserves
the existing arbitrary-code execution trust gap; it does not harden hostile code.

## Placement and approved compatibility

Own storage policy, parsing, publication and transport in `mcp/artifacts/`, with
declared `__init__.py` exports; `server.py` only constructs/binds the capability.
Keep parsing/expiry in a pure module importing no I/O, FastMCP or other features.
The artifact shell depends one way on the declared MCP execution surface and
public export/validation APIs. No core module imports this capability or FastMCP.
Mirror new tests under `tests/`, as `testpaths` excludes source-tree tests.

ADR 0001 A1 freezes `mcp_discovery`; ADR 0003 separately approves this exception.
Implement an exact historical core projection for
color comparison, and independently compare actual server discovery with that
core plus exactly two tools/five templates, preserving core ordering and identities.
Full live scanners/info must include the artifact module; filtering runtime
discovery to conceal additions is forbidden. Result: 18 tools, 10 static resources,
9 templates, 2 prompts. The frozen baseline bytes/digests and other exact surfaces
remain unchanged. Current implementation is checked against this approved policy.

## Verification and completion

Mechanical oracles: a real rendered PNG/PDF, persisted UTF-8 source/report,
their exact read-back hashes, and actual FastMCP discovery/serialization.
Use real Clients with 3.4.2 and minimum 2.13.3. Local probes confirmed that 3
needs explicit `ResourceResult`/`ResourceContent` MIME; 2 needs raw bytes/text
plus static decorator MIME. Exercise both adapters, tools and resource templates.
Prove one execution with a nondeterministic figure and an execution marker;
assert image/report/selected-Figure identity, failed IDs and unchanged old effects.
Cover repeats/concurrent calls, no overwrites, restart retrieval, controlled-clock
expiry (no sleeps), cleanup after failed publication, missing/corrupt/oversize files,
and seeded generated malformed IDs, escapes, symlinks and manifest inputs.
Add import-boundary and registered-entry-point policy checks, including deliberate
violations; record existing trusted-code identity gaps rather than inventing auth.
Observe red/green failures or representative mutations for new contracts.

Gate new tests via existing `uv run pytest tests/`; preserve the existing 270-test
MCP/integration contract selection plus native validation and frozen color/exact
comparison gates. Run Ruff check/format and mypy through existing CI commands.
Run focused artifact contracts in both FastMCP environments; report unrun Python
matrix/full slow suite/CI explicitly. Update discovery/count claims and MCP usage
docs only when implementation is approved. No visual design changes are proposed.

## 충돌·미확인

Task 1/2 checkpoints `c14dd7bd`/`8747bf1a` passed independent review with no blockers.
Local evidence: `.superpowers/sdd/2026-10-18-mcp-artifact-delivery/` reports/logs;
real Client render/get/five-resource demo passed on Python 3.10/macOS.
FastMCP 3.4.2/2.13.3 focused contracts passed; full slow suite, Python 3.11–3.13,
other OS/filesystems and remote CI are unrun. Task 3: 452 passed/1 stale live assertion,
repaired module 37 passed; native validation 116 passed. Final branch review pending.
