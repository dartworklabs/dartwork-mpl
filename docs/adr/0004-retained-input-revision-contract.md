---
orphan: true
---

# ADR 0004: Retained input revision contract

| 항목 | 값 |
| --- | --- |
| **상태** | 제안 |
| **날짜** | 2026-10-20 |
| **결정자** | 사용자 진행 승인 수신; 입력 선택 보완 정합 중 |
| **부분 대체** | ADR 0001 A1의 `mcp_discovery` live 전체 exact 일치 범위와 ADR 0003의 닫힌 7개 추가 목록만 — 결정 1·2의 `delete_plot_inputs` 한 개 추가 및 그 투영 범위에 한정 |

## Context — current facts and approval boundary

The shipped artifact implementation at `9c578b25` has production content equivalent
to merged PR #510 on main `4c28bbd3`. It exposes 18 tools, 10 static resources,
9 resource templates and 2 prompts. `render_plot` has only `code`, `figure_var`,
`timeout_seconds`, `chart_type_hint`; there is no revision or retained-input path.
Artifact v1 has exactly `plot.png`, `plot.pdf`, `source.py`, `report.json`,
`manifest.json`, a combined 32 MiB limit and seven-day retention. Its six manifest
keys are `schema_version`, `artifact_id`, `created_at`, `expires_at`, `files`,
`validation`. Reading it does not renew its lifetime.

ADR 0001 A1 freezes exact discovery through the historical comparison. Accepted
ADR 0003 permits exactly two artifact tools and five artifact templates, splitting
historical-core comparison from full-live discovery. It grants no later addition.
ADR 0003's implementation-pending prose is historical drift; actual code and the
artifact delivery design show implementation. This proposal edits neither record.

A recovered source cannot recover deleted CSV bytes by identity alone. The
[lifecycle proposal](../superpowers/specs/2026-10-20-plot-revision-input-lifecycle-design.md)
therefore recommends explicit, operator-authorized whole-file copies. That is a
new data-retention and API contract, not a consequence of the open report dict.

`AGENTS.md` requires a separately approved exception to a preceding lock. After
both lifecycle adoption and this bounded exception were explained, the user said
“좋아 진행해” and asked where inputs are stored, how users select them, and how
updated data avoids confusion. This is the go-ahead receipt for that explained
scope; it is not approval inferred from this ADR's existence. Exact wording and
new receipt engineering details are separated in the [freshness supplement](../superpowers/specs/2026-10-20-plot-revision-input-freshness-design.md).
This record remains a working proposal while those documents are reconciled;
that label does not cancel the receipt or require the same approval again.
No actual input policy/grant or product change has been deployed.

## Proposed decision — bounded scope with go-ahead receipt

1. Append exactly one tool, `delete_plot_inputs(artifact_id: str)`, after the
   existing tool registrations. Keep every existing identity and relative order.
   Add no static resource, resource template or prompt. The received go-ahead
   permits full live **19/10/9/2** after implementation. No future addition is allowed.
2. Preserve the frozen historical baseline and all pinned digests. Extend the
   explicit legacy-core projection by exactly that one tool, while retaining ADR
   0003's seven existing additions. Full-live source scanning, actual FastMCP
   discovery and `dartwork_mpl_info` must reveal the complete approved inventory;
   the projection cannot hide unknown registrations. Gate full names/category/
   order against unchanged legacy plus the seven accepted additions and this one
   tool covered by the bounded go-ahead receipt.
3. Permit only these related contract additions, as specified by the linked spec:
   optional `render_plot(..., revision: object | None = None)`; a closed version-1
   revision with optional verified `parent_artifact_id` and named `copy`/`retained`
   inputs; optional `report.provenance` with version, pinned parent digests, copied
   input identity/size/child locator/selection/evidence and `reproducibility:"not_claimed"`;
   read-only `dartwork_inputs` name→path global only for input-bearing requests;
   operator configuration selected only by `DARTWORK_MPL_INPUT_POLICY`; and the
   delete tool above. No prompt, intent, transcript, child listing or new locator
   resource is added. The spec and freshness supplement own exact keys, validation
   and error mapping. Per-input selection is closed `{kind:"copy"}` or
   `{kind:"retained",artifact_id,input_name}`; neither claims latest upstream data.
   Artifact creation time is child-copy publication time, not data capture time.
4. Keep legacy four-argument rendering behavior, report/source/log serialization
   and error enum. `revision=None` adds no injection or provenance. Render/get
   output envelopes, artifact v1's five members, six manifest keys, 32 MiB limit
   and seven-day lifetime stay intact. Internal input metadata is outside v1.
5. Retention is opt-in through an operator-owned private JSON policy naming
   `storage_dir` and `copy_roots`, outside `datasets` for stored copies and without
   artifact/copy-root overlap. No policy means no copying/reuse. Requests, source,
   hashes and model/data content grant no authority. Copy complete explicit files;
   do not discover dependencies or extract rows/columns. Per request allow at most
   **8 files, 8 MiB each, 32 MiB payload**; the input store allows **512 MiB and
   128 sets**, counting metadata, pending/reserved and revoked residual storage.
   No live eviction or threshold override is approved. Descriptor-confined reads,
   bounded streaming, copy 10s/post-check 5s deadlines and cancellation cleanup
   belong to this opt-in path, not an OS sandbox or universal wall-clock guarantee.
   Same-host local filesystems and keeping storage outside datasets are operator
   preconditions; configured overlap checks are not universal mount detection.
   Shutdown stops admission and drains owned calls/workers before closing FDs/lock.
6. Each child owns a new whole-byte copy set with its artifact's same ID, creation
   and expiry instants, expiring exactly **seven days** after child creation.
   A live verified parent/input set is pinned at admission; admitted work may
   complete after source expiry. Reads do not extend any lifetime. Revisions can
   create further independent seven-day copies; deletion/expiry never cascades
   to committed children. Delete revokes one complete input set, leaves all five
   artifact members intact, and returns `{schema_version:1,artifact_id,
   state:"deleted"|"absent"}` or the existing error arm. Revoked input lookup is
   `not_found` before expiry checks. Under the grant and serial lock, delete does
   not require live or valid metadata or a matching bundle: it also handles the
   spec's expired, revoked, corrupt/metadata-less, orphan and unknown-commit states.
   Only fixed owned names in validated no-follow directories may be removed;
   unknown/unsafe residue is retained, counted and returns `publication_error`.
   Delete, expiry and positively owned orphan cleanup share marker persistence,
   payload-then-metadata removal, set-directory fsync, marker removal, rmdir and
   storage-root fsync before `deleted`. Any failed barrier returns an error;
   `absent` also requires safe absence and root fsync. Failed marker persistence
   permits only current-process denial, with no restart-revocation guarantee.
   A changed/missing artifact root or absent/corrupt bundle never proves an input
   set unpublished. Startup rolls back only positively owned pending namespaces;
   unrevoked committed sets with valid metadata remain counted until their own
   expiry unless explicitly deleted. Restoring the original root before expiry
   allows reuse. Committed corrupt/metadata-less residue is not guessed away.
   Commit observation follows
   artifact-stage exit and is bounded manifest-only read with no root creation or
   cleanup; no persistent artifact-root binding or new configuration key is added.
   Offline bytes remain until next startup. Lost responses can leave a client
   without the ID needed to delete a counted copy until its seven-day expiry and
   offline cleanup; no listing/idempotency is added. Unlink promises neither secure
   erase nor deletion of backups/other copies. Fsync ordering and process-crash
   recovery are design intent, not a hardware power-loss durability claim.

The exception in decisions 1–2 changes only discovery comparison scope and the
closed addition list. Decisions 3–6 bound the associated proposal; they do not
release any color, algorithm, historical payload or other exact-surface lock.
The receipt covers the explained spec and exception together; writing this ADR
does not deploy a policy or grant access to actual inputs.

## Trade-offs and alternatives

Independent copies make deleted-workspace revision possible without re-executing
an ancestor or coupling a child to live ancestry. They cost sensitive-byte storage,
explicit grant/deletion policy, bounded allocation and paired-commit recovery.
Repeated revisions may retain the same bytes beyond the original seven days;
individual deletion deliberately offers no global derived-copy revocation.
Unavailable artifact roots preserve committed copies and consume capacity until
their own expiry; corrupt residual metadata can require explicit operator deletion.

Caller-managed durable inputs avoid server copies but leave availability and
permission with callers. Lineage-only is a valid separately scoped intermediate
step but cannot recover deleted input. A sixth artifact member, baseline digest
regeneration, silent discovery filtering and universal semantic/reproducibility
claims are outside this proposal.

## Consequences and application evidence

This record remains **제안** during freshness-document reconciliation and does
not change accepted ADR status or authority. The go-ahead above covers the prior
explained lifecycle and bounded exception; selection receipt is its unshipped
report clarification, not an unrelated public API expansion. Planning follows
this bounded review. Deploying operator policy is a later grant over actual roots.

Effect is **구현 뒤 현실 변경**: approval selects a target, while runtime remains
18/10/9/2 with four render arguments until implementation is verified. The spec's
G1–G8 are future executable acceptance criteria, not implemented/passed gates.
Required evidence includes legacy exact serialization, full-live/historical-core
checks, unchanged shipped colors/baselines, actual file/stdio deleted-original
recovery, independent child expiry, quota boundaries and commit/cancellation/
startup/close negative paths, root-change/restoration, all six delete states and
fault-injected barrier failures with real restarts. Supported FastMCP majors and
concurrent sessions must demonstrate one owned lifecycle; process crashes do not
prove hardware power-loss behavior. CI protection must actually run checks before
they are called merge gates. Update current behavioral documentation only against
that implementation evidence; do not rewrite accepted ADR history.
