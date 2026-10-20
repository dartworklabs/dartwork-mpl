---
orphan: true
---

# Viewer Boundary Repairs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Tasks 1–6 local evidence and handoff complete at `202db843`; parent confirmed pytest exit 0; upstream publication is tracked separately.
**Goal:** Repair #499 with local-only HTTP effects, confined create-only saves, bounded inputs, and recoverable state feedback.
**Architecture:** Keep the existing `ui` capability and public `run` entry point. Separate pure boundary decisions from directory-handle filesystem effects, then wire both into the existing routes and client; preserve `save_formats` unchanged.
**Tech Stack:** Python >=3.10, existing FastAPI/Pydantic >=2.0/uvicorn UI extra, stdlib JSON/filesystem/subprocess/random, pytest, Ruff, mypy.
**Spec:** `docs/superpowers/specs/2026-10-20-viewer-boundary-repair-design.md` (read completely).

## Global Constraints

- Approved 2026-10-20: user “추천하는대로 갈게”; local-only/create-only #499, existing callbacks serial, no overwrite/auth/proxy/new dependencies.
- Limits: 1 MiB request/config; 8 MiB preset file; depth 16; 65,536 total JSON values; 4,096 entries/container; 64 KiB/string; 64 tabs; 1,000 presets; 256 UTF-8 bytes/label; 1,024 UTF-8 bytes/relative output path, plus platform component limits; integer token 640 digits.
- Keep native matplotlib, the `run` keyword surface, defaults/types/constraints/list-text input and optional imports; never mutate the caller's model class.
- Preserve pre-existing files and stored corrupt bytes; structural stored checks/projected reads differ from strict active-model validation. Only viewer-owned fixed state names permit replacement.
- No output-size cap, overload429, startup default rejection, hostile-code sandbox, new runtime/package, layout redesign, or tested-Windows claim.
- Preserve shipped colors/hash pins, MCP discovery18/10/9/2 and five-member artifacts/seven-day retention. Never touch the excluded unrelated agent-contract draft.
- Log evidence under `~/scratch/dartwork-mpl-followups-2026-10-20/viewer499/`; no datasets or retained /tmp artifacts. Parent owns integration, final review, full-suite run and commits.

## 현재 권위와 상태

- **질문 종류:** 현재 실재 / 현재 계약 / 변경 의도. **role: purpose; path: `AGENTS.md`; 실제 정본:** project/user instructions, native plotting, <=200-line designs, executable checks and actual before/after PoC before merge/deploy.
- **role: architecture; paths:** `src/dartwork_mpl/ui/{ui.py,_boundary.py,_files.py,_config.py,_scripts.py}`; `run` owns routes/startup, fixed state files and client tabs/saves/presets/reload. Local-only startup and strict Host checks are implemented; identity is absent.
- **role: verification; paths:** `tests/test_ui_security.py`, `tests/test_ui_param.py`, `pyproject.toml`; baseline helper tests missed real HTTP failures; new real-socket coverage is present; pytest collects `tests/` and injects `src`.
- No Handbook exists; do not initialize one. `docs/api/ui.rst` and `docs/usage_guide/interactive.md` describe behaviors changed here.

## 지켜야 할 현재 불변식

1. Keep viewing/controls/defaults/tabs/downloads/presets/configured image copies/authorized reload and the optional-extra boundary.
2. Preserve all pre-existing output files; support new safe subpaths. State updates remain a distinct bounded fixed-name sink.
3. Keep approved website/login/community/docs separation; no account/remote service/viewer removal/framework/MCP/color/prompt change.
4. Keep supported declared types/defaults/constraints/list-text without clamping/dropping active fields or mutating the model; report stored projection explicitly.

## 설계 이유와 제약

- **role: architecture; paths:** `src/dartwork_mpl/ui/{ui.py,_config.py,_scripts.py}` and issue #499: real HTTP reproduced copy traversal/symlink overwrite, script overwrite, foreign Host writes, malformed-state500, and ignored render keys; supplied foreign Origin already rejects.
- Raw baseline: `~/scratch/dartwork-mpl-agent-loop-execution-2026-10-20/viewer/`; review: `~/scratch/dartwork-mpl-followups-2026-10-20/viewer499/design-review-r1.md`.
- Pin every actual sink independently; no cross-root transaction or trusted-callback timeout guarantee. Retain private staging through unchanged `save_formats` for deterministic bytes.

## 충돌·미확인

- Approved target is implemented in this worktree; no merge/deployment or hosted CI is claimed. Race-safe operations need actual primitive capability detection before filesystem effects; affected unavailable operations return501 while render/download stay usable.
- Bounds were measured on repository examples, not private collections. Multi-process state updates remain last-writer-wins; inode cleanup is best-effort.
- No remote proxy/identity or untested SSH setup is approved. Known-field value drift may still return422; reset/controls must remain usable without deleting corrupt bytes.

## Review Focus

- Renamed fields and two functions sharing a directory must not turn structurally valid state into corruption (Task3/4).
- Same field with newly invalid type/range must return422 while reset restores usable controls (Task4/5).
- A copy root aliasing the script root must create one file, including str/PathLike/~ and CWD-relative roots (Task2/4).
- Host/Origin authorities with userinfo, malformed ports or malicious suffixes must deny before a callback (Task1/4).
- Late external creates, parent swaps and failed cleanup must preserve old bytes and honestly report partial files (Task2/4).

## File and interface map

- Create `src/dartwork_mpl/ui/_boundary.py`: pure host/header/route policy, bounded JSON/schema/model/path decisions and closed refusal dataclasses; no filesystem/network imports.
- Create `src/dartwork_mpl/ui/_files.py`: root lifetimes, prepared create-only saves and fixed-state byte store; no model/HTTP/client knowledge. `_files` may import `_boundary` value types, never reverse.
- Modify `_config.py`: bounded state semantics/projection with the store; `ui.py`: startup/resources/HTTP wiring/staging; `_scripts.py`: response handling and escaping. Keep public `ui/__init__.py` exports.
- Create `tests/test_ui_boundary.py`, `tests/test_ui_files.py`, `tests/test_ui_http_security.py`; existing pytest testpaths exclude source tests. Each definition gets a behavior docstring.
- Failure aliases below are closed unions of named immutable refusals, with distinct variants where payload/status differs; one HTTP mapping emits `{detail, code}` and optional relative partial paths.
- Tasks1/2 may be assigned independently with these interfaces; Task3/4 integration follows both. No worker runs the full suite or commits.

### Task 1: Pure local policy and complete bounded input language

**Files:** Create `_boundary.py` and `tests/test_ui_boundary.py` under the paths above; update obsolete helper expectations in `tests/test_ui_security.py` only during Task4 wiring.
**Interfaces:** Produce `CopyTo = str | os.PathLike[str] | list[str | os.PathLike[str]] | None` (typing-only PathLike), `RelativeOutput(parts: tuple[str,...])`, `InputFailure`, `AccessDenied`, `StartupRejected` and `InvalidStoredState`.
Produce `normalize_bind(host: str) -> str | StartupRejected`; `authorize_request(method: str, route_template: str | None, raw_headers: list[tuple[bytes,bytes]], bind_host: str) -> LocalAccess | AccessDenied` and explicit `ROUTE_POLICY[(method, template)]` for every registered route.
Produce `decode_json(raw: bytes, *, max_bytes: int) -> JsonValue | InputFailure`, `parse_output(filename: str) -> RelativeOutput | InputFailure`, and `parse_request(route_template: str, value: JsonValue, model_cls: type[ParamModel], descriptors: list[ParamDescriptor]) -> ParsedRequest | InputFailure`.
Produce `parse_stored(kind: StateKind, raw: bytes) -> StoredState | InvalidStoredState` and `project_stored(state: StoredState, field_names: frozenset[str]) -> JsonValue`; StateKind is Literal["config","presets"]. ParsedRequest variants: `ModelRequest(model: ParamModel)`, `PresetRequest(label: str, model: ParamModel)`, `StateRequest(model: ParamModel, tabs: tuple[Tab,...] | None = None, fig_width: int | None = None)`, `SaveRequest(model: ParamModel, output: RelativeOutput | None)`; Tab has id/name/structural params; save-state defaults omitted tabs to empty, while config replacement omits unspecified optional fields. No downstream reread of raw request data.

- [x] Step 1: Add failing tests `test_public_bind_rejected_before_effects`, `test_effect_denied_for_bad_authority`, `test_decoder_rejects_ambiguous_or_nonfinite_json`, `test_active_fields_closed_even_when_model_extra_allows`, `test_tab_values_are_structural_and_ids_unique`; assert `normalize_bind("localhost") == "127.0.0.1"`, public bind→StartupRejected, duplicate JSON→MalformedInput, stale tab values accepted, duplicate/bool ids and unknown active keys→InvalidRequest. Approved default/list-text/alias-name cases pass; wire aliases reject422.
- [x] Step 2: Run `uv run --extra ui pytest tests/test_ui_boundary.py -q`; Expected: RED for absent behavior, recorded with exact assertions in scratch.
- [x] Step 3: Implement the interfaces: fixed localhost mapping, strict Host grammar/independent same-http-authority Origin+Referer (not bind-port equality); complete schemas/declared names and nested closed-model checks without mutating classes; bounded stdlib hooks and walk. Keep stored model drift structurally valid, bound outgoing serialized state too.
- [x] Step 4: Run that module; Expected: GREEN. Seed `random.Random(499)` arbitrary bytes/JSON/path cases: valid typed value or named refusal, no crashes; include exact-bound/one-over cases and invalid Unicode, duplicate/nonfinite/huge integer/deep values. Inject one route-policy omission and one raw-handle construction outside its owner; each boundary inventory assertion must fail, legal owner construction passes.
- [x] Step 5: Review diff/docstrings and record logical commit checkpoint `fix(ui): parse bounded local viewer inputs`; parent commits after integration.

### Task 2: Directory handles, create-only saves and fixed-state byte store

**Files:** Create `_files.py`, `tests/test_ui_files.py`; consume Task1's value types (the agreed declarations permit parallel work).
**Interfaces:** Produce `FilesystemCapabilities`, `detect_capabilities() -> FilesystemCapabilities`, `open_roots(script_root: Path, copy_to: CopyTo, *, cwd: Path, capabilities: FilesystemCapabilities | None = None) -> RootScope | FileFailure`; RootScope owns/explicitly closes descriptors, including partial startup failure.
Produce `prepare_save(roots: RootScope, output: RelativeOutput, *, include_copies: bool) -> PreparedSave | FileFailure`, `commit_save(plan: PreparedSave, source: BinaryIO) -> SaveReceipt | FileFailure`; PreparedSave owns pinned parent handles and cleanup, receipts contain primary/copy relative targets.
Produce `FixedStateStore(roots: RootScope)` with `read(kind: StateKind, *, max_bytes: int) -> bytes | MissingState | FileFailure` and `update(kind: StateKind, *, max_bytes: int, edit: Callable[[bytes | MissingState], bytes | StateEditRefusal]) -> StateWritten | StateEditRefusal | FileFailure`; StateEditRefusal = InvalidStoredState | InputFailure | StateUnchanged; StateUnchanged is a no-write callback miss, with no staging/replacement. Update locks the entire read/edit/serialized-bound/replacement sequence in this process; new-state overflow returns LimitExceeded413 without replacement.
FileFailure variants cover unsafe target400, target/root conflict409, unsupported501, I/O503 and partial-save503 (relative affected paths); callers never choose an arbitrary state name. Capability seam supplies unavailable primitives on POSIX without patching stdlib.

- [x] Step 1: Add failing tests `test_existing_primary_or_copy_is_unchanged`, `test_symlink_or_parent_swap_cannot_redirect_save`, `test_late_create_conflicts_without_overwrite`, `test_failed_second_write_rolls_back_owned_files`, `test_failed_cleanup_reports_relative_partial_paths`, `test_state_replace_preserves_corrupt_bytes_when_edit_refuses`; assert conflict variant and `after == before` full root/sentinel snapshots on refusals, rollback removes only owned files, partial result names exactly remaining relative paths.
- [x] Step 2: Run `uv run --extra ui pytest tests/test_ui_files.py -q`; Expected: RED with existing-target/symlink invariants visibly violated or new contract absent.
- [x] Step 3: Implement actual no-follow/dir-fd open/mkdir/unlink/rmdir/rename primitives and fstat identity checks; detect actual rename support, not `os.replace in supports_dir_fd`. Normalize one/list str/PathLike, expanduser/CWD-relative and dedup inode roots before requests; reject bad configured roots before any output save. Use O_EXCL and stage fixed-state bytes beside fixed targets before atomic rename.
- [x] Step 4: Run that module; Expected: GREEN including missing-parent rollback, primary/copy alias, second-root refusal, root identity changes, unavailable-capability/no-root-creation, state symlink/nonregular refusal, partial-startup/close cleanup. Seed path sequences with independent outside sentinel oracle; use owned file-operation seams only for deterministic late-create/I/O/cleanup failures. Record best-effort/race limits accurately.
- [x] Step 5: Review diff/docstrings and record logical commit checkpoint `fix(ui): confine viewer filesystem effects`; parent commits after integration.

### Task 3: State persistence without breaking model reload

**Files:** Modify `_config.py`, `tests/test_ui_param.py`; add state-semantic cases to `tests/test_ui_boundary.py`/`tests/test_ui_files.py` as appropriate.
**Interfaces:** Add `ViewerState(store: FixedStateStore, field_names: frozenset[str])` with `load_config()`, `load_presets()`, `save_config(parsed: StateRequest, function_name: str)`, `save_preset(parsed: PresetRequest)`, `delete_preset(index: int)` returning named success/miss/refusal values; constructor takes no raw request path. Keep `_config`'s existing internal helper contracts unless wiring demonstrably requires change; HTTP uses ViewerState exclusively.

- [x] Step 1: Add failing `test_drift_projects_reads_without_rewriting`, `test_other_preset_entries_survive_append_delete`, `test_shared_directory_models_do_not_corrupt_state`, `test_structural_corruption_blocks_update_delete`, `test_per_process_preset_updates_are_serialized`; assert `projected["params"] == {"opacity": 0.5}`, `projected["dropped_fields"] == ["alpha"]`, bytes unchanged on read/refusal, unrelated preset values equal before/after append/delete, and missing defaults.
- [x] Step 2: Run `uv run --extra ui pytest tests/test_ui_param.py tests/test_ui_boundary.py tests/test_ui_files.py -q`; Expected: RED on newly pinned state contract, old unaffected helper tests still pass.
- [x] Step 3: Implement structural-only stored parsing/projection via Task1 and atomic bounded updates via Task2. Never validate retained stored values against the current model or rewrite files merely to read; project tab keys, default out-of-range stored figWidth, retain unrelated preset JSON values and metadata.
- [x] Step 4: Run the same targeted command; Expected: GREEN, including 1,000-presets boundary and failed edits leaving bytes intact; document same-process lock and cross-process last-writer-wins.
- [x] Step 5: Record logical commit checkpoint `fix(ui): preserve state across parameter model drift`; parent commits after integration.

### Task 4: Wire every HTTP effect and exercise real sockets

**Files:** Modify `ui.py`, `tests/test_ui_security.py`, `tests/test_ui_hardening.py`; create self-contained `tests/test_ui_http_security.py`; modify `scripts/check_integration_junit.py` protected inventory for all new test modules.
**Interfaces:** Add private `_create_app(figure_fn, param_model, *, title: str, script_root: Path, copy_to: CopyTo, host: str, restart: Callable[[], None] | None = None, capabilities: FilesystemCapabilities | None = None) -> FastAPI`. `run` keeps keyword names/defaults, spells runtime-resolvable `str | os.PathLike[str] | list[str | os.PathLike[str]] | None` (internal CopyTo may remain typing-only), validates bind before filesystem effects, owns launch/resources; restart is the owned exec-observer seam.
The factory owns RootScope lifespan/ViewerState, callback serial execution and one refusal→HTTP mapping. Preserve framework routes and classify `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` as local-read; GET/HEAD `<unmatched>` retain normal404 after Host validation; unknown registered templates and all unknown mutations deny403.

- [x] Step 1: Build module-local fixture helpers and child bootstrap (no conftest imports): child imports `_create_app`, binds a real loopback socket/uvicorn, reports readiness and package origin, receives only temporary roots and trusted plotting fixture. Use stdlib HTTP/raw socket requests and real files, terminate/wait/remove child files in finally. `restart` writes an observer receipt, never execs user code. Assert child import origin equals parent's expected source/install root.
- [x] Step 2: Add `test_real_http_saved_targets_are_create_only`, `test_real_http_rejects_foreign_or_unknown_effect`, `test_real_http_bounds_wire_input`, `test_real_http_state_drift_and_corruption`, `test_real_http_downloads_and_reload`, `test_real_http_unsupported_filesystem_keeps_render`; assertions include `response.status == 409`, `after == before`, foreign effect403/no callback receipt, malformed400/oversized413/media415/unknown422, stored bad bytes409 unchanged, unsupported state501 + render200, reload observer count1. Run `uv run --extra ui pytest tests/test_ui_http_security.py -q`; Expected: RED on #499 before wiring.
- [x] Step 3: Wire streamed1MiB/media/encoding checks before Task1 parsing and all registered policies before callbacks; preserve bodyless reload/DELETE. Use Task2 prepared plans for primary/every image copy (scripts remain script-root-only). For images render once into private TemporaryDirectory using unchanged save_formats/basename, then stream to sinks; clean staging/figures on all outcomes. Return stable detail+code without payload/traceback leaks.
- [x] Step 4: Run HTTP module and affected existing UI modules; Expected: GREEN with PNG/SVG/PDF/script downloads, image/script new names/safe subpaths/multiple copies, config/tabs/preset append-delete/reload observer. Test bad Host/Origin/Referer before callback, missing/duplicate headers and malformed framing on raw socket, malformed/deep/chunked/oversized/nonfinite/unknown requests, all-root collision/symlink/late-create/controlled swap, model types/default/list-text, renamed fields/shared directories, known-field422/reset inputs, and501 with render/download200. Compare complete manifests/hashes/outside sentinels on refusals; no public binding.
- [x] Step 5: Confirm exact-bound parser and handle/policy guard regressions were seen RED; record targeted results and logical commit checkpoint `fix(ui): enforce viewer boundaries over HTTP`. Add `tests.test_ui_boundary`, `tests.test_ui_files`, `tests.test_ui_http_security` to protected inventory; check its missing/skipped-module rejection with existing checker tests. Parent commits later.

### Task 5: Honest client feedback, documentation and rendered PoC

**Files:** Modify `_scripts.py`, `docs/api/ui.rst`, `docs/usage_guide/interactive.md`, `run` docstring in `ui.py`; browser evidence in scratch `viewer499/poc/`.
**Interfaces:** Preserve endpoints/success shapes (preset list remains a list); added dropped_fields/detail/code are additive. Reuse existing text/esc/toast/reset controls; no new layout or overwrite action.

- [x] Step 1: Capture failing browser behavior for init409/501, persistState409/501, savePreset4xx/5xx and showLoadModal4xx/5xx: no false Saved/No presets, errors observable as text, same recurring auto-save409/501 notified once; record retained-field422 followed by usable Reset. Use actual frontend/temporary fixture or owned response adapter, not Python string-presence assertions alone.
- [x] Step 2: Implement response checks in exactly those four paths; keep default controls/init on bad stored reads, report dropped fields, preserve bytes, and escape preset timestamp through esc. Server collision explains “file exists; choose a new name”; never suggest overwrite or auto-delete corruption. Update API/interactive docs for local bind, CopyTo normalization, create-only copies/new names, all limits/error statuses, scoped501/OS-independent distinction and honest race/callback limits; no untested SSH instructions.
- [x] Step 3: Reuse baseline `viewer499/poc/fixture.py` and launch recipe; capture after at baseline desktop/mobile dimensions, matched scale; compose before/after images plus enlarged collision/corrupt-state/capability/timestamp and four error-path evidence. Actual screenshots are required before merge/deploy; pre-existing toolbar wrapping remains outside scope. Parent presents accessible workspace images; only a persistent project-defined Tailnet HTTPS service may serve static review evidence, never proxy viewer effect routes.
- [x] Step 4: Run affected UI tests and browser flows; Expected: GREEN feedback/recovery, no timestamp HTML execution, unchanged existing target hashes. Check docs link/code syntax and record logical commit checkpoint `fix(ui): explain safe saves and state failures`; parent commits later.

### Task 6: Installed-wheel proof and integration handoff

**Files:** Reuse `tests/test_ui_http_security.py`; save receipts/manifests/logs in scratch; no new dependency/configuration outside existing protected test inventory.

- [x] Step 1: Build wheel with `uv build --wheel`; create one disposable directory/venv outside checkout, install the wheel with `[ui]` and pytest, copy the exact HTTP module plus an empty pytest ini. Register cleanup before setup; remove venv/fixtures even on failure, preserve evidence logs outside disposable.
- [x] Step 2: From that directory run its interpreter: `python -I -m pytest -c <empty.ini> --rootdir <disposable> -p no:cacheprovider <copied_test_ui_http_security.py>`. Module asserts parent and child dartwork_mpl origins are under installed site-packages, outside checkout; record distribution/version/origin. Expected: same positive/negative real-HTTP module GREEN with zero skips; PYTHONPATH/source pytest settings/conftest cannot influence it.
- [x] Step 3: Local integrated gates complete: UI282/zero skips, targeted Ruff format/check and mypy109 PASS. Existing all-extras `UV_PYTHON=3.12 uv run --no-sync pytest tests/ -q --cov --cov-report=term-missing --durations=30 --junitxml=<integration/pytest-final.xml>` completed with5871 passed/zero failures/errors/skips, coverage91.69% (required80%); same-report JUnit checker PASS33 modules. Parent confirmed original exec71530 exit 0. Gate definition remains `.github/workflows/ci.yml` + checker; no new CI job.
- [x] Step 4: Local handoff evidence complete: RED/GREEN logs, wheel-r3 receipt, manifests and desktop/mobile before/after PoC shown inline; independent r2 review PASS/0 Critical/0 Important at202db843 (including78fa97c1/1d1d130d,8 pinned hashes). Local integration content verified by parent; upstream refresh/comparison, combined-diff promotion, commits and PR remain parent-owned. Preserve colors/MCP, <=200-line documents, cleanup and remote/Windows claim limits.

## Local closeout receipts (2026-10-20)

- Under `~/scratch/dartwork-mpl-followups-2026-10-20/viewer499/`: `boundary/nested-native-pass-report.json` (84 boundary + 45 state tests; nested native validation once), `files/report.json` (34 filesystem tests), `state/report.json` (state RED/GREEN and projection/limit mutations).
- Latest `http/wheel-r3/wheel-receipt.json`: exact copied HTTP21 + alias-state2 PASS/zero skips (45 deselected), installed imports outside checkout, base-only optional-absence/render/save smoke and disposable cleanup; wheel SHA256 `5926272330c87bdf7d924eae8b94b196c457ed9fc239de375f49673d2b76db20`. Older r1/r2 receipts and obsolete-pin preflight failure remain historical.
- `client/receipt.json`: browser fixture13 RED,16/16 GREEN; `poc/after-receipt.json`: desktop/mobile old overwrite200→new409, unchanged existing hashes, corrupt-state recovery, escaped timestamp and Reset. PoC already shown inline (T3 attachment `d0fb58d6-52f6-4b40-9456-3177e9eef7c1-4f26d371-cf80-47c9-8bcf-8d375c483b5f-html`).
- `../integration/`: `pytest-final.log`/XML5871 passed, coverage91.69%, `junit-guard-final.log` PASS33, `mypy-final.log` PASS109; UI282 and final Ruff PASS in `review-fixes-r1/`. `implementation-review-r2/report.md` PASS closes r1 I1/I2. Local content verified; parent confirmed pytest exit 0; upstream publication remains separate. No hosted CI, #470 speedup, release, merge, Windows or remote-auth claim; lifecycle approval and pre-existing generator-alias follow-up remain separate.
