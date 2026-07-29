---
orphan: true
---

# ADR 0002: Separate shipped color compatibility from OKLab authoring

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-27 |
| **Decision makers** | dartwork-mpl maintainers |
| **Normative predecessor** | Git commit `6be8cb56b8752e03515101caa7ae2f6c52cc13dc` (legacy v5) |
| **Dependency status** | Standalone; supersedes the overlapping migration requirements of ADR 0001 without using ADR 0001 as baseline or review evidence |

## Context

The normative predecessor has not yet undergone the proposed migration. Its
compiler authors OKLCH hue/chroma while solving rendered output against CIELAB
`L*`; its multi-hue runtime computes selections rather than replaying a frozen
index manifest; and it has no v6 compatibility SSOT, shipped-tone policy, or
accepted 18-surface comparison asset. Files in a dirty worktree, including an
earlier spec, ADR, prototype implementation, or prototype JSON, have no
authority for this decision.

This decision therefore covers the complete ordered migration, not two
remaining clauses of an already accepted redesign. It first freezes the exact
predecessor outputs, then independently derives diagnostic observations from
those immutable bytes and admits an isolated
OKLab/OKLCH compatibility replay only after exact comparison, and only then
adds the generic authoring facilities below.

First, the compatibility migration may use a shipped-only two-stage boundary:
solve one actual `L` at probe chroma `0.04`, freeze that `L`, and then search
chroma. This reproducing primitive is not a true maximum at fixed modeled
relative Y and gains shipped authority only if the accepted predecessor
baseline proves exact output equality. It must never pose as the generic
authoring primitive.

Second, compatibility migration must replace predecessor runtime selection with
accepted frozen multi-hue indices. A later, separate OKLab/OKLCH candidate
selector and admission workflow is needed for a genuinely new family. After
the switch, falling back to optimization when a manifest row is absent would
hide corrupt build data and make runtime output depend on algorithm revisions.

The reproducibility design must also avoid two false forms of canonicality. A
raw whole-lock or whole-package-entry hash commits public identity to unused or
private URL/path metadata, while an opaque oracle `constants_sha256` without a
closed archived preimage cannot be independently recomputed. Both problems can
produce internally self-consistent hashes without the intended public or
scientific meaning.

Three further closure gaps matter at process and publication boundaries. A
sealed filesystem and from-empty environment do not by themselves prevent
CPython from running automatic `site` processing, executable `.pth` lines, or
`sitecustomize`/`usercustomize` before a Python-level broker exists. A retained
arithmetic-trace count and digest without the complete record array cannot be
verified after private runtime state is destroyed. And sealing only a primary
completion while reopening its referenced subordinate paths later does not
prove that one immutable, complete multi-file output set crossed the terminal
boundary.

The project therefore needs both stronger generic authoring behavior and a
harder compatibility boundary.

**Related design-decision axes:**

- axis 2 — domain identity: distinguish accepted catalog replay from color
  authoring;
- axis 4 — review authority: exact frozen compatibility and independent
  admission have different evidence;
- axis 10 — external review authority: CIEDE2000/CVD remain downstream model
  diagnostics; and
- axis 11 — temporal compatibility: published color bytes and indices are
  immutable unless separately approved.

## Decision

Create an immutable shipped-compatibility lane and a separate private
OKLab/OKLCH authoring lane through an ordered, non-circular migration.

The first implementation batch independently extracts the predecessor's 18
exact public surfaces into two non-aliased sealed ignored candidates with
separate evidence. Candidate migration code may not be imported to create
either one, and neither extractor may read the other's output. A third captured
cross-extraction invocation requires the two complete byte strings to agree,
copies one byte-identical final candidate, and publishes a closed manifest.
The design specification closes every surface's JSON grammar, predecessor
source symbol or public invocation, normalization, sequence, terminal-leaf
count, and cross-surface equality. Boolean and null are admitted only where the
exact `dm.list_colors()` taxonomy requires them; floating-point JSON values are
not. The observational extractor runs in one fresh process with MCP/default-
state discovery sealed before any style mutation; the independent static
extractor imports neither project nor matplotlib modules. This fixed order
prevents a style switch from rewriting an earlier discovery result, and multi-
hue selector indices are captured at choice time rather than inferred from
duplicate hex values.
A fresh A-then-B review must reconstruct and accept all six outputs. A separate
promotion batch then consumes only that closed output set, its complete
preinstall A/B and snapshot closure, and canonical maintainer approval. It
first installs that closure as a create-only content-addressed tracked archive,
then installs create-only
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/color_v5_compatibility.json`
and sibling `color_v5_baseline_acceptance.json` last as the pre-review
promotion completion marker.
Every leaf is written to fsynced same-filesystem private staging, atomically
installed without replacement, and followed by bottom-up directory
synchronization. Complete archive, compatibility, and acceptance are three
separate durable phases; no later phase begins before the earlier file-and-
directory barrier passes. Two sibling entries are not claimed to be one
crash-atomic transaction. A byte-identical partial
archive before either file, or a complete archive plus exact compatibility file
without acceptance, is recoverable by validation and create-only continuation;
acceptance without compatibility or any differing byte is fatal. The batch
then receives its own fresh A-then-B review on one unchanged clean-capsule
snapshot. Acceptance proves the completed preinstall review and byte-transfer
transaction; it does not by itself prove that this later promotion A/B occurred.

After promotion Reviewer B passes, a sixth closed archive-promotion kind,
`legacy-v5-baseline-authority`, performs a nonnumeric authority-finalization
transition. It consumes only the promotion subject, both PASS reports, their
historical input/control/evidence manifests and blobs, A's completion token,
the common reviewed snapshot archive, and a post-promotion four-key maintainer
approval. It copies that exact closure create-only beneath
`legacy-v5-baseline-review-v1/promotion-review/`, publishes the tracked
approval, crosses their file-and-directory durability barrier, and publishes
create-only sibling `color_v5_baseline_authority.json` last. The marker's
closed self-hashed record binds the compatibility and acceptance identities,
the complete promotion A/B sequence and snapshot closure, the post-promotion
approval, and the finalization provenance. It contains no containing Git tree
or commit ID, no `baseline_authority_commit`, and no future-review edge.

Authority finalization cannot change the reviewed archive/pair or any color
value. It is a deterministic completion binding of a finished review, not a
new semantic subject whose review would require another completion marker and
recurse indefinitely. The next compatibility batch independently reparses the
entire binding and has its own fresh A-then-B review. Only a later exact HEAD
containing the preinstall archive and pair, complete marker-reachable promotion
review archive and approval, and authority marker grants baseline authority. A
commit containing the exact pair before promotion B or without that marker is
therefore distinguishable and non-authoritative. No separate quality golden is
trusted: exact shipped bytes preserve deterministic
output-derived diagnostics when their implementations are unchanged. The compatibility batch therefore
leaves the predecessor validation implementations and thresholds unchanged and
reruns that gate suite as a sanity check; it does not pin a second set of v6
quality observations.
The baseline approval's closed walkthrough binds the predecessor/tree,
byte-identical final candidate, both extractor evidence records, cross-
extraction manifest, preinstall subject and A/B sequence, and reviewed snapshot
archive. It excludes the acceptance, promotion provenance, and future
promotion reports, so it is constructible without a hash cycle.
The tracked acceptance binds the completed preinstall review, while the fresh
promotion A/B sequence reviews the proposed asset/acceptance pair. It cannot
embed its own future promotion-report hashes without a cycle. The separate
downstream marker closes the opposite edge after B: marker → promotion-review
closure → reviewed pair. The compatibility migration records the exact later
full commit as `baseline_authority_commit`; offline verification must start at
the fixed-path marker and prove that the compatibility, acceptance, and every
acceptance-or-marker-reachable archived leaf are exact mode/blob/raw bytes in
that commit tree. For migration that authority commit equals the
captured HEAD. Every later consumer must additionally prove, from a closed Git
capsule, the unique literal first-parent chain from current HEAD to the
authority commit,
mode/full-blob-OID/raw-byte equality for every such authority path in both
trees, and no index/worktree overlay. A byte-identical copy in an unrelated
history, a commit reachable only through a second-or-later merge parent,
branch/ref/replace object, or live worktree presence grants no authority. The
first-parent restriction is intentional: each hop is locally verifiable from
one raw commit and keeps the capsule canonical without claiming that a partial
captured graph proves arbitrary Git ancestry. The authority commit must
therefore be the post-integration commit on the intended first-parent release
line, not a topic commit reachable only as a merge's secondary parent. The
acyclic dependency order is preinstall inputs → acceptance/pair → promotion
A/B results → authority marker → Git tree → authority commit → later migration
record; no object hashes one of its descendants.

Only a later batch, based on a new exact HEAD containing that complete verified
baseline authority closure,
may introduce the mapped-relative-Y solver, renderer, and two-stage probe-
chroma boundary under the exact compatibility names
`_solve_oklch_l_for_relative_y_shipped_compat()`,
`_render_oklch_at_neutral_tone_shipped_compat()`, and
`_max_chroma_at_neutral_tone_shipped_compat()`. Those functions acquire shipped
authority only after every catalog compiler is routed directly to that lane,
all 18 surfaces compare exactly, and the unchanged predecessor validation/gate
suite passes on those same bytes. Any
temporary shared `luminance_lock` boolean renderer is removed before
acceptance; unlocked comparison arithmetic receives an explicitly shipped
diagnostic-compatibility name but no predecessor authority. Outputs then become
an exact contract.

The migration-only legacy transform is part of this decision rather than an
inherited draft assumption. With
`legacy_Y_white=0.2126729+0.7151522+0.0721750=1.0000001`, it computes
`f=(L*+16)/116; raw_Y=(f*f)*f` for `L*>8`, otherwise
`raw_Y=(L* * 27)/24389`, then `target_Y=raw_Y/legacy_Y_white` and
`NeutralTone=float(numpy.cbrt(target_Y))` in exactly that binary64 operation
order without FMA or reassociation. The introduced compatibility policy pins
the observation ID `legacy-mapped-encoded-srgb-to-relative-y-v1`: it takes the
predecessor-compatible mapped encoded RGB produced after the final linear-
channel clamp and exact predecessor OETF, decodes each
channel through the predecessor scalar sRGB branch, forms the left-associated
dot with `(0.2126729,0.7151522,0.0721750)`, and divides only the completed dot
by `legacy_Y_white`. It is used for the search predicate, stored achieved Y,
and residual; the generic authoring lane instead observes its raw-linear
witness with the separately normalized row. This distinction is normative
because the two finite-precision associations can differ by one ULP. The
introduced compatibility policy also pins
40 mapped-relative-Y search iterations derived from the predecessor's 40
rendered-L* comparisons, 30 boundary tone probes, 22 boundary chroma
probes, probe chroma `0.04`, upper chroma `0.40`, the sequential boundary
fraction `0.97`, 24 gamut-map iterations, and linear-sRGB tolerance `1e-6`;
cyclic recipe fractions remain their separately captured predecessor values.
Predecessor CIELAB L* is used by the one-time migration/provenance path; full
CIELAB remains an internal downstream diagnostic coordinate, including for
CIEDE2000. Neither enters production authoring or construction.
Every stored migration tone is verified by replaying that forward transform
from the exact predecessor input bits; an inverse round trip is not required to
recover every L* bit. A closed, UTF-8-sorted 58-row mapping plan gives every
operational `Tone` leaf one exact predecessor JSON pointer, closed AST-literal
locator, or the one blue/red rendered-endpoint operation, and binds the complete
four-field projection with a golden hash. All real source values exceed the
L*=8 toe and therefore use the upper branch; lower-branch coverage is
synthetic. The predecessor Fourier family-derivation curves,
including the CIELAB floor curve, are retained only through migration
provenance and are not promoted into the direct-OKLCH new-family authoring
policy.

The authoring batch starts from another new exact HEAD containing the accepted
compatibility migration. A dirty worktree containing an earlier design,
prototype implementation, or prototype baseline cannot stand in for either
accepted predecessor phase. Present-tense user documentation activates only
after the corresponding implementation and evidence have passed both reviews.

The authoring lane uses actual OKLCH `L` by default. Fixed modeled-relative Y is
an explicit opt-in only when one authored path coordinate must place varying
hue/chroma points on the same nominal D65-sRGB modeled-relative-Y fiber. That
is a coordinate-topology contract, not a claim of perceived-brightness
uniformity, physical display luminance, accessibility, or shipped-catalog
fidelity; it is not selected through an ambiguous boolean. The generic fixed-Y boundary
uses a complete projective polynomial search over the raw sRGB cube for interior
targets and returns a verifiable boundary witness rather than assuming
monotonicity or an arbitrary chroma ceiling. Exact black/white endpoints use a
separate canonical-scalar policy because exact-rational expansion deliberately
retains sub-ULP matrix row-sum residue.

Existing package WCAG relative-luminance and contrast helpers remain preserved
public/validation utilities outside this authoring extension. V1 defines no new
WCAG policy, result schema, threshold contract, or hash domain and therefore
makes no claim that those helpers are replayably pinned by this ADR. They may
not construct authoring coordinates, choose hue/chroma/lightness, choose a
gamut intersection, rank selector candidates, enter the validation-oracle
policy, or determine admission, and one color cannot receive a general
“accessible” classification. Any future replayable pair-specific accessibility
contract requires a separate design and versioned evidence rather than an
implicit extension of authoring admission.

The independent direct fixed-`L` oracle keeps its rational isolating brackets
separate from production. A candidate's cross-lane algebraic identity is only
source rank, polynomial ID, and distinct-root ordinal; interval bytes are proof
witnesses and are not canonical identity. After the oracle independently
selects its maximum without access to production brackets, exact Sturm ordinal
checks prove each pair of brackets names the same root, and a trimmed monic
square-free GCD/common-root certificate proves coincident multi-source clusters.
Only the identity union, active faces, and derived candidate kind compare
exactly across lanes.

Both direct and fixed-Y scalar witnesses derive modeled relative Y only as
`(Y_r*r + Y_g*g) + Y_b*b`, with the three multiplications and two additions
executed in that association and no FMA/reduction/reassociation. Stored achieved
Y is bit-compared with that recomputation; fixed-Y residual is the one declared
subtraction. Authoring schemas recursively classify every binary64 leaf for
signed-zero handling before any range check or rational conversion:
nonnegative/rational operands reject negative zero, exact-zero fields require
positive-zero bits, and signed evidence preserves a negative zero only when the
specified input/operation produced it. Shipped bytes are unaffected. A merged
projective candidate also carries the complete ordered role union derived from
all sources—neutral, component boundary, stationary, requested cap—rather than
one lossy role label; source identities determine candidate order and ordinal.

Generation, rendering, discrete decoding, endpoint verification, the
projective proof checker, and both independent oracles share one closed
scalar-kernel record with exactly 49 binary64 leaves. It freezes sRGB8
decoding, the complete sRGB
EOTF/OETF, forward linear-sRGB→LMS→OKLab matrices and real sign-preserving
cube root, inverse structural-`L` affine rows, cubing, LMS→linear-sRGB, the
modeled-Y row, residual/direction associations, extraction, and same-base-
runtime replay scope. Its canonical JSON is exactly 4,121 bytes and its V1
digest is
`3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`.
Each standalone scientific artifact embeds the binding exactly once and every
policy reference resolves to it. Each implementation reconstructs the record
from its own private literal table, compares structure before hashes, and may
not use the artifact record or a producer/shared constants object as numeric
input. Source hashes are provenance, not a substitute semantic preimage.

The projective checker and direct oracle must also link their selected
certified coordinate and independently recompute direction-scaled `a,b`, raw
and encoded RGB, the appropriate neutral raw/encoded witness, modeled Y, and
the fixed-Y residual. Every bit and semantic ID is compared with production;
anti-collapse uses the recomputed neutral, never production's copy. Algebraic
agreement alone cannot yield PASS. “Exact” certificate arithmetic means exact
integer/rational arithmetic over frozen binary64 bit patterns, not exact ideal-
real color science; `pow`, `cbrt`, `sin`, `cos`, `hypot`, CIEDE2000's degree
conversion/`exp`, and directed `nextafter` are runtime-traced, so bit replay is
claimed only for the same accepted base runtime. Nextafter direction is encoded
by separate positive/negative operation IDs with one finite input and finite
output; infinity is an internal adapter literal, never a serialized operand.
Direct-oracle `down64` uses zero calls when nearest conversion is already below
the rational bound and otherwise exactly one negative-direction call; `up64`
uses the symmetric zero/one positive-direction rule. A generic walk or second
step is invalid and contextual replay fixes call order.

New multi-hue discrete candidates are selected offline using an OKLab maximin
objective and deterministic tie-breaking. CIEDE2000 and named CVD simulations
run only after selection under a predeclared admission policy. Accepted indices
and validation records are frozen into the SSOT before runtime can use the
family. A missing frozen row is always an error.

A versioned generation policy completely determines dense sampling, typed
rendering, OKLab arc resampling, output order, and 8-bit quantization for a new
256-entry LUT. A strict proposal envelope keeps a scientific payload—recipe,
policies, generated LUT, selected rows, validation rows, and oracle evidence—
byte-independent of approval history and invocation location. Its oracle
evidence identifies the accepted truth bytes with only truth ID/path and raw/
semantic hashes; it does not contain the bootstrap-acceptance path or hash.
Sibling public governance/reproducibility records bind prior approvals, a path-neutral
invocation recipe, captured source snapshot, stage-specific content-addressed
input bundle, normalized runtime-content identities, and a complete inline
call-order arithmetic-trace record array with its recomputable count and
domain-separated digest, plus their own public root hash. Every authoritative
environment retains exactly
`{policy_id, records, record_count, records_sha256}`: `records` is the complete
call-order array of closed `{operation, inputs, outputs}` rows, finite numeric
values use canonical `float.hex()` strings, the count equals its array length,
and the digest covers the complete array. The closed operation set includes
finite unary degree/exp adapters and fixed-direction positive/negative
nextafter adapters, so CIEDE2000 and successor construction cannot escape or
require a non-finite trace operand. The implementation spec closes all 14 rows'
call shapes and semantics: unary scalar math/directed-nextafter and scalar
NumPy cbrt are `1×1→1`; ordered `atan2`, binary-only `hypot`, and power are
`2×1→1`; `dist` is exactly two three-component vectors; and `fsum` is one
ordered vector of length `1..4096`, further constrained to each algorithm's
recomputed prefix/gap length. Power deterministically uses an integer exponent
when its canonical binary64 exponent is integral and Python-float power
otherwise, so caller type cannot select different arithmetic. Cbrt requires a
scalar `numpy.float64` call and immediate Python-float extraction. The offline
verifier and rejection suite consume this same table rather than inventing
arity or vector rules. Even the admitted empty trace retains
explicit `records=[]`; it is permitted exactly for
`legacy-baseline-extractor-a`, `legacy-baseline-extractor-b`,
`legacy-baseline-cross-extraction`, `policy-preselection`, and
`characterization-verification`. The other six environment profiles require a
nonempty trace. A count/hash-only substitute is invalid. Ignored
preselection, proposal, comparison, and review artifacts are producer paths
only: every downstream stage captures their exact bytes create-only and reads
only its immutable input bundle. Completion inventories are closed per schema:
only comparison owns an artifact map, named-output schemas enumerate their
literal paths, and report-only schemas permit no ordinary subordinate output.
Every native producer closes the complete authorized primary-plus-subordinate
set and writes a private terminal manifest last. That acyclic manifest names
each relative path, kind, byte count, and raw hash but is not referenced by the
primary. After the non-resumable terminal stop, the supervisor kills/reaps,
copies and fully seals every member, proves exact set equality, and a byte-only
publisher installs subordinates first and the primary completion marker last.
Every review separately captures an immutable pre-run control bundle
containing harness, prompt, scope, and—for B—the A-completion token; post-run
evidence must reproduce those bytes and add a closed public structured log.
That log ends in exactly one domain-separated, self-hashed terminal result. The
outer report derives and cross-binds its terminal ordinal, terminal hash,
verdict, and findings from that sealed result; the dependency order from
control through terminal result/public log, evidence, and report remains
acyclic. Provider run/session identifiers, raw conversation, and raw tool
transport remain private and are neither hashed nor archived.
Discrete thresholds and admission floors must already occupy a reviewed,
maintainer-approved immutable policy-registry entry referenced by the current
membership index, updated by the guarded compare-then-replace transition,
before selection begins.
Policy promotion archives and independently revalidates both reviewers'
historical external-input, control, and evidence manifests and all declared
blobs. Each immutable entry binds both external-input bundle hashes and both
complete execution-input hashes. Before Reviewer A, a distinct captured
environment-v3 verifier independently replays the tracked discrete or
admission characterization: it recompiles/decodes the LUT and reruns selection,
or rederives authority rows and reruns the validation oracle. Its ignored,
self-hashed evidence owns the exact source snapshot, no-site startup, native
closure, complete inline arithmetic trace, and terminal handoff. Reviewer A's
real external-input manifest contains exactly that evidence; B carries A's
historical copy, and both reports, the maintainer walkthrough, and the final
entry bind its raw and semantic hashes. The promotion is itself a closed, nonnumeric byte-
transfer transaction: it captures a role-complete immutable promotion bundle,
including the canonical maintainer-approval file, and embeds its complete
`ExecutionInputs`, source snapshot, source files, and self-hashed archive-
promotion provenance in the entry before the registry index gains authority.
It strict-parses and reconstructs the accepted verifier evidence/hash DAG but
does not import or execute color arithmetic.
Discrete approval is specific to the complete recipe, generation policy,
renderer policy, recomputed LUT-input hash, and actual LUT bytes; a policy ID
alone is not reusable authority. Admission reference rows are derived only
from immutable accepted shipped-compatibility or previously frozen authoring
assets, are byte-excluded from the candidate rows, and are evaluated against a
separately accepted create-only validation-oracle truth asset. The first truth
bytes are authorized by a dedicated preinstall subject, fresh sequential A→B
review, maintainer walkthrough, complete tracked snapshot/review archive, and
fixed-path bootstrap acceptance. Promotion writes that acceptance create-only
before installing truth create-only from the reviewed archived candidate blob.
One preinstall acceptance is sufficient because this is curated-byte
installation, not fixed-Y's independent-regeneration claim. Downstream
admission characterization, registry entry, and preselection bind both the
truth payload hash and sibling bootstrap-acceptance hash. Proposal governance
binds those objects through `policy_approvals` and its public reproducibility
root, while the proposal's scientific truth record binds only the truth bytes.
Creation and promotion must traverse both layers and require the acceptance's
truth cross-links to equal that scientific record; the truth does not point
backward to acceptance. Every reference-member validation hash
has an exact domain-separated preimage binding validation policy, truth,
bootstrap acceptance, authority-derived hex row, identity, `n`, and all three
replayed metrics.
Promotion replays those computations and create-only copies the unchanged
payload into a separately validated per-family frozen manifest; runtime only
validates and replays that manifest.

Scientific characterization is split from invocation provenance. The tracked
fixed-Y asset contains only a canonical scientific payload; fingerprints,
source snapshot/input bundle, path-neutral environment and invocation recipe,
and repo-relative implementation-source hashes live in separate evidence. Raw
host/path/argv/cwd/env/PID/loader/capsule path, descriptor, inode,
mount/namespace, address/load base, and provider transport remains private and
cannot enter any public hash. The ignored candidate and evidence
first require their own A→B review. Only then is the payload installed
create-only from the reviewed blob promoted into a tracked create-only review
archive. A fresh post-install snapshot regenerates it in a process whose
declared source set excludes the expected asset; after sealing that output, a
different verifier process may read both files and prove byte identity. The
post-install subject then receives a second A→B review and its own tracked
acceptance. Normative claims require both archived acceptances to bind the same
raw and semantic payload hashes as the tracked scientific asset. Each
acceptance also binds a complete content-addressed archive of the reviewed
execution snapshot, including canonical fingerprint preimages, the closed Git
capsule, and source bytes, so the historical hash DAG remains independently
verifiable after the original worktree changes or becomes inaccessible. Every
generation/verification phase manifest embeds the complete declared-source
array and a byte-identical copy of its environment-owned complete computation
broker-read array, not only their hashes; both bootstrap sources and control-
only registry/shell identities remain cross-linked through startup/handoff
records. The review
subject carries each phase's real input manifest and blobs.

Snapshot archives are self-addressed by their own archive hash. Loose Git
objects use one canonical stored-block zlib representation, so equal snapshot
bytes cannot acquire different archive identities merely because a compressor
made a different valid choice. Tracked archive leaves use Git mode `100644`;
the `0555` directory and `0444`/`0555` file seals apply only to ignored live or
detached materializations and are not representable tracked-directory claims.
Archive-only policy, fixed-Y acceptance, and validation-truth bootstrap
promotions bind their own complete input bundles and canonical maintainer
approval through closed promotion provenance; they do not pretend to be
floating-point environment-v3 runs.

All durable tracked create-only and guarded-index-replacement lifecycles use
one publication decision.
A final immutable leaf is never populated in place: complete bytes and logical
mode are written to unique same-filesystem private staging outside the
repository, short writes are handled, the file is synchronized and verified,
then the final dirent is atomically created only if absent. Exact existing bytes
are reverified and resynchronized; differing/torn/wrong-type targets remain
fatal and untouched. Missing parents are created top-down without following
symlinks, and each phase synchronizes affected directories bottom-up through
the first pre-existing ancestor. An overwrite-capable rename, direct
`O_EXCL`-then-write at the final path, file-only `fsync`, delete-then-rename, or
directory existence as completion is insufficient. Unsupported no-replace or
directory-sync semantics fail closed.

The mutable policy index uses guarded compare-then-replace, not a lock-free or
filesystem-content CAS claim. Every conforming publisher holds the same
abstract repo-scoped exclusive writer guard from expected-old comparison
through atomic rename, directory synchronization, and postcheck; a backend
that cannot demonstrate mutual exclusion among conforming publishers fails
preflight. Conforming writers therefore serialize and stale inputs fail. A
non-cooperating process with direct write
access is outside that concurrency guarantee and can race an ordinary Linux
rename; the next observed mismatch fails integrity, but the design does not
claim the intervening write cannot be overwritten. Non-directory-leaf alias
checks record `st_dev/st_ino/st_nlink`, require link count one and unique inodes
across the reviewed-plus-overlay/target set, and repeat through no-follow
regular-file or `O_PATH|O_NOFOLLOW` symlink descriptors at barriers and final
verification. Thus a pre-existing hard-link alias cannot pass merely because
its bytes and mode match.

Ignored live external-input, review-control, and review-evidence bundles use a
different whole-tree primitive. Blobs and then `manifest.json` are written,
mode-synchronized to `0444`, their directories mode-synchronized to `0555`,
and the complete private same-filesystem tree is atomically installed no-
replace. The visible result is absent or complete; an exact existing tree is
rehash/mode/link-checked and re-synchronized bottom-up before no-op. Tracked
archives continue to use `100644` leaf publication and a manifest marker.

Content-addressed bundles and snapshot archives publish all blobs, cross a
durability barrier, then publish `manifest.json` as completion marker. Baseline
uses preinstall archive → compatibility → acceptance, then, only after
promotion A/B, promotion-review archive → tracked post-promotion approval →
authority marker; policy uses archive → entry →
synchronized/revalidated old-index guarded replacement; fixed-Y uses archive → stage
acceptance, then durable preinstall acceptance → payload; truth uses archive →
bootstrap acceptance → truth; frozen families use captured promotion bundle →
frozen envelope. Every arrow includes a file-and-directory barrier. A power-
loss model independently loses unsynchronized file data, leaf dirents, and
`mkdir` dirents and must prove that a surviving marker/index always has every
prerequisite. For baseline finalization, an exact promotion-review archive
prefix or complete archive-plus-approval without the marker is resumable and
non-authoritative; a surviving marker with any missing, differing, aliased, or
unbound prerequisite is fatal. Retry may complete only exact durable prefixes.

Frozen-family retry applies the same rule to its early existing-target path: it
revalidates and re-synchronizes the complete captured bundle and envelope
before returning no-op, while a bundle-only prefix resumes at envelope
installation. A synchronization failure after an exact leaf becomes visible is
a fatal but resumable exact prefix—not an “untouched” state—and may not advance
to a marker or index switch.

A durable snapshot archive is also a publication boundary. For every path it
derives HEAD/index/worktree/reviewed states and requires every non-HEAD index or
worktree state to equal the exact reviewed mode/content state. This rejects a
staged secret hidden beneath safe reviewed worktree bytes at the same declared
path, as well as unrelated staged, dirty, deleted, or untracked state. The live
index is parsed only to resolve stage-0 meaning; stat fields, optional
extensions, split-index layout, shared-index files, and raw index bytes are not
published. The capsule contains one deterministic version-2 zero-stat,
extension-free index built from that meaning. Raw common/worktree
Git config is transient validation input only. The archive contains a canonical
synthetic config derived from object format and a closed operational projection;
it never stores raw config bytes or hashes, comments, remote/branch names or
values, or `config.worktree`. Thus local credential-bearing URLs cannot become
tracked evidence. The complete HEAD and approved source closure remains
self-contained and offline-verifiable. Review and promotion therefore run only
from a new isolated clean Git capsule reconstructed from that exact HEAD, with
no alternates/shared object store, inherited config, remote, replace/graft
state, or linked-worktree administration, and then overlaid with exactly the
declared reviewed source states. The declared set `A` may include project
sources that still equal HEAD. The actual deviation set
`D={p | I[p]!=H[p] or W[p]!=H[p]}` must equal exactly
`{p in A | R[p]!=H[p]}`; unchanged `(H,H,H,H)` declarations are valid and do
not enter `D`. A dirty feature/main worktree may supply those
guarded bytes, but it is never the review root or archive baseline. The harness
rejects it rather than hashing or allowlisting unrelated local state. For the
current two-document pre-commit batch, the capsule must contain exactly two
`(H,I,W,R)=(ABSENT,ABSENT,R,R)` deviations, so only for this batch `D=A`; every other path has
`(H,I,W)=(H,H,H)` with `R` undefined. This deliberately
uses the already content-addressed HEAD commit instead of publishing a
derivative hash of unrelated dirty bytes. When an invocation consumes shipped
baseline authority, it first requires the fixed-path baseline authority marker
and derives the complete finite acceptance-or-marker-reachable path set by
strict parsing rather than directory-name inference. The capsule additionally
carries only the exact raw commit path from current HEAD to the immutable
authority commit plus the authority root's complete tree closure. Capture derives required authority commits from
sealed strict inputs before the original object database is hidden, follows
only each commit's first literal parent, and captures every path commit and
authority tree/blob. Offline verification reconstructs the same unique first-
parent path, the byte-exact leaf manifest, and exact object-union membership
after the original checkout and object database are inaccessible; unrestricted
parent history is not captured. It requires exact mode, full blob OID, and raw
SHA-256 equality for every derived authority path and rejects an extra or
missing leaf in either tracked baseline archive root. Validation-truth promotion uses this same
archive and byte-transfer provenance machinery.

HEAD and authority tree manifests share one closed leaf encoding: recursive
non-directory blobs sorted by unsigned raw path, with each record
`raw_path NUL mode NUL full_blob_oid NUL raw_blob_sha256 NUL`. Tree entries are
not records, gitlinks fail, and symlink blobs hash their raw target bytes. This
framing prevents two offline implementations from choosing different manifest
preimages while claiming the same closure.

All durable evidence follows three layers: scientific payload, public
reproducibility/governance, and private invocation transport. The publisher
constructs the public projection from guarded bytes in memory and scans the
entire proposed tracked tree, archive/Git objects, filenames, encodings, and
document metadata for raw private canaries and their hashes before any write.
Hostname, absolute roots, raw argv/cwd/env, loader/capsule names, descriptors,
inode/mount/namespace/address/load-base facts, PIDs, provider IDs, raw
transcripts/tool output, and arbitrary approval text are never public fields or
hash inputs. Replaying the same public inputs under different roots, hostnames,
and private capsule locations must produce identical public bytes.

Computational environment capture uses an exact ownership partition for every
file-backed loaded module and broker read. Captured project records win only by
exact path/hash identity; an installed distribution wins only through one
verified `Distribution.files`/`locate_file()` entry; an otherwise unowned path
beneath `purelib`/`platlib` fails; and only then may a residual source/bytecode
origin belong to exactly one coalesced `stdlib`/`platstdlib` group or an
extension bind one sealed loaded-mapping record. Equal stdlib roots serialize once,
distribution ownership wins even when its file lies beneath a stdlib root, and
every used distribution retains only its normalized name, exact version,
selected registry-wheel content hash, used logical file records, and exact
module/read triggers.

The same self-sealed static supervisor is the sole installed-root producer. It
creates a fresh empty root directly from fully sealed selected wheel leaves; no
external installer, cache, index, network, prior virtual environment, or
preexisting installed file participates. Its policy-bound memory-safe V2 parser
has closed classic-ZIP local/central, CRC, bounded DEFLATE, folded non-identity
metadata-header, and per-file uniform LF-or-CRLF RECORD-CSV semantics and is bound by the exact supervisor
executable hash. Required identity headers remain unique, unfolded single
physical lines; unrelated headers may use only the explicitly bounded SP/HTAB
continuation subset needed by the selected locked wheels. It
copies only canonical direct regular wheel members byte-for-byte beneath
purelib or platlib. V1 rejects `.data` relocation, generated entry-point
scripts, installed-RECORD rewriting, packaged bytecode, symlinks/special files,
and every collision. This deliberately narrow install model makes a guarded
wheel member, its unchanged RECORD row, and the resulting located entry the
same byte identity; an ambient installer's `../../../bin/...` row is not a V1
input. The private request names one reviewed base-import profile so the
supervisor can provision exactly its artifact set before Python; the preparer
later requires that same row to be the unique Python/platform match.

The private `WheelProvisioningWitnessV2` binds each selected archive, locked
name/version, root role, member, and installed leaf. The public
`base_handoff.provisioning` instead contains the exact normalized-name-sorted
whole-wheel identities required by the selected base-import profile. Therefore
an unread member has no public member row or use trigger, but changing any byte
of a selected wheel still changes the common base through its archive hash. Only
an artifact absent from both the selected profile and actual used closure is
hash-neutral.

Each environment invocation is one supervisor transaction with two sequential,
non-overlapping Python children. Before the first child the supervisor also
constructs one private `ComputationInputInventoryV1` that closes every control-
only, computation-bootstrap, brokered project/data, and external-input leaf.
A fresh no-site control preparer receives the sealed request, platform, both
reviewed registries, that inventory, provisioning witness, lock, selected
wheels, distribution/stdlib inventory, and optional package-initializer leaves.
It alone uses the captured `importlib.metadata.Distribution.files`/
`locate_file()` semantics, constructs the private per-entry index, and records
every raw read in its private ledger. Its first eight reads are exactly request,
OS-release, CPU-info, platform attestation, project-execution registry, base-
runtime-import registry, computation-input inventory, and provisioning witness,
in that order. It then performs only the closed fixed imports and ownership
reads. It emits only typed public base/invocation handoffs plus a private
transfer manifest.

At the preparer's terminal stop the supervisor copies and revalidates the
private index/ledger and public handoffs, kills and reaps the child, closes its
root, descriptors, mappings, and process handles, and proves zero lifetime/
kernel-object overlap. Only then does it launch a fresh no-site computation
child. Raw control leaves, private index/ledger, and preparer memory are absent
from that child. Its private entry index is the exact typed projection of the
predeclared computation inventory plus runtime-manifest leaves and two handoffs;
it cannot grow from a future observed read. Deleting names, GC, zeroization, or
an in-process capability revocation is explicitly not an isolation boundary.
The computation bootstrap is consumed exactly once before its broker-ready
barrier and is bound by startup/source/snapshot records, never by a computation
broker row. Any later open, read, import, reload, or alias of that path or leaf
is fatal.

The typed platform projection intentionally exposes the raw OS-release digest
only as the suffix of `linux-os-release-sha256:<digest>` in `os_build_id`.
CPU-info and attestation-leaf digests remain private; no broader claim that all
raw-source digests are private is made.

The typed base handoff binds the preparer startup, source, complete stdlib/
native closure, platform, public wheel-provisioning identity, and a complete
public runtime-import manifest. The
computation mount contains only synthesized sealed stdlib/distribution trees
described by that manifest, never private installed roots; every directory
child ordering, normalized node-kind/mode/byte-count query, exact one-file
module binding/loader/spec/package path, explicit source/sourceless
`ModuleSpec.cached` plus present module `__cached__`, extension null spec cache
plus absent module `__cached__`, and negative module lookup exposed by the
sealed manifest hook is therefore a public deterministic consequence rather
than a leak from unused inventory. Directory-backed distribution namespaces and
physical-path fallback are forbidden. Exact sealed `os`/`os.path`/`pathlib`
query wrappers expose only normalized public stat/DirEntry/listing values, so
declared fonts/styles/data remain usable without revealing kernel metadata;
their bindings are protected by the same post-base guard. Raw runtime-tree
stat/getdents metadata is denied and no inode/device/uid/gid/nlink/timestamp
canonicality is claimed. A one-way, bounded,
nonblocking supervisor receipt pipe is the sole inherited computation IPC
descriptor/channel. The separate state-bound ptrace/process-memory control ABI
is explicit administrator-TCB mediation over a stopped tracee, not a child-
owned endpoint. The pipe
delivers one sanitized public record for each successful guarded read and each
project execution transition, while the supervisor retains independently
decoded logs. The target can steal only public evidence and thereby force
failure, not query or forge a private row.

Computation broker-read ordinal zero is the base-handoff leaf, before every base
import. After the fixed base list (including `types` and NumPy), a stopped base-
ready barrier uses exact capture/commit control stops. The child first projects
the complete inline base stdlib, module, and broker-prefix preimages; while it
is stopped the supervisor traverses the loader/VM closure, writes exactly one
`BaseReadyClosureTransferV1` into the registered bounded buffer, and accepts a
second stopped commit only if the entire stdlib/module/dependency/mapping/read
closure is unchanged. Only afterward may the invocation handoff and project
source root become reachable. The common base hash binds all of
those complete preimages and the split/startup/receipt/seal/VM/supervisor
policies, not a small core-role subset. Control-only reads do not become used-
distribution triggers. Collection requires each selected digest to match a
wheel row under the sealed bootstrap's exact private TOML parser. The invocation-
specific public projection contains exactly the ordered selected identities
embedded in the complete used-distribution rows. The common base hash binds a
`base_numpy` projection containing NumPy's selected-wheel identity, extension
binary, build capabilities, and CPU feature set but omitting invocation-
derived used-file fields; runtime and full environment hashes bind the complete
NumPy record and its unique used-distribution row. Every environment also
retains the complete computation input-open array inline under dependency
discovery. Its globally contiguous records have exact ordinal/root/role/path/
byte-count/raw-hash fields and closed handoff, source-snapshot, external-input,
distribution, and stdlib ownership variants; repeated opens and interleaving
remain visible. The array count and a common domain-separated digest enter the
runtime, environment, phase-manifest, and enclosing hashes. Its retained
base-ready boundary selects the NumPy/base prefix; a separate prefix
digest enters the common base hash, so base-data dependence cannot hide behind
different later invocation closures. Distribution
triggers point to these global ordinals, permitted stdlib data reads are records
rather than unowned exceptions, and offline verification reconstructs every
source/bundle/used-distribution/stdlib cross-link after the private ledger is
destroyed. Whole-lock and
complete-package-entry hashes, URLs, paths, filenames, receipts, cache
locators, direct/editable/source installs, artifacts absent from both public
closures, and derivative hashes of those private values are excluded. A member
of a profile-selected wheel is not member-serialized merely because it exists,
but its bytes remain indirectly bound by the public whole-wheel identity. V1 fails closed unless every used
non-project distribution has a guarded selected-wheel witness.

After the base commit, profile-authorized project code may first import another
manifest-bound stdlib/distribution module; it may not see an ambient site tree.
Those opens, module origins, native images, and triggers enter only the final/
runtime closure, while the unchanged prospective manifest bytes remain common-
base inputs. Before publication the child freezes a complete terminal
`sys.modules` preimage, including fileless rows, and the supervisor validates it
against the base subset, manifest/read rows, project events, shell/namespace
exceptions, and live mappings. A second capture/commit pair transfers exactly
one `FinalRuntimeClosureTransferV1` containing the final module, mapping, and
dependency triplets. Dependency discovery also retains the complete ordered
logical module-authorization completion array, count, and domain-separated
digest, with each authority index resolving to the exact manifest, reviewed
project-policy, synthetic-shell, or sole namespace row. It is one record per
successfully completed logical module, not a trace of every `sys.modules`
micro-operation. Synthetic shells have their explicit one-shot completions;
the ordinary `scripts` namespace follows the normal no-op-loader success tail.
Both transfer wrappers are private framing; their inline
public arrays are rechecked again at the nonresumable terminal stop.

The profile-pinned CPython 3.12+ evidence lane uses a sealed C-level import-core/
dict watcher as fail-fast instrumentation for ordinary importlib, mapping, and
Python/C import-API transitions. Authorization begins after the finder returns
the exact prospective spec but before `module_from_spec()` or loader
`create_module()`. Source/sourceless/project creation executes no project
opcode. Before `_imp.create_dynamic` begins, the bound broker receipt and
prospective sealed member/mapping authority must already exist; the mediated
loader establishes the actual mapping association before any mapped constructor,
`PyInit_*`, or `Py_mod_create` instruction. The created module is not yet
inserted; multi-phase metadata is then frozen before
insertion and `Py_mod_exec`, while legacy single-phase metadata receives a post-
create consistency freeze. A successful ordinary import admits the stock
`spec._initializing=true`, initial insertion, exec/no-op, success-tail pop/
reinsert, and `_initializing=false` sequence as one logical transaction. V1
additionally requires that the popped/reinserted object is the initially
inserted object; stock CPython would reinsert any replacement then occupying
the slot. The sole public transition is emitted only after the policy-verified
sequence. Failure may
unwind only its own still-authorized object and
makes the invocation nonpublishable. Protected metadata records presence as
well as value, including the absent extension `__cached__` attribute.

This watcher is not a hostile same-process sandbox. The exact reviewed project
source, bootstrap/harness/import core, profile-pinned CPython build, NumPy, and
complete reachable Python/native/runtime closure are explicit TCB whose
identities are hashed into the relevant evidence and review subjects. Denying
`ctypes`, `_ctypes`, `numpy.ctypeslib`, `_testcapi`, and profile-enumerated FFI/
debug helpers remains useful deterministic hygiene, but is not an exhaustive
arbitrary-memory proof. A hostile reviewed build-script sandbox is a V1 non-
goal; adding one requires a separate ADR and a memory-safe native verifier or
other hardened runtime. Exact shipped/manual color and palette bytes, all
43x256 LUT bytes/indices/metadata,
independent oracle replay, process-separated generation/verification, side-by-
side evidence, and sequential adversarial review remain unchanged result
guarantees. The exact CPython profile narrows only evidence publication and does
not raise the ordinary library's Python floor.

Registered authoring entry modules live beneath `dartwork_mpl._colors`, while
ordinary Python dotted import executes both parent package initializers first.
The current public initializers eagerly load broad API, Matplotlib/font, color-
registration, semantic, and discrete dependencies, so pretending that an exact
leaf import bypasses them would contradict the isolation profiles. V1 therefore
uses a separately hash-bound, broker-bound authoring package-shell policy. Only
the verified invocation handoff can select its mode. For shell rows, the
control preparer hash-reads the two real initializer leaves exactly once and
passes only their captured path/hash identities. The fresh computation child
never mounts, reads, compiles, or executes those bodies; it creates two source-
bound nonexecuting synthetic package shells, while the ordinary path finder
locates the exact target beneath them. Through the guarded broker/import/Python
interfaces, a sticky guard rejects reload/refinding,
delete/rebind/remove/reinsert, aliasing, initializer exec, third shells, or
restored attempts. This is the ordinary-transition instrumentation described
above, not a second hostile same-process boundary. Protected metadata is fixed except for CPython's exact
stack-balanced child-import bookkeeping; persistent direct-child attributes
must correspond to successful monitored imports.

A reviewed registry has one closed, counted, hashed row for each of the exact
eleven invocation kinds. Its selected invocation-bound project-execution policy
carries exact namespace, required/optional module, and non-module `data_files`
path/hash arrays; hashes are resolved only from the captured source snapshot.
Those rows and the external bundle also form the private predeclared computation
input inventory, so a future observed read cannot broaden authority. The supervisor and child retain a
strictly well-nested pre-exec/success event stream, and `project_imports` is the
unique success projection reconciled with terminal `sys.modules`, not a final-
snapshot guess. Synthetic shells have zero events/import rows. The sole
ordinary namespace-policy exception is the exact `scripts` namespace parent;
the two shell-mode parents are separately dispatch-owned and terminally
reconciled, not namespace-policy rows. In a normal
process, and for the three registered `scripts.*` evidence rows, no shell is
installed; a real initializer may execute only as an explicit ordinary policy/
event row. Existing public exports, registration, manual palettes/colors,
fonts, and shipped LUT surfaces remain unchanged. Thus the evidence lane does
not redefine the user import contract or silently hide a forbidden execution
that later deletes itself from `sys.modules`.

Native execution is sealed before Python starts and is not reconstructed by
rehashing paths after the operation. V1 publication is Linux-only. The native
supervisor is itself one byte-identical stage-zero/final freestanding static
ELF64-little image with no loader/dependency/constructor/TLS/rseq runtime. It
self-copies to an executable fully sealed memfd, re-execs those bytes from an
empty environment, stays nondumpable under the explicit initial-namespace
administrator TCB, and admits no governed signal, ptrace, process-memory,
pidfd, shared-alias, or output-mutation route. Before `clone3` it proves one
thread, no prior seccomp/USER_NOTIF listener, shared or mutable-file mapping,
rseq, asynchronous/device/IPC state, unexpected descriptor, or executable
pseudo range other than the admitted vDSO. The supervisor copies the process
executable, `PT_INTERP` loader, candidate DSOs/
extensions, their closed dependencies, and every child-readable runtime,
source, and input leaf to fully inode-sealed memfds in role-specific private
mount roots. Each of the two children is created directly with distinct private
user, IPC, mount, and network namespaces and a non-caller credential mapped to
an exclusively leased host
UID/GID from a supervisor-reserved range unavailable to ordinary users and
container managers. Before each sole lifecycle exec, the bootstrap makes propagation
private, pivots to the prepared root, changes cwd, recursively detaches the old
root, and proves exact root/cwd/mountinfo before dropping credentials. It
closes every outside descriptor, mount, IPC, network, device, and mutable-input
route. The preparer receives only immutable EOF stdin and write-only sinks; the
computation additionally receives the exact read-only broker-receipt fd whose
peer is supervisor-only.
Outside the explicit kernel/initial-namespace-administrator TCB, only the bound
supervisor retains ptrace authority.

An architecture-closed, supervisor-hash-bound seccomp filter has an exact allow
set and default-kill action. With the exact `PTRACE_O_TRACESECCOMP`,
`PTRACE_O_TRACESYSGOOD`, `PTRACE_O_TRACEEXEC`, and `PTRACE_O_EXITKILL` option
set, it identifies every admitted mapping/control/`brk` syscall exit and
closes all
shared mappings, System V shm, sockets/descriptor transfer, userfaultfd,
io_uring/AIO, cross-process memory/pidfd routes, and device/DMA acquisition.
Together with the absent `/dev/shm` mount and inherited descriptors, this also
closes POSIX shm reachability. Anonymous memory must be private and
non-executable; every file-backed mapping must use a retained fully sealed
memfd. `brk` is limited to a tracked anonymous-private non-executable heap;
`rseq` receives fixed `ENOSYS` and is proven unregistered; x86-64 requires
actual `vsyscall=none` behavior rather than inventing a second fileless image.
The credential boundary
exists from child creation and survives exec's dumpability reset. glibc IFUNC,
preinit/init arrays, and constructors run under the already active complete
boundary; only afterward, but still before executable `main` and Python
interpreter entry, a sealed `la_preinit` set/get-zero barrier restores and
verifies non-dumpability. Calling it a pre-constructor or first-application-
instruction barrier would be false.

Each child environment is constructed from empty. A public behavior hash binds
the fixed thread controls, integer Python hash seed, allocator, C locale, UTC,
Python behavior variables, and exact `glibc.pthread.rseq=0` tunable; the sole
private path-valued entry is `LD_AUDIT`, bound to the retained sealed
`startup-audit` role. Environment sealing is not treated as a Python-startup
barrier. V1 also binds two closed, path-neutral CPython startup records containing
the exact `-S -s -B -X utf8` argv policy, one sealed bootstrap role/hash, an
empty sealed cwd role, flags, the complete pre-broker Python startup input and
module closures, and each lifecycle's exact path stages, finder, hook, and
importer-cache role vectors and hashes. Each bootstrap has no
recipe operand and imports only already-cached built-in `sys` before installing
the deny-by-default broker; every base import and operation import occurs
afterward. Automatic `site`, `.pth`, customizers, cwd, ambient project/site, or
unbound script-directory insertion and unrecorded startup reads fail. The sole
script-derived path exception is the sealed, role-bound
bootstrap directory: it is the first entry in that lifecycle's exact initial path
vector, contains only the bound bootstrap leaf, and is removed at the
broker-ready transition before any base or operation import. `-I` and `-E` are
forbidden because they would ignore the authoritative from-empty Python
behavior variables; empty `PYTHONPATH` and `PYTHONNOUSERSITE=1` remain defense
in depth, not substitutes for the no-site startup contract.
The path-neutral common base binds the control-preparer closure, process split,
typed base handoff/runtime tree, computation startup, receipt policy, and
complete stopped base-ready closure. The full runtime binds the invocation
handoff, package dispatch, project execution policy/events, and complete
computation read stream. The supervisor's exact capability array contains the
closed advertised mechanism-capability IDs, so an implementation cannot add a raw-control role, receipt channel,
synthetic shell, or event mechanism under an old capability claim. Their exact
role, order, schema, source-subset, and rejection contracts live in the
implementation spec.
Unknown inherited variables, any additional `LD_*`, or alternate locale,
allocator, Python, or NumPy variables fail before Python. Every captured ELF
is also rejected if it contains `DT_AUDIT` or `DT_DEPAUDIT`, so the role-bound
environment leaf is the only audit source. The audit leaf and its private
helpers are freestanding and base-identity-disjoint; a normal libc-linked
auditor that maps the base libc identity again at another address is not an
admitted V1 artifact. The same-address loader proxy is the sole coalesced
exception. The lane is single-threaded and its
external-writer contract is alias-complete:
no non-TCB principal can retain or acquire a shared backing object, mutable file
alias, descriptor/socket, process handle, asynchronous writer, or device map
through terminal handoff. The supervisor retains an append-only private native
ledger through that handoff; a transient direct map/unmap, reachable writer,
external write, event gap, unmatched loader correlation, or policy teardown
makes the private run non-publishable even when before/final snapshots match.
The handoff is one exact self-`SIGSTOP` from the sealed harness only after all
profile-authorized ordinary outputs and the primary are closed and a private
terminal manifest has been written last. The manifest enumerates the exact
relative path, byte count, and raw hash of the complete set but is not embedded
in the primary or environment, avoiding a primary↔manifest hash cycle. The
supervisor never resumes user space: it kills/reaps, copies every member to
fresh fully sealed storage, rehashes it, and proves exact schema-profile and
primary-reference equality. A static byte-only publisher installs subordinate
leaves first and the primary completion marker last. A partial subordinate set
is non-authoritative; a surviving primary with a missing, differing, or extra
member is fatal.
Darwin and every other platform fail native preflight before Python and emit no
environment, candidate, provenance, partial output, or placeholder record.
Endpoint Security plus Hardened Runtime does not close anonymous/System V/POSIX
shared memory, Mach memory entries, XPC shared memory, inherited IPC, and
asynchronous device/I/O routes; minimal App Sandbox and deprecated custom
Seatbelt profiles do not supply a supported deny-all boundary.

`LD_AUDIT` also changes the completeness proof for loaded images. glibc loads
the auditor in a separate dynamic-link namespace, while `dl_iterate_phdr`
reports only the namespace of its caller; the Python-side callback stream is
therefore a base-namespace cross-check, not a whole-process inventory. At the
stopped `la_preinit`, base-ready capture/commit, operation-closure capture/
commit, and pre-exit barriers, the supervisor
instead follows the exact sealed glibc's version-2 `r_debug_extended` chain from
the process executable's runtime `DT_DEBUG`; a copy-relocated `_r_debug` is
forbidden and never a fallback. This pins the glibc-2.35-or-later ABI and exact
preflighted loader behavior. Both node addresses must belong to the loader's
writable mapping, both `r_ldbase` values equal `AT_BASE`, and both equal
`r_brk` values fall in its executable range. V1 admits exactly the base node
and one audit node, both `RT_CONSISTENT`; the latter must contain the sealed
`startup-audit` leaf rather than being trusted by ordinal alone. It walks every
`link_map` in both. The second node's `r_next` must be null: because glibc
retains empty namespace nodes, merely counting two active `r_map` values would
not exclude a stale or hidden third namespace.
Each stopped walk snapshots and rereads the headers and link topology without
intervening tracee execution; any change or non-consistent state fails.
The merged union must reconcile one-to-one with sealed leaves, complete VM
regions, the native event ledger, and the base callback stream. The audit leaf
receives `startup-audit`; each remaining audit-only image receives a canonical
`audit-transitive/<ordinal>` role before base-only
`native-transitive/<ordinal>` assignment. A shared physical image is coalesced
only at the same base and segment layout; an extra namespace, auditor-private
`DT_NEEDED` omission, orphan map/callback, or same identity at distinct bases
is fatal. The audit closure is stable from `la_preinit` through handoff.

The complete physical capsule, path map, raw VM ledger, audit tokens,
subordinate IDs, and user-namespace/allocation-lease facts remain private
because they may include unused candidates and machine-local state; the
public environment contains only the exact path-neutral mapping records
actually used by a fully reconciled loader closure. Each record binds its
content identity, ELF header/program headers, and normalized segments.
The base hash binds the supervisor/seal/VM policy plus executable, loader, and
arithmetic core mappings; the runtime hash binds the full invocation mapping
set.

Linux permits exactly one fileless transitive image: the
`AT_SYSINFO_EHDR` vDSO, identified without its loader name and hashed from its
ASLR-neutral complete mapped ELF image. It can carry no core role. Every
ordinary Linux image comes from a sealed file-content leaf; a caller-selectable
GNU build ID is metadata, not identity or fallback. Package-name and
directory-prefix inference are not authority.

Python math origins are a closed built-in/frozen/stdlib/native union:
stdlib uses the four-field path/hash
projection of exactly one closure record whose complete aliases include
`math`; native privately retains a no-load handle and binds the `PyInit_math`
address to exactly one frozen loaded image before publishing only that image's
sealed-file identity. No path string is compared with a public identity, and no
redundant `math_module_sha256` exists. Core
references are the literal roles `process-executable`, `process-loader`,
`python-runtime`, `math-provider`, `numpy-multiarray`, and native-only
`math-module`.

ADR 0001 remains a historical accepted design record. This ADR is standalone:
it does not use ADR 0001 as an implementation baseline, review input, or
authority record. Its more complete ordered bootstrap supersedes only ADR
0001's overlapping migration requirements and establishes
the operative compatibility/new-family separation and scope of the
compatibility-only helper.

## Trade-off

**Advantages:**

- published colors remain exactly stable;
- new-family defaults express actual OKLab/OKLCH coordinates without inherited
  CIELAB or compatibility heuristics;
- interior fixed-Y authoring has a defensible global mathematical objective
  for its narrowly declared modeled-Y-fiber topology, while endpoint semantics
  and all perceptual/physical non-claims are explicit;
- a missing manifest cannot silently mutate output;
- selection and downstream pair-specific contrast/perceptual diagnostics
  remain architecturally separate; and
- once accepted, new-family output remains reproducible after policy changes.

**Costs and concessions:**

- two explicitly different internal lanes remain instead of one superficially
  uniform implementation;
- baseline preinstall, create-only promotion, post-promotion authority
  finalization, compatibility migration, and authoring must pause at separate
  integration boundaries so each later phase
  starts from an exact HEAD containing the accepted prior phase; they cannot be
  collapsed into one convenient dirty-worktree migration;
- the generic boundary needs careful polynomial root isolation and an
  independently implemented exact-rational Cartesian cubic oracle;
- interior direct fixed-`L` authoring needs a second independently transcribed
  face-root oracle plus algebraic cross-bracket equivalence proofs, endpoint
  policies need a scalar verifier, and strict
  native-runtime provenance and complete inline arithmetic-trace arrays add
  offline tooling and public-evidence size;
- exact maximin selection can be exponential and therefore stays offline with
  a deterministic node budget;
- new-family admission requires a human-reviewed policy because no universal
  CVD/CIEDE2000 threshold exists;
- each discrete or admission policy characterization requires a separate
  captured numeric-verification invocation and durable review binding before
  the nonnumeric registry promotion, adding one environment/trace evidence
  object and another full replay;
- reproducible evidence requires an immutable captured source/import snapshot,
  semantic Git/index/blob manifests, content-addressed lifecycle/review
  bundles, public prompt/scope/result logs, complete per-invocation arithmetic
  trace preimages, complete globally ordered computation broker-read preimages,
  post-operation invocation-specific loaded closures, used-distribution
  manifests, a private-to-public publication firewall, and policy preselection
  approval, which substantially increases offline tooling and evidence-storage
  cost;
- the evidence lane must maintain two nonexecuting synthetic parent packages,
  a sticky shell guard, a reviewed per-profile execution policy, a supervisor-
  retained well-nested event stream, namespace exception, and terminal module
  reconciliation, while continuously proving ordinary imports retain every
  existing side effect;
- publishable V1 environments require the self-sealed supervisor to provision a
  fresh root directly from strict direct-member wheels and retain a private
  member-to-leaf witness. Arbitrary existing virtual environments,
  `.data`/generated-script/RECORD-rewrite semantics, symlinks, and sdist/direct/
  editable/path/Git installs fail closed. Parsing hostile ZIP/DEFLATE/metadata
  in the initial-namespace supervisor deliberately enlarges the highest-
  privilege TCB, so the admitted V2 component is memory-safe, quota-bounded,
  executable-identity-bound, fuzzed, accepts only its bounded folded-header
  subset, positive-goldens both admitted NumPy architectures, and rejects every
  unsupported encoding;
  this cost is accepted rather than silently trusting an external installer.
  Ordinary automatic virtualenv/site initialization is also unavailable: a
  sealed no-site bootstrap must construct and verify every operational import-
  path role;
- each native invocation launches and fully tears down a separate no-site
  control preparer before computation, reconciles a private transfer manifest,
  predeclares the complete computation input inventory, performs eight fixed
  singleton control reads, synthesizes a public runtime tree, carries two typed
  handoffs, retains a bounded receipt/event channel, and performs base-ready and
  final capture/commit transfer pairs. This adds a
  second Python startup/stdlib/native closure, another namespace/credential,
  two bounded supervisor-to-child memory writes, more copy/reap barriers, and a
  deliberately narrower historical claim after private ledgers are destroyed;
- reconciling post-base imports requires a complete final module preimage,
  retained ordered logical-authorization completion preimage, exact stock
  create/insert/exec/success-tail behavior, manifest ModuleSpec/loader/cache/
  package semantics plus protected metadata presence/value, and a CPython-3.12+
  dict-watcher/import-core diagnostic ABI. Every executing project-source,
  CPython, NumPy, and reachable runtime/native byte is consequently reviewed TCB;
  denied FFI/debug modules are hygiene rather than a hostile same-process
  boundary. This narrows supported evidence-publisher runtimes and increases
  source/closure review, custom harness, transfer, offline-verifier, and
  adversarial-test cost while leaving ordinary dartwork-mpl runtime support
  unchanged;
- publishable native provenance requires a Linux supervisor before Python
  starts. It must self-seal and protect its own static executable, prove a
  clean one-thread/no-prior-seccomp pre-clone state, seal every executable and
  readable input leaf, construct both child environments from empty, create
  both sequential children directly in distinct private user/IPC/mount/network
  namespaces with
  exclusively leased subordinate UID/GID, pivot and detach the old root, close
  inherited descriptors, mutable mounts, IPC/network, shared mappings,
  asynchronous writer APIs, and devices, mediate `brk`, disable and verify
  rseq, reject x86-64 without `vsyscall=none`, run a deliberately
  single-threaded exact seccomp/ptrace state machine, and verify a post-
  constructor/pre-main dumpability barrier, then kill/reap, copy, rehash, fully
  seal, and retain the complete terminal primary-plus-subordinate set until a
  primary-last publisher has crossed every file and directory durability
  barrier. This is
  materially more expensive than ordinary virtual-environment execution;
- Darwin and every non-Linux platform are unavailable for V1 publication. A
  future positive Darwin lane requires a separately reviewed supported kernel
  or VM/container boundary, coordinated schema/hash-domain changes, and the
  full shared-memory/IPC/device/async-I/O adversarial matrix rather than more
  entitlements around the current process model;
- each standalone scientific artifact carrying generic authoring/oracle
  evidence stores the canonical 4,121-byte scalar-kernel constants binding,
  and changing that binding intentionally cascades through every outer
  scientific, review, acceptance, and archive hash;
- canonical uncompressed DEFLATE stored blocks make snapshot archives larger
  than compressor-tuned loose objects, and exact distribution-file ownership
  deliberately fails on incomplete or conflicting installed metadata rather
  than guessing from a package directory;
- the baseline authority marker and durable policy/fixed-Y/truth promotion
  records duplicate approval and complete historical input closures, increasing
  tracked provenance size in exchange for post-worktree verification;
- validation-oracle V1 needs its own one-time durable bootstrap review/archive,
  maintainer acceptance, and explicit downstream acceptance cross-links;
- durable archive publication rejects unrelated local changes and generally
  requires a dedicated clean worktree; comments and nonoperational
  remote/branch metadata are intentionally absent from fingerprint identity;
  durable no-replace publication additionally costs same-filesystem private
  staging plus extra file/directory synchronizations and is unavailable on a
  filesystem that cannot provide the required atomic and persistence semantics;
  and
- documentation must keep actual OKLab `L`, `NeutralTone`, and modeled relative
  Y visibly distinct.

## Alternatives

| Alternative | Why it was not selected |
|---|---|
| Keep only the shipped compatibility implementation | Safe for existing output but leaves the new-family boundary and selector requirements selected by this ADR incomplete. |
| Replace every shipped call with the corrected fixed-Y solver | Conceptually cleaner naming, but any output difference would violate the exact catalog contract this ADR first establishes; quantitative diagnostics belong to a source-bound implementation artifact, not an unsupported ADR claim. |
| Migrate the whole catalog to direct OKLCH `L` | Removes the Y solver, but changing the catalog's coordinate contract is an incompatible aesthetic redesign that requires its own source-bound comparison and approval. |
| Treat an untracked earlier spec, ADR, prototype implementation, self-hashed compatibility JSON, or the pre-marker pair as baseline authority | It is absent from the normative predecessor or does not bind the completed promotion review, and can make implementation plus golden agree circularly. Only independent extraction, preinstall A/B, separate create-only promotion and promotion A/B, the tracked post-promotion review closure and authority marker, and a later exact HEAD containing every marker-reachable leaf establish authority. |
| Use nested bisection for generic fixed-Y maximum | Simple, but fixed-`C,h` Y is cubic in `L` and outer feasibility need not be monotone; a maximum claim cannot rest on those unstated assumptions. |
| Re-run CIEDE2000 selection at runtime | Re-couples construction and validation, makes output algorithm-version-dependent, and masks missing SSOT data. |
| Use equal-arc or greedy discrete sampling | Fast and deterministic, but does not solve the maximin separation objective selected by this ADR. It may be offered later as a separately named preview, not a fallback. |
| Reuse historical common/tritan 10/8 floors for every new family | Those were Octave search criteria, not universal visibility or accessibility thresholds. |
| Trust a self-hashed create-only truth file or ignored A/B reports | Neither independently authorizes the first bytes; a self-consistent first writer could rewrite implementation, vectors, results, and every current hash together. |
| Re-emit production root intervals from the direct oracle | It would turn the independent oracle into a producer-certificate copier. Algebraic identity plus exact root-equivalence proof permits genuinely independent valid brackets. |
| Key snapshot archives by the reviewed snapshot and use a normal zlib compressor | A single snapshot could admit several byte-distinct valid archives, making the path non-content-addressed and compressor-version-dependent. |
| Write final leaves directly with `O_CREAT|O_EXCL`, rely on file-only `fsync`, or use overwrite-capable rename | Power loss can expose a torn leaf or lose a leaf/parent dirent, and overwrite rename violates immutable no-replace authority. Fsynced staging, atomic no-replace installation, and bottom-up directory barriers are required. |
| Publish a whole content-addressed directory and treat its existence as completion | Portable whole-directory replacement is not the authority primitive, and a surviving directory may still lack durable children. Blobs precede a separately durable manifest marker. |
| Hash the raw whole lock or a complete package entry | It binds unused packages and unselected artifacts, leaks equality for private URL/path metadata, and changes public identity for inputs the invocation never used. |
| Trust an external installer or preexisting virtual environment | Installer versions may relocate `.data`, generate scripts, rewrite RECORD, preserve symlinks, or select different compatible wheels. V1 instead has one fresh direct-member install grammar, whole-wheel identity, and member witness. |
| Support wheel `.data` relocation and generated entry points in V1 | It would require exact scheme routing, script transformation, generated-file identity, and deterministic installed-RECORD rewriting. V1 rejects that larger contract; only direct regular wheel members can be owned. |
| Run an untrusted wheel parser and accept its output manifest | Sandboxing protects the host but does not prove output bytes came from the guarded archive; independent verification would need the same semantic parser again. V1 accepts the cost of one memory-safe, bounded, self-sealed supervisor component and makes its parser executable identity and malformed-input tests part of the TCB. |
| Let computation or another Python helper read the sealed request/platform leaves | Bytes selecting the operation/base would escape the closed control history. The supervisor TCB necessarily constructs/validates them, but only the doomed preparer opens them in Python and records that history; computation receives typed, hash-bound handoffs after reap. |
| Read control data, delete buffers/revoke authority, and then import NumPy in the same process | Frames, allocator arenas, GC, ctypes, and native code can still observe residual data. A real kill/reap boundary and fresh computation exec are required. |
| Mount private installed stdlib/distribution trees while hiding only the index | Raw listings/stat and negative lookup outcomes still expose unused inventory and can select imports without a successful read record. Computation uses only the public manifest tree through its sealed normalized path hook; raw runtime-tree stat/getdents is denied. |
| Retain distribution trigger ordinals or a broker-read digest without the complete computation records | Offline verification cannot recover omitted handoff/stdlib/data reads, repetition, or interleaving. One inline five-owner stream is the ordinal preimage for phase manifests, triggers, and environment hashes. |
| Sanitize a whole package entry | It still binds unselected artifacts and cannot establish which compatible artifact the installer actually supplied. |
| Infer the installed wheel from compatibility tags | Multiple compatible/build wheels and installer-version ranking make tag inference evidence of possibility, not actual selection. A guarded archive from the sealed direct-member provisioning transaction is the authority. |
| Archive raw installer receipts, locators, or wheel bytes | Receipts and locators carry private paths/URLs, while archiving every third-party wheel is unnecessarily large. The selected content digest plus used-file records is the smallest public identity. |
| Rehash each native pathname after the operation | Replacement can make that path name bytes other than those mapped, and same-inode rewriting can alter the file after code already executed. Sealing and mapping association must precede authoring. |
| Treat a base-process `dl_iterate_phdr` pass as the complete image set under `LD_AUDIT` | glibc selects the caller's namespace, while each audit module is loaded into a separate namespace. The stopped version-2 debugger rendezvous must enumerate and merge both chains, including auditor-private dependencies. |
| Trust only loader callbacks plus before/after VM snapshots | Anonymous RW memory can be changed to RX, executed, and unmapped between both snapshots without a loader callback. Continuous kernel mediation and an append-only private event ledger are required for a publishable run. |
| Set Linux `PR_SET_DUMPABLE=0` only before exec | Ordinary nonprivileged exec sets dumpability back to 1. A fresh subordinate kernel credential isolates that reset window, and the sealed `la_preinit` barrier restores and verifies zero after constructors but before `main`/Python entry. |
| Hash the supervisor binary but inherit its launcher state | A dynamic or mutable supervisor, outer USER_NOTIF filter, inherited shared map, or peer-writable supervisor remains an authority over the child and final output. The static self-sealed supervisor and clean pre-clone baseline are part of the policy. |
| Sanitize selected inherited environment variables | Omitted loader, glibc, allocator, locale, Python, or hash-seed variables still change execution, and `PYTHONHASHSEED=random` is not a reproducible value. V1 builds one exact environment from empty and role-binds its sole private path. |
| Treat empty `PYTHONPATH` or `PYTHONNOUSERSITE=1` as a startup barrier | Neither disables automatic `site`, executable `.pth` processing, customizers, nor every initial path insertion. The exact no-site argv/bootstrap/input/module/path-stage record and broker-first order are required. |
| Import a registered `dartwork_mpl._colors.*` leaf and assume its parents are inert, or use unbound synthetic packages | Python executes the eager initializers, while an unbound bypass evades source identity. The preparer binds both initializer hashes; computation uses guarded nonexecuting shells and leaves ordinary imports unchanged. |
| Infer project execution or fileless imports only from final `sys.modules` | A module can execute and later disappear. The reviewed execution policy plus supervisor-retained pre/success events records project execution, while the complete final preimage and C-level instrumentation detect and reconcile ordinary import-API transient state. Neither is advertised as arbitrary-memory history. |
| Treat the same-process watcher or a child-writable sticky flag as a hostile-code boundary | CPython and NumPy expose same-process native memory surfaces, so code already executing inside that process could bypass or restore either mechanism without a syscall. V1 instead makes every exact executing project/runtime/native byte reviewed, hash-bound TCB and uses the watcher only as fail-fast ordinary-transition instrumentation. |
| Move color computation into a separate memory-safe native verifier now | That could establish a future hostile-script boundary, but it would add another numeric implementation and equivalence burden to a task whose result integrity is already enforced by immutable shipped goldens, independent oracles, process separation, and sequential review. Such a boundary requires its own ADR rather than an implicit watcher claim. |
| Keep the evidence publisher on stock CPython 3.10/3.11 | Those runtimes do not supply the exact dict-watcher/import-core ABI and stock import sequence pinned for deterministic diagnostics and replay. V1 evidence uses an exact CPython 3.12+ profile; this is a reproducibility requirement, not a security-floor claim, and ordinary package support remains broader. |
| Declare a closed arithmetic operation set without closing every row's arity and vector grammar | Variadic `hypot`, vector `dist`/`fsum`, power exponent semantics, and scalar NumPy cbrt would remain verifier-dependent. One normative 14-row table and context-specific fsum lengths drive replay and rejection tests. |
| Serialize infinity as the second generic `nextafter` operand or leave CIEDE2000 `exp`/degree conversion outside the trace | That contradicts the finite-only trace grammar or leaves authoritative libm output unowned. Direction-specific operation IDs keep records finite, and explicit degree/exp adapters retain the missing calls. |
| Use `chroot` or a new mount namespace without `pivot_root` | A copied cwd, directory descriptor, or old-root mount can retain host reachability. The old root is detached and root/cwd/mountinfo are checked before exec. |
| Treat rseq, vsyscall, or `brk` as harmless runtime details | rseq lets the kernel rewrite registered TLS, x86 vsyscall is an extra executable pseudo route, and untraced `brk` changes the VM map. V1 disables/verifies rseq, requires vsyscall-none behavior, and mediates heap-break changes. |
| Use only a read-only bind or advisory lock | A different mount or uncooperative writer can still mutate the inode. Every child-readable Linux input leaf is instead copied to a fully sealed memfd. |
| Use fs-verity without a retained isolated name tree | It protects content reads but permits rename/delete/link and does not constrain later loader name resolution. It can be an implementation ingredient, not the complete proof. |
| Hash the full physical native capsule | It binds unused late-load candidates, breaks unused-artifact neutrality, and can expose a derivative of private loader layout. Only actually loaded path-neutral mapping records are public. |
| Treat Hardened Runtime plus task-right authorization as a Darwin writer boundary | Those controls address executable code and foreign task rights, not anonymous/System V/POSIX shared memory, Mach memory entries, XPC shared memory, inherited IPC handles, or asynchronous device/I/O completion. |
| Add minimal App Sandbox entitlements and keep the positive Darwin lane | App Sandbox is necessary for a future attempt but does not expose a supported deny-all contract for every baseline IPC, shared-memory, device, and inherited-handle route. |
| Apply a custom Seatbelt “pure computation” profile | The public custom-profile API is deprecated, its pure-computation profile is unsupported, and it cannot be the normative boundary for a new publication format. |
| Admit a Darwin OS build after a finite probe suite | Passing sampled probes shows only that those routes failed on that host; it is not an exhaustive supported denial authority for unenumerated kernel, IPC, or driver channels. |
| Check only executable maps and final bytes | A peer can mutate a read-only `MAP_SHARED` view, a mutable-file `MAP_PRIVATE` source, shared memory, or an async target without creating executable pages. Every writer route must be closed continuously; an unchanged final snapshot proves no such closure. |
| Copy only the primary completion and reopen referenced output paths later | A subordinate may be replaced between close and reopen, and the primary then describes bytes that never crossed one immutable handoff. The private terminal manifest and supervisor seal the exact complete set before publication. |
| Retain only arithmetic-trace count and digest | The call-order preimage disappears with private runtime state, so an offline verifier can check only self-consistency asserted by the producer. Every authoritative environment retains and strict-parses the complete record array. |
| Let the nonnumeric policy-registry archive promoter rerun LUT/OKLab/selector/oracle arithmetic | That silently gives a byte-transfer transition an uncaptured floating-point runtime, no environment owner, and no arithmetic trace. A separate environment-v3 verifier must produce reviewed evidence before the promoter copies accepted bytes. |
| Give each oracle an opaque or duplicated constants hash | An opaque hash lacks a canonical preimage; three copied records can drift. One closed archived record with a golden digest is shared as evidence while each implementation retains independent private literals. |
| Reuse a source-file hash or validation-oracle constants record for authoring constants | A source hash is provenance rather than the semantic numeric preimage, and validation constants contain a different model and unrelated values. |
| Treat the existing WCAG helper or its source hash as a V1 authoring/admission policy | This ADR defines no closed coefficient, role, threshold, result, or hash contract, and adding the helper to admission would contradict the authoring/accessibility boundary. A future replayable pair-specific policy needs a separate design. |
| Archive raw local Git config or only its hash | Raw bytes can publish credentials/comments permanently; a hash still leaks equality and can be a dictionary oracle while preventing complete leaf verification. Synthetic operational config captures only behavior used by the registered commands. |
| Archive the live Git index or only its hash | Index stat data, extensions, split-index links, and shared-index files expose machine state and give semantically equal trees different identities. A canonical zero-stat, extension-free index preserves the stage-0 meaning needed offline. |
| Authorize non-HEAD bytes by declared path alone | A staged private blob and safe reviewed worktree file can share one path. Exact HEAD/index/worktree/reviewed state implications bind the reviewed bytes and mode instead. |
| Run the two-document review in the existing dirty feature worktree and rely on its stable fingerprint | Stability detects later mutation but does not make unrelated non-HEAD paths eligible under the exact-state rule. A clean isolated exact-HEAD capsule carries only the two reviewed states and does not publish hashes of unrelated bytes. |
| Archive raw invocation/reviewer transcripts and redact paths | Host, loader, provider, and absolute-path material is open-ended; hashes still leak equality and regex redaction is not a proof. Typed public projection plus a private-data publication firewall supports only the narrower durable claim. |
| Archive the full dirty/untracked worktree | It preserves a larger historical preimage by publishing unrelated private bytes. Durable evidence is limited to already-public HEAD plus explicitly reviewed source bytes instead. |
| Put full snapshots in a protected external store | It could retain arbitrary private preimages, but loses repository-self-contained offline verification and introduces storage, key, retention, and availability authority. |
| Classify imports by the first matching sysconfig or package-directory prefix | `stdlib`, `platstdlib`, `purelib`, and `platlib` can overlap, and installed distributions commonly live beneath one of those roots; first-prefix ownership silently misclassifies real environments. |

## Consequences

- Compatibility migration translates exact predecessor behavior into the three
  new shipped-compatibility entry points above; no mapped-Y body or named tone
  policy is claimed to pre-exist in the normative predecessor.
- No ambiguous shared boolean renderer may survive compatibility acceptance.
  Separate shipped-locked,
  shipped-unlocked-diagnostic, direct-authoring, and fixed-Y-authoring entry
  points make coordinate meaning structural.
- Generic direct-OKLCH and fixed-relative-Y authoring use separate typed entry
  points and unambiguous coordinate field names.
- A fixed-Y recipe carries a closed modeled-Y-fiber topology contract and its
  comparison proves bit-identical requested targets and bounded modeled-Y
  residuals over dense/final samples. The direct counterfactual remains a
  diagnostic, not a perceptual or admission threshold.
- For interior targets, a private projective solver returns chroma, actual `L`,
  raw RGB, modeled-Y residual, ordered active limiting faces including every
  corner face, and a global lower/upper boundary certificate. Requested-equality witness
  shortfall and constrained gamut-reduction certificates use different field
  names; intended chroma reduction is never labeled numerical error.
- Positive modeled-Y witnesses must satisfy simultaneous absolute and relative
  residual guards and preserve endpoint identity; a tiny positive target may
  fail closed but is never silently reclassified as black.
- Compatibility migration defines each binary64 `tone_seed` through the exact
  legacy transform above; characterization retains those resulting bits,
  computes target Y with the exact left-associated binary64 expression
  `(tone_seed * tone_seed) * tone_seed`, and passes the same seed as
  `NeutralTone`.
  It never reconstructs the argument through an unspecified cube root.
- The complete 58-row tone mapping plan gives each operational `Tone` one
  deterministic source owner and golden plan hash, preventing equal-valued
  literals or undocumented derived endpoints from being chosen by proximity.
- Direct interior witnesses preserve the requested `L` bits and may not collapse
  to black/white or claim positive chroma with a bitwise neutral scalar output.
  Their achieved modeled Y is recomputed and bit-bound through the canonical
  scalar association rather than accepted as a free evidence field.
  An analytically feasible request that fails a scalar postcondition fails
  closed; only an analytically infeasible request may be labeled constrained
  reduction.
- Projective and direct oracle PASS records carry a closed scalar-witness
  recomputation from the independently certified coordinate. They bit-compare
  the independently derived neutral-reference `L`, direction-scaled `a,b`,
  raw/encoded/neutral channels, modeled Y, and the applicable residual and
  reject a base-runtime mismatch. Production witness values cannot be numeric
  inputs to oracle recomputation; they are read only afterward for bit
  comparison. Both production witness variants therefore serialize
  `oklab_ab`, including an operation-derived negative-zero sign at `C=0` when
  required. Direct scalar replay occurs at the certified conservative
  binary64 lower witness `Plo`, not at the generally irrational exact maximum.
- Existing WCAG luminance/contrast helpers remain pair-specific public/
  validation utilities outside this extension. V1 adds no WCAG policy/result
  domain; those helpers cannot choose authoring coordinates, gamut, selector
  candidates, validation-oracle inputs, or admission, and no single color is
  labeled generally accessible.
- Black/white direct and fixed-Y endpoint records carry scalar-policy evidence
  and are never passed off as exact-rational polynomial certificates.
- Analytic candidates are ordered before binary64 witness rounding, proven
  coincident roots merge with complete source provenance and the complete
  ordered role union, and every result,
  oracle, comparison, and sequential-review envelope has a closed schema.
- Direction construction is versioned as hue normalization followed by one
  `math.radians` call and cached cosine/sine; production, both interior oracles,
  the proof checker, and endpoint verifier independently recompute and
  bit-compare that sequence. Analytic results carry the complete exact-rational
  coefficient object as well as its digest; checkers compare reconstructed
  fields before comparing hashes.
- Fixed-Y characterization and per-family oracle-results artifacts each embed
  one closed scalar-kernel constants record with exactly 49 binary64 leaves.
  Its canonical JSON is
  exactly 4,121 bytes and its V1 digest is
  `3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`;
  endpoint, projective-checker, Cartesian-oracle, direct-oracle, generation,
  rendering, and discrete-decoding policy hashes all resolve
  to that binding. Each implementation reconstructs private literals before
  computation, and archived verification checks the record, golden digest, and
  complete outer-hash cascade without using candidate constants as input.
- Direct-oracle acceptance proves exact-rational containment between its
  exhaustive maximum interval and production's directed binary64 bounds and
  independently reconstructs the aggregate production coefficient record and
  exact winning source-identity/face cluster before publishing a recomputed
  PASS verdict. Production and oracle retain separate rational brackets; exact
  Sturm ordinal/intersection checks and square-free GCD common-root proof—not
  byte-equal intervals—establish equivalence, and production brackets cannot
  steer oracle isolation or maximum selection.
- Direct-oracle components serialize one canonical topology. Every exact merged
  boundary carries the complete duplicate-free canonical union of all face and
  endpoint source identities, and `m` boundaries yield exactly `2*m-1`
  alternating point/open components with byte-identical shared-boundary
  tuples. Every point, including coincident rational `C=0` and requested-`C`
  endpoints, has a null interior anchor and is classified by exact algebraic
  face-sign proof at that root; every open interval has one strict rational
  interior anchor and is classified only at that anchor. Proven-distinct
  algebraic roots remain separate
  even when binary64 rounds them alike, so neither source unions nor cells can
  acquire alternative hashes for the same topology.
- Scalar-parity root samples are identified by production result, proof,
  cluster ordinal, certified interval, sources, and equality proof. Rounded
  binary64 `u` values are sampling representatives and never merge proven-
  distinct algebraic roots.
- A versioned authoring generator and strict proposal/promotion/frozen schemas
  make every new 256-entry LUT reproducible and prevent runtime derivation.
- A private offline selector proposes indices from final quantized LUT bytes;
  after compatibility migration runtime begins replaying accepted SSOT indices
  only and a missing row fails.
- Admission policy and oracle results become frozen provenance for every new
  family.
- Policy identifiers are accepted only through tracked immutable approval
  entries referenced by one guarded-compare-then-replace registry index; a
  separately sealed preselection envelope proves that an accepted
  selector invocation consumed already reviewed threshold/floor bytes. This
  does not claim to prove what an author may have explored privately.
- Discrete and admission policy characterizations have distinct closed,
  self-hashed schemas with complete derived rows, rationale, and reference
  evidence. A separate captured environment-v3 verifier recompiles the LUT
  from the complete recipe/generation/renderer records, reconstructs all 256
  discrete OKLab rows and selector results, and verifies the actual LUT hash
  before Reviewer A; policy-registry promotion only verifies and copies that
  accepted evidence DAG. Admission references are derived
  only from immutable accepted shipped/frozen assets, are byte-excluded from
  candidate rows, and replay through separately accepted immutable oracle
  truth. That truth is usable only with its fixed-path tracked bootstrap
  acceptance and complete archived review/snapshot closure. Each derived
  reference-member validation result has a defined domain and complete
  policy/truth/acceptance/identity/hex/metric preimage. Registry, review, and
  preselection identities are cross-bound rather than reusable by a policy
  label or hash alone.
- Comparison evidence contains the closed ordered 18-surface report with zero
  mismatches plus four required presentation roles: shipped preservation,
  compatibility-versus-fixed-Y diagnostics, direct-versus-fixed previews, and
  discrete selection/validation. Promotion independently reruns the comparator;
  neither a Boolean nor a stale docs panel is authority.
- Completion output rules are schema-specific: comparison enumerates an
  artifact map, named-output schemas prove an exact path set, and report-only
  schemas require no ordinary output. Bundle stores follow their separate
  content-addressed lifecycle and are never smuggled into a generic map. Every
  native producer transfers the complete authorized output set through one
  private manifest written last; after kill/reap, every member is copied,
  rehashed, fully sealed, and checked against both profile and primary before a
  byte-only primary-last publication.
- Source fingerprints bind the Git executable/config policy, HEAD, stage-0
  index modes and raw blob hashes, canonical semantic index, working tree,
  arbitrary Git path bytes, and untracked blobs. Evidence executes only from a
  read-only captured Git/source snapshot, never the live worktree. Durable
  publication requires every non-HEAD index/worktree state to equal the exact
  reviewed source mode/hash; a shared path does not authorize different staged
  bytes. Git config and raw index layout are transiently validated but only the
  object-format/bare operational projection and canonical synthetic capsule
  config plus deterministic zero-stat/extension-free index are bound. Raw
  config, live/shared index bytes, remote/branch values, and unrelated local
  bytes are never archived. Public invocation recipes, environment, operation
  registry, and source-capsule layout have exact path-neutral preimages.
  Authoring provenance binds the self-sealed static native supervisor and
  seal/VM/launch-environment policy from before either child creation, the exact
  strict wheel-provisioning parser/public artifact projection/private witness,
  private computation-input inventory, process split/transfer manifest policy,
  both no-site broker-first CPython
  argv/bootstrap/cwd/pre-broker/path-stage records,
  the complete terminal-output-set policy, the process executable and loader,
  every startup/late mapping
  callback, normalized mapping records, continuous kernel-event reconciliation,
  final enumeration, and address-derived roles. V1 runs only on Linux and uses
  private user/IPC/mount/network namespaces with verified old-root detachment,
  an exclusively leased subordinate credential, fully sealed runtime/source/
  input leaves, a from-empty fixed-seed/rseq-disabled environment, a closed descriptor/
  IPC/network/device/async-writer surface, an exact
  `PTRACE_O_TRACESECCOMP`/`PTRACE_O_TRACESYSGOOD`/`PTRACE_O_TRACEEXEC`/
  `PTRACE_O_EXITKILL` state machine with traced `brk`, no registered rseq, and
  no x86-64 vsyscall route, and a verified post-constructor/pre-main
  non-dumpable `la_preinit` barrier in a single-threaded lane. Darwin and other
  platforms fail native preflight before Python and emit no public record.
  It also binds exact scalar extractors, the preparer's complete stdlib/native
  closure and typed base/runtime-import handoff, exact manifest module binding/
  loader/spec/cache grammar and protected import metadata, the exact private
  control role/order grammar, the stopped
  base-ready and final capture/commit transfers, complete base/final module
  closures, retained module-guard transition array/count/hash, sticky post-base
  module-table guard, receipt logs, invocation-
  selected package dispatch, and closed project-execution registry/policy/
  namespace/module/data/event arrays,
  used-file manifests for every used Python
  distribution—including an exact cross-binding between NumPy's nested
  distribution records and its runtime-distribution row—and literal gradual-
  underflow probes. A common base-runtime identity binds `base_numpy`, the
  split/startup/receipt/seal/VM/credential/supervisor/launch-environment policy,
  the public runtime tree, inline base broker prefix, and complete base stdlib/
  module/dependency/mapping closures and is compared across
  stages; each real
  operation then captures its own complete terminal module/import preimage,
  complete used mapping projection,
  full runtime identity, and complete inline arithmetic-trace preimage/count/
  digest under the one 14-row call/shape grammar. Both discrete/admission policy-characterization verifiers,
  preselection, and frozen
  promotion each own a complete environment-v3
  record for their actual invocation; no environment is inferred from another
  stage. Baseline promotion and authority finalization, policy-registry,
  fixed-Y, and validation-truth archive promotions instead own closed archive-
  promotion provenance because they transfer already reviewed bytes and
  perform no color arithmetic. There is no synthetic universal warm-up.
- Environment-v3 serializes the complete residual stdlib closure and exact
  installed-distribution ownership triggers under the project/distribution/
  site-exclusion/stdlib/native precedence. Equal sysconfig roots coalesce;
  overlaps and metadata gaps fail instead of selecting the first prefix. Its
  site-exclusion rule is a post-load provenance classifier, not a startup
  barrier; startup authority comes only from the separately bound no-site
  broker-first record.
  Its public projection omits hostname, roots, loader names, subordinate IDs,
  user-namespace/lease facts, distribution metadata not selected into either
  the prospective runtime manifest or observed used closure, and every
  derivative hash of those private values. This omission is field-level, not a
  false byte-neutrality claim for an unread member of a selected wheel: the
  public provisioning projection binds that wheel's whole-archive hash. A prospective manifest candidate
  intentionally remains common-base identity even if unread; it does not
  thereby become a used-distribution trigger or selected-artifact-projection
  row. Each used row
  binds the guarded wheel archive actually supplied by controlled provisioning;
  the invocation-specific selected-artifact projection is reconstructed from
  those complete ordered rows and bound by runtime/full environment hashes.
  Offline verification repeats that reconstruction without retaining or
  hashing the raw lock, package tables, installer receipts, URLs, paths,
  filenames, cache locators, or artifacts absent from both public closures.
  Math origins use their
  exact one-record stdlib projection or private `PyInit_math`
  address-to-sealed-mapping binding and closed core-role literals; a
  path/public-identity comparison and redundant module SHA field are forbidden.
  Every ordinary native image comes from a prelaunch sealed leaf. Linux's only
  fileless exception is the ASLR-neutral mapped vDSO identified by
  `AT_SYSINFO_EHDR` and forbidden from core roles. A source path
  disappearing after Linux sealing is neutral, while a GNU build ID is never
  identity.
- Offline verification strict-parses and recomputes both Python startups, every
  preparer stdlib/native closure, typed handoff/provisioning and runtime-tree/
  module-binding preimage, every
  complete inline computation broker-read record/count/digest and its handoff/
  source/external/distribution/stdlib/phase-manifest cross-links, its base-ready
  prefix and complete base closure/common-base binding, the complete final
  module array/count/domain with base-subset/manifest/receipt/distribution/
  project/shell/namespace links and its final transfer equality, every complete inline
  arithmetic trace including every row's exact arity/vector semantics,
  degree/exp, and fixed-direction nextafter records, the public private-control
  policy ID, package-dispatch/profile/source links, closed project-execution
  registry and selected namespace/module/data policy,
  namespace/event/import projections, the complete mapping-record/order/hash,
  role links and base-ready subset, environment
  cascade, and enclosing completion hashes. For policy
  approval it resolves the archived Reviewer-A verification-evidence blob and
  cross-checks its raw/semantic identity through both reports, the walkthrough,
  and the entry rather than assigning an environment to the archive promoter.
  It does not claim to
  recreate the destroyed private descriptors, namespace/mount transaction, VM
  addresses, seccomp/ptrace stop sequence, subordinate-ID lease, post-exec
  dumpability transaction, private transfer manifest/index, request/platform/
  control or receipt transport logs, or historical kernel
  credential/inode-to-mapping association. The hash-bound VM-policy/supervisor
  capability, live production guards, and unchanged-snapshot A/B evidence
  authorize that narrower historical claim.
- The common source snapshot is distinct from stage-specific immutable input
  bundles. Tracked scientific payloads exclude policy approvals and invocation
  provenance; their validation-oracle truth record likewise excludes bootstrap
  acceptance. Proposal siblings bind the admission-entry/preselection
  acceptance chain through a distinct public reproducibility hash, require its
  truth cross-links to equal the scientific record, and every
  review report is valid only with its complete pre-run control and post-run
  content-addressed evidence bundles. Closed subject/envelope schemas cover
  ordinary semantic batches, both fixed-Y review stages, and validation-truth
  bootstrap.
- Every input/control/evidence bundle has one canonical `manifest.json` plus
  content-addressed `blobs/` layout. Both fixed-Y review stages promote their
  complete A/B closures and the common complete execution-snapshot archive to
  tracked create-only acceptance records; ignored reviewer output alone cannot
  support a normative claim.
- Validation truth similarly promotes one preinstall A/B closure and common
  snapshot archive to a tracked bootstrap acceptance, then installs only the
  reviewed archived candidate. Ignored reviews or a self-hashed truth alone
  have no admission authority.
- `color_v5_baseline_acceptance.json` authorizes only the completed preinstall
  review and initial promotion transaction. Shipped baseline authority also
  requires the tracked promotion A/B closure, post-promotion approval, and
  fixed-path `color_v5_baseline_authority.json`; ignored reports, the original
  pair alone, or a commit predating that marker grants no authority.
- A surviving baseline authority marker implies that both tracked archives,
  the compatibility asset, acceptance, promotion review sequence, approval,
  and every cross-link passed their bottom-up durability barriers. Consumers
  derive and verify that complete path set in the authority commit before
  applying the first-parent and no-overlay checks.
- Every archive promotion also captures its own role-complete input bundle and
  canonical maintainer-approval file. The baseline authority marker, policy
  entries, fixed-Y acceptances, and validation-truth bootstrap acceptance
  embed the resulting self-hashed promotion provenance, and later consumers
  reparse that bundle rather than trusting a detached approval claim.
  The six promotion kinds form a closed registry that fixes the external
  bundle kind, entry module, operation ID, three operand values, output-role
  literal, and tracked manifest root as one indivisible row. Their executable
  role resolves to a deterministic verified byte-transfer state machine, not
  an ambient Python runtime: an independent verifier reconstructs the complete
  target-byte map and final authority state. Host interpreter identity is
  therefore non-authoritative and no environment-v3 record is fabricated for
  these non-color transitions. Recovery admits only byte-identical expected
  archive subsets before an authority marker, the exact baseline asset-before-
  acceptance boundary, the exact post-promotion archive/approval-before-marker
  boundary, policy immutable orphans while the old index still
  matches its expected-old guard input, and truth acceptance before reviewed
  truth installation. Retry reconstructs the full reviewed repository state and
  permits only that state plus one exact derived target-map overlay: HEAD, Git
  index, and every non-target path remain byte/mode-identical. A current
  fingerprint without that complete path-map proof has no recovery authority;
  all other partial, unrelated, or aliased states fail closed. Every final leaf
  is absent or byte-complete after power loss; every surviving marker/index
  implies its file and parent-dirent prerequisites passed bottom-up barriers.
- Fixed-Y phase evidence contains literal declared-source arrays and a byte-
  identical copy of each environment-owned complete computation broker-read
  array with its hash; the two startup closures and typed control handoff supply
  the non-computation bootstrap/registry/shell source identities. Both review subjects include the corresponding
  phase input manifests and blobs, so tracked acceptance can replay public read
  preimages after ignored producer paths disappear.
- Execution-snapshot archives are keyed by their own self-hash and use the
  canonical `git-loose-zlib-stored-v1` object and
  `git-index-v2-zero-stat-extension-free-v1` index representations. Tracked leaves are
  regular Git-`100644` blobs; physical read-only modes belong only to private
  materializations. Their project closure is HEAD plus exact reviewed source
  states under both index/worktree implications,
  and their Git config is synthetic operational state; local raw config and
  unrelated dirty/untracked bytes are structurally unpublishable. When shipped
  authority is consumed, the exact object union additionally contains only its
  captured `H -> ... -> A` first-parent-chain commits and complete `A` tree;
  offline parsing starts from the fixed authority marker, closes every
  acceptance-or-marker-reachable path, and rejects missing steps,
  non-first-parent substitution, unrelated copied history, or extra objects.
- The exact legacy-v5 predecessor commit is the only initial implementation
  authority. Baseline capture, promotion, deterministic post-review authority
  finalization, compatibility migration, and authoring are ordered boundaries;
  each later semantic batch starts from a new exact HEAD containing the already
  accepted prior result and, for baseline, its completed authority marker. The
  finalization marker records a finished promotion A/B sequence and is not
  misrepresented as another recursively reviewed semantic change. The present two-document
  review neither reads an earlier draft/prototype nor treats a future asset
  path as existing evidence.
- Reviewers never use a dirty development checkout as their snapshot root. A
  new exact-HEAD, no-alternates capsule is clean before the declared source
  states are overlaid. Unchanged declared sources remain outside `D`; the
  current spec/ADR capsule exceptionally has `D=A` with exactly the two
  reviewed `(ABSENT,ABSENT,R,R)` documents and no other non-HEAD state.
- Loaded-image completeness under `LD_AUDIT` comes from the stopped
  `r_debug_extended` two-namespace union, not from the base caller's
  `dl_iterate_phdr` pass. The public dependency roles distinguish the audit
  leaf and audit-only closure as `startup-audit` and `audit-transitive/*`, and
  zero orphan mappings is mandatory.
- Frozen family paths are durably create-only: byte-identical repetition is
  reverified/resynchronized as a no-op and any different overwrite is fatal.
- No public API, existing color, LUT, index, or registration changes as a
  consequence of accepting this ADR.
- At acceptance, no V1 extension archive had been emitted, so the corrected
  draft identifiers remain in place. Discovery of any escaped
  old-format artifact requires a coordinated V2/V3 bump beginning with the
  scalar-kernel constants and selected-artifact/used-distribution/environment
  schemas, both Python-startup/argv/pre-broker/path-stage domains, process-split/
  private-transfer, computation-inventory, provisioning/parser/witness and
  control-role policies, base/invocation handoffs, public runtime-import
  manifest/module-binding tree, synthetic package-shell and post-base module-
  table guards and transition preimages, project-execution
  registry/policy/namespace/data/event/import and
  receipt capabilities, computation broker-read schema/domain, complete base/
  final module and closure-transfer/prefix domains,
  and
  phase/trigger cross-links,
  arithmetic-trace 14-row operation/shape/call set, schema, and domain,
  native-execution/VM/credential-policy/
  mapping/vDSO domains, terminal-handoff policy/manifest/output profiles and
  capabilities, policy-characterization verification evidence and its
  review/entry cross-links, and continuing
  across scientific payloads, oracle results, tools, fingerprints, capsules,
  snapshots, archives, acceptances, and tracked review-root identities; a
  partial bump is invalid.
- The implementation contract lives in
  `docs/superpowers/specs/2026-07-27-oklab-authoring-extension-design.md`.
- Each semantic batch requires two fresh-agent, sequential adversarial reviews
  on one unchanged clean-capsule source snapshot before the next batch begins. Each review
  has independently captured role-complete subject and pre-run control bundles,
  and B's bundle contains A's completed report, historical execution-input,
  control, and evidence bundles plus A's completion token. Each sealed public
  review log has one terminal result from which the report's verdict and
  findings are mechanically derived; raw provider transport is not stored.
  Harness records make the procedure
  auditable; maintainer attestation remains the honest authority for reviewer
  independence rather than a cryptographic identity claim.
