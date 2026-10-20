---
orphan: true
---

# Viewer boundary repair — #499

Status: approved scope; independent review r1 reconciled on 2026-10-20; implementation pending. User accepted local-only ("추천하는대로 갈게").
That approval and #499 authorize this narrow local-only/create-only repair and plan; input defaults below grant no hosted access.
## 현재 권위와 상태

- **질문 종류:** 현재 실재 / 현재 계약 / 변경 의도.
- **role: purpose; path: `AGENTS.md`; 실제 정본:** project/user instructions.
  Native matplotlib objects, optional viewer, <=200-line designs, executable acceptance,
  shipped-color freeze, and actual before/after UI PoC before merge/deployment apply.
- **role: architecture; paths:** `src/dartwork_mpl/ui/ui.py`,
  `src/dartwork_mpl/ui/_config.py`, `src/dartwork_mpl/ui/_scripts.py`.
  `run(figure_fn, param_model=None, *, title, copy_to, host, port)` owns startup and HTTP routes;
  persistence uses fixed viewer filenames; client scripts manage tabs, saves, presets, reload.
  Current public bind disables Host allowlisting; no user authentication exists.
- **role: verification; paths:** `tests/test_ui_security.py`, `tests/test_ui_param.py`, `pyproject.toml`.
  Existing helper tests allow public hosts and miss real HTTP copy/overwrite failures.
  Python >=3.10; pytest collects `tests/`; the optional `ui` extra supplies FastAPI/Pydantic/uvicorn.
- No `docs/handbook/index.md` or legacy Handbook exists; these actual authorities are used directly.
  This repair does not initialize a Handbook. `docs/api/ui.rst` and `docs/usage_guide/interactive.md`
  document host/copy_to, parameter defaults/coercion, downloadable scripts and server saves.
## 지켜야 할 현재 불변식

1. Keep native viewing, parameter controls/defaults, tabs, downloads, presets, configured paper-image copies,
   and authorized reload; keep the public `run` signature and optional-extra boundary.
2. Preserve every pre-existing image/script target; safe saves may create new relative subpaths.
   Fixed viewer config/preset files remain intentional updates through a separate bounded sink.
3. Preserve the approved website/login/community/docs separation; no account system, remote service,
   viewer removal, framework rewrite, hostile-code sandbox, MCP or color/prompt changes.
4. Preserve supported ParamModel declared types, defaults, constraints and documented list-text input;
   active-request validation must not silently clamp numbers/drop fields or mutate the supplied model.
   Stored-model drift is projected explicitly on reads, without rewriting stored data.
## 설계 이유와 제약

- **role: architecture; paths:** `src/dartwork_mpl/ui/ui.py`,
  `src/dartwork_mpl/ui/_config.py`, `src/dartwork_mpl/ui/_scripts.py`; issue #499.
  Existing real HTTP evidence shows copy-root traversal and symlink overwrite (200), running-script
  overwrite (200), arbitrary-Host native write under public configuration (200), malformed state/config
  (500), and silently ignored render keys (200). Supplied foreign Origin is already rejected (403).
  Preset timestamp enters an HTML text sink unescaped; no remote XSS chain was demonstrated.
- Evidence: `~/scratch/dartwork-mpl-agent-loop-execution-2026-10-20/viewer/{report.md,http-evidence.json,probe.py}`.
  Those probes bound the actual socket to loopback and never invoked reload/overwritten code.
- Root confinement must cover each actual sink, not a resolved primary pathname reused for copies.
  No cross-root filesystem transaction exists; neither validation nor thread timeout is an OS sandbox.
## 충돌·미확인

- **Adopted target versus current reality:** local-only startup is approved; public-bind acceptance
  remains in shipped code/tests until this repair. Intentional overwrite is excluded from P0.
- Numeric input limits are measured against repository examples, not private user collections.
  Compatibility beyond those samples remains unknown; limits must be documented and fail explicitly.
- Race-safe filesystem primitives must be capability-checked before startup filesystem effects.
  Use actual no-follow/open/mkdir/unlink/rmdir/rename dir-fd primitives, not membership of `os.replace`.
  Where absent, return explicit 501 (`unsupported_filesystem_capability`) for affected filesystem operations,
  including auto-save/config/preset/delete; do not create roots/state or fall back to resolve-then-write.
  Keep render/download; safely unavailable stored-state reads report the same capability error and the UI
  shows defaults plus the limitation. No ctypes platform framework in P0; no Windows verification claim.
- Hosted access/identity and remote proxy behavior remain future separate design work. Loopback proves
  network locality, not human identity; same-user local processes remain trusted in this P0 policy.
## Narrow P0 behavior

### Startup and one route policy
Accept loopback IP literals (`127.0.0.0/8`, `::1`); map `localhost` directly to `127.0.0.1` without DNS;
reject wildcard/non-loopback/other hostname binds before uvicorn or filesystem mutation.
Keep the host argument for compatibility and return an actionable startup error for excluded values.
Do not configure Tailnet Serve, forwarded-header trust, a credential scheme or an account framework.
An operator-created proxy would intentionally extend this trust boundary and is outside this policy.
Declare all registered routes in one method+route-template policy, including framework read routes.
Reads receive an explicit local-read policy; changing routes receive local-effect scope or deny.
The local-effect grant is startup-selected loopback-only operation, not Origin/Host as authentication.
Cover POST render/export/script, save-state/config/preset, save-server image/script, DELETE preset,
and POST reload. Rendering executes the trusted callback, so it is an effect even without persistence.
Unclassified mutating methods/routes deny (403); a registration inventory check fails on any omission.
Every request requires a valid Host hostname in {`localhost`, `127.0.0.1`, `::1`, selected bind literal}.
Reject missing/duplicate/malformed/foreign Host (403), including userinfo/path/query/fragment/bad ports.
For effects, independently check each supplied Origin and Referer: valid `http` URL, exact same authority
as Host, no userinfo/fragment; Origin has no path/query, Referer may. Never compare to the bind port.
Malformed/duplicate/foreign sources reject (403); absent sources permit native clients. Ignore forwarded headers.

### Confined create-only outputs and bounded state updates
Accept `copy_to` as one `str | os.PathLike` or a list thereof; `expanduser`, resolve relative to startup CWD,
canonicalize script/copy roots independently, deduplicate `(st_dev, st_ino)`, and open directory handles.
Missing configured roots may be created only from startup configuration; root authority is the pinned directory object.
Use private typed Root/RelativeOutput/PreparedSave handles constructed only by this boundary.
Reject absolute, parent-traversal, NUL, blank, oversized and unsafe separator paths (400).
After extension normalization, plan every primary/copy target and validate all before rendering/writes.
Reject symlink components/final targets and non-directories; traverse using directory handles,
no-follow opens and fstat checks (unsafe paths: 400; existing target: 409).
Subsequent operations use those handles, never the original filename.
Pin each parent object; root/parent path replacement must never redirect writes to a replacement tree.
If its configured path identity no longer matches, reject with 409 when detected; do not promise
protection against a malicious same-owner process moving already-authorized directory objects.
Keep safe subdirectories; missing relative parents can be created only after the complete plan validates,
with handle-relative no-follow operations and rollback of empty directories this request created.

Existing targets at any destination return 409 before any target changes. No overwrite token/UI in P0.
Generate images with unchanged `save_formats(fig, <private staging>/<basename>, formats=(fmt,), bbox_inches=None)`;
preserve basename-derived SVG salt, metadata, validation and geometry. Stream completed staging files to sinks;
always remove staging and close returned figures. Script generation completes before destination writes too.
Enforce create-only with exclusive creation (not exists()+write); another writer's late creation returns 409.
Keep callbacks serial as today; serialize multi-root saves within the process and deduplicate destinations.
On a later reservation/write failure, remove only request-created files whose open-object identity still
matches, then remove request-created empty directories. Identity checks/cleanup are best-effort: an identity
check and unlink are not atomic, so no stronger guarantee against malicious same-owner replacement is claimed.
If cleanup fails, return a controlled 503 with a partial-save code and affected relative paths.
No success until every destination is complete; failures never change pre-existing files.
Crash/kill may leave newly created partial/complete files; a retry conflicts and requires a new name.
This is best-effort rollback, not cross-root atomicity; concurrent readers may observe provisional files.
Generated automatic names use collision-resistant suffixes and the same exclusive-create rule.

Config/preset writes use only the two fixed filenames below the pinned script root, a separate typed
sink, bounded read-modify-write, and sibling staging plus handle-relative atomic replacement.
Reject symlink/nonregular state files; serialize read-modify-write within this process only.
Multiple viewer processes sharing a directory can still lose updates (last replacement wins).
Replacement intentionally updates only these viewer-owned names, never a request-supplied filename.
Malformed JSON/UTF-8/top-level/entry shape or over-limit existing state returns controlled 409
(`invalid_stored_state`) on the relevant API; preserve the original bytes and refuse updates/deletes.
Missing state retains current defaults/empty-list behavior. Model field/type/range drift is not corruption.
Stored params receive structural JSON checks, never current-model value validation. GET config/presets project
only declared field names, report `dropped_fields` on config/each preset, and preserve original file bytes.
Project tab params too; out-of-range stored figWidth uses the UI default. Preset append/delete preserves all
other entries' raw JSON values. A retained field with an obsolete value can still fail active validation (422);
controls/reset remain usable. Defaults on a corrupt-state read do not authorize overwriting corrupt bytes.
Escape preset timestamp at its HTML text sink with the existing esc helper; errors use text sinks.

### One bounded input language
JSON-bearing routes require `application/json`, absent or UTF-8 charset, and no Content-Encoding (415 otherwise).
Read each body once, enforcing 1 MiB while streaming even without Content-Length, then use stdlib `json.loads`:
duplicate-key rejection via object_pairs_hook, parse_constant rejection, finite parse_float, and parse_int capped
at 640 digits. Invalid UTF-8/JSON, duplicate/non-finite numbers and RecursionError return 400; bounds return 413.
Walk the decoded value to bound depth/count/container/string sizes, then parse complete endpoint schemas.
Uvicorn owns ambiguous framing rejection before the app; verify it over a raw socket, not an app parser.
Wrong shape/unknown fields/invalid active values return 422. Errors retain `detail` and add a stable `code`.
Render/export/script/config/server-save/preset active params use declared field names only, including nested
closed models, even if a subclass sets extra=allow/ignore. Aliases are not an alternate wire language.
Preserve open dictionary fields where explicitly declared and bounded; apply existing supported UI
list-text coercion exactly once, then Pydantic validation/defaults; reject non-finite numeric results
after coercion too. Preserve default behavior; do not introduce startup default rejection.
State schema: active params object, tabs of {id,name,params} with unique integer ids (not booleans), bounded
names and declared-key bounded JSON params (no current-model value constraints on tabs); figWidth integer 30..100.
Omitted fields retain defaults. Preset save: label string and params object; server save: params/optional filename.
On-disk schemas additionally admit only existing function/updated_at and preset timestamp metadata.

Measured through actual _config save functions: 5 shipped/documented models; maximum 18 fields,
321-byte render, 349-byte preset request; 32-tab state 11,961 bytes/depth 4/726 values;
pretty-printed state 19,247 bytes and five stored presets 1,233 bytes.
Raw measurements/reproducer: `~/scratch/dartwork-mpl-followups-2026-10-20/viewer499/`.
Limits: 1 MiB request/config; 8 MiB preset file; depth 16; 65,536 total JSON values;
4,096 entries/container; 64 KiB/string; 64 tabs; 1,000 presets; 256 UTF-8 bytes/label;
1,024 UTF-8 bytes/relative output path, plus platform component limits. Check serialized next state
before replacement; existing large files are rejected before parsing. Limits include UTF-8 bytes.
There is no hard callback CPU/memory/deadline guarantee: synchronous trusted arbitrary Python cannot
be safely stopped by thread timeout. Callback failures are controlled errors; returned figures always close;
process isolation/deadline support requires a separate callback contract, beyond P0.

## Executable acceptance and scoped implementation tasks

1. Add a private cohesive boundary within `ui/`, wire startup and all existing routes through it;
   keep public imports/signature. Add confined sinks and fixed-state updates without moving other slices.
2. Add schemas/decoder, limits, timestamp escaping and conflict/corrupt-state/capability feedback.
   Explain “file exists; choose a new name”; no overwrite affordance. Check non-OK responses in init,
   persistState, savePreset and showLoadModal; auto-save repeats of the same 409/501 notify once.
   Update `run` annotations/docstring, `docs/api/ui.rst`, `docs/usage_guide/interactive.md`: local-only,
   create-only copies/new names, limits/errors, scoped 501 despite general OS-independent package support.
   Do not advertise untested SSH setup or a proxy as supported access.
3. Add `tests/test_ui_http_security.py` beside existing UI tests (pytest testpaths excludes src tests).
   Exercise a real uvicorn loopback socket and real temporary files; capture app/factory at its own seam.
   Check principal/action/object matrix: trusted-local × every effect × script/each copy/state root;
   foreign Host/Origin, non-loopback startup and undeclared effect all deny. Never bind a public socket.
4. Positive HTTP: render and PNG/SVG/PDF/script download; new image/script; safe subpath and multiple
   copies; config/tab update; preset append/delete; reload through an owned exec observer only.
   Negative HTTP: traversal/absolute/NUL/symlink file/parent/root swap; invalid second copy root;
   primary/copy/script collision; late external create; controlled parent swap between check and write.
   Compare full root manifests, bytes/hashes and outside sentinels before/after each refusal.
   Force later I/O failure and cleanup failure at owned sink seams; assert rollback/partial semantics.
5. Test malformed/deep/oversized/chunked/duplicate/non-finite/unknown inputs and corrupt stored state;
   type/default/list-text compatibility, stored field drift/shared directories, preset bounds and callback cleanup.
   Generated pure decoder/path properties must yield valid typed values or named rejections, never crash;
   observe regression red before fix and a plausible failing mutation for each new boundary assertion.
   Inventory registered routes and handle construction sites; injected unclassified route/raw-path bypass fails.

Required local gate: `uv run --extra ui pytest tests/test_ui*.py` (no optional-dependency skips),
targeted Ruff format/check and `uv run mypy src/dartwork_mpl/`; run normal repository CI after integration.
Add new UI modules to `scripts/check_integration_junit.py`'s protected executed-test inventory.
Build/install wheel+ui in one disposable environment outside checkout. Copy the self-contained HTTP test
module there (no conftest), run `python -I -m pytest -c <empty.ini> --rootdir <disposable> -p no:cacheprovider`,
assert parent/child imports are installed, record distribution/version/origin/results, then remove disposable files.
Use seeded `random.Random` for generated pure parser/path properties; add no dependencies.
Retain logs/manifests in scratch, not datasets or /tmp; do not execute an adversarial/overwritten script.
Before merge/deploy, render baseline and proposed UI at identical desktop/mobile sizes, show side-by-side
plus enlarged conflict/corrupt-state/capability feedback and timestamp sink evidence as workspace images.
Reuse `~/scratch/dartwork-mpl-followups-2026-10-20/viewer499/poc/`'s fixture/launch recipe; no layout redesign.
If browser review is needed, parent owns a persistent project-defined Tailnet HTTPS review service;
it must not expose this unauthenticated viewer's effect routes through a proxy.

No preceding ADR freezes viewer binding. This spec records the approved local-only/create-only repair;
an ADR is required if later preserving remote writes, introducing identity, or changing these grants.
