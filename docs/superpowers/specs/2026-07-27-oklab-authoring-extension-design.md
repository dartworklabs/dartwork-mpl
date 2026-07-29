# OKLab-centered migration, authoring, and shipped-compatibility isolation

**Date:** 2026-07-27

**Status:** Accepted

**Decision record:** [ADR 0002](../../adr/0002-separate-shipped-color-compatibility-from-oklab-authoring.md)

**Normative predecessor:** exact Git commit
`6be8cb56b8752e03515101caa7ae2f6c52cc13dc`

**Dependency status:** standalone. This document restates the relevant
conceptual direction from historical ADR 0001 and earlier design drafts, but
neither is an implementation baseline or review input. ADR 0002's more complete
contract supersedes only the overlapping migration requirements; prototype
code and assets remain non-authoritative.

## 1. Purpose

Define the complete migration from the exact legacy-v5 predecessor to an
OKLab/OKLCH-centered system without changing any published color. This is not
an extension of an already installed redesign. It must:

1. capture and independently verify the predecessor's complete shipped output;
2. introduce an isolated OKLab/OKLCH compatibility-replay lane and prove it
   reproduces that baseline exactly;
3. replace a falsely generic fixed-relative-Y chroma-boundary design with a
   mathematically complete new-family primitive; and
4. provide an OKLab/OKLCH candidate selector and admission path for a genuinely
   new multi-hue family.

The shipped catalog and new-family authoring are different products with
different stability requirements. They must not share an implicit fallback.
After compatibility migration, the shipped catalog must replay accepted output
exactly. The authoring lane may use new algorithms, but its result is reviewed,
independently validated, and frozen before it can become runtime data.

This design does not claim that modeled relative CIE Y is physical display
luminance, perceived brightness, or OKLab `L`. It remains a calculated nominal
D65-sRGB output coordinate.

The model roles follow their primary definitions: [OKLab](https://bottosson.github.io/posts/oklab/)
is the perceptual construction/authoring space and [CSS Color 4](https://www.w3.org/TR/css-color-4/#ok-lab)
defines OKLCH as its polar form; [CIEDE2000](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/)
is a CIELAB color-difference calculation; and the
[Machado](https://doi.org/10.1109/TVCG.2009.113) and
[Brettel–Viénot–Mollon](https://doi.org/10.1364/JOSAA.14.002647) models simulate
specified forms of color-vision deficiency. These sources justify keeping the
roles separate; none turns a modeled-Y equality, finite color-difference row,
or simulated CVD result into an observer-wide accessibility guarantee.

### 1.1 Normative baseline and non-circular bootstrap

The only predecessor authority for this design is the complete tree at commit
`6be8cb56b8752e03515101caa7ae2f6c52cc13dc`. At that commit:

- `src/dartwork_mpl/_colors/_generate.py` authors OKLCH hue/chroma while solving
  rendered output against CIELAB `L*` targets;
- `src/dartwork_mpl/_colors/_discrete.py` selects multi-hue rows at runtime;
- `docs/color_system/design-rationale.md` documents the mixed CIELAB/OKLCH
  construction; and
- no `SHIPPED_TONE_COMPATIBILITY_POLICY`, frozen
  `MULTI_HUE_DISCRETE_INDICES`, v6 compatibility SSOT, or accepted 18-surface
  comparison artifact exists.

Those are baseline facts, not defects that may be hidden by reading a dirty
worktree. Any similarly named local spec, ADR, source file, or JSON outside
that commit has zero authority until a later semantic batch reviews and
accepts it. A path named below may therefore be a required future deliverable;
mentioning the path does not assert that the file exists in this document-only
review snapshot.

Migration is a closed sequence of separately reviewed semantic batches:

1. **Baseline preinstall.** From a detached materialization of the normative
   predecessor, two extractors that cannot import candidate migration code
   create sealed ignored candidates rather than tracked assets. Independent
   extraction must agree on all 18
   exact surfaces, including 200 palette colors, both cycles, curated/manual
   rows, all 43x256 LUT entries, forward/reverse discrete outputs, all 72
   multi-hue `n=1..8` result/index rows, metadata, and 892 vendor colors. This
   preinstall batch receives its own local verification and A-then-B review.
   There is deliberately no separate quality golden:
   exact shipped bytes preserve every deterministic output-derived diagnostic
   when its implementation is unchanged. The compatibility batch must not
   modify predecessor validation implementations or thresholds and must rerun
   that unchanged gate suite as a sanity check; those derived results are not
   separately pinned into the v6 compatibility authority.
2. **Baseline promotion.** A separate semantic batch consumes only the six
   sealed preinstall outputs, complete A/B closure, snapshot archive, and
   canonical maintainer approval. It installs create-only
   `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/color_v5_compatibility.json`
   and sibling `color_v5_baseline_acceptance.json`, then receives a new local
   verification and fresh A-then-B review. After promotion B passes, a closed
   non-semantic finalizer archives that completed promotion-review closure,
   captures a post-promotion maintainer approval, and publishes
   `color_v5_baseline_authority.json` last. The baseline gains authority only
   in a later exact HEAD containing the preinstall archive, both baseline
   files, the complete promotion-review archive and approval, and that marker.
3. **Compatibility migration.** Starting from a new exact HEAD that already
   contains and verifies that complete baseline authority closure, introduce the OKLab/OKLCH
   compatibility-replay lane, v6 SSOT, frozen indices, architecture gates, and
   deterministic side-by-side report. Acceptance requires zero exact-surface
   mismatches and a PASS from the unchanged predecessor validation/gate suite.
   Prototype results in an earlier dirty worktree are not evidence.
4. **Authoring extension.** Starting from another exact HEAD that already
   contains the accepted compatibility migration, add the direct-OKLCH default,
   narrowly opt-in fixed-Y primitive, selector, validation, and frozen-family
   admission machinery defined below. It cannot enter any shipped call graph.
5. **Documentation activation.** Present-tense user documentation changes only
   after the corresponding implementation and evidence batch has passed A and
   B. Until then, this design describes requirements and target paths,
   not installed behavior.

No phase may be reviewed against a capsule that merely overlays its unaccepted
predecessor phase in the same dirty worktree. Each accepted phase must first be
part of the content-addressed HEAD used by the next phase. This ordering makes
the baseline, compatibility proof, and authoring proof non-circular.

Both baseline stages use the ordinary `semantic-batch` A/B report schemas with
special subject IDs. The canonical ignored preinstall output tree is exactly:

```text
build/color-authoring/legacy-v5-baseline-preinstall-v1/
  extractor-a/color_v5_compatibility.json
  extractor-a/evidence.json
  extractor-b/color_v5_compatibility.json
  extractor-b/evidence.json
  cross-extraction/color_v5_compatibility.json
  cross-extraction/manifest.json
```

`legacy-v5-baseline-preinstall-v1` contains every changed extractor,
cross-checker, and test source at `source-snapshot` and exactly the six roles
`baseline-extractor-a-candidate`, `baseline-extractor-a-evidence`,
`baseline-extractor-b-candidate`, `baseline-extractor-b-evidence`,
`candidate-compatibility`, and `baseline-cross-extraction-manifest` at
`external-input`, each once. The two extractor candidates are distinct regular
files in disjoint sealed output directories. Symlinks, hard links, path
aliases, shared temporary files, or either extractor reading the other
extractor's output are forbidden. The subject contains no shipped-exact-
surfaces or side-by-side record because those authorities are what this flow
creates.

The extractor IDs also close their independent methods.
`baseline-extractor-a-v1` is the observational extractor: it starts one fresh
predecessor process, imports the exact predecessor package, then runs the
section 1.2 observations in this fixed state order: default-state MCP
resources/tools and API index; colormap/named-color registries, typing,
taxonomy, and public inventory; all remaining default color calls including
selector choice-time instrumentation; semantic scientific then Korean style;
and dark style last. A later mutation cannot feed an earlier observation. It
may read literal source only to verify an observed result, never to substitute
for a required public call. `baseline-extractor-b-v1` is the static
reconstruction extractor: it does not import or execute a project or
matplotlib module; it parses the exact predecessor Python AST/data/style assets,
independently
reimplements the documented selector/registration/normalization algorithms,
and parses MCP decorators and function bodies to prove the endpoint identities
and returned projections. Its standard-library parser implements the exact
hex/RGBA normalization directly. Both methods use the one closed normalization below. Sharing an
extraction helper, normalized intermediate file, project module object,
selector implementation, or candidate output is forbidden; their only common
authority is the immutable predecessor snapshot and this specification.

Each evidence file is canonical JSON with exactly:

```text
schema, extractor_id, extractor_source_raw_sha256,
baseline_commit, baseline_tree_sha256, candidate_import_count,
invocation_recipe, source_fingerprint, execution_snapshot,
execution_inputs, environment, source_files,
surface_order, surface_hashes, compatibility_asset_path,
compatibility_asset_byte_count, compatibility_asset_raw_sha256,
evidence_sha256
```

The schema is `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1`.
Extractor IDs are the distinct literals `baseline-extractor-a-v1` and
`baseline-extractor-b-v1`; their source paths and hashes must be distinct and
both occur in the reviewed source set. `baseline_commit` is the normative
predecessor, `baseline_tree_sha256` is SHA-256 of its canonical complete Git
tree manifest, and `candidate_import_count` is the non-Boolean integer zero.
`compatibility_asset_path` is exactly the matching extractor candidate path in
the tree above. `compatibility_asset_byte_count` is a positive non-Boolean
integer, and it and `compatibility_asset_raw_sha256` are recomputed from that
regular file. Each extractor's primary completion path is its sibling
`evidence.json`, written only after the candidate has been flushed, canonical-
byte checked, and sealed. Its invocation recipe's final
`output-artifact-role` operand is respectively the exact literal
`legacy-v5-baseline-extractor-a-output` or
`legacy-v5-baseline-extractor-b-output`.
The recipe, fingerprint, snapshot, inputs, environment, and complete ordered
source-file array use section 10's closed records and the extractor-specific
invocation profile. `candidate_import_count` excludes the one reviewed
extractor entry source and harness but counts every other project source absent
from the predecessor tree; any such import fails.
`surface_order` is section 3.6's exact 18-member order. `surface_hashes` has one
closed `surface_id,canonical_sha256,count` row in that order;
`compatibility_asset_raw_sha256` is the raw-byte hash of the sealed candidate.
The evidence self-hash uses
`b"dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1\0"` plus canonical
JSON with only `evidence_sha256` omitted.

The extractors run in distinct fresh capsules. Both execution-input manifests
have zero external records, and the broker exposes only their independently
materialized predecessor snapshot; neither ignored output directory is visible
to the other invocation. Only after both extractor directories are sealed, a
distinct `legacy-baseline-cross-extraction` invocation captures exactly those
four candidate/evidence files and writes the final candidate as a byte-for-byte
copy at the cross-extraction candidate path above. Its primary
`cross-extraction/manifest.json` has schema
`dartwork-mpl-legacy-v5-baseline-cross-extraction-v1` and exactly:

```text
schema, baseline_commit, baseline_tree_sha256,
invocation_recipe, source_fingerprint, execution_snapshot,
execution_inputs, environment, source_files,
extractor_outputs, candidate_compatibility, surface_hashes_sha256,
cross_extraction_sha256
```

`extractor_outputs` is an A-then-B array whose rows have exactly
`extractor_id`, `candidate_role`, `candidate_path`, `candidate_byte_count`,
`candidate_raw_sha256`, `compatibility_payload_sha256`, `evidence_role`,
`evidence_path`, `evidence_byte_count`, `evidence_raw_sha256`, and
`evidence_sha256`. The roles and paths equal the four extractor entries above.
`candidate_compatibility` has exactly `role`, `path`, `byte_count`,
`raw_sha256`, and `compatibility_payload_sha256`; its role and path are
`candidate-compatibility` and the cross-extraction candidate path. Every byte
count is a positive non-Boolean integer. `surface_hashes_sha256` uses section
1.2's domain and ordered surface rows.

Strict parsing independently validates both evidence objects and both
compatibility objects, requires the two complete extractor candidate byte
strings to be identical, and requires the final candidate to be identical to
both. Reviewers reconstruct this record from all six sealed files instead of
trusting its equality claims. The cross-check invocation reads only its four-
record immutable external bundle; its output-artifact role is the literal
`legacy-v5-baseline-cross-extraction-output`.
`cross_extraction_sha256` is SHA-256 of
`b"dartwork-mpl-legacy-v5-baseline-cross-extraction-v1\0"` plus canonical JSON
with only that field omitted. The manifest is published last only after
rehashing both source candidates, both evidence files, and the copied candidate
twice with identical results.

Strict parsing must show that the two independent evidence files agree on the
tree, ordered surface rows, and candidate hash. Preinstall A/B validates both
extractor implementations, all six retained outputs, and the independently
reconstructed cross-extraction manifest before treating the copied candidate
as the selected promotion candidate.

`legacy-v5-baseline-promotion-v1` is a later semantic batch. Its changed
baseline paths are the compatibility asset,
`color_v5_baseline_acceptance.json`, and every regular leaf of the canonical
tracked promotion-input archive rooted at
`legacy-v5-baseline-review-v1/archive/input-bundles/` at `source-snapshot`;
its external bundle contains exactly all six sealed preinstall outputs,
complete preinstall A/B reports, their historical execution-
input/control/evidence manifests and distinct blobs, A's completion token, the
common preinstall snapshot archive, and canonical maintainer approval.
Promotion copies the reviewed closure into that content-addressed archive,
copies the candidate byte-for-byte, and constructs the acceptance record; it
does not run either extractor. It publishes every immutable leaf with section
3.5's fsynced atomic no-replace primitive. It installs and durably verifies the
archive first, publishes and durably verifies the compatibility file second,
then crosses a durable-prerequisite barrier before publishing acceptance last
as the completion marker. No claim of crash-atomic creation across the two
sibling paths is made. A fully valid byte-identical archive and pair are an
idempotent no-op. Before either target exists, a byte-identical subset of the
expected archive leaves and exact subset of required new parent directories is
a recoverable crash state: retry validates every existing leaf and directory,
creates only missing state, and revalidates the complete durable archive. After
that archive is complete, the exact compatibility file without acceptance is
the one recoverable pair boundary; retry reparses, rehashes, and durability-
barriers the archive and compatibility bytes before publishing acceptance.
Because acceptance is never published before that barrier, acceptance without
compatibility or with an incomplete archive is not a machine-produced crash
state and is fatal, as is an unexpected/aliased path or any differing byte.
Promotion itself receives a new A/B sequence. The subject deliberately stops
at the proposed preinstall archive, compatibility asset, and acceptance: no
promotion report, post-promotion approval, or authority marker exists when A
starts, and pretending that such a future object was reviewed would be a hash
cycle.

After promotion B passes, the same reviewed finalizer implementation performs
one deterministic, non-color authority-finalization transition. It accepts
only the unchanged promotion subject, valid sequential A/B PASS closure, A
completion token, common snapshot archive, and a new post-promotion maintainer
approval. It copies that complete closure create-only beneath
`legacy-v5-baseline-review-v1/promotion-review/`, then publishes the approval,
crosses the full durability barrier, and publishes
`color_v5_baseline_authority.json` last. This finalizer cannot change the
compatibility asset, acceptance, their preinstall archive, or any scientific
value. It is analogous to issuing the A-completion token: a mechanically
recomputed completion binding over an already finished review, not a new
semantic subject. Requiring another A/B pair to review that binding would only
move the same completion boundary forward forever. The compatibility-migration
batch nevertheless independently resolves the full binding and receives its
own ordinary A/B review.

Only a still later exact HEAD containing the complete preinstall archive and
pair, the full promotion-review archive and approval, and the authority marker
makes the baseline authoritative. A commit containing the pair before
promotion B, or containing the pair without the marker-reachable promotion
closure, is mechanically distinguishable and has zero baseline authority.

### 1.2 Legacy compatibility asset contract

The accepted compatibility file has exactly these top-level keys:

```text
schema, baseline_commit, baseline_git_tree_oid, baseline_tree_sha256,
surface_order, source_closure, inventory, surfaces, surface_hashes,
compatibility_payload_sha256
```

`schema` is `dartwork-mpl.color-compatibility/v2`; `baseline_commit` is the
normative predecessor; and `baseline_git_tree_oid` is exactly
`af45c52a5f56091bed9cea7609cb67d74852a0e5`, that commit's lowercase full tree
object ID. The verifier hashes the raw predecessor commit payload to reproduce
`baseline_commit`, parses its literal `tree` header, requires that OID to equal
`baseline_git_tree_oid`, and recursively captures/parses every referenced raw
tree/blob object while independently reproducing each Git object ID. A physical
directory in an extracted review/worktree is never a tree entry: only a raw
parent-tree record can create one. In particular, after excluding an untracked
overlay file, its now-empty parent directory must not be invented as Git's
empty-tree object. These two fields identify the legacy extraction source; they
are not the later `baseline_authority_commit` or that commit's root tree. To compute
`baseline_tree_sha256`, recursively enumerate
the predecessor tree's non-directory entries by unsigned raw-path byte order.
Gitlinks are forbidden. For each regular or symlink blob append:

```text
git_mode + NUL + object_type + NUL + decimal_path_byte_count + b":" +
raw_path + NUL + lowercase_full_git_object_id + NUL +
sha256(raw_blob_bytes).hexdigest().encode("ascii") + NUL
```

Hash `b"dartwork-mpl-legacy-v5-tree-manifest-v1\0"` plus the concatenated
records. Git mode and object type are the canonical ASCII values reported by
the independently parsed tree (`100644`, `100755`, or `120000`; `blob`). The
manifest is reconstructed from Git objects, never from worktree stat data or
filters. The exact predecessor has 942 such entries and the required digest is
`c4ad8b723efc689a6ee503037837d049c8cd1c836a07f6a599295750d6688cb1`.
Root-tree identity and the leaf manifest are separate checks over that one raw
closure: neither is reconstructed from physical directories, and matching the
leaf digest cannot excuse an added, omitted, or reordered raw tree entry.
Section 10's `head_manifest_sha256` uses a different domain and record
encoding, so the two digest strings are not expected to match. Both algorithms
must nevertheless enumerate the same complete non-directory predecessor-tree
entry set and independently agree on every path, mode, object ID, and raw blob
SHA-256 before either digest is accepted.

`surface_order` is section 3.6's exact 18-member order. `source_closure` is the
UTF-8-path-sorted nine-record primary color-data closure below. Each record has
exactly `path`, `git_mode`, `byte_count`, and `raw_sha256`, and every value is
recomputed from the predecessor tree rather than copied from this table:

| Path | Required raw SHA-256 |
|---|---|
| `docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json` | `a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518` |
| `src/dartwork_mpl/_colors/_curated.py` | `ee570b840323015db427e1bb36f500eb4f12d67027aa3894f9b7ba02caa295f5` |
| `src/dartwork_mpl/_colors/_generated.py` | `999950452b2f2d8e2d58449af7c7fa043d918c922719be68939f765f5f762d54` |
| `src/dartwork_mpl/asset/color/ant_colors.json` | `9cad970d63064bfd35c122a03e9ee0d53d5e90754fea2e3dbaa911fa1f09fa7c` |
| `src/dartwork_mpl/asset/color/chakra_colors.json` | `fd5c54c87c532a3448edab06c870407ec9616f93cb18eeacab933a34237af6f9` |
| `src/dartwork_mpl/asset/color/material_colors.json` | `cce34cc9f41ed4562524ab03e26d1bbcb27f3f81e1e3c9ae22acb0d372817888` |
| `src/dartwork_mpl/asset/color/opencolor.txt` | `8210fd90139d05ab38b34a2b62a5968adeabe9999f5f12607054c9c630728ad7` |
| `src/dartwork_mpl/asset/color/primer_colors.json` | `91f269a580137ea58da44075b4cd732062aef3ea8b17a5cf20f3f339b78dab94` |
| `src/dartwork_mpl/asset/color/tailwind_colors.json` | `281d2942d14d55d8dcabe389054757d2b898c9ab467ba1d752dbdef0f881436f` |

This nine-record projection is not claimed to be the complete implementation
closure. The complete predecessor tree is bound above, and each extractor's
full project import/read closure is separately bound by its section 10 source
snapshot and `source_files`. Each extractor is one distinct reviewed standalone
entry source and records its own source hash only in its evidence, so extractor
implementation bytes do not enter the common data projection. Both extractors
must read and revalidate all nine records even when one algorithm needs only a
subset. Reading a candidate migration module, draft asset, or live-worktree
file fails.

The remaining per-surface derivation roots are not additional primary data
records, but both extractors must resolve these exact predecessor paths and raw
hashes through their complete `source_files`/execution snapshot. A shorthand
module name used below refers only to the matching row:

| Exact predecessor path | Required raw SHA-256 |
|---|---|
| `src/dartwork_mpl/_colors/_families.py` | `e883d943814c26fd872a37cdb8cd9e86af62b7f5ef9d8b5ea9b69b3639dc524a` |
| `src/dartwork_mpl/_colors/_register.py` | `e7ae8dfbfb089fc8f383175bd4c92988f6b4c2d0f1fde63537075d2ccc04da47` |
| `src/dartwork_mpl/_colors/_typing.py` | `2ec8854547bf0896a43adad559b911e4c503fe94c801ae7df56db16604dfb114` |
| `src/dartwork_mpl/_colors/_semantic.py` | `882dbea7ac630e0ea5efcc006655e684e4e743dab23b36fe3997053950c03cf0` |
| `src/dartwork_mpl/_colors/_api.py` | `f98b9520fe3d340a692d63050beaa001421a12900c61172b1c7f34e405281109` |
| `src/dartwork_mpl/_colors/_discrete.py` | `b95694ffaf67a02a9d5dda756b9100f7372d81d0f03d5f45ef9356cdf614d892` |
| `src/dartwork_mpl/_colors/_metrics.py` | `53ab7b27f7cad307d0bf4ee81e02b94fadf901730e486c91681413816f1bb435` |
| `src/dartwork_mpl/_colors/_loader.py` | `748ab324bed91a8c9d6ceb8c191ae4d49e528498bf282b4fde953e4911be929b` |
| `src/dartwork_mpl/_colors/__init__.py` | `5748b37fe1393b1848dbff2156f9a96fbe033f39e4aedf1fac53963726532889` |
| `src/dartwork_mpl/mcp/resources.py` | `b6fe4d5f6e8db6642800ddf4b0e86d67ff04b41f3936faf500a9ae5b09aacbf0` |
| `src/dartwork_mpl/mcp/tools.py` | `e41958bb47a45e4453ac326f7cf4b1c2aa00f5f8300037702aec83f48aafbdf3` |
| `src/dartwork_mpl/__init__.py` | `854fcdb990c806b880eaf94983b807e7946c427091e55023926ffce98993b48f` |
| `src/dartwork_mpl/style.py` | `c1f9c8baf6c2ae8a5cd031db81dfae66f195ba42c416c0f0a59fc498ed3445b3` |
| `src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle` | `f78fe340b22e46764191eac9052204462d1442353277d2d9534df753a73d4a22` |

Each hash is recomputed from the normative predecessor blob. The table neither
widens the nine-record `source_closure` nor permits an extractor to omit any
other imported/read source from its complete captured closure.

`inventory` has exactly `cmap_positions=11008`, `cycle_positions=16`,
`dc_tokens=380`, `families=56`, `palette_positions=200`,
`qualitative_families=13`, `registered_colormaps=99`, and
`vendor_tokens=892`. `surfaces` has exactly the 18 `surface_order` keys. A
surface value is a canonical JSON tree containing only strings, non-Boolean
integers, Booleans, null, arrays, and objects with unique UTF-8 keys; floats are
forbidden. Canonical object-member order is never semantic: the serializer
sorts object keys by unsigned UTF-8 bytes. Every observable predecessor order
is therefore represented by an array or checked explicitly before extraction.
Arrays retain the order stated below. A terminal-leaf count counts every JSON
primitive, including Boolean and null, once and never counts an object key.
Every color value is lowercase six-digit `#rrggbb`; tuples become arrays; sets
and unordered iteration are forbidden.

Use these exact predecessor sequences:

```text
P = (amber, blue, cobalt, coral, cyan, fuchsia, gray, green, indigo, lime,
     orange, pink, purple, red, rose, sky, tangerine, teal, violet, yellow)
M = (afterglow, aurora, blaze, canopy, glacier, haze, iris, lagoon, lava)
D = (blue_orange, blue_red, cyan_red, gray_blue, gray_red, green_purple,
     indigo_amber, purple_orange, teal_amber, teal_rose, violet_lime)
C = (hue, halo, corona)
Q = (trustworthy, vivid, neon, pastel, dusty, ember, earth, jewel, forest,
     teal_accent, coral_accent, octave, octave_print)
F = P + M + D + C + Q
K = (afterglow, amber, aurora, blaze, blue, blue_orange, blue_red, canopy,
     cobalt, coral, corona, cyan, cyan_red, fuchsia, glacier, gray, gray_blue,
     gray_red, green, green_purple, halo, haze, hue, indigo, indigo_amber,
     iris, lagoon, lava, lime, orange, pink, purple, purple_orange, red, rose,
     sky, tangerine, teal, teal_amber, teal_rose, violet, violet_lime, yellow)
```

`palette` is an object with exactly the `P` keys and ten hex values per key,
read from exact predecessor `_generated.PALETTE`. `cycles` has exactly
`octave` and `octave_print`, each with eight hex values from
`_generated.CYCLES`. `cmaps_256` has exactly the `K` keys and 256 hex values per
key from `_generated.CMAPS_256`. `curated_rows` has exactly the 15
`_curated.CURATED` keys `(trustworthy, vivid, neon, pastel, dusty, ember,
earth, jewel, forest, teal_accent, coral_accent, blue_red, blue_orange,
teal_amber, green_purple)`, each with eight values. `diverging_canonicals` has
exactly the `D` keys and the eight-value rows exposed by predecessor
`_discrete.DIVERGING_CANONICALS`. Source mapping encounter order is checked
before canonicalization; any order exposed publicly is retained independently
by an array surface below.

`semantic_coordinates` is an object with exactly locale keys `default` and
`kr`; each locale has exactly token keys `dc.pos`, `dc.neg`, `dc.ref`, and
`dc.hl`, whose values are two-element `[family,index]` arrays. Its exact value
is:

```text
default: dc.pos=[green,6], dc.neg=[red,6],  dc.ref=[gray,6], dc.hl=[violet,6]
kr:      dc.pos=[red,5],   dc.neg=[blue,6], dc.ref=[gray,6], dc.hl=[violet,6]
```

`semantic_colors` has the identical locale/token keysets and resolves those
coordinates through `palette`: default is `dc.pos=#40bf59`,
`dc.neg=#fb5b5e`, `dc.ref=#74797f`, `dc.hl=#926fff`; `kr` uses
`dc.pos=#ff7879`, `dc.neg=#2d99f0`, `dc.ref=#74797f`, and `dc.hl=#926fff`.
Runtime extraction must use a fresh isolated process and exercise the public
`dm.style.use("scientific")` and then `dm.style.use("report-kr")` paths; static
extraction parses `_semantic.py`, `_generated.py`, and `style.py`. In both
locale rows the observed token order must equal predecessor
`SEMANTIC_TOKEN_NAMES = (dc.pos, dc.neg, dc.ref, dc.hl)` before object
canonicalization. Reverse coordinate lookup is permitted only after proving
each observed semantic hex has exactly one coordinate in `palette`.

`dark_cycle_coordinates` is exactly
`[[blue,3],[orange,3],[green,9],[pink,6],[amber,6],[violet,5],[cyan,6]]`, parsed
from `asset/mplstyle/theme-dark.mplstyle` in cycler order. `dark_cycle` is
exactly `[#8acbff,#ffc381,#338a3f,#ef5389,#fb9600,#a386ff,#22a6ba]`; runtime
extraction obtains it from a fresh `dm.style.use("dark")` call and static
extraction resolves the seven style tokens through `palette`.

`taxonomy` is a 56-element array equal to the predecessor public
`dm.list_colors()` result. Every row is an object with exactly `name`, `kind`,
`continuous`, and `discrete_size`; the runtime source dictionaries must expose
those keys in that order before canonicalization, and row order is exactly
`F`. Sequential rows have `kind="sequential", continuous=true,
discrete_size=10`; multi-hue rows have `"multi-hue",true,null`; diverging rows
have `"diverging",true,8`; cyclic rows have `"cyclic",true,null`; and
qualitative rows have `"qualitative",false,8`. Filtered public calls for every
kind must equal the corresponding order-preserving subset of this complete row
array.

`registrations` is the ordered array of the 99 names returned by filtering a
fresh predecessor `matplotlib.colormaps` iteration for prefix `dc.`. For each
`f` in `K`, the two consecutive names are exactly `"dc." + f` and
`"dc." + f + "_r"`; `_r` is one literal suffix appended after the complete
family name, including a family name that already contains underscores. The
forward row equals `cmaps_256[f]` and the reverse row equals
`list(reversed(cmaps_256[f]))`. After those 86 entries come only `dc.octave`,
`dc.octave_print`, and `dc.<q>` for the first eleven members of `Q`, in that
order. None of those thirteen names has a registered `_r` partner, and no
other `dc.` colormap name is present. Before emission, every entry must be a
`ListedColormap` with its own registered name and `N` equal to its source-row
length; converting `.colors` through `matplotlib.colors.to_hex` must reproduce
the corresponding `cmaps_256`, `cycles`, or `curated_rows` row. The public
`dm.colors(q, reverse=True)` path may synthesize an unregistered
`ListedColormap` whose `.colors` is the reversed qualitative row; it must not
register `dc.<q>_r` or alter this 99-name registry.

`typing_literals` is an object with exactly `DartworkColor` and
`DartworkColormap`. Values are the ordered Literal-argument arrays obtained
both from a static AST parse of `_typing.py` and from `typing.get_args` in the
isolated predecessor runtime. They contain exactly 1,272 and 99 unique strings
respectively and are strictly increasing in Python string order.
`DartworkColormap` equals `sorted(set(registrations))`. `DartworkColor` has
exact prefix counts `ad.=130`, `cu.=100`, `dc.=380`, `md.=190`, `oc.=140`,
`pr.=90`, and `tw.=242`; its set equals the 892 `vendor_colors` keys plus the
380 predecessor `dc.` named-color keys. Those 380 are exactly 200 palette
tokens, 120 curated-row tokens, 56 tokens from the seven non-curated diverging
canonicals, and the four semantic token names; cycle names such as
`dc.octave0` are absent.

`mcp_discovery` has exactly two members. `palette_colors` is an array of 1,272
`[name,hex]` pairs preserving the iteration order of the duplicate-rejecting
JSON object returned by a fresh invocation of resource
`dartwork-mpl://palette/colors`. `list_color_families` is a seven-row array in
the exact object-member order returned by tool `list_color_families`; each row
is an object with exactly `name`, `count`, and `sample`, where `sample` is the
ordered five-pair projection of the returned sample object. Names/counts are
`(dc,380),(oc,140),(tw,242),(md,190),(ad,130),(cu,100),(pr,90)`. Exact samples
are:

| Name | Five ordered sample pairs |
|---|---|
| `dc` | `amber0..4`: `#fbf3df,#f9e7bf,#fbda9b,#fecc75,#ffbb50` |
| `oc` | `gray0..4`: `#f8f9fa,#f1f3f5,#e9ecef,#dee2e6,#ced4da` |
| `tw` | `slate50,100,200,300,400`: `#f8fafc,#f1f5f9,#e2e8f0,#cbd5e1,#94a3b8` |
| `md` | `red50,100,200,300,400`: `#ffebee,#ffcdd2,#ef9a9a,#e57373,#ef5350` |
| `ad` | `red1..5`: `#fff1f0,#ffccc7,#ffa39e,#ff7875,#ff4d4f` |
| `cu` | `red50,100,200,300,400`: `#fed7d7,#feb2b2,#fc8181,#f56565,#e53e3e` |
| `pr` | `blue0..4`: `#cae8ff,#a5d0ff,#79c0ff,#58a6ff,#388bfd` |

Every sample name includes its row prefix. The complete pair mapping equals
`typing_literals.DartworkColor` by name and equals the union of
`vendor_colors`, predecessor `dc.` token rows, and the default semantic row by
value. Calling MCP tool `get_color_value(name)` for every pair must return its
exact hex. Both registered endpoint identities must exist; extractors call the
captured predecessor endpoints and may not regenerate their answers from a
candidate registry. A duplicate-detecting ordered JSON decoder is required
before conversion to the pair/row arrays; raw indentation is nonsemantic.
Extraction occurs in a fresh process immediately after root package import,
which performs eager color/colormap/default-semantic registration, and before
any `style.use` call. It is the first stateful block in extractor A's fixed
order; semantic and dark-cycle mutations occur only after these pairs are
sealed in memory and cannot be consulted to revise them. Extractor B never
shares this mutable registry.

`public_inventory` is the exact 88-element ordered array
`list(dartwork_mpl.__all__)`, independently obtained by literal-AST parsing of
root `src/dartwork_mpl/__init__.py`. Its exact value is:

```text
EXPERIMENTAL, Config, config, Color, color, colors, cspace, hex, list_colors,
oklab, oklch, rgb, set_colors, show_colors, ensure_contrast,
readable_text_color, icon_font, icon_font_path, list_icon_fonts, Style,
list_styles, load_style_dict, style, style_path, AGENT_DOCS, agent_doc_path,
get_agent_doc, dpi, fs, fw, lw, adopt_axis_label_font, simple_layout,
tight_crop, get_bounding_box, mix_colors, pseudo_alpha, cm, inch, mm, pt,
length, col1, col2, Length, figsize, figsize_grid, list_aspect_tokens, tokens,
make_offset, set_decimal, format_axis_millions, format_axis_myriad,
format_axis_year, format_axis_billions, format_axis_currency, format_axis_si,
recommend_tick_decimals, rotate_tick_labels, avoid_tick_overlap, save_formats,
save_and_show, show, annotate_value, annotate_corner, label_axes, label_hline,
place_legend, wrap_axis_label, wrap_axis_labels, arrow_axis, prompt_path,
get_prompt, list_prompts, copy_prompt, find_template, validate_figure,
validate_with_fixes, validate_fixes, validate_data, make_palette,
optimize_legend, suggest_chart_type, check_figure_quality, lint_code,
migrate_legacy_code, plot_diverging_bar, plot_fonts
```

The captured MCP `dartwork-mpl://api/index` result must equal
`sorted(public_inventory)` after duplicate-rejecting JSON parsing.

`discrete_hex` and `reverse_discrete_hex` are objects with exactly the `F`
keys. Each family value is an object whose exact decimal-string keyset is
`1..10` for sequential, `1..8` for multi-hue, `1..9` for diverging, `1..24`
for cyclic, or `1..8` for qualitative; each value at key `str(n)` is an
n-element hex array. Extraction enumerates `n` numerically even though
canonical object serialization sorts string keys by UTF-8. Rows equal the
public `dm.colors(f,n=n,reverse=False/True)` results, and every reverse row
equals `list(reversed(forward_row))`. Static extraction independently replays
the exact predecessor `_discrete.py` branches: sequential ladder rules,
diverging canonical/center rules, cyclic LUT positions `floor(i*256/n)`, and
qualitative prefixes of `cycles` or `curated_rows`.

`multi_hue_discrete_indices` has exactly the `M` keys and nested decimal keys
`1..8`. Every n-row is an n-element strictly increasing non-Boolean integer
array in `[0,255]`, recorded by selector-position instrumentation at original
predecessor choice time and independently reproduced by static selector replay.
Extractor A uses a read-only Python trace on the exact predecessor selector:
for `n=1` it records `data.indices[len(data.hexes)//2]` in `_multi_hue`; for
`n=2..8`, at `_multi_hue_tuple`'s return event it records
`tuple(data.indices[i] for i in best)` from that frame. The trace may observe
but may not replace locals, return values, functions, modules, or LUT rows; the
unmodified public return must still equal the corresponding discrete hex row.
Extractor B returns the original LUT indices directly from its independent
static replay of the candidate-domain and clique selection.
For every element,
`cmaps_256[f][index[i]] == discrete_hex[f][str(n)][i]`. An extractor must never
recover an index afterward with `.index(hex)`, because duplicate quantized LUT
values make that inverse ambiguous.

`vendor_colors` is an object with exactly 892 unique keys and lowercase hex
values, built independently from the six exact predecessor assets using
prefixes/counts `oc.=140`, `tw.=242`, `md.=190`, `ad.=130`, `cu.=100`, and
`pr.=90`. OpenColor uses the predecessor non-comment `name:value` line parser;
each JSON asset uses its ordered `(weight,hex-without-#)` pairs and predecessor
normalization `name.lower().replace(" ","")`. A name collision, malformed
source row, wrong prefix count, or value outside lowercase six-digit hex fails;
repeated hex values under different names are allowed.

These are the exact nested grammars, derivation roots, independent public
observations, and terminal-leaf counts:

| Surface | Exact JSON grammar | Exact predecessor source / independent runtime observation | Leaf count |
|---|---|---|---:|
| `palette` | `{family:[hex×10]}` with exactly `P` | `src/dartwork_mpl/_colors/_generated.py:PALETTE`; exact module symbol plus named-token resolution | 200 |
| `cycles` | `{octave:[hex×8],octave_print:[hex×8]}` | `_generated.CYCLES`; `dm.colors(name,n=8)` | 16 |
| `cmaps_256` | `{family:[hex×256]}` with exactly `K` | `_generated.CMAPS_256`; `mpl.colormaps["dc."+family].colors` through `to_hex` | 11,008 |
| `curated_rows` | `{family:[hex×8]}` with the exact 15-key set above | `_curated.CURATED`; named tokens `dc.<family>0..7` | 120 |
| `diverging_canonicals` | `{family:[hex×8]}` with exactly `D` | `_discrete.DIVERGING_CANONICALS`; `dm.colors(family,n=8)` | 88 |
| `semantic_coordinates` | `{default:{token:[family,index]},kr:{token:[family,index]}}`, four tokens per locale | `_semantic.py` plus `_generated.PALETTE`; public style calls and unique-coordinate resolution | 16 |
| `semantic_colors` | `{default:{token:hex},kr:{token:hex}}`, identical keys | public style calls plus named-color mapping | 8 |
| `dark_cycle_coordinates` | `[[family,index]×7]` | `theme-dark.mplstyle`; public dark style and unique-coordinate resolution | 14 |
| `dark_cycle` | `[hex×7]` | public dark-style `axes.prop_cycle`, in cycler order | 7 |
| `taxonomy` | `[{name:str,kind:str,continuous:bool,discrete_size:int-or-null}×56]` | `_families.FAMILIES`; exact `dm.list_colors()` and each kind filter | 224 |
| `registrations` | `[registered_name×99]` | `_register._register`; fresh filtered `mpl.colormaps` iteration and row resolution | 99 |
| `typing_literals` | `{DartworkColor:[str×1272],DartworkColormap:[str×99]}` | AST of `_typing.py`; `typing.get_args` | 1,371 |
| `mcp_discovery` | `{palette_colors:[[name,hex]×1272],list_color_families:[{name,count,sample:[[name,hex]×5]}×7]}` | captured predecessor resource/tool; every entry through `get_color_value` | 2,628 |
| `public_inventory` | `[name×88]` | root `__init__.py:__all__`; `list(dm.__all__)`; MCP API-index cross-check | 88 |
| `discrete_hex` | `{family:{decimal_n:[hex×n]}}` with exact `F`/kind n-keysets | static `_discrete.py` replay; `dm.colors(...,reverse=False)` | 3,287 |
| `reverse_discrete_hex` | same grammar and keysets | `dm.colors(...,reverse=True)` and exact reversal | 3,287 |
| `multi_hue_discrete_indices` | `{family:{decimal_n:[int×n]}}`, exact `M`, n=`1..8` | choice-time selector instrumentation plus independent static replay | 324 |
| `vendor_colors` | `{prefixed_name:hex}` with exactly 892 keys | six assets plus `_loader` normalization; named-color mapping | 892 |

Every extractor validates these exact keysets, types, sequences, counts, and
cross-surface equalities before it may emit its candidate. Dedicated bootstrap
schema tests mutate every nested key/type/order/count and every cross-link:
semantic coordinate to palette; dark coordinate to palette; registration to
continuous/cycle/curated rows; typing names to registration/vendor/`dc.` token
sets; MCP pairs to typing/vendor/default semantic and registered endpoint;
public inventory to MCP API index; every forward/reverse discrete row; every
multi-hue index to LUT and forward row; and every vendor prefix count. The
existing predecessor behavior tests remain independent observations rather
than asset authority.

`surface_hashes` is an array in `surface_order`; each record has exactly
`surface_id`, `count`, and `canonical_sha256`. Count is the number of terminal
scalar leaves in that surface. Its hash is SHA-256 of
`b"dartwork-mpl-legacy-v5-surface-v2\0" + surface_id.encode("ascii") + NUL +
canonical_json(surfaces[surface_id])`. Every extractor-evidence surface row
must equal it. `compatibility_payload_sha256` hashes
`b"dartwork-mpl-color-compatibility-v2\0"` plus canonical JSON of the complete
object with only that field omitted. The tracked file is those canonical JSON
bytes plus one LF. No review/acceptance hash appears inside the scientific
asset.

The sibling target
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/color_v5_baseline_acceptance.json`
has schema `dartwork-mpl-legacy-v5-baseline-acceptance-v1` and exactly:

```text
schema, normative_predecessor_commit, baseline_tree_sha256,
preinstall_execution_snapshot_sha256,
preinstall_snapshot_archive_path, preinstall_snapshot_archive_sha256,
compatibility_path, compatibility_raw_sha256,
compatibility_payload_sha256, surface_order, surface_hashes_sha256,
extractor_a_evidence_sha256, extractor_b_evidence_sha256,
cross_extraction_sha256,
preinstall_subject_manifest_sha256,
reviewer_a_report_sha256, reviewer_b_report_sha256,
reviewer_a_execution_inputs_sha256, reviewer_b_execution_inputs_sha256,
reviewer_a_control_bundle_sha256, reviewer_b_control_bundle_sha256,
reviewer_a_evidence_bundle_sha256, reviewer_b_evidence_bundle_sha256,
reviewer_a_completion_token, preinstall_review_sequence_sha256,
maintainer_approval, promotion_provenance, acceptance_sha256
```

Every predecessor, snapshot, candidate, evidence, report, token, sequence, and
promotion link is independently reparsed through sections 3.6 and 10 rather
than accepted as a hash-shaped string. `compatibility_path` is the literal
sibling path above, raw and payload hashes reproduce its exact reviewed bytes,
and `surface_hashes_sha256` hashes
`b"dartwork-mpl-legacy-v5-surface-hashes-v1\0"` plus canonical JSON of its
complete ordered `surface_hashes`. `cross_extraction_sha256` is independently
recomputed from the unique archived `baseline-cross-extraction-manifest`, whose
selected candidate identity must equal the installed compatibility bytes.
`maintainer_approval` is the canonical closed approval object and
`promotion_provenance` is the complete archive-promotion record; neither
contributes arbitrary prose or private transport.
`preinstall_execution_snapshot_sha256` equals the snapshot nested in the unique
archived preinstall execution-snapshot manifest.
`preinstall_snapshot_archive_path` is not caller supplied: it is the canonical
repo-relative path formed from the parent directory of
`promotion_provenance.promotion_input_manifest_path` plus the `blob_path`
selected by the unique `reviewed-execution-snapshot-archive-manifest` role in
that promotion-input bundle, and
`preinstall_snapshot_archive_sha256` is the independently recomputed semantic
self-hash of those bytes. Every distinct archive leaf named by that manifest
must likewise resolve through the corresponding closed promotion-bundle role.
`acceptance_sha256` hashes
`b"dartwork-mpl-legacy-v5-baseline-acceptance-v1\0"` plus canonical JSON with
only that field omitted. The acceptance points to the scientific asset and the
complete earlier review closure; the asset never points back, so the authority
graph is acyclic. This acceptance completes the preinstall-promotion byte
transfer; it does not yet prove that promotion A/B occurred. A self-hashed
asset, an acceptance without the archived preinstall closure, either file on
its own, or even the exact pair committed before promotion B has zero baseline
authority.

For the preinstall-acceptance lifecycle, `maintainer_approval` has exactly
`approval_ref`, `walkthrough_subject_sha256`, `review_sequence_sha256`, and
`independence_attested`. `approval_ref` matches
`maintainer-approval-[0-9a-f]{32}`, `review_sequence_sha256` equals
`preinstall_review_sequence_sha256`, and `independence_attested` is the Boolean
true. Its walkthrough hash is exactly:

```text
SHA256(
    b"dartwork-mpl-legacy-v5-baseline-maintainer-walkthrough-v1\0" +
    canonical_json({
        "normative_predecessor_commit": normative_predecessor_commit,
        "baseline_tree_sha256": baseline_tree_sha256,
        "preinstall_subject_manifest_sha256":
            preinstall_subject_manifest_sha256,
        "compatibility_raw_sha256": compatibility_raw_sha256,
        "compatibility_payload_sha256": compatibility_payload_sha256,
        "cross_extraction_sha256": cross_extraction_sha256,
        "extractor_a_evidence_sha256": extractor_a_evidence_sha256,
        "extractor_b_evidence_sha256": extractor_b_evidence_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "review_sequence_sha256": preinstall_review_sequence_sha256,
        "common_execution_snapshot_sha256":
            preinstall_execution_snapshot_sha256,
        "reviewed_execution_snapshot_archive_sha256":
            preinstall_snapshot_archive_sha256,
    })
)
```

The four-key approval object is written create-only as canonical JSON plus one
LF at
`build/color-authoring/maintainer-approvals-v1/<raw_sha256>.json`, where the
filename is the plain SHA-256 of those complete bytes. Promotion captures that
exact regular file under `maintainer-approval`. The walkthrough preimage
deliberately contains no `approval_ref`, acceptance hash, promotion-input hash,
`promotion_provenance`, or future promotion-review hash, so the graph remains
acyclic.

The acceptance deliberately binds the completed preinstall A/B sequence, not
its own not-yet-run promotion review: embedding future promotion-report hashes
would create a self-reference. Fresh promotion A/B instead reviews the proposed
asset/acceptance pair and its complete external closure. The promotion subject,
A/B reports, and common snapshot likewise cannot point to an object emitted
only after B. The pair therefore cannot certify its own promotion merely by
being self-consistent.

The post-promotion archive root is exactly:

```text
docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/
  legacy-v5-baseline-review-v1/promotion-review/
    subjects/<subject_manifest_sha256>/manifest.json
    reports/<report_sha256>.json
    input-bundles/<bundle_sha256>/manifest.json
    input-bundles/<bundle_sha256>/blobs/<raw_sha256>
    review-controls/<bundle_sha256>/manifest.json
    review-controls/<bundle_sha256>/blobs/<raw_sha256>
    review-evidence/<bundle_sha256>/manifest.json
    review-evidence/<bundle_sha256>/blobs/<raw_sha256>
    execution-snapshots/<archive_sha256>/manifest.json
    execution-snapshots/<archive_sha256>/blobs/<raw_sha256>
    approvals/<raw_sha256>.json
```

The finalizer copies exactly one promotion subject manifest; promotion A and B
reports; both historical external-input, review-control, and review-evidence
manifests plus every distinct blob each declares; the A completion token
through B's control bundle; and the one common complete execution-snapshot
archive. It also copies its own role-complete finalization input bundle and the
post-promotion approval. All JSON is strict canonical JSON plus one LF; paths
are derived from independently recomputed semantic or raw hashes, never caller
supplied. An extra, missing, aliased, non-canonical, stale, or hash-only leaf is
fatal. The finalizer reparses both reports as PASS, reconstructs their
different execution inputs, controls, evidence, B predecessor link and A
completion token, recomputes the review sequence, and requires every reviewed
source byte to equal the unchanged promotion subject and common snapshot.

The final authority target is exactly
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/color_v5_baseline_authority.json`.
It has schema `dartwork-mpl-legacy-v5-baseline-authority-v1` and exactly:

```text
schema,
compatibility_path, compatibility_raw_sha256,
compatibility_payload_sha256,
acceptance_path, acceptance_raw_sha256, acceptance_sha256,
promotion_subject_manifest_path, promotion_subject_manifest_sha256,
promotion_execution_snapshot_sha256,
promotion_snapshot_archive_path, promotion_snapshot_archive_sha256,
reviewer_a_report_sha256, reviewer_b_report_sha256,
reviewer_a_execution_inputs_sha256, reviewer_b_execution_inputs_sha256,
reviewer_a_control_bundle_sha256, reviewer_b_control_bundle_sha256,
reviewer_a_evidence_bundle_sha256, reviewer_b_evidence_bundle_sha256,
reviewer_a_completion_token, promotion_review_sequence_sha256,
postpromotion_approval_path, postpromotion_approval_raw_sha256,
postpromotion_maintainer_approval, authority_finalization_provenance,
authority_marker_sha256
```

The compatibility and acceptance paths are the two literal targets above, and
their raw and semantic hashes must reproduce the promotion subject. The
promotion subject path is exactly
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/legacy-v5-baseline-review-v1/promotion-review/subjects/<promotion_subject_manifest_sha256>/manifest.json`.
`promotion_snapshot_archive_path` is the same fixed root followed by
`execution-snapshots/<promotion_snapshot_archive_sha256>/manifest.json`, and
`postpromotion_approval_path` is that root followed by
`approvals/<postpromotion_approval_raw_sha256>.json`. Report paths are
analogously derived as `promotion-review/reports/<matching-report-sha256>.json`;
every bundle path is derived by the displayed archive layout. All report,
execution-input, control, evidence, token, sequence, source-fingerprint, and
snapshot fields are independently recomputed from those tracked bytes. The
snapshot archive's nested execution-snapshot hash must equal
`promotion_execution_snapshot_sha256`, which in turn must equal the subject
and both reports. `authority_finalization_provenance` is section 3.5's complete
archive-promotion provenance for kind `legacy-v5-baseline-authority`; its
tracked input bundle contains exactly the promotion review closure and approval
just described and resolves every copied target byte.

Marker reachability is structural, not directory-name inference. It starts at
the three fixed asset/acceptance/marker paths; follows the subject, report,
snapshot, approval, and finalization-provenance fields above; follows each
strict manifest's declared blobs and each report's execution/control/evidence
links; and follows the acceptance into the preinstall archive. The verifier
independently derives that finite path set, enumerates both tracked archive
roots, and requires set equality. Thus an unreferenced extra leaf is fatal just
like a missing leaf, while an ambient directory entry cannot silently become an
authority edge.

Every reached tracked leaf is a regular `100644` file. Its full Git blob OID is
recomputed from the exact raw bytes under the capsule's recorded object format;
the later `S_A(p)` check binds that mode, OID, and raw SHA-256 in the authority
tree. No caller-provided blob ID or filesystem mode substitutes for that check.

`postpromotion_maintainer_approval` has exactly `approval_ref`,
`walkthrough_subject_sha256`, `review_sequence_sha256`, and
`independence_attested`. The reference matches
`maintainer-approval-[0-9a-f]{32}`, the sequence equals
`promotion_review_sequence_sha256`, and independence is the Boolean true. Its
walkthrough hash is exactly:

```text
SHA256(
    b"dartwork-mpl-legacy-v5-baseline-postpromotion-maintainer-walkthrough-v1\0" +
    canonical_json({
        "compatibility_raw_sha256": compatibility_raw_sha256,
        "compatibility_payload_sha256": compatibility_payload_sha256,
        "acceptance_raw_sha256": acceptance_raw_sha256,
        "acceptance_sha256": acceptance_sha256,
        "promotion_subject_manifest_sha256":
            promotion_subject_manifest_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "reviewer_a_execution_inputs_sha256":
            reviewer_a_execution_inputs_sha256,
        "reviewer_b_execution_inputs_sha256":
            reviewer_b_execution_inputs_sha256,
        "reviewer_a_control_bundle_sha256":
            reviewer_a_control_bundle_sha256,
        "reviewer_b_control_bundle_sha256":
            reviewer_b_control_bundle_sha256,
        "reviewer_a_evidence_bundle_sha256":
            reviewer_a_evidence_bundle_sha256,
        "reviewer_b_evidence_bundle_sha256":
            reviewer_b_evidence_bundle_sha256,
        "reviewer_a_completion_token": reviewer_a_completion_token,
        "promotion_review_sequence_sha256":
            promotion_review_sequence_sha256,
        "common_execution_snapshot_sha256":
            promotion_execution_snapshot_sha256,
        "reviewed_execution_snapshot_archive_sha256":
            promotion_snapshot_archive_sha256,
    })
)
```

The producer writes that four-key approval create-only as canonical JSON plus
one LF at
`build/color-authoring/maintainer-approvals-v1/<raw_sha256>.json`; the finalizer
captures it under `maintainer-approval` and copies it to the canonical tracked
`postpromotion_approval_path`. Its plain raw-file SHA-256 must equal both the
filename and `postpromotion_approval_raw_sha256`, and its parsed value must
equal the marker's nested object. The walkthrough deliberately excludes its own
reference, approval raw/path fields, finalization provenance, and marker fields,
so the graph is acyclic.

`authority_marker_sha256` is exactly:

```text
SHA256(
    b"dartwork-mpl-legacy-v5-baseline-authority-v1\0" +
    canonical_json(marker with only authority_marker_sha256 omitted)
)
```

For phase ordering, “promotion-review archive” means the `subjects`, `reports`,
`input-bundles`, `review-controls`, `review-evidence`, and
`execution-snapshots` subtrees; the canonical `approvals/<raw_sha256>.json`
leaf is the next phase even though the finalizer's own immutable input bundle
necessarily carries that same approval as an input blob. Publication order is
the complete tracked promotion-review archive, then the tracked
post-promotion approval, one full prerequisite durability barrier, and
the authority marker last, followed by the marker's file-and-directory barrier.
An exact archive subset, or a complete archive plus approval with the marker
absent, is resumable but non-authoritative. A marker with any missing or
differing prerequisite is corruption. Neither the approval nor marker claims
to be a third scientific review; both are independently recomputable bindings
of the already completed promotion A/B sequence.

That later baseline-authority HEAD is a full lowercase commit ID selected only
after promotion Reviewer B has passed on the unchanged promotion capsule and
the finalizer has durably published the exact closure above. Because the commit
does not yet exist while either the acceptance or marker is constructed, it is
embedded in neither. The compatibility-migration batch records it as
`baseline_authority_commit` in the v6 `baseline` record and every shipped-
compatibility authority record. Let `A` be that commit, let `H` be
`execution_snapshot.source_fingerprint.head_sha` (equal to the Git capsule's
`head_commit_oid`), and let `P` contain the compatibility, acceptance, and
authority-marker paths plus every regular leaf transitively reached by the
strict acceptance or marker, including the complete preinstall and promotion-
review archives and tracked approval.
For commit `C`, define `S_C(p)` as `(git_mode, full_blob_oid,
sha256(raw_blob_bytes))`. Both `A` and `H` must resolve as full lowercase
commits in the capsule's one recorded Git object format. The compatibility-
migration batch requires `A == H`.
Every later consumer requires an offline-verified **first-parent** chain proving
`A` is a first-parent ancestor of or equal to `H`: starting at `H`, each next
OID is exactly the first literal `parent` header in the current raw commit
payload, and traversal must reach `A` before a parentless commit. This rule is
deliberately narrower than general Git ancestry so a closed capsule has one
locally verifiable path in merge histories without capturing an unbounded
ancestry DAG. Operationally, `A` must therefore be selected as the post-
integration commit on the intended first-parent release line, not as a topic-
branch commit that later appears only as a merge's secondary parent. A history
policy that cannot retain that line must fail or create and review a new
authority version; general reachability is not silently substituted. It
additionally requires the acceptance-and-marker-prescribed `S_A(p)` for
every `p in P`, `S_H(p) == S_A(p)`, and `I[p] == W[p] == H[p]` with no overlay.
Unrelated paths may change. Presence at a byte-identical but unrelated commit,
a commit reachable only through a non-first merge parent, a branch/ref/replace
object, or the live worktree grants no authority.

## 2. Baseline evidence and design hazards

### 2.1 The shipped result must be protected before migration

The baseline-capture batch must establish a comparison contract covering 18
exact surfaces, including 200
palette colors, two cycles, all curated/manual rows, 43×256 = 11,008 continuous
LUT positions, every forward and reverse discrete form, all 72 predecessor-
computed multi-hue result/index rows that migration will freeze,
registrations, typing/MCP discovery, semantic colors, and 892 vendor colors.

Those predecessor results are public behavior. No later migration or authoring
batch may alter their names, order, values, hashes, or generated metadata. The
contract becomes authority only after promotion A/B completes, its closure and
post-promotion approval are durably archived behind the authority marker, and
the complete marker-reachable set is integrated into the later authority
commit; this document does not pretend the not-yet-created JSON is already
accepted.

### 2.2 A shipped compatibility boundary is not a generic objective

The compatibility-migration batch may introduce a shipped-only boundary that
reproduces the predecessor through two independent operations:

1. find one `L` at the fixed probe chroma `C=0.04`, using the mapped output; and
2. hold that `L` fixed while searching raw-sRGB chroma.

That behavior is admissible only if exact comparison proves it replays the
predecessor catalog. It is not the geometric solution to:

```text
maximize C
subject to there exists L such that
    raw_linear_sRGB(OKLCH(L, C, h)) is in [0, 1]^3
    modeled_relative_Y(raw_linear_sRGB) = target_Y
```

The mismatch follows directly from the specified two-stage compatibility
algorithm and the objective: one fixed-`L` slice cannot establish a maximum
over all admissible `L`. Quantitative
compatibility-versus-boundary values are deliberately not asserted here. The
implementation batch must add `scripts/characterize_oklab_authoring.py` and
generate ignored
`build/color-system-comparison/oklab-authoring-characterization/` from its
reviewed solver. The output separates a reproducible scientific payload from
per-invocation provenance. The payload records the complete hue/target grid,
compatibility and generic policy records, exact-oracle algorithm and root-
isolation records, per-point witnesses, catalog/LUT difference counts, and its
payload hash. A separate public evidence envelope records the seven-value source
fingerprint, source snapshot, invocation-input bundle, path-neutral environment,
invocation recipe, and repo-relative script/kernel hashes and is written last
as the completion marker; raw command/host/path transport stays private. After
the ignored candidate payload and generation evidence pass a pre-install A→B
review, the payload is installed create-only at
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/fixed-y-characterization.json`,
a new post-install source snapshot must regenerate the payload in a process
whose declared inputs exclude that tracked expected file; a second verifier
process then compares the sealed output with the expected bytes. Invocation
evidence is not a byte-reproduction target. No numerical claim enters normative
documentation before that post-install reproduction and tracked payload pass
their own distinct A→B review.

After compatibility migration is accepted, replacing that helper in the
shipped call graph is forbidden independently of the size of the mismatch: the
catalog is an exact byte contract, not an invitation to silently substitute a
more general objective.

### 2.3 Frozen replay and new-family selection are both target behavior

The predecessor runtime computes multi-hue selections; it does not contain
`MULTI_HUE_DISCRETE_INDICES`. Compatibility migration must first capture those
results and replay accepted frozen indices. Authoring must then add a separate
OKLab/OKLCH selector for an unpinned new family, followed by CIEDE2000/CVD
validation. Neither target behavior is treated as present in the baseline.

After compatibility migration, manifest absence must mean corruption or
incomplete admission, not permission to optimize at runtime.

## 3. Decision summary

Adopt one immutable shipped lane and one explicit authoring lane.

### 3.1 Shipped compatibility lane

- The compatibility-migration batch introduces a mapped-Y solver, mapped
  renderer, and 30-probe + 22-probe chroma algorithm under these exact names.
  They acquire immutable shipped status only after the accepted baseline proves
  exact predecessor replay:

  ```python
  SHIPPED_TONE_COMPATIBILITY_POLICY: ShippedToneCompatibilityPolicy

  _solve_oklch_l_for_relative_y_shipped_compat(
      hue_deg: float,
      chroma: float,
      target_y: RelativeY,
      policy: ShippedToneCompatibilityPolicy =
          SHIPPED_TONE_COMPATIBILITY_POLICY,
  ) -> SolvedColor

  _render_oklch_at_neutral_tone_shipped_compat(
      *,
      neutral_tone_value: NeutralTone,
      chroma: float,
      hue_deg: float,
      policy: ShippedToneCompatibilityPolicy =
          SHIPPED_TONE_COMPATIBILITY_POLICY,
  ) -> Rgb

  _max_chroma_at_neutral_tone_shipped_compat(
      hue_deg: float,
      neutral_tone_value: NeutralTone,
      policy: ShippedToneCompatibilityPolicy =
          SHIPPED_TONE_COMPATIBILITY_POLICY,
  ) -> float
  ```

  The compatibility value types and result are closed:

  ```python
  RelativeY = NewType("RelativeY", float)
  NeutralTone = NewType("NeutralTone", float)

  @dataclass(frozen=True, slots=True)
  class SolvedColor:
      rgb: tuple[float, float, float]
      oklab_l: float
      requested_chroma: float
      mapped_chroma: float
      achieved_y: RelativeY
      residual: float

  @dataclass(frozen=True, slots=True)
  class ShippedToneCompatibilityPolicy:
      policy_id: Literal["shipped-tone-compatibility-v1"]
      relative_y_model_id: Literal[
          "legacy-d65-srgb-y-row-white-normalized-v1"
      ]
      relative_y_observation_id: Literal[
          "legacy-mapped-encoded-srgb-to-relative-y-v1"
      ]
      relative_y_search_iterations: int
      boundary_tone_iterations: int
      boundary_chroma_iterations: int
      probe_chroma: float
      max_chroma_upper: float
      sequential_catalog_chroma_fraction: float
      gamut_map_iterations: int
      linear_gamut_tolerance: float
  ```

  `relative_y(x)` and `neutral_tone(x)` reject booleans, non-real values,
  non-finite values, negative zero, and values outside `[0,1]`; they return the
  corresponding `NewType` without changing any other binary64 bit.
  `relative_y_from_tone(t)` computes `(float(t) * float(t)) * float(t)` and
  `tone_from_relative_y(y)` computes `float(numpy.cbrt(float(y)))`, followed by
  the same validation. Endpoints are positive-zero black and exact-one white.

  The shipped-only modeled-Y observation is identified by
  `legacy-mapped-encoded-srgb-to-relative-y-v1`. Starting with the exact
  mapped encoded-sRGB triple returned after the predecessor-compatible path's
  final linear-channel clamp and exact OETF, decode each channel in `r,g,b`
  order with the
  predecessor scalar branch and operation order:

  ```text
  if encoded <= 0.04045:
      linear = encoded / 12.92
  else:
      p = (encoded + 0.055) / 1.055
      linear = p ** 2.4

  yr = 0.2126729 * linear_r
  yg = 0.7151522 * linear_g
  yb = 0.0721750 * linear_b
  legacy_raw_Y = (yr + yg) + yb
  achieved_Y = legacy_raw_Y / 1.0000001
  ```

  Each displayed arithmetic operator executes exactly once as an IEEE-754
  binary64 operation in the shown association and order. The branch comparison
  and Python binary64 power are part of the
  contract; FMA, vector reduction, reassociation, dotting the raw-linear
  channels with the separately normalized row, or observing pre-map channels
  is forbidden. The compatibility search predicate compares this
  `achieved_Y` with `target_Y`; the stored `achieved_y` is the same bit pattern
  and `residual` is its one binary64 subtraction from `target_y`. The exact-
  surface gate remains decisive because monotonic algebra alone cannot prove
  that finite-precision predicate histories reproduce the predecessor.
  Generic authoring does not use this encoded decode round trip; section 5.1
  defines its separate raw-linear normalized-row association.

  `SolvedColor` validation requires finite encoded RGB in `[0,1]`, finite
  `oklab_l` in `[0,1]`, finite nonnegative chroma with
  `mapped_chroma <= requested_chroma`, and an `achieved_y` recomputed through
  the shipped modeled-Y association. `residual` is the one binary64 subtraction
  `float(achieved_y) - float(target_y)`. The `target_y=0` and `target_y=1`
  records are respectively exact `(0,0,0)`/`L=0` and `(1,1,1)`/`L=1`, with
  zero chroma and positive-zero residual. These are compatibility records, not
  the richer generic fixed-Y certificates in section 5.

- Define every numeric field of
  `SHIPPED_TONE_COMPATIBILITY_POLICY` explicitly in the compatibility-migration
  artifact. The predecessor has no `SHIPPED_TONE_POLICY`, so this is not
  described as a rename. Once the policy passes exact replay, each function
  explicitly passes it and none may delegate to a generic authoring function.
- The compatibility-migration batch must establish this required call graph;
  any temporary boolean compiler surface used while migrating must be gone
  before acceptance:

  ```text
  _catalog.compile_candidate_snapshot()
  ├── _generate.compile_palette_shipped_compat()
  │   └── shipped renderer → shipped solver
  ├── _cmaps.compile_cmaps_shipped_compat()
  │   ├── shipped renderer → shipped solver
  │   └── shipped boundary
  └── non-shipped comparison branch
      └── compile_cmaps_shipped_unlocked_diagnostic_compat()
          ├── _render_direct_oklch_shipped_diagnostic_compat()
          └── shipped boundary
  ```

  The diagnostic branch defines the unlocked arithmetic needed for comparison
  evidence, but it has no shipped-predecessor status and its explicit name
  prevents it from posing as new-family authoring. Shared internal loops may
  accept a typed renderer callback; they may not accept a boolean that changes
  coordinate meaning.
- Never call a generic authoring primitive as a fallback for a shipped name.

#### 3.1.1 Legacy migration transform and derived policy

The standalone migration does not inherit an unnamed conversion from an
earlier draft. For each predecessor CIELAB lightness target, one migration-only
converter derives the modeled-relative-Y target and serialized
`NeutralTone`. With binary64 inputs, the exact operation sequence is:

```text
legacy_Y_white = 1.0000001

if legacy_Lstar > 8.0:
    f = (legacy_Lstar + 16.0) / 116.0
    legacy_raw_Y = (f * f) * f
else:
    legacy_raw_Y = (legacy_Lstar * 27.0) / 24389.0

target_Y = legacy_raw_Y / legacy_Y_white
neutral_tone = float(numpy.cbrt(target_Y))
```

The two branch operation IDs are the exact literals
`legacy-lstar-upper-to-modeled-relative-y-v1` and
`legacy-lstar-lower-to-modeled-relative-y-v1`. The upper ID denotes the four
assignments `f`, `legacy_raw_Y`, `target_Y`, and `neutral_tone` above and its
primitive operation trace is exactly `add 16 → divide 116 → multiply f by f →
multiply the preceding result by f → divide by legacy_Y_white → numpy.cbrt`.
The lower ID denotes the three assignments `legacy_raw_Y`, `target_Y`, and
`neutral_tone`, with trace `multiply by 27 → divide by 24389 → divide by
legacy_Y_white → numpy.cbrt`. The IDs name these exact binary64 traces and no
algebraically equivalent substitute.

Every displayed arithmetic operator executes exactly once as a binary64
operation in the shown association and order; no FMA, extended accumulator,
reassociation, algebraic replacement, or alternate power operator may replace
it. The branch comparison is exact binary64. The converter stores
the resulting binary64 values in the v6 SSOT and is forbidden from production
authoring after migration. `legacy_Y_white` is the exact sum, in source order,
of the predecessor row `(0.2126729, 0.7151522, 0.0721750)`; the target runtime
uses the separately declared normalized modeled-Y row and does not call CIELAB.
That row is formed by three independent binary64 divisions
`legacy_row[i] / legacy_Y_white` in index order, yielding exactly
`(0.21267287873271212, 0.7151521284847872, 0.07217499278250072)`; its declared
left-associated sum is exactly `1.0`. Dividing both the legacy target Y and its
row by the same white value makes white a true relative-Y endpoint. This is a
project-specific normalization of the predecessor's rounded D65-sRGB matrix,
not a claim that the coefficients or resulting values are measured display
luminance. Binary64 rounding can still perturb an intermediate comparison, so
only the complete exact-surface replay—not the algebra alone—authorizes the
compatibility implementation.

The shipped compatibility policy is introduced from exact predecessor
behavior, not renamed from a nonexistent object. Its one frozen value is:

```python
SHIPPED_TONE_COMPATIBILITY_POLICY = ShippedToneCompatibilityPolicy(
    policy_id="shipped-tone-compatibility-v1",
    relative_y_model_id="legacy-d65-srgb-y-row-white-normalized-v1",
    relative_y_observation_id="legacy-mapped-encoded-srgb-to-relative-y-v1",
    relative_y_search_iterations=40,
    boundary_tone_iterations=30,
    boundary_chroma_iterations=22,
    probe_chroma=0.04,
    max_chroma_upper=0.40,
    sequential_catalog_chroma_fraction=0.97,
    gamut_map_iterations=24,
    linear_gamut_tolerance=1e-6,
)
```

Strict loading requires the exact key set and literal IDs, rejects booleans as
integers, requires all three iteration counts and gamut-map iterations to be
positive integers, both chroma values and tolerance to be finite positive
binary64, `probe_chroma <= max_chroma_upper`, and the catalog fraction in
`(0,1]`. No omitted default or unknown policy ID is accepted.

The predecessor's cyclic paths retain their distinct captured fractions
(`0.95` or `0.96`) through recipe data; `0.97` is not generalized to them.
Every other recipe literal comes from the exact predecessor SSOT and is bound
by the baseline asset. A changed literal, operation order, iteration count, or
rounding path must reproduce every exact surface or fail compatibility
migration; matching only final prose or a subset of hex values is insufficient.
The compatibility batch leaves predecessor validation implementations and
thresholds unchanged and reruns that gate suite from the accepted exact bytes.
Those diagnostics are derived sanity checks, not separately pinned v6
observations or a second mutable baseline authority.

#### 3.1.2 Compatibility SSOT and frozen-index contract

Compatibility migration creates exactly
`src/dartwork_mpl/asset/color/color_v6_ssot.json`. Its top-level keys are:

```text
schema, baseline, coordinates, migration, policies, recipe,
multi_hue_discrete_indices, row_contracts, section_hashes,
ssot_payload_sha256
```

`schema` is `dartwork-mpl.color-ssot/v6`. `baseline` is byte-for-byte the
closed baseline record used by section 3.6's exact-surface comparator, including
`baseline_authority_commit`, compatibility payload, preinstall acceptance, and
post-promotion authority-marker identities.
`coordinates` has exactly the
keys `canonical`, `authoring`, `compatibility_output_model`, `neutral_tone`,
`relative_y_coefficients`, `migration_inputs`, and `validation_models`. Their
values are respectively `"OKLab"`, `"OKLab/OKLCH"`,
`"nominal-d65-srgb-modeled-relative-y"`,
`"cbrt(modeled-relative-y)"`, the exact array
`[0.21267287873271212,0.7151521284847872,0.07217499278250072]`,
`["CIELAB L*"]`, and `["CIELAB","CIEDE2000","Machado/BVM CVD"]`. This
distinguishes predecessor CIELAB L* as a migration input from full CIELAB as an
internal downstream diagnostic coordinate, including CIEDE2000 evaluation.
Neither is an authoring coordinate or construction objective.

`migration` has exactly these keys:

```text
legacy_coordinate, legacy_y_row, legacy_white_y, relative_y_model_id,
toe_lstar, toe_numerator, toe_denominator,
upper_operation_sequence_id, lower_operation_sequence_id,
source_records, tone_mappings, tone_mapping_plan_sha256,
retired_authoring_mechanisms, scope
```

Its fixed values are `legacy_coordinate="CIELAB L* D65"`,
`legacy_y_row=[0.2126729,0.7151522,0.0721750]`,
`legacy_white_y=1.0000001`,
`relative_y_model_id="legacy-d65-srgb-y-row-white-normalized-v1"`,
`toe_lstar=8.0`, `toe_numerator=27.0`, `toe_denominator=24389.0`,
`upper_operation_sequence_id="legacy-lstar-upper-to-modeled-relative-y-v1"`,
`lower_operation_sequence_id="legacy-lstar-lower-to-modeled-relative-y-v1"`, and
`scope="offline-v5-compatibility-provenance-only"`.
`source_records` is the UTF-8-path-sorted eight-row array below; each row has
exactly `path` and `raw_sha256` and is re-read from the normative predecessor:

| Path | Required raw SHA-256 |
|---|---|
| `docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json` | `a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518` |
| `src/dartwork_mpl/_colors/_cmaps.py` | `784d8dbc8cd6814beeced9203189fee2b4981a05caccf80b0cd32c459a3dc316` |
| `src/dartwork_mpl/_colors/_color.py` | `7dba297888150b9858537bdc3154eff4e6a9c17b91598baa171ab19c037a73df` |
| `src/dartwork_mpl/_colors/_conversion.py` | `c21f5061ada996d8726ffc0a4357d21b1602e6a801a29f738e23191d78edd261` |
| `src/dartwork_mpl/_colors/_cycles.py` | `e8a3dafe55383f91a842dc95192435cb7de7b316fb0b00403686f28561db6f76` |
| `src/dartwork_mpl/_colors/_generate.py` | `c7a800c4d3bc72684686c934bdccad14fa367e4f96052d73198a9ca281b89146` |
| `src/dartwork_mpl/_colors/_metrics.py` | `53ab7b27f7cad307d0bf4ee81e02b94fadf901730e486c91681413816f1bb435` |
| `src/dartwork_mpl/_colors/_recipe.py` | `9887efb779581bbb3bb67871ef5973489cae0ef2f5fd5c8cc8fb399135ca11af` |

In this subsection, a normative-predecessor lookup of path `P` means resolving
the unique leaf `P` from the archived preinstall execution snapshot reached
through the strict baseline acceptance, after first verifying that acceptance
as a dependency of the fixed-path post-promotion authority marker, and
requiring its recorded source state, Git mode, blob identity, and raw bytes to
equal `P` in commit
`6be8cb56b8752e03515101caa7ae2f6c52cc13dc`. The compatibility-migration HEAD,
index, worktree, ambient Git-object lookup, and any same-named candidate file
are never lookup inputs.

`tone_mappings` is a non-empty array uniquely sorted by UTF-8 `target_path`.
Each record has exactly `target_path`, `source_path`, `source_locator`,
`source_operation_id`, `legacy_lstar_float_hex`, `branch`,
`raw_y_float_hex`, `normalized_y_float_hex`, and
`neutral_tone_float_hex`. It covers every operational predecessor L* target in
palette, gray, single-hue, multi-hue, diverging, and cyclic recipes, including
the evaluated blue/red derived endpoint. `branch` is `upper` or `lower`; the
four numeric strings are canonical finite binary64 `float.hex()` values. A
strictly reconstructed V1 plan has `branch="upper"` in all 58 rows because its
minimum predecessor L* is `12.0`; `lower` remains a valid converter branch only
for the separate synthetic toe fixtures, not an accepted plan row. A
strict rebuild resolves `source_locator` only against the normative-predecessor
lookup of `source_path`. It
bit-compares `legacy_lstar_float_hex`, executes section 3.1.1 forward in the
declared operation order, and bit-compares all three result fields. It never
uses an inverse calculation as authority: cubing and cube-root rounding need
not recover the original L* bit pattern for every input.
`target_path` is an RFC 6901 pointer evaluated against the complete v6 SSOT
root and is required to resolve beneath `/recipe`. `source_operation_id` is
exactly `json-pointer-v1`, `python-ast-literal-v1`, or
`blue-red-rendered-endpoint-average-v1`; its locator is respectively an RFC
6901 pointer, the closed three-item AST locator below, or the literal
`blue_red.l_end`. Let `J` be the exact v5-SSOT path in `source_records`, let `C`
be `src/dartwork_mpl/_colors/_cmaps.py`, and let `M` be the literal module name
`dartwork_mpl._colors._cmaps`. A JSON-pointer row has `source_path=J` and the
displayed pointer string. Every AST row has `source_path=C` and serializes the
displayed `owner :: selector` as exactly `[M,owner,selector]`.

The AST selector grammar is closed. `param/<name>` selects the numeric default
of the one named parameter on the top-level owner function. `tuple-local/<name>`
selects that name's value from the one direct-body tuple-target/tuple-value
assignment. `dict/<binding>/<key>/<index>` selects the zero-based element of the
literal tuple under one string key in the uniquely named direct-body literal
dictionary. `nested/<name>/param/<parameter>` selects a default on the one
direct-child nested function. `loop/<comma-separated-targets>/<key0>/<key1>/<index>`
selects the indexed element of the unique literal tuple in the one direct-body
`for` whose tuple target has exactly those names and whose first two literal
elements equal the two keys. Each lookup requires exactly one matching AST node,
a source-level finite numeric literal, and no intervening alias or evaluation;
zero or multiple matches fail. The normalized AST inventory is built from the
archived predecessor bytes, never from line numbers or candidate code.
An AST integer literal is converted exactly once with `float(value)` before its
bits are recorded; this applies, in particular, to the ten source-integer
diverging endpoints. No decimal-string round trip participates.

The following table is the complete mapping-plan projection in unsigned UTF-8
`target_path` order. There are exactly 58 rows; no template expansion or
value-based ownership choice occurs at implementation time.

| `target_path` | `source_operation_id` | locator payload |
|---|---|---|
| `/recipe/catalog/cyclic/hue_map/neutral_tone` | `python-ast-literal-v1` | `cyclic_hue :: param/L` |
| `/recipe/catalog/cyclic/twilight/neutral_tone_center` | `python-ast-literal-v1` | `cyclic_twilight :: tuple-local/L_center` |
| `/recipe/catalog/cyclic/twilight/neutral_tone_seam` | `python-ast-literal-v1` | `cyclic_twilight :: tuple-local/L_seam` |
| `/recipe/catalog/diverging/neutral_tone_center` | `python-ast-literal-v1` | `compile_cmaps :: nested/dv/param/l_center` |
| `/recipe/catalog/diverging/rows/0/neutral_tone_end` | `blue-red-rendered-endpoint-average-v1` | `blue_red.l_end` |
| `/recipe/catalog/diverging/rows/1/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/blue/orange/2` |
| `/recipe/catalog/diverging/rows/10/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/gray/red/2` |
| `/recipe/catalog/diverging/rows/2/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/teal/rose/2` |
| `/recipe/catalog/diverging/rows/3/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/green/purple/2` |
| `/recipe/catalog/diverging/rows/4/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/purple/orange/2` |
| `/recipe/catalog/diverging/rows/5/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/cyan/red/2` |
| `/recipe/catalog/diverging/rows/6/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/teal/amber/2` |
| `/recipe/catalog/diverging/rows/7/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/violet/lime/2` |
| `/recipe/catalog/diverging/rows/8/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/indigo/amber/2` |
| `/recipe/catalog/diverging/rows/9/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: loop/a,b,le/gray/blue/2` |
| `/recipe/catalog/gray/neutral_tone_bottom` | `python-ast-literal-v1` | `seq_gray :: param/L_bot` |
| `/recipe/catalog/gray/neutral_tone_top` | `python-ast-literal-v1` | `seq_gray :: param/L_top` |
| `/recipe/catalog/multi_hue/rows/0/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/aurora/3` |
| `/recipe/catalog/multi_hue/rows/0/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/aurora/2` |
| `/recipe/catalog/multi_hue/rows/1/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/afterglow/3` |
| `/recipe/catalog/multi_hue/rows/1/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/afterglow/2` |
| `/recipe/catalog/multi_hue/rows/2/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/blaze/3` |
| `/recipe/catalog/multi_hue/rows/2/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/blaze/2` |
| `/recipe/catalog/multi_hue/rows/3/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/lava/3` |
| `/recipe/catalog/multi_hue/rows/3/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/lava/2` |
| `/recipe/catalog/multi_hue/rows/4/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/lagoon/3` |
| `/recipe/catalog/multi_hue/rows/4/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/lagoon/2` |
| `/recipe/catalog/multi_hue/rows/5/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/glacier/3` |
| `/recipe/catalog/multi_hue/rows/5/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/glacier/2` |
| `/recipe/catalog/multi_hue/rows/6/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/canopy/3` |
| `/recipe/catalog/multi_hue/rows/6/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/canopy/2` |
| `/recipe/catalog/multi_hue/rows/7/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/haze/3` |
| `/recipe/catalog/multi_hue/rows/7/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/haze/2` |
| `/recipe/catalog/multi_hue/rows/8/neutral_tone_end` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/iris/3` |
| `/recipe/catalog/multi_hue/rows/8/neutral_tone_start` | `python-ast-literal-v1` | `compile_cmaps :: dict/multi/iris/2` |
| `/recipe/catalog/single_hue/neutral_tone_bottom` | `python-ast-literal-v1` | `seq_single :: param/L_bot` |
| `/recipe/catalog/single_hue/neutral_tone_top` | `python-ast-literal-v1` | `seq_single :: param/L_top` |
| `/recipe/constants/palette/neutral_tone_top` | `json-pointer-v1` | `/constants/L_TOP` |
| `/recipe/constants/palette_gray/neutral_tone_floor` | `json-pointer-v1` | `/constants/gray/floor` |
| `/recipe/family_params/amber/neutral_tone_floor` | `json-pointer-v1` | `/params/amber/floor` |
| `/recipe/family_params/blue/neutral_tone_floor` | `json-pointer-v1` | `/params/blue/floor` |
| `/recipe/family_params/cobalt/neutral_tone_floor` | `json-pointer-v1` | `/params/cobalt/floor` |
| `/recipe/family_params/coral/neutral_tone_floor` | `json-pointer-v1` | `/params/coral/floor` |
| `/recipe/family_params/cyan/neutral_tone_floor` | `json-pointer-v1` | `/params/cyan/floor` |
| `/recipe/family_params/fuchsia/neutral_tone_floor` | `json-pointer-v1` | `/params/fuchsia/floor` |
| `/recipe/family_params/green/neutral_tone_floor` | `json-pointer-v1` | `/params/green/floor` |
| `/recipe/family_params/indigo/neutral_tone_floor` | `json-pointer-v1` | `/params/indigo/floor` |
| `/recipe/family_params/lime/neutral_tone_floor` | `json-pointer-v1` | `/params/lime/floor` |
| `/recipe/family_params/orange/neutral_tone_floor` | `json-pointer-v1` | `/params/orange/floor` |
| `/recipe/family_params/pink/neutral_tone_floor` | `json-pointer-v1` | `/params/pink/floor` |
| `/recipe/family_params/purple/neutral_tone_floor` | `json-pointer-v1` | `/params/purple/floor` |
| `/recipe/family_params/red/neutral_tone_floor` | `json-pointer-v1` | `/params/red/floor` |
| `/recipe/family_params/rose/neutral_tone_floor` | `json-pointer-v1` | `/params/rose/floor` |
| `/recipe/family_params/sky/neutral_tone_floor` | `json-pointer-v1` | `/params/sky/floor` |
| `/recipe/family_params/tangerine/neutral_tone_floor` | `json-pointer-v1` | `/params/tangerine/floor` |
| `/recipe/family_params/teal/neutral_tone_floor` | `json-pointer-v1` | `/params/teal/floor` |
| `/recipe/family_params/violet/neutral_tone_floor` | `json-pointer-v1` | `/params/violet/floor` |
| `/recipe/family_params/yellow/neutral_tone_floor` | `json-pointer-v1` | `/params/yellow/floor` |

For `blue-red-rendered-endpoint-average-v1`, `source_path=C`; the derived
operation independently takes the accepted baseline colors
`palette.blue[6]=#2d99f0` then `palette.red[6]=#fb5b5e`, evaluates each through
the exact predecessor `lab_l_hex` path, and executes the source-order binary64
assignments `summed=float(blue_l+red_l)` then
`legacy_lstar=float(summed/2)`. Its required predecessor L* result is
`60.970937210626154` (`0x1.e7c47aba70dedp+5`) before forward migration; any
other colors, metric entry point, order, or association fails. The strict parser projects every
row to exactly `target_path`, `source_path`, `source_locator`, and
`source_operation_id`, canonicalizes that 58-element array, and requires:

```text
tone_mapping_plan_sha256 = SHA256(
    b"dartwork-mpl-v6-tone-mapping-plan-v1\0" +
    canonical_json(complete ordered four-field projection)
)
= d668cf0e07d90e64b0c4c8bab51514529f0107b7a19e2ad9e9d9777d7b526863
```

That digest is the required `migration.tone_mapping_plan_sha256`. No prose
locator, source line number, nearest equal literal, inverse tone lookup, or
candidate output is admitted. Equal values at `_recipe.py:L_TOP`,
`seq_single.L_top`, and `compile_cmaps.dv.l_center`, for example, remain three
different provenance owners because their exact locators differ.

`retired_authoring_mechanisms` is exactly
`["legacy-fourier-family-derivation-v5"]`. The predecessor Fourier curves,
including the CIELAB floor curve, remain reachable through the hashed
historical source but are not copied into an operational recipe or treated as
direct-OKLCH laws for new families.
`policies` has exactly `shipped_tone_compatibility`, `compatibility_gamut`, and
`output_quantization`. The first is the complete shipped tone policy above.
`compatibility_gamut` has exactly `policy_id`, `iterations`,
`linear_gamut_tolerance`, `preserve`, `final_linear_channel_clamp`, and
`encoded_transfer_id`. Their values are respectively
`"legacy-oklch-chroma-reduction-v1"`, `24`, `1e-6`,
`["oklab_l","hue"]`, `true`, and
`"predecessor-numpy-srgb-oetf-v1"`, reproducing the predecessor mapping path.
The transfer ID means the exact `_linear_to_srgb`
branch, NumPy binary64 operations, constants, and result extraction from the
hashed normative-predecessor `_conversion.py`; an algebraically similar scalar
OETF is not interchangeable unless every returned bit and exact surface agrees.
`output_quantization` is exactly
`"encoded-srgb-python-round-ties-even-v1"`. This compatibility SSOT contains
no validation/admission threshold, presentation preference, omitted default,
or generic authoring policy; those belong to separately reviewed downstream
records.

`recipe` has exactly `constants`, `family_order`, `family_params`, and
`catalog`. It is the complete operational compatibility recipe extracted from
the eight migration sources. In the following grammar, `F64` is a finite non-
Boolean JSON number whose parsed binary64 bits equal the identified predecessor
literal. `Tone` is an `F64` leaf addressed by exactly one
`tone_mappings.target_path`; its bits equal that row's
`neutral_tone_float_hex`. `Index` is a non-Boolean JSON integer. These aliases
are explanatory and never appear as serialized keys.

`constants` has exactly `palette` and `palette_gray`. `palette` has exactly
`neutral_tone_top`, `rise_power`, and `fall_power`, sourced respectively from
the normative predecessor v5 SSOT `/constants/L_TOP`,
`/constants/shape_q`, and `/constants/shape_r`, with the first converted to
`Tone`. `palette_gray` has exactly `neutral_tone_floor`, `hue_deg`, and
`chroma_profile`, sourced from `/constants/gray/floor`,
`/constants/gray/tint_hue`, and `/constants/gray/C_profile`; its profile is an
exact ten-`F64` array. `family_order` is exactly:

```text
red, rose, coral, tangerine, orange, amber, yellow, lime, green, teal,
cyan, sky, blue, cobalt, indigo, violet, purple, fuchsia, pink
```

`family_params` is an object with exactly those 19 keys. Each value has exactly
`hue_start_deg`, `hue_drift_deg`, `hue_gamma`, `chroma_peak_position`,
`chroma_peak`, `neutral_tone_floor`, `chroma_end_fraction`, and
`chroma_start_fraction`. In that order of meaning, the leaves are uniquely
sourced from the same family's normative predecessor v5 SSOT fields `h0`,
`dh`, `gamma`, `tp`, `cmax`, `floor`, `cend`, and `c0`; only `floor` is
converted to `Tone`. No Fourier-derived recomputation is permitted.

`catalog` has exactly `render`, `single_hue`, `gray`, `multi_hue`,
`diverging`, `cyclic`, and `cycles`. Its closed grammar is:

```text
render = {
  palette_output_count: 10,
  palette_dense_sample_count: 121,
  palette_refinement_limit: 14,
  palette_cv_stop: 0.015,
  continuous_dense_sample_count: 513,
  continuous_output_counts: [32, 256],
  arc_metric_id: "delta-e-ok-v1",
  arc_accumulator_id: "left-associated-binary64-prefix-sum-v1",
  inverse_resampler_id: "bisect-left-linear-t-v1",
  open_output_rule_id: "endpoint-inclusive-v1",
  closed_output_rule_id: "sample-n-plus-one-drop-terminal-v1",
  closed_seam_delta_e_ok_limit: 1e-6,
  output_quantization_policy_path: "/policies/output_quantization"
}

single_hue = {
  family_order_path: "/recipe/family_order",
  family_params_path: "/recipe/family_params",
  neutral_tone_top: Tone,
  neutral_tone_bottom: Tone,
  chroma_shape_id: "single-hue-two-branch-sine-power-v1",
  rise_base: 0.12, rise_scale: 0.88, rise_power: 1.2,
  fall_subtraction_scale: 0.90, fall_power: 1.4,
  boundary_chroma_fraction_policy_path:
    "/policies/shipped_tone_compatibility/sequential_catalog_chroma_fraction"
}

gray = {
  neutral_tone_top: Tone, neutral_tone_bottom: Tone, hue_deg: F64,
  chroma_base: F64, chroma_amplitude: F64,
  chroma_shape_id: "base-plus-amplitude-sin-pi-t-v1"
}

multi_hue = {
  family_params_path: "/recipe/family_params",
  interpolation_id: "fritsch-carlson-monotone-cubic-v1",
  hue_unwrap_id: "shortest-signed-arc-negative-180-tie-v1",
  knot_parameterization_id: "uniform-zero-to-one-v1",
  boundary_chroma_fraction_policy_path:
    "/policies/shipped_tone_compatibility/sequential_catalog_chroma_fraction",
  rows: [{name, anchor_families, chroma_knots,
          neutral_tone_start, neutral_tone_end}, ...]
}

diverging = {
  resampler_id: "python-round-linear-endpoint-index-v1",
  half_count_rule_id: "max-32-floor-output-div-2-v1",
  arm_order_id: "first-forward-second-reverse-drop-center-v1",
  palette_anchor_index: 6, center_chroma: 0.004, gamma: 0.85,
  neutral_tone_center: Tone,
  rows: [{name, low_family, high_family, neutral_tone_end}, ...]
}

cyclic = {
  hue_map: {
    name: "hue", neutral_tone: Tone,
    sample_id: "i-over-n-times-360-mod-360-v1",
    safety_probe_start_deg: 0, safety_probe_stop_exclusive_deg: 360,
    safety_probe_step_deg: 5, boundary_chroma_fraction: 0.95
  },
  twilight: {
    path_id: "two-half-sine-power-lobes-v1",
    neutral_tone_seam: Tone, neutral_tone_center: Tone,
    lobe_a_chroma_cap: 0.15, lobe_b_chroma_cap: 0.16,
    chroma_exponent: 0.85, boundary_chroma_fraction: 0.96,
    closed: true,
    rows: [{name, anchor_a_family, anchor_a_index,
            anchor_b_family, anchor_b_index}, ...]
  }
}

cycles = {rows: [{name, members}, ...]}
```

Every displayed object has exactly the displayed keys. A `multi_hue.rows`
record's `name` is a non-empty string, `anchor_families` is an array of at
least two family names, `chroma_knots` is an equally sized `F64` array, and its
two endpoints are `Tone`. A `diverging.rows` record has exactly the displayed
four keys and valid family names. A `cyclic.twilight.rows` record has exactly
the displayed five keys; its two indices are `Index` values in `[0,9]`.
`cycles.rows` records have exactly `name` and `members`; each member is exactly
`[family,Index]` with index in `[0,9]`.

Array order is normative: multi-hue rows are `aurora, afterglow, blaze, lava,
lagoon, glacier, canopy, haze, iris`; diverging rows are `blue_red,
blue_orange, teal_rose, green_purple, purple_orange, cyan_red, teal_amber,
violet_lime, indigo_amber, gray_blue, gray_red`; twilight rows are `halo,
corona`; cycle rows are `octave, octave_print`. Their non-tone leaves are the
exact corresponding AST literals or symbolic family names in the normative
predecessor `_cmaps.py` or `_cycles.py`; each tone leaf is resolved through its
unique migration row. The complete colormap order is `family_order`, `gray`,
the nine multi-hue rows, the eleven diverging rows, `hue`, `halo`, `corona`.
Pointers, rather than duplicate `0.97` or quantization literals, bind values
owned by `policies`.

No operational legacy `L*`, Fourier curve, duplicate policy, candidate output,
omitted default, or new-family authoring default may remain. Strict loading
requires complete one-to-one coverage between operational tone paths and
mapping rows and exact reconstruction of every predecessor AST/JSON source
leaf named above. Nested records reject extra fields, aliases, missing rows,
inferred defaults, or a literal owned by another subrecord. Rebuilding every
catalog output and all 18 surfaces is the final check; it cannot replace the
closed structural/source checks.

`multi_hue_discrete_indices` is a UTF-8-family-sorted object containing exactly
the nine baseline multi-hue families. Each family has exactly decimal keys
`"1"` through `"8"`; a row for `n` is an array of exactly `n` non-Boolean
indices in strictly increasing original-LUT order, each in `[0,255]`. The row
must equal the baseline's directly captured selector positions and indexing the
accepted `cmaps_256` row must reproduce both baseline forward discrete hex and
the reversed contract. Runtime reads only this manifest; it never invokes a
selector or reconstructs an index from a possibly duplicated hex value.

`row_contracts` has exactly `palette`, `direct_32`, `full_256`, `cycles`,
`curated_rows`, `dark_cycle`, and `discrete_forward`. Each value is an object
whose UTF-8 asset keys map to records having exactly `count`, `unique_count`,
`adjacent_duplicate_count`, `max_run_length`, and `canonical_sha256`.

The seven source maps and cardinalities are exact:

| Contract | Normative row source | Cardinality |
|---|---|---|
| `palette` | `baseline.surfaces.palette` | 20 rows × 10 |
| `direct_32` | normative predecessor v5 SSOT `/colormaps/swatches_32` | 43 rows × 32 |
| `full_256` | `baseline.surfaces.cmaps_256` | 43 rows × 256 |
| `cycles` | `baseline.surfaces.cycles` | 2 rows × 8 |
| `curated_rows` | `baseline.surfaces.curated_rows` | 15 rows × 8 |
| `dark_cycle` | `{"dark_cycle":baseline.surfaces.dark_cycle}` | 1 row × 7 |
| `discrete_forward` | flattened `baseline.surfaces.discrete_hex` | 547 rows |

`direct_32` is deliberately not described as an accepted baseline surface: it
is read from the exact hashed predecessor SSOT record in `migration.source_records`.
The 547 discrete rows are exactly sequential `20 × n=1..10`, diverging
`11 × n=1..9`, multi-hue `9 × n=1..8`, cyclic `3 × n=1..24`, and qualitative
`13 × n=1..8`; their keys are `family + "/" + canonical_decimal(n)`.

For a lowercase-hex row, `count` is its length, `unique_count` is the number of
distinct strings, `adjacent_duplicate_count` counts indices `i>0` for which
`row[i] == row[i-1]`, and `max_run_length` is the longest contiguous equal-
value run. All four are non-Boolean integers. `canonical_sha256` is SHA-256 of
`b"dartwork-mpl-color-row-contract-v1\0" + contract_name.encode("ascii") +
NUL + asset_key.encode("utf-8") + NUL + canonical_json(row)`. Objects serialize
by UTF-8 key order and every row retains its source order. These are per-asset
observations; no false global all-unique rule is allowed.

`section_hashes` has exactly one key for every preceding top-level field except
itself and `ssot_payload_sha256`. Each value is SHA-256 of
`b"dartwork-mpl-color-ssot-v6-section\0" + key.encode("ascii") + NUL +
canonical_json(value)`. `ssot_payload_sha256` hashes
`b"dartwork-mpl-color-ssot-v6\0"` plus canonical JSON of the complete object
with only that field omitted. The tracked file is canonical JSON plus one LF.
One strict accessor owns loading; recipe, build, runtime, typing, MCP, and
generated outputs may not duplicate literals. `_generated.py` is derived from
this SSOT, and rebuilding it plus all 18 surfaces must be byte-identical.
This document intentionally does not pin a whole-v6 fixture digest: the v6
bytes do not exist in the normative predecessor and may first be produced only
by the compatibility-migration batch after the independently accepted baseline
is in its exact HEAD. Pinning a digest from the current dirty worktree would be
circular. The closed schema, predecessor lookups, hash preimages, exact-surface
gate, and later A/B-reviewed artifact determine and authorize that digest.

### 3.2 New-family authoring lane

New authoring uses distinct typed policies rather than a
`luminance_lock: bool` that changes the meaning of `tone`:

- **Direct OKLCH policy — default:** the authored coordinate is actual OKLab /
  OKLCH `L`; gamut mapping preserves `L` and `h` while reducing `C`.
- **Fixed modeled-relative-Y policy — opt-in:** the author explicitly requests
  `target_Y`; the solver adjusts actual `L` and reduces `C` only when needed.

Fixed-Y may be selected only when the authored coordinate semantics require
points at one prescribed path coordinate to lie on the same nominal D65-sRGB
modeled-relative-Y fiber while hue or chroma varies. This is a coordinate-
topology requirement only. It is not evidence of perceived-brightness
uniformity, physical display luminance, accessibility, or fidelity to the
shipped catalog, and it is never selected merely to imitate that catalog.
Direct OKLCH remains the default whenever that exact topology is not required.

The generic lane remains private and authoring-time in this change. It does not
add a public arbitrary-family registration API.

### 3.3 Authoring type and serialization contract

The private request and recipe types are a discriminated union, not a shared
record with optional coordinates:

```python
@dataclass(frozen=True, slots=True)
class DirectOklchPoint:
    lightness: float
    chroma: float
    hue_deg: float

@dataclass(frozen=True, slots=True)
class FixedRelativeYPoint:
    target_y: RelativeY
    chroma: float
    hue_deg: float

@dataclass(frozen=True, slots=True)
class DirectOklchAxisRecipe:
    lightness_top: float
    lightness_floor: float
    gamut_policy_id: str

@dataclass(frozen=True, slots=True)
class FixedYTopologyContract:
    policy_id: Literal["fixed-y-level-set-topology-v1"]
    invariant_id: Literal[
        "same-path-coordinate-same-modeled-relative-y-v1"
    ]
    claim_scope: Literal["nominal-d65-srgb-modeled-relative-y-only"]
    intended_use: str
    direct_oklch_unsuitable_reason: str

@dataclass(frozen=True, slots=True)
class FixedRelativeYAxisRecipe:
    target_y_top: RelativeY
    target_y_floor: RelativeY
    boundary_policy_id: str
    topology_contract: FixedYTopologyContract

CoordinateAxisRecipe: TypeAlias = (
    DirectOklchAxisRecipe | FixedRelativeYAxisRecipe
)

@dataclass(frozen=True, slots=True)
class AuthoringFamilyRecipe:
    coordinate_axis: CoordinateAxisRecipe
    h0: float
    dh: float
    gamma: float
    tp: float
    cmax: float
    cend: float
    c0: float
```

Required authoring entry points are exactly:

```python
render_direct_oklch(
    request: DirectOklchPoint,
    *,
    policy: DirectOklchGamutPolicy,
) -> DirectOklchMappedColor

render_fixed_relative_y_oklch(
    request: FixedRelativeYPoint,
    *,
    policy: RelativeYBoundaryPolicy,
) -> RelativeYSolvedColor

compile_authoring_family(
    family: str,
    recipe: AuthoringFamilyRecipe,
    *,
    generation_policy: AuthoringGenerationPolicy,
    renderer_policy: DirectOklchGamutPolicy | RelativeYBoundaryPolicy,
    discrete_policy: DiscreteCandidatePolicy,
    admission_policy: AdmissionPolicy,
    validation_policy: ValidationOraclePolicy,
) -> AuthoringProposal
```

Every policy argument is required. The `coordinate_axis` variant, the renderer
policy type, and the policy ID named by that axis must agree exactly. A direct
axis cannot receive a relative-Y policy and a fixed-Y axis cannot receive a
direct-gamut policy.

`DIRECT_OKLCH_GAMUT_V1` is the frozen value:

```python
DirectOklchGamutPolicy(
    policy_id="direct-oklch-gamut-v1",
    scalar_kernel_constants_sha256="3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db",
    coefficient_model_id="binary64-direction-exact-rational-v1",
    hue_conversion_id="normalized-degrees-math-radians-v1",
    semantic_gamut_tolerance=0.0,
    root_interval_width=2.0**-48,
    root_bisection_limit=64,
    inward_bisection_limit=64,
    comparison_refinement_limit=4096,
    max_direction_norm_abs_error=2.0**-50,
    max_abs_chroma_error=1e-10,
    max_rel_chroma_error=2.0**-32,
)
```

For this policy ID, the scalar-kernel hash must equal section 5.1's golden
digest, the coefficient and hue-conversion models must match exactly, semantic
tolerance must be `0.0`, both bisection limits and the comparison-refinement
limit must be positive non-boolean integers, and the finite root width,
direction-norm guard, and both error budgets must be positive. Unknown or
partially specified policy records fail. A positive constrained upper bound
must satisfy both `gap <= max_abs_chroma_error` and
`gap <= max_rel_chroma_error*upper`; a zero upper bound requires zero gap. The
relative budget is a numerical anti-collapse guard, not a perceptual threshold.

The direct renderer uses the exact-rational coefficient and Sturm-isolation
model in section 5.4. At fixed requested `L` and `h`, each raw channel and each
channel-minus-one is a cubic polynomial in `C`. Partition
`[0, requested_C]` at every real face root and choose the greatest certified
feasible `C' <= requested_C` across all components. Thus it does not assume that
feasibility is a single chroma prefix. An analytically feasible request must
also satisfy every scalar postcondition and is then returned unchanged. If that
same request fails a scalar postcondition, rendering fails closed with the
direct boundary error: it is not silently rounded inward and cannot be labeled
`constrained-reduced`. Only an analytically infeasible request enters the inward
procedure, which produces a conservative witness at the greatest feasible
component. Face-root identity and de-duplication use section 5.1's
closed source registry, and the winning coordinate uses section 5.4's exact
direct fixed-L key before witness rounding.

The final direct witness is recomputed through the canonical scalar kernel. Its
`oklab_l` must be bit-identical to requested `L`; raw and encoded channels must
be finite and inside `[0,1]` without a clamp. Its stored
`achieved_relative_y` must be the bit-identical result of the common witness-Y
association in section 5.1, recomputed from the stored raw channels rather than
trusted or obtained by decoding encoded RGB. Recompute and store the `C=0`
neutral baseline through the same association. For interior `0<L<1`, neither
raw nor encoded output may be bit-exact black or white. When mapped `C>0`, both
the raw and encoded triples must differ bitwise from their stored neutral
baselines. Failure raises the direct boundary error; it may not return black,
white, or a neutral output while claiming an interior positive coordinate.
This is a representation anti-collapse rule, not a visibility threshold; final
8-bit LUT quantization may still merge nearby colors and records those
duplicates explicitly.

For interior `0<L<1`, let `M` be
the greatest analytically feasible chroma no greater than the request. The
closed result type is:

```python
@dataclass(frozen=True, slots=True)
class DirectOklchMappedColor:
    kind: Literal["direct-oklch-mapped-color"]
    mapping_mode: Literal["unchanged", "constrained-reduced", "endpoint"]
    request: DirectOklchPoint
    direction: DirectionEvidence
    model: ModelEvidence
    mapped_chroma: float
    constrained_chroma_lower_bound: float
    constrained_chroma_upper_bound: float
    constrained_abs_error_bound: float
    requested_minus_mapped_chroma: float
    selection: SelectionCertificate
    witness: DirectColorWitness
```

The shared evidence types and exact JSON encoding are defined in section 5.1.
For `unchanged` and `constrained-reduced`, the result guarantees
`lower <= M <= upper <= requested_chroma`, lower and `mapped_chroma` equal the
witness chroma, and numerical error is the outward-rounded `upper-lower` gap
from section 5.4. `requested_minus_mapped_chroma` is
the separately rounded exact-ratio difference: intended gamut reduction may be
large and is not numerical uncertainty. Failure to meet both absolute and
relative chroma-certificate budgets in the policy is an error. The result never
clamps a raw channel and calls the clipped result an unchanged OKLCH point.
Exact `lightness=0` and `lightness=1` are endpoint policies: any positive
requested chroma maps to chroma-zero black or white respectively, with lower,
upper, and numerical-error bound all zero. This avoids treating sub-ULP inverse-
matrix row-sum residue as a colored endpoint. Endpoint mode carries
`EndpointModelEvidence` and makes no exact-rational `M` claim; its separate
scalar-policy verification is defined in section 5.6.

The canonical `coordinate_axis` JSON variant is either:

```json
{
  "kind": "direct-oklch-v1",
  "lightness_top": 0.9,
  "lightness_floor": 0.45,
  "gamut_policy_id": "direct-oklch-gamut-v1"
}
```

or:

```json
{
  "kind": "fixed-relative-y-v1",
  "target_y_top": 0.729,
  "target_y_floor": 0.091125,
  "boundary_policy_id": "relative-y-boundary-v1",
  "topology_contract": {
    "policy_id": "fixed-y-level-set-topology-v1",
    "invariant_id": "same-path-coordinate-same-modeled-relative-y-v1",
    "claim_scope": "nominal-d65-srgb-modeled-relative-y-only",
    "intended_use": "<non-empty design intent>",
    "direct_oklch_unsuitable_reason": "<non-empty coordinate reason>"
  }
}
```

Loading dispatches only on `kind`, requires the exact key set, and rejects
unknown policy IDs, booleans as numbers, non-finite values, and empty policy
IDs. Point validation requires `lightness` or `target_y` in `[0,1]`,
`chroma >= 0`, and finite `hue_deg`. Axis validation requires
`1 >= lightness_top > lightness_floor >= 0` or
`1 >= target_y_top > target_y_floor >= 0`. Common family validation requires
finite `h0` and `dh`, `gamma > 0`, `0 < tp < 1`, `cmax >= 0`, and
`0 <= c0,cend <= 1`. Authoring records recursively reject `tone`, `tone_top`,
`tone_floor`, `neutral_tone`, and `luminance_lock`. Every selected policy ID and
all of that policy's numeric fields appear in the proposal's `policies` map;
replay cannot reconstruct an omitted default.

Fixed-Y is admissible only when the authored coordinate semantics require
points at one prescribed path coordinate to lie on the same nominal D65-sRGB
modeled-relative-Y fiber while hue or chroma varies. Both free-text fields are
non-empty UTF-8 and are reviewed as design intent; the three literal IDs bound
the only V1 machine claim. This is not a claim of perceived-brightness
uniformity, physical display luminance, accessibility, or shipped-catalog
fidelity. A desire for visually “even” lightness alone does not justify this
exception; direct OKLCH remains the default.

The compatibility-migration batch establishes the v6 compatibility SSOT schema;
it is absent from the normative predecessor and becomes immutable only after
that batch is accepted. The later authoring batch must not change it. A derive
record lives under ignored `build/color-authoring/<family>/proposal.json`;
acceptance copies it into the separately validated authoring manifest defined
in section 3.5. A test fixture can prove that transition without registering a
new public family.
Every downstream consumer captures that ergonomic ignored path into section
10's immutable, content-addressed external-input bundle and never reopens the
live ignored file.

### 3.4 Deterministic new-family LUT generation

The seven family parameters do not by themselves define a 256-entry LUT. The
following required policy closes the sampling, interpolation, rendering,
equalization, ordering, and quantization contract:

```python
@dataclass(frozen=True, slots=True)
class AuthoringGenerationPolicy:
    policy_id: str
    scalar_kernel_constants_sha256: str
    output_count: int
    dense_sample_count: int
    shape_rise_power: float
    shape_fall_power: float
    axis_interpolation_id: str
    hue_path_id: str
    chroma_shape_id: str
    gamut_application_id: str
    arc_metric_id: str
    arc_accumulator_id: str
    inverse_resampler_id: str
    quantizer_id: str
    output_order_id: str

AUTHORING_GENERATION_V1 = AuthoringGenerationPolicy(
    policy_id="authoring-family-lut-v1",
    scalar_kernel_constants_sha256="3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db",
    output_count=256,
    dense_sample_count=4097,
    shape_rise_power=1.2,
    shape_fall_power=1.5,
    axis_interpolation_id="linear-top-to-floor-v1",
    hue_path_id="power-drift-degrees-v1",
    chroma_shape_id="sin-rise-power-fall-v1",
    gamut_application_id="typed-renderer-request-map-v1",
    arc_metric_id="delta-e-ok-times-100-v1",
    arc_accumulator_id="prefix-math-fsum-v1",
    inverse_resampler_id="left-bracket-linear-t-v1",
    quantizer_id="srgb8-python-round-half-even-v1",
    output_order_id="top-to-floor-v1",
)
```

For this policy ID, every field, including the section 5.1 scalar-kernel golden
digest, must equal the frozen value. Unknown, omitted, or extra fields fail.
`4097` is the versioned sampling resolution of this
offline policy, not a perceptual constant or a claim of optimality. Its
equalization residuals must appear in the proposal comparison; changing the
resolution or method requires a new policy ID and cannot recompute a frozen
family.

All following operations use finite binary64 values and the displayed
association. Evaluate `t_j = float(j) / 4096.0` for `j=0..4096`. At each `t`:

```text
axis(t) =
    lightness_top + (lightness_floor-lightness_top)*t
or
    target_y_top + (target_y_floor-target_y_top)*t

h(t) = (h0 + dh*t**gamma) % 360.0

if t <= tp:
    v = min(max(t/tp, 0.0), 1.0)
    shape(t) = c0 + (1.0-c0) *
        sin((pi/2.0)*v)**shape_rise_power
else:
    v = min(max((t-tp)/(1.0-tp), 0.0), 1.0)
    shape(t) = 1.0 - (1.0-cend)*v**shape_fall_power

C_requested(t) = cmax*shape(t)
```

A direct axis constructs `DirectOklchPoint(axis(t), C_requested(t), h(t))`; a
fixed-Y axis constructs
`FixedRelativeYPoint(axis(t), C_requested(t), h(t))`. Invoke only the matching
typed renderer with the exact supplied renderer policy. The renderer's result
is the only gamut application: this lane has no shipped-boundary call, legacy
pre-cap fraction, raw-RGB clamp, or boolean coordinate switch.

Require every rendered encoded channel to be finite and inside `[0,1]`. Decode
each unquantized encoded triple through the canonical sRGB-to-OKLab kernel and
compute each adjacent segment with the exact `delta_e_ok_100` primitive in
section 7.3. Let `segment[j]` join dense points `j-1` and `j`, and compute each
prefix independently as:

```text
A[0] = 0.0
A[j] = math.fsum(segment[1:j+1])  for j=1..4096
```

Reject a non-finite or zero `A[4096]`. Set `r[0]=0.0` and `r[255]=1.0`. For
each `k=1..254`, set `target=A[4096]*k/255.0` and let
`j=bisect_left(A, target)`. If `A[j] == target`, set `r[k]=t_j`; otherwise the
left-bracket segment is necessarily positive and:

```text
f = (target-A[j-1])/(A[j]-A[j-1])
r[k] = t_(j-1) + f*(t_j-t_(j-1))
```

Any out-of-range index, non-positive interpolation denominator, non-finite
value, or `r[k]` outside `[0,1]` fails. Re-render all 256 `r[k]` values through
the same typed renderer. Quantize exactly once after validating encoded
channels: for each channel use Python `round(channel*255.0)` (ties to even),
then emit lowercase `#rrggbb`. The final row is ordered by increasing `t`:
index 0 is the top coordinate and index 255 the floor coordinate. Do not
reverse it, interpolate quantized RGB, or run a second equalization pass.

This compiler is private authoring/build tooling outside shipped `_generate`
and `_cmaps`. Similar recipe fields do not authorize sharing their compiler
path.

### 3.5 Proposal, promotion, and frozen replay schema

Family identifiers match `[a-z][a-z0-9_]{0,63}`. The identifier must equal the
directory component and filename stem in these canonical paths:

```text
build/color-authoring/<family>/proposal.json
src/dartwork_mpl/asset/color/oklab_authoring_frozen_v1/<family>.json
```

The first path is Git-ignored authoring output. The second is tracked SSOT.
Strict JSON loading rejects duplicate keys before schema validation.

The namespace is create-only. Before importing a renderer or generating any
candidate bytes, proposal creation rejects a family already present in any
shipped catalog/name registry or in `oklab_authoring_frozen_v1`. Promotion uses
section 3.5's `publish_immutable_100644` and durable directory barrier for the
frozen path; `os.replace`, direct final-path writing, or another overwrite-
capable operation is forbidden. If a race leaves an
existing target, promotion reparses and validates it: byte-identical complete
frozen bytes are an idempotent no-op, while any difference is fatal. Re-freezing
the same family from a different recipe, policy, proposal, or acceptance record
requires a new versioned family identifier or a separately approved ADR; the
derive lifecycle never mutates an existing frozen identity.

A proposal envelope has exactly the keys:

```text
schema, lifecycle, family, payload, payload_sha256,
policy_approvals, provenance, public_reproducibility_sha256
```

with `schema="oklab-authoring-proposal-v1"` and `lifecycle="derive-v1"`. A
frozen envelope has exactly:

```text
schema, lifecycle, family, payload, payload_sha256,
accepted_proposal_sha256, accepted_public_reproducibility_sha256,
acceptance, promotion_provenance,
frozen_envelope_sha256
```

with `schema="oklab-authoring-frozen-v1"` and `lifecycle="frozen"`.
`acceptance` has exactly
`comparison_report_payload_sha256`, `reviewer_a_report_sha256`,
`reviewer_b_report_sha256`, `reviewed_source_fingerprint`,
`reviewed_execution_snapshot_sha256`, and `maintainer_approval`. The three
artifact hashes and snapshot hash are lowercase 64-digit SHA-256 strings; the
fingerprint is section 10's exact seven-field record. The reviewed execution
snapshot is explicitly the common source-only snapshot; per-review input hashes
are transitively bound through the two reports and `review_sequence_sha256`.
`maintainer_approval` has
exactly `approval_ref`, `walkthrough_subject_sha256`,
`review_sequence_sha256`, and `independence_attested`; the first two are
respectively a harness-generated public identifier matching
`maintainer-approval-[0-9a-f]{32}` and a hash supplied only after the
walkthrough, the sequence hash is
recomputed from the accepted A/B envelopes and completion token, and the final
field must be the literal true. This is the human attestation that the harness'
fresh-instance/sequential procedure was followed, not a cryptographic identity
signature. Reviewer B must identify the same fingerprint and source-only
execution snapshot passed by A. Its invocation-input bundle is necessarily
different because it also contains A's completed report, historical input,
control/evidence closure, and completion token. The frozen payload is
canonically byte-identical to the accepted
proposal payload; promotion does not regenerate or edit it.

`promotion_provenance` has the same exact six keys as proposal provenance:
`invocation_recipe`, `environment`, `source_fingerprint`, `execution_snapshot`,
`execution_inputs`, and `source_files`. Its environment is the complete
environment-v3 owner with `invocation_kind="promotion-replay"`; execution
inputs resolve section 10's exact promotion bundle; source fingerprint,
snapshot, and source files bind the unchanged reviewed promotion snapshot.
Its base-runtime hash equals preselection/proposal/comparison while its full
runtime closure, environment hash, and trace are promotion-specific. A new
promotion completes replay in memory, reaches the post-operation capture
barrier, constructs this provenance, and only then serializes and atomically
installs the complete create-only frozen envelope with that durable primitive.
The outer frozen self-hash
therefore owns the record without a detached evidence/hash cycle.

Before that install, promotion copies and rehashes its complete external-input
bundle create-only at the canonical tracked path
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/frozen-family-review-v1/<family>/input-bundles/<external_input_bundle_sha256>/manifest.json`
with the universal `blobs/<raw_sha256>` children. The frozen provenance's
`execution_inputs` resolves only to that tracked copy. The bundle contains the
canonical maintainer-approval input defined below in addition to section 10's
reviewed closure; a hash-bound ignored producer bundle alone is not durable
authority. All bundle blobs are durably published and pass their prerequisite
barrier before `manifest.json`; that manifest passes its own barrier before the
frozen envelope is published. A surviving frozen envelope therefore always has
a complete durable tracked bundle.

If the frozen target already exists, promotion takes an early validation path
before launching a new `promotion-replay` invocation. It strictly validates the
stored envelope/provenance and requires payload, proposal, acceptance, and
accepted public-reproducibility and tracked captured-bundle identities to match,
then reopens and `fsync`s the envelope and every required tracked bundle leaf,
`fsync`s all containing directories bottom-up, repeats the complete no-follow
byte/mode/inode/link-count and hash validation, and only then returns an
idempotent no-op. If the complete tracked bundle exists but the frozen envelope
is absent, that exact bundle-only prefix is reverified/resynchronized and
promotion resumes at envelope installation; it is not mistaken for completion.
It never synthesizes a second environment against the post-install snapshot.

For frozen acceptance, `walkthrough_subject_sha256` is exactly:

```text
SHA256(
    b"dartwork-mpl-oklab-authoring-frozen-maintainer-walkthrough-v1\0" +
    canonical_json({
        "family": family,
        "proposal_envelope_sha256": proposal_envelope_sha256,
        "comparison_report_payload_sha256":
            comparison_report_payload_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "review_sequence_sha256": review_sequence_sha256,
        "common_execution_snapshot_sha256":
            reviewed_execution_snapshot_sha256,
    })
)
```

`proposal_envelope_sha256` equals `accepted_proposal_sha256`, and every other
value equals the strict comparison/reviewer/sequence link. For a policy approval
entry, the formula is exactly:

```text
SHA256(
    b"dartwork-mpl-oklab-authoring-policy-maintainer-walkthrough-v1\0" +
    canonical_json({
        "approval_id": approval_id,
        "family": family,
        "policy_kind": policy_kind,
        "policy_id": policy_id,
        "policy_record_sha256": policy_record_sha256,
        "characterization_payload_sha256":
            characterization_payload_sha256,
        "verification_evidence_raw_sha256":
            verification_evidence_raw_sha256,
        "verification_evidence_sha256":
            verification_evidence_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "review_sequence_sha256": review_sequence_sha256,
        "common_execution_snapshot_sha256":
            reviewed_execution_snapshot_sha256,
    })
)
```

Both are closed objects with exactly the displayed keys. Neither includes
`approval_ref`, the surrounding approval/frozen/entry/index hash, or a
promotion-input hash, so the dependency remains acyclic. After computing the
walkthrough, the maintainer approval is materialized create-only at
`build/color-authoring/maintainer-approvals-v1/<raw_sha256>.json`. Its bytes are
exactly canonical JSON of the complete four-key `maintainer_approval` object
plus one LF, and the filename is their plain SHA-256. Every promotion captures
that regular file under the one exact external-input role
`maintainer-approval`; the parsed blob must be canonical-byte and value
identical to the object embedded in the immutable output.

Both envelopes use a scientific payload with exactly these keys:

```text
recipe, policies, digests, lut256, candidate_domain,
selection_rows, validation_rows, validation_oracle_evidence
```

The payload is deliberately independent of approval history, machine/root
location, and invocation transport. Proposal-level `policy_approvals` and
`provenance` are public reproducibility/governance siblings, not scientific
payload members. Promotion copies the payload and `payload_sha256`
byte-for-byte; it does not make scientific identity depend on where or by whom
the computation ran.

`recipe` is the exact `AuthoringFamilyRecipe` serialization. `policies` has
exactly `generation`, `renderer`, `discrete`, `admission`, and `validation`;
every field is explicit, including numeric values otherwise represented by a
Python default. The renderer record's type and ID must match the recipe axis.
`lut256` is exactly 256 lowercase seven-character `#rrggbb` strings.

`candidate_domain` has exactly `count` and `records`. `records` is the complete
eligible domain after lowest-index RGB de-duplication and policy filtering, in
strictly increasing original-index order. Each record has exactly `index` and
`hex`; its non-boolean index is unique and in `0..255`, and its hex equals
`lut256[index]`. `count` is a non-boolean integer equal to the array length and
must be in `8..256` because a written proposal contains every `n=1..8` row.

`selection_rows` is an array in exact `n=1..8` order, never an object with
integer-like keys. Each row has exactly `n`, `indices`, `hex`, and `objective`.
`indices` contains `n` strictly increasing non-boolean integers in `0..255`;
every index must occur in `candidate_domain.records`, and `hex` must equal
`[lut256[i] for i in indices]`. `objective` has exactly
`midpoint_error_q`, `minimum_q`, `coverage_q`, and `gap_cv_q`. For `n=1`, only
`midpoint_error_q` is a nonnegative integer and the other values are null. For
`n>=2`, `midpoint_error_q` is null and the other values are nonnegative
integers.

`validation_rows` is also an array in exact `n=1..8` order. Each row has
exactly `n`, `modes`, `common_min_delta_e00`, `common_mode`, `common_pair`,
`floors`, and `admission_passed`. `modes` is an array in exact order `normal`,
`protan`, `deutan`, `tritan`; each mode record has exactly `mode`,
`min_delta_e00`, `min_pair_delta_e00`, `min_delta_e_ok_100`, and
`min_pair_delta_e_ok_100`. A pair is two strictly increasing selected-row
positions in `0..n-1`, not LUT indices. For `n=1`, all minima, pairs,
`common_min_delta_e00`, `common_mode`, `common_pair`, `floors`, and
`admission_passed` are null. For `n>=2`, minima are finite nonnegative non-
boolean values and pairs are present. `common_min_delta_e00`, `common_mode`, and
`common_pair` are the exact result of section 8's value/mode-rank/pair ordering.
`floors` exactly repeats the matching admission-policy row.
`admission_passed` equals the three comparisons against the normal, common, and
tritan floors and must be true for a written proposal.

`ValidationOraclePolicy` serializes the exact recognized
`VALIDATION_ORACLE_V1` record in section 8. It is not an open collection of
arbitrary non-empty IDs. The policy selects the independent finished-output
oracle and cannot be imported by construction or selection modules.

`validation_oracle_evidence` has exactly `policy_sha256`, `truth`, `source`,
`constants_sha256`, and `reference_suite`. `policy_sha256` is SHA-256 of
`b"dartwork-mpl-validation-oracle-policy-v1\0"` plus the canonical policy.
`source` has exactly `role`, `path`, and `sha256`; its role is the literal
`finished-output-validation-oracle-v1`, its path is the canonical repo-relative
POSIX implementation path, and its hash is the raw-byte SHA-256. Exactly one
identical path/hash record must occur in `provenance.source_files`.
`truth` has exactly `truth_id`, `path`, `raw_sha256`, and
`truth_payload_sha256`. Its ID and truth path are the literal V1 values in
section 8. Strict parsing of the tracked truth must reproduce both hashes before
the current source, constants, or suite is evaluated. Bootstrap acceptance is
deliberately absent from this scientific record: two valid approval histories
over identical truth bytes must produce byte-identical
`validation_oracle_evidence`, `validation_input_sha256`, and `payload_sha256`.

Acceptance nevertheless remains mandatory proposal-level governance. Before
proposal publication and again during promotion, validation strictly reparses
the admission entry and the captured preselection envelope named by
`policy_approvals`, requires their non-null
`validation_truth_acceptance_sha256` values to be identical, and resolves that
value to the strict fixed-path acceptance
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/validation-oracle-truth-review-v1/acceptances/bootstrap.json`
and its complete archive. The recomputed acceptance self-hash must equal both
governance records, and its truth raw/payload hashes must equal this four-key
scientific truth record. A hash-shaped string alone has no authority. The
complete `policy_approvals` object is bound by
`public_reproducibility_sha256`, so changing approval history changes the
proposal/governance identity but not scientific identity. The truth itself
does not point back to acceptance; this downstream sibling traversal keeps the
authority graph acyclic.
`constants_sha256` is SHA-256 of
`b"dartwork-mpl-validation-oracle-constants-v1\0"` plus canonical JSON of the
complete ordered matrices, white point, transfer constants, and reference
values consumed by the recognized policy.

`reference_suite` has exactly `suite_id`, `reference_vectors_sha256`,
`case_count`, `case_results_sha256`, and `verdict`. Its ID must equal the
policy's `reference_suite_id`; count is a positive non-boolean integer; verdict
is the literal `PASS`. The vector and result hashes use respectively
`b"dartwork-mpl-validation-reference-vectors-v1\0"` and
`b"dartwork-mpl-validation-reference-results-v1\0"` plus canonical JSON of the
complete arrays in suite-declared case order. Proposal creation and promotion
rerun the suite from the captured source snapshot and require source bytes,
complete constants/vectors, exact count, result hash, and PASS to match the
immutable truth asset. No hash-shaped string without both immutable expected
bytes and its matching rerun is accepted.

`digests` has exactly:

```text
lut_input_sha256, lut_sha256,
candidate_domain_count, candidate_domain_sha256,
selection_input_sha256, selection_rows_sha256,
validation_input_sha256, validation_rows_sha256
```

Their canonical inputs are exactly:

```text
lut_input = {
    "recipe": recipe,
    "generation": policies.generation,
    "renderer": policies.renderer,
}
selection_input = {
    "lut_sha256": lut_sha256,
    "discrete": policies.discrete,
    "candidate_domain_count": candidate_domain.count,
    "candidate_domain_sha256": candidate_domain_sha256,
}
validation_input = {
    "selection_rows_sha256": selection_rows_sha256,
    "admission": policies.admission,
    "validation": policies.validation,
    "validation_oracle_evidence": validation_oracle_evidence,
}
```

`candidate_domain_count` must equal `candidate_domain.count`.
`lut_input_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-lut-input-v1\0"` plus canonical JSON of the
complete `lut_input` object above; no field is omitted.
`candidate_domain_sha256` hashes the complete `{count,records}` object;
`lut_sha256`, `selection_rows_sha256`, and `validation_rows_sha256` hash their
corresponding values. Approval-entry/preselection identities and the
bootstrap-acceptance path/hash are intentionally absent from these scientific
preimages. Proposal validation separately proves that the sibling approvals
authorize the exact discrete/admission policy bytes, that the preselection
envelope consumed them before selection, and that the governance traversal
above authorizes the exact scientific truth bytes.

`provenance` has exactly `invocation_recipe`, `environment`,
`source_fingerprint`, `execution_snapshot`, `execution_inputs`, and
`source_files`. `invocation_recipe` is the closed path-neutral recipe defined
below; raw argv, cwd, executable path, environment strings, and shell rendering
are private and forbidden here.
It has exactly `schema`, `executable_role`, `entry_module`, `operation_id`, and
`operands`, with schema `oklab-authoring-invocation-recipe-v1`.
`executable_role` is exactly `captured-python-runtime` for a row in the
environment profile registry, and exactly
`verified-archive-byte-transfer-machine` for a row in the archive-promotion
registry below; no other value or cross-registry pairing is valid. Entry module
and operation ID must be one exact row of the corresponding registry. Each
operand has exactly `role` and
`value`; role is one of `family`, `source-snapshot`, `external-input-bundle`,
`output-artifact-role`, or `expected-artifact-role`, and value is respectively
the validated family ID, a lowercase SHA-256, or a closed logical artifact
role. Operand order/cardinality is fixed per operation profile. Filesystem
locations are resolved privately from those roles and may not appear as operand
values. For an environment-profile row, the supervisor verifies raw argv and
cwd against both this recipe and the closed
`native_execution.python_startup` contract, serializes the fixed path-neutral
`invocation-request` leaf inside the control-preparation root, and verifies the
computation environment against the closed
`native_execution.launch_environment` contract in memory. The fresh native
control-preparer child, not the computation child, opens the leaf exactly once
as private-control record zero. It strict-parses the public recipe projection
and emits it only inside the canonical `invocation_handoff`; the raw leaf, its
byte count/hash, parser storage, and private role resolution die with that
child. The supervisor revalidates the typed handoff, kills and reaps the
preparer, and only then creates the fresh computation child. A pre-broker,
repeated, byte-different, omitted, wrong-child, or post-control-preparation
request read is fatal. No operand pathname or optional argument is appended to
either child's argv. For an archive row, the
host transport verifies argv/cwd against the recipe but has no normative
environment; acceptance comes from the abstract transition and independent
postcondition verification below. The recipe does not purport to describe
environment variables, CPython startup flags, or physical paths; those are
closed by their own records.

The sealed request bytes are exactly UTF-8 canonical JSON plus one terminal LF
for an object having exactly `schema`, `invocation_kind`,
`base_import_profile_id`, and `invocation_recipe`. Schema is
`oklab-authoring-private-invocation-request-v1`; invocation kind is the literal
`invocation_kind` string of one environment-profile row;
`base_import_profile_id` is a nonempty ID naming one exact row in the
separately sealed reviewed base-import registry; and invocation recipe is the
complete public object above, whose entry module, operation, operand order,
and values must equal the corresponding fields of that selected environment-
profile row. Canonical JSON uses this document's exact serializer and has no LF in
its hash preimage; the sealed-leaf byte count/hash cover the serialized LF.
Absolute paths, native leaf locators, descriptors, private role resolutions,
and optional keys are forbidden. The supervisor's separately sealed native
inventory resolves recipe roles to source, bundle, and output capabilities;
neither the request nor either public handoff duplicates or chooses those
physical resolutions. The computation child never receives this private
request leaf; it receives only the two public handoff leaves defined in the
environment contract.
For every environment-v3 computation, `captured-python-runtime` resolves to
the `process-executable` mapping; that mapping's file identity equals
`python.executable_sha256`. This resolution rule applies only to the
environment-v3 profiles. For an archive-promotion row,
`verified-archive-byte-transfer-machine` resolves instead to the exact abstract
state-transition contract in the archive-promotion registry below. It is not a
host executable, interpreter, or environment selector. The host process that
implements that transition is non-authoritative transport; the tracked entry-
module bytes remain bound through `source_files` and the execution snapshot,
and the transition is accepted only when an independent verifier reconstructs
the same complete output bytes and target postcondition. An archive recipe
therefore neither resolves through `process-executable` nor carries an
environment-v3 record.
`environment` is the strict `oklab-authoring-environment-v3` record below. The
fingerprint and complete execution-snapshot record are section 10's schemas and
must cross-link exactly. `execution_inputs` is section 10's closed record; its
source-snapshot hash must equal the embedded execution snapshot and its external
bundle must contain exactly the prior preselection envelope. `source_files` is
an array of unique repo-relative POSIX paths in lexicographic order, each paired with its raw-byte SHA-256 in a
record having exactly `path` and `sha256`; its hash must equal the snapshot's
`source_files_sha256`.

`public_reproducibility_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-public-reproducibility-v1\0"` plus canonical
JSON having exactly `family`, `payload_sha256`, `policy_approvals`, and
`provenance`. The proposal stores that recomputed value. A frozen envelope's
`accepted_public_reproducibility_sha256` must equal the accepted proposal's
recomputed value; the accepted proposal self-hash still binds the complete
proposal envelope.

`policy_approvals` has exactly `registry_payload_sha256`,
`discrete_entry_sha256`, `admission_entry_sha256`, and
`preselection_envelope_sha256`. Its authority is a tracked registry with
create-only approval entries and one explicitly mutable atomic membership
index:

```text
src/dartwork_mpl/asset/color/oklab_authoring_policy_registry_v1/
  index.json
  entries/<entry_sha256>.json
  reviews/
    reports/<reviewer_report_sha256>.json
    input-bundles/<external_input_bundle_sha256>/manifest.json
    input-bundles/<external_input_bundle_sha256>/blobs/<raw_sha256>
    review-controls/<review_control_bundle_sha256>/manifest.json
    review-controls/<review_control_bundle_sha256>/blobs/<raw_sha256>
    review-evidence/<review_evidence_bundle_sha256>/manifest.json
    review-evidence/<review_evidence_bundle_sha256>/blobs/<raw_sha256>
```

Every tracked leaf in this layout, including the intentionally content-mutable
`index.json`, is a regular stage-0 Git blob with mode `100644`; directories
have no tracked mode. Immutable-entry/bundle semantics come from hashes,
no-replacement installation, and index reachability—not checkout write bits.

`index.json` has exactly `schema`, `revision`, `entries`, and
`registry_payload_sha256`, with schema
`oklab-authoring-policy-registry-index-v1`. `revision` is a non-Boolean
nonnegative integer equal to `len(entries)`; the tracked bootstrap is revision
zero with an empty array. Index references are sorted by UTF-8
`(family,policy_kind_rank,policy_id)`, where discrete has rank 0 and admission
rank 1, and that tuple is unique. Each reference has exactly `family`,
`policy_kind`, `policy_id`, `entry_path`, and `entry_sha256`; path is exactly
`entries/<entry_sha256>.json`, and duplicate path/hash is forbidden. The index
self-hash uses
`b"dartwork-mpl-authoring-policy-registry-index-v1\0"` plus canonical JSON with
only `registry_payload_sha256` omitted.

Every referenced entry is an immutable canonical JSON file with schema
`oklab-authoring-policy-approval-entry-v1`; its filename and index hash must
equal the independently recomputed entry self-hash, and its tuple fields must
equal the reference. An entry has exactly:

```text
schema, approval_id, family, policy_kind, policy_id, policy_record_sha256,
characterization_path, characterization_payload_sha256,
verification_evidence_raw_sha256, verification_evidence_sha256,
recipe_sha256, generation_policy_sha256, renderer_policy_sha256,
lut_input_sha256, lut_sha256, validation_truth_payload_sha256,
validation_truth_acceptance_sha256,
reviewer_a_path, reviewer_a_report_sha256,
reviewer_b_path, reviewer_b_report_sha256,
reviewer_a_external_input_manifest_path,
reviewer_a_external_input_bundle_sha256,
reviewer_a_execution_inputs_sha256,
reviewer_b_external_input_manifest_path,
reviewer_b_external_input_bundle_sha256,
reviewer_b_execution_inputs_sha256,
reviewer_a_control_manifest_path, reviewer_a_control_bundle_sha256,
reviewer_b_control_manifest_path, reviewer_b_control_bundle_sha256,
reviewer_a_evidence_manifest_path, reviewer_a_evidence_bundle_sha256,
reviewer_b_evidence_manifest_path, reviewer_b_evidence_bundle_sha256,
reviewed_source_fingerprint, reviewed_execution_snapshot_sha256,
archive_promotion_provenance, maintainer_approval, entry_sha256
```

`schema` is `oklab-authoring-policy-approval-entry-v1` and `policy_kind` is
`discrete` or `admission`; identifiers and family obey their
respective strict schemas. Policy-record hashes use
`b"dartwork-mpl-discrete-policy-v1\0"` or
`b"dartwork-mpl-admission-policy-v1\0"` plus the complete canonical policy.
For a discrete entry, `recipe_sha256`, `generation_policy_sha256`,
`renderer_policy_sha256`, `lut_input_sha256`, and `lut_sha256` are lowercase
hashes equal to its characterization and both validation-truth hashes are
null. For an admission entry those five fields are exactly null and
`validation_truth_payload_sha256` and
`validation_truth_acceptance_sha256` are the non-null immutable truth and
bootstrap-acceptance hashes below.
The characterization path is a unique tracked repo-relative POSIX regular
file. `verification_evidence_raw_sha256` is the raw hash of the exact ignored
verification evidence captured under Reviewer A's sole external-input role;
`verification_evidence_sha256` is its independently recomputed schema self-
hash. Reviewer B's historical copy, both reports/scopes, and the promotion
bundle must resolve those same bytes and hashes. Each reviewer path is exactly
`src/dartwork_mpl/asset/color/oklab_authoring_policy_registry_v1/reviews/reports/<matching-report-hash>.json`.
Each input/control/evidence manifest path is exactly under the matching
`src/dartwork_mpl/asset/color/oklab_authoring_policy_registry_v1/reviews/`
subtree shown above. A content-addressed bundle path
may be shared only when its hash and every byte are identical; in particular
Reviewer A's one-record verification-evidence input bundle is a real non-null
manifest, not an implied source-snapshot read.
Both stored `execution_inputs_sha256` values are independently recomputed from
the archived manifests and the reports.

`archive_promotion_provenance` is the same closed record used by baseline
acceptance/authority finalization and fixed-Y acceptance promotion and has
exactly:

```text
schema, promotion_kind, invocation_recipe, source_fingerprint, execution_snapshot,
execution_inputs, source_files, promotion_input_manifest_path,
maintainer_approval_raw_sha256, promotion_provenance_sha256
```

Its schema is `oklab-authoring-archive-promotion-provenance-v1`;
`promotion_kind` is `legacy-v5-baseline`,
`legacy-v5-baseline-authority`, `policy-registry`, `fixed-y-preinstall`,
`fixed-y-postinstall`, or `validation-oracle-truth-bootstrap`; and
`invocation_recipe` is the closed path-neutral recipe with executable role
`verified-archive-byte-transfer-machine` and the matching promotion operation.
Raw command, cwd, host executable, interpreter, environment, and path values
are private non-authoritative transport and are forbidden in this record. The
fingerprint, complete execution-snapshot record, and ordered source-file array
obey section 10 and equal the reviewed snapshot. `execution_inputs` is the full
`oklab-authoring-execution-inputs-v1` record for the promotion itself: its
control hash is null, its snapshot hash equals the embedded snapshot, and its
external hash equals the strictly parsed promotion-input manifest at the
canonical tracked path in `promotion_input_manifest_path`. That manifest
contains the promotion kind's complete role closure and exactly one
`maintainer-approval` record whose raw hash equals
`maintainer_approval_raw_sha256` and whose parsed value equals the surrounding
output's approval object.

The archive-promotion invocation registry is this exact six-row table. Every
row has executable role `verified-archive-byte-transfer-machine`, entry module
`dartwork_mpl._colors._authoring_archive_promotion`, and operand-role order
`source-snapshot, external-input-bundle, output-artifact-role`:

| `promotion_kind` | External bundle `invocation_kind` | Exact `operation_id` | Exact `output-artifact-role` value | Exact tracked promotion-input manifest |
|---|---|---|---|---|
| `legacy-v5-baseline` | `legacy-v5-baseline-promotion` | `legacy-v5-baseline-promotion` | `legacy-v5-baseline-archive-and-pair` | `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/legacy-v5-baseline-review-v1/archive/input-bundles/<external-input-bundle>/manifest.json` |
| `legacy-v5-baseline-authority` | `legacy-v5-baseline-authority-finalization` | `legacy-v5-baseline-authority-finalization` | `legacy-v5-baseline-promotion-review-and-authority-marker` | `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/legacy-v5-baseline-review-v1/promotion-review/input-bundles/<external-input-bundle>/manifest.json` |
| `policy-registry` | `policy-registry-promotion` | `policy-registry-promotion` | `policy-registry-archive-entry-and-index` | `src/dartwork_mpl/asset/color/oklab_authoring_policy_registry_v1/reviews/input-bundles/<external-input-bundle>/manifest.json` |
| `fixed-y-preinstall` | `fixed-y-acceptance-promotion` | `fixed-y-preinstall-promotion` | `fixed-y-preinstall-archive-and-acceptance` | `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/fixed-y-review-v1/archive/input-bundles/<external-input-bundle>/manifest.json` |
| `fixed-y-postinstall` | `fixed-y-acceptance-promotion` | `fixed-y-postinstall-promotion` | `fixed-y-postinstall-archive-and-acceptance` | `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/fixed-y-review-v1/archive/input-bundles/<external-input-bundle>/manifest.json` |
| `validation-oracle-truth-bootstrap` | `validation-truth-acceptance-promotion` | `validation-oracle-truth-bootstrap-promotion` | `validation-oracle-truth-archive-acceptance-and-asset` | `docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/validation-oracle-truth-review-v1/archive/input-bundles/<external-input-bundle>/manifest.json` |

`<external-input-bundle>` in this table is not caller substitution: it is
exactly `execution_inputs.external_input_bundle_sha256`. The first operand
value is exactly `execution_snapshot.execution_snapshot_sha256`; the second is
exactly that external-bundle hash; and the third is exactly the row's output-
role literal. These values are validated across their actual owners: the
external-input manifest supplies only `schema`, `invocation_kind`, `records`,
and `external_input_bundle_sha256`; enclosing provenance supplies
`promotion_kind` and `promotion_input_manifest_path`; and
`invocation_recipe` supplies executable role, entry module, operation ID, and
the ordered operands. Those owned values, the manifest's actual tracked
location, and the registry row must all match one and the same row. A field
combination assembled from different rows is invalid, and an attempt to place a
provenance/recipe field inside the strict manifest is an unknown-key failure.
The manifest's external-input role set and cardinality are the matching
`invocation_kind` row in section 10; there is no implicit promotion kind or
fallback bundle kind.

`verified-archive-byte-transfer-machine` is a closed deterministic transition,
not shorthand for Python behavior. Its only readable inputs are (a) the
immutable regular-file/symlink records of the hash-addressed execution snapshot
and (b) the immutable regular files in the hash-addressed external-input
bundle. It strict-parses the row's schemas and role closure, resolves every
source and external byte string by its recorded path/role and raw SHA-256,
recomputes every canonical-JSON and domain-separated SHA-256 preimage in the
enclosing lifecycle, and derives the complete ordered target-path/byte map
specified there. That map is an array of records having exactly `path`,
`git_mode`, `byte_count`, and `raw_sha256`, sorted by unsigned UTF-8 path bytes;
`git_mode` is `100644`, and the bytes themselves are retained alongside the
hashed public projection until post-install verification. It may copy an archived blob byte-for-byte or emit the exact
canonical JSON required by those schemas; locale-sensitive ordering, host path
ordering, timestamps, random values, network reads, ambient files, and
implementation-defined serialization are forbidden.

Before publication the machine holds the repo-scoped exclusive writer guard,
rehashes both captured inputs, and reconstructs the complete reviewed pre-write
repository state from `execution_snapshot`. The provenance
`source_fingerprint` always identifies that reviewed pre-write state; a retry
does not replace it with a fingerprint of partial output. Under the same guard,
the machine captures a transient current seven-field fingerprint and complete
root-path record map with section 10's exact algorithms. On an initial run the
current fingerprint and map must equal the reviewed values exactly. On a retry,
the current state is valid only if it equals the reviewed state overlaid with
one of the permitted partial states below: HEAD commit/tree, canonical Git
index bytes and every index entry remain exact; every path outside the derived
target map has identical presence, type, logical mode, and raw bytes; and every
target path is either its exact reviewed state or its exact derived final
`100644` byte state. The machine also derives `target_directory_set`, the
depth-then-unsigned-UTF-8-sorted set of fixed parent directories beneath the
repository root that are absent from the reviewed state but required by the
target map. An exact subset of those real, non-symlink directories is permitted
on retry; every such directory may contain only expected child directories or
present exact target leaves. Empty directories do not enter Git's seven-field
fingerprint, so this separate complete `lstat` audit is mandatory. The current
file-path union must equal the reviewed union plus the present new-target
subset—no tracked, standard-untracked, staged, deleted, renamed, or mode-only
non-target difference is allowed. Ignored paths remain
outside the source map and the broker forbids reading them except through the
captured external bundle. The machine independently rederives this overlay from
the reviewed snapshot and captured promotion bundle, serializes it through
section 10's exact status/index-patch/worktree-patch/raw-worktree and seven-
field algorithms, and requires the resulting expected fingerprint to equal the
transient current fingerprint. A hash comparison without the complete record-
map and directory-set comparison is invalid.

The abstract machine exposes exactly two tracked-file publication primitives.
Their host implementation is not permitted to weaken these semantics:

```text
publish_immutable_100644(path, bytes):
    prepare a private same-filesystem staging file outside the repository root
    write all bytes; set regular-file mode 100644; fsync the file
    atomically install at path with no-replace semantics
    fsync the target directory and the private staging directory
    outcome after power loss is exactly ABSENT or the complete 100644 bytes

replace_index_under_writer_guard(path, expected_old_bytes, new_bytes):
    under the writer guard, re-read and bit-compare expected_old_bytes
    prepare/write/mode/fsync a private same-filesystem staging file
    immediately re-read and bit-compare expected_old_bytes again
    atomically replace only path; fsync target and staging directories
    re-open and bit-compare new_bytes before releasing the writer guard
    outcome after power loss is exactly the complete old or new bytes
```

On the Linux V1 backend, immutable installation uses
`renameat2(RENAME_NOREPLACE)` and guarded index replacement uses same-filesystem
atomic rename from that private staging directory. The repo-scoped exclusive
writer guard is the concurrency authority boundary: every conforming publisher
of `index.json` enters the same abstract repo-scoped exclusive guard before its
first comparison and holds it through post-replacement verification and
directory sync. A backend must demonstrate mutual exclusion among conforming
publishers or fail preflight; its private lock transport is not evidence. Thus
two conforming writers serialize and the later stale expected value fails. This is
deliberately called guarded compare-then-replace, **not** filesystem compare-
and-swap: ordinary Linux rename cannot atomically predicate replacement on file
contents, and a non-cooperating process with direct filesystem write access is
outside this concurrency guarantee. Such a write may be detected by the final
or next integrity check, but the design does not claim it cannot occur or be
overwritten between comparison and rename.

A backend without equivalent
all-or-nothing, no-replace/replace, file-`fsync`, and directory-`fsync`
semantics fails before publication; copying directly to a target, a named temp
inside the repository, or delete-then-rename is forbidden. A private staging
orphan is outside the repository and has no authority or recovery input role.

Ignored live input/control/evidence bundles use a separate closed tree
primitive rather than pretending the tracked `100644` leaf primitive can
produce their operational modes:

```text
publish_live_bundle_0444_0555(bundle_path, manifest_bytes, blob_map):
    create one unique private same-filesystem staging directory outside repo
    create blobs/ privately; create every regular leaf with O_EXCL and nlink 1
    write/hash/fsync each blob in raw-SHA order; chmod 0444; fsync again
    write/hash/fsync manifest.json last; chmod 0444; fsync again
    chmod blobs/ then bundle root to 0555; fsync both bottom-up
    prepare/revalidate final parents by no-follow durable top-down mkdir rules
    atomically rename the complete root to bundle_path with no-replace semantics
    fsync the final parent and private staging parent
    re-open/revalidate every byte, mode, inode uniqueness, and directory entry
    outcome after power loss is exactly ABSENT or one complete sealed tree
```

The final tree has exactly `manifest.json`, `blobs/`, and the manifest-required
blob leaves; it has no empty directory, symlink, hard link, alternate manifest,
or extra entry. `manifest.json` is constructed only after every staged blob is
durable, and consumer launch occurs only after final-parent synchronization and
the post-install revalidation. If the final bundle already exists, the
publisher strict-parses and rehashes the complete tree, requires file modes
`0444`, directory modes `0555`, `st_nlink==1` for each regular leaf, and unique
leaf inodes. Because reopening a `0444` final leaf for writing is neither
portable nor permitted, Linux V1 then calls `syncfs` on a verified no-follow
descriptor in that bundle's filesystem, `fsync`s the bundle directories and
final parent bottom-up, repeats the checks, and only then returns an idempotent
no-op. A backend without an equivalent read-only-tree synchronization barrier
fails reuse rather than temporarily making a final leaf writable. A partial, differently moded,
aliased, extra, or byte-different final tree is fatal and untouched. A torn
private staging tree has no authority and is discarded/rebuilt. This primitive
is used identically by external-input, review-control, and review-evidence
bundles.

Before either tracked-file primitive, the machine applies `lstat` to every existing target-
path component, rejects every symlink, requires every existing parent component
to be a directory, and requires each existing target leaf to be a regular
`100644` file with the expected bytes. Missing directories are created one at a
time, top-down, only in `target_directory_set`, with no-replace semantics. After
each `mkdir`, it opens the new directory without following symlinks, `fsync`s
that directory and its containing directory, and rechecks the complete prefix.
After publishing any leaf, it `fsync`s every containing target directory
bottom-up through the repository root. Thus a crash may retain an exact expected
directory/leaf or lose it, but cannot authorize a torn leaf or an authority
record whose prerequisite directory entry was never made durable.

Alias checking is inode-complete for every non-directory leaf, not merely
path/type/byte comparison. For every regular file or symlink in the complete
reviewed-plus-overlay union, every existing target, and every private staging
file, the machine records `(st_dev, st_ino, st_nlink)` from `lstat`. It opens a
regular file with no-follow semantics and a symlink with Linux
`O_PATH|O_NOFOLLOW`, then requires `fstat` to match the same device/inode and
type. `st_nlink` must equal one, and no two audited leaf paths may share a
`(st_dev, st_ino)` pair. It repeats these
checks immediately before each prerequisite barrier and in the final
postcondition while holding the applicable guard. Consequently an exact-byte
hard link to another target, a non-target path, or a path outside the audited
tree is fatal rather than a valid retry state. Directory link counts are not
subject to the leaf `st_nlink==1` rule. As with guarded index
replacement, a hostile process that creates an alias after the final check is
not claimed to be excluded by an advisory lock; it makes the next integrity
check fail and is outside the conforming-publisher concurrency model.

Before publishing an authority marker or replacing the policy index, the
machine performs a durable-prerequisite barrier: it reparses and rehashes every
required earlier leaf through a no-follow descriptor, `fsync`s those files, and
`fsync`s their containing directories bottom-up. Only after that barrier may it
follow the enclosing lifecycle's exact order: baseline compatibility followed
by acceptance as the pre-review completion marker, or, after promotion B,
promotion-review closure and approval followed by the baseline authority
marker; policy entry followed by
`replace_index_under_writer_guard`; the corresponding fixed-Y acceptance (with preinstall
payload installation remaining the explicitly subsequent lifecycle step); or
truth bootstrap acceptance followed by recovery-safe create-only truth
installation. Every immutable item, including each completion/authority marker,
uses `publish_immutable_100644`; the final row-specific state is reparsed,
rehashed, and directory-barriered before success is reported.

Every durable lifecycle uses this exact phase order; each arrow includes the
complete file-and-bottom-up-directory prerequisite barrier just defined:

| Lifecycle | Durable phase order |
|---|---|
| tracked content-addressed bundle or standalone snapshot archive | all `blobs/*` leaves → `manifest.json` completion marker |
| ignored live input/control/evidence bundle | staged durable `blobs/*` → staged durable `manifest.json` → atomic sealed-tree install |
| baseline pre-review promotion | complete tracked preinstall promotion-input archive → compatibility asset → baseline acceptance |
| baseline post-review authority finalization | complete tracked promotion-review archive → tracked post-promotion approval → baseline authority marker |
| policy registry | complete tracked review/promotion archive → immutable entry → old-index durability/revalidation → `replace_index_under_writer_guard` |
| fixed-Y pre/post acceptance | complete tracked review/promotion archive → corresponding stage acceptance |
| validation truth bootstrap | complete tracked review/promotion archive → `bootstrap.json` acceptance → truth asset |
| frozen family | complete tracked captured promotion bundle → frozen envelope |
| fixed-Y scientific payload | fully validated durable preinstall acceptance → payload leaf |

Directory existence alone completes no phase. A content-addressed directory
without its durable manifest is an exact resumable subset; a manifest with a
missing or differing blob is fatal. `bootstrap.json` precedes truth because
the archived review closure authorizes the acceptance, and that durable
acceptance then authorizes truth installation. Before guarded policy-index
replacement, the old index
and every new prerequisite are reopened, verified, and synchronized; after
replacement the index directory is synchronized and the new bytes reparsed.

Existing byte-identical complete state is an idempotent no-op. The only
recoverable partial states are also closed: an exact subset of expected
new parent directories and content-addressed archive leaves before that row's
authority marker; for the
baseline pre-review promotion, a complete preinstall archive plus exact
compatibility with acceptance absent; for baseline authority finalization, an
exact promotion-review archive subset or the complete archive and approval with
the authority marker absent;
for policy, a complete archive and optional exact immutable entry while the
old index bytes/self-hash still equal the expected-old guard input; and for truth,
the exact bootstrap acceptance with truth absent. Retry first reconstructs the
complete expected target map from captured inputs, validates every existing
leaf, validates the full reviewed-plus-overlay predicate and unchanged
authority state above, creates only missing bytes in the same order, and
repeats both the overlay and full postcondition checks. A fixed-Y preinstall
acceptance without the later scientific payload is the separate documented
next-step boundary, not a partial archive-promotion output. Any other partial,
stale, aliased, differently moded, unexpected, or byte-different state is
fatal. The row's output-role literal denotes exactly that complete
postcondition, not a filename supplied to the host process.

An independent verifier applies this same transition to the two captured
inputs and requires exact equality of the derived target map, final authority
state, and installed bytes. Consequently host interpreter/runtime identity
cannot change or authorize an archive result and is intentionally neither
captured nor resolved; only the literal abstract-machine role, its closed
transition, the tracked entry-module bytes, both input identities, and the
verified postcondition are authority. These operations own no environment-v3
record.

Archive-promotion contract tests mutate every table cell, each of the three
operand roles and values, the executable role, the bundle `invocation_kind`,
manifest root, target ordering, and one byte in every derived output class.
They also attempt a `captured-python-runtime` substitution and every cross-row
combination. Recovery tests materialize every permitted partial state, then
independently inject a non-target raw-byte/mode change, HEAD change, index
change, standard-untracked path, staged target, out-of-order authority marker,
target byte/mode mismatch, unexpected directory, and private staging path inside
the repository. A power-loss fault harness cuts execution before and after every
parent `mkdir`, each partial/short staging write, staging-file `fsync`, atomic
no-replace link/rename, live-bundle file/directory `chmod` and second file
`fsync`, atomic whole-bundle no-replace rename, existing-tree `syncfs`,
staging-name removal, guarded
atomic replacement, every bottom-up directory `fsync`, each prerequisite
barrier, marker install, and marker/index-directory `fsync`, then
remounts/reopens a persistence model in
which unsynchronized file data, leaf dirents, and `mkdir` dirents are
independently losable.
Every reachable repository state must contain each leaf as either absent or the
complete expected 100644 bytes, must admit only the declared directory subset,
and must never retain an authority marker or new index without all of its
durable prerequisites. Only the exact reviewed-plus-overlay states may resume.
It must discard/rebuild torn private staging, leave a torn/differing final
target fatal and untouched, recreate a lost prerequisite or marker dirent on
retry, and prove that every permitted crash prefix retries to the exact
postcondition or a byte-level no-op. Any file/directory synchronization error
prevents the next phase. Strict verification must reject every mutation before publication; an injected
host interpreter/environment field is an unknown-key failure.

`promotion_provenance_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-archive-promotion-provenance-v1\0"` plus
canonical JSON of the complete record with only that field omitted. The
entry/acceptance self-hash therefore binds the promotion's complete
`ExecutionInputs`, while the nested self-hash permits it to be validated before
the outer completion marker exists. Archive-only promotions perform no color
or floating-point computation and deliberately have no environment-v3 record;
their authority is the closed byte-transfer transaction above.
The characterization file has the recognized closed schema for its kind and
its stored self-hash must equal `characterization_payload_sha256`. A discrete
characterization has exactly:

```text
schema, family, policy, policy_record_sha256, generation_policy_id,
recipe, recipe_sha256, generation_policy, generation_policy_sha256,
renderer_policy, renderer_policy_sha256, lut_input_sha256,
lut_sha256, lut_rows, duplicate_groups, peak_chroma, candidate_domain,
candidate_domain_sha256, selection_rows, selection_rows_sha256,
visual_strip, rationale, characterization_payload_sha256
```

Its schema is `oklab-authoring-discrete-policy-characterization-v1`; `family`
uses the family grammar; `policy` is the complete `DiscreteCandidatePolicy`;
and its record hash uses the discrete-policy domain above. `recipe` is the
complete family recipe, `generation_policy` is the complete generation policy,
and `renderer_policy` is the complete axis-matching renderer policy.
`generation_policy_id` equals `generation_policy.policy_id`. Their three
hashes use the exact preselection formulas below. `lut_input_sha256` uses the
proposal digest's exact preimage and therefore binds the complete recipe,
generation policy, and renderer policy rather than their labels. `lut_rows`
contains exactly
256 index-ordered records with exactly `index`, `hex`, `oklab_l`, and
`oklab_chroma`. Indices are `0..255`, hex values are lowercase `#rrggbb`, and
both coordinates use section 5.1's two-key binary64 form. `lut_sha256` is the
plain SHA-256 of canonical JSON of the reconstructed 256-hex array.

`duplicate_groups` contains exactly the RGB values occurring at least twice,
sorted by first position. Each group has exactly `hex` and `positions`; the
positions are the complete strictly increasing occurrence list. `peak_chroma`
is the recomputed maximum over all rows. `candidate_domain` and `selection_rows`
use the proposal schemas and ordering, and their two hashes are plain SHA-256 of
the respective complete canonical values. `visual_strip` has exactly `path`,
`media_type`, `byte_count`, and `sha256`; it names a tracked repo-relative POSIX
regular PNG, has media type `image/png`, a positive non-boolean byte count, and
its raw-byte hash. `rationale` has exactly `intended_use`, `lightness_min`,
`lightness_max`, `min_peak_chroma_fraction`, `achromatic_peak_chroma_max`, and
`max_search_states`; every value is a non-empty explanatory string. The
self-hash is SHA-256 of
`b"dartwork-mpl-oklab-authoring-discrete-policy-characterization-v1\0"` plus
the complete canonical artifact with only `characterization_payload_sha256`
omitted.

Parsing syntax and hashes is not enough to approve a discrete characterization.
The captured discrete verification invocation decodes every one of the 256
lowercase hex values to integer sRGB
channels, divides by 255 with the canonical binary64 association, applies the
canonical sRGB EOTF and OKLab construction kernel, and recomputes
`oklab_l` and `math.hypot(a,b)`. Both stored binary64 records must be bit-
identical. It then derives the complete duplicate groups from the 256 hex rows,
the exact first-occurrence order, `peak_chroma`, and the policy-admitted
candidate domain. Finally it runs the specified selector independently for
every `n=1..8`, derives every selection row and both aggregate hashes, and
requires byte identity with the artifact. The replay receives no stored domain,
peak, duplicate, or selected value as an input. Any mismatch is fatal.
Before decoding, that verifier recompiles the LUT from the stored complete recipe and
policies, requires the recomputed `lut_input_sha256` and `lut_sha256`, and
requires exact row bytes. Stored `lut_rows` are comparison output, never
generator input.

An admission characterization has exactly:

```text
schema, family, policy, policy_record_sha256, validation_policy,
validation_policy_sha256, validation_truth_payload_sha256,
validation_truth_acceptance_sha256,
reference_sets, rationale,
characterization_payload_sha256
```

Its schema is `oklab-authoring-admission-policy-characterization-v1`.
`policy` is the complete `AdmissionPolicy`; its hash uses the admission-policy
domain above. `validation_policy` is the complete recognized
`VALIDATION_ORACLE_V1`, and its hash uses the validation-policy domain in this
section. `validation_truth_payload_sha256` is the recomputed create-only truth
asset hash defined in section 8 and must equal the admission registry entry and
preselection. `validation_truth_acceptance_sha256` is the recomputed self-hash
of section 8's fixed-path tracked bootstrap acceptance and must equal the same
two downstream records. `reference_sets` is non-empty and uniquely sorted by the UTF-8 bytes of
`reference_set_id`. Each record has exactly `reference_set_id`, `source_path`,
`source_sha256`, `authority_assets_sha256`, `member_count`, `rows`, and
`reference_set_result_sha256`.
The ID is non-empty, source path is a tracked repo-relative POSIX regular file,
source hash covers its raw bytes, and member count is a positive non-boolean
integer. Rows are in exact `n=2..8` order and have exactly `n`,
`member_results`, `reference_min_normal_delta_e00`,
`reference_min_common_delta_e00`, and
`reference_min_tritan_delta_e00`; metrics use the binary64 form. A member
result has exactly `member_id`, `reference_family`,
`normal_min_delta_e00`, `common_min_delta_e00`,
`tritan_min_delta_e00`, and `validation_result_sha256`, and is sorted by the
source member order. Each reference minimum is derived as the exact binary64
minimum of the corresponding complete member-result column. The result hash is
SHA-256 of `b"dartwork-mpl-admission-reference-set-result-v1\0"` plus the
complete canonical reference-set record with only that hash omitted.

Every member `validation_result_sha256` is derived from a separate closed
object with exactly these 12 keys and no self-hash field:

```text
schema, validation_policy_sha256,
validation_truth_payload_sha256,
validation_truth_acceptance_sha256,
reference_set_id, member_id, reference_family, n, reference_hex,
normal_min_delta_e00, common_min_delta_e00, tritan_min_delta_e00
```

`schema` is
`oklab-admission-reference-member-validation-result-v1`.
`reference_hex` is the exact lowercase-hex row independently rederived from
the accepted shipped or frozen authority asset: an array of exactly `n`
lowercase `#rrggbb` strings in authority order. It is never caller-supplied.
The three metrics use section 5.1's defined two-key binary64 representation.
Policy,
truth, and bootstrap-acceptance hashes are independently reparsed before they
enter this preimage. Define:

```text
validation_result_sha256 = SHA256(
    b"dartwork-mpl-oklab-admission-reference-member-validation-result-v1\0" +
    canonical_json(the complete 12-key object)
)
```

There is no omitted field: the hash is stored only by the surrounding member
result. The preimage binds authority-derived row identity and replayed metrics
without pointing to the enclosing reference-set or characterization hash.

Every referenced source file has the closed schema
`oklab-admission-reference-source-v1` and exactly `schema`,
`reference_set_id`, `excluded_family`, `members`, and
`source_payload_sha256`. Its ID equals the containing result ID and
`excluded_family` equals the candidate characterization family. Members are a
non-empty array uniquely sorted by UTF-8
`(reference_family,member_id)`; each has exactly `member_id`,
`reference_family`, `intended_use_tags`, and `authority`. IDs and family
names are non-empty; `reference_family` must not equal `excluded_family`;
tags are a non-empty UTF-8-sorted unique array of non-empty strings. No inline
hex row is allowed.

`authority` is exactly one of two closed records. A shipped record has exactly
`kind="shipped-compatibility-v1"`, the literal path
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/color_v5_compatibility.json`,
`raw_sha256`, `compatibility_payload_sha256`, `baseline_commit`,
`baseline_git_tree_oid`, `baseline_tree_sha256`, `baseline_authority_commit`, the literal sibling
`acceptance_path`, `acceptance_raw_sha256`, `acceptance_sha256`, the literal
`authority_marker_path` from section 1.2, `authority_marker_raw_sha256`,
`authority_marker_sha256`, and `family`.
A frozen-authoring record has
exactly `kind="accepted-authoring-frozen-v1"`, canonical path
`src/dartwork_mpl/asset/color/oklab_authoring_frozen_v1/<family>.json`,
`raw_sha256`, `frozen_envelope_sha256`, and `family`. In both variants,
`authority.family == reference_family != excluded_family`. The shipped rows
are derived only from the strictly validated
`surfaces.discrete_hex[family][str(n)]`; frozen rows are derived only from the fully
accepted envelope's `payload.selection_rows`. Both produce exact `n=2..8`
lowercase-hex arrays. An unaccepted proposal, arbitrary file, alias, current
candidate artifact, or caller-supplied row is invalid.

This authority variant is unavailable during the document-only and baseline-
preinstall/promotion reviews. From compatibility migration onward, every
authority asset, its baseline acceptance, and its baseline authority marker
must already exist in the reviewed source snapshot and are included by
path/raw hash in policy scope; the baseline cannot be created and consumed as
authority in one semantic batch. Each shipped
authority use also applies section 3.6's common `A/H/P/S_C` ancestry,
tree-identity, and no-overlay rule through the invocation's captured authority
closure; copying identical rows into an unrelated history is not authority.
`authority_assets_sha256` is
SHA-256 of `b"dartwork-mpl-admission-authority-assets-v1\0"` plus canonical
JSON of the complete authority records in member order. For every `n`, each
derived reference hex array must also differ byte-for-byte from the paired
discrete characterization's candidate `selection_rows[n].hex`; an author
cannot obtain apparent independence by copying candidate bytes under an older
family/member label. Candidate recipe, policy, domain, selection, validation
result, proposal, and candidate-family bytes are otherwise forbidden in the
source schema. The self-hash uses
`b"dartwork-mpl-admission-reference-source-v1\0"` plus the complete source
with only `source_payload_sha256` omitted.

The captured admission verification invocation strictly parses that source and
every authority asset, recomputes
their raw/semantic hashes and the authority hash, derives all reference rows
and `member_count`, enforces candidate-row inequality, and runs the independently pinned
`VALIDATION_ORACLE_V1` over every member row. Each member metric and
`validation_result_sha256` is copied only from that replay; every aggregate
minimum and result hash is then rederived. The candidate being approved is not
an admissible reference member, directly or through a renamed field.

Admission `rationale` has exactly `intended_use` and `floor_rows`; intended use
is non-empty and rows are exact `n=2..8` order. Each rationale row has exactly
`n`, `normal_min_delta_e00`, `common_min_delta_e00`, and
`tritan_min_delta_e00`, with three non-empty explanatory strings rather than
numeric results. The top-level closed schema rejects recipe, LUT, domain,
selection, validation, proposal, and other candidate-result fields, so a
post-selection result cannot masquerade as a predeclared floor. Its self-hash
uses
`b"dartwork-mpl-oklab-authoring-admission-policy-characterization-v1\0"` plus
the complete canonical artifact with only `characterization_payload_sha256`
omitted. Registry loading requires the exact discrete/admission kind-to-schema
pairing and recomputes every nested and top-level hash.

Policy characterization numeric replay is a separately captured computation,
not an undeclared capability of the archive byte-transfer machine. Before
Reviewer A starts, exactly one of the two environment-v3 verification profiles
above reads the tracked characterization and its declared source dependencies
from the immutable snapshot and writes one ignored, ordinary-profile-`none`
evidence primary. It has exactly:

```text
schema, family, policy_kind, policy_id, policy_record_sha256,
characterization_path, characterization_raw_sha256,
characterization_payload_sha256, replay, provenance,
verification_evidence_sha256
```

The schema is
`oklab-authoring-discrete-policy-characterization-verification-v1` or
`oklab-authoring-admission-policy-characterization-verification-v1`, paired
exactly with `policy_kind="discrete"` or `"admission"`. Identifiers, path,
policy hash, and characterization semantic hash equal the strict parsed
characterization; `characterization_raw_sha256` is its ordinary tracked-file
hash. `provenance` is section 3's exact six-key invocation provenance and owns
this verifier's environment-v3 record, source fingerprint, execution snapshot,
execution inputs, and source files. The verifier's snapshot contains the
characterization and all of its declared tracked dependencies before the
ignored evidence exists. Its empty external-input bundle is real and hash-
bound. The evidence self-hash uses the schema-paired domain
`b"dartwork-mpl-oklab-discrete-policy-characterization-verification-v1\0"`
or
`b"dartwork-mpl-oklab-admission-policy-characterization-verification-v1\0"`
plus canonical JSON of the complete evidence with only
`verification_evidence_sha256` omitted.

A discrete `replay` has exactly `kind`, `policy_record_sha256`,
`recipe_sha256`, `generation_policy_sha256`, `renderer_policy_sha256`,
`lut_input_sha256`, `lut_sha256`, `lut_rows_sha256`,
`duplicate_groups_sha256`, `peak_chroma`, `candidate_domain_sha256`,
`selection_rows_sha256`, and `exact_match`. Kind is `discrete`; the first six
hashes and peak equal independently recomputed characterization fields.
`lut_rows_sha256` and `duplicate_groups_sha256` are ordinary SHA-256 of
canonical JSON of the complete independently recomputed arrays; domain and
selection hashes use their already defined formulas. `exact_match` is Boolean
true. The verifier recompiles the LUT before decoding, recomputes all 256 OKLab
rows, duplicate groups, peak chroma, candidate domain, and every `n=1..8`
selector result without using stored derived rows as numeric input, then
requires byte identity with the characterization. A mismatch or false result
publishes no evidence primary.

An admission `replay` has exactly `kind`, `policy_record_sha256`,
`validation_policy_sha256`, `validation_truth_payload_sha256`,
`validation_truth_acceptance_sha256`, `reference_sets_sha256`, and
`exact_match`. Kind is `admission`; `reference_sets_sha256` is ordinary SHA-256
of canonical JSON of the complete independently recomputed reference-set
array, and `exact_match` is Boolean true. The verifier reparses the fixed truth
and acceptance, independently derives every authority row, runs the accepted
validation oracle over every member, and recomputes every member result,
aggregate minimum, result hash, rationale-bound policy field, and complete
reference set before byte comparison. Stored metrics or rows are never numeric
inputs. A mismatch publishes nothing. Both profiles route every governed
transcendental through their retained inline arithmetic trace and are subject
to the same no-site startup and complete terminal-output-set handoff as all
other environment-v3 producers.

Reviewer A captures this exact evidence under its sole
`policy-characterization-verification-evidence` external-input role. Its raw
and semantic hashes enter both policy-review subjects/reports, the maintainer
walkthrough, and the final entry. Reviewer B and policy promotion reconstruct
the historical A bundle and require byte identity. The two policy reviewers
therefore assess a source-bound numeric replay; the later
`policy-registry-promotion` only strict-parses and cross-binds that accepted
evidence while performing its declared byte-transfer/index transition.

Registry promotion also enforces the complete identity chain, not merely
hash-shaped fields. For each entry,
`entry.family == characterization.family`,
`entry.policy_kind` equals the recognized characterization kind,
`entry.policy_id == characterization.policy.policy_id`, and
`entry.policy_record_sha256 == characterization.policy_record_sha256` equal
the independently recomputed complete policy hash. Both reviewer reports and
their scopes carry and equal the same family, kind, policy ID, policy hash, and
characterization hash. They also carry the verification evidence raw and
semantic hashes, equal the final entry, resolve the exact Reviewer-A external-
input blob, and require the evidence's policy/characterization identity and
execution snapshot to equal their common reviewed subject. For preselection,
the parsed
`recipe_sha256`, `generation_policy_sha256`, and `renderer_policy_sha256`
must equal the discrete entry and characterization values, and parsed
`policies.generation.policy_id` must equal the discrete characterization's
`generation_policy_id`. The entry's `lut_input_sha256` and `lut_sha256`
must equal the characterization. The complete parsed validation policy and its hash
must equal the admission characterization's `validation_policy` and
`validation_policy_sha256`; its `truth_id` and the strictly parsed truth
asset hash must equal `validation_truth_payload_sha256` in the admission
characterization, admission entry, and preselection. The strictly parsed
fixed-path bootstrap acceptance must likewise equal
`validation_truth_acceptance_sha256` in all three, and its truth raw and
semantic hashes must equal the tracked truth. The registry, entry,
characterization, reviews, and preselection therefore form one non-reusable
identity graph.

Proposal generation recompiles the LUT before importing the selector. Its
`digests.lut_input_sha256` and `digests.lut_sha256` must equal the discrete
entry/characterization values and its 256 rows must be byte-identical. A
difference aborts before candidate-domain derivation. `promotion-replay`
repeats that
sequence from captured recipe/policy bytes; it may not use characterization
rows as generator input.

The policy reviewer files are closed A/B envelopes. A has exactly
`schema`, `role`, `approval_id`, `family`, `policy_kind`, `policy_id`,
`reviewer_instance_id`,
`source_fingerprint_start`, `source_fingerprint_end`,
`source_fingerprint_post_write`, `execution_snapshot_sha256`,
`execution_inputs`, `review_execution`, `policy_record_sha256`,
`terminal_result_ordinal`, `terminal_result_sha256`,
`characterization_payload_sha256`, `verification_evidence_raw_sha256`,
`verification_evidence_sha256`, `verdict`, `findings`, and
`reviewer_a_report_sha256`. B has exactly `schema`, `role`, `approval_id`,
`family`, `policy_kind`, `policy_id`, `reviewer_instance_id`, the three source
fingerprints,
`execution_snapshot_sha256`, `execution_inputs`, `review_execution`,
`policy_record_sha256`, `terminal_result_ordinal`, `terminal_result_sha256`,
`characterization_payload_sha256`, `verification_evidence_raw_sha256`,
`verification_evidence_sha256`, `verdict`, `findings`,
`predecessor_reviewer_a_report_sha256`, and `reviewer_b_report_sha256`. Their
schemas/domains are respectively `oklab-authoring-policy-reviewer-a-v1` and
`oklab-authoring-policy-reviewer-b-v1`; the role is `reviewer-a` or
`reviewer-b`; self-hashing omits only the matching self-hash field. Section
3.6's closed finding, `ReviewExecution`, start/end/post-write, fresh-instance,
and sequential-predecessor rules apply unchanged. Both reports must PASS the
same policy/characterization/verification evidence/source snapshot; their
stage-specific execution inputs obey section 10's role table, and B must bind A's recomputed hash and
complete historical input, control, evidence, and completion-token closure.

Policy review reports and input/control/evidence bundles are first produced
under ignored build paths; none is added to the source tree between A and B.
After both PASS and explicit maintainer approval, a distinct policy-registry
promotion validates the normative role closure, terminal results, A/B reports,
both historical `ExecutionInputs`, every manifest/blob, completion token, and
B's byte-identical embedded copy of A's complete closure. It strict-parses the
captured verification evidence, recomputes its raw/semantic hashes and complete
environment/trace/owner hash chain, and requires all report, scope,
walkthrough, and entry cross-links; it performs no color arithmetic itself.
Its promotion bundle
also contains exactly the canonical maintainer-approval file. It constructs the
closed `archive_promotion_provenance`, installs the two reports, all six
historical input/control/evidence subtrees, and its own promotion-input subtree
at tracked create-only paths, and rehashes them. Only then does it install
`entries/<entry_sha256>.json` with no replacement. The entry's promotion path is
exactly under the registry `reviews/input-bundles/` layout and resolves the
same external hash as its nested `ExecutionInputs`. Byte-identical complete
installs are no-ops; any differing immutable path is fatal.
The complete archive passes section 3.5's durable prerequisite barrier before
the entry is published, and the entry passes a second barrier before any index
switch. Exact archive/entry orphans under the old index have zero authority and
are the only resumable pre-switch state.

`index.json` is the sole intentionally mutable registry file. Under the repo-
scoped exclusive writer guard, promotion captures and strictly validates its
expected old canonical bytes/self-hash, derives a new index preserving every
old reference byte-for-byte plus exactly one sorted new reference, and increments
`revision` by one. It first reopens, verifies, and synchronizes the old index
and the complete archive/entry closure, then uses section 3.5's
`replace_index_under_writer_guard`: write/mode/`fsync` same-filesystem private staging,
immediately recheck the old raw bytes/self-hash, atomically replace only
`index.json`, `fsync` the directory, and reparse the result. A
stale comparison by a second conforming, guard-obeying publisher fails. This is
not a claim of content-predicated CAS against a non-cooperating filesystem
writer. A crash before the switch may leave immutable orphan
files, which have zero authority; after the switch all referenced bytes already
exist. An already indexed identical tuple/hash is an idempotent no-op, while the
same tuple with different bytes is fatal. This expected source mutation occurs
only after A→B.

A subsequent preselection runs on a new post-install snapshot. Under one read
guard it parses `index.json`, recomputes `registry_payload_sha256`, resolves
exactly the requested family's indexed discrete/admission entries, reparses all
linked tracked artifacts including each entry's A/B historical input, control,
and evidence bundles, each entry's promotion-input bundle and canonical
maintainer-approval blob, and then
rereads the index requiring identical raw bytes/self-hash before sealing.
Directory presence or an orphan entry never authorizes policy. Current policy/
characterization bytes must reproduce the index/entry hashes and archived
review artifacts must reproduce their historical common fingerprint/snapshot;
the new registry-containing fingerprint need not equal that historical value.

`entry_sha256` is SHA-256 of
`b"dartwork-mpl-authoring-policy-approval-entry-v1\0"` plus the complete entry
with only that field omitted. `registry_payload_sha256` is the current strict
index self-hash defined above.
Promotion reparses every linked artifact, its own tracked promotion bundle, and
the captured approval bytes; recomputes all hashes; and requires the four-key
approval object and sequence checks above. The entry's common fingerprint and
snapshot equal both policy review reports and its archive-promotion provenance.
Reusing an ID with different policy bytes, characterization, reviews, snapshot,
promotion inputs, or approval is fatal.

Before selection, the preparation command atomically writes
`build/color-authoring/<family>/policy-preselection.json` and exits without
importing or invoking the selector or validation oracle. This closed envelope
has exactly:

```text
schema, family, recipe_sha256, generation_policy_sha256,
renderer_policy_sha256, validation_policy_sha256,
validation_truth_payload_sha256, validation_truth_acceptance_sha256,
lut_input_sha256, lut_sha256,
registry_payload_sha256, discrete_entry_sha256, admission_entry_sha256,
invocation_recipe, source_fingerprint, execution_snapshot_sha256, execution_inputs,
environment, source_files,
preselection_envelope_sha256
```

Its schema is `oklab-authoring-policy-preselection-v1`. `execution_inputs` is
section 10's record with the named source snapshot and an empty external-input
bundle. `environment` is the complete environment-v3 owner with
`invocation_kind="policy-preselection"`; `invocation_recipe` is the matching
closed path-neutral profile; `source_files` is the exact ordered path/hash array
covering the two startup bootstraps, both reviewed registries, the selected
project policy's required/optional module and `data_files` leaves, and any
sealed-package-shell initializer identities under the declared-
source hash; it is not equated with `project_imports` alone. `lut_input_sha256`
and `lut_sha256` are copied only after reparsing
the discrete characterization and registry entry and must equal both.
The validation-truth hash is copied only after strict parsing of the admission
characterization, registry entry, and literal truth path; all three must agree.
The acceptance hash is copied only after strict parsing of the literal
bootstrap-acceptance path and its complete archive; its truth hashes must agree
with the same three records and tracked truth.
All component hashes are lowercase 64-digit SHA-256 values with these
exact preimages:

```text
recipe_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-recipe-v1\0" +
    canonical_json(complete recipe)
)

generation_policy_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-generation-policy-v1\0" +
    canonical_json(complete policies.generation)
)

renderer_policy_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-renderer-policy-v1\0" +
    canonical_json({
        "coordinate_axis_kind": recipe.coordinate_axis.kind,
        "renderer_policy": policies.renderer,
    })
)

validation_policy_sha256 = SHA256(
    b"dartwork-mpl-validation-oracle-policy-v1\0" +
    canonical_json(complete policies.validation)
)
```

None of those four preimages omits a field.
`registry_payload_sha256`, `discrete_entry_sha256`, and
`admission_entry_sha256` are copied only after independently reparsing their
complete tracked objects and recomputing the registry/entry formulas above.
The envelope self-hash uses
`b"dartwork-mpl-authoring-policy-preselection-v1\0"` plus the complete
canonical envelope with only `preselection_envelope_sha256` omitted.

Proposal generation is a separate invocation that first captures the live
ignored preselection file into a role-complete external-input bundle and then
reparses only those captured bytes together with the tracked registry from the
named source snapshot. It refuses to import or invoke selection until every
recipe/policy and entry/review/approval link matches byte-for-byte. Historical
review fingerprints and source snapshots must agree with one another and their
archived bundles; the proposal's current post-install fingerprint and source
snapshot instead agree with the preselection envelope and current captured
policy bytes. The two generations are deliberately not equated.
The proposal strictly reparses the preselection environment and requires its
`base_runtime_environment_sha256` to equal proposal provenance; full runtime,
project imports, computation broker-read stream, environment hash, and trace
are invocation-specific and must
not be copied.
The proposal copies the three approval hashes unchanged. This process evidence
cannot prove that a person never ran a private experiment; it does prove that
no accepted proposal run selected a candidate before consuming the previously
reviewed and maintained policy bytes.

All evidence follows one three-layer publication model:

1. the **scientific payload** contains only recipe/policy/LUT/domain/selection/
   validation/oracle scientific values and their hashes;
2. **public reproducibility and governance** contains path-neutral source,
   runtime-content, invocation-recipe, policy/review, and acceptance records;
3. **private invocation evidence** contains collection details needed only
   while deriving or checking the public projection.

Only the first two layers may be serialized into a proposal, frozen family,
tracked review/archive, filename, Git object, or hash preimage. The private
class includes hostname, absolute path, cwd, raw argv or environment, sysconfig
root, loader path/install name, PID, device/inode/stat cache, capsule path,
retained descriptor, mount or namespace identifier,
VM address or load base, temporary name,
provider run/session/instance identifier, raw conversational transcript, raw
tool output, and arbitrary approval text—including any digest, encoding, or
equality oracle derived from one of those values. Private bytes remain in
memory or ignored short-lived storage and are destroyed after the transaction.
They are never copied, named, hashed, or linked from public/tracked objects
unless a later rule defines one exact typed content projection from a guarded
leaf. Such a projection publishes only its stated value: for example,
`platform.os_build_id` deliberately carries the sealed OS-release raw digest,
while CPU-info and platform-attestation raw digests remain private. No blanket
“private” label may erase an explicit projection or authorize an undeclared one.

The publisher constructs a typed public projection from the actual guarded
bytes in memory; it does not regex-redact a previously serialized private
record and never trusts a surviving caller-supplied hash. Every path-bearing
fact must resolve to one public class: project `(project, repo-relative path,
raw SHA-256)`, stdlib `(root role, relative path, file kind, raw SHA-256)`,
distribution `(normalized name, version, declared logical path, file kind,
raw SHA-256)`, native image `(semantic role, path-neutral sealed-mapping
projection, and sealed-file/kernel-memory content identity)`, or tool
`(semantic role, executable SHA-256, normalized version and capabilities)`. A
value that cannot be projected without exposing private transport fails
publication. The physical native capsule and its path map remain private
because they may contain unused candidates; only the complete actually loaded
mapping projection below is public.

Immediately before any durable write, scan the complete proposed tracked tree,
archive filenames/blobs, and newly reachable Git objects. Seed it with canaries
for the current hostname, home/repository/venv/temp/Python/Git/sysconfig roots,
loader/capsule names, descriptors, inode/mount/namespace/address/load-base facts,
raw argv, PIDs, subordinate UID/GID values, user-namespace identifiers,
provider identifiers, approval text, and raw
transcript/tool-output fragments. Neither a canary nor its SHA-256, path hex,
base64, or decoded equivalent may occur. Parse generated PNG/PDF/HTML metadata
rather than scanning only visible text. A fixture must run the same effective
runtime and source bytes under different repository/home/temp roots and
hostnames and produce byte-identical scientific payload, public provenance,
snapshot/archive, and frozen bytes. Failure publishes nothing.

The environment record separates common base-runtime identity from the actual
invocation-specific loaded closure and arithmetic trace. It has exactly:

```text
schema, invocation_kind, selected_artifact_lock_projection_sha256,
python, numpy, platform, native_execution,
dependency_discovery, runtime_distributions, runtime_dependencies,
floating_point, base_runtime_environment_sha256,
runtime_environment_sha256, arithmetic_trace, environment_sha256
```

`schema` is `oklab-authoring-environment-v3`; `invocation_kind` is one of
`legacy-baseline-extractor-a`, `legacy-baseline-extractor-b`,
`legacy-baseline-cross-extraction`,
`policy-preselection`, `proposal`, `comparison`,
`discrete-policy-characterization-verification`,
`admission-policy-characterization-verification`,
`characterization-generation`, `characterization-verification`, or
`promotion-replay`. `selected_artifact_lock_projection_sha256` is the
domain-separated hash of exactly the selected wheel identities in the complete
used-distribution closure, reconstructed from `runtime_distributions` below.
No raw whole-lock or complete-package-entry hash is a public field or public
hash input. Nested records have these exact keys:

Environment-v3 publication V1 is Linux-only. Before launching Python, the
native supervisor requires kernel `uname` system `Linux` and machine `x86_64`
or `aarch64`; every other host fails native preflight. The launched child must
then report `os_name="posix"`, `sys_platform="linux"`,
`uname_system="Linux"`, the same admitted `uname_machine`, and
`byteorder="little"`, or the private run fails. Every admitted ELF object must
likewise be ELF64 little-endian; an AArch64 big-endian userland is not a V1
lane. Darwin and every other platform produce no environment record,
candidate owner, or public provenance. A future Darwin lane requires a
separately reviewed execution boundary and coordinated schema and hash-domain
changes; no dormant Darwin record is valid under V1.

```text
python = {
    implementation, version, hexversion, build, compiler, cache_tag,
    soabi, multiarch, executable_sha256,
    base_stdlib_closure_records, base_stdlib_closure_count,
    base_stdlib_closure_sha256,
    stdlib_closure_records, stdlib_closure_count, stdlib_closure_sha256,
    process_executable_role, process_loader_role, runtime_library_role,
    math_origin_kind, math_origin,
    math_module_role, math_provider_role
}

numpy = {
    version, locked_artifact_identity, distribution_records,
    used_distribution_sha256,
    multiarray_umath_sha256,
    multiarray_role, build_config_sha256, cpu_baseline,
    cpu_dispatch_compiled, cpu_features_enabled
}

platform = {
    os_name, sys_platform, uname_system, uname_release, uname_machine,
    os_build_id, cpu_identity, byteorder
}

native_execution = {
    policy_id, seal_policy_id, vm_policy_id, process_split_policy_id,
    python_startup, control_preparation,
    terminal_handoff_policy_id, supervisor, launch_environment,
    base_mapping_records, base_mapping_record_count,
    base_mapping_records_sha256,
    mapping_records, mapping_record_count, mapping_records_sha256
}

python_startup = {
    policy_id, argv_tokens, argv_policy_sha256, cwd_role,
    bootstrap_source, stdlib_archive, flags,
    pre_broker_inputs, pre_broker_input_count, pre_broker_inputs_sha256,
    pre_broker_modules, pre_broker_module_count, pre_broker_modules_sha256,
    sys_path_stages, sys_path_stages_sha256
}

dependency_discovery = {
    policy_id, control_policy_id, entry_module, operation_sequence,
    package_dispatch, project_execution_policy,
    project_import_events, project_import_event_count,
    project_import_events_sha256, project_namespace_packages, project_imports,
    broker_read_records, broker_read_record_count,
    broker_read_records_sha256, base_broker_read_record_count,
    base_broker_read_records_sha256,
    base_module_records, base_module_record_count, base_module_records_sha256,
    module_records, module_record_count, module_records_sha256,
    module_guard_transition_records, module_guard_transition_count,
    module_guard_transition_records_sha256,
    base_dependency_records, base_dependency_record_count,
    base_dependency_records_sha256,
    dependency_record_count, dependency_records_sha256
}

floating_point = {
    sys_float_info, rounding_mode, subnormal_probe, numpy_geterr,
    determinism_environment
}

arithmetic_trace = {
    policy_id, records, record_count, records_sha256
}
```

`native_execution.process_split_policy_id` is exactly
`control-preparation-then-fresh-computation-v1`. One environment invocation is
one supervisor transaction containing **two sequential, non-overlapping child
lifetimes**, never one Python lifetime with a logical revocation:

1. a fresh, no-site `python-control-preparer` child receives the raw sealed
   control leaves, constructs and reconciles the private per-entry ownership
   index and private actual-read ledger, and emits exactly two public leaves:
   the base handoff and the complete preparation record that contains the
   invocation handoff described below;
2. at the preparer's terminal stop, while user space remains stopped, the
   supervisor copies and revalidates its private index, ledger, and public
   outputs into fresh supervisor-owned sealed leaves. It then kills and reaps
   that child and closes every preparer descriptor, mapping, root, and process
   handle; and
3. only after reap and a zero-overlap guard does the supervisor create a fresh
   CPython computation child. Raw request, OS-release, CPU-info, attestation,
   policy registries, computation-input inventory, provisioning witness, lock,
   wheel, metadata, located-entry, stdlib-inventory, and stdlib-entry leaves are
   absent from that child's mount, descriptor, argv, environment,
   address space, and inherited kernel objects. For a sealed-package-shell row,
   the two package-initializer leaves are absent as well and only their typed
   path/hash pairs cross the boundary. For an ordinary `scripts.*` row they
   remain ordinary captured project-source leaves and may execute only when the
   profile's project-execution policy explicitly permits them. The child receives
   the public handoffs plus individually sealed runtime/source/external leaves
   whose opens remain mediated by the supervisor's private index.

There is no `fork()` ancestry or reusable worker between the two children: each
starts through a distinct `clone3` plus exec boundary from the static
supervisor. They have different private tmpfs roots and subordinate
credentials; no file descriptor, anonymous/shared mapping, pipe endpoint,
socket, process handle, Python object, allocator arena, audit state, or loader
state crosses from the first child to the second. The supervisor retains only
sealed bytes and its own parsed private index/ledger. Deleting Python names, forcing
GC, zeroing a buffer, revoking an audit-hook capability, or asserting that a
frame is unreachable is explicitly insufficient. A lifetime overlap, shared
kernel object, unreaped preparer, or raw-control leaf reachable by the
computation child is fatal before CPython starts.

The preparer closes one private `ControlPreparationTransferManifestV1` last and
then enters its non-returning terminal stop. That manifest has exactly `schema`,
`private_index`, `private_control_ledger`, `base_handoff`,
`control_preparation`, and `transfer_manifest_sha256`; schema is
`oklab-authoring-private-control-preparation-transfer-v1`, and its self-hash
uses `b"dartwork-mpl-private-control-preparation-transfer-v1\0"` over the
complete object with only that field omitted. `private_index` has exactly
`schema`, `records`, `record_count`, and `records_sha256`, with schema
`oklab-authoring-private-entry-index-v1`. Each UTF-8 `(role,leaf_id)`-sorted
record has exactly `role`, `leaf_id`, `phase`, `open_policy`, `sealed_identity`,
and `public_template`; phase is `control-only` or `computation` and sealed
identity has exactly `byte_count` and `raw_sha256`.

`open_policy` is exactly one of
`control-singleton-v1`, `control-repeatable-input-v1`,
`control-ordered-shell-pair-v1`, `computation-base-handoff-once-v1`,
`computation-invocation-handoff-once-v1`,
or `computation-repeatable-input-v1`. The first policy admits one
open per indexed leaf ID only in its role's fixed singleton state; repeatable policies admit an
open only while the corresponding control/computation phase is active and log
every occurrence; the shell policy admits exactly the final adjacent root then
`_colors` pair; the two handoff policies admit respectively ordinal zero before
base import and one post-base/pre-source read. A success
advances the applicable state before user space resumes; a failed open does not
create a public record but any policy/state mismatch is terminal.

The role/policy pairing is closed. Every request/platform/policy/inventory/
witness/lock/selected-wheel/distribution-metadata/located-entry control leaf
uses `control-singleton-v1` once per indexed leaf; fixed-import `stdlib-entry`
leaves alone may use `control-repeatable-input-v1`; and the optional two
initializer roles use `control-ordered-shell-pair-v1`. `base-handoff` and `invocation-handoff` use
their respective once-only policies. `source-snapshot`, `external-input`,
`stdlib-runtime`, and `distribution-runtime` use
`computation-repeatable-input-v1`. No other role/policy pair is admitted.
Forbidden or control-only bytes are omitted from the computation index rather
than represented by a dead denial row.

For a control-only record `public_template` is null. For a computation record
it has exactly `root`, `role`, `path`, `byte_count`, and `raw_sha256`, using one
of the five public broker variants below and the same sealed identity. On a
successful open the supervisor injects exactly the next global `ordinal` as the
sixth key; no other field is synthesized or normalized. Thus the template is a
closed pre-ordinal schema, not an impossible claim to know the future ordinal.

The index `role` is exactly one of the private-control roles defined below or
one of `base-handoff`, `invocation-handoff`, `source-snapshot`,
`external-input`, `stdlib-runtime`, and `distribution-runtime`. Leaf IDs are
path-neutral and unique: singleton controls use `control/<role>`, repeated
control candidates use `control/<role>/<eight lowercase decimal digits>`;
computation inventory rows use `source/<eight digits>` or
`external/<eight digits>` in their sorted inventory order; runtime file rows
use `runtime/<eight digits>` in manifest-file order; and handoffs use exactly
`handoff/base` and `handoff/invocation`. A role/ID prefix mismatch, gap,
duplicate, alias, or ID derived from a physical path is fatal.

Before launching the preparer, the supervisor derives one sealed private
`ComputationInputInventoryV1` leaf from the already verified execution snapshot
and external-input bundle. It has exactly `schema`, `source_records`,
`external_records`, `record_count`, and `records_sha256`; schema is
`oklab-authoring-private-computation-input-inventory-v1`. Each UTF-8-path-sorted
source record has exactly `leaf_id`, `path`, `byte_count`, `raw_sha256`, and
`availability`, where availability is `control-only`,
`computation-pre-broker`, or `computation-brokered`. Those classes are exactly
the control bootstrap/registries and sealed-package-shell initializer records,
the computation bootstrap, and the selected project policy's required/optional module plus
`data_files` leaves respectively. The three sets are disjoint and their union
must equal the predeclared `source_files`; an uncategorized or multiply
categorized path fails. Each
`(role,path)`-sorted external record has exactly `leaf_id`, `role`, `path`,
`byte_count`, and `raw_sha256` and is computation-brokered. Counts cover both
arrays and the digest uses
`b"dartwork-mpl-private-computation-input-inventory-v1\0"` over an object
containing exactly those two arrays. The inventory contains no physical path,
descriptor, unused output, or runtime-distribution entry.

The preparer reads that leaf once as control record six. Before computation it
can validate only the predeclared snapshot: it requires the source records to
equal `source_files` and the static bootstrap/registry/policy/shell partition
above, and requires external records to equal the exact invocation bundle. It
does not claim to know the future broker-read subset. It then builds the complete
index without opening computation project/external bytes. It adds computation
records for exactly the `computation-brokered` source rows and all external
rows; the computation bootstrap remains startup-owned, and control-only rows
are absent from the computation index (their separate control-role records
remain). It adds one runtime computation record for every
manifest file node and finally the two generated handoff leaves. The complete
index set is therefore exactly control leaves union selected computation
inventory union runtime-manifest files union two handoffs. The supervisor may
rehash and rebind those same leaf IDs to fresh sealed copies after reap, but may
not add, drop, rename, merge, or augment an index record. Exact set equality is
checked before computation launch. At terminal reconciliation, every realized
source read must be a computation-brokered inventory row, every executed module
must be in the module arrays, every non-module source read must be in
`data_files`, and the realized reads plus the static categories must reproduce
the closed six-source union; an unused optional module/data row remains
declared but need not be opened.

Count is the array length and the private digest uses
`b"dartwork-mpl-private-entry-index-records-v1\0"`. No physical path, fd, inode,
or address is an index value; the supervisor separately binds each leaf ID to
its sealed descriptor. The ledger is the exact array below, and the two public
members are the canonical objects below. While user space remains stopped, the supervisor
copies every member into fresh supervisor-owned fully sealed leaves, rehashes
and reparses them, proves exact set and cross-link equality, kills/reaps the
preparer, and closes every preparer tmpfs, transfer descriptor, mapping, and
process handle before the computation `clone3`. The private manifest, its hash,
the index, and the ledger are never mounted into computation, serialized into
any public object, archived, or used as a public hash preimage. Their transient
private canonical transfer serialization is the exact object just defined. A partial transfer, reopened
preparer path, shared output mapping, or computation launch before this close-
and-reap barrier is fatal.

The control preparer is a distinct CPython process because V1 deliberately uses
the captured `importlib.metadata.Distribution.files` and `locate_file()`
semantics as installed-distribution authority. It loads neither NumPy nor any
project module; treating a separately implemented native wheel/RECORD parser as
equivalent would require a new ownership policy. Its Python/startup/stdlib/
extension/native closure is therefore public common-base evidence rather than
an unbound helper.
`native_execution.control_preparation` has exactly:

```text
schema, policy_id, base_handoff, invocation_handoff,
control_preparation_sha256
```

Its schema is `oklab-authoring-control-preparation-v1` and its policy ID is
`sealed-native-control-preparation-v1`. `base_handoff` has exactly:

```text
schema, process_split_policy_id, control_policy_id,
computation_broker_policy_id, receipt_policy_id,
base_closure_transfer_policy_id, final_closure_transfer_policy_id, preparer,
provisioning, runtime_import_manifest, platform, base_handoff_sha256
```

Its schema is `oklab-authoring-control-base-handoff-v1`; the six policy IDs
after `schema`, in field order, are the process-split ID above,
`brokered-control-preparation-inputs-v1`,
`brokered-computation-dependency-discovery-v1`,
`supervisor-used-read-receipts-v1`,
`supervisor-base-ready-closure-transfer-v1`, and
`supervisor-final-runtime-closure-transfer-v1`. `preparer` has exactly:

```text
role, python, python_startup, launch_environment, input_role_grammar,
stdlib_closure_records, stdlib_closure_count, stdlib_closure_sha256,
mapping_records, mapping_record_count, mapping_records_sha256,
dependency_records, dependency_record_count, dependency_records_sha256
```

Its role is `python-control-preparer`. `python` is the exact scalar projection
`{implementation,version,hexversion,build,compiler,cache_tag,soabi,multiarch,
executable_sha256}` using the computation record's extractors and the same
sealed process-executable identity. `launch_environment` is the complete closed
from-empty behavior record below. `input_role_grammar` is the fixed policy
literal `request-platform-policies-computation-inventory-provisioning-lock-distribution-stdlib-optional-shell-v1`; it
contains no actual leaf, multiplicity, initializer presence, or invocation-
specific order. Those facts live only in the private transfer manifest and
typed invocation projection.

`python_startup` has exactly the computation startup record's fifteen keys,
but is a distinct closed variant rather than a reference to the computation
values. Its policy ID is `cpython-no-site-control-preparer-v1`, cwd role is
`empty-control-cwd`, and `bootstrap_source` is exactly
`{"role":"control-preparer-bootstrap",
"path":"src/dartwork_mpl/_authoring_control_prepare.py",
"sha256":<that captured source leaf's raw SHA-256>}`. Its argv is the same
closed `-S/-s/-B/-X utf8` form with role `control-preparer-bootstrap` in place
of `startup-bootstrap`. The argv digest uses
`b"dartwork-mpl-control-preparer-startup-argv-v1\0"`.

The preparer pre-broker-input grammar uses root role
`control-preparer-bootstrap-dir`, relative path
is `_authoring_control_prepare.py`, file kind is `source`, and hash equals the
preparer `bootstrap_source.sha256`. Its pre-broker-module origin kind and
origin are respectively `control-preparer-bootstrap` and
`{"role":"control-preparer-bootstrap"}`.

Its path-stage array has exactly `interpreter-initial`, `broker-ready`, and
`control-ready`. Every present role has `group_index=0`. Initial path entries
are exactly `control-preparer-bootstrap-dir`, optional `stdlib-archive`,
`stdlib-root`, then optional distinct `platstdlib-root`. Broker-ready removes
only the bootstrap directory. Control-ready appends
`distribution-purelib` and then optional distinct `distribution-platlib`.
Those last two path-neutral role names resolve to the preparer's private sealed
installed roots, never to the computation's later public synthesized trees;
equal stdlib or distribution root pairs coalesce to the first role exactly as
in the computation grammar. No source-snapshot role occurs.

All three preparer meta-path arrays are exactly built-in importer, frozen
importer, then ordinary path finder. All three path-hook arrays are exactly
zipimporter then file-finder; `manifest-runtime-path-hook` is computation-only
and invalid here. At initial, the bootstrap entry uses file-finder, an optional
archive uses zipimporter, and each stdlib role uses file-finder. Broker-ready
retains the archive/stdlib assignments; control-ready additionally assigns
file-finder to both present private distribution roles. Each transition clears
and rebuilds the complete cache under the private broker, and every finder/hook
stdlib origin cross-links the sibling preparer closure.

Its input, module, and path-stage digests use respectively
`b"dartwork-mpl-control-preparer-pre-broker-inputs-v1\0"`,
`b"dartwork-mpl-control-preparer-pre-broker-modules-v1\0"`, and
`b"dartwork-mpl-control-preparer-sys-path-stages-v1\0"`. All other exact
flags, no-site exclusions, optional empty stdlib archive, finder/hook/cache
identity, canonical serialization, and recheck rules not explicitly replaced
above are byte-for-byte the computation grammar. Every stdlib input/module
origin in this record resolves to the sibling
`preparer.stdlib_closure_records`, never to the future computation child's
`python.stdlib_closure_records`. A computation bootstrap role, filename, four-
stage path array, manifest path hook, computation-closure cross-link, or
computation hash domain in this preparer record is invalid.

After broker-ready it imports exactly once, in this order, `sys`, `os`,
`platform`, `sysconfig`, `json`, `hashlib`, `importlib`,
`importlib.metadata`, `pathlib`, `struct`, and `types`; no NumPy or project
module is permitted. The complete post-preparation stdlib closure remains
inline and hashes under `dartwork-mpl-control-preparer-stdlib-closure-v1\0`.
The complete loaded mapping and dependency arrays use the same path-neutral
record grammars as computation under distinct
`dartwork-mpl-control-preparer-mappings-v1\0` and
`dartwork-mpl-control-preparer-loaded-images-v1\0` domains. They include every
extension/DSO reached by those imports plus the mandatory admitted vDSO; no
core-only subset is substituted. Counts are exact array lengths. Any preparer
source, stdlib module, native mapping, startup stage, or launch behavior omitted
from this inline closure changes the base handoff and common base hash.

`base_handoff.provisioning` has exactly `schema`, `policy_id`, `artifacts`, and
`provisioning_sha256`. Schema is `oklab-authoring-wheel-provisioning-v2`, policy
ID is `sealed-wheel-provisioning-v2`, and `artifacts` is the normalized-name-
sorted unique array of exact locked-wheel identities required by the selected
base-import profile. Its self-hash uses
`b"dartwork-mpl-wheel-provisioning-v2\0"` over the complete object with only
`provisioning_sha256` omitted. The array must later equal that profile's
`artifact_identities`; it is prospective common-base identity, not an observed
used-distribution projection.

Before either Python child exists, the same self-sealed static supervisor
strict-parses the reviewed base-profile registry, resolves the request's exact
`base_import_profile_id`, and provisions one fresh empty private installation
root directly from exactly that profile's supplied fully sealed wheel leaves.
The preparer later independently requires that same row to be the unique
Python/platform match. No external installer, cache, index, network, live
environment, or preexisting installed file participates. The exact parser is
the bounds-checked, memory-safe `wheel-provisioner-parser-v2` component compiled
into the self-sealed supervisor; it accepts an immutable sealed-byte slice,
uses checked integer arithmetic and streaming CRC/SHA/decompression, exposes no
callback or filesystem path, and is identity-bound by the supervisor executable
hash plus `sealed-wheel-provisioning-v2` capability. A general ZIP library,
zlib callback, installer, or alternate parser is not equivalent under this ID.

The archive grammar is closed. Each wheel is 1..536,870,912 bytes and contains
1..65,535 members; one member may expand to at most 268,435,456 bytes and the
sum of uncompressed regular-member sizes is at most 1,073,741,824 bytes. The
classic EOCD is exactly the final 22 bytes, has zero disk numbers and comment
length, equal on-disk/total nonzero entry counts, no ZIP64 sentinel, and names a
central-directory range ending immediately at that EOCD. Central entries are
contiguous, consume that whole range, and are strictly increasing by local-
header offset. Their local-header-plus-data ranges are disjoint, start at byte
zero, end exactly at the central directory, and contain no prefix, gap,
descriptor, overlay, or trailing byte. Every central/local pair has the exact
same raw name, general-purpose flags, method, CRC-32, and compressed and
uncompressed sizes; both extra fields and the central comment are empty, disk
start is zero, and the only admitted flag values are `0x0000` and the UTF-8 bit
`0x0800`. Methods are stored `0` or raw RFC-1951 DEFLATE `8`. Stored sizes are
equal. DEFLATE must consume its entire byte range, reach one final block, have
only zero terminal padding bits, and yield exactly the declared size. IEEE
CRC-32 and SHA-256 are recomputed over the yielded bytes before any install
leaf exists. Every offset, addition, size, output quota, or decompression error
fails before allocation or write beyond the stated bounds.

Names are the printable ASCII subset of UTF-8 and round-trip byte-identically.
A regular name has no trailing slash; a directory name has one trailing slash,
method `0`, zero sizes/CRC, and no data. After removing that directory marker,
every name is a nonempty relative POSIX component sequence with no NUL/control,
empty, `.`, `..`, backslash, or absolute component. Raw names and ASCII-
case-folded names are each unique. Central external attributes may denote only
a regular file, directory, or zero/unspecified type consistent with that name;
Unix symlink and every special type fail. Directory members create no installed
leaf; missing parent directories are deterministically synthesized read-only
from regular-member prefixes and carry no file identity. A first path component
ending in `.data`, a `.pyc`/`.pyo` member, a second/case-aliased member, and every
cross-wheel output collision fail. Thus V1 deliberately excludes wheel data-
scheme relocation, generated entry-point scripts, installed-RECORD rewriting,
symlinks, and generated bytecode.

Exactly one ASCII-case-unique `.dist-info` directory contains exactly one
regular `METADATA`, `WHEEL`, and `RECORD` member. `METADATA` and `WHEEL` are
strict UTF-8 with LF-only lines and a terminal LF. Their header block ends at
the first empty physical line. A new header begins with a nonempty ASCII field
name matching `[A-Za-z0-9-]+`, then exact `: `, then a possibly empty UTF-8
value containing no NUL, CR, DEL, or C0 control other than HTAB. A continuation
line begins with SP or HTAB, requires a preceding header, and remains attached
to that header; every other physical-line form fails. The parser retains exact
physical bytes and need not semantically unfold an irrelevant field. Each
physical header/continuation line is at most 1,048,576 bytes excluding its LF.
A logical field's byte count is the sum of every attached physical line plus
one LF byte per line. The complete header-section byte count runs from its first
byte through the empty separator's LF inclusive. Each logical field and the
complete header section are at most 16,777,216 bytes, and the combined header-
plus-continuation line count, excluding the separator, is at most 65,535. The
body after that separator is opaque valid UTF-8 and remains bound by the wheel
member/archive hashes. This is a closed deterministic subset that deliberately
does not claim general RFC-email or `email.parser` equivalence.

Header names compare ASCII-case-insensitively. `METADATA` has exactly one each
of `Metadata-Version`, `Name`, and `Version`; `WHEEL` has exactly one
`Root-Is-Purelib`. Each required identity-bearing header is one physical line:
a duplicate of one or a continuation line attached to one of those four names
fails. The
`Root-Is-Purelib` value is lowercase `true` or `false`. The normalized Name and
literal Version must equal the locked identity. Other single- or multiple-use
headers are opaque and may use the bounded continuation form. V1 project names are
ASCII, begin/end alphanumeric, and normalize by lowercasing ASCII then replacing
each maximal `[-_.]+` run with one `-`; this is also the public
`normalized_name` algorithm. V1 versions match
`[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?`
and are already lowercase canonical strings. The one required basename is
exactly `normalized_name.replace("-","_") + "-" + version + ".dist-info"`;
no spelling derived from the unnormalized METADATA Name is equivalent.

`RECORD` is strict UTF-8 CSV with one per-file delimiter selected by its first
line ending: exact LF or exact CRLF. Every line, including the last, uses that
same delimiter and the file ends with it. LF mode forbids every CR; CRLF mode
requires every CR to be immediately followed by LF and every LF to be
immediately preceded by CR. Bare, mixed, or missing-terminal delimiters fail.
The parser removes only the selected line delimiter before parsing each record.
Each resulting physical record contains exactly three fields. A field is either
unquoted bytes excluding quote/comma/CR/LF, or a double-quoted field in which a
literal quote is exactly `""` and CR/LF is forbidden; there are no escapes,
spaces outside quotes, or multiline fields. Decoded paths are unique and equal byte-for-byte to canonical regular-
member names. Every non-directory member appears exactly once. A non-`RECORD`
row has exactly `sha256=<43 URL-safe-base64 characters without padding>` that
decodes to the recomputed 32 bytes, plus a canonical unsigned decimal size with
no leading zero except `0`. The `RECORD` row alone has empty hash and size.
Directory, missing, extra, duplicate, differently quoted-to-an-alias, other-
algorithm, padded-base64, or mismatched rows fail. The Boolean selects
respectively `distribution-purelib` or `distribution-platlib`; every regular
member, including the three metadata files and unchanged `RECORD`, installs
byte-identically at its archive-relative name. No member is rewritten, omitted,
generated, relocated, or installed twice.

While doing so the supervisor constructs one private
`WheelProvisioningWitnessV2` having exactly `schema`, `policy_id`, `records`,
`record_count`, `records_sha256`, and `witness_sha256`. Schema is
`oklab-authoring-wheel-provisioning-witness-v2` and policy ID is
`sealed-wheel-provisioning-v2`. Each install-ordinal-
sorted record has exactly `install_ordinal`, `wheel_leaf_id`,
`locked_artifact_identity`, `root_role`, `metadata_member`, `record_member`,
`installed_files`, `installed_file_count`, and `installed_files_sha256`. Each
member-path-sorted installed-file record has exactly `member_path`,
`installed_leaf_id`, `byte_count`, and `raw_sha256`; leaf IDs are
`installed/<eight-digit install ordinal>/<eight-digit member ordinal>`.
Counts are exact; installed-file and record-array digests use respectively
`b"dartwork-mpl-wheel-provisioning-installed-files-v2\0"` and
`b"dartwork-mpl-wheel-provisioning-records-v2\0"`; the witness self-hash uses
`b"dartwork-mpl-wheel-provisioning-witness-v2\0"` with only
`witness_sha256` omitted. The supervisor then makes every installed leaf/root
read-only and seals the complete input set. The witness is a control-only leaf:
the preparer reads it once, rehashes each selected wheel/metadata/located entry,
reparses lock and installed distribution identity, and requires one unique
member-to-installed-leaf association. It never becomes public; the exact
artifact array and later used-file records are its typed consequences.

`runtime_import_manifest` has exactly `schema`, `policy_id`, `profile_id`,
`registry_source`, `records`, `record_count`, and `records_sha256`; schema is
`oklab-authoring-runtime-import-manifest-v1` and policy ID is
`public-synthesized-runtime-import-tree-v1`. Records are sorted by raw UTF-8
`[root_role,logical_path]` and have exactly `root_role`, `logical_path`,
`node_kind`, `mode`, `byte_count`, `content_sha256`, `owner`, and
`module_binding`. Root role is one of `stdlib-root`, `platstdlib-root`,
`distribution-purelib`, or `distribution-platlib`; logical path is canonical
relative POSIX; node kind is `directory` or `regular-file`; mode is respectively
`0555` or `0444` as a four-character string. A directory has null byte count,
content hash, owner, and module binding. A file has a non-Boolean nonnegative
byte count, its raw SHA-256, one exact prospective owner object, and either one
exact module binding or null. A stdlib owner has
exactly `kind`, `root_role`, `relative_path`, and `file_kind`, with
`kind="stdlib"`, root/path equal to the enclosing record, and file kind
`source`, `bytecode`, `extension`, or `regular-data`. A distribution owner has exactly
`kind`, `normalized_name`, `version`, `locked_artifact_identity`,
`declared_path`, and `file_kind`, with `kind="distribution-candidate"`; its
identity/path/kind are the exact private-index projection that a later actual
module origin or broker read must use to construct a public used-file row.
Distribution file kind is exactly `source`, `extension`, or `regular-data`;
packaged bytecode is unreachable because the sole provisioner rejects it. A
regular file that is both module-backed and data-read has
one intrinsic source/bytecode/extension kind, never `regular-data`; a data-only
file is `regular-data`. Any disagreement between suffix-independent loader/
mapping classification, the prospective owner, a later broker-read role, and a
used-file row is fatal. Symlinks, devices, empty/dot/dot-dot components,
implicit directories, duplicate paths/modules, duplicate file-owner tuples,
one owner at two logical nodes, and any unlisted tree node are forbidden.

`module_binding` is null exactly for `regular-data`; otherwise it has exactly
`module_name`, `module_kind`, and `loader_id`. The name is a nonempty dotted
sequence of printable-ASCII Python identifiers and is globally unique across
the manifest. Kind is `module` or `package`. Loader is respectively
`manifest-source-loader-v1`, `manifest-sourceless-loader-v1`, or
`manifest-extension-loader-v1` for source, stdlib bytecode, or extension; no
other file-kind/loader pairing is valid. A package path's basename is exactly
`__init__.py`, `__init__.<python.cache_tag>.pyc` beneath `__pycache__`, or
`__init__.<python.soabi>.so`; a module path's basename is the final name
component plus the corresponding suffix and is never an `__init__` spelling.
For a non-top-level name, the preceding dotted components equal the contiguous
parent-directory suffix. A top-level stdlib extension may additionally have a
fixed registry-declared prefix such as `lib-dynload/`; the explicit binding,
not a directory scan, remains authority. Distribution bytecode, suffix
guessing, two bindings for one name, one name at two files, and a directory-
backed namespace binding are forbidden.

The manifest hook returns a spec only for that exact binding. It sets `name` to
`module_name`, `origin` and `__file__` to the path-neutral fixed string
`/__dartwork_runtime__/<root_role>/<logical_path>`, `has_location=true`,
and `loader_state=null`. For a source binding, `ModuleSpec.cached` and the
present module attribute `__cached__` both equal the fixed origin's parent plus
`/__pycache__/<source-stem>.<python.cache_tag>.pyc`; for a stdlib sourceless-
bytecode binding both are present and equal the fixed origin. For an extension,
`ModuleSpec.cached` is null and the module attribute `__cached__` is absent,
matching stock CPython 3.12 `_init_module_attrs` rather than inventing a
present-null attribute. The source rule applies equally to `__init__.py`, whose
source stem is `__init__`. No optimization suffix or `sys.pycache_prefix` participates,
and the declared cache path is metadata only: V1 neither reads, writes, nor
materializes it. `__package__` is the parent name for a module and the complete
name for a package. A module has `submodule_search_locations=null` and no
`__path__`; a package uses the same immutable one-item sequence containing the
fixed origin's parent directory for both fields. The
loader implementation is the named sealed loader in the exact interpreter/
bootstrap identity: it broker-opens only the bound file, applies that
interpreter's strict source, sourceless-bytecode, or extension execution path,
and may not fall back, generate bytecode, enumerate a directory, synthesize a
namespace, or alter the spec. Directory nodes answer only manifest child
queries. A missing binding is a deterministic negative lookup even if a
similarly named file exists physically.

The reviewed registry leaf
`src/dartwork_mpl/_authoring_base_import_profiles.json` has exactly `schema`,
`profiles`, `profile_count`, and `profiles_sha256`, with schema
`oklab-authoring-base-import-profile-registry-v1`. Profiles are UTF-8-
`profile_id` sorted and each has exactly `profile_id`, `python_key`,
`platform_key`, `artifact_identities`, `entries`, `entry_count`, and
`entries_sha256`. `python_key` is exactly the preparer-available scalar object
`{implementation,version,cache_tag,soabi,multiarch,executable_sha256}`;
implementation is `cpython`, version major is `3`, minor is at least `12`, and
the exact executable/profile pair supplies the admitted dict-watcher/import-core
diagnostic ABI and reproducibility profile. A 3.10/3.11 or alternate-
interpreter row is invalid in V1 evidence; this is an exact-instrumentation
requirement, not a hostile same-process security claim.
`platform_key` is the complete typed public `platform` object;
`artifact_identities` is the nonempty normalized-name-sorted unique array of
exact selected-wheel identities required by the profile and includes NumPy.
It deliberately contains no post-import NumPy build configuration, enabled CPU
feature set, used-file row, or computation-derived value.

Each profile `entries` member is one of two exact tagged forms. A stdlib entry
has exactly `kind="stdlib"`, `root_role`, `relative_path`, `file_kind`, and
`module_binding`; root is stdlib/platstdlib, relative path is canonical and later
equals the manifest logical path, and file kind/module binding use the grammar
above. A distribution entry has exactly `kind="distribution-candidate"`,
`root_role`, `logical_path`, `normalized_name`, `version`,
`locked_artifact_identity`, `declared_path`, `file_kind`, and `module_binding`;
root is purelib/platlib, identity/name/version agree, and that exact locked
identity occurs once in the sibling `artifact_identities` array. Entry arrays are sorted
by canonical UTF-8 JSON, unique, and contain file entries only. `entry_count`
is their length and `entries_sha256` uses
`b"dartwork-mpl-base-import-profile-entries-v1\0"` plus the complete array.
`profile_count` is the profile length and `profiles_sha256` uses
`b"dartwork-mpl-base-import-profile-registry-v1\0"` plus the complete profile
array. Duplicate profile IDs, duplicate complete keys, or an unknown key is
fatal.

No entry module binding may name `ctypes`, `_ctypes`, `numpy.ctypeslib`, or
`_testcapi`, or another exact FFI/debug helper enumerated by the reviewed
profile policy; no artifact required solely by such a binding is selected. A
transitive native image that supplies `_ctypes` or the separately enumerated
libffi bridge is likewise forbidden by the mapping closure, even if no Python
binding was requested. These exclusions are deterministic surface hygiene and
catch accidental dependencies. They are not an exhaustive removal of same-
process memory access: CPython, NumPy, and their complete reachable native
closure are explicitly trusted below.

The preparer reads that registry exactly once under private role
`base-runtime-import-policy`. A profile matches only when its Python/platform
keys equal the already derived preparer values and every listed artifact has
one exact controlled-install witness and installed distribution identity;
the request ID must name that row and the witness/installed artifact set must
equal its artifact array, so any unlisted installed artifact fails. Exactly one
profile must match. Its `profile_id` becomes the manifest field. For each
stdlib entry, the preparer resolves the named retained entry beneath the exact
coalesced root and requires the root-relative path to equal `relative_path`.
For each distribution entry it calls the same captured Distribution object's
`locate_file(declared_path)`, requires one guarded regular file
with that exact provisioned-member identity,
the result to lie component-wise beneath the selected coalesced purelib/platlib
root, and derives its canonical root-relative POSIX path. That derived path must
equal both the registry `logical_path` and the canonical `declared_path`;
an outside-root, symlinked, rewritten, generated, or relocated result is
invalid distribution metadata in V1. Each source entry maps one-to-one to one
manifest file node; the preparer generates every and only missing parent
directory node, hashes/counts the file, requires closure under the fixed base
imports, and includes no other installed file.

This is a prospective allowlist, never the observed read
set; entries may remain unread, but their public bytes intentionally belong to
the common base. A `distribution-candidate` owner is not a
`runtime_distributions` row or ownership trigger merely by appearing here.
Only a frozen module origin or successful computation broker read materializes
the corresponding used-file row/trigger; unread manifest entries remain absent
from the used-distribution projection. An installed member outside the manifest
gets no public member row or trigger, but if it belongs to a profile-selected
wheel its bytes remain indirectly bound by that wheel's whole-archive identity
in `provisioning.artifacts`; changing any member of that archive changes the
common base. Only an artifact absent from both the selected base profile and the
actual used closure is fully private and hash-neutral. The
computation mount materializes exactly these records into fresh sealed trees;
it does not mount the original stdlib/site roots. `record_count` is the array
length and the digest uses
`b"dartwork-mpl-runtime-import-manifest-v1\0"` plus canonical JSON of the
complete records. The supervisor hashes/counts every physical node and verifies
tree/manifest identity before child launch. After consuming ordinal-zero base
handoff, the child independently verifies the canonical manifest, selected
profile/source cross-links, and exact sealed `manifest-runtime-path-hook-v1`
registration before the first base import; it does not open every prospective
file merely to duplicate the supervisor's content check. The path hook answers
module lookup and directory-child queries solely from the manifest, returns
children in UTF-8-basename order, and opens a file only through the broker.
The same sealed bootstrap installs `manifest-runtime-filesystem-query-v1` as the
only `os.stat`, `os.lstat`, `os.listdir`, `os.scandir`, `os.path` predicate, and
`pathlib` query backend for the fixed `/__dartwork_runtime__` prefix. It accepts
only canonical string paths in that prefix, no bytes path, `dir_fd`, symlink,
or dot/dot-dot alias. `listdir`/`scandir` return exactly the manifest's immediate
UTF-8-basename-sorted children. A virtual DirEntry has only the fixed logical
path/name, `inode()=0`, manifest-backed `is_file`/`is_dir`, and the same virtual
stat result. The Linux stat result has exact mode `0o100444`/`0o040555`, inode/
device/rdev/uid/gid/atime/mtime/ctime and all nanosecond values zero, nlink one,
size equal to the file byte count or zero for a directory, blksize 4096, blocks
zero, and no platform-extra value. Missing nodes raise `FileNotFoundError`;
forbidden forms raise `PermissionError`. These sealed function identities are
verified before base import and at both closure barriers. Runtime code needing
fonts, styles, or other declared package data therefore observes the public
virtual tree rather than failing or learning physical metadata.

Raw runtime-tree `stat`, `lstat`, `statx`, `getdents*`, path-hook/query-wrapper
bypass, libc-native query, and direct directory descriptors are denied to the
child. Thus the public contract
determines existence, node kind, normalized mode, byte count, module mapping,
logical child order, and negative module lookup, but makes no claim about
kernel inode/device/uid/gid/nlink/timestamp fields because they are
unobservable. Each actually opened file is rehashed/count-checked against its
one manifest row and receives the ordinary broker record/used trigger; at base-
ready the child and supervisor reconcile every used row while unread rows
remain trigger-free.
`registry_source` has exactly `path` and `sha256`, names that literal registry
leaf, and cross-links its captured `source_files` record.

`base_handoff.platform` is the complete typed public `platform` object. Its
`base_handoff_sha256` is SHA-256 of
`b"dartwork-mpl-control-base-handoff-v1\0"` plus canonical JSON of the complete
base handoff with only `base_handoff_sha256` omitted. Those canonical JSON bytes
plus one LF form the first sealed public handoff leaf.

`invocation_handoff` has exactly `schema`, `invocation_kind`,
`invocation_recipe`, `base_handoff_sha256`, `package_dispatch_profile`,
`project_execution_policy`, and `invocation_handoff_sha256`. Its schema is
`oklab-authoring-control-invocation-handoff-v1`; kind and recipe are the exact
verified request projection. `base_handoff_sha256` equals the nested base
handoff; the private request's `base_import_profile_id` equals that base
handoff's `runtime_import_manifest.profile_id`, and the resolved profile row's
`artifact_identities` array equals `base_handoff.provisioning.artifacts`.
`package_dispatch_profile` has exactly `mode`, `entry_module`,
`policy_id`, `loader_id`, `shell_packages`, and `shell_records`: it is the registry-derived
pre-operation projection of `package_dispatch` below, without a terminal state.
Its policy ID is `broker-bound-authoring-package-shell-v1` and must equal the
final dispatch policy ID.
For shell mode the control preparer privately reads the two initializer leaves,
records their captured path/hash pairs, and emits only those pairs; for an
ordinary row both arrays are empty.

The captured, reviewed
`src/dartwork_mpl/_authoring_execution_profiles.json` leaf has exactly
`schema`, `profiles`, `profile_count`, and `profiles_sha256`; schema is
`oklab-authoring-project-execution-profile-registry-v1`. `profiles` is sorted by
raw UTF-8 `invocation_kind`, contains exactly the eleven invocation kinds in the
environment-v3 enum, and has no duplicate. Each profile has exactly
`invocation_kind`, `entry_module`, `operation_sequence`,
`namespace_packages`, `required_modules`, `optional_modules`, `data_files`,
`record_count`, and `records_sha256`. The first three fields equal the unique row
of the exact dependency-discovery table below, and `operation_sequence` is its
one-element array. A registry module row has exactly `module_name` and
`source_path`; a registry data row has exactly `source_path`; namespace records
use the exact schema below. Each array is sorted by its stated UTF-8 key, all
module names and all paths are unique in their respective unions, and required
modules contain the entry module exactly once. `record_count` is the combined
namespace/required/optional/data length. `records_sha256` hashes an object
containing exactly those four arrays under
`b"dartwork-mpl-project-execution-profile-row-v1\0"`; `profile_count` is exactly
eleven and `profiles_sha256` hashes the complete profile array under
`b"dartwork-mpl-project-execution-profile-registry-v1\0"`. An unknown key,
twelfth/missing row, invocation/table mismatch, duplicate, unsorted array,
count/hash mismatch, or required/optional/data overlap is fatal.

`project_execution_policy` is selected before computation from the exact
invocation row in that registry. The control preparer reads the leaf exactly
once under private role `project-execution-policy`, strict-parses and rehashes
the closed registry, resolves every selected path to its unique captured
`source_files` hash, and emits an object having
exactly `schema`, `policy_id`, `invocation_kind`, `registry_source`,
`namespace_packages`, `required_modules`, `optional_modules`, `data_files`,
`record_count`, and `records_sha256`. Schema is
`oklab-authoring-project-execution-policy-v1`, policy ID is
`profile-bound-project-execution-v1`, and kind equals the invocation. Each
module record has exactly `module_name`, `source_path`, and `sha256`; both arrays
are individually UTF-8-module-name sorted, their union is unique, and every row
cross-links one `source_files` leaf. The required array contains the exact entry
module once. The optional array is the closed set of conditionally reachable
dependencies admitted by that reviewed profile; it is never generated from the
observed events, final module table, imports requested by the target, or a
directory scan. `data_files` is the UTF-8-`source_path`-sorted unique array of
exact `source_path`/`sha256` records for non-module project bytes the profile
may broker-read; it is prospective and reviewed, not inferred from observed
reads. Module paths, either bootstrap, either registry, shell initializers, and
external-bundle paths are forbidden data rows. `namespace_packages` is empty for every shell row and is
exactly
`[{"module_name":"scripts","root_role":"source-snapshot",
"relative_path":"scripts"}]` for every `scripts.*` row. It is the sole V1
ordinary namespace-policy exception: it executes no code and produces no event or
`project_imports` row, but terminal `sys.modules` retains the exact ordinary
namespace-package object/spec/search location and only successful direct-child
bindings. Any second search location, source/bytecode, initializer, alias, or
other namespace name fails. The byte-identical array is
`dependency_discovery.project_namespace_packages`.

`record_count` is the combined namespace/required/optional/data length and
`records_sha256` uses
`b"dartwork-mpl-project-execution-policy-v1\0"` over an object containing exactly
the four complete arrays.

For shell mode the bootstrap, both initializer triples, and every eager public-
API dependency are forbidden policy members. For an ordinary scripts row the
real root/`_colors` initializers may occur only if explicitly listed in that
row, in which case they are ordinary monitored executions. Outside the two
dispatch-owned synthetic shells defined below, V1 forbids project namespace
packages and every fileless/no-origin project parent except the exact `scripts`
record above; each executed project module is one source-backed record. Every
required row must succeed
exactly once, every success belongs to the required/optional union, and the
entry target succeeds exactly once. The complete policy is copied byte-
identically into `dependency_discovery.project_execution_policy`; a missing,
caller-selected, retroactively broadened, hash-only, or invocation-mismatched
policy is fatal.
`registry_source` has exactly `path` and `sha256`, names that literal registry
leaf, and cross-links its captured `source_files` record.

The invocation handoff self-hash uses
`b"dartwork-mpl-control-invocation-handoff-v1\0"` and the complete object with
only its self-hash omitted. `control_preparation_sha256` uses
`b"dartwork-mpl-control-preparation-v1\0"` and the complete control-preparation
record with only that outer self-hash omitted. Canonical JSON of the complete
control-preparation record plus one LF is the second sealed public handoff leaf.
No private ledger/index hash, raw control count/hash/path, unused candidate,
descriptor, or physical role resolution occurs in either public object or any
public hash input.

The computation broker is installed before it reads either handoff. Its first
successful post-broker input read is exactly the base-handoff leaf and therefore
public broker-read ordinal zero, before any computation-child base import. The
child strict-parses it with the sealed bootstrap's no-import parser. Immediately
before the operation-ready source transition, after the common-base boundary,
it reads the complete control-preparation leaf exactly once, validates both
self-hash chains and byte equality of the nested base handoff, and freezes the
invocation recipe/profile. A missing, early, repeated, reordered, byte-different,
or otherwise placed handoff read is fatal. Thus invocation-specific selection
does not enter the common-base broker prefix, while the full runtime/environment
hash still binds the complete preparation record and both actual reads.

The computation child receives exactly one inherited IPC descriptor/channel
exception: a nonblocking read-only pipe endpoint with role `broker-receipt`;
its write-only peer remains supervisor-owned. The separately defined ptrace/
`process_vm_*` control ABI is administrator-TCB mediation over the already
stopped tracee, not an inherited endpoint or child capability. The pipe is
created fresh after the preparer is
reaped, has kernel capacity exactly 65,536 bytes, contains no initial byte, and
is the only computation descriptor besides immutable EOF stdin and the closed
output roles. Each receipt is one UTF-8 canonical JSON line of at most 4,096
bytes including LF, having exactly `kind` and `record`; kind is `broker-read`,
`project-pre-exec`, or `project-success`, and record is the exact public record
for that stream. Every serialized path is at most 2,048 UTF-8 bytes, every
module name at most 512, and every other receipt string at most 512; the total
canonical line limit remains authoritative even when those component limits
would otherwise fit. No more than one receipt may be pending.

Before broker-ready, the bootstrap verifies descriptor 3 through its sealed
native startup helper and wraps it exactly once with the already present frozen/
built-in `_io.FileIO(3,"rb",closefd=False)` primitive; `_io` and that object are
part of the computation pre-broker module closure. This performs no non-cached
import and consumes no byte before the first supervisor receipt. Importing
`os`, `io`, or another helper merely to discover/read the channel before ordinal
zero is forbidden. The wrapper object is private harness state, never exposed
to the entry module, and remains the sole reader through terminal stop.

All computation data opens route through the sealed synchronous broker wrapper;
a raw/native open outside its sealed instruction range is denied (loader image
opens remain in the separate pre-exec mapping ledger). At each successful
guarded input-open syscall exit, while the tracee is stopped, the supervisor
nonblockingly writes exactly one `broker-read` receipt and appends the same bytes
to its monotonic log before resuming. The wrapper must drain, strict-parse, and
append that receipt before returning the opened data to importlib or permitting
another guarded open. For a project execution event the sealed wrapper enters a
dedicated, state-specific harness-range `prctl(PR_GET_DUMPABLE)` syscall-exit
stop; the supervisor requires its zero result, validates the execution state,
writes the corresponding event receipt/log entry, and resumes only after the
same one-pending bound. A full pipe, partial/short write, `EAGAIN`, wrong
kind/state, unexpected EOF, or receipt not consumed before the next guarded
action is terminal, so no blocking write or import deadlock is possible.

The supervisor retains both the exact framed transport lines and two decoded
bare-record arrays, one for reads and one for project events. Every frame must
decode to exactly one next record of the matching array, with no normalization.
The target can at most steal an already public receipt and cause a terminal
length/byte mismatch; it cannot write the pipe, request a future row, or infer
an unused private-index row. At terminal stop the child's complete inline read
and event arrays, canonical-serialized without LF, must be byte-identical to
canonical JSON of the corresponding decoded supervisor arrays; the framed logs
must reconcile one-to-one with them. An extra
endpoint, child write capability, fabricated/reordered record, unpaired open or
event, shared memory, socket, `SECCOMP_IOCTL_NOTIF_ADDFD`, or second receipt
channel is fatal. This channel delivers evidence, not file authority; every
open decision remains in the supervisor-private index.

Child-to-supervisor control uses no second IPC channel. The sealed harness
issues one raw `prctl(PR_GET_DUMPABLE,arg2,arg3,arg4,arg5)` only from the exact
state-specific instruction ranges admitted below. `arg2` is always the 64-bit
literal `0x44574d504c435431`; `arg3` is the sole registered harness-control
buffer address; `arg4` is its current canonical-JSON payload length excluding
the eight-byte prefix; and `arg5` is the contiguous zero-based control-stop
ordinal. After broker-ready and before the first fixed base import, the sealed
helper obtains the buffer through exactly
`mmap(NULL,8388608,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0)`.
The mediated result must be one fresh page-aligned, initially all-zero mapping
with no overlap, alias, file backing, executable permission, resize, remap, or
second candidate. It is registered exactly once at the first
`base-ready-capture` stop: `arg3` selects that mapping, and the supervisor
reconciles it with the mmap-exit/VM ledger before accepting the stop. Every
later control stop must reuse that same base address and size.

The buffer is the exact 8,388,608-byte private mapping used by the base-ready
transfer: its first eight bytes repeat `arg4` as unsigned little-
endian, the next `arg4` bytes are canonical JSON with no LF, and every remaining
byte is zero. It has no Python object exported to project code and remains at
one address/size through terminal stop.

The instruction range and supervisor state select exactly one payload schema:
`BaseReadyChildProjectionV1` at `base-ready-capture`,
`BaseReadyClosureTransferV1` at `base-ready-commit`, one exact next
`project_import_events` record at a project pre/success stop,
`FinalClosureChildProjectionV1` at `operation-closure-capture`, or
`FinalRuntimeClosureTransferV1` at `operation-closure-commit`. The supervisor
reads the buffer twice while stopped, checks the
pointer, mapping, prefix, length, zero tail, ordinal, expected schema, and state,
and retains the payload before acting. Event payloads are at most 4,096 bytes
and must equal the event receipt it then writes; base payload bounds are the
fixed buffer capacity. The kernel syscall must return zero. That zero return,
plus the matching receipt for an event, is the only ACK. A direct syscall from
another range, reused/skipped ordinal, alternate pointer, child-visible
supervisor write authority, payload mutation between reads, or resume before
the state-specific check is fatal. Raw addresses, control ordinals, and buffer
framing remain private; the public event and base-closure preimages are retained
in their declared environment arrays.

`python_startup.policy_id` is `cpython-no-site-broker-first-v1`; this V1 lane
requires `python.implementation="cpython"`. The exact
`argv_tokens` array is:

```text
[
  {"kind":"role","value":"process-executable"},
  {"kind":"literal","value":"-S"},
  {"kind":"literal","value":"-s"},
  {"kind":"literal","value":"-B"},
  {"kind":"literal","value":"-X"},
  {"kind":"literal","value":"utf8"},
  {"kind":"role","value":"startup-bootstrap"}
]
```

The supervisor resolves the two roles privately and supplies no other argv
token. In particular, there is no `-c`, `-m`, stdin/interactive mode, optional
flag, recipe operand, or trailing argument. `argv_policy_sha256` is SHA-256 of
`b"dartwork-mpl-cpython-startup-argv-v1\0"` plus canonical JSON of this whole
array. `cwd_role` is exactly `empty-startup-cwd`, resolved to a sealed empty
directory. `bootstrap_source` has exactly `role`, `path`, and `sha256`; its role
is `startup-bootstrap`, its path is the literal future implementation path
`src/dartwork_mpl/_authoring_bootstrap.py`, and the path/hash pair must occur
exactly once in the execution snapshot and `source_files`. The private physical
bootstrap directory contains only that leaf and is distinct from cwd, every
stdlib/distribution root, and the source-snapshot import root.

`stdlib_archive` is either null or has exactly `role`, `byte_count`, and
`raw_sha256`. A non-null record has `role="stdlib-archive"`, the exact
non-Boolean integer `byte_count=22`, and
`raw_sha256="8739c76e681f900923b900c9df0ef75cf421d39cabb54650c4b9ad19b6a76d85"`.
Those bytes are the four EOCD signature bytes `50 4b 05 06` followed by 18
zero bytes: the unique V1 zero-member, zero-comment, single-disk empty ZIP used
only to satisfy the captured interpreter's initial path layout. Any different
field, member, central-directory entry, trailing byte, symlink, or other ZIP
feature fails. The role is present in every
applicable path stage and has exactly one matching archive-container
`pre_broker_inputs` record; otherwise the field is null and the role is absent
from every stage. No stdlib module may load from the archive in V1. Supporting
archive members requires a new startup policy and stdlib-closure grammar.

The ordinary package retains its Python 3.10 floor, but the V1 evidence lane
requires a profile-pinned CPython 3.12-or-later executable for the closed dict-
watcher/import-core ABI below. `flags` has exactly `no_site=1`, `no_user_site=1`,
`dont_write_bytecode=1`, `utf8_mode=1`, `ignore_environment=0`, `isolated=0`,
and `hash_randomization=0`, all non-Boolean integers taken from the named
`sys.flags` members. `-I` and `-E` are forbidden because either would ignore the
from-empty authoritative Python behavior variables, including the fixed hash
seed and allocator. Safety instead comes from `-S`, the one-file sealed
bootstrap directory, the sealed empty startup cwd, absent `PYTHONPATH`, and
exact path replacement before any non-cached import. The bootstrap's only import before installing the
deny-by-default audit/input broker is the already cached built-in `sys`; its
object identity must be unchanged in `sys.modules`. It first verifies argv,
cwd, flags, the initial path vector, and the absence of `site`,
`sitecustomize`, and `usercustomize`, installs the broker directly from its own
sealed bytes, and only then imports any other harness or base module.

`pre_broker_inputs` is the complete first-consumption-order array of Python
startup source, bytecode, archive-container, and path-configuration input bytes
consumed by the interpreter/import subsystem from process entry through the
broker-ready barrier. It deliberately excludes executable, loader, shared-
object, audit, and other native-image bytes, which are already retained and
cross-bound by the sealed mapping/dependency closure, and excludes kernel facts
that are governed by the native supervisor rather than Python import identity.
Each record has exactly `sequence`, `root_role`, `relative_path`, `file_kind`,
and `sha256`; sequence is the contiguous non-Boolean range
`0..pre_broker_input_count-1`. For `startup-bootstrap-dir`, `stdlib-root`, or
`platstdlib-root`, `relative_path` is a canonical nonempty relative POSIX path,
`file_kind` is `source` or `bytecode`, and each stdlib row cross-links to the
same four-field projection in `python.stdlib_closure_records`. The one
`startup-bootstrap-dir` row instead has
`relative_path="_authoring_bootstrap.py"`, `file_kind="source"`, and a hash
equal to `bootstrap_source.sha256`. For `stdlib-archive`, the only
valid row has `relative_path=null`, `file_kind="archive-container"`, and its
hash equals `stdlib_archive.raw_sha256`; its observed byte count must equal
`stdlib_archive.byte_count`. No archive-member row exists in V1.
Built-in and frozen code has no invented file record and is bound by the
process-executable/Python-runtime identities. An ambient `pyvenv.cfg`, `._pth`,
or other path-configuration file is forbidden; V1 admits only a captured
CPython runtime whose sealed landmark layout starts without one. A runtime that
requires such a file needs a new reviewed startup policy. The supervisor's
pre-broker read ledger permits no other Python startup/config/import input byte
to reach the interpreter. Thus code that imports and then deletes itself from
`sys.modules` cannot escape the preimage. The count is the array length and
`pre_broker_inputs_sha256` hashes
`b"dartwork-mpl-cpython-pre-broker-inputs-v1\0"` plus the complete array.

`pre_broker_modules` is the UTF-8-module-name-sorted snapshot at the first
bootstrap statement. Each record has exactly `module_name`, `origin_kind`, and
`origin`. The origin kind is `built-in`, `frozen`, `stdlib-file`, or
`startup-bootstrap`; built-in/frozen origins use that literal string,
`stdlib-file` uses the exact four-field stdlib-closure projection, and the
bootstrap uses `{"role":"startup-bootstrap"}`. Duplicate names/origins,
third-party/project/site origins, and an absent or present-but-different module
fail. `pre_broker_module_count` is the array length and
`pre_broker_modules_sha256` hashes
`b"dartwork-mpl-cpython-pre-broker-modules-v1\0"` plus the complete array.

`sys_path_stages` has exactly four computation records in order:
`interpreter-initial`, `broker-ready`, `base-ready`, and `operation-ready`.
Each has exactly
`stage`, `path_entries`, `meta_path`, `path_hooks`, and `importer_cache` as
path-neutral role projections. Each `path_entries` member has exactly `role`
and non-Boolean `group_index`; role is one of `startup-bootstrap-dir`,
`stdlib-root`, `platstdlib-root`, `stdlib-archive`,
`distribution-purelib`, `distribution-platlib`, or `source-snapshot`, and
indices are contiguous within each role. Each `meta_path` member has exactly
`position`, `finder_id`, and `origin`; positions are contiguous, finder ID is
`builtin-importer`, `frozen-importer`, or `path-finder`, and origin is the
matching `built-in`/`frozen` literal or exact stdlib four-field projection.
Each `path_hooks` member has exactly `position`, `hook_id`, and `origin`, with
hook ID `zipimporter`, `manifest-runtime-path-hook`, or `file-finder`. Each
`importer_cache` member has exactly `path_entry_index` and `finder_id`, with
finder ID `zipimporter`, `manifest-runtime-finder`, `file-finder`, or `none`, and covers
every path entry exactly once in ascending index order. A custom
or otherwise unlisted finder/hook/cache object or repr-derived identity fails.

The `meta_path` IDs are exactly `builtin-importer`, `frozen-importer`, then
`path-finder`; the first two origins cross-link the `_frozen_importlib`
pre-broker module record and the last cross-links
`_frozen_importlib_external`. `path_hooks` is exactly `zipimporter` then
`file-finder` at `interpreter-initial`, and exactly `zipimporter`,
`manifest-runtime-path-hook`, then `file-finder` at each later stage. The first
and last origins cross-link the `zipimport` and `_frozen_importlib_external`
pre-broker records respectively. The manifest hook origin has exactly `role`,
`component`, and `sha256`, with role `startup-bootstrap`, component
`manifest-runtime-path-hook-v1`, and hash equal to
`bootstrap_source.sha256`; its code is part of that sealed bootstrap, not an
ambient plugin. Those named
records must have their captured runtime's already permitted built-in/frozen or
stdlib origin kind; no version-dependent repr or callable address is an
identity.

At `interpreter-initial`, the bootstrap directory cache entry is
`file-finder`, an optional archive is `zipimporter`, and stdlib/platstdlib
entries are `none`; no import occurs after this snapshot and before broker
installation. At broker-ready/base-ready/operation-ready, every stdlib,
platstdlib, purelib, and platlib cache entry is exactly
`manifest-runtime-finder`; the optional archive remains `zipimporter`, and the
operation-only source-snapshot entry is `file-finder`. The manifest finder is
dormant and fails every request until the ordinal-zero base handoff installs
its verified manifest; afterward it resolves only manifest rows and delegates
each content open to the sealed broker. Clearing, replacing, bypassing, or
calling the ordinary file finder on a runtime role is fatal.

Initial entries may contain only the sealed bootstrap directory and admitted
runtime/stdlib roles. Broker-ready entries remove the bootstrap directory and
retain every verified runtime search role needed by the captured interpreter,
including the sealed zero-member stdlib archive when present, then append only
the public synthesized runtime-import-manifest purelib/platlib trees. They never
expose the private ownership roots. Base-ready has the byte-identical path vector and
marks only the stopped base-closure barrier. Only operation-ready may append
the source-snapshot root, after the base record is
collected and immediately before the exact `entry_module` import. No stage may
contain the empty-string path, cwd, original worktree, ambient or unverified
user/global site,
undeclared root, `.pth`-derived entry, arbitrary finder/hook, or live-path
cache. Every role resolves to one retained sealed root; equal roots coalesce
and ambiguous overlap fails. Each transition replaces `sys.path`, clears and
rebuilds the importer cache under the broker, and verifies the captured
built-in/frozen/stdlib identities plus the sealed-bootstrap manifest-hook
identity. The final three records are
rechecked after the operation and at handoff. `sys_path_stages_sha256` hashes
`b"dartwork-mpl-cpython-sys-path-stages-v1\0"` plus the complete four-record
array.

Path-entry order is semantic and closed. Initial is
`startup-bootstrap-dir`, optional `stdlib-archive`, `stdlib-root`, then optional
distinct `platstdlib-root`; broker-ready removes only the first entry.
It then appends the manifest-backed `distribution-purelib` and then an
optional distinct `distribution-platlib`; base-ready is byte-identical. If their
private source roots were equal, only `distribution-purelib` occurs in the
public manifest. Operation-ready appends only `source-snapshot`.
For equal stdlib/platstdlib roots only `stdlib-root` occurs. Every present role
has `group_index=0`; a second group or other order requires a new startup
policy. An initial path entry for a nominal but absent stdlib archive is
invalid: the archive role is present only when its fully sealed archive leaf
and non-null `stdlib_archive` binding exist.

Automatic `site` processing, `.pth` execution, either customizer, an ambient
startup hook, or any import/read before the broker outside the closed startup
preimage is terminal and produces no owner. `PYTHONNOUSERSITE=1` is retained as
defense in depth; it is not treated as a substitute for `-S` or this startup
contract.

`math_origin_kind` is exactly `built-in`, `frozen`, `stdlib-file`, or
`native-role`. Built-in/frozen origins use that literal `math_origin` string
with null `math_module_role`. A stdlib origin has a `math_origin` object with
exactly `root_role`, `relative_path`, `file_kind`, and `sha256`. It must equal
the canonical four-field projection of exactly one record `r` in
`python.stdlib_closure_records`, and the complete `r.module_aliases` must
contain the literal `math`. `module_aliases` is forbidden in `math_origin`, and
`math_module_role` is null. This projection binds the loaded file without
copying invocation-closure aliases into the base math-origin value. A native
origin has exactly `math_origin={"role":"math-module"}` and
`math_module_role="math-module"`, which resolves to the strong identity of the
uniquely address-bound loaded image below; no loader or filesystem path is
serialized.

The core references are closed literals, not arbitrary non-empty role names:
`process_executable_role` is exactly `process-executable`,
`process_loader_role` is exactly `process-loader`, `runtime_library_role` is
exactly `python-runtime`, `math_provider_role` is exactly `math-provider`, and
`numpy.multiarray_role` is exactly `numpy-multiarray`. `math_module_role` is
exactly `math-module` only for `native-role` and null for all other origin
kinds; the nested native `math_origin.role` is also exactly `math-module`.
Every non-null reference resolves to exactly one dependency record and one
`native_execution.mapping_records` identity. The
`process-executable` file identity's SHA-256 equals
`python.executable_sha256`. There is no
`math_module_sha256` field: stdlib origins already bind their public file hash,
while native origins bind the tagged retained-sealed-file identity. A legacy
extra hash field or
any other origin-kind/nullability/role combination fails strict parsing. The
V1 authoring
path forbids `numpy.linalg`,
`numpy.dot`, `numpy.matmul`, and every direct BLAS/LAPACK call; therefore it
has no BLAS/LAPACK provider role. The public NumPy build-capability record
retains only the closed SIMD baseline/
dispatch projection; it neither publishes compiler/library paths nor claims
that unused BLAS/LAPACK providers participated in authoring arithmetic.

Dependency discovery uses policy
`authoring-sealed-loaded-image-set-v2`. Every invocation runs in a new
two-child supervisor transaction: a fresh control-preparer Python process is
fully reaped before a fresh computation Python process starts. No process,
module object, trace adapter, loader handle, temporary directory, descriptor,
mapping, or collector state is reused across invocations or child lifetimes.
The closed profile registry
is below. On Linux, “loaded image set” means the stopped supervisor's merged
base-plus-audit `r_debug_extended` union defined later, not the Python caller's
`dl_iterate_phdr` namespace alone:

| `invocation_kind` | Exact `entry_module` | Exact `operation_sequence` |
|---|---|---|
| `legacy-baseline-extractor-a` | `scripts.extract_color_v5_baseline_a` | `legacy-baseline-extractor-a` |
| `legacy-baseline-extractor-b` | `scripts.extract_color_v5_baseline_b` | `legacy-baseline-extractor-b` |
| `legacy-baseline-cross-extraction` | `scripts.cross_check_color_v5_baseline` | `legacy-baseline-cross-extraction` |
| `policy-preselection` | `dartwork_mpl._colors._authoring_preselection` | `policy-preselection` |
| `proposal` | `dartwork_mpl._colors._authoring_proposal` | `proposal` |
| `comparison` | `dartwork_mpl._colors._authoring_comparison` | `comparison` |
| `discrete-policy-characterization-verification` | `dartwork_mpl._colors._authoring_discrete_policy_verification` | `discrete-policy-characterization-verification` |
| `admission-policy-characterization-verification` | `dartwork_mpl._colors._authoring_admission_policy_verification` | `admission-policy-characterization-verification` |
| `characterization-generation` | `dartwork_mpl._colors._authoring_characterization` | `characterization-generation` |
| `characterization-verification` | `dartwork_mpl._colors._authoring_characterization_verification` | `characterization-verification` |
| `promotion-replay` | `dartwork_mpl._colors._authoring_promotion` | `promotion-replay` |

`operation_sequence` is a one-element array containing that literal operation
ID. `package_dispatch` has exactly `policy_id`, `mode`, `entry_module`,
`loader_id`, `shell_packages`, `shell_records`, and `terminal_state`. Its policy
ID is `broker-bound-authoring-package-shell-v1`, and `entry_module` equals the
registry row. For the three `scripts.*` rows, mode is `ordinary-pathfinder`,
loader ID is null, both arrays are empty, and terminal state is
`not-applicable`. For every `dartwork_mpl._colors.*` row, mode is
`sealed-package-shell`, loader ID is
`source-bound-nonexecuting-package-shell-v1`, shell packages are exactly
`["dartwork_mpl","dartwork_mpl._colors"]`, and terminal state is
`installed-and-verified-before-operation`. Its two `shell_records` occur in
that order and each has exactly `module_name`, `source_path`, and `sha256`:
the paths are `src/dartwork_mpl/__init__.py` and
`src/dartwork_mpl/_colors/__init__.py`, names match the shell array, and each
path/hash occurs exactly once in `source_files`. No other pairing is valid.

The authoring-shell mode is necessary because standard Python import executes
parent package initializers before a dotted target. It does not modify those
initializers or ask them to recognize a mutable marker. The computation child
never reads their bytes. During the earlier isolated control-preparation
lifetime, the control broker performs exactly one guarded hash-only read of the
root initializer and then one of `_colors`, records their captured path/hash
pairs in `invocation_handoff.package_dispatch_profile.shell_records`, and
denies every repeat. The preparer is reaped before computation, so no raw
initializer byte, parser buffer, frame, or code object reaches the authoring
target. The computation broker permanently denies those two paths as input,
source, bytecode, compile, or exec authority.

Immediately before operation-ready, only after the computation child has read
and validated the invocation handoff, the sealed bootstrap uses the
base-imported `types` and `importlib` machinery to construct two fresh package-
shell module objects in root-then-`_colors` order and installs them into
previously absent exact `sys.modules` keys. Each shell's protected metadata is
exactly the import machinery's `__name__`, `__package__`, one-entry private
sealed-source `__path__`, package `__spec__`, and source-bound nonexecuting
`__loader__`; `__file__`, `__cached__`, `__all__`, ordinary exports, and
initializer globals are absent. The spec origin is the literal `package-shell`
and `has_location` is false. The root additionally has the exact `_colors`
binding to the second synthetic shell. Thereafter the only permitted additional
attributes are persistent direct-child bindings installed by successful
ordinary imports: a binding name is the child's final module-name component,
its object is the exact terminal `sys.modules` object, and its successful
execution event cross-links that same full child name. Protected metadata may
never change except for CPython's ordinary stack-balanced push/pop of the active
direct-child name in `parent.__spec__._uninitialized_submodules`. Each push
must correspond to the currently opening monitored project execution, nested
pushes are LIFO, its pop occurs when that child import resolves, and the list is
empty at every completed top-level import, before/after the operation, and at
handoff. A different value/order, unpaired or persistent mutation, export,
alias, overwritten child binding, or unrelated attribute is not admitted.

The broker installs a sticky shell guard before insertion. Any attempt to read,
compile, execute, find a source spec for, or reload either real initializer;
delete, replace, alias, remove and reinsert, or mutate either shell/protected
metadata; install a third shell; or catch and restore one of those attempts
permanently invalidates the run. A loader-level refusal alone is not treated as
sufficient because `importlib.reload()` can ask the ordinary path finder for a
new real spec. The source broker, execution monitor, shell guard, and terminal
reconciliation must all agree that both initializer bodies executed zero times.
These shell-guard claims apply to the guarded broker/import/Python interfaces
under the reviewed computation TCB; they do not reintroduce a hostile same-
process memory boundary.

The ordinary `PathFinder` locates the exact registered target and permitted
captured dependencies beneath those shells. A sealed execution monitor wraps
only the located project loader's `exec_module` boundary; it may not substitute
source bytes, a module name, a path, or import resolution. Immediately before
the first opcode it validates the profile's exact module-name/path/hash
allowlist and emits the corresponding `pre-exec` event; immediately after the
loader returns successfully it emits the paired `success` event. Direct
`compile`/`exec`, a custom project loader/finder, manual code-object execution,
an alias name/path, or project code reached outside one active monitored pair is
denied. After target import returns and before its operation is called, the
bootstrap and broker recheck the shell object identities, protected metadata,
permitted child bindings, source hashes, target identity, event ledger, and
module table and only then emit the terminal dispatch state. The same check is
repeated after the operation and at handoff.

The shells are synthetic nonexecuting packages, so ownership represents them
only through `package_dispatch.shell_records`, never as executed
`project_imports` or project-import events. The startup `__main__` bootstrap is
likewise owned only by `python_startup.bootstrap_source`/pre-broker records and
`source_files`; its standard script `__spec__=None` cannot fabricate a project-
import row. The exact target and every project dependency whose source actually
executes do occur in `source_files`, the event ledger, and `project_imports`.

For a normal public import outside this evidence lane, and for a registered
`scripts.*` row, no shell is installed. Ordinary public imports execute the
captured initializer files exactly as before; a scripts evidence row may execute
only its profile-authorized script dependencies and may not silently enter a
shell profile. The evidence mechanism therefore requires no branch in those files
and must preserve the predecessor's exports, registration, fonts, manual
colors, palettes, and all 43 shipped 256-entry LUT bytes and indices. A caller-
created `__main__` function or marker has no selection surface because the
ordinary initializers never query one. `package_dispatch` is part of complete
`dependency_discovery`, so the runtime/environment/enclosing hashes bind the
selected mode, shell source identities, and verified terminal state.

The matching `invocation_recipe.operands` role order is closed:

| `invocation_kind` | Exact operand-role order |
|---|---|
| `legacy-baseline-extractor-a` | `source-snapshot, external-input-bundle, output-artifact-role` |
| `legacy-baseline-extractor-b` | `source-snapshot, external-input-bundle, output-artifact-role` |
| `legacy-baseline-cross-extraction` | `source-snapshot, external-input-bundle, output-artifact-role` |
| `policy-preselection` | `family, source-snapshot, external-input-bundle, output-artifact-role` |
| `proposal` | `family, source-snapshot, external-input-bundle, output-artifact-role` |
| `comparison` | `family, source-snapshot, external-input-bundle, output-artifact-role` |
| `discrete-policy-characterization-verification` | `family, source-snapshot, external-input-bundle, output-artifact-role` |
| `admission-policy-characterization-verification` | `family, source-snapshot, external-input-bundle, output-artifact-role` |
| `characterization-generation` | `source-snapshot, external-input-bundle, output-artifact-role` |
| `characterization-verification` | `source-snapshot, external-input-bundle, expected-artifact-role, output-artifact-role` |
| `promotion-replay` | `family, source-snapshot, external-input-bundle, output-artifact-role` |

The final operand value, primary schema/path, ordinary-output profile, and
publication lifecycle are closed by the same row:

| `invocation_kind` | Exact `output-artifact-role` value | Primary schema | Canonical primary path | Ordinary profile | Publication |
|---|---|---|---|---|---|
| `legacy-baseline-extractor-a` | `legacy-v5-baseline-extractor-a-output` | `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1` | `build/color-authoring/legacy-v5-baseline-preinstall-v1/extractor-a/evidence.json` | `named` | ignored primary-last |
| `legacy-baseline-extractor-b` | `legacy-v5-baseline-extractor-b-output` | `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1` | `build/color-authoring/legacy-v5-baseline-preinstall-v1/extractor-b/evidence.json` | `named` | ignored primary-last |
| `legacy-baseline-cross-extraction` | `legacy-v5-baseline-cross-extraction-output` | `dartwork-mpl-legacy-v5-baseline-cross-extraction-v1` | `build/color-authoring/legacy-v5-baseline-preinstall-v1/cross-extraction/manifest.json` | `named` | ignored primary-last |
| `policy-preselection` | `oklab-authoring-policy-preselection-output` | `oklab-authoring-policy-preselection-v1` | `build/color-authoring/<family>/policy-preselection.json` | `none` | ignored primary-last |
| `proposal` | `oklab-authoring-proposal-output` | `oklab-authoring-proposal-v1` | `build/color-authoring/<family>/proposal.json` | `none` | ignored primary-last |
| `comparison` | `oklab-authoring-comparison-output` | `oklab-authoring-comparison-report-v1` | `build/color-authoring/<family>/comparison/report.json` | `artifact-map` | ignored primary-last |
| `discrete-policy-characterization-verification` | `oklab-authoring-discrete-policy-characterization-verification-output` | `oklab-authoring-discrete-policy-characterization-verification-v1` | `build/color-authoring/<family>/policy-characterization-verification/discrete.json` | `none` | ignored primary-last |
| `admission-policy-characterization-verification` | `oklab-authoring-admission-policy-characterization-verification-output` | `oklab-authoring-admission-policy-characterization-verification-v1` | `build/color-authoring/<family>/policy-characterization-verification/admission.json` | `none` | ignored primary-last |
| `characterization-generation` | `oklab-fixed-y-characterization-generation-output` | `oklab-fixed-y-characterization-generation-evidence-v1` | `<output-root>/fixed-y-characterization-generation-evidence.json` | `named` | ignored primary-last |
| `characterization-verification` | `oklab-fixed-y-characterization-verification-output` | `oklab-fixed-y-characterization-evidence-v1` | `<output-root>/fixed-y-characterization-evidence.json` | `named` | ignored primary-last |
| `promotion-replay` | `oklab-authoring-frozen-family-output` | `oklab-authoring-frozen-v1` | `src/dartwork_mpl/asset/color/oklab_authoring_frozen_v1/<family>.json` | `none` | tracked create-only |

`<output-root>` is the already selected fresh ignored output root and is not a
public path value; the manifest stores the displayed filename relative to it.
`<family>` is the one validated recipe family. Any mixed row, alternate role,
path, schema, profile, or lifecycle fails before output creation.

Complete environment ownership is:

| Invocation | One authoritative complete environment owner |
|---|---|
| `legacy-baseline-extractor-a` | extractor-A evidence `.environment` |
| `legacy-baseline-extractor-b` | extractor-B evidence `.environment` |
| `legacy-baseline-cross-extraction` | cross-extraction manifest `.environment` |
| `policy-preselection` | `policy-preselection.json.environment` |
| `proposal` | `proposal.provenance.environment` |
| `comparison` | `comparison/report.json.comparison_environment` |
| `discrete-policy-characterization-verification` | verification evidence `.provenance.environment` |
| `admission-policy-characterization-verification` | verification evidence `.provenance.environment` |
| `characterization-generation` | generation evidence `.environment`; a combined-evidence copy must be byte-identical |
| `characterization-verification` | combined evidence `.verification_environment` |
| `promotion-replay` | frozen envelope `.promotion_provenance.environment` |

Every actual environment-v3 computation invocation has exactly one owner in
this table. A copied alias must be byte-identical; a detached environment or
hash-only link has no authority. Reviewer processes instead carry closed
`ReviewExecution`; policy, fixed-Y, and validation-truth archive promotions carry the closed
`archive_promotion_provenance`. Those byte-review/transfer lifecycles are not
unlisted environment-v3 computations.

The exact execution order is:

1. the Linux native supervisor builds and inode-seals the private capsule and
   every runtime/source/input leaf, activates the namespace, descriptor,
   syscall, writer, and executable-VM policy, and retains that authority through
   both child lifetimes and the verified terminal handoff;
2. it launches the fresh no-site Python control preparer. Its sealed bootstrap
   installs the private control broker before any non-cached import, consumes
   the request/platform/policy and ownership inputs in the exact ledger order,
   uses the closed `importlib.metadata` semantics to build the private index and
   public runtime-import/project/dispatch projections, and writes the private
   transfer manifest last;
3. at the preparer's terminal stop the supervisor copies and revalidates the
   complete private/public transfer set, kills/reaps the preparer, destroys its
   namespace/tmpfs/descriptors/mappings, and proves the zero-overlap guard. It
   then materializes fresh sealed public handoff leaves and exactly the public
   synthesized runtime-import trees; no raw control leaf or private directory
   topology enters the next child;
4. the supervisor launches the fresh no-site CPython computation child with the
   one inherited broker-receipt pipe exception and the exact stopped-tracee
   control ABI. The bootstrap installs its deny-by-
   default broker before every non-cached/base import, reaches broker-ready, and
   consumes the base-handoff leaf as public broker-read ordinal zero;
5. the computation child imports the fixed base list through only the public
   synthesized trees. It then enters the stopped base-ready capture/commit
   pair; the supervisor freezes and transfers the complete base broker prefix,
   module/stdlib/dependency/mapping closures and independently verifies them at
   both stops before ACK. The commit, not revocation or buffer deletion,
   defines the common base;
6. only after base-ready, the child consumes the complete control-preparation
   leaf, validates its invocation handoff, freezes the exact project-execution
   policy and dispatch profile, and appends the sealed public source root. A
   shell row constructs the two nonexecuting synthetic parents from the typed
   shell records while their real source paths remain denied; an ordinary row
   installs no shell. It then imports exactly the registered entry module under
   the monitored well-nested project-event state machine and requires terminal
   dispatch verification before the operation;
7. execute exactly its one operation from the captured source/input bundle;
8. after it returns, forbid every further import, `dlopen`, authoring call, or
   mutation of the operation result/artifacts, freeze `sys.modules` and all
   import state, reconcile the project policy/events/import projection and both
   supervisor receipt logs, and close every profile-declared ordinary non-
   primary output;
9. enumerate loaded modules and the base `dl_iterate_phdr` cross-check twice,
   enter the stopped operation-closure capture/commit pair so the supervisor
   can traverse and merge both `r_debug_extended` namespaces, transfer the
   authoritative final mapping/dependency arrays, and verify them twice. After
   the commit ACK, collect the remaining stdlib/project/distribution records,
   construct the environment, and, using only the already imported harness
   serializer, write and close the primary completion envelope. Then validate
   the exact schema-profile ordinary output set, hash every closed leaf, and
   write and close the private terminal output manifest last; and
10. re-enumerate both namespaces immediately before the terminal transition, require byte-
   identical module and loaded-image identities, reconcile the complete
   kernel-mediated ledger, close every output handle, and issue the one exact
   harness-range self-`tgkill(SIGSTOP)`. At that non-returned signal-delivery
   stop the supervisor rechecks the closure, never resumes user space, kills
   and reaps the child, copies the manifest and every manifest member to fresh
   fully sealed private leaves, verifies hashes and exact set equality, and
   discards the child tmpfs. A static byte-only publisher installs and syncs
   every subordinate leaf first and publishes the primary completion marker
   last. It may not import, `dlopen`, recompute authoring data, reopen a live
   producer path, alter artifact bytes, or weaken/tear down the policy before
   reap.

There is no synthetic warm-up fixture. The two legacy extractor operations are
outside the new-authoring trace surface and must retain explicit `records=[]`.
The cross-extraction, policy-preselection, and characterization-verification
operations are parser/copy/hash-only and likewise must retain explicit
`records=[]`. These are the exact five empty-trace invocation kinds:
`legacy-baseline-extractor-a`, `legacy-baseline-extractor-b`,
`legacy-baseline-cross-extraction`, `policy-preselection`, and
`characterization-verification`. The other six environment profiles execute
authoring generation, rendering/oracle replay, selection/admission, or frozen
numeric replay and must have a nonempty trace. In particular, preselection never runs
selection before approval, and characterization verification never imports a
producer, solver, renderer, selector, oracle, catalog, or compatibility module.
For `policy-preselection`, those same generator/selector/oracle/renderer/
proposal imports are forbidden. `arithmetic_trace` covers only the actual
registered operation; neither a warm-up call nor an empty trace outside that
literal five-member allowlist is valid.

For an authoring-shell row, neither parent initializer is a project import: both
synthetic modules are explicit zero-execution exceptions owned only by
`package_dispatch.shell_records`. This does not authorize any module from their
ordinary eager bodies. The profile's literal module-name/path allowlist and its
forbidden selector/producer/registrar/catalog/renderer/oracle rules are checked
before every project execution, not inferred from the terminal module set.

`project_import_events` is the complete append-only execution-order array. Each
record has exactly `ordinal`, `event_kind`, `execution_id`, `module_name`,
`source_path`, and `sha256`. Ordinals are contiguous non-Boolean integers from
zero. `event_kind` is `pre-exec` or `success`; `execution_id` is a contiguous
non-Boolean integer assigned in pre-exec order once per permitted module
execution. Events form one strict single-threaded well-nested stack: pre-exec
pushes its ID, success closes the most recent unmatched ID with byte-identical
module/path/hash fields, and the stack is empty before the operation and at
handoff. Thus `A pre, B pre, B success, A success` is valid for a nested import;
adjacent pairing is not required. Each execution/module/path occurs once,
reentrant execution of the same module is forbidden, and success without a
matching top frame or any unmatched frame is fatal. The pre-exec record is
committed to both the supervisor's private kernel-mediated ledger and the
child's public receipt stream before the first project opcode; the success
record is committed after `exec_module` returns and before another project
execution can begin. An exception publishes no owner. A forbidden name, wrong
path/hash, alias, nested unmatched execution, duplicate/reload, initializer,
manual exec, missing pair, or event observed only by one side is terminal.
Deleting or replacing a module during its body cannot erase either record.
`project_import_event_count` equals the array length and
`project_import_events_sha256` is SHA-256 of
`b"dartwork-mpl-project-import-events-v1\0"` plus canonical JSON of the complete
inline array.

`project_imports` is the UTF-8-module-name-sorted unique projection of the
successful event pairs, not a reconstruction from final `sys.modules` alone.
Each record has exactly `module_name`, `source_path`, and `sha256`; every
path/hash occurs exactly once in the execution snapshot's `source_files`. At
terminal reconciliation every projected module key must still name the same
loader-produced object with the same origin/hash, no additional project-backed
source module may exist, and the public event bytes must equal the supervisor-
retained ledger. In ordinary mode the only fileless project parent is the exact
`project_namespace_packages` record. In shell mode that array is empty and the
only fileless parents are exactly the two dispatch-owned, terminally reconciled
synthetic shells, which remain excluded from events/imports. A module that
executed and deleted/replaced itself therefore remains
observable and also fails the terminal state check. An open phrase such as
“modules required by authoring” never expands this set.

`dependency_discovery.control_policy_id` is
`brokered-control-preparation-inputs-v1`. The private control ledger belongs
only to the control-preparer lifetime and is the complete actual-open-order
array from its accepted broker-ready barrier through its terminal stop. Each
private record has exactly
`sequence`, `role`, `leaf_id`, `byte_count`, and `raw_sha256`; sequence is the
contiguous non-Boolean range `0..N-1`, `leaf_id` is the supervisor-assigned
role-relative identifier of one retained sealed leaf rather than an ambient
pathname, and count/hash equal the guarded bytes returned by that open. Its
closed roles are exactly `invocation-request`, `platform-os-release`,
`platform-cpuinfo`, `platform-attestation`, `project-execution-policy`,
`base-runtime-import-policy`, `computation-input-inventory`,
`provisioning-witness`, `uv-lock`, `selected-wheel`,
`distribution-metadata`, `distribution-located-entry`, `stdlib-inventory`,
`stdlib-entry`, and `package-initializer-source`. Every actual control open,
including a repeated open, is a record; a role not in this list is denied.
The first eight roles and each uv-lock/wheel/metadata/inventory/located-entry
leaf use `control-singleton-v1`; fixed-import stdlib leaves alone may use
`control-repeatable-input-v1`; the two initializer records use
`control-ordered-shell-pair-v1`. Any other role/policy pairing is invalid.

Records zero through three are exactly one read each of
`invocation-request`, `platform-os-release`, `platform-cpuinfo`, and
`platform-attestation` in that order. Their leaf IDs are exactly
`control/<role>`. The first record strictly parses the already supervisor-verified
recipe/dispatch/base-profile request. The next two are parsed into the typed OS-build and CPU
projections, which must byte-for-byte reproduce the fourth canonical
attestation leaf. Those request and platform projections enter only the typed
public handoffs; their raw buffers remain confined to the preparer. A
missing, repeated, reordered, mutated, aliased, early, or late singleton read;
a second sealed leaf with one of those roles; or a projection/attestation
difference fails. Records four and five are exactly the one
`project-execution-policy` and one `base-runtime-import-policy` read in that
order. Record six is exactly the one `computation-input-inventory` read, and
record seven is exactly the one `provisioning-witness` read. Only after those
eight singleton reads does the preparer perform its fixed
imports; every resulting `stdlib-entry` open is retained in actual occurrence
order. It then executes the closed ownership-build state machine: explicit
requests for lock, selected-wheel, distribution/stdlib inventory, and located
entries are issued in UTF-8 `(role,leaf_id)` order, while any nested opens they
cause remain adjacent in their actual broker order. For a shell profile the
final two `package-initializer-source` records are adjacent root then
`_colors`; a scripts profile has none. The ledger is therefore an occurrence-
order history, not a post-hoc sorted set. Reordering it for canonicalization,
or claiming that importlib's nested reads themselves occurred in leaf-ID order,
is invalid. The preparer and supervisor independently reconcile
the complete sequence, roles, leaf IDs, counts, and hashes against the sealed
input inventory before the preparer terminal stop. The supervisor then
kills/reaps it and retains the private index/ledger solely in supervisor memory
until computation handoff; neither is mapped into the fresh computation child.
The ledger and its private hashes are destroyed after verified computation
terminal handoff and are never public fields or public hash inputs; the two
handoffs, public recipe/dispatch, platform record, selected-artifact, shell-
source, and used-file projections are their typed consequences.

`dependency_discovery.policy_id` is
`brokered-computation-dependency-discovery-v1`. Its
`broker_read_records` is the complete computation-child public input-open stream
beginning with the successful base-handoff read at ordinal zero, before any base
import, and ending at the terminal stop. It therefore includes both typed
handoffs plus NumPy/base, project, external-input, distribution, and permitted
stdlib reads, including repeated opens and their interleaving; it excludes only
the separately retained computation pre-broker startup records and the first
child's private control ledger.
Each record has exactly `ordinal`, `root`, `role`, `path`, `byte_count`, and
`raw_sha256`. Ordinals are the contiguous non-Boolean integers `0..N-1`, path is
a nonempty surrogate-free POSIX string governed by its tagged variant below,
byte count is a non-Boolean nonnegative integer, and the hash is the guarded
bytes actually returned by that open. The exact tagged ownership forms are:

| `root` | Exact `role` | `path` and required cross-link |
|---|---|---|
| `control-handoff` | exactly `base` or `invocation` | respectively `control-base-handoff.json`, whose bytes equal canonical `control_preparation.base_handoff` plus LF and whose ordinal is zero, or `control-preparation.json`, whose bytes equal the complete canonical `control_preparation` plus LF and whose ordinal is strictly after the base-prefix boundary and immediately before the source transition |
| `source-snapshot` | null | exact canonical no-dot/dot-dot `source_files` path/hash; later import origins also equal `project_imports` |
| `external-input` | the unique nonempty bundle-role string | exact canonical no-dot/dot-dot producer `source_path`, byte count, and raw hash in the invocation's external-input bundle |
| `distribution` | exactly `{normalized_name,version,file_kind}` | exact canonical no-dot/dot-dot provisioned-member `declared_path`, file kind, and content hash in one `runtime_distributions` used-file record; name/version equal that row |
| `stdlib` | exactly `{root_role,file_kind}` | exact no-dot/dot-dot relative path beneath sealed `stdlib-root` or `platstdlib-root`; file kind is `source`, `bytecode`, `extension`, or `regular-data`; a frozen source/bytecode origin equals its stdlib-closure record, while an extension origin equals its manifest binding and unique native mapping |

No absolute path, root-prefix grant, symlink spelling, private locator, omitted
open, or invented read is serialized. A control-handoff record is public typed
transport, owns no distribution trigger, and must byte-cross-link to the inline
object; its leaf hash is ordinary raw SHA-256 of those canonical-plus-LF bytes.
A distribution record has exactly one
`ownership_triggers` broker-read link to the same global ordinal; a stdlib read
is itself the retained public ownership trigger and cannot point into a
distribution or residual site root. Project/external rows must also match the
invocation's declared input authority. After the operation, the frozen module
table, complete computation stream, used-distribution rows, stdlib/project
closures, and external bundle are reconciled as one exact partition before an
environment owner can be written.

`broker_read_record_count` equals the array length and
`broker_read_records_sha256` is SHA-256 of
`b"dartwork-mpl-environment-broker-read-records-v1\0"` plus canonical JSON of
the complete array. Both the array and digest remain inline in every
authoritative environment through `dependency_discovery`; the runtime and full
environment hashes and every enclosing completion therefore bind the complete
preimage after the private ledger is destroyed.

`base_broker_read_record_count` is the exact length of this array at the common-
base boundary, after NumPy/base collection and immediately before the
invocation-handoff read and source-root transition. It defines the complete prefix
`broker_read_records[:base_broker_read_record_count]` without renumbering.
`base_broker_read_records_sha256` is SHA-256 of
`b"dartwork-mpl-base-broker-read-records-v1\0"` plus canonical JSON of that
prefix. The prefix begins with exactly the base-handoff record and contains no
invocation-handoff or project-source row. The common base hash binds the count
and digest; therefore a NumPy/base
data read cannot be hidden merely because later invocation-specific imports
differ. An out-of-range boundary, empty claimed prefix when NumPy was imported,
or any post-operation relabeling of the boundary fails.

At that same stopped common-base boundary, before the invocation handoff or
source root is reachable, the child and supervisor retain three complete inline
base closures. `python.base_stdlib_closure_records` uses the exact stdlib record
grammar/order below and contains every stdlib-file module present at the
boundary; its count is the array length and its digest uses
`b"dartwork-mpl-python-base-stdlib-closure-v1\0"`. It is a real preimage, not a
subset reconstructed from final aliases. The later complete stdlib closure must
contain each base record with byte-identical file identity and at least the same
base aliases.

`base_module_records` is the UTF-8-module-name-sorted complete `sys.modules`
snapshot at that boundary. Each record has exactly `module_name`, `state`,
`origin_kind`, and `origin`. A null sentinel has `state="null"` and both latter
fields null; otherwise state is `module` and origin kind is `built-in`,
`frozen`, `startup-bootstrap`, `stdlib-file`, `distribution-file`,
`distribution-native`, or `native-image`. Namespace/no-origin modules are
forbidden in the computation base. The first two kinds use their literal
string; startup uses exactly `{"role":"startup-bootstrap"}`. A `stdlib-file`
origin has exactly `root_role`, `relative_path`, `file_kind`, and `sha256` and
equals the four-field projection of one unique
`python.base_stdlib_closure_records` row. A `distribution-file` origin has
exactly `normalized_name`, `version`, and `used_file`; `used_file` has exactly
`declared_path`, `file_kind`, and `sha256` and equals one unique record in the
same-name/version final `runtime_distributions` row and one unique prospective
manifest owner/node. A `distribution-native` origin has those same three keys
plus `mapping_identity`, which equals one unique base mapping and has the same
sealed-file hash as `used_file.sha256`. A `native-image` origin is exactly one
retained base mapping `identity` object. The matching module-origin trigger in
the final used-distribution row is mandatory for both distribution variants;
the final row may be constructed later, but it must reproduce this frozen base
projection byte-for-byte. No project-source or package-shell row is valid
at this boundary. Count is the array length and the hash domain is
`b"dartwork-mpl-base-module-closure-v1\0"`.

`module_records` is the corresponding complete UTF-8-name-sorted terminal
`sys.modules` snapshot frozen before `operation-closure-capture`; its count is
the array length and its hash domain is
`b"dartwork-mpl-final-module-closure-v1\0"`. It uses the same four keys and all
base origin forms above, plus only `project-source`,
`synthetic-package-shell`, and `project-namespace`. A project-source origin has
exactly `source_path` and `sha256` and equals the same-name unique
`project_imports` row, source manifest row, successful event, and broker read.
A synthetic-shell origin has exactly `policy_id`, `source_path`, and `sha256`,
uses `broker-bound-authoring-package-shell-v1`, and equals the same-name one of
the two ordered package-dispatch shell records; it has no execution event or
source read. A project-namespace origin is exactly the same-name unique
`project_namespace_packages` record and is admitted only for `scripts` in an
ordinary profile. No distribution namespace, implicit package, missing-spec,
or other no-origin module is admitted.

Every base record must occur byte-identically in the terminal array, and the
child also freezes the `(module_name,module_object_identity)` pair at both
boundaries so a retained name cannot be replaced. A terminal built-in, frozen,
null, startup-bootstrap, or other fileless/native-only record must therefore
already be that same base record; the only new fileless records are the exact
two synthetic shells or one `scripts` namespace just defined. Each new stdlib
or distribution file/native origin equals one manifest module binding, its
broker record and used ownership row, and when applicable one final mapping.
This complete terminal preimage—not inference from reads alone—is the public
reconciliation preimage for post-base imports and fileless module state during
conforming execution by the exact reviewed computation TCB. It is not a proof
of every same-process memory write.

The sealed computation harness installs the interpreter-ABI-bound
`sticky-post-base-module-table-guard-v1` C-level import-core and `sys.modules`
dict watcher before the base imports, freezes the exact name/object map at the
successful base-ready commit, and arms it before releasing the invocation
handoff. This is fail-fast integrity instrumentation for ordinary importlib,
Python mapping, and Python/C import-API transitions, including accidental
drift and direct `_imp` use. Under those interfaces, a built-in/frozen/null/
startup/native-only resolution is permitted only as a lookup of the byte-
identical frozen base object; an unbound first load, wrong-object mutation, or
unapproved clear/update synchronously enters the nonreturning harness failure
path and the supervisor publishes nothing. The watcher is not a hostile-code
sandbox and does not claim to stop or faithfully record arbitrary writes to
the computation process's own memory.

Normal post-base import timing follows stock profile-pinned CPython rather than
an invented single insertion. After the finder returns the exact prospective
`ModuleSpec`, but before `module_from_spec()` and therefore before any loader
`create_module()`, the sealed import core enters one nested
`module-insertion-authorization` state. It binds the authority row, module name,
prospective spec identity and frozen controlled spec fields, and expected
loader; no module object is asserted to exist yet. A sealed source, sourceless,
or project loader's reviewed `create_module` path returns `None` for ordinary
import-core creation or the one contract-bound expected object, and executes no
project opcode. Before an extension loader may call
`_imp.create_dynamic`, it consumes the bound broker row and binds the
prospective sealed member/mapping authority; no dynamic create begins before
that successful receipt. The mediated dynamic loader then establishes the
actual sealed-file mapping association before any mapped constructor or
`PyInit_*` instruction executes. For a multi-phase
extension, create and `_init_module_attrs` complete before the initial
`sys.modules` insertion and before `Py_mod_exec`; for a legacy single-phase
extension, native initialization has already occurred when create returns.
There is consequently no claim that an extension module dictionary was frozen
before `PyInit_*` or `Py_mod_create`.

Once a module object exists and import-controlled attributes have been
initialized, their required presence/value and the controlled `ModuleSpec`
state are frozen before the initial insertion and, for source/sourceless code,
before its first opcode. For a multi-phase extension this is before
`Py_mod_exec`; for a legacy extension it is a post-create consistency freeze.
The exact successful ordinary-import transaction is:

```text
authorization/spec freeze -> create -> module-attribute init/freeze
-> spec._initializing=true -> initial same-name insertion
-> exec (or the loader's exact no-op)
-> CPython success-tail pop -> V1 initial-object identity check -> reinsert
-> spec._initializing=false -> commit
```

The watcher admits that exact initial insertion and stock success-tail
pop/reinsert as one logical authorization, while V1 additionally requires the
popped/reinserted object to be the object from the initial insertion. Stock
CPython itself would reinsert whatever object then occupies the name; same-
object identity is this policy's deliberate restriction, not a stock guarantee.
A source/sourceless manifest loader consumes its bound broker row before its
first code/data use, and a project loader emits its existing `pre-exec` event
before the first project opcode. A failure before initial insertion changes no
target-name slot under the outer authorization; any successful nested import has
its own complete nested transaction. Every outer-create failure is nevertheless
nonpublishable. A failure after insertion may delete only that same still-authorized name/object,
emits no successful logical transition, makes the invocation nonpublishable,
and cannot resume authoring. A different name or object, an extra mutation,
wrong ordering, a nonnested state, or direct `_imp` outside the authorization
takes the ordinary-API fatal path. Synthetic shells retain separately typed
one-shot logical authorizations and do not fabricate `_load_unlocked` success-
tail operations they never execute. The sole `scripts` namespace has its own
authority kind but follows the ordinary namespace-module `_load_unlocked`
create/insert/no-op/success-tail transaction above.

`module_guard_transition_records` is therefore the complete occurrence-order
array of successful logical authorization completions, not a low-level
`sys.modules` dictionary-operation trace. Each ordinary module, including the
`scripts` namespace, emits its record only after the policy-verified success-
tail reinsert and `_initializing` reset. Each synthetic shell emits after its
own exact logical completion, and each successful logical module contributes
exactly one record. The four-field public grammar remains
unchanged. The offline verifier resolves those logical records against the
manifest/project/shell/namespace authorities and terminal module/event/read
arrays; it does not infer or attest every process-memory microstep. The C import
core uses frozen internal manifest hook/finder/path-role vectors rather than a
mutable Python list after base commit. Its watched Python-visible mirrors,
importer cache, installed `os`/`os.path`/`pathlib` query bindings, dictionaries,
specs, nested state stack, watcher registrations, and logical completion array
are checked at both operation-closure stops and terminal stop.

Protected module metadata tracks presence as well as value for `__name__`,
`__package__`, `__loader__`, `__spec__`, `__file__`, `__cached__`, and
`__path__`. Thus an extension's absent `__cached__` differs from a present-null
attribute. Package path and `submodule_search_locations` are the immutable one-
item sequence above; the only admitted import-core changes are the exact
`_initializing` transition and stack-balanced `_uninitialized_submodules`
transition from reviewed instruction ranges. Assignment, replacement, or
change-and-restore through the guarded Python/import interfaces outside that
transaction fails immediately. These checks establish consistency of the
origin, cache presence/value, loader, package identity, and search path for
conforming TCB execution; they are not a memory-safety boundary.

The same-process computation TCB explicitly includes every exact reviewed
project source byte authorized to execute, the computation bootstrap/harness
and import core, the profile-pinned CPython executable/build, NumPy, and the
complete reachable loaded Python/native/runtime closure. Their identities are
captured, hashed into the appropriate source/runtime/environment evidence, and
included in review; changing any executing member invalidates that evidence.
`ctypes`, `_ctypes`, `numpy.ctypeslib`, `_testcapi`, and the exact additional
FFI/debug surfaces named by policy remain denied as deterministic hygiene, but
their absence is neither exhaustive nor a claim that NumPy exposes no pointer-
based memory mechanisms. Symbol/address collection used by the harness remains
native and hash-bound rather than a project-facing convenience API.

A hostile reviewed build-script sandbox is an explicit V1 non-goal. If such a
boundary is ever required, a separate ADR must introduce a memory-safe native
color verifier or another reviewed hardened runtime and coordinate its schema,
hash domains, and oracle equivalence; this design does not smuggle that claim
into a CPython process. The exact shipped/manual color and palette bytes, all
43x256 LUT bytes/indices/metadata, independent oracle replay,
generation/verification process split,
18-surface comparison, and sequential adversarial A-then-B review remain strict
result guarantees and are not weakened by this TCB correction. The CPython
3.12+ pin is for exact diagnostic/reproducibility semantics and does not raise
dartwork-mpl's ordinary user-facing Python floor.

`native_execution.base_mapping_records` is the canonical complete loaded-
mapping array captured at the same stopped boundary, not merely a six-role core
subset. Its count is the array length and its hash uses
`b"dartwork-mpl-base-native-mappings-v1\0"`. It therefore includes every
extension and DSO already loaded by the fixed base list, including providers for
`_hashlib`, `_decimal`, and NumPy when present. `_ctypes` and libffi are forbidden
in the computation closure. The final
mapping array must contain each byte-identical base record. Likewise,
`base_dependency_records` is the canonical complete role-record array over
those mappings at that boundary; its `native-transitive/<ordinal>` values use a
base-local identity-sorted ordinal namespace and are not required to equal later
final ordinals. Final closure instead cross-links every base mapping identity
and every non-transitive core role. Its count is the array length and its hash uses
`b"dartwork-mpl-base-loaded-images-v1\0"`. Any file/module/mapping loaded before
the boundary but omitted from one of these arrays, or any base array changed by
later invocation-specific collection, is fatal. These complete preimages, the
base broker-read prefix, and the typed base handoff are all common-base hash
inputs.

Native execution is captured from process creation, not reconstructed from
post-operation pathnames. `native_execution.policy_id` is
`authoring-native-mapping-capture-v1`. `seal_policy_id` is exactly
`linux-sealed-memfd-namespace-v1`, and `vm_policy_id` is exactly
`linux-seccomp-ptrace-closed-writer-surface-v1`.
`terminal_handoff_policy_id` is exactly
`sealed-terminal-output-set-primary-last-v1`. Every non-review Python evidence
producer governed by this design uses the same native supervisor and writes one
private `TerminalOutputManifestV1` only after
the public primary and all ordinary subordinate leaves are closed. It has
exactly:

```text
schema, producer_profile_id, output_artifact_role, primary,
ordinary_outputs, terminal_output_manifest_sha256
```

Its schema is `oklab-authoring-terminal-output-manifest-v1`.
For an environment-v3 computation, `producer_profile_id` is its exact
`invocation_kind` and `output_artifact_role` equals the recipe table above. The
two additional producer profiles are exactly:

| `producer_profile_id` | Exact output role | Primary schema/path | Ordinary profile | Publication |
|---|---|---|---|---|
| `discrete-policy-characterization` | `oklab-authoring-discrete-policy-characterization-output` | `oklab-authoring-discrete-policy-characterization-v1` at the policy batch subject's predeclared exact `characterization_path` | `named` (`visual_strip.path`) | tracked create-only, subordinates first |
| `admission-policy-characterization` | `oklab-authoring-admission-policy-characterization-output` | `oklab-authoring-admission-policy-characterization-v1` at the policy batch subject's predeclared exact `characterization_path` | `none` | tracked create-only |

Those paths and hashes must later be copied unchanged into the promoted
registry entries. These two profiles are policy-characterization producer
transactions, not unlisted environment-v3 owners. The private terminal
manifest closes only their byte-transfer set; their semantic batch's clean
review capsule and review evidence separately bind the source closure, while
the subsequent policy A/B review treats the tracked bytes as source-snapshot
inputs. Reviewer/provider processes and
content-addressed bundle publishers use their separately closed lifecycles and
are not silently added here. `primary` has exactly `path`, `kind`, `schema`,
`completion_hash_field`, `completion_hash`, `byte_count`, and `raw_sha256`.
Its kind is the literal `regular-file`.
The schema/hash-field/domain pairing is the unique row in section 10's
completion table. `ordinary_outputs` is the UTF-8-relative-path-sorted array of
records having exactly `path`, `kind`, `byte_count`, and `raw_sha256`; every
kind is the literal `regular-file`, and the path set must
equal the selected `artifact-map`, `named`, or `none` output profile, and every
hash/count must equal both the closed leaf and the primary's schema-specific
reference. Paths are canonical output-root-relative POSIX strings: no empty,
absolute, dot/dot-dot, backslash, NUL, duplicate, case alias, symlink, hardlink,
directory, device, socket, FIFO, or unclaimed member is valid. `none` is the
real empty array. The self-hash is SHA-256 of
`b"dartwork-mpl-oklab-terminal-output-manifest-v1\0"` plus canonical JSON of
the complete manifest with only that field omitted.

This manifest is private transport and is never published, archived, or named
by a public hash. In particular, neither the primary, its environment, its
provenance, nor the invocation recipe may contain the manifest hash: because
the manifest names the primary's raw hash, the reverse edge would be a hash
cycle. The public primary already binds every ordinary output through its
closed schema. Content-addressed input/control/evidence bundle stores remain
their separate producer transactions and are not smuggled into this ordinary
inventory. If a future environment profile produces such a store inside the
child, a new reviewed output profile and handoff version are required.

At the accepted terminal stop the supervisor verifies no writable descriptor
or mapping to any terminal-output member remains, kills and reaps without resuming user space, no-follow
enumerates the whole tmpfs, and requires exact equality with the manifest. It
copies the manifest and every member to a new memfd, applies and re-reads the
four full seals, rehashes each source/copy twice, and only then discards tmpfs.
For an ignored-output lifecycle only, under one exclusive canonical-output-root
writer lease, the byte-only publisher removes and directory-syncs any stale
primary, stages/fsyncs/replaces and rehashes every subordinate, syncs every
affected directory bottom-up, then stages/fsyncs and atomically publishes the
primary last and syncs its parent.
This is a primary-as-commit-marker transaction, not a false claim of multi-file
atomicity. A crash or failure before the primary may leave only
non-authoritative subordinate bytes; retry must revalidate or replace the full
declared set under the same lease. A surviving primary requires every declared
member to be present, durable, and byte-identical; a missing/different/extra
member is fatal. An ignored lifecycle's post-primary source/input guard failure
removes and syncs the primary, leaving any subordinate prefix non-authoritative.
A tracked create-only lifecycle never removes or replaces a tracked leaf and
uses only section 10's repository-writer overlay, durability, and recovery
rules; a failed final guard is fatal and cannot be papered over by deleting its
primary.

`supervisor` has
exactly `role`, `executable_sha256`, `version`, and `capabilities`. Its role is
`native-capsule-supervisor`, its executable hash covers the exact launched
native supervisor bytes, and its version is the exact single-line
`MAJOR.MINOR.PATCH` ASCII stdout of the no-locale supervisor `--version`
operation with its one terminal LF removed. The unique UTF-8-sorted
`capabilities` array is exactly:

```text
["broker-bound-authoring-package-shell-v1",
 "brokered-computation-dependency-discovery-v1",
 "brokered-control-preparation-inputs-v1",
 "close-outside-fds-v1","closed-async-writer-surface-v1",
 "closed-ipc-network-surface-v1",
 "control-preparation-then-fresh-computation-v1",
 "cpython-no-site-broker-first-v1","cpython-no-site-control-preparer-v1",
 "drop-capabilities-groups-v1",
 "glibc-post-constructor-pre-main-audit-v1",
 "glibc-r-debug-extended-two-namespace-v1",
 "isolated-subordinate-uid-v1","memfd-exec-seal-v1",
 "no-new-privs-v1","no-shared-mutable-mappings-v1","no-vsyscall-exec-v1",
 "nondumpable-no-external-writer-v1",
 "nondumpable-root-supervisor-v1","preclone-clean-mm-seccomp-v1",
 "private-user-ipc-mount-network-namespaces-v1",
 "proc-maps-inode-bind-v1","profile-bound-project-execution-v1",
 "public-synthesized-runtime-import-tree-v1",
 "rseq-disabled-verified-v1",
 "sealed-terminal-output-set-primary-last-v1",
 "sealed-wheel-provisioning-v2",
 "seccomp-ptrace-exec-vm-mediation-v1",
 "self-sealed-static-supervisor-v1","single-thread-exec-map-v1",
 "sticky-post-base-module-table-guard-v1",
 "supervisor-base-ready-closure-transfer-v1",
 "supervisor-final-runtime-closure-transfer-v1",
 "supervisor-project-execution-events-v1",
 "supervisor-used-read-receipts-v1"]
```

A missing, extra, reordered, or alternate capability/seal/credential mechanism
fails rather than weakening the contract.
`closed-ipc-network-surface-v1` includes exactly the fresh one-way
`broker-receipt` pipe described above as its sole inherited computation IPC
descriptor/channel exception; it denies every other inherited pipe/socket/IPC
object and does not treat that evidence channel as an external-writer or input-
authority capability. The state-bound ptrace/process-memory ABI is separately
owned by the administrator TCB and is not an inherited IPC object.

The only admitted supervisor artifact is one freestanding, fully static
ELF64-little executable with no `PT_INTERP`, dynamic section, `DT_NEEDED`,
`dlopen` path, ELF constructor, libc/pthread/TLS runtime, or rseq registration.
Its stage-zero file, every path ancestor, and every writable alias are owned by
the initial-namespace administrator TCB and are not writable by a governed
principal. The stage-zero process immediately blocks every blockable signal,
sets every settable disposition to the closed supervisor baseline, does not inspect
its inherited environment, sets and re-reads `PR_SET_DUMPABLE=0`, canonicalizes
the private request into a fully sealed memfd, copies its own exact bytes into an
`MFD_ALLOW_SEALING|MFD_EXEC` memfd, applies and re-reads the four required
seals, and rehashes byte equality. It then uses `execveat(AT_EMPTY_PATH)` to
enter those same sealed bytes with an empty environment and only the closed
typed supervisor descriptors. The final process verifies that
`/proc/self/exe` is that fully sealed memfd and that its raw hash equals
`supervisor.executable_sha256`; the root-owned stage-zero artifact and final
memfd must be byte-identical. No dynamically linked or merely pathname-hashed
launcher is conforming.

The initial-namespace administrator launches stage zero as a fresh process
outside every pre-existing seccomp filter and independently treats any outer
filter or user-notification listener as fatal; the final supervisor requires
both `PR_GET_SECCOMP==0` and the corresponding proc status before installing
the child policy. This administrator, the kernel, and every principal holding
initial-namespace `CAP_SYS_PTRACE` are explicit TCB. The final supervisor keeps
the exact administrator credential required for mount, user-ID-map, ptrace,
and reap operations, has no supplementary groups, remains nondumpable, and is
not reachable by a governed non-TCB principal through signal, ptrace,
`process_vm_*`, `/proc/<pid>/mem`, pidfd, inherited IPC, or a shared/mutable
mapping. An extra administrative principal is therefore a TCB expansion and
fails host admission rather than being described as an untrusted peer.

`launch_environment` has exactly `policy_id`, `behavior_sha256`, and
`role_bindings`. Its policy is `empty-child-environment-v1`.
`behavior_sha256` is SHA-256 of
`b"dartwork-mpl-child-behavior-environment-v1\0"` plus canonical JSON of the
exact `floating_point.determinism_environment` record below. `role_bindings`
is the one-element array:

```text
[{"variable":"LD_AUDIT","role":"startup-audit",
  "identity":<file-sha256 identity>}]
```

Its identity equals both the retained sealed audit leaf's mapping identity and
the unique public `startup-audit` runtime-dependency identity. The private
absolute value supplied to `LD_AUDIT` resolves only that leaf inside the
prepared root, contains no list separator, and is never public. The leaf and
its closed `DT_NEEDED` closure are captured before launch; dependencies are
not additional environment bindings. Every captured ELF, including the
process executable, loader, audit closure, Python/extension/runtime DSOs, must
contain neither `DT_AUDIT` nor `DT_DEPAUDIT`; `LD_AUDIT` is the sole admitted
audit-module source. The audit leaf and each audit-only dependency are
freestanding DSOs with no libc/libpthread/libdl/libgcc runtime or TLS/rseq
registration; every audit `DT_NEEDED` identity is sealed and absent from the
base namespace. The only cross-namespace identity allowed is glibc's
same-address, same-segment process-loader proxy, which is coalesced below.
Thus an ordinary libc-linked auditor that would map the base libc identity at
a second address fails preflight. The supervisor builds the child environment
from empty: it inserts exactly the variables represented by the behavior
record plus this one role-bound variable. It rejects every inherited or extra
key, duplicate key, non-UTF-8/NUL value, other `LD_*`, locale/allocator/Python
override, and caller-selected loader path. Neither raw environment text nor a
path digest is authority. The exact sealed glibc/loader pair must recognize
`glibc.pthread.rseq` with admitted value zero during private preflight; an
unknown, ignored, rewritten, or distribution-specific alternate tunable fails.

`PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, `PYTHONINSPECT`,
`PYTHONPLATLIBDIR`, every site/customizer selector, and every other unlisted
Python variable are absent, not present with an empty value. Conversely, `-E`
and `-I` are forbidden: the admitted from-empty values of `PYTHONHASHSEED`,
`PYTHONMALLOC`, `PYTHONDONTWRITEBYTECODE`, `PYTHONNOUSERSITE`, and
`PYTHONUTF8` must actually be consumed and rechecked through the startup and
floating-point records.

The supervisor privately retains one append-only native event ledger from
child creation until the verified terminal handoff. It records every admitted
mapping/protection/exec/control syscall and completion, loader correlation,
credential transition, and boundary guard before any candidate owner becomes
publishable. Raw addresses, descriptors, inode/process IDs, syscall stops, and
the ledger itself remain private. Publication requires every allowed
executable range to reconcile exactly with one retained sealed leaf or the
closed vDSO exception, the startup audit history, the normalized mapping
projection, and the final guards. A lost, unpaired, duplicate, sequence-gap,
timed-out, or post-barrier event; an allowed executable mapping that never
becomes one declared loader image; any executable-page mutation; or any
unload/unmap of an executable image before handoff is terminal and publishes
nothing. Thus a direct mapping may execute only sealed bytes, but an unmatched
direct mapping still dooms the private run and can never influence a published
result. Before/final VM snapshots are consistency checks, not authority for
the interval between them.

The external-writer boundary is alias-complete, not a task-write-only claim.
From stage-zero supervisor entry through verified handoff, no governed non-TCB
principal may mutate the supervisor, its retained leaves, ledger, or output
owner. From child creation, no such principal may additionally possess or
acquire a shared backing object, mutable file alias, inherited descriptor or
socket, task/process handle, userfaultfd, asynchronous I/O context, device
mapping, or other route capable of supplying bytes to or changing bytes read by
the child. The sealed static supervisor, unique subordinate-ID lease,
immutable child credentials and capability sets, closed descriptor/mount/IPC/
network surface, post-exec dumpability barrier, and sole bound tracer remain
live for their stated whole intervals.
Final snapshots, a zero observed-event count, or absence of a detected write
are not authority. Any reachable writer route, external memory write,
credential-boundary loss, unexpected signal, or asynchronous completion is
terminal even when every executable mapping remains unchanged.

On Linux the supervisor repeats this construction independently before each of
the two Python children, with role-specific roots and no shared child object:

1. recursively resolves through no-follow descriptors the exact process
   executable, `PT_INTERP` loader, every candidate extension/DSO, each closed
   `DT_NEEDED` dependency, and every regular runtime/source/input leaf that the
   child may read or map. A path or byte source outside that finite captured
   hierarchy is unavailable rather than discovered live;
2. copies each leaf to a fresh memfd, using
   `MFD_ALLOW_SEALING|MFD_EXEC` only for an executable candidate and
   `MFD_ALLOW_SEALING` followed by mode `0444` for every other leaf, hashes
   source and copy independently, requires equality, and verifies that the new
   inode has no pre-existing mapping or writable descriptor alias. The syscall
   policy, not a mode bit, independently forbids execute permission for every
   non-executable leaf;
3. applies and re-reads exactly `F_SEAL_WRITE|F_SEAL_GROW|F_SEAL_SHRINK|
   F_SEAL_SEAL`; `F_SEAL_FUTURE_WRITE` is not an alternative because it can
   preserve an existing writer;
4. constructs a recursively private mount tree containing only those sealed
   leaves, the role's unique empty startup-cwd directory, and one child-private
   nosuid/nodev/noexec output tmpfs. It exposes no `/proc`,
   `/dev`, `/dev/shm`, `mqueue`, `hugetlbfs`, `sysfs`, FUSE/device mount,
   host-writable bind, or live input broker. The root is read-only, nosuid, and
   nodev except for the one private output tmpfs. Runtime/source/input leaves
   are read-only and non-executable unless they are declared executable capsule
   leaves; output is non-executable. The supervisor retains its leaf and mount
   authority privately and never mutates child-readable bytes during the run;
5. immediately before cloning, proves the final supervisor still has exactly
   one thread and `PR_GET_SECCOMP==0`; proves there is no inherited seccomp filter/listener,
   rseq registration, SysV-shm attachment, POSIX-shm object, userfaultfd,
   io_uring ring, legacy-AIO context, socket, device/DMA handle, or pending
   asynchronous writer; and proves the exact typed descriptor table consists only
   of descriptors 0/1/2, fully sealed leaves, role-specific private inputs, and
   supervisor-owned mount/output setup handles. Before the computation clone it
   additionally includes only the fresh supervisor write end of the closed
   broker-receipt pipe; the preparer has already been reaped and no handle from
   its transaction exists. Its complete map is limited to
   the retained fully sealed static-supervisor `PT_LOAD` ranges, kernel vDSO/
   non-executable vvar ranges, and anonymous-private non-executable stack/heap
   ranges. It has no `MAP_SHARED*` range, mutable-file-backed private range,
   executable anonymous range, unsealed file range, or other kernel pseudo
   executable. This checked state, including the absence of an outer
   `SECCOMP_RET_USER_NOTIF`/`SECCOMP_IOCTL_NOTIF_ADDFD` authority, is the
   `preclone-clean-mm-seccomp-v1` policy outcome; a final snapshot alone does
   not substitute for the fresh-exec construction above. Then, under an
   exclusive allocation lease, it creates the selected lifecycle child directly with
   `clone3()` using exactly
   `flags=CLONE_NEWUSER|CLONE_NEWIPC|CLONE_NEWNS|CLONE_NEWNET` and
   `exit_signal=SIGCHLD`; every other admitted `clone_args` field is zero and
   the structure size is the one exact size pinned for the admitted kernel
   ABI. `CLONE_VM`, `CLONE_FILES`, `CLONE_FS`,
   `CLONE_SYSVSEM`, `CLONE_THREAD`, and every other sharing flag are absent.
   The child's only pre-credential behavior is an immutable native bootstrap
   in the hash-bound supervisor TCB; it immediately stops rather than reading a
   caller-controlled gate. The supervisor writes one-entry `uid_map`
   and `gid_map` files that map closed nonzero inside IDs to a unique
   subordinate host UID/GID unused by any other live process or namespace,
   after writing `deny` to `setgroups`. Those host IDs come from a supervisor-
   reserved range absent from ordinary login, `/etc/subuid`,
   `/etc/subgid`, and container-manager delegation; the privileged allocator is
   the sole mapping authority and refuses a second lease or map while the child
   or namespace is live. The supervisor seizes the stopped child. Before
   dropping credentials, the bootstrap changes `/` propagation recursively to
   private, changes cwd to the prepared `new_root`, performs
   `pivot_root(".",".old_root")`, changes cwd to the new `/`, recursively
   detaches `/.old_root`, removes that mount point, and closes every old-root/
   cwd/directory handle. It then opens the unique sealed
   `/empty-startup-cwd` directory no-follow, proves that it contains no entry
   other than `.` and `..`, changes cwd to it, and closes the directory handle.
   From the initial namespace
   the supervisor verifies `/proc/<pid>/root`, `/proc/<pid>/cwd`, and the
   complete `/proc/<pid>/mountinfo` against the exact prepared root, startup
   cwd, and output tmpfs; no copied parent mount or route to the old root may remain. It then
   fixes the real, effective, saved, and filesystem UID/GID values to those
   mapped IDs,
   empties all child capability sets and supplementary groups, exposes no
   namespace descriptor, sets `no_new_privs`, performs `PR_SET_DUMPABLE=0`
   followed immediately by `PR_GET_DUMPABLE`, and stops again. The supervisor
   requires a successful set and a returned zero before release. The lease
   remains held through child
   reap. The kernel and initial-user-namespace administrator are explicit TCB;
   among governed non-TCB processes, only the hash-bound supervisor retains
   `CAP_SYS_PTRACE` in an ancestor of the target user namespace. Failure to
   create the child inside that boundary or prove the unique external
   credential is fatal; post-creation `unshare` or mapping the caller's
   ordinary host UID is not an alternative;
6. after that bootstrap setup and before that child's one exec, invokes a
   role-specific close-range sequence. Descriptor 0 is an immutable EOF
   source whose every writer has already been closed; descriptors 1 and 2 are
   write-only supervisor sinks. The control preparer receives no read-capable
   IPC descriptor; its fixed request/control leaves are ordinary brokered leaves
   in its private root. The computation exec preserves exactly one additional
   nonblocking read-only `broker-receipt` pipe endpoint at the fixed descriptor
   number 3 and closes every other descriptor from 4 upward. It receives no
   other inherited control/IPC descriptor, directory/namespace descriptor,
   pidfd, socket, memfd, userfaultfd,
   io_uring, device, PTY, or mutable-file descriptor. Output is committed
   only to the private tmpfs; the supervisor copies the complete closed
   terminal manifest and member set after handoff;
7. sets exactly the bitwise OR of `PTRACE_O_TRACESECCOMP`,
   `PTRACE_O_TRACESYSGOOD`, `PTRACE_O_TRACEEXEC`, and `PTRACE_O_EXITKILL`,
   and installs before each lifecycle's one admitted `execve` a compiled-in, supervisor-
   hash-bound, architecture-closed seccomp filter. Its measured allow set is
   exact and its default action is kill; an unknown audit architecture,
   x32/compat ABI, traced stop outside the closed route set, tracer loss, or
   supervisor death is fatal. Only Linux x86-64 and AArch64 are V1 lanes.
   Before admitting an OS build, the supervisor proves raw-syscall coverage and
   entry/event/exit-stop ordering with `PTRACE_GET_SYSCALL_INFO`; missing or
   ambiguous support fails closed. The filter traces the exact mapping,
   protection, unmapping, `brk`, that child's one exec, permitted descriptor-open/close,
   and exact audit-leaf/harness `prctl` control routes plus that lifecycle's one
   terminal harness-range `tgkill(SIGSTOP)`. In the computation child,
   `PR_GET_DUMPABLE` is admitted only from distinct sealed instruction ranges
   and matching state-machine positions for `base-ready-capture`,
   `base-ready-commit`, each project-pre/success event receipt, and the one
   `operation-closure-capture`/`operation-closure-commit` pair; each matched
   syscall exit must return zero and is a resumable stopped control barrier.
   The preparer has none of
   those computation routes. Every other harness `prctl` request, wrong range,
   wrong event depth, skipped/duplicate barrier, or control stop outside the
   exact state fails.
   It kills every clone/fork; all System V shared-
   memory/message/semaphore calls including every `shmat`; POSIX message
   queues; sockets and descriptor-passing routes; `memfd_create`;
   `userfaultfd` and `/dev/userfaultfd`; io_uring and legacy kernel AIO;
   `splice`/`vmsplice`/`tee`; child `ptrace`;
   `process_vm_readv`/`process_vm_writev`; `pidfd_open`/`pidfd_getfd`;
   `process_madvise`/`process_mrelease`; perf/BPF; mount/namespace creation; and
   device/DMA acquisition. `rseq` is the one closed fallback route that returns
   fixed `ENOSYS` rather than killing the process, so glibc can continue without
   registering it; no raw registration or unregistration is admitted. The
   filter provides no user-notification listener or
   `SECCOMP_IOCTL_NOTIF_ADDFD` route. After setup it also kills every
   filter, tracer, credential, group, capability, or namespace change. The
   initial sealed-Python exec is the only admitted exec transition. On x86-64,
   admission additionally requires `vsyscall=none` behavior: neither the
   supervisor nor the stopped child may have a `[vsyscall]` range, and a
   sacrificial raw call to each legacy fixed entry must terminate with the
   admitted fault rather than execute or emulate. AArch64 admits no such
   range. Failure is preflight rejection, not another fileless-image kind;
8. records the initial exec's seccomp stop, admits only the exact sealed Python,
   requires the corresponding `PTRACE_EVENT_EXEC`, and rechecks the unique
   UID/GID maps and empty child capability sets while the post-exec tracee is
   still stopped. The exec environment must byte-match the closed
   `launch_environment` construction, including
   `GLIBC_TUNABLES=glibc.pthread.rseq=0` and the one sealed `LD_AUDIT` role.
   Linux may reset dumpability to `1` on that exec; the unique
   subordinate kernel credential is the mandatory writer boundary during this
   interval. The dynamic loader, IFUNC resolution, `DT_PREINIT_ARRAY`,
   `DT_INIT`, and `DT_INIT_ARRAY` constructors run first, but already under the
   sealed-leaf, namespace, descriptor, seccomp, ptrace, credential, and
   external-writer boundary. The sealed startup audit leaf's `la_preinit`,
   which glibc invokes after those constructors and before executable `main`
   and the Python interpreter entry, performs the only post-exec
   `PR_SET_DUMPABLE=0`, immediately performs `PR_GET_DUMPABLE`, and blocks at
   a ptrace-observed stop. Both calls traverse the filter and exact exit-stop
   state machine and are admitted only from the audit leaf's retained
   executable range at that one state; the set must return success and the get
   must return `0` before release. `PR_SET_DUMPABLE` with any nonzero value and
   every `PR_SET_PTRACER` are always denied; after the barrier every
   dumpability set and credential/capability/namespace change is denied. The
   supervisor uses supported `PTRACE_GET_RSEQ_CONFIGURATION` at the exec stop,
   the `la_preinit` stop, and every later operation/terminal guard and requires
   a null registration address and zero registered size/flags for the sole
   thread. The audit leaf also resolves the retained glibc's exported
   `__rseq_size` without loading a new object and requires zero. Missing or
   ambiguous ptrace support, any nonzero registration, or any admitted `rseq`
   transition is fatal; context switches therefore have no rseq TLS region for
   the kernel to rewrite. The
   subordinate-ID lease remains necessary after dumpability is zero; neither
   control substitutes for the other;
9. at each kernel syscall-entry stop, while the only target thread is stopped,
   validates the scalar register arguments and the seccomp-stop identity,
   duplicates a referenced file descriptor through the stopped task, and
   compares its device/inode, seals, byte hash, offset, and ELF segment to one
   retained leaf. Every `MAP_SHARED` or `MAP_SHARED_VALIDATE` request is denied
   regardless of protection; every `shmat` and `remap_file_pages` is denied.
   Anonymous mappings must be `MAP_PRIVATE` and initially non-executable. A
   file-backed `MAP_PRIVATE` mapping is admitted only from the exact retained,
   fully sealed leaf; a mutable file is denied even when the requested mapping
   is private or read-only. Executable file mappings must additionally match an
   executable `PT_LOAD` range and may never be writable. `mprotect` and
   `pkey_mprotect` may add execute only to a tracked sealed-file range that has
   never been writable and may not add write to a range that is or has been
   executable. Every `brk` entry/exit is traced. `brk(0)` may query the current
   break; growth or shrinkage is admitted only within the one tracked
   anonymous-private, writable, non-executable heap interval established at
   exec, may not overlap or merge with any other range, and is reconciled with
   the returned break and `/proc/<pid>/maps` before release. A failed or
   surprising partial change is terminal rather than omitted from the ledger.
   `mremap` is limited to an already tracked anonymous-private,
   non-executable range, admits only zero or `MREMAP_MAYMOVE` flags, preserves
   one-to-one ownership, and may neither overlap nor replace a sealed mapping;
   `MREMAP_FIXED` and `MREMAP_DONTUNMAP` are denied;
   `munmap` may not hide an executable image before handoff. Every admitted
   mapping result is reconciled against `/proc/<pid>/maps` before release;
10. stores the exact pending
   `{audit_arch,syscall_number,arguments,seccomp_ret_data}` from a
   `PTRACE_SYSCALL_INFO_SECCOMP` stop, resumes an admitted call with
   `PTRACE_SYSCALL`, and accepts its completion only when `waitpid(__WALL)`
   reports `SIGTRAP|0x80` and `PTRACE_GET_SYSCALL_INFO` reports
   `PTRACE_SYSCALL_INFO_EXIT` for that one pending architecture/syscall state.
   The initial exec alone additionally requires its one intervening
   `PTRACE_EVENT_EXEC`. Before target user code can run, the supervisor checks
   the return/error and exact resulting `/proc/<pid>/maps` range against the
   retained leaf/segment and appends the result to the private ledger. A plain
   `SIGTRAP`, `PTRACE_SYSCALL_INFO_NONE`, missing `PTRACE_O_TRACESYSGOOD`,
   unexpected signal delivery/restart, event/return, map replacement, or ledger
   disagreement kills the child and publishes nothing. The sole signal
   exception is the exact final self-`SIGSTOP` after its matched `tgkill`
   syscall exit; it enters the non-resumable terminal handoff rather than
   authoring code; and
11. executes the sealed Python through the sealed interpreter and uses a sealed
   glibc `LD_AUDIT` leaf from process startup. Its base-namespace
   `la_objopen`/`la_objclose` history and the `la_preinit` dumpability barrier
   are complete; those callbacks are not treated as an enumeration of the
   audit module's own namespace. The exact sealed glibc/loader pair must expose
   the version-2 `r_debug_extended` debugger rendezvous and the preflight below
   must prove its two-namespace behavior before an OS build is admitted. At
   operation and terminal handoff the supervisor also requires
   zero live descendants, threads beyond the admitted main thread, shared
   mappings, userfaultfds, io_uring rings, legacy AIO contexts, sockets, device
   mappings, rseq registration, a `[vsyscall]` range, an old-root/cwd escape,
   pending asynchronous completions, or open output handles. At every guard it
   also rechecks its own sealed executable identity, nondumpability, sole
   thread, no shared/mutable mapping, no unexpected descriptor/control
   endpoint, and exclusive subordinate-ID/ptrace authority. Once the
   terminal stop is accepted, the tracee is never resumed except for supervisor
   kill/reap. A non-glibc loader or one that cannot guarantee startup audit and
   the post-constructor/pre-main barrier fails V1.

This is a deliberately single-threaded offline publication lane, not a general
Python sandbox. All seven thread-count members of `determinism_environment`
must equal canonical decimal `1` on Linux, and any library that nevertheless
attempts to create a thread makes the run non-publishable. Scalar syscall
arguments and the stopped descriptor table are therefore immutable across the
entry decision; the design does not use `SECCOMP_USER_NOTIF_FLAG_CONTINUE` or
claim that a race-prone userspace-notification check is a security boundary.

The mount tree is transport, not authority: inode-wide memfd seals make every
runtime/source/input alias immutable, while absence of shared mappings and
outside handles closes live writer routes. A read-only bind alone is
insufficient because another mount may still write the inode. fs-verity alone
is also insufficient because it does not close name replacement or every live
alias. After a leaf is sealed, deletion or replacement of its original source
pathname is neutral; failure is required only when the source cannot be
captured before sealing or an actual read/mapping does not resolve to the
retained sealed leaf.

Darwin V1 has no admitted publication implementation. Endpoint Security plus
Hardened Runtime can constrain executable mappings and task-right acquisition,
but it does not provide the required supported deny boundary for anonymous,
System V, and POSIX shared memory, Mach memory-entry transfer, XPC shared
memory, inherited IPC handles, or asynchronous device/I/O completion. Minimal
App Sandbox entitlements still do not establish this closed contract, and the
deprecated custom Seatbelt interfaces are not an admissible fallback. A Darwin
request therefore fails in native preflight before Python starts and produces
no environment record, candidate owner, or public provenance. Enabling Darwin
later requires a separately reviewed VM/container or supported kernel boundary,
coordinated schema and hash-domain changes, and full real-machine adversarial
admission; no positive Darwin record exists under V1.

Every callback and loader-namespace enumeration is joined to the supervisor's
mapping authority. Complete `/proc/<pid>/maps` fragments for a file image must
match a retained descriptor's device/inode, file offsets, permissions, and
exact ELF header/`PT_LOAD` layout; `AT_PHDR` binds the process executable and
`AT_BASE` binds the interpreter. Every executable-image mapping must have
passed the continuously active VM policy and must never have been writable; a
JIT, anonymous executable mapping, write-to-execute transition, or private-
ledger gap fails before publication.
Non-executable kernel pseudo mappings that are not loader images are not
`runtime_dependencies`, but their complete private VM-region baseline and
every policy-observed transition must agree at all guards. A `[vsyscall]`
region is forbidden rather than classified here. One public mapping
identity at two distinct bases, any unload/remove/unmap before the supervisor
accepts the verified pre-exit handoff, any image outside the sealed root, any
unconsumed executable-map event, or any policy/callback/history/final-
enumeration disagreement fails. Ordinary OS teardown after that handoff cannot
publish or mutate artifacts and is not a closure event. A late load before the
operation barrier is allowed only from an already sealed leaf, passes the same
kernel mediation, and enters the complete mapping set; every load or executable
permission transition after the barrier fails.

`dl_iterate_phdr` is only a base-namespace cross-check in V1. glibc selects the
namespace containing its caller, so a call from the Python collector cannot
establish completeness while `LD_AUDIT` has loaded the auditor in a separate
namespace. The collector nevertheless calls it twice after the actual
operation at the no-import/no-mutation barrier and records every callback's raw
`dlpi_name` bytes, `dlpi_addr`, `dlpi_phnum`, and ordered program-header tuples.
Those two base-namespace callback streams must agree exactly, but neither is
the authority for the complete loaded-image set.

The authoritative enumeration is
`glibc-r-debug-extended-two-namespace-v1`. From the process executable fixed by
`AT_PHDR`, the stopped supervisor locates its unique `PT_DYNAMIC` and unique
runtime `DT_DEBUG` entry, then follows the exact sealed glibc header's
`r_debug_extended` layout. This is a pinned glibc-2.35-or-later ABI lane plus
an exact behavior preflight, not a claim that another libc exposes the same
protocol. Each node address must lie in the retained process loader's writable
mapping; each `r_ldbase` must equal `AT_BASE`; and each identical nonzero
`r_brk` must lie in that loader's executable `PT_LOAD`. The first node must
have `r_version == 2` and be the base namespace; its nonnull `r_next` must be
the one audit namespace. The
second node must also have version 2, a null `r_next`, a nonnull `r_map`, and a
link-map member that reconciles with the unique sealed `startup-audit` leaf.
Both nodes must be `RT_CONSISTENT`. V1 permits no third, inactive, previously
used, caller-created, or cyclic namespace node; this is deliberately stricter
than counting two currently active namespaces because glibc retains
`r_debug_extended` nodes after a namespace becomes empty. The main
executable's runtime `DT_DEBUG` pointer is the sole root; an `_r_debug` symbol
or copy is never a fallback, and an executable copy relocation against
`_r_debug` is rejected separately during capsule preflight. A missing/duplicate
`DT_DEBUG`, unknown layout, invalid or repeated pointer, inconsistent state, or
unbounded chain is fatal. The exact sealed
glibc/loader pair and auditor fixture must demonstrate this contract in native
preflight; a glibc revision without the version-2 rendezvous is unsupported.

For each namespace the supervisor walks the complete public `link_map`
`l_next`/`l_prev` chain from `r_map` while the sole tracee thread is ptrace-
stopped. It bounds pointer/count traversal by the complete readable VM
projection, does not dereference `l_name`, and
correlates `l_addr` and `l_ld` to exactly one retained leaf's load bias,
`PT_DYNAMIC`, program headers, and complete `/proc/<pid>/maps` fragments, or to
the one vDSO exception below. `l_name` remains private transport and never
identifies an image. The base chain must equal the two `dl_iterate_phdr`
streams after normalization. The union of both link-map chains is then
reconciled one-to-one with the event ledger and every live loader-image
mapping. A physical image represented in both namespaces is coalesced only
when identity, load base, dynamic address, segment layout, and live VM regions
are all identical; the same identity at distinct bases remains fatal. An
orphan link-map node, callback, executable mapping, retained-as-used leaf, or
audit event fails publication.

For each nominal traversal the supervisor first snapshots both complete
`r_debug_extended` headers and every traversed public link pointer, walks and
correlates the chains, then rereads the same header/topology projection before
the tracee can execute. The before/after projection must be byte-identical,
both states must remain `RT_CONSISTENT`, and every pointer must remain within
its already validated readable or loader-owned range. A torn or self-changing
rendezvous is fatal even if the resulting image union happens to match.

The supervisor performs this traversal at the stopped `la_preinit` barrier;
once at `base-ready-capture` and again at `base-ready-commit`; twice at the
stopped `operation-closure-capture`/`operation-closure-commit` barriers with
only the sealed transfer parser executing between them; and once at the non-
resumable pre-exit handoff. Each capture/commit traversal pair
must be byte-identical and is the exact authority for the inline base mapping/
dependency triplets or final mapping/dependency arrays transferred under its
respective `supervisor-*-closure-transfer-v1` policy. The audit-
namespace chain, including the audit leaf and every audit-only `DT_NEEDED`
dependency, must already be complete at `la_preinit` and remain byte-for-byte
stable. Base-namespace additions are allowed only before the operation
barrier, from presealed leaves and through the mediated loader history. Counts,
raw private transport fields, normalized mappings, namespace membership, and
identities must agree at every applicable pass. The complete union must contain
the `AT_PHDR` process image, `AT_BASE` interpreter, the unique `startup-audit`
leaf, and its complete audit closure. A missing member is fatal rather than
silently omitted.

Every public `native_execution.mapping_records` member has exactly
`identity`, `format_kind`, `byte_count`, `slice_offset`, `slice_size`,
`header_commands_sha256`, and `segment_records`. `format_kind` is exactly
`elf64-little`. For a sealed file, `byte_count` and `slice_size` are the whole
leaf length and `slice_offset` is zero. A vDSO record also uses zero slice
offset; its `byte_count` and `slice_size` equal the checked
`max(file_offset+file_size)` over the nonempty segment array. That is a
file-coordinate extent and makes no claim that holes are backed bytes.
`header_commands_sha256` is raw SHA-256 of the exact ELF header plus ordered
program-header bytes that the mapping uses.

An ELF `segment_records` member has exactly `ordinal`, `file_offset`,
`file_size`, `memory_offset`, `memory_size`, `flags`, and `alignment` and
represents one `PT_LOAD` in original order. All integers are non-Boolean and
nonnegative, range arithmetic cannot overflow, file ranges lie within the
stated leaf or mapped vDSO image, memory ranges do not overlap, and the
complete VM-policy ledger plus final live regions cover the normalized records
exactly. A transient or direct mapping cannot be omitted: if it does not remain
as and reconcile with one loader image through handoff, the run fails instead
of emitting a second kind of public mapping record. Absolute addresses, paths,
device/inode values, mount IDs, syscall stops, and load bases are absent.

Sort `mapping_records` by UTF-8 canonical JSON of `identity`. Duplicate
identities or unreferenced records fail. `mapping_record_count` is the exact
length, and `mapping_records_sha256` is SHA-256 of
`b"dartwork-mpl-native-execution-mappings-v1\0"` plus canonical JSON of the
complete array. The complete physical capsule is never hashed into a public
owner: it may contain unused candidate leaves, whereas every mapping record is
the exact successfully mediated, loader-correlated used set. The private VM
ledger may contain a rejected request or a terminally mismatched direct map;
such a run has no public owner at all.

Core role bindings are derived by address containment in those mappings.
`process-executable` is the mapping fixed by `AT_PHDR`; `process-loader` is
fixed by `AT_BASE`.
`python-runtime` contains the address of `Py_GetVersion` obtained from the
already-open process handle; `math-provider` contains
`dlsym(RTLD_DEFAULT,"cos")`; `numpy-multiarray` contains
`PyInit__multiarray_umath` resolved from the already-loaded extension handle.
For a native `math` origin, immediately after the fixed base import and before
the broker is sealed, the sealed native harness—not Python `ctypes`/FFI—freezes
the exact `math.__spec__.origin`,
opens only that already-loaded object with `RTLD_NOLOAD|RTLD_NOW`, retains the
handle through final enumeration, and resolves exactly one `PyInit_math`
address. `math-module` is the one image whose executable segment contains that
address in every frozen enumeration, and it is the same `N` selected by module
ownership below. Its already-derived sealed-file identity—not the origin
path—becomes public. Missing or loading handles, ambiguous containment,
ownership disagreement, or rebound mapping fails; transport facts remain
private.

Every required symbol resolves once to exactly one image. One image may carry
several core roles, represented as one record per `(role,image_key)`. The leaf
selected by `LD_AUDIT` receives exactly `startup-audit`, cross-linked to
`launch_environment`; it may carry no core role. After excluding every image
key carrying a core role or `startup-audit`, remaining audit-namespace image
keys receive `audit-transitive/00000000`, `...00000001`, and so on in
canonical image-key order. After also excluding those keys, remaining base-
namespace image keys receive `native-transitive/00000000`, `...00000001`, and
so on in canonical image-key order. The exact audit closure is therefore
visible without inferring a `DT_NEEDED` graph from public paths. Every union
image receives at least one role; an image that belongs to neither admitted
namespace or an audit-only image labeled `native-transitive` fails. Address
containment uses only executable `PT_LOAD` ranges from the frozen mapping
projection. Overlap or a symbol outside all ranges fails.
Handles use `RTLD_NOLOAD|RTLD_NOW`; a platform without `RTLD_NOLOAD` fails.

Every public `runtime_dependencies` element has exactly `role` and `identity`.
`identity` is exactly one of these closed tagged objects:

```text
{"kind":"file-sha256","sha256":<lowercase 64 hex>}
{"kind":"linux-vdso-memory-sha256","sha256":<lowercase 64 hex>}
```

A `file-sha256` is raw SHA-256 of the exact sealed leaf. It is admitted only
after the VM-to-retained-leaf proof above and must equal its mapping record.
It is forbidden for an image not backed by a retained, fully sealed memfd.
GNU/ELF build IDs, including `PT_NOTE` values, are caller-selectable metadata
and are never an identity, fallback, or independent hash input.

Linux admits exactly one fileless image: the kernel vDSO identified at every
enumeration by setting `errno=0` and reading
`B=getauxval(AT_SYSINFO_EHDR)`. V1 requires `B != 0` and exactly one
base-namespace link-map node plus exactly one base `dl_iterate_phdr` callback
satisfying `dlpi_addr == B`, an ELF header at `B`, `dlpi_phdr == B+e_phoff`,
and `dlpi_phnum == e_phnum`. Both representations must coalesce to the same
physical union image. `dlpi_name`, `l_name`, and the string
`linux-vdso.so.1` have no authority. The header-containing `PT_LOAD` is unique,
has `p_offset=p_vaddr=0`, and contains the complete ELF header and PHDR table
within `p_filesz`. The only admitted triples are
`ELFCLASS64/ELFDATA2LSB/EM_X86_64` with `uname_machine=x86_64` and
`ELFCLASS64/ELFDATA2LSB/EM_AARCH64` with `uname_machine=aarch64`; `e_type` is
`ET_DYN`.

The private `LinuxVdsoMemoryPreimageV1` has exactly `schema`, `elf_header`,
`program_headers`, and `load_segments`, with schema
`linux-vdso-memory-v1`. `elf_header` has exactly `class`, `data`,
`ident_version`, `osabi`, `abi_version`, `type`, `machine`,
`object_version`, `entry_memory_offset`, `phoff`, `shoff`, `flags`,
`ehsize`, `phentsize`, `phnum`, `shentsize`, `shnum`, and `shstrndx`. Each
original-order program header has exactly `index`, `type`, `flags`, `offset`,
`memory_offset`, `physical_address`, `file_size`, `memory_size`, and
`alignment`. Each PHDR-order `PT_LOAD` record has exactly
`program_header_index` and `mapped_bytes_hex`, containing the exact bytes at
`[B+p_vaddr,B+p_vaddr+p_filesz)`. No absolute address enters the preimage.
Require ordered, nonoverlapping, readable, nonwritable `PT_LOAD` ranges,
`p_filesz <= p_memsz`, valid ELF alignment, and an all-zero
`p_memsz-p_filesz` tail.

Every relocation table reachable from `PT_DYNAMIC` is parsed within bounded
`PT_LOAD` file-image bytes. Only the architecture's `R_*_NONE` entries are
allowed; `DT_RELR`, text relocation, unknown encoding, or any relocation that
can write a mapped byte fails. No byte is zeroed, inverse-relocated, or
otherwise normalized; only process-specific base addresses are omitted.
Define:

```text
vdso_sha256 = SHA256(
    b"dartwork-mpl-linux-vdso-memory-v1\0" +
    canonical_json(LinuxVdsoMemoryPreimageV1)
)
```

The public identity's `sha256` is exactly `vdso_sha256`. Both post-operation
enumerations and the pre-exit guard independently reconstruct the complete
private preimage and require byte identity.

The vDSO may carry none of the six core roles or any audit role. It receives exactly one
`native-transitive/<ordinal>` role; a core symbol inside it is fatal. Every
other inode-less loader image and every identity tag outside the two closed
forms above fails.

The canonical image key is canonical JSON of `identity`. Every key resolves to
exactly one mapping record and at least one role. Emit core, `startup-audit`,
`audit-transitive`, and `native-transitive` role records as assigned above and
sort them by UTF-8 canonical JSON of `[role,identity]`.
Duplicate `(role,image_key)` records fail; repeated keys across distinct core
roles are required when one mapping provides several roles and are excluded
from transitive assignment. `dependency_records_sha256` is SHA-256 of
`b"dartwork-mpl-loaded-images-v3\0"` plus canonical JSON of that complete
role-record array; `dependency_record_count` is exactly its length. This
resolves the exact loaded provider instead of inferring one from a version
string such as `libc_ver()`.

Module-file ownership and pure-stdlib collection have one exact computation
base-ready barrier. The raw control/index construction described below has
already completed in the reaped preparer. After the computation broker-ready
barrier, the child reads and freezes the typed base handoff as broker-read
ordinal zero. It then imports these module names exactly once and in this order:
`sys`, `os`, `platform`, `sysconfig`, `math`, `json`, `hashlib`,
`importlib`, `importlib.metadata`, `pathlib`, `fractions`, `decimal`, `struct`,
`types`, then `numpy`. `ctypes`, `_ctypes`, `numpy.ctypeslib`, `_testcapi`, and
the exact additional FFI/debug helpers enumerated by the selected profile are
absent from the manifest and forbidden as surface hygiene; this is not claimed
to remove every same-process memory mechanism. No project authoring module is part of this base
list, and computation-side `importlib.metadata` may not enumerate distribution
metadata or reconstruct the private index.

All stdlib/distribution lookup state visible to computation comes from the
public `base_handoff.runtime_import_manifest` and its synthesized sealed trees,
never the preparer's physical roots. The manifest path hook's normalized child
order, node kind/mode/byte count, and negative module lookups are deterministic
consequences of that complete public manifest; raw runtime-tree stat/getdents
and path lookup against a private/unused candidate tree are denied. Every
successful file read still receives one public used-read
record. A runtime module/path outside the manifest, direct access to dist-info
or the private located-file index, or a manifest-backed import/read before its
permitted phase is fatal. The successful base-ready commit freezes only the
fixed base prefix. After the invocation handoff and operation-ready source
transition, a policy-authorized project module may import an already-loaded
runtime module or first request another manifest-declared stdlib/distribution
module through the same sealed manifest hook. Every resulting open is brokered,
the frozen post-operation module table must agree, and every non-base module,
used-file trigger, dependency, and mapping belongs only to the final/runtime
closure and full environment hash. It cannot retroactively enter or alter the
common-base preimage. Thus post-base Matplotlib and other profile-declared
transitive imports are reachable without granting an ambient site tree.

Immediately after NumPy and the base collectors finish, the child enters the
two-stop `supervisor-base-ready-closure-transfer-v1` barrier. Before the first
stop it freezes its broker prefix plus complete stdlib/module projections into
one dedicated 8,388,608-byte anonymous-private, writable, non-executable
transfer buffer allocated before base import and registered only by the first
stop's exact control ABI. The buffer has no child alias. Its first eight bytes are an
unsigned little-endian payload length; bytes after that payload through the
fixed capacity are zero. The initial payload is canonical JSON for an exact
`BaseReadyChildProjectionV1` object having exactly:

```text
schema,
base_broker_read_records, base_broker_read_record_count,
base_broker_read_records_sha256,
base_stdlib_closure_records, base_stdlib_closure_count,
base_stdlib_closure_sha256,
base_module_records, base_module_record_count, base_module_records_sha256,
child_projection_sha256
```

Its schema is
`oklab-authoring-base-ready-child-projection-v1` and the self-hash domain is
`b"dartwork-mpl-base-ready-child-projection-v1\0"` over the complete object
with only `child_projection_sha256` omitted.

The first stopped syscall-exit state is `base-ready-capture`: an exact
`prctl(PR_GET_DUMPABLE)` issued only from its sealed harness range and required
to return zero. While the sole tracee is stopped, the supervisor reads the
registered buffer twice with `process_vm_readv`, requires byte identity and
zero tail, reconciles the broker prefix with its receipt log and the child's
stdlib/module projection with the frozen module table, traverses the complete
`r_debug_extended`/VM state, and constructs the base dependency/mapping arrays.
It then constructs one `BaseReadyClosureTransferV1` object having exactly:

```text
schema,
base_broker_read_records, base_broker_read_record_count,
base_broker_read_records_sha256,
base_stdlib_closure_records, base_stdlib_closure_count,
base_stdlib_closure_sha256,
base_module_records, base_module_record_count, base_module_records_sha256,
base_dependency_records, base_dependency_record_count,
base_dependency_records_sha256,
base_mapping_records, base_mapping_record_count, base_mapping_records_sha256,
base_ready_closure_transfer_sha256
```

Schema is
`oklab-authoring-base-ready-closure-transfer-v1`; its self-hash domain is
`b"dartwork-mpl-base-ready-closure-transfer-v1\0"` over the complete object
with only `base_ready_closure_transfer_sha256` omitted. Every triplet is the
exact inline public array/count/digest declared by the environment schema.

The supervisor overwrites only that registered buffer with the new exact
length, canonical object, and zero tail via `process_vm_writev`; a short write,
second target range, changed registered mapping, oversized payload, nonzero tail, or
any write outside the exact base-ready-capture or later operation-closure-
capture state is fatal. It rereads the complete
buffer twice before resuming. This is the first of exactly two
supervisor-to-child memory writes
and is an explicit administrator-TCB action, not a capability available to the
child or another principal. The child strict-parses the transferred bytes using
already loaded harness code, verifies every count/digest and its own three
triplets, retains the five final triplets, and immediately enters the second
zero-return `PR_GET_DUMPABLE` stop, `base-ready-commit`, without an import,
source read, `dlopen`, finalizer, signal handler, or operation call. At commit
the supervisor rereads the unchanged buffer, repeats the full loader/VM
traversal, requires byte-identical closure, and ACKs only exact equality.

The transfer object and raw address are private framing and are not an extra
public environment field; its five component triplets are the inline public
preimages and must equal the supervisor-retained transfer again at terminal
stop. The base boundary is the successful commit ACK. The invocation handoff
and source root remain unreachable until then, and no broker read occurs during
the two-stop transfer.

The same registered buffer later carries the distinct
`supervisor-final-runtime-closure-transfer-v1` two-stop barrier. After the
operation returns, the child forbids further import/read/`dlopen`, freezes its
module and project state, reconciles both receipt logs, and writes one
`FinalClosureChildProjectionV1` object having exactly:

```text
schema,
broker_read_record_count, broker_read_records_sha256,
project_import_event_count, project_import_events_sha256,
project_namespace_packages, project_imports,
module_guard_transition_records, module_guard_transition_count,
module_guard_transition_records_sha256,
module_records, module_record_count, module_records_sha256,
child_projection_sha256
```

Its schema is `oklab-authoring-final-closure-child-projection-v1`; its self-hash
uses `b"dartwork-mpl-final-closure-child-projection-v1\0"` over the complete
object with only `child_projection_sha256` omitted.
`module_guard_transition_records` is the complete occurrence-order array of
successful logical authorization completions after base commit. It is not the
preimage of individual dictionary operations. Each record has exactly
`ordinal`, `transition_kind`,
`module_name`, and `authority_index`; ordinal is contiguous from zero. Kind is
`manifest-module`, `project-module`, `synthetic-shell`, or `project-namespace`.
The index selects respectively the exact manifest record, the UTF-8-sorted
required/optional policy union, shell record 0/1, or sole namespace record 0;
the selected authority must name that module and its exact final module row.
Counts are exact and the digest uses
`b"dartwork-mpl-module-guard-transitions-v1\0"` plus canonical JSON of the full
array. Existing-base lookups produce no transition; a successful post-base new
module produces exactly one, after the stock success-tail pop/reinsert plus
V1's initial-object identity check for an ordinary import. No failed authorization can appear in a publishable run
because that invocation terminates without publication. The complete array, count, and
digest are retained verbatim as the three corresponding
`dependency_discovery` fields; the child projection is not their sole
preimage.

At the exact
`operation-closure-capture` zero-return control stop, the supervisor validates
that projection against its receipt/event logs and source policy. It requires
the transition array/guard state, base module prefix invariants, exact manifest binding/origin/receipt links,
exact project event/source rows, only the admitted shell/namespace exceptions,
and every native origin's unique live mapping; no child-authored module row is
accepted by self-assertion. It then performs the
first complete final `r_debug_extended`/VM traversal, and constructs one
`FinalRuntimeClosureTransferV1` object having exactly:

```text
schema,
module_records, module_record_count, module_records_sha256,
mapping_records, mapping_record_count, mapping_records_sha256,
runtime_dependencies, dependency_record_count, dependency_records_sha256,
final_runtime_closure_transfer_sha256
```

Its schema is `oklab-authoring-final-runtime-closure-transfer-v1`; its self-hash
uses `b"dartwork-mpl-final-runtime-closure-transfer-v1\0"` over the complete
object with only `final_runtime_closure_transfer_sha256` omitted. The module
triplet is the supervisor-validated complete terminal projection and is exactly
`dependency_discovery.module_records` and its count/hash. The mapping
triplet is exactly `native_execution.mapping_records` and its count/hash; the
dependency array is exactly top-level `runtime_dependencies` and its count/hash
equals the fields in `dependency_discovery`. The supervisor overwrites only the
registered buffer with this object using the same full-write/double-read/zero-
tail rules. This is the second and final supervisor-to-child memory write.

The child parses and retains all three final arrays, recomputes every count/digest,
and immediately enters `operation-closure-commit` without another import,
input read, mapping change, finalizer, signal handler, operation call, or output
mutation. The supervisor rereads the unchanged transfer and repeats the full
traversal; only byte-identical closure receives the commit ACK. The child may
then construct the complete environment and primary using the retained public
arrays. At the non-resumable terminal stop the supervisor traverses once more
and requires the primary's arrays, its retained transfer, live mappings, and
private native ledger to agree. The transfer wrapper/address/hash are private
framing and do not become an extra public field.

The supervisor alone may revalidate the retained raw control inputs/private
index after computation; the child can recheck only the public base handoff and
used-read receipts. Equal physical stdlib/platstdlib or purelib/platlib roots
were coalesced privately by the preparer, while their public role identities and
the exact synthesized tree occur in the runtime-import manifest. The optional
strictly empty `python_startup.stdlib_archive` remains role-bound and may supply
no module. No automatic site processing or `.pth` file constructs either tree
or path stage.

After the profile operation and before loader enumeration, freeze the tuple of
`(module_name,module_object_identity)` from `sys.modules.items()`, sorted by
UTF-8 module-name bytes. A null module object remains in the frozen tuple but
contributes no file record. Traversal may call no import API. For each non-null
frozen object, inspect only the already-present `__spec__`,
`__spec__.origin`, and `__file__`. Built-in/frozen origins, missing specs,
namespace/no-origin modules, and null placeholders are fileless cases.

For every file-backed origin, compute five facts from already frozen authority:

```text
P = exact path/hash match in captured project source_files
D = exact verified located-path owner in the distribution index below
I = component-boundary containment beneath coalesced purelib/platlib
S = matching coalesced stdlib root groups
N = matching sealed loaded-mapping record for an extension origin
```

Ownership is decided in this exact order:

```text
if P and D:                         fail conflicting exact owners
if more than one D:                 fail multiple distribution owners
if P:                               project owner
elif exactly one D:                 distribution owner
elif I:                             fail unowned site-install path
elif extension:
    require exactly one N           native-image owner
elif source/bytecode and len(S)==1: stdlib owner
else:                               fail unresolved or ambiguous owner
```

For the native `math` module, `N` is not inferred by comparing its path string
with a tagged public identity. It is exactly the sealed mapping record selected
by the retained `PyInit_math` address-containment chain above; its frozen
origin is used only to obtain the no-load handle. The ownership, mapping, and
core-role passes must therefore select the same unique identity before any
public record is serialized.

A project- or distribution-owned extension also binds exactly one native
mapping; packaging ownership and loaded-image evidence are orthogonal, not
competing stdlib owners. That mapping must have `kind="file-sha256"`, and its
sealed-leaf hash must equal the extension's exact project-source or
distribution used-file hash. A vDSO identity can never stand in for an
installed extension. For NumPy, that same hash also equals
`numpy.multiarray_umath_sha256` and the `numpy-multiarray` mapping identity.
A distribution-owned source file never enters the stdlib closure.
Component containment treats path components, so a sibling such
as `site-packages2` is not a site-root match. Every distribution origin is the
same guarded regular provisioned member named by its canonical declared path;
a symlink, relocation, generated file, or resolved stdlib target cannot acquire
distribution ownership. Conflicting origin/file identity, a symlink component,
a missing file, or any unresolved case fails. After
traversal, the sorted `(name,object identity)` tuple must be unchanged; any
import, replacement, or deletion fails.

Each stdlib file record has exactly `root_role`, `relative_path`,
`file_kind`, `sha256`, and `module_aliases`. Root role is `stdlib-root` or
`platstdlib-root`; kind is `source` or `bytecode`; aliases are the complete
non-empty globally unique UTF-8-sorted frozen `sys.modules` keys resolving to
that same file. The record binds the loaded origin bytes and never substitutes
source for bytecode. Relative path is surrogate-free POSIX with no absolute or
`..` component. Alias grouping happens only after ownership is fixed. Sort by
UTF-8 `(root_role,relative_path)`; the complete array is
`python.stdlib_closure_records`, count is its exact length, and
`stdlib_closure_sha256` is SHA-256 of
`b"dartwork-mpl-python-stdlib-closure-v3\0"` plus canonical JSON of that array.
This binds modules such as `fractions` and `json` without double-counting aliases
such as `os.path`; mutating the preimage, count, or hash fails.

Installed-distribution ownership uses the authoritative logical paths declared
by each `importlib.metadata.Distribution`, but public evidence includes only
files actually used by a frozen module origin or computation broker read, plus
the deliberately public runtime-import manifest that defines the common-base
tree. In the isolated control-preparer process, after its broker-ready barrier
and fixed preparer imports but before its terminal stop, build the private
located-path index from each non-null `distribution.files` sequence and that
same object's `locate_file(path)`. Enumerating distribution metadata and
resolving or opening a located entry are control-plane broker events over
already sealed runtime inputs; every actual file open is recorded in the
preparer's private append-only ledger. The computation process neither calls
these ownership methods nor receives the resulting index. No installer-,
supervisor-, caller-supplied, or computation-reconstructed path allowlist is
trusted.
Validate every `declared_path=path.as_posix()` as a nonempty surrogate-free
printable-ASCII relative POSIX string with no NUL/control, empty, `.`, `..`, or
backslash component and no trailing slash. It must be the exact regular-member
name copied byte-identically by `sealed-wheel-provisioning-v2`; no component is
collapsed or relocated. Absolute/outside-root paths, installer-generated
entry-point scripts, `.data` outputs, device/inode facts, unused metadata,
`direct_url.json`, and their bytes/hashes remain private and cannot become a V1
ownership row merely because some ambient installer would have declared them.

When an exact frozen origin/read matches that private index, materialize one
public used-file record with exactly `declared_path`, `file_kind`, and
`sha256`. File kind is exactly the manifest owner's `source`, `extension`, or
`regular-data`; the regular file uses its guarded raw-byte SHA-256. A symlink or any
other file kind, duplicate declared paths, two entries resolving to one used
location, or one used file claimed by two distributions fails.
`packages_distributions()`,
package-name inference, and directory-prefix ownership are forbidden.

Each distribution row also contains `locked_artifact_identity`, having exactly
`normalized_name`, `version`, `artifact_kind`, and `artifact_sha256`.
`artifact_kind` is the literal `wheel` in V1. `artifact_sha256` is the ordinary
raw-byte SHA-256 of the exact wheel archive supplied to the sealed direct-member
provisioning transaction; it is a content leaf, not another semantic hash.
Name/version must equal both installed public metadata and the wheel's single
strictly parsed distribution metadata identity.

Name/version matching, compatible-tag inference, a receipt digest, cache key,
URL fragment, or caller-supplied hash does not prove artifact selection. The
static supervisor's exact `sealed-wheel-provisioning-v2` transaction and
`WheelProvisioningWitnessV2` above are the sole installed-root producer and
selection witness. Before the control-preparer launch, the supervisor seals the
selected wheel archives, witness, distribution metadata, installed located
entries, and `uv.lock` into the role-bound runtime-input set; no external
installer, live cache, prior installation root, or original lock path remains
reachable. After the preparer broker-ready barrier, control preparation reads
the witness in its fixed position, independently reopens and hashes those
guarded bytes, strictly parses the privately captured `uv.lock`, and requires
the recomputed digest to
occur as a `sha256:` digest in a `wheels` row of a matching registry package
entry. The witness member map, installed Distribution metadata/located entries,
lock row, and guarded archive must form one unique association. Zero matches, two different selected
archives, a stale or unavailable witness, or conflicting associations fail
before publication. Duplicate raw rows that differ only in URL/location but
name the same selected bytes collapse to the same public identity.

The V1 private lock parser is exactly `uv-lock-toml-parser-v1`, compiled into
the sealed control-preparer bootstrap and therefore bound by that public
bootstrap source hash. No ambient `tomllib`, third-party TOML package, or
version-selected fallback participates. It accepts only strict TOML 1.0.0:
well-formed UTF-8, no NUL/surrogate, semantic duplicate key/table/redefinition,
invalid escape/date/number, recovery, or implementation extension. The complete
document is 1..16,777,216 bytes, has nesting depth at most 32, at most 1,000,000
total scalar/container values, and no decoded string over 1,048,576 bytes;
checked-limit failure is terminal. It is parsed before selection, but only this closed typed projection is
authoritative: top-level integer `version=1`, integer `revision=3`, and a
nonempty `package` array of tables. Each candidate package table has one string
`name`, one string `version`, one inline/table `source`, and one array `wheels`.
The source has exactly one nonempty string key `registry`; a direct/path/VCS/
editable key or mixed source fails for a used candidate. Each wheel element is
an inline/table value with exactly one string `hash` relevant to selection; that
value is lowercase `sha256:<64 hex>`. URL, filename, size, and time fields may
also occur with valid TOML types but never disambiguate or order selection.

Candidate Name is normalized by the exact public ASCII algorithm above and its
Version uses the exact V1 version grammar. The selected name/version/source
must match one package table and its rehashed archive must match at least one
wheel hash. Multiple raw wheel rows are allowed only when every matching row
names the same digest; they collapse to that one byte identity. Other wheel rows
with different hashes remain permitted unselected private candidates. Two
package tables matching the identity, zero or two different guarded archives
for it, a hash array/string hybrid, duplicate relevant key, unknown top-level
lock version, or malformed ignored field fails instead of selecting by parser order. Dependency,
marker, sdist, unselected-package/wheel, URL, filename, size, and time values
remain private parsed syntax and do not enter the public projection.

V1 publication rejects a used sdist-built, editable, path, Git, VCS, or direct-
URL distribution rather than hashing its private source or pretending that a
wheel tag identifies what was installed. Supporting such installations needs
a later schema with explicit build-output identity and provenance. Source or
registry URLs, wheel filenames, sizes, upload times, markers, dependency rows,
sdists, unselected wheels, receipt/cache bytes or locators, complete lock
package entries, the whole lock, and every hash derived from those excluded
private values are not public inputs. The publisher discards the private
lock/receipt/cache locator state after sealing the public owner.

Sort only the used-file records by UTF-8 `declared_path`. For normalized
distribution name `numpy`, the used-distribution hash is SHA-256 of
`b"dartwork-mpl-numpy-used-distribution-v1\0"` plus canonical JSON having
exactly `locked_artifact_identity` and that used-record array. That exact array
is `numpy.distribution_records`; its lock identity is
`numpy.locked_artifact_identity`, and `numpy.used_distribution_sha256` is the
recomputed value.
`build_config_sha256` uses
`b"dartwork-mpl-numpy-build-capabilities-v1\0"` plus canonical JSON having
exactly `schema="numpy-build-capabilities-v1"`, `cpu_baseline`, and
`cpu_dispatch_compiled`. The collector may inspect
`numpy.show_config(mode="dicts")` privately, but only its mapping
`["SIMD Extensions"]` and exact list-valued keys `baseline`, `found`, and `not
found` participate in this typed projection. Compiler commands, library/include
directories, raw config strings, and their hashes are forbidden public inputs.
`cpu_baseline` is the UTF-8-sorted unique string
array from `baseline`; `cpu_dispatch_compiled` is the same normalization of
`found`; `cpu_features_enabled` is the UTF-8-sorted set of keys whose value is
exactly Boolean true in
`numpy._core._multiarray_umath.__cpu_features__`. A non-string element,
duplicate after normalization, missing key, non-Boolean feature value, or
unexpected container type fails. The core hash is raw SHA-256 of the guarded
bytes backing `numpy._core._multiarray_umath`, and its role resolves that same
loaded binary; its absolute path is private. The preparer distribution version
must equal computation `numpy.__version__`; enumeration comes only from the
preparer's `importlib.metadata.distribution("numpy").files`, and each path is
resolved by that same object's `locate_file`. Computation cross-checks only the
typed identity, manifest-backed files actually available to it, and loaded
module/mapping records; it does not repeat metadata enumeration. Collection or
cross-check failure is fatal.

`runtime_distributions` is the complete array of every non-project Python
distribution owning an exact frozen imported-module origin or exact computation
broker-read record; NumPy occurs exactly once even when only its
base import used it. The owning origin/read set is derived from the frozen
module table and the broker ledger during validation rather than inferred from
a package label. Control-plane reads used only to construct and verify the
candidate index do not by themselves make every installed distribution used;
they exist only in the reaped preparer ledger. A computation event cannot be
relabeled as control-plane. Each record
has exactly `name`, `version`,
`locked_artifact_identity`, `records`,
`ownership_triggers`, and `used_distribution_sha256`. `name` is the distribution metadata
`Name` after lowercasing and replacing every maximal `[-_.]+` run with `-`;
`version` is the exact nonempty metadata version. Non-NumPy used-file hashes use
SHA-256 of `b"dartwork-mpl-python-used-distribution-v1\0"`, normalized name,
one NUL, and canonical JSON having exactly the lock identity and complete used
records. Sort by UTF-8 name and
reject duplicate names, unresolved imported files, and one file claimed by two
distributions. The unique NumPy row must satisfy field equality:
`row.version == numpy.version`,
`row.locked_artifact_identity == numpy.locked_artifact_identity`,
`row.records == numpy.distribution_records`, and
`row.used_distribution_sha256 == numpy.used_distribution_sha256`.

The selected-artifact lock projection has exactly:

```text
{
    "schema": "oklab-selected-artifact-lock-projection-v1",
    "artifacts": [
        <each runtime_distributions[i].locked_artifact_identity>
    ]
}
```

`artifacts` is nonempty, contains exactly the complete used-distribution set
and exactly one NumPy identity, and contains no unused row. Each identity's
normalized name and version equal its surrounding runtime-distribution row.
Sort identities by the UTF-8 tuple `(normalized_name, version, artifact_kind,
artifact_sha256)`; normalized names are unique. Unknown, omitted, duplicated,
reordered, or caller-injected identities fail. Define:

```text
selected_artifact_lock_projection_sha256 = SHA256(
    b"dartwork-mpl-oklab-selected-artifact-lock-projection-v1\0" +
    canonical_json(selected-artifact lock projection)
)
```

The projection is reconstructed rather than duplicated as another environment
object. The complete `runtime_distributions` rows are its archived canonical
preimage. An unused lock row or artifact is identity-neutral only when it is
absent from both the prospective `runtime_import_manifest` and the observed
`runtime_distributions` closure. A manifest-selected candidate remains common-
base identity even when no runtime trigger later uses it; in that case it is
absent only from this selected-artifact projection. Changing a wheel bound by
either public object changes the corresponding intended hash chain.

`ownership_triggers` is non-empty and contains the complete reason that the
distribution participates. Each trigger has exactly `kind`, `module_name`,
`broker_read_ordinal`, `declared_path`, and `sha256`. For
`kind="module-origin"`, module name is non-empty and broker ordinal is null; for
`kind="broker-read"`, module name is null and ordinal is a non-Boolean
nonnegative integer naming the exact event in
`dependency_discovery.broker_read_records`. Declared path/hash equal one distribution
record. Sort by kind rank module-origin/broker-read, then UTF-8
module name or ordinal, and reject duplicates. Every exact distribution-owned
frozen origin and computation broker read has one trigger and no unused
trigger is allowed,
so the historical environment retains the partition preimage rather than only
the resulting used-file hashes.

During control preparation, only after that child's sealed bootstrap has
installed its broker and the supervisor has accepted broker-ready, the preparer
constructs the exact distribution/stdlib private index without importing NumPy
or project modules. Its read authority is the closed singleton, policy,
selected-wheel, distribution-metadata/located-entry, stdlib-inventory/entry,
lock, and optional shell-source roles above. Every metadata enumeration,
`Distribution.files`/`locate_file()` resolution, lock/wheel/policy read, and
located-file read enters its private append-only ledger. It emits only the typed
base/runtime-import and invocation/project/dispatch projections, closes the
private transfer manifest, and is killed/reaped.

The supervisor then authorizes computation only through the public synthesized
runtime trees and its own private per-entry index; neither a physical
distribution/stdlib root nor the raw index is child-visible. Computation starts
the retained public read stream with base handoff ordinal zero, reaches the
stopped base-ready closure before reading the invocation handoff, and later
appends only the public source root at operation-ready. After the operation,
frozen module origins, public tree manifest, and complete computation read/event
streams derive the `runtime_distributions` subset above. Each used access has
exactly one stored record and trigger, while the supervisor reconciles both
child ledgers and the private transfer inventory before publication. A missing,
extra, reordered, wrong-lifetime, unsealed, or pre-broker event fails. This makes
Matplotlib or another transitive distribution visible and byte-bound when an
entry module actually uses it, while excluded installer-generated scripts grant
no authority to read neighboring executables.

All scalar metadata strings are non-empty unless a field is explicitly nullable;
`hexversion`, counts, and ranks are non-boolean nonnegative integers. Hashes are
lowercase 64-digit SHA-256 and byte encodings are lowercase even-length hex.
`python.version` has exactly `major`, `minor`, `micro`, `releaselevel`, and
`serial`; the first, second, third, and last fields are non-boolean nonnegative
integers and release level is `alpha`, `beta`, `candidate`, or `final`.
`python.build` has exactly the non-empty strings `build_no` and `build_date`.
The scalar extractor table is normative:

| Field | Exact extractor and normalization |
|---|---|
| `python.implementation` | `sys.implementation.name`, unchanged string |
| `python.version` | named fields of `sys.version_info`, with `candidate` serialized when Python reports `candidate` |
| `python.hexversion` | `sys.hexversion`, exact integer |
| `python.build` | `platform.python_build()` two-tuple mapped to `build_no,build_date` |
| `python.compiler` | `platform.python_compiler()`, unchanged string |
| `python.cache_tag` | `sys.implementation.cache_tag`, unchanged string |
| `python.soabi` | `sysconfig.get_config_var("SOABI")`, unchanged string |
| `python.multiarch` | `sysconfig.get_config_var("MULTIARCH")`, unchanged string |
| `python.executable_sha256` | raw bytes of the retained sealed `process-executable` leaf; its private `sys.executable` resolution is only a pre-seal locator |
| `platform.os_name` | `os.name` |
| `platform.sys_platform` | `sys.platform` |
| `platform.uname_system` | `os.uname().sysname`, checked against the closed platform family |
| `platform.uname_release` | `os.uname().release`, nonempty public OS-release identifier |
| `platform.uname_machine` | `os.uname().machine`, normalized architecture identifier |
| `platform.byteorder` | `sys.byteorder` |

Every string in this table must be a non-empty `str`; every tuple has exactly
the stated arity; every integer rejects Boolean. No fallback API, display label,
locale conversion, or whitespace normalization is allowed. A platform lacking
one value fails rather than inventing an empty value. `os.uname().nodename`
and `.version` are private and are neither serialized nor hashed. The
separately specified `os_build_id` and `cpu_identity` algorithms below are their
only extractors.

The retained `platform` strings are the exact normalized public fields above;
byte order is exactly `little`. Before constructing the preparer mount tree, the
native supervisor reads the host `/etc/os-release` and `/proc/cpuinfo` through
no-follow descriptors, copies both into non-executable fully sealed input
leaves, and creates a canonical sealed platform-attestation leaf from the
rules below. Neither child has a procfs mount. Only the control preparer reads
each of those three leaves exactly once, in the closed private-control positions
above, after its broker-ready barrier. It derives the typed platform record and
byte-identical canonical attestation for the base handoff, then dies before
computation. The fresh computation child receives no raw leaf; its local scalar
Python/OS extractors must equal exactly the handoff's `os_name`, `sys_platform`,
`uname_system`, `uname_release`, `uname_machine`, and `byteorder` before base-
ready. It cannot independently derive `os_build_id` or `cpu_identity` without
the deliberately absent raw leaves; those remain preparer-derived and
supervisor-attested typed fields. The brokers and supervisor deny a direct host read, a second/late preparer read, any
computation read, or any unmatched byte.
`os_build_id` is `linux-os-release-sha256:` plus the raw SHA-256 of the sealed
`/etc/os-release` copy.
`cpu_identity` has exactly `kind="linux-proc-cpuinfo-v1"` and `records`; parse
the sealed `/proc/cpuinfo` copy without locale conversion, retain only
`vendor_id`, `cpu family`, `model`, `stepping`, `model name`, `Features`, and
`flags`, normalize horizontal ASCII whitespace in each value to one space,
form unique `[name,value]` pairs, and sort them by raw UTF-8 bytes. Each record
has exactly `name` and `value`, and at least one architecture-appropriate
feature row plus `model` or `model name` is required. The preparer recomputes the
same typed record from the sealed source and requires byte equality with the
sealed attestation. These collection rules are part of the stable runtime
identity rather than optional display metadata.

The attestation leaf is not an open-ended “canonical” record. Its bytes are
exactly UTF-8 canonical JSON plus one terminal LF for this exact object:

```text
{
    "schema": "oklab-authoring-platform-attestation-v1",
    "os_release": {
        "byte_count": <raw os-release leaf length>,
        "raw_sha256": <raw os-release leaf SHA-256>,
        "os_build_id": <the exact prefixed value above>
    },
    "cpuinfo": {
        "byte_count": <raw cpuinfo leaf length>,
        "raw_sha256": <raw cpuinfo leaf SHA-256>,
        "cpu_identity": <the complete typed record above>
    }
}
```

Both counts are positive non-Boolean integers and both hashes are lowercase
64-digit SHA-256. The preparer hashes the two guarded raw source leaves, derives
`os_build_id` and `cpu_identity`, reconstructs this complete object, canonical-
serializes it with the terminal LF, and requires byte equality with the third
sealed leaf. The private-ledger count/hash for each role covers the exact bytes
actually returned. An omitted/extra key, alternate field association, JSON
spelling, whitespace, newline count, source count/hash, or typed projection is
fatal. The raw CPU-info SHA-256 and attestation-leaf SHA-256 remain private
control evidence. The raw OS-release SHA-256 appears publicly only through the
suffix of byte-identical typed `platform.os_build_id` fields, including the
nested base-handoff copy of the same `platform` object; a standalone digest
field, differing copy, or any other raw-source/attestation hash is forbidden.

`sys_float_info` has exactly `max`, `max_exp`, `max_10_exp`, `min`, `min_exp`,
`min_10_exp`, `dig`, `mant_dig`, `epsilon`, `radix`, and `rounds`; floating
fields use section 5.1's binary64 form and integer fields reject booleans.
Require IEEE binary64 invariants including radix 2, mantissa 53, and rounds 1.
`rounding_mode` has exactly `name="FE_TONEAREST"` and the non-boolean native
integer `native_value` returned by `fegetround()`.

`subnormal_probe` has exactly `policy_id`, `records`, and `verdict`, with ID
`binary64-gradual-underflow-v1` and verdict `PASS`. Every record has exactly
`operation`, `inputs`, `expected_output`, and `observed_output`; numeric values
are exact `float.hex()` strings. Construct inputs at runtime from hex strings
and emit exactly these six canonical records in this order, replacing only each
`observed_output` placeholder with the observed string:

```json
[
  {"operation":"python-min-normal-times-half",
   "inputs":["0x1.0000000000000p-1022","0x1.0000000000000p-1"],
   "expected_output":"0x0.8000000000000p-1022","observed_output":"<observed>"},
  {"operation":"python-min-subnormal-times-one",
   "inputs":["0x0.0000000000001p-1022","0x1.0000000000000p+0"],
   "expected_output":"0x0.0000000000001p-1022","observed_output":"<observed>"},
  {"operation":"python-add-two-min-subnormals",
   "inputs":["0x0.0000000000001p-1022","0x0.0000000000001p-1022"],
   "expected_output":"0x0.0000000000002p-1022","observed_output":"<observed>"},
  {"operation":"python-nextafter-zero-toward-max-finite",
   "inputs":["0x0.0p+0","0x1.fffffffffffffp+1023"],
   "expected_output":"0x0.0000000000001p-1022","observed_output":"<observed>"},
  {"operation":"numpy-float64-vector-min-normal-times-half",
   "inputs":["0x1.0000000000000p-1022","0x1.0000000000000p-1"],
   "expected_output":"0x0.8000000000000p-1022","observed_output":"<observed>"},
  {"operation":"numpy-float64-vector-min-subnormal-times-one",
   "inputs":["0x0.0000000000001p-1022","0x1.0000000000000p+0"],
   "expected_output":"0x0.0000000000001p-1022","observed_output":"<observed>"}
]
```

The first three use the literal Python `*`, `*`, and `+` operations; the
fourth calls `math.nextafter`. Each NumPy row constructs a C-contiguous,
shape-`(1,)` `numpy.float64` array containing the first input and calls
`numpy.multiply(array,numpy.float64(second_input))`; the result must retain
dtype, shape, and C contiguity, and the recorded scalar is exactly
`result[0].item().hex()`. Python results use `result.hex()`. No wider vector,
reduction, cast, or alternate operation is conforming.

Every observed bit pattern must equal its expected value; otherwise collection
fails. `numpy_geterr` has exactly `divide`, `over`, `under`, and `invalid`, each
one of `ignore`, `warn`, `raise`, `call`, `print`, or `log`.
`determinism_environment` is the complete non-path child-environment
projection. It has exactly the following UTF-8-key-sorted members:
`ACCELERATE_MAX_THREADS`, `BLIS_NUM_THREADS`, `GLIBC_TUNABLES`, `LANG`,
`LC_ALL`, `MKL_NUM_THREADS`, `NPY_DISABLE_CPU_FEATURES`,
`NPY_ENABLE_CPU_FEATURES`, `NUMEXPR_NUM_THREADS`, `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `PYTHONDONTWRITEBYTECODE`, `PYTHONHASHSEED`,
`PYTHONMALLOC`, `PYTHONNOUSERSITE`, `PYTHONUTF8`, `TZ`, and
`VECLIB_MAXIMUM_THREADS`. Each value is an exact `{state,value}` record. The
two `NPY_*_CPU_FEATURES` members are exactly
`{"state":"missing","value":null}` and are absent from the child; all other
members have `state="value"`. Each of the seven thread controls has value
`"1"`; `GLIBC_TUNABLES` is exactly `"glibc.pthread.rseq=0"`; `LANG` and
`LC_ALL` are `"C"`; `PYTHONDONTWRITEBYTECODE`, `PYTHONNOUSERSITE`, and
`PYTHONUTF8` are `"1"`; `PYTHONHASHSEED` is the fixed canonical integer string
`"0"`, never `"random"`; `PYTHONMALLOC` is `"malloc"`; and `TZ` is `"UTC"`.
No empty state, alternate allocator, feature override, locale, hash seed, or
glibc tunable is admitted in V1. The supervisor constructs this environment
from empty and the harness compares it with the typed projection and
`launch_environment.behavior_sha256`; it does not compare an inherited raw
environment with a projection derived from those same bytes.

`arithmetic_trace.policy_id` is `authoring-arithmetic-trace-v1`. Every
authoring-path use of `radians`, `degrees`, `sin`, `cos`, `atan2`, `sqrt`,
`hypot`, `dist`, `exp`, floating power, `fsum`, `nextafter`, and NumPy `cbrt`
routes through the trace adapter.
Each successful call appends a record having exactly `operation`, `inputs`, and
`outputs`. The operation is one of `math-radians`, `math-degrees`, `math-sin`,
`math-cos`, `math-atan2`, `math-sqrt`, `math-hypot`, `math-dist`, `math-exp`,
`float-pow`, `math-fsum`, `math-nextafter-positive`,
`math-nextafter-negative`, or `numpy-cbrt`; inputs and outputs are arrays of exact
finite canonical binary64 `float.hex()` strings, preserving signed zero.
Inputs are nested once by positional argument, with a scalar represented by a
singleton inner array; outputs are one array flattened in C order. Arity,
inner-array shape, and output shape are fixed per operation adapter. Boolean,
non-string, noncanonical/non-finite hex, keyword argument, extra key, unknown
operation, or alternate vector/reduction shape fails strict parsing. Any
exception aborts the invocation and publishes neither a partial trace nor an
enclosing owner.

The shape and call grammar is this exact 14-row table. `1×1` means one outer
positional-argument array containing one scalar; `2×1` means two ordered scalar
argument arrays; `2×3` means two ordered three-component vectors. Every output
is one flat singleton. Except for `numpy-cbrt`, the adapter materializes exact
built-in Python `float` inputs before applying the row semantics; no caller-
supplied integer, Decimal, array scalar, subclass, generator, keyword, or
implicit broadcast reaches the adapter. The sole internal type conversion is
the integral-exponent branch stated for `float-pow`.

| Operation | Exact input shape | Exact output shape | Exact successful call semantics |
|---|---:|---:|---|
| `math-radians` | `1×1` | `1` | `math.radians(x)` |
| `math-degrees` | `1×1` | `1` | `math.degrees(x)` |
| `math-sin` | `1×1` | `1` | `math.sin(x)` |
| `math-cos` | `1×1` | `1` | `math.cos(x)` |
| `math-atan2` | `2×1` | `1` | `math.atan2(y,x)` from ordered inputs `[[y],[x]]` |
| `math-sqrt` | `1×1` | `1` | `math.sqrt(x)` |
| `math-hypot` | `2×1` | `1` | binary-only `math.hypot(x,y)`; the variadic API is not exposed |
| `math-dist` | `2×3` | `1` | `math.dist((x0,x1,x2),(y0,y1,y2))` in that component order |
| `math-exp` | `1×1` | `1` | `math.exp(x)` |
| `float-pow` | `2×1` | `1` | base/exponent are canonical binary64 floats; if `exponent.is_integer()` call `base ** int(exponent)`, otherwise call `base ** exponent`; caller type never selects the branch |
| `math-fsum` | `1×n`, `1 <= n <= 4096` | `1` | materialize the one ordered tuple once and call `math.fsum(tuple_values)` |
| `math-nextafter-positive` | `1×1` | `1` | `math.nextafter(x, math.inf)` inside the direction-fixed adapter |
| `math-nextafter-negative` | `1×1` | `1` | `math.nextafter(x, -math.inf)` inside the direction-fixed adapter |
| `numpy-cbrt` | `1×1` | `1` | construct exactly one scalar `numpy.float64(x)`, call `numpy.cbrt` once, require a scalar `numpy.float64`, and immediately extract one Python float |

For `math-fsum`, the shape parser admits the closed `1..4096` union, while
semantic replay also enforces the algorithm-local length: dense-LUT prefix
`j` uses exactly `j` values for `j=1..4096`; OKLab squared distance uses three;
the 256-position arc prefix `i` uses exactly `i` for `i=1..255`; and the gap
mean/deviation calls for selected size `n=2..8` each use exactly `n-1` values.
No empty reduction is executed or recorded. These contextual checks use the
specified call order and recomputed operands, not a private callsite field.
For `float-pow`, converting an integral binary64 exponent to `int` is part of
the adapter semantics and preserves the displayed integer-square/cube path;
nonintegral policy exponents remain Python-float power. `math.pow`, a caller-
type-dependent choice, or a second power operation ID is invalid.

`math-degrees` and `math-exp` each have exactly one singleton finite input and
one singleton finite output. The two `math-nextafter-*` operations also have
exactly one singleton finite input and one singleton finite output; their
operation name records and fixes the implementation direction to respectively
positive or negative infinity. Infinity is therefore neither an operand nor a
valid serialized value. The adapter calls `math.nextafter(x, math.inf)` or
`math.nextafter(x, -math.inf)` only after selecting the closed operation and
fails if the returned value is non-finite. A generic two-operand
`math-nextafter`, caller-chosen direction, or infinity-shaped hex string is
invalid.

The accepted-base-runtime conformance suite must reproduce these exact adapter
goldens. They test the closed adapter semantics and are not silently injected
into an invocation's call-order trace:

| Operation | Exact `inputs` | Exact `outputs` |
|---|---|---|
| `math-degrees` | `[["0x1.921fb54442d18p+1"]]` | `["0x1.6800000000000p+7"]` |
| `math-exp` | `[["0x0.0p+0"]]` | `["0x1.0000000000000p+0"]` |
| `math-nextafter-positive` | `[["0x0.0p+0"]]` | `["0x0.0000000000001p-1022"]` |
| `math-nextafter-negative` | `[["0x0.0p+0"]]` | `["-0x0.0000000000001p-1022"]` |

Positive nextafter of `0x1.fffffffffffffp+1023` and negative nextafter of
`-0x1.fffffffffffffp+1023` are mandatory rejection vectors because their
observed outputs are non-finite; neither appends a record or owner.

`records` is this complete call-order array inline in every authoritative
environment owner; it is not a detached hash or reconstructible-only runtime
buffer. `record_count` is a non-Boolean integer equal to `len(records)` and
`records_sha256` is SHA-256 of
`b"dartwork-mpl-authoring-arithmetic-trace-v1\0"` plus the complete record
array. The empty trace is the explicit `records=[]` and hashes canonical `[]`;
it is allowed only for the exact five-member set
`{legacy-baseline-extractor-a, legacy-baseline-extractor-b,
legacy-baseline-cross-extraction, policy-preselection,
characterization-verification}`; all other six profiles require a nonempty
trace. Untyped
floating `**` or untraced vectorized transcendental calls are forbidden.

Trace operands may derive only from public scientific/policy bytes, closed
literals, or prior traced outputs. Records may contain no repr, keyword name,
callsite/module/stack, timestamp, thread/process ID, pathname, environment,
loader/provider/transcript/error text, or any encoding or digest derived from
private transport. The complete inline array and digest pass the publication
canary scan. An offline verifier locates the inline array through the exact
environment-owner table, strict-parses every record, recomputes count/digest,
the complete `environment_sha256`, and every enclosing owner hash. That proves
the retained public preimage and hash chain; it does not falsely recreate the
destroyed private ptrace/VM history or prove historical call occurrence from a
digest alone.

For base identity, `base_python` is the complete `python` record with only
`stdlib_closure_records`, `stdlib_closure_count`, and
`stdlib_closure_sha256` omitted; the complete inline `base_stdlib_*` fields
remain.
`base_numpy` is the complete `numpy` record with only the invocation-derived
`distribution_records` and `used_distribution_sha256` omitted. Its version,
selected-wheel content identity, multiarray binary, build-capability record,
and admitted CPU feature set remain bound. NumPy used-file records stay in the
complete invocation `numpy` record and its unique `runtime_distributions` row;
they are runtime identity, not a false common-base invariant.
`native_execution_policy` is exactly the eight-field projection
`{policy_id,seal_policy_id,vm_policy_id,process_split_policy_id,python_startup,
terminal_handoff_policy_id,supervisor,launch_environment}`. This makes the
closed pre-broker startup, continuously enforced Linux writer/VM policy,
two-lifetime split, complete terminal output-set handoff, and verified
supervisor/receipt capability part
of the common base identity, rather than invocation-local claims inferred from
final mappings or surviving output paths.
Define:

```text
base_broker_read_prefix = {
    "schema": "oklab-authoring-base-broker-read-prefix-v1",
    "records": dependency_discovery.broker_read_records[
        :dependency_discovery.base_broker_read_record_count],
    "record_count": dependency_discovery.base_broker_read_record_count,
    "records_sha256": dependency_discovery.base_broker_read_records_sha256,
}
```

The named prefix preimage is the initial slice of the complete inline broker-
read array above; its count/digest must recompute from `records`. A hash-shaped
field alone is not base authority.

`base_module_closure`, `base_dependency_closure`, and `base_mapping_closure`
each have exactly `schema`, `records`, `record_count`, and `records_sha256`.
Their schemas are respectively `oklab-authoring-base-module-closure-v1`,
`oklab-authoring-base-dependency-closure-v1`, and
`oklab-authoring-base-mapping-closure-v1`; their other values are the exact
corresponding inline fields declared above. Counts/digests must recompute under
their stated domains.

```text
base_runtime_environment_sha256 = SHA256(
    b"dartwork-mpl-oklab-base-runtime-environment-v1\0" +
    canonical_json({
        "schema": "oklab-authoring-base-runtime-v1",
        "python": base_python,
        "numpy": base_numpy,
        "platform": platform,
        "floating_point": floating_point,
        "control_base_handoff":
            native_execution.control_preparation.base_handoff,
        "base_broker_read_prefix": base_broker_read_prefix,
        "native_execution_policy": native_execution_policy,
        "base_module_closure": base_module_closure,
        "base_dependency_closure": base_dependency_closure,
        "base_mapping_closure": base_mapping_closure,
    })
)

runtime_environment_sha256 = SHA256(
    b"dartwork-mpl-oklab-invocation-runtime-environment-v3\0" +
    canonical_json({
        "schema": schema,
        "invocation_kind": invocation_kind,
        "selected_artifact_lock_projection_sha256":
            selected_artifact_lock_projection_sha256,
        "python": python,
        "numpy": numpy,
        "platform": platform,
        "native_execution": native_execution,
        "dependency_discovery": dependency_discovery,
        "runtime_distributions": runtime_distributions,
        "runtime_dependencies": runtime_dependencies,
        "floating_point": floating_point,
        "base_runtime_environment_sha256":
            base_runtime_environment_sha256,
    })
)
```

`environment_sha256` uses
`b"dartwork-mpl-oklab-invocation-environment-v3\0"` plus the complete
environment with only `environment_sha256` omitted. Different invocation kinds
are required to have equal `base_runtime_environment_sha256`, not equal loaded
closures or traces. Full `runtime_environment_sha256` equality is required only
when replaying the same invocation kind. Proposal/comparison and
characterization-generation/verification therefore must not copy one another's
full runtime hash or arithmetic trace. Once frozen, stored bytes—not labels or
a cross-platform recomputation—remain runtime authority.

The common base hash binds the complete typed base handoff—including the closed
control/split/receipt policies, preparer startup/runtime/stdlib/native closure,
platform, and public runtime-import manifest—but not the invocation handoff,
raw request, private index/ledger, or complete control-preparation record. Their
invocation-specific public consequences remain bound by the full runtime hash.
The common base hash intentionally omits the invocation-specific selected-
artifact projection, NumPy used-file fields, and post-base loaded mappings:
`base_numpy` still binds NumPy's selected wheel and arithmetic/build identity,
while the inline base broker prefix binds every NumPy/base read and the
complete invocation NumPy record and runtime row bind its actual used files.
The complete base-ready stdlib/module/dependency/mapping arrays replace the old
core-only projection. The runtime hash binds the complete native execution and the
selected-artifact projection reconstructed from
the full used closure. Thus two stages may share a base hash while legitimately
using different non-base distributions and therefore different runtime and
environment hashes.

Canonical JSON is UTF-8 from `json.dumps` with `ensure_ascii=False`,
`allow_nan=False`, `sort_keys=True`, and `separators=(",", ":")`. Hash inputs
exclude a terminal newline; files contain exactly one. Subordinate hashes are
plain SHA-256 of their canonical values. `payload_sha256` is:

```text
SHA256(
    b"dartwork-mpl-oklab-authoring-payload-v1\0" +
    canonical_json({"family": family, "payload": payload})
)
```

This binds a payload to its family. Define `proposal_envelope_sha256` as SHA-256
of `b"dartwork-mpl-oklab-authoring-proposal-v1\0"` followed by the complete
canonical proposal envelope. The frozen `accepted_proposal_sha256` must equal
that recomputed value. `frozen_envelope_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-frozen-v1\0"` followed by the complete
canonical frozen envelope with only `frozen_envelope_sha256` omitted. It binds
the acceptance evidence as well as the unchanged payload.

Proposal creation first verifies the prior policy registry/preselection seal,
captured source snapshot, and role-complete external-input bundle, then validates every input, compiles the LUT,
selects all eight rows from the one recorded candidate domain, runs the
independent oracle/reference suite/admission, verifies every linkage and digest,
and atomically writes one complete envelope. It never publishes a partial
success. Promotion strictly reparses the proposal and all prior approval
artifacts from its immutable external-input bundle, verifies every
hash/source-snapshot/execution-input/runtime record, regenerates the LUT with
exact hex equality, re-derives the candidate domain and requires exact
count/record/hash equality, reruns selection with exact indices and objective
equality, recomputes validation/admission and its suite evidence, reproduces
proposal and comparison invocation traces separately on the common base
runtime, verifies the two sequential review artifacts and visual comparison
approval, then create-only copies the unchanged payload into a frozen envelope.

Frozen build/runtime loading validates the exact schema, lifecycle, hashes,
family/filename binding, candidate/LUT/index/hex linkage, and complete ordered
rows, then replays stored bytes only. It validates the stored domain but does
not decode OKLab or rerun filtering. It never reads the proposal path or invokes
generation, rendering, selection, validation, or admission as a fallback.
Missing or malformed frozen data is fatal.

### 3.6 Comparison and reviewer envelopes for promotion

Promotion has exactly one non-source input set: the `promotion-replay`
external-input bundle defined by section 10's normative role-table row. No
other paragraph defines or narrows that set. Promotion reads only blobs
captured in that bundle and project source files declared by its execution
snapshot; canonical producer paths are resolved through the role table rather
than treated as a shorter alternate input list.

The comparison report is a closed envelope with exactly:

```text
schema, family, proposal_envelope_sha256,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot_sha256,
execution_inputs, invocation_recipe,
proposal_base_runtime_environment_sha256,
proposal_runtime_environment_sha256, comparison_environment,
source_files, artifacts, summary, comparison_report_payload_sha256
```

`schema` is `oklab-authoring-comparison-report-v1`. The family and proposal
hash bind the canonical path above. All three fingerprints use section 10's
exact seven-field schema and must equal each other, the proposal provenance,
the captured source snapshot, and the current fingerprint.
`execution_snapshot_sha256` equals the proposal provenance. `execution_inputs`
names that source snapshot and an external bundle containing exactly the
proposal at its canonical producer path; comparison imports/reads the captured
proposal blob and never the live ignored path. The proposal base/full runtime
hashes equal the corresponding fields in `proposal.provenance.environment`.
`invocation_recipe` is the closed path-neutral comparison profile and raw
command/cwd/environment transport is private.
`comparison_environment` is a complete environment-v3 record with
`invocation_kind="comparison"`; its base-runtime hash must equal the proposal
base hash. Its invocation-specific loaded closure, full runtime hash,
computation broker-read stream, arithmetic trace, and full environment hash
are reproduced independently and
are expected to differ when actual imports or operations differ. Copying the
proposal environment or trace is invalid.
`source_files` must equal the proposal's ordered records and every project-local
comparison import/read must resolve to those captured source-snapshot bytes or
the declared proposal input blob.

`artifacts` is a relative-path-sorted array of records having exactly `path`,
`media_type`, `byte_count`, and `sha256`; it includes every ordinary regular
comparison output except `report.json`, excluding the separately governed
`input-bundles/`, `review-controls/`, and `review-evidence/` stores. It rejects
symlinks and has unique paths. `summary`
has exactly:

```text
coordinate_axis_kind, renderer_policy_id, generation_policy_id,
lut_sha256, candidate_domain_sha256, selection_rows_sha256,
validation_rows_sha256, rendered_sample_count, oracle_algorithm_ids,
oracle_results_artifact, oracle_results_sha256,
shipped_exact_surfaces_artifact, shipped_exact_surfaces_sha256,
fixed_y_topology_evidence, side_by_side_manifest_artifact,
side_by_side_manifest_sha256, side_by_side,
all_machine_checks_passed, visual_artifacts
```

The first kind is exactly `direct-oklch-v1` or `fixed-relative-y-v1`; the
renderer ID must be the corresponding V1 ID. All four payload digests equal the
proposal values.

The oracle result artifact has exactly:

```text
schema, family, proposal_envelope_sha256, execution_snapshot_sha256,
scalar_kernel_constants, sample_plan_id, sample_count, samples,
result_count, results,
oracle_algorithm_ids, all_machine_checks_passed, oracle_results_sha256
```

Its schema is `oklab-authoring-oracle-results-v1` and sample-plan ID is
`final-lut-256-v1`. `scalar_kernel_constants` is exactly the one complete
section 5.1 two-key binding and occurs nowhere else in this artifact; every
endpoint/projective/Cartesian/direct algorithm reference resolves to its
golden digest through section 5.6's closed registry. Direct-face results
continue to
bind their complete reconstructed coefficient records rather than duplicating
this field per result. `samples` has exactly 256 entries in ascending LUT-index
order. Each has exactly `sample_index`, `lut_hex`, `production_result_kind`,
and `production_result_sha256`; indices are exact `0..255`, hex equals the
proposal LUT, kind is one of `direct-interior`, `direct-endpoint`,
`fixed-y-interior`, or `fixed-y-endpoint`, and the result hash is reproduced by
replaying the typed renderer for that exact final resampled coordinate. Thus
`sample_count` and summary `rendered_sample_count` are both derived as 256, not
author-supplied coverage claims.

Each `results` entry has exactly `sample_index`, `result_kind`, `query_role`, and
`payload`. `result_kind` is `direct-face-oracle`,
`projective-proof-verification`, `cartesian-oracle`, or
`endpoint-policy-verification`; `query_role` is the exact
`CartesianOracleQuery.role` only for a Cartesian entry and otherwise null;
`payload` is the matching complete closed section 5.6 record. Required coverage
for each sample is mechanically derived from `production_result_kind`:

| Production kind | Required entries, exactly once |
|---|---|
| `direct-interior` | one `DirectFaceOracleResult` |
| `direct-endpoint` | one `EndpointPolicyVerification` |
| `fixed-y-interior` | one `ProjectiveProofVerification` plus every conditional/non-conditional Cartesian query required by section 5.6 |
| `fixed-y-endpoint` | one `EndpointPolicyVerification` |

No extra result is allowed. Entries are ordered by `(sample_index,
result_kind_rank, query_role_rank)`, where direct-face, projective-proof,
Cartesian, and endpoint have ranks 0, 1, 2, and 3, and Cartesian query rank uses
section 5.6's query table order. Every payload's
`production_result_sha256` must equal its sample. `result_count` is the exact
array length. `oracle_algorithm_ids` is the UTF-8-byte-sorted unique set of IDs
derived from this required complete array, not merely the IDs an artifact chose
to include.

`all_machine_checks_passed` is recomputed as the conjunction of exact
sample/result coverage and order; schema/hash/source linkage; every PASS
verdict; every expected/observed Cartesian or direct query equality; complete
direct component coverage, projected source-identity equality, complete
algebraic-root equivalence proofs, recomputed direct PASS verdict, directed
bound conversion, and exact rational production-contains-oracle chain; and
projective proof/bound agreement; every independently reconstructed certified
coordinate, independently derived neutral-reference `L`, direction-scaled
`a,b`, raw/encoded/neutral channel, modeled-Y and applicable residual bit
comparison; all scalar-kernel association IDs; and the same-base-runtime
replay-scope equality. It
must be true both in this artifact and the summary. `oracle_results_sha256` is
SHA-256 of `b"dartwork-mpl-oklab-authoring-oracle-results-v1\0"` plus canonical
JSON of the complete artifact with only that field omitted.

`oracle_results_artifact` has exactly `path`, `schema`, `result_count`, and
`sha256`. The path is a unique relative JSON path in `artifacts`, schema/count
equal the parsed container, and SHA-256 equals the raw file's artifact-map hash.
Parsing canonical bytes and recomputing the container self-hash must reproduce
summary `oracle_results_sha256`.

`shipped_exact_surfaces_artifact` has exactly `path`, `schema`,
`surface_count`, and `sha256`. It names one artifact with this closed schema:

```text
schema, baseline, surface_order, surfaces, inventory,
mismatch_surface_count, mismatch_surfaces,
all_exact_surfaces_preserved, evidence_sha256
```

The schema is `dartwork-mpl-shipped-exact-surfaces-v1`. `baseline` has exactly
`path`, `raw_sha256`, `schema`, `compatibility_payload_sha256`,
`baseline_commit`, `baseline_git_tree_oid`, `baseline_tree_sha256`,
`baseline_authority_commit`,
`acceptance_path`, `acceptance_raw_sha256`, `acceptance_sha256`,
`authority_marker_path`, `authority_marker_raw_sha256`, and
`authority_marker_sha256`, and names the immutable accepted V5 compatibility
asset, its sibling preinstall acceptance, and the fixed-path baseline authority
marker. Strict parsing of the acceptance must resolve the archived successful
preinstall A/B closure; strict parsing of the marker must resolve the complete
promotion A/B closure, post-promotion approval, finalization provenance, and
every cross-link. An asset or pair hash alone is insufficient.
`baseline_authority_commit` is immutable commit `A`,
not necessarily current commit `H =
execution_snapshot.source_fingerprint.head_sha`; `H` must equal the Git
capsule's `head_commit_oid`. The verifier resolves both only from the capsule's
closed objects, validates the matching `authority_closure`, and parses every
adjacent raw commit in its captured `H -> ... -> A` path to prove the next OID
is literally the current commit's **first** `parent` header. A merge commit's
second or later parent never qualifies. Migration requires `A == H`; every
later comparison requires first-parent-ancestor-or-self. For the closed set
`P` consisting of the compatibility, acceptance, and authority-marker paths
plus every regular leaf transitively reached through the strict acceptance or
marker, it independently
derives `S_C(p)=(git_mode,full_blob_oid,sha256(raw_blob_bytes))` from each
commit tree, requires the acceptance-and-marker-prescribed `S_A(p)`, and requires
`S_H(p)==S_A(p)` for every path. It separately requires the captured index and
worktree states to equal `H[p]` at every `p in P`. Unrelated paths may change.
A missing chain/tree object, unrelated history containing copied bytes,
non-first-parent-only reachability, worktree/index overlay, branch/ref/replace
lookup, or any mismatch fails.
`surface_order` is exactly:

```text
palette, cycles, cmaps_256, curated_rows, diverging_canonicals,
semantic_coordinates, semantic_colors, dark_cycle_coordinates, dark_cycle,
taxonomy, registrations, typing_literals, mcp_discovery, public_inventory,
discrete_hex, reverse_discrete_hex, multi_hue_discrete_indices, vendor_colors
```

Each comparison `surfaces` row has exactly `surface_id`, `baseline_sha256`,
`candidate_sha256`, and `equal`, occurs once in that order, and is derived by
strictly parsing the baseline and independently regenerating the corresponding
current surface. Every surface ID maps to the identically named member of the
baseline asset's closed top-level `surfaces` object; legacy draft spellings such
as `cmaps256` are rejected.
`inventory` has exactly `baseline` and `candidate`; each value has exactly
`cmap_positions`, `cycle_positions`, `dc_tokens`, `families`,
`palette_positions`, `qualitative_families`, `registered_colormaps`, and
`vendor_tokens`. Baseline values are strictly parsed from the accepted asset,
candidate values are independently derived, and the two complete records must
be equal. Publishable evidence requires exactly 18 rows,
`mismatch_surface_count=0`, `mismatch_surfaces=[]`, and
`all_exact_surfaces_preserved=true`. The self-hash is SHA-256 of
`b"dartwork-mpl-shipped-exact-surfaces-v1\0"` plus canonical JSON with only
`evidence_sha256` omitted. The summary's artifact schema/count/raw hash and
`shipped_exact_surfaces_sha256` must reproduce the parsed object and its
self-hash. Promotion reruns this comparator from the captured baseline and
source snapshot; it does not trust the Boolean or copy current rows from the
report.

For `coordinate_axis_kind="fixed-relative-y-v1"`,
`fixed_y_topology_evidence` is a non-null closed record with exactly:

```text
topology_contract_sha256, sample_plan_id, dense_target_bits_sha256,
final_target_bits_sha256, maximum_abs_y_residual,
direct_counterfactual_artifact, fixed_y_topology_evidence_sha256
```

The topology hash covers the complete recipe contract; `sample_plan_id` is
`dense-4097-and-final-256-v1`. The two target hashes cover, in generation
order, every exact binary64 target-Y bit pattern requested by the dense and
final renderers. Every renderer request must receive the bit-identical axis
value, every witness must satisfy the simultaneous absolute and relative
modeled-Y residual rules, and `maximum_abs_y_residual` is recomputed from all
such witnesses. `direct_counterfactual_artifact` is one exact
`path,media_type,byte_count,sha256` artifact reference. It is diagnostic only:
no minimum direct-versus-fixed deviation and no perceptual threshold may be
inferred from it. Its self-hash uses
`b"dartwork-mpl-fixed-y-topology-evidence-v1\0"` plus the complete record with
only `fixed_y_topology_evidence_sha256` omitted. A direct-OKLCH comparison has
this field exactly null. For fixed-Y, the counterfactual reference must equal
the `direct_oklch_vs_fixed_y_preview` side-by-side role byte-for-byte.

The topology-contract hash is SHA-256 of
`b"dartwork-mpl-fixed-y-topology-contract-v1\0"` plus canonical JSON of the
complete `FixedYTopologyContract`. For each stream, the target-bit preimage is
the complete ordered array of records having exactly `sample_index` and
`target_y_float_hex`; indices are `0..4096` or `0..255` and the hex string is
the exact request value. Hash with
`b"dartwork-mpl-fixed-y-target-bits-v1\0"`, the ASCII stream role `dense` or
`final`, one NUL, and canonical JSON of that array. The maximum residual uses
the standard `{number,float_hex}` binary64 record and is the exact maximum of
`abs(witness.relative_y_residual)` in dense-then-final stream order.

`side_by_side` is a closed object with exactly `schema`, `roles`, and
`side_by_side_manifest_sha256`. Its schema is
`dartwork-mpl-authoring-side-by-side-v1`; `roles` has exactly these four keys,
in this order:

```text
shipped_18_surface_overview
compatibility_probe_vs_fixed_y_boundary
direct_oklch_vs_fixed_y_preview
discrete_selection_and_validation
```

Each role value is exactly `path,media_type,byte_count,sha256`, resolves to one
identical record in `artifacts`, and has an image or HTML media type. The
manifest self-hash is SHA-256 of
`b"dartwork-mpl-authoring-side-by-side-v1\0"` plus canonical JSON with only
`side_by_side_manifest_sha256` omitted. `side_by_side_manifest_artifact` has
exactly `path`, `schema`, and `sha256`, names the canonical JSON artifact for
that complete object, and cross-matches its raw artifact hash; the summary hash
equals the parsed semantic self-hash. The `visual_artifacts` array is derived
as the UTF-8-path-sorted unique paths from those four role references; it is
not an independently extensible list. Together
these roles distinguish byte preservation, compatibility diagnostics,
coordinate-policy previews, and post-selection validation without implying
that any diagnostic retunes shipped output.

`comparison_report_payload_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-comparison-report-v1\0"` plus canonical JSON of
the complete report with only that field omitted. It is written atomically and
last under section 10's start/end/post-write guards. Reviewer reports use the
same canonical JSON and duplicate-key rejection rules as proposals.

Reviewer A has exactly these keys:

```text
schema, family, role, reviewer_instance_id, verdict,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot_sha256,
execution_inputs, review_execution, proposal_envelope_sha256,
terminal_result_ordinal, terminal_result_sha256,
comparison_report_payload_sha256, findings, reviewer_a_report_sha256
```

Its constants are `schema="oklab-authoring-reviewer-a-report-v1"` and
`role="reviewer-a"`. Reviewer B has exactly:

```text
schema, family, role, reviewer_instance_id, verdict,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot_sha256,
execution_inputs, review_execution, proposal_envelope_sha256,
terminal_result_ordinal, terminal_result_sha256,
comparison_report_payload_sha256, findings,
predecessor_reviewer_a_report_sha256, reviewer_b_report_sha256
```

Its constants are `schema="oklab-authoring-reviewer-b-report-v1"` and
`role="reviewer-b"`. All three fingerprint fields use section 10's exact schema
and must equal one another, the comparison/proposal fingerprint, the source
snapshot, and the current state. Each complete `execution_inputs` record
uses section 10's role table; A captures proposal/comparison/artifacts and B
captures the same subject plus A's report, historical input manifest/blobs,
control manifest/blobs, evidence manifest/blobs, and completion token.
The report is first written with the expected
post-write value equal to the verified end value; immediately after atomic
publication the harness captures the real guard and removes the report unless
it equals the stored value. Because review output is ignored and excluded from
the snapshot, this adds no source-fingerprint cycle.

Every content-addressed input, review-control, or review-evidence bundle uses
one universal storage layout. Its directory contains exactly the regular file
`manifest.json` and one regular `blobs/<raw_sha256>` file for every distinct raw
hash referenced by that manifest; multiple records may share one blob. No
other file, directory, symlink, or alternate manifest name is allowed. The
canonical logical paths are:

```text
input-bundles/<external_input_bundle_sha256>/manifest.json
review-controls/<review_control_bundle_sha256>/manifest.json
review-evidence/<review_evidence_bundle_sha256>/manifest.json
```

For an ignored live producer bundle, publication physically seals directories
to `0555` and manifest/blob files to `0444` before consumer launch; a platform
that cannot enforce and recheck those permissions fails that invocation. Every
external-input, review-control, and review-evidence producer invokes section
3.5's `publish_live_bundle_0444_0555` whole-tree transaction; none may publish
or chmod leaves directly. Its atomic install, idempotent-resynchronization, and
ABSENT-or-complete crash state therefore apply to all three bundle kinds. Those
permission bits are operational hardening, not hash input. A tracked policy,
fixed-Y, or frozen-family archive instead requires every leaf to be a regular
stage-0 Git blob with mode `100644`; Git has no directory mode and checkout
write bits/ACLs/ownership/timestamps are ignored. A consumer that needs an
executable read-only store materializes tracked bytes into a private ignored
tree and applies the live `0555`/`0444` seal there.

Producer and tracked-archive prefixes may differ, but the subtree from
`input-bundles`, `review-controls`, or `review-evidence` downward has identical
relative regular-file paths and bytes; physical metadata is deliberately not
part of that equality. A field ending `_bundle_path` or `_manifest_path` always
names the literal `manifest.json`, never its directory.

Every review has an immutable pre-run control bundle separate from its subject
input and post-run public review log. A `ReviewControlBundle` manifest has exactly
`schema`, `review_attempt_id`, `reviewer_instance_id`, `role`,
`subject_input_bundle_sha256`, `records`, and
`review_control_bundle_sha256`; schema is
`oklab-authoring-review-control-bundle-v1` and role is `reviewer-a` or
`reviewer-b`. Both IDs are generated by the local harness, never copied from a
provider: they match respectively `review-attempt-[0-9a-f]{32}` and
`review-instance-[0-9a-f]{32}`. Each record has exactly `role`, `path`, `media_type`,
`byte_count`, `raw_sha256`, and `blob_path`. A's records occur exactly once
and in order `harness-source`, `prompt`, `scope`; B adds
`predecessor-completion-token` after `scope`. Blob path is exactly
`blobs/<raw_sha256>`; path is canonical bundle-relative POSIX; every blob is a
regular file with matching byte count and raw hash. The completion-token blob is
exactly 64 lowercase ASCII hex bytes with no newline. The bundle self-hash uses
`b"dartwork-mpl-oklab-authoring-review-control-bundle-v1\0"` plus the complete
manifest with only its self-hash omitted.

Role paths/media types are exact:
`harness-source -> (harness-source.txt,text/plain; charset=utf-8)`,
`prompt -> (prompt.txt,text/plain; charset=utf-8)`,
`scope -> (scope.json,application/json)`,
`predecessor-completion-token ->
(predecessor-completion-token.txt,text/plain; charset=us-ascii)`, and
`public-review-log -> (public-review-log.json,application/json)`. The harness-source and
prompt bytes must be valid UTF-8; no media-type parameter or alternate spelling
is accepted.

The harness captures and publishes this bundle create-only at
`review-controls/<review_control_bundle_sha256>/manifest.json` before the reviewer process
starts, using `publish_live_bundle_0444_0555`; the reviewer is not launched
until the complete sealed-tree install and final-parent synchronization pass.
It rehashes the bundle before and after execution. The
subject bundle is separately captured first; the control manifest's
`subject_input_bundle_sha256` equals that external-input manifest hash. Thus
scope can refer to subject bytes without referring to—and cycling through—the
control bundle that contains scope. `ExecutionInputs` binds both hashes.

The prompt is exact non-empty UTF-8 bytes and harness source is its complete
public, path-neutral source file. Both address inputs only by logical bundle
role, repo-relative path, and content hash and must pass the publication
firewall; any privately rendered provider prompt or transport wrapper is not
this stored control artifact. The scope blob is canonical JSON with exactly `schema`,
`review_kind`, `subject`, `source_fingerprint`,
`execution_snapshot_sha256`, `subject_input_bundle_sha256`, `files`, and
`rubric`. Schema is `oklab-authoring-review-scope-v1`; review kind is one of
`authoring-proposal`, `policy-approval`, `semantic-batch`,
`fixed-y-characterization-preinstall`, or
`fixed-y-characterization-postinstall`, or
`validation-oracle-truth-bootstrap`. The authoring subject has exactly
`family`, `proposal_envelope_sha256`, and
`comparison_report_payload_sha256`; policy subject has exactly `approval_id`,
`family`, `policy_kind`, `policy_id`, `policy_record_sha256`, and
`characterization_payload_sha256`, `verification_evidence_raw_sha256`, and
`verification_evidence_sha256`; every generic subject has exactly
`subject_id` and `subject_manifest_sha256`.
`subject_input_bundle_sha256` equals the report's external-input bundle. Files
are UTF-8-path-sorted exact `path`/`raw_sha256` records covering every subject
file. `rubric` has exactly `rubric_id`, `severity_levels`, `pass_rule`, and
`required_checks`; severity levels are exactly `P0,P1,P2`, pass rule is
`zero-p0-p1-p2-findings`, and required checks are a non-empty ordered unique
array of non-empty strings.

The scope may bind only the already-created subject external-input hash. It
must not contain its own control-bundle hash, any evidence-bundle hash,
`ExecutionInputs.execution_inputs_sha256`, a reviewer-report hash,
`review_sequence_sha256`, a walkthrough hash, or an acceptance hash. This
closed exclusion keeps the pre-run control dependency graph acyclic.

After execution, every report is accompanied by a create-only post-run
`ReviewEvidenceBundle`. Its manifest has exactly `schema`,
`review_attempt_id`, `reviewer_instance_id`,
`review_control_bundle_sha256`, `records`, and
`review_evidence_bundle_sha256`, with schema
`oklab-authoring-review-evidence-bundle-v1`. Records use the same six-key blob
schema. Attempt/instance equal the parsed control and report. They reproduce
every control record byte-for-byte in the same order,
followed by exactly one `public-review-log` record. No alternate harness, prompt,
scope, or token bytes are allowed. Its self-hash uses
`b"dartwork-mpl-oklab-authoring-review-evidence-bundle-v1\0"` plus the complete
manifest with only its self-hash omitted. Publish it at
`review-evidence/<review_evidence_bundle_sha256>/manifest.json` through the same
`publish_live_bundle_0444_0555` transaction, including its ABSENT-or-complete
crash state, existing-tree resynchronization, no-replacement, read-only, and
pre/post rehash rules.

The stored log is a public structured projection, not a provider transcript.
It is canonical JSON with exactly `schema`, `review_attempt_id`,
`reviewer_instance_id`, `events`, `terminal_result_ordinal`,
`terminal_result_sha256`, and `public_review_log_sha256`, with schema
`oklab-authoring-public-review-log-v1`. Attempt/instance equal the control,
evidence, report, and `ReviewExecution` records. Events are non-empty and
ordinal ordered exactly `0..N-1`; each has exactly `ordinal`, `event_kind`,
`payload`, and `event_sha256`. Its hash is SHA-256 of
`b"dartwork-mpl-oklab-authoring-public-review-event-v1\0"` plus canonical JSON
of `ordinal`, `event_kind`, and `payload`.

The only event kinds are `control-accepted`, `subject-inspected`,
`finding-recorded`, and `terminal-result`. Their payloads have respectively
exactly `review_control_bundle_sha256`; `subject_role,raw_sha256`;
`finding_ordinal,finding_sha256`; or the complete terminal object below.
Subject roles come from the scope's closed file list. A finding hash covers the
canonical complete public finding also present at that ordinal in the terminal
result. No event accepts free-form conversation, provider metadata, tool
request/response, absolute path, or raw output.
Event 0 is the one control acceptance. It is followed by exactly one
`subject-inspected` event for every scope file in scope order, then exactly one
`finding-recorded` event per terminal finding in finding order, then the
terminal event. Thus a PASS log still enumerates every reviewed subject byte;
no extra, omitted, duplicated, or reordered event is valid.

Exactly one event has kind `terminal-result`; it is event `N-1`, and its
payload has exactly:

```text
schema, review_attempt_id, reviewer_instance_id, role,
review_control_bundle_sha256, verdict, findings, terminal_result_sha256
```

Attempt/instance equal the public log and `ReviewExecution`; instance/role
equal the report; and the control hash equals `ReviewExecution` and the parsed
control manifest. Verdict is `PASS` or `FAIL`; findings use the report's closed
public schema; PASS requires none and FAIL at least one. Its self-hash is
SHA-256 of
`b"dartwork-mpl-oklab-authoring-review-terminal-result-v1\0"` plus canonical
JSON with only `terminal_result_sha256` omitted. The containing event's
`event_sha256` follows the event formula over the complete terminal object.
Log `terminal_result_ordinal` is the non-Boolean integer `N-1`, and its terminal
hash equals the object self-hash. No other event may contain that schema.
`public_review_log_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-authoring-public-review-log-v1\0"` plus the complete log
with only that field omitted.

The public log is sealed before the harness constructs the evidence manifest
or outer report; the report API accepts no independent verdict/findings input
and derives its top-level verdict, findings, terminal ordinal, and terminal
hash only from the sealed terminal event. A terminal object may not contain a
log/evidence/report/completion-token/sequence/walkthrough/acceptance hash. The
evidence manifest and report may bind the earlier public log; the log cannot
bind either later object. A provider's raw conversation, tool trace, run ID,
session ID, and provider instance ID remain private, are not hashed or archived,
and are not an evidentiary dependency. The durable claim is limited to the
public subject/control/result sequence plus maintainer attestation.

`review_execution` is a closed `ReviewExecution` record with exactly:

```text
schema, harness_policy_id, review_attempt_id, reviewer_instance_id, role,
context_mode,
review_control_bundle_path, review_control_bundle_sha256,
review_evidence_bundle_path, review_evidence_bundle_sha256,
harness_source_sha256, prompt_sha256, scope_sha256,
public_review_log_raw_sha256,
terminal_result_ordinal, terminal_result_sha256,
predecessor_completion_token
```

Its schema is `oklab-authoring-review-execution-v1`; policy is
`sequential-independent-review-v1`; context mode is
`fresh-independent-agent-v1`; source/prompt/scope/public-log values are
the recomputed evidence-record raw hashes; the public log is also strictly
parsed and its internal `public_review_log_sha256` is recomputed. Attempt and reviewer-instance IDs
match the harness-generated public formats above, role is `reviewer-a` or `reviewer-b`, and
instance/role equal both the report and terminal result. Both paths are canonical content-addressed
paths and both hashes must reproduce their manifests and every blob. The
evidence manifest must name this control hash and reproduce its bytes. A report
without either complete bundle is invalid and cannot PASS. A's predecessor
token is null. B's token equals both its control-bundle token blob and the field.
The execution terminal ordinal/hash equal the sealed public-log pointers and
the report's top-level copies; they are never caller-supplied independently.
After A's final report, evidence-bundle verification, and successful post-write
guard, the harness issues:

```text
SHA256(
    b"dartwork-mpl-reviewer-a-completion-v1\0" +
    canonical_json({
        "reviewer_a_report_sha256": recomputed_A_hash,
        "review_attempt_id": A.review_execution.review_attempt_id,
        "source_fingerprint_post_write": A.source_fingerprint_post_write,
        "execution_snapshot_sha256": A.execution_snapshot_sha256,
        "execution_inputs_sha256": A.execution_inputs.execution_inputs_sha256,
        "review_control_bundle_sha256":
            A.review_execution.review_control_bundle_sha256,
        "review_evidence_bundle_sha256":
            A.review_execution.review_evidence_bundle_sha256,
    })
)
```

B's predecessor token must equal that value. The harness API refuses to create
B before issuing it, uses a new agent instance with fresh context, and
passes only B's frozen captured subject/control bundles, which include A's
completed envelope, historical execution-input manifest/blobs, control
manifest/blobs, evidence manifest/blobs, and completion token; A and B
review-attempt and reviewer-instance IDs must both differ. Private provider
run/session/instance values are neither compared nor published. A finding has exactly
`severity`, `summary`, and `anchors`; severity is `P0`, `P1`, or `P2`, summary is
non-empty public-safe UTF-8 with no private canary, and anchors is a non-empty array of exact repo-relative
`path`/positive-`line` records. `verdict` is `PASS` or `FAIL`. PASS requires an
empty findings array; FAIL requires at least one finding. Promotion accepts only
PASS.

The self-hashes are:

```text
reviewer_a_report_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-reviewer-a-report-v1\0" +
    canonical_json(A with only reviewer_a_report_sha256 omitted)
)

reviewer_b_report_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-reviewer-b-report-v1\0" +
    canonical_json(B with only reviewer_b_report_sha256 omitted)
)
```

Semantic-batch, fixed-Y, and validation-truth-bootstrap reviews use a closed
`ReviewSubjectManifest`. It has exactly `schema`, `review_kind`,
`subject_id`, `source_fingerprint`, `execution_snapshot_sha256`, `files`,
`evidence_requirement`, and `subject_manifest_sha256`; schema is
`oklab-authoring-review-subject-v1`, and review kind is `semantic-batch`,
`fixed-y-characterization-preinstall`, or
`fixed-y-characterization-postinstall`, or
`validation-oracle-truth-bootstrap`. Subject ID is a non-empty immutable
identifier. Each file has exactly `role`, `location`, `path`, `byte_count`,
and `raw_sha256`; location is `source-snapshot` or `external-input`. Records
are unique and sorted by UTF-8 `(role,location,path)`; every source record
reproduces the named snapshot byte and every external record reproduces the
subject bundle blob. Its self-hash uses
`b"dartwork-mpl-oklab-authoring-review-subject-v1\0"` plus the complete
manifest with only its self-hash omitted.

`evidence_requirement` is a closed tagged record. For the current two-document
spec/ADR batch it is exactly
`{"kind":"not-applicable","reason_id":"design-documents-only-v1"}`. For the
`legacy-v5-baseline-preinstall-v1` semantic batch it has exactly
`kind="legacy-v5-baseline-preinstall"`, `baseline_commit`,
`baseline_tree_sha256`, `compatibility_asset_raw_sha256`,
`extractor_a_evidence_sha256`, `extractor_b_evidence_sha256`, and
`cross_extraction_sha256`; all values must reproduce section 1.1 and the six
external preinstall outputs. For the
`legacy-v5-baseline-promotion-v1` semantic batch it has exactly
`kind="legacy-v5-baseline-promotion"`, `compatibility_asset_raw_sha256`,
`compatibility_payload_sha256`, `acceptance_sha256`,
`preinstall_subject_manifest_sha256`, `preinstall_review_sequence_sha256`,
`preinstall_snapshot_archive_sha256`, and `promotion_provenance_sha256`; each
value resolves through the complete external promotion bundle and proposed
source files. For every other implementation semantic batch
it has exactly `kind="required"`,
`shipped_exact_surfaces_sha256`, and `side_by_side_manifest_sha256`; those
hashes resolve respectively to a strict 18-surface artifact and a canonical
four-role side-by-side manifest included as external-input subject records.
`not-applicable` is forbidden once a batch changes source, tests, generated
assets, or runtime data; the two baseline variants are the only implementation
exceptions to `required`. For either fixed-Y review it has exactly
`kind="fixed-y-characterization"`, `review_kind`, and
`characterization_payload_sha256`; both values equal the enclosing subject and
strictly parsed payload. For validation truth bootstrap it has exactly `kind`,
`truth_id`, `truth_target_path`, `truth_raw_sha256`, and
`truth_payload_sha256`, with section 8's literal values and independently
recomputed hashes. Any other key, kind, path, or hash fails.

A semantic-batch manifest contains exactly all paths changed by that declared
batch. The changed paths are at `source-snapshot`. The baseline-preinstall batch
contains exactly section 1.1's six preinstall output roles at `external-input`
in addition to its changed paths, and no shipped or side-by-side evidence. The
baseline-promotion batch contains exactly section 1.1's
closed promotion bundle at `external-input` and every proposed tracked archive,
compatibility, and acceptance leaf at `source-snapshot`, again with no shipped
or side-by-side evidence. The later `promotion-review/` closure, post-promotion
approval, and `color_v5_baseline_authority.json` are forbidden from that
subject because they do not exist before B; the closed authority finalizer
creates only those mechanically derived bytes after B and is not represented as
a recursively reviewed semantic batch. Every
other implementation batch also contains exactly `shipped-exact-surfaces` and
`side-by-side-manifest` at `external-input`. The current spec/ADR batch contains
only the two declared
document paths
`docs/superpowers/specs/2026-07-27-oklab-authoring-extension-design.md` and
`docs/adr/0002-separate-shipped-color-compatibility-from-oklab-authoring.md`.
They form the complete normative design source set for this batch. Earlier
uncommitted drafts, prototype source, and prototype JSON are deliberately not
read, imported, or resolved. References to implementation and asset paths are
requirements for later ordered batches from section 1.1, not claims that those
paths exist or authority records consumed by this document review.
Its review root is not the live feature worktree: it is the
dedicated clean review capsule defined in section 10, reconstructed from the
exact content-addressed HEAD commit and overlaid with only those two source
bytes. At this pre-commit batch's frozen HEAD both document paths are absent,
so each must have exact `(H,I,W,R)=(ABSENT,ABSENT,R,R)`; every other path must
have `(H,I,W)=(H,H,H)` with `R` undefined. A fixed-Y preinstall manifest contains exactly
`candidate-payload`, `generation-evidence`, and
`generation-execution-input-manifest`, all at `external-input`, plus one
`generation-execution-input-blob/<raw_sha256>` external record for each
distinct blob declared by that manifest. The V1 generation bundle has zero
records, so its non-null manifest is mandatory and it contributes no blob role.

A fixed-Y postinstall manifest contains exactly `tracked-payload` at
`source-snapshot`; `regenerated-payload`, `reproduction-evidence`,
`generation-execution-input-manifest`, and
`verification-execution-input-manifest` at `external-input`; and one matching
`<phase>-execution-input-blob/<raw_sha256>` external record for every distinct
blob in each phase manifest. The verification bundle includes the sealed
generated payload. All phase manifests and blobs use the canonical ignored
`build/color-system-comparison/oklab-authoring-characterization/input-bundles/<hash>/`
producer subtree and are later installed under the fixed-Y tracked archive's
`input-bundles/<hash>/` subtree. Extra, missing, renamed, or location-mismatched
records fail.

A validation-truth-bootstrap manifest contains exactly `candidate-truth` at
`external-input` and `validation-oracle-source` plus
`validation-reference-vectors` at `source-snapshot`, using section 8's fixed
paths and hashes. Extra authoring, policy, proposal, selector, frozen-family,
or candidate-construction records fail.

Generic Reviewer A has exactly:

```text
schema, review_kind, subject_id, role, reviewer_instance_id, verdict,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot_sha256,
execution_inputs, review_execution, subject_manifest_sha256,
terminal_result_ordinal, terminal_result_sha256,
findings, reviewer_a_report_sha256
```

B has the same fields plus
`predecessor_reviewer_a_report_sha256` immediately before
`reviewer_b_report_sha256`. For a semantic batch the schemas are
`oklab-semantic-batch-reviewer-a-v1` and
`oklab-semantic-batch-reviewer-b-v1`; for either fixed-Y kind they are
`oklab-fixed-y-characterization-reviewer-a-v1` and
`oklab-fixed-y-characterization-reviewer-b-v1`; for truth bootstrap they are
`oklab-validation-oracle-truth-bootstrap-reviewer-a-v1` and
`oklab-validation-oracle-truth-bootstrap-reviewer-b-v1`. The domain tag is
`dartwork-mpl-` plus the exact schema plus one terminal NUL, and self-hashing
omits only the matching report-hash field. All fingerprint, input, control,
evidence, fresh-instance, sequential-token, finding, and restart rules above
apply unchanged. Schema, review kind, subject ID, and manifest hash must agree
with the scope and both reports.

B's predecessor hash must equal A's recomputed self-hash and its completion
token must match the formula above. The review harness refuses to create B until
a valid A PASS and guard exist; any later A or B finding invalidates both
acceptance slots and restarts at A. For an `authoring-proposal` review only,
both reports bind the same family, proposal-envelope hash, comparison-report
hash, source fingerprint, and execution snapshot. Generic semantic-batch,
fixed-Y, and truth-bootstrap reports contain no family, proposal, or comparison fields; those keys
are forbidden. They instead bind exactly the same `review_kind`, `subject_id`,
`subject_manifest_sha256`, source fingerprint, and execution snapshot as their
scope and subject manifest. Every review kind deliberately has different
`execution_inputs` for A and B: B's external bundle additionally contains A's
completed report, historical input bundle, control bundle, evidence bundle,
and completion token.

`review_sequence_sha256` is SHA-256 of
`b"dartwork-mpl-sequential-review-v1\0"` plus canonical JSON having exactly
`reviewer_a_report_sha256`, `reviewer_a_completion_token`,
`reviewer_b_report_sha256`, `reviewer_a_execution`, `reviewer_b_execution`,
`reviewer_a_execution_inputs_sha256`, `reviewer_b_execution_inputs_sha256`,
`reviewer_a_control_bundle_sha256`, `reviewer_b_control_bundle_sha256`,
`reviewer_a_evidence_bundle_sha256`, `reviewer_b_evidence_bundle_sha256`,
`common_source_fingerprint`, and `common_execution_snapshot_sha256`. Every
value is copied from and independently recomputed against the two reports and
their captured bundles. These fields
make sequence violations and reused contexts auditable. They cannot prove the
real-world identity or mental independence of a reviewer; the harness enforces
the procedure and the maintainer's explicit `independence_attested=true` is the
acceptance authority for that remaining social claim.

Promotion recomputes and parses every link rather than accepting hash-shaped
strings. It validates canonical family-bound paths, exact schemas, self-hashes,
PASS/role/instance separation, proposal and comparison links, A-to-B
predecessor order, both execution-input bundles, every review-evidence manifest
and blob, both immutable review-control manifests and blobs, and the visual
report's artifact map before copying the
three verified hashes, common fingerprint/snapshot, sequence hash, and approved
maintainer object into `acceptance`. Any validation failure precedes frozen-
envelope publication; a later durability failure may leave only the exact
non-authoritative bundle prefix allowed by section 3.5, never a frozen marker
without that durable bundle. These envelopes provide deterministic review
provenance and mismatch detection; they are not cryptographic human-identity
signatures. The validated `maintainer_approval` object remains the authority for
the user's explicit walkthrough and independence attestation.

## 4. Coordinate and layer contracts

| Name | Meaning | Allowed layer |
|---|---|---|
| actual `L` | OKLab/OKLCH lightness coordinate | construction |
| `C`, `h` | canonical binary64 OKLCH authoring parameter and hue; direction norm is recorded | construction |
| `DeltaEOK×100` | 100-scaled Euclidean OKLab distance | construction and reporting |
| `target_Y` | modeled relative CIE Y from nominal D65 sRGB | explicit output contract only |
| `NeutralTone` | `cbrt(target_Y)` convenience coordinate | shipped compatibility/provenance only |
| raw linear sRGB | unclamped destination channels | gamut feasibility |
| full CIELAB / CIEDE2000 | model-specific finished-output diagnostic | validation only; predecessor CIELAB L* remains a migration input only |
| named CVD simulation | model-specific finished-output diagnostic | validation only |
| existing project WCAG helpers | preserved public/validation utility outside this authoring extension | forbidden as a V1 authoring or admission input |

OKLab/OKLCH authoring construction modules may import the canonical conversion
and gamut kernels. They may not import CIELAB, CIEDE2000, CVD simulation,
`_luminance`, the WCAG role/threshold helpers, `ensure_contrast`, or the
independent quality oracle. V1 deliberately defines no WCAG coefficient,
transfer, pair-acquisition/compositing, threshold-context, rounding, result
schema, policy ID, or policy hash. Consequently WCAG is absent from
`ValidationOraclePolicy`, `policies.validation`, `validation_input_sha256`,
admission floors/verdicts, and `all_machine_checks_passed`; no V1 artifact may
claim a WCAG or general accessibility PASS.

This does not remove or redesign the existing public `ensure_contrast` utility
or `TEXT_CONTRAST` validator: their shipped API/output behavior remains in the
compatibility-preservation boundary. It states only that those broader
behaviors—including foreground/background discovery, alpha compositing, text
size/weight context, and display rounding—are not silently promoted into this
new-family authoring specification. A future replayable pair-specific WCAG
diagnostic requires a separate accessibility-policy design with its own closed
input acquisition, math, contextual thresholds, unrounded machine decision,
result schema/hash, and adversarial review. Sharing the low-level sRGB transfer
primitive does not make modeled relative CIE Y and WCAG the same role.

## 5. Generic fixed-relative-Y gamut boundary

### 5.1 Required result

The low-level primitive is private but has a structured contract:

```python
solve_max_chroma_for_relative_y(
    hue_deg: float,
    target_y: RelativeY,
    *,
    policy: RelativeYBoundaryPolicy,
) -> RelativeYGamutBoundary
```

The result and every nested evidence record are closed frozen/slotted types:

```python
ActiveFace: TypeAlias = Literal[
    "r=0", "r=1", "g=0", "g=1", "b=0", "b=1"
]

PolynomialId: TypeAlias = Literal[
    "projective-u-zero-v1", "projective-u-one-v1",
    "projective-r-zero-v1", "projective-r-one-v1",
    "projective-g-zero-v1", "projective-g-one-v1",
    "projective-b-zero-v1", "projective-b-one-v1",
    "projective-y0-zero-v1", "projective-stationary-chroma-v1",
    "projective-requested-chroma-cap-v1",
    "direct-chroma-zero-v1", "direct-requested-chroma-v1",
    "direct-r-zero-v1", "direct-r-one-v1",
    "direct-g-zero-v1", "direct-g-one-v1",
    "direct-b-zero-v1", "direct-b-one-v1",
]

SolverPolicyId: TypeAlias = Literal[
    "direct-oklch-gamut-v1", "relative-y-boundary-v1"
]

CoefficientModelId: TypeAlias = Literal[
    "binary64-direction-exact-rational-v1"
]

@dataclass(frozen=True, slots=True)
class ExactRational:
    numerator: int
    denominator: int

@dataclass(frozen=True, slots=True)
class CertifiedInterval:
    coordinate: Literal[
        "projective-u", "chroma", "chroma-cubed", "lightness"
    ]
    lower: ExactRational
    upper: ExactRational

@dataclass(frozen=True, slots=True)
class CandidateSource:
    source_rank: int
    polynomial_id: PolynomialId
    distinct_root_ordinal: int
    interval: CertifiedInterval

@dataclass(frozen=True, slots=True)
class AnalyticSelection:
    candidate_kind: Literal[
        "request", "neutral", "component-endpoint", "face-root",
        "stationary-root", "cap-root", "cluster"
    ]
    sources: tuple[CandidateSource, ...]
    active_faces: tuple[ActiveFace, ...]

@dataclass(frozen=True, slots=True)
class EndpointSelection:
    candidate_kind: Literal[
        "target-y-zero-black-policy", "target-y-one-white-policy",
        "lightness-zero-black-policy", "lightness-one-white-policy"
    ]
    active_faces: tuple[ActiveFace, ...]

SelectionCertificate: TypeAlias = AnalyticSelection | EndpointSelection

ProjectivePolynomialId: TypeAlias = Literal[
    "projective-r-zero-v1", "projective-r-one-v1",
    "projective-g-zero-v1", "projective-g-one-v1",
    "projective-b-zero-v1", "projective-b-one-v1",
    "projective-y0-zero-v1", "projective-stationary-chroma-v1",
    "projective-requested-chroma-cap-v1",
]

@dataclass(frozen=True, slots=True)
class RootIsolationProof:
    source: CandidateSource
    multiplicity: Literal[1, 2, 3]
    sturm_count: Literal[1]

@dataclass(frozen=True, slots=True)
class ProjectivePolynomialProof:
    polynomial_id: ProjectivePolynomialId
    coefficients: tuple[ExactRational, ...]
    degree: Literal[0, 1, 2, 3]
    domain_distinct_root_count: int
    roots: tuple[RootIsolationProof, ...]

@dataclass(frozen=True, slots=True)
class ProjectiveRootCluster:
    cluster_ordinal: int
    coordinate_interval: CertifiedInterval
    sources: tuple[CandidateSource, ...]
    equality_proof_sha256: str

@dataclass(frozen=True, slots=True)
class ProjectiveCellProof:
    cell_ordinal: int
    cell_kind: Literal["point", "open-interval"]
    lower_cluster_ordinal: int
    upper_cluster_ordinal: int
    rational_anchor: ExactRational | None
    partition_signs: tuple[Literal[-1, 0, 1], ...]
    classification: Literal["feasible", "infeasible", "undefined-scale"]

@dataclass(frozen=True, slots=True)
class ProjectiveCandidateProof:
    candidate_ordinal: int
    roles: tuple[
        Literal[
            "neutral", "component-boundary", "stationary", "requested-cap"
        ], ...
    ]
    selection: AnalyticSelection
    projective_u_interval: CertifiedInterval
    chroma_cubed_interval: CertifiedInterval
    chroma_lower_bound: float
    chroma_upper_bound: float
    constraint_admitted: bool

@dataclass(frozen=True, slots=True)
class ProjectiveProofCertificate:
    schema: Literal["oklab-projective-proof-v1"]
    objective_kind: Literal[
        "global-boundary", "requested-equality", "request-bounded-maximum"
    ]
    requested_chroma: float | None
    polynomials: tuple[ProjectivePolynomialProof, ...]
    root_clusters: tuple[ProjectiveRootCluster, ...]
    cells: tuple[ProjectiveCellProof, ...]
    candidates: tuple[ProjectiveCandidateProof, ...]
    selected_candidate_ordinal: int
    proof_sha256: str

@dataclass(frozen=True, slots=True)
class DirectionEvidence:
    hue_conversion_id: Literal["normalized-degrees-math-radians-v1"]
    requested_hue_deg: float
    normalized_hue_deg: float
    hue_radians: float
    cos_h: float
    sin_h: float
    direction_norm_squared: ExactRational

@dataclass(frozen=True, slots=True)
class ExactRationalCoefficientRecord:
    schema: Literal["oklab-exact-rational-coefficients-v1"]
    coordinate_model: Literal["projective-fixed-y", "direct-fixed-l"]
    hue_conversion_id: Literal["normalized-degrees-math-radians-v1"]
    normalized_hue_hex: str
    radians_hex: str
    cos_hex: str
    sin_hex: str
    direct_lightness_hex: str | None
    q_coefficients: tuple[
        tuple[ExactRational, ExactRational, ExactRational, ExactRational],
        tuple[ExactRational, ExactRational, ExactRational, ExactRational],
        tuple[ExactRational, ExactRational, ExactRational, ExactRational],
    ]
    y0_coefficients: (
        tuple[ExactRational, ExactRational, ExactRational, ExactRational]
        | None
    )

@dataclass(frozen=True, slots=True)
class AnalyticModelEvidence:
    policy_id: SolverPolicyId
    coefficient_model_id: CoefficientModelId
    coefficient_record: ExactRationalCoefficientRecord
    coefficient_sha256: str
    coefficient_abs_error_bound: float

@dataclass(frozen=True, slots=True)
class EndpointModelEvidence:
    policy_id: SolverPolicyId
    endpoint_policy_id: Literal["canonical-scalar-black-white-v1"]
    scalar_semantics_sha256: str

ModelEvidence: TypeAlias = AnalyticModelEvidence | EndpointModelEvidence

@dataclass(frozen=True, slots=True)
class DirectColorWitness:
    association_id: Literal[
        "modeled-relative-y-mul3-left-add-binary64-v1"
    ]
    chroma_direction_association_id: Literal[
        "chroma-direction-mul-binary64-v1"
    ]
    oklab_l: float
    chroma: float
    oklab_ab: tuple[float, float]
    raw_linear_srgb: tuple[float, float, float]
    encoded_srgb: tuple[float, float, float]
    neutral_baseline_raw_linear_srgb: tuple[float, float, float]
    neutral_baseline_encoded_srgb: tuple[float, float, float]
    achieved_relative_y: float

@dataclass(frozen=True, slots=True)
class RelativeYColorWitness:
    association_id: Literal[
        "modeled-relative-y-mul3-left-add-binary64-v1"
    ]
    residual_association_id: Literal[
        "achieved-y-minus-target-y-binary64-v1"
    ]
    chroma_direction_association_id: Literal[
        "chroma-direction-mul-binary64-v1"
    ]
    oklab_l: float
    chroma: float
    oklab_ab: tuple[float, float]
    projective_u: float | None
    raw_linear_srgb: tuple[float, float, float]
    encoded_srgb: tuple[float, float, float]
    neutral_baseline_raw_linear_srgb: tuple[float, float, float]
    neutral_baseline_encoded_srgb: tuple[float, float, float]
    achieved_relative_y: float
    relative_y_residual: float

@dataclass(frozen=True, slots=True)
class ScalarWitnessRecomputation:
    schema: Literal[
        "oklab-authoring-scalar-witness-recomputation-v1"
    ]
    algorithm_id: Literal[
        "scalar-witness-recompute-from-certified-coordinate-v1"
    ]
    bit_replay_scope_id: Literal[
        "same-base-runtime-environment-v1"
    ]
    base_runtime_environment_sha256: str
    constants_sha256: str
    association_id: Literal[
        "modeled-relative-y-mul3-left-add-binary64-v1"
    ]
    residual_association_id: Literal[
        "achieved-y-minus-target-y-binary64-v1"
    ]
    chroma_direction_association_id: Literal[
        "chroma-direction-mul-binary64-v1"
    ]
    projective_coordinate_algorithm_id: (
        Literal["projective-u-from-l-c-binary64-v1"] | None
    )
    coordinate_kind: Literal["direct-fixed-l", "projective-fixed-y"]
    direction_ab: tuple[float, float]
    oklab_l: float
    chroma: float
    oklab_ab: tuple[float, float]
    projective_u: float | None
    target_y: float | None
    neutral_reference_l: float
    raw_linear_srgb: tuple[float, float, float]
    encoded_srgb: tuple[float, float, float]
    neutral_baseline_raw_linear_srgb: tuple[float, float, float]
    neutral_baseline_encoded_srgb: tuple[float, float, float]
    achieved_relative_y: float
    relative_y_residual: float | None
    verdict: Literal["PASS"]

# Normative for both witness variants; shown as scalar operations.
canonical_a = float(chroma * direction.cos_h)
canonical_b = float(chroma * direction.sin_h)
yr = SRGB_D65_Y[0] * raw_linear_srgb[0]
yg = SRGB_D65_Y[1] * raw_linear_srgb[1]
yb = SRGB_D65_Y[2] * raw_linear_srgb[2]
canonical_achieved_y = (yr + yg) + yb

@dataclass(frozen=True, slots=True)
class RelativeYGamutBoundary:
    kind: Literal["relative-y-global-boundary"]
    boundary_mode: Literal[
        "interior-certified",
        "target-y-zero-black-policy",
        "target-y-one-white-policy",
    ]
    target_y: RelativeY
    direction: DirectionEvidence
    model: ModelEvidence
    neutral_reference_l: float
    boundary_chroma_lower_bound: float
    boundary_chroma_upper_bound: float
    boundary_abs_error_bound: float
    proof: ProjectiveProofCertificate | None
    selection: SelectionCertificate
    witness: RelativeYColorWitness
```

`RelativeYGamutBoundary` is only a global-boundary certificate. Requested-
chroma rendering does not inherit its `boundary_*` fields; section 5.5 defines
closed equality and constrained-reduction types.

The displayed witness-Y association is normative. Each multiplication and
addition executes exactly once in that order as an IEEE-754 binary64 scalar
operation. FMA, `math.fsum`, NumPy reduction, reassociation, channel clamp, and
encoded-RGB decode are forbidden. A stored `achieved_relative_y` in either
witness type must be bit-identical to `canonical_achieved_y` recomputed from
its stored raw-linear triple. Each stored `oklab_ab` must likewise be
bit-identical, including zero signs, to `(canonical_a,canonical_b)` recomputed
from its stored chroma and hash-linked `DirectionEvidence`. A
`RelativeYColorWitness.relative_y_residual`
must also be bit-identical to the one binary64 subtraction
`float(achieved_relative_y - target_y)` in the declared execution model. The
strict production loader, projective checker/Cartesian oracle comparison, and
independent direct-face oracle each recompute these fields. Endpoint scalar
verification retains its exact zero/one rules.

In memory every `ExactRational` is reduced with positive denominator. Evidence
JSON encodes its numerator and denominator as canonical base-10 strings.
Every binary64 value anywhere in result evidence is encoded as exactly
`{"number": value, "float_hex": value.hex()}`; it must be finite and reloading
must reproduce the same bits. RGB is a three-element array of those records.
Counts, ranks, and ordinals are non-boolean JSON integers. Every nested object
uses exactly its dataclass field set; unknown, omitted, or extra keys fail.

#### Canonical authoring scalar-kernel constants

Generation, rendering, discrete decoding, endpoint verification, the projective
proof checker, and both independent oracles share one complete semantic kernel
record. The record has exactly:

```text
AuthoringScalarKernelConstantsV1 = {
    schema,
    kernel_algorithm_id,
    bit_replay_scope_id,
    srgb8_decode_id,
    encoded_srgb_eotf,
    linear_srgb_to_lms_coefficients,
    cube_root_algorithm_id,
    cube_root_semantics_id,
    lms_cuberoot_to_oklab_coefficients,
    oklab_to_lms_cuberoot_coefficients,
    chroma_direction_association_id,
    cube_association_id,
    lms_to_linear_srgb_coefficients,
    linear_srgb_oetf,
    modeled_relative_y_coefficients,
    matrix_row_association_id,
    modeled_relative_y_association_id,
    residual_association_id,
    result_extraction_id,
}
```

`schema` is exactly `oklab-authoring-scalar-kernel-constants-v1`.
`kernel_algorithm_id` is `srgb-oklab-scalar-kernel-v1`;
`bit_replay_scope_id` is `same-base-runtime-environment-v1`;
`srgb8_decode_id` is `unsigned-channel-divide-255-binary64-v1`;
`cube_root_algorithm_id` is `numpy-cbrt-float64-scalar-v1`;
`cube_root_semantics_id` is `real-cuberoot-sign-preserving-v1`;
`chroma_direction_association_id` is
`chroma-direction-mul-binary64-v1`;
`cube_association_id` is `mul-left-cube-binary64-v1`;
`matrix_row_association_id` is `mul3-left-add-binary64-v1`;
`modeled_relative_y_association_id` is the exact literal
`modeled-relative-y-mul3-left-add-binary64-v1`;
`residual_association_id` is
`achieved-y-minus-target-y-binary64-v1`; and
`result_extraction_id` is `numpy-scalar-immediate-python-float-v1`.
`linear_srgb_to_lms_coefficients`, `lms_cuberoot_to_oklab_coefficients`, and
`oklab_to_lms_cuberoot_coefficients` are `3 x 3` arrays in their named input and
output orders. The last includes the formerly implicit coefficient of `L` as
an explicit exact `1.0` in every row.
`lms_to_linear_srgb_coefficients` is a `3 x 3` array whose rows are red, green,
blue and columns are `l**3`, `m**3`, `s**3`.
`modeled_relative_y_coefficients` is the length-three red, green, blue row.
`encoded_srgb_eotf` and `linear_srgb_oetf` each contain their exact algorithm ID
plus the five binary64 branch constants shown below.
Every leaf is section 5.1's exact two-key binary64 record. Object keys are
lexically ordered by canonical JSON; every array order stated here is semantic
and immutable.

Let `B(n,h)` denote `{"number":n,"float_hex":h}`. The V1 record contains
exactly these 49 binary64 leaves:

```text
encoded_srgb_eotf = {
  algorithm_id: "srgb-eotf-piecewise-binary64-v1",
  branch_cutoff:       B(0.04045, "0x1.4b5dcc63f1412p-5"),
  linear_divisor:      B(12.92,   "0x1.9d70a3d70a3d7p+3"),
  nonlinear_offset:    B(0.055,   "0x1.c28f5c28f5c29p-5"),
  nonlinear_divisor:   B(1.055,   "0x1.0e147ae147ae1p+0"),
  nonlinear_exponent:  B(2.4,     "0x1.3333333333333p+1"),
}

linear_srgb_to_lms_coefficients = [
  [
    B(0.4122214708, "0x1.a61d629f2e197p-2"),
    B(0.5363325363, "0x1.129a2d9e60e32p-1"),
    B(0.0514459929, "0x1.a572112081026p-5"),
  ],
  [
    B(0.2119034982, "0x1.b1fa76156a7c5p-3"),
    B(0.6806995451, "0x1.5c84a69936914p-1"),
    B(0.1073969566, "0x1.b7e5df0497455p-4"),
  ],
  [
    B(0.0883024619, "0x1.69afd7a044c17p-4"),
    B(0.2817188376, "0x1.207ae728a2f45p-2"),
    B(0.6299787005, "0x1.428c9177a5edbp-1"),
  ],
]

lms_cuberoot_to_oklab_coefficients = [
  [
    B( 0.2104542553, "0x1.af02a3fe8a4fap-3"),
    B( 0.7936177850, "0x1.9655120032aadp-1"),
    B(-0.0040720468, "-0x1.0add9bd572b38p-8"),
  ],
  [
    B( 1.9779984951, "0x1.fa5e1bfffde12p+0"),
    B(-2.4285922050, "-0x1.36dc1bffe5d3ep+1"),
    B( 0.4505937099, "0x1.cd686fff371a5p-2"),
  ],
  [
    B( 0.0259040371, "0x1.a869680b729e0p-6"),
    B( 0.7827717662, "0x1.90c776001f502p-1"),
    B(-0.8086757660, "-0x1.9e0ac0001353dp-1"),
  ],
]

oklab_to_lms_cuberoot_coefficients = [
  [
    B( 1.0,          "0x1.0000000000000p+0"),
    B( 0.3963377774, "0x1.95d9920068c8ap-2"),
    B( 0.2158037573, "0x1.b9f751ffa8cc8p-3"),
  ],
  [
    B( 1.0,          "0x1.0000000000000p+0"),
    B(-0.1055613458, "-0x1.b06117feec881p-4"),
    B(-0.0638541728, "-0x1.058bf3fe39e34p-4"),
  ],
  [
    B( 1.0,          "0x1.0000000000000p+0"),
    B(-0.0894841775, "-0x1.6e86f5fdf38b5p-4"),
    B(-1.291485548,  "-0x1.4a9ecbffeaa8dp+0"),
  ],
]

lms_to_linear_srgb_coefficients = [
  [
    B( 4.0767416621, "0x1.04e955dc3d73ap+2"),
    B(-3.3077115913, "-0x1.a76317ea9de73p+1"),
    B( 0.2309699292, "0x1.d906c3222ffefp-3"),
  ],
  [
    B(-1.2684380046, "-0x1.44b85a62c2affp+0"),
    B( 2.6097574011, "0x1.4e0c87d01bf65p+1"),
    B(-0.3413193965, "-0x1.5d82d4f5d4f2ap-2"),
  ],
  [
    B(-0.0041960863, "-0x1.12fea56e00671p-8"),
    B(-0.7034186147, "-0x1.68267c131178dp-1"),
    B( 1.707614701,  "0x1.b5263caef6bcdp+0"),
  ],
]

linear_srgb_oetf = {
  algorithm_id: "srgb-oetf-piecewise-binary64-v1",
  branch_cutoff:       B(0.0031308,           "0x1.9a5c37387b719p-9"),
  linear_multiplier:   B(12.92,               "0x1.9d70a3d70a3d7p+3"),
  nonlinear_multiplier:B(1.055,               "0x1.0e147ae147ae1p+0"),
  nonlinear_exponent:  B(0.4166666666666667,  "0x1.aaaaaaaaaaaabp-2"),
  nonlinear_offset:    B(0.055,               "0x1.c28f5c28f5c29p-5"),
}

modeled_relative_y_coefficients = [
  B(0.21267287873271212, "0x1.b38dd69739b28p-3"),
  B(0.7151521284847872,  "0x1.6e286b77038f1p-1"),
  B(0.07217499278250072, "0x1.27a0f71970228p-4"),
]
```

Under the declared scalar association, each linear-sRGB matrix row maps the
neutral LMS-cube triple `(1,1,1)` to exact binary64 `1.0`; the three modeled-Y
coefficients also sum to exact rational `1`. These are pinned invariants, not a
license to replace the project-normalized Y row with a nearby external table.

The named association is executable, not descriptive shorthand. For any row
`c` and triple `x`, `row3(c,x)` performs exactly:

```text
p0 = float(c[0] * x[0])
p1 = float(c[1] * x[1])
p2 = float(c[2] * x[2])
s01 = float(p0 + p1)
row_value = float(s01 + p2)
```

The inverse authoring path first computes `a=float(C*cos_h)` and
`b=float(C*sin_h)` under `chroma-direction-mul-binary64-v1`. For each inverse
row it treats the stored `1.0` first coefficient as a structural identity:
`p1=float(alpha*a)`, `p2=float(beta*b)`, `s=float(L+p1)`, then
`root=float(s+p2)`. Multiplying `L` by `1.0` is not an operation in this
association. It cubes each root as `square=float(x*x)` then
`cube=float(square*x)`. It applies `row3(lms_to_linear_srgb_coefficients,
cubes)` for each raw channel. The modeled-Y value is exactly
`row3(modeled_relative_y_coefficients, raw_linear_srgb)`, and its association ID
is therefore the frozen literal
`modeled-relative-y-mul3-left-add-binary64-v1`.

The scalar EOTF and OETF execute exactly these branches with the stored
binary64 constants:

```text
e = float(encoded)
if e <= eotf.branch_cutoff:
    linear = float(e / eotf.linear_divisor)
else:
    shifted = float(e + eotf.nonlinear_offset)
    normalized = float(shifted / eotf.nonlinear_divisor)
    linear = float(normalized ** eotf.nonlinear_exponent)

q = float(raw_linear)
if q <= oetf.branch_cutoff:
    encoded = float(oetf.linear_multiplier * q)
else:
    powered = float(q ** oetf.nonlinear_exponent)
    scaled = float(oetf.nonlinear_multiplier * powered)
    encoded = float(scaled - oetf.nonlinear_offset)
```

An 8-bit channel is first converted with the one binary64 division
`float(unsigned_integer) / 255.0`. Forward conversion decodes red, green, and
blue independently, applies `row3(linear_srgb_to_lms_coefficients, linear_rgb)`
for `l,m,s`, immediately extracts each
`float(numpy.cbrt(numpy.float64(value)))`, then applies
`row3(lms_cuberoot_to_oklab_coefficients, roots)` for `L,a,b`. A scalar power
using `**(1/3)`, `math.pow`, a NumPy vector/reduction, matrix multiplication,
FMA, reassociation, evaluation of an unselected transfer branch, or deferred
NumPy-scalar extraction is nonconforming. Inverse encoding uses the OETF above
without a clamp. Exact black and white remain the separate endpoint policy:
generic nonlinear white encoding rounds below `1.0` under this association and
therefore cannot replace the bit-exact endpoint record.

The cube-root operation is the real, sign-preserving scalar cube root
`float(numpy.cbrt(numpy.float64(x)))`; it preserves signed zero and is never
implemented as `x ** (1/3)`. The stored OETF exponent is used directly and is
never recomputed as `1/2.4`.

This record freezes the arithmetic graph and all coefficients used by generic
authoring; hue normalization/trigonometry and root/refinement policies remain
separately versioned. Validation-only CIELAB, CIEDE2000, and CVD are excluded;
the existing package WCAG helpers are likewise outside this V1 rather than
being falsely described as a pinned authoring policy. Their white points,
coefficients, contextual acquisition, and thresholds do not enter this record. Bit-identical witnesses
are claimed only under the hash-linked accepted environment-v3 runtime that
also records the `numpy-cbrt`/power trace. The same semantic record on an
uncaptured runtime is not evidence of cross-platform bit identity and cannot
publish V1 artifacts.

The binding has exactly `constants_record` and `constants_sha256`. Its hash is:

```text
constants_sha256 = SHA256(
    b"dartwork-mpl-oklab-authoring-scalar-kernel-constants-v1\0" +
    canonical_json(constants_record)
)
```

The canonical JSON is exactly 4,121 bytes with no terminal LF, and the only V1
digest is
`3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`.
Strict parsing checks the exact key set, dimensions, array order, dual numeric
bits, all frozen literals, canonical byte length, and golden digest before any
oracle computation. Negative zero, Boolean, non-finite values, shape drift, or
a record/hash pair that is merely self-consistent fails.

Every standalone scientific artifact that consumes generic authoring math
embeds this two-key binding exactly once. Generation, renderer, and discrete
policy records carry the exact golden digest; their enclosing hashes therefore
bind the kernel transitively. Each independent verifier/checker owns a separate
private literal table, reconstructs the same complete record, compares the two
records structurally before comparing independently recomputed hashes, and only
then performs its computation. It may not import a producer/shared constants
object or use the candidate artifact's record as numeric input; that would make
a self-consistent forgery validate itself. Invocation source hashes remain
provenance, not the semantic preimage.

Signed zero is part of the authoring evidence contract rather than an
accidental second spelling of rational zero. A recursive schema registry
classifies every binary64 leaf into exactly one of these closed classes:

- `canonical-nonnegative`: nonnegative coordinates, RGB channels, bounds,
  gaps, errors, reductions, budgets, tolerances, and oracle query chroma that
  are not contractually exact-zero fields; this class also covers such values
  when they later enter `Fraction.from_float`;
- `canonical-signed-rational-operand`: signed values such as `cos_h`/`sin_h`
  that enter `Fraction.from_float`; a zero in this class is positive zero;
- `signed-bit-evidence`: hue deltas and residual/parity values for which a
  negative value has meaning, plus recomputation-derived signed intermediates
  whose sign bit is itself evidence. In particular, both elements of
  `oklab_ab` in a production witness, scalar recomputation, or endpoint
  verification are in this class: canonical `C=+0.0` multiplied by a negative direction may
  legitimately produce `-0.0`; and
- `canonical-exact-zero`: the disjoint class whose contract says exactly
  zero, including zero slack/error/bounds and endpoint residuals.

After the dual number/hex bit check and before any range predicate, branch,
hash-derived comparison, or rational conversion, the strict loader rejects
the negative-zero bit pattern for the first two classes. A signed-bit-evidence
zero is accepted only when it is bit-identical to the original input or to the
result of the one specified recomputation; callers cannot choose its sign. For
`oklab_ab`, the only authority is the exact `float(C*cos_h)` /
`float(C*sin_h)` operation under
`chroma-direction-mul-binary64-v1`; numeric equality to zero is insufficient.
Canonical-exact-zero requires bits `0x0000000000000000`, not merely numeric
equality. Arrays and nested unions are checked leaf by leaf, and an
unclassified or multiply classified binary64 field fails closed. The loader
never silently rewrites `-0.0` to `+0.0`, because doing so would change the
evidence/hash preimage. These authoring-only rules do not reinterpret any
shipped-compatibility bytes.

`CandidateSource` uses this closed registry; `source_rank` must equal the rank
paired with `polynomial_id`, and the interval coordinate must equal the listed
coordinate:

| Rank | `polynomial_id` | Coordinate |
|---:|---|---|
| 0 | `projective-u-zero-v1` | `projective-u` |
| 1 | `projective-u-one-v1` | `projective-u` |
| 2 | `projective-r-zero-v1` | `projective-u` |
| 3 | `projective-r-one-v1` | `projective-u` |
| 4 | `projective-g-zero-v1` | `projective-u` |
| 5 | `projective-g-one-v1` | `projective-u` |
| 6 | `projective-b-zero-v1` | `projective-u` |
| 7 | `projective-b-one-v1` | `projective-u` |
| 8 | `projective-y0-zero-v1` | `projective-u` |
| 9 | `projective-stationary-chroma-v1` | `projective-u` |
| 10 | `projective-requested-chroma-cap-v1` | `projective-u` |
| 100 | `direct-chroma-zero-v1` | `chroma` |
| 101 | `direct-requested-chroma-v1` | `chroma` |
| 102 | `direct-r-zero-v1` | `chroma` |
| 103 | `direct-r-one-v1` | `chroma` |
| 104 | `direct-g-zero-v1` | `chroma` |
| 105 | `direct-g-one-v1` | `chroma` |
| 106 | `direct-b-zero-v1` | `chroma` |
| 107 | `direct-b-one-v1` | `chroma` |

The two coordinate-endpoint sources use ordinal zero and singleton rational
intervals. Every polynomial source ordinal is its zero-based position among
the distinct real roots of that polynomial inside the closed search domain,
ordered by exact value before feasibility filtering. Candidate sources are
serialized in ascending `(source_rank, distinct_root_ordinal, interval.lower,
interval.upper)` order with no duplicate source. When exact GCD/resultant and
root-isolation comparisons prove that multiple sources name one coordinate,
the implementation emits one candidate with the sorted union of its sources
and active faces. Merely overlapping dyadic intervals or equal rounded
binary64 witnesses never merges candidates. A source whose identity, ordinal,
or coordinate equality cannot be proved within
`comparison_refinement_limit` fails closed.

`candidate_kind` is derived, never chosen by a caller. It is `request` when the
selected coordinate contains the direct-request source or is the selected
projective cap root of a `RequestedEqualityResult`; otherwise it is `neutral`
when exact chroma is zero; otherwise it is `cluster` when sources from more than
one registry row are merged; otherwise endpoint source IDs map to
`component-endpoint`, the stationary ID maps to `stationary-root`, the cap ID
maps to `cap-root`, and a channel-face ID maps to `face-root`. No other source/
kind combination is valid.

An interior fixed-Y result always carries `ProjectiveProofCertificate`; an
endpoint global boundary carries null proof. Polynomial order is exactly
`r=0,r=1,g=0,g=1,b=0,b=1,y0=0,stationary`, followed by the requested-cap
polynomial only for requested rendering. Coefficients are trimmed ascending
rationals; roots are source-ordinal ordered, each interval has coordinate
`projective-u`, and the root count equals the tuple length. Root clusters begin
with `u=0`, end with `u=1`, contain the sorted union of every polynomial root,
and merge only proven equal coordinates.

Cells alternate a point cell (`lower==upper` cluster ordinal, null anchor) with
an open interval between consecutive clusters (distinct bounds and one strict
rational interior anchor), thereby covering `[0,1]` without a gap. Each
`partition_signs` tuple has seven entries in the feasibility-polynomial order
`r=0,r=1,g=0,g=1,b=0,b=1,y0=0`. Feasible means the zero-face signs are
nonnegative, one-face signs nonpositive, and `y0` positive; `y0=0` is
`undefined-scale`. Classification is derived from those signs, never trusted as
an independent assertion.

Candidate records are ordinal ordered and include every feasible component
boundary, feasible stationary root, neutral endpoint, and—when present—every
feasible requested-cap root. Their `projective_u_interval` and
`chroma_cubed_interval` coordinates match their names; binary64 chroma bounds
are directed conversions enclosing the latter interval's nonnegative cube
root. `constraint_admitted` is derived from objective kind and exact requested
chroma: all feasible candidates for global, exactly feasible cap roots for
requested equality, and exactly feasible candidates with `C<=Cr` for a
request-bounded maximum. The selected ordinal must name the exact-key winner
among admitted candidates from section 5.4.
Global proof has null requested chroma; both requested objectives carry the
exact binary64 request.

Each candidate's `roles` is derived from the complete merged
`selection.sources`, never supplied by a caller. Source rank 0 contributes
`neutral`; ranks 1 through 7 contribute `component-boundary`; rank 9
contributes `stationary`; and rank 10 contributes `requested-cap`. Rank 8 is an
undefined-scale partition source and cannot contribute a candidate. Remove
duplicates and serialize the complete union only in this order:
`neutral`, `component-boundary`, `stationary`, `requested-cap`. An empty,
duplicated, incomplete, extra, or reordered tuple fails. There is one candidate
per proven merged coordinate. Candidates themselves are ordered
lexicographically by their canonical tuple of
`(source_rank, distinct_root_ordinal)` identities, and
`candidate_ordinal == array index`; interval bytes and role labels never affect
that order.

`proof_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-projective-proof-v1\0"` plus canonical JSON of the proof
with only that field omitted. Unknown/missing fields, an empty required proof,
ordering/count mismatch, or a result/proof objective mismatch fails loading.

Every model-evidence policy ID must match the enclosing result variant.
Interior analytic results use only `AnalyticModelEvidence`:
`coefficient_model_id` is exactly
`binary64-direction-exact-rational-v1`, `coefficient_record` is the complete
closed `ExactRationalCoefficientRecord` defined above, its SHA-256 is a
lowercase 64-digit string independently recomputed over that record as defined
in section 5.4, and
`coefficient_abs_error_bound` is exactly `0.0`. Thus none of these strings is
an extension point inside a V1 result. Endpoint selections use only
`EndpointModelEvidence`; its scalar-semantics hash is the stable semantic hash
defined below and its policy ID is fixed above. Analytic selections
and endpoint model evidence, or endpoint selections and analytic model
evidence, are invalid combinations.

The endpoint semantic hash contains no implementation-file identity. It is
SHA-256 of
`b"dartwork-mpl-endpoint-scalar-semantics-v1\0"` plus canonical JSON having
exactly `algorithm_id="canonical-scalar-black-white-v1"`,
`constants_sha256`, `association_id`, and `hue_conversion_id`. The constants
hash is exactly the canonical authoring scalar-kernel digest above;
`association_id` is exactly
`modeled-relative-y-mul3-left-add-binary64-v1` and must equal the literal inside
that constants record; hue-
conversion ID is `normalized-degrees-math-radians-v1`. Raw script/kernel file
hashes remain only in invocation `implementation_sources` and never enter the
tracked scientific result payload.

`active_faces` describes the selected analytic coordinate through exact shared-
root/GCD classification, not an epsilon comparison with the inward-rounded
witness. Corners contain every incident face in the fixed order
`r=0,r=1,g=0,g=1,b=0,b=1`; an interior coordinate has an empty tuple. Black
endpoint selections contain `r=0,g=0,b=0`, and white endpoints contain
`r=1,g=1,b=1`. `projective_u` is null only for `L=C=0`, where the ratio is
undefined. In every result, the named lower bound and `mapped_chroma` where
present equal `witness.chroma`, and every numerical error field equals the
exact `outward_gap(upper,lower)` definition in section 5.4.

Generic authoring exposes no `max_chroma_at_tone()` convenience wrapper.
Fixed-Y callers pass `target_y` explicitly; `NeutralTone` remains confined to
the separately named compatibility lane.

### 5.2 Projective polynomial formulation

For fixed hue `h`, parameterize every non-negative `(L, C)` direction with:

```text
u = C / (L + C),  0 <= u <= 1
direction(u) = (L, a, b) = (1-u, u*cos(h), u*sin(h))
```

OKLab-to-linear-sRGB is homogeneous of degree three because it cubes three
affine LMS terms before the final matrix multiplication. Let:

```text
q(u)  = raw_linear_sRGB(direction(u))
y0(u) = SRGB_D65_Y dot q(u)
```

Each component of `q` and `y0` is a cubic polynomial in `u`. For an interior
`target_Y > 0` and any direction with `y0(u) > 0`, scale by:

```text
s = cbrt(target_Y / y0(u))
L = s * (1-u)
C = s * u
rgb_linear = target_Y * q(u) / y0(u)
```

This satisfies requested modeled Y exactly in the declared exact-rational
analytic model. The returned canonical scalar witness separately must satisfy
section 5.4's simultaneous absolute and relative Y guards. The parameterization
also covers all `L>=0, C>=0` candidates without assuming that Y is monotone in
`L` or that feasibility is monotone in `C`.

### 5.3 Complete candidate enumeration

The solver must partition `[0, 1]` at every real root of:

- `q_r(u)=0`, `q_g(u)=0`, `q_b(u)=0`;
- `target_Y*q_r(u)-y0(u)=0`, and likewise for green and blue;
- `y0(u)=0`; and
- the endpoints.

These are the six raw-sRGB cube faces plus undefined-scale boundaries. Interior
stationary chroma candidates satisfy:

```text
3*y0(u) - u*y0'(u) = 0
```

The solver evaluates all feasible interval boundaries and all feasible
stationary candidates, then chooses the global largest `C`. This handles
disconnected feasible intervals, folds, tangent roots, and repeated roots.

### 5.4 Numerical policy

The frozen policy is:

```python
RELATIVE_Y_BOUNDARY_V1 = RelativeYBoundaryPolicy(
    policy_id="relative-y-boundary-v1",
    scalar_kernel_constants_sha256="3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db",
    coefficient_model_id="binary64-direction-exact-rational-v1",
    hue_conversion_id="normalized-degrees-math-radians-v1",
    semantic_gamut_slack=0.0,
    root_interval_width=2.0**-48,
    root_bisection_limit=64,
    inward_bisection_limit=64,
    comparison_refinement_limit=4096,
    max_direction_norm_abs_error=2.0**-50,
    y_residual_abs=5e-13,
    y_residual_rel=2.0**-40,
    max_abs_chroma_error=1e-10,
    max_rel_chroma_error=2.0**-32,
)
```

All numeric fields reject booleans and non-finite values. The scalar-kernel hash
must equal section 5.1's golden digest. The three limits are positive integers.
The root width, direction-norm guard, and all four
residual/error budgets are positive; semantic slack is required to equal zero
and the hue-conversion ID must equal
`normalized-degrees-math-radians-v1` for this policy ID. `5e-13` is an absolute arithmetic postcondition, not a
physical or perceptual precision
claim. `2**-40` is the simultaneous relative-Y arithmetic guard.
`1e-10` and `2**-32` are respectively the simultaneous absolute and relative
OKLCH-chroma certificate budgets. These are numerical anti-collapse guards,
not visibility or just-noticeable-difference claims; an input that cannot meet
all applicable bounds fails rather than weakening the policy.

Both policies operate on finite IEEE-754 binary64 inputs and use the one
versioned direction sequence:

```text
normalized_hue_deg = requested_hue_deg % 360.0
hue_radians = math.radians(normalized_hue_deg)
cos_h = math.cos(hue_radians)
sin_h = math.sin(hue_radians)
```

Each operation occurs once in that order and the four returned binary64 values
are cached for coefficient construction and final witness rendering. Replacing
`math.radians` with multiplication/division by `math.pi`, changing association,
using NumPy, or recomputing the direction through another path is nonconforming.
Those cached values define the numerical direction for the invocation; the
solver does not claim exact trigonometric correspondence to an ideal real angle.

Record the exact rational
`direction_norm_squared=F(cos_h)**2+F(sin_h)**2`. With
`eps=F(policy.max_direction_norm_abs_error)`, require exactly
`(1-eps)**2 <= direction_norm_squared <= (1+eps)**2`; no rounded `hypot` result
certifies this guard. Throughout this contract, `C` is the canonical binary64
OKLCH authoring parameter passed to `(a,b)=(C*cos_h,C*sin_h)`. The exact-rational
Cartesian norm is therefore `C*sqrt(direction_norm_squared)`, not asserted to
be bit-exact `C`. Because the square-root factor is one positive constant for
the fixed hue, maximizing and ordering this parameter is equivalent to
maximizing Euclidean chroma along that ray. All `*_chroma_*` certificate widths
and budgets are expressed in the authoring parameter; the exact squared norm
makes the sub-ULP coordinate-model difference explicit rather than mislabeling
it coefficient error.

Polynomial coefficients live in the canonical conversion kernel and are
constructed with `fractions.Fraction` from the exact integer ratios of the
cached direction values and canonical binary64 OKLab and `SRGB_D65_Y`
constants. Let `F(x) = Fraction.from_float(x)`. For each inverse-LMS row:

Here and throughout the certificate/oracle sections, **exact arithmetic** means
exact integer/rational arithmetic over the exact binary64 bit patterns frozen
or captured by this artifact. `float_hex` is semantic authority; its JSON
number is accepted only when parsing reproduces the same bits. Conversion to a
rational uses the finite binary64's exact signed significand and power-of-two
exponent, reduced to a positive denominator—equivalently
`float.as_integer_ratio()` or `Fraction.from_float()`. Decimal text is never
passed directly to `Fraction`. Consequently zero coefficient-construction
error does not claim zero approximation error relative to ideal real-valued
sRGB, OKLab, trigonometric functions, or physical color. `pow`, `cbrt`, `sin`,
`cos`, and `hypot` are runtime-traced operations; portable bit identity is not
claimed outside `same-base-runtime-environment-v1`.

```text
d_i       = F(alpha_i)*F(cos_h) + F(beta_i)*F(sin_h) - 1
cube_i    = (1, 3*d_i, 3*d_i**2, d_i**3)
q[j,k]    = sum_i F(M[j,i]) * cube_i[k]
y0[k]     = sum_j F(SRGB_D65_Y[j]) * q[j,k]
```

The direct fixed-`L` variant uses the same constants but a distinct, explicit
expansion. For requested binary64 `Lr`:

```text
e_i       = F(alpha_i)*F(cos_h) + F(beta_i)*F(sin_h)
cube_i    = (
    F(Lr)**3,
    3*F(Lr)**2*e_i,
    3*F(Lr)*e_i**2,
    e_i**3,
)
q[j,k]    = sum_i F(M[j,i]) * cube_i[k]
```

The six direct face polynomials are `q[j]` and `q[j]-(1,0,0,0)`; their search
coordinate is `C`. Neither expansion imports or rounds coefficients through
NumPy.

Coefficients are stored in ascending degree order. Construction is exact only
relative to this declared binary64-input model, so
`coefficient_abs_error_bound` is exactly `0`. Evidence stores the cached
direction values and the complete typed `coefficient_record` having exactly `schema`,
`coordinate_model`, `hue_conversion_id`, `normalized_hue_hex`, `radians_hex`,
`cos_hex`, `sin_hex`,
`direct_lightness_hex`, `q_coefficients`, and `y0_coefficients`. The schema is
`oklab-exact-rational-coefficients-v1`; the coordinate model is
`projective-fixed-y` or `direct-fixed-l`. Projective records have null direct
lightness and a four-rational `y0_coefficients` array. Direct records have the
requested `L` hex string and null `y0_coefficients`. `q_coefficients` is always
three rows of four reduced `ExactRational` values in RGB/ascending-degree order.
Every direction hex field must bit-match the enclosing `DirectionEvidence`;
for direct results `direct_lightness_hex` must equal the exact request
`L.hex()`. An analytic result that serializes only a digest and omits the
record is invalid.
`coefficient_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-exact-rational-coefficients-v1\0"` plus canonical JSON of
the complete stored record. Angular approximation and final binary64 witness rounding are
separate and may not be described as coefficient error.

Every face, scale, cap, and stationary polynomial therefore has rational
coefficients. Remove exact zero leading coefficients, perform exact square-free
factorization, and isolate distinct real roots with exact-rational Sturm counts
and dyadic bisection. Obtain repeated roots from the exact polynomial GCD with
its derivative. No absolute polynomial epsilon, sign-change-only rule, or
unordered `numpy.roots` output establishes a root.

A root is resolved only when it is exact rational or enclosed by
`[u_lo, u_hi]` containing exactly one distinct root with
`u_hi-u_lo <= 2**-48`. No root may consume more than 64 bisections. Interval
overlap alone never merges roots. For roots from different polynomials, refine
in canonical source order until exact square-free GCD/Sturm reasoning proves
that they are the same algebraic coordinate or their intervals are disjoint.
Proven-equal roots form one ordered cluster; proven-distinct roots form separate
clusters. Failure to decide within the comparison-refinement budget raises
`RelativeYBoundaryError` rather than creating an unresolved cluster.

An isolating interval is a proof witness, not the canonical identity of its
algebraic root. Two conforming solvers may prove the same ordinal distinct root
with different rational brackets. Cross-implementation checks therefore compare
the source rank, polynomial ID, and distinct-root ordinal and then prove the two
brackets name the same algebraic root; they never require interval bytes to
match.

Every equality proof hashes one closed preimage with exactly `schema`,
`proof_kind`, `cluster_ordinal`, `coordinate_interval`, `sources`, and
`common_factor_coefficients`. Schema is
`oklab-projective-root-equality-v1`; proof kind is `singleton-source` or
`common-factor`; sources exactly equal the cluster's canonical sorted tuple. A
singleton has one source, its identical source interval, and an explicit null
common factor. A multi-source proof has at least two sources, the exact
intersection containing their one proven common root, and the trimmed ascending
monic square-free common-factor coefficients reconstructed from the recorded
polynomials. Canonical endpoint-source polynomials are `(0,1)` for `u` and
`(-1,1)` for `u-1`. No field is omitted. For every cluster:

```text
equality_proof_sha256 = SHA256(
    b"dartwork-mpl-projective-root-equality-v1\0" +
    canonical_json(complete equality-proof preimage)
)
```

The independent proof checker reconstructs this exact object and hash; an
opaque hash or overlap assertion is insufficient. `coordinate_interval` is the
exact intersection that contains the one proven common root. A cluster whose topology
or objective upper bound cannot be established under the policy raises
`RelativeYBoundaryError`.

Feasibility is evaluated against the exact-rational projective inequalities
with zero semantic slack. Each positive-width feasible component has a rational
interior anchor. For a boundary candidate, first test the component-side root-
bracket endpoint. If it fails the scalar postconditions, retain that outer
candidate and the verified inner anchor and bisect toward the outer candidate,
keeping the closest passing point. Stop at `2**-48` width or 64 bisections. A
singleton component must itself pass. This is the required inward-rounding
procedure; the solver never clamps a failing channel.

For a positive exact projective candidate, enclose its cube-root scale with
exact rational cube comparisons. Convert the witness chroma toward zero from
the lower scale bound; convert objective upper bounds toward positive infinity.
Derive `L` from the same inward projective point and refine toward its certified
interior anchor until the scalar postconditions hold. Thus returned `Cw` cannot
exceed the exact feasible candidate it witnesses.

Recompute the final witness through the canonical scalar
OKLab-to-linear-sRGB kernel with the cached direction. It must satisfy:

```text
isfinite(L), isfinite(C), L >= 0, C >= 0
0.0 <= raw_r <= 1.0
0.0 <= raw_g <= 1.0
0.0 <= raw_b <= 1.0
exact_y_gap <= Fraction.from_float(policy.y_residual_abs)

when 0 < target_y < 1:
    0.0 < achieved_y < 1.0
    exact_y_gap <= (
        Fraction.from_float(target_y) *
        Fraction.from_float(policy.y_residual_rel)
    )
    at least one raw channel > 0.0
    at least one raw channel < 1.0
    when C > 0:
        raw_linear_srgb differs bitwise from the stored neutral baseline
        encoded_srgb differs bitwise from the stored neutral baseline
```

Compute `achieved_y` from raw linear channels with section 5.1's canonical
five-operation association; `residual` is that value minus `target_y`, rounded
once to nearest binary64 with ties to even, while
`exact_y_gap` is
`abs(Fraction.from_float(achieved_y)-Fraction.from_float(target_y))`.
The rational relative comparison cannot underflow for a positive subnormal
target. Encoded channels are produced without a preceding clamp or an
encode/decode Y round trip. `target_y=0` and `target_y=1` use exact chroma-zero
black and white records with zero residual. Any positive target that cannot
meet both absolute and relative arithmetic postconditions fails; it is never
coerced to the black endpoint. This says nothing about human visibility or
8-bit quantization—a positive encoded witness may still quantize to `#000000`.

The neutral baseline is independently recomputed through the scalar kernel at
the result's `neutral_reference_l` and `C=0`; its raw/encoded triples are stored
in the witness, while the neutral `L` remains the result field and is
independently linked again by section 5.6. The triples are checked for finite
in-gamut channels without a clamp; this is a representation comparison,
not a second solution witness. A positive-chroma witness that collapses to
those same raw or encoded bits fails rather than claiming chroma that the scalar
representation lost. This is not a just-noticeable-difference rule; later 8-bit
quantization may still merge distinct floating outputs and records the duplicate.

For every root, stationary point, endpoint, and unresolved root-cluster
enclosure, compute an outward upper bound for
`C(u)**3 = target_y*u**3/y0(u)` with exact-rational interval operands. Convert
the final cube-root upper bound to binary64 toward positive infinity.

All certificates use this single subtraction primitive:

```text
outward_gap(upper, lower):
    require finite binary64 upper >= lower >= 0
    exact_gap = Fraction.from_float(upper) - Fraction.from_float(lower)
    if exact_gap == 0: return 0.0
    return the least finite binary64 value whose exact ratio >= exact_gap

certified_gap_ok(gap, upper, policy):
    require gap <= policy.max_abs_chroma_error
    if upper == 0: require gap == 0
    otherwise require:
        Fraction.from_float(gap) <=
        Fraction.from_float(policy.max_rel_chroma_error) *
        Fraction.from_float(upper)
```

The implementation obtains the last value by nearest conversion followed, when
necessary, by the traced `math-nextafter-positive` adapter (internally
`math.nextafter(value, math.inf)`); it fails rather than return infinity.
Ordinary binary64 subtraction is not the certificate definition.

For interior `0 < target_y < 1`, let `C_global` be the exact analytic-model
maximum over the complete certified feasible set. Let `U_global` be the largest
outward candidate bound over every feasible component and `Cw` the selected
conservative witness. The global result records:

```text
boundary_mode = "interior-certified"
boundary_chroma_lower_bound = Cw
boundary_chroma_upper_bound = U_global
boundary_abs_error_bound = outward_gap(U_global, Cw)
```

Candidate choice occurs in the exact analytic model before any binary64 witness
rounding. Treat every isolated root as a real algebraic value and compare the
following ascending keys:

```text
global or constrained: (-C, abs(L-neutral_reference_l), L, u)
requested equality:    (abs(L-neutral_reference_l), L, u)
direct fixed-L:         (-C,)
```

Here `neutral_reference_l` is the exact-model `C=0` root described in section
5.5, and the equality key omits `C` because every admitted root has exactly the
requested chroma. Compare rational functions with exact rational interval
arithmetic and cube comparisons; refine isolating intervals until their images
are disjoint. If images can be equal, use exact polynomial GCD/resultant sign
and equality tests to prove equality before moving to the next key component.
If every key component is equal, the points have the same `(L,C,u)` coordinate
and must be merged under the source-union rule in section 5.1. If strict order
or equality cannot be proved within `comparison_refinement_limit`, fail closed.

The comparison schedule is also frozen. Preorder analytic candidates by their
tuple of `(source_rank,distinct_root_ordinal)` identities, fold from the first
candidate, and compare each later candidate with the current incumbent. Test
key components left to right. First apply the exact equality/resultant test; if
it does not decide equality and the rational image intervals overlap, bisect
the wider canonical-representative source interval, breaking equal-width ties
by the smaller source identity, then recompute the image. Each such bisection
charges one invocation-wide comparison refinement. Exactly 4096 charges are
permitted; the next attempted charge fails. Root-isolation and inward-witness
bisections use their own counters. This schedule affects only reproducible
resource exhaustion—the proven mathematical order remains the selection rule.

Only after selecting the unique analytic coordinate does the implementation
construct its conservative binary64 witness. Rounded chroma, rounded `L`,
active-face rank, source order, display decimals, and epsilon comparisons never
participate in candidate choice. This rule applies uniformly to endpoints,
stationary points, face roots, root clusters, equality roots, and constrained
candidates.

The global guarantee is exactly:

```text
boundary_chroma_lower_bound <= C_global <= boundary_chroma_upper_bound
certified_gap_ok(
    boundary_abs_error_bound,
    boundary_chroma_upper_bound,
    policy,
)
```

Fail if any candidate is omitted from `U_global`, the bound is larger, or the
scalar witness fails. This is a global absolute OKLCH-chroma certificate, not a
Y tolerance, confidence interval, coefficient error, or amount by which an
authoring request was gamut-mapped. There is no arbitrary `C<=0.4` ceiling.

The declared Y weights are strictly positive and sum exactly to one, so the
abstract raw-RGB cube has unique `target_y=0` and `target_y=1` solutions: black
and white. The canonical scalar kernel's displayed association evaluates
`OKLab(0,0,0)` and `OKLab(1,0,0)` to those exact binary64 triples. Its exact-
rational coefficient expansion nevertheless preserves sub-ULP inverse-matrix
row-sum residue and is therefore not the endpoint-policy authority. Endpoint
records use `EndpointModelEvidence`, `boundary_mode="target-y-zero-black-policy"`
or `"target-y-one-white-policy"`, and lower, upper, and absolute-error bound
all exactly zero. They are checked by the separate endpoint verifier in section
5.6 and make no analytic `C_global` claim.

The implementation characterization records raw polynomial-versus-scalar
kernel differences on its pinned hue/`u` grid and every produced root. That
parity measurement is a regression guard over execution arithmetic, not an
epsilon used to discover roots or enlarge the certified gamut.

### 5.5 Generic fixed-Y rendering

Let `F` be the complete union of certified projective feasible components. The
neutral reference is the analytic model's `C=0` root, computed from the same
coefficients as `neutral_reference_l = cbrt(target_y/y0(0))`. The stored
binary64 value is the nearest value with ties-to-even, selected by exact
rational cube comparisons. It is not inferred from the compatibility
`NeutralTone` type.

Requested rendering and global-boundary solving answer different questions.
The result is therefore a discriminated union rather than a boundary record
with reused field names:

```python
@dataclass(frozen=True, slots=True)
class RequestedEqualityResult:
    kind: Literal["requested-equality"]
    target_y: RelativeY
    requested_chroma: float
    direction: DirectionEvidence
    model: AnalyticModelEvidence
    feasible_equality_root_count: int
    mapped_chroma: float
    equality_witness_shortfall_bound: float
    neutral_reference_l: float
    proof: ProjectiveProofCertificate
    selection: AnalyticSelection
    witness: RelativeYColorWitness

@dataclass(frozen=True, slots=True)
class ReducedConstrainedResult:
    kind: Literal["constrained-reduced"]
    target_y: RelativeY
    requested_chroma: float
    direction: DirectionEvidence
    model: AnalyticModelEvidence
    feasible_equality_root_count: Literal[0]
    mapped_chroma: float
    constrained_chroma_lower_bound: float
    constrained_chroma_upper_bound: float
    constrained_abs_error_bound: float
    requested_minus_mapped_chroma: float
    neutral_reference_l: float
    proof: ProjectiveProofCertificate
    selection: AnalyticSelection
    witness: RelativeYColorWitness

@dataclass(frozen=True, slots=True)
class EndpointRelativeYResult:
    kind: Literal["endpoint-policy"]
    mapping_mode: Literal["unchanged", "constrained-reduced"]
    target_y: RelativeY
    requested_chroma: float
    direction: DirectionEvidence
    model: EndpointModelEvidence
    mapped_chroma: float
    constrained_chroma_lower_bound: float
    constrained_chroma_upper_bound: float
    constrained_abs_error_bound: float
    requested_minus_mapped_chroma: float
    selection: EndpointSelection
    witness: RelativeYColorWitness

RelativeYSolvedColor: TypeAlias = (
    RequestedEqualityResult | ReducedConstrainedResult | EndpointRelativeYResult
)
```

For requested chroma `Cr>0`, enumerate roots on every component of the cap
polynomial:

```text
target_y*u**3 - Cr**3*y0(u) = 0
```

`Cr` is interpreted by its exact binary64 integer ratio and roots use the same
policy. If feasible equality roots exist, choose the unique analytic coordinate
with section 5.4's exact requested-equality key. Conservative witness rounding
happens afterward and cannot change that choice.

Return `RequestedEqualityResult` only when exact root counting proves at least
one feasible equality root. Its exact field set is the dataclass above;
`mapped_chroma` equals `witness.chroma`, and
`equality_witness_shortfall_bound` equals
`outward_gap(Cr,witness.chroma)`. Root intervals and source-local ordinals live
only in `selection.sources` under section 5.1's closed schema, so there is no
second, ambiguously ordered root field. `feasible_equality_root_count` is the
number of distinct feasible coordinates after proven cross-polynomial merging.
Its guarantee is:

```text
there exists u in F with C(u) == Cr
0 <= Cr-witness.chroma
   <= equality_witness_shortfall_bound
certified_gap_ok(equality_witness_shortfall_bound, Cr, policy)
```

This bound measures only conservative binary64 witness adjustment. It is not
global-boundary uncertainty and the result does not inherit any `boundary_*`
field. Inward rounding is therefore never silently described as exact.

If no feasible equality root exists, maximize `C(u)` over
`{u in F: C(u)<=Cr}` by considering every component endpoint, every feasible
stationary enclosure, every cap-root enclosure, and every unresolved cluster's
outward objective bound. Let this exact constrained maximum be `M_r`. Let
`U_r` be the lesser of `Cr` and the greatest outward bound over that complete
constrained candidate set. Select the unique analytic coordinate with section
5.4's exact global-or-constrained key, then construct its conservative witness.

Return `ReducedConstrainedResult` with:

```text
kind = "constrained-reduced"
requested_chroma = Cr
feasible_equality_root_count = 0
mapped_chroma = witness.chroma
constrained_chroma_lower_bound = witness.chroma
constrained_chroma_upper_bound = U_r
constrained_abs_error_bound = outward_gap(U_r, witness.chroma)
requested_minus_mapped_chroma
neutral_reference_l
witness
```

`requested_minus_mapped_chroma` is the nearest-ties-even binary64 conversion of
the exact ratio difference `Fraction.from_float(Cr) -
Fraction.from_float(witness.chroma)`. It is the intentional mapping amount and
may be large; it is never called numerical error. The constrained guarantee is:

```text
constrained_chroma_lower_bound <= M_r
    <= constrained_chroma_upper_bound <= Cr
certified_gap_ok(
    constrained_abs_error_bound,
    constrained_chroma_upper_bound,
    policy,
)
```

This searches every disconnected component and fold; it never assumes chroma-
prefix feasibility. If `Cr` exceeds the global boundary, the constrained
optimum equals the global optimum, but this result does not claim that identity
unless a separately returned global boundary certificate establishes it. Any
component whose outward uncertainty could violate either certificate budget
causes failure.

For interior target Y, `Cr=0` has the exact analytic neutral as its equality
candidate. The cap polynomial then has its multiplicity-three `u=0` root
merged with the neutral endpoint, so the single candidate has the complete
source union and `roles=("neutral", "requested-cap")`; neither role may be
discarded. Return `RequestedEqualityResult` only if its conservative witness
meets every scalar Y and certificate postcondition; otherwise fail with
`RelativeYBoundaryError` rather than promising a rounded neutral. At
`target_y=0` or `target_y=1`, every request instead returns
`EndpointRelativeYResult` with endpoint model/selection evidence. `Cr=0` uses
`mapping_mode="unchanged"`; a positive request uses `"constrained-reduced"`.
Lower, upper, mapped chroma, and numerical-error bound are exactly zero, while
the separately rounded requested reduction is `Cr`. These records make no
analytic equality-root or constrained-maximum claim. The mapper never clamps
RGB first and then labels the clipped result fixed-Y.

After compatibility migration, the accepted shipped mapped-Y solver remains
separate from this generic primitive and may change only through a new explicit
shipped-compatibility decision with exact-surface approval.

### 5.6 Independent endpoint and polynomial oracles

The closed constants registry for this section maps exactly
`endpoint-scalar-policy-verifier-v1`, `projective-proof-checker-v1`,
`cartesian-cubic-derivative-isolation-v1`, and
`direct-fixed-l-face-isolation-v1` to the one canonical authoring scalar-kernel
binding from section 5.1. Each enclosing standalone scientific artifact embeds
that complete binding once, and every contained algorithm reference resolves
through this registry to that binding; policy records that carry a
`constants_sha256` field contain its exact golden digest. A verifier first
strict-parses and recomputes the archived binding, then reconstructs it from
its own private literal table and requires structural equality plus two
independently recomputed golden hashes. The archived record is evidence, never
a constants provider. Direct-face results do not duplicate an opaque constants
field per result: their algorithm ID resolves to the enclosing artifact's
single binding. Their independently rebuilt aggregate exact-rational
coefficient record additionally checks polynomial construction, but does not
replace the full binding needed for direction multiplication, inverse/OETF,
modeled Y, residual, and operation-association semantics.

Endpoint policies are not submitted to the exact-rational polynomial oracles.
They use a separately transcribed scalar verifier with this closed record:

```python
@dataclass(frozen=True, slots=True)
class EndpointPolicyVerification:
    verifier_algorithm_id: Literal["endpoint-scalar-policy-verifier-v1"]
    result_kind: Literal[
        "relative-y-global-boundary", "relative-y-endpoint-render",
        "direct-oklch-endpoint-render"
    ]
    production_result_sha256: str
    endpoint_kind: Literal[
        "target-y-zero-black-policy", "target-y-one-white-policy",
        "lightness-zero-black-policy", "lightness-one-white-policy"
    ]
    requested_chroma: float | None
    mapped_chroma: float
    direction: DirectionEvidence
    scalar_semantics_sha256: str
    oklab_ab: tuple[float, float]
    raw_linear_srgb: tuple[float, float, float]
    encoded_srgb: tuple[float, float, float]
    achieved_relative_y: float
    verdict: Literal["PASS"]
```

For every verifier/oracle in this section, `production_result_sha256` is
SHA-256 of `b"dartwork-mpl-oklab-solver-result-v1\0"` plus canonical JSON of the
complete production result being checked. It is a lowercase 64-digit string
and must match before any numeric comparison; one verification record cannot
be reused for a different result.

The verifier reconstructs the closed section 5.1 constants binding from its
private literals and owns the canonical displayed multiplication/addition
association; it imports no production endpoint, conversion helper, or shared
constants object. It independently executes
`normalized-degrees-math-radians-v1` from the hash-linked requested hue and
requires bit identity for normalized hue, radians, cosine, sine, and the exact
direction norm before checking the endpoint. It requires `mapped_chroma` to be
exact positive zero, independently evaluates the two
`chroma-direction-mul-binary64-v1` products, and bit-compares its `oklab_ab`
with the production witness—including an operation-derived negative-zero sign.
Black kinds must produce bit-exact
raw/encoded `(0,0,0)` and achieved Y `0.0`; white kinds must produce bit-exact
`(1,1,1)` and `1.0`. It also reparses the production record and requires the
matching `EndpointModelEvidence`/`EndpointSelection`, zero mapped/lower/upper/
numerical-error fields, and exact requested-reduction rule. Requested chroma is
null only for a global-boundary result. No clamp, epsilon, exact-rational face
test, or polynomial certificate participates. A scalar result or linkage
disagreement fails; PASS is the only publishable record.

Its `scalar_semantics_sha256` is recomputed from the four-field semantic record
defined for `EndpointModelEvidence` and must equal the production model value.
The verifier may bind its own raw implementation source in invocation evidence,
but that provenance is not part of this scientific verification record.

#### 5.6.1 Fixed-Y Cartesian cubic oracle

Production Sturm isolation cannot validate itself. Characterization and tests
therefore use a separately written, test-only oracle with this frozen contract:

```text
oracle_algorithm_id = "cartesian-cubic-derivative-isolation-v1"
oracle_root_interval_width = 2**-96
oracle_refinement_limit = 1024
```

Every invocation is one explicitly bound fixed-chroma slice. Its closed query
and result records are:

```python
@dataclass(frozen=True, slots=True)
class CartesianOracleQuery:
    role: Literal[
        "global-lower", "global-upper-successor",
        "requested-equality", "equality-witness",
        "constrained-lower", "constrained-request",
        "constrained-upper-successor",
    ]
    chroma: float
    expected_feasibility: Literal["feasible", "infeasible"]
    query_input_sha256: str

@dataclass(frozen=True, slots=True)
class CartesianOracleRoot:
    ordinal: int
    multiplicity: Literal[1, 2, 3]
    lightness_interval: CertifiedInterval
    classification: Literal[
        "feasible", "negative-lightness", "out-of-gamut"
    ]
    active_faces: tuple[ActiveFace, ...]
    refinements: int

@dataclass(frozen=True, slots=True)
class CartesianOracleResult:
    oracle_algorithm_id: Literal[
        "cartesian-cubic-derivative-isolation-v1"
    ]
    production_result_sha256: str
    query: CartesianOracleQuery
    target_y: RelativeY
    direction: DirectionEvidence
    coefficients: tuple[ExactRational, ...]
    coefficient_sha256: str
    degree: Literal[0, 1, 2, 3]
    cubic_discriminant: ExactRational | None
    distinct_real_root_count: int
    roots: tuple[CartesianOracleRoot, ...]
    feasible_root_ordinals: tuple[int, ...]
    observed_feasibility: Literal["feasible", "infeasible"]
    total_refinements: int
```

`lightness_interval.coordinate` is `lightness`; roots and feasible ordinals are
in exact increasing-root order. The Cartesian coefficient-hash preimage has
exactly `schema="oklab-cartesian-oracle-coefficients-v1"` and `coefficients`,
the complete trimmed ascending `ExactRational` array. No field is omitted, and:

```text
coefficient_sha256 = SHA256(
    b"dartwork-mpl-cartesian-oracle-coefficients-v1\0" +
    canonical_json(complete Cartesian coefficient preimage)
)
```

The discriminant is present exactly for
degree three. Counts, ordinals, multiplicities, and refinement counts are
non-boolean nonnegative integers, every root multiplicity is positive, active
faces use section 5.1's exact classification and order, and
`observed_feasibility` is `feasible` exactly when at least one root has that
classification. It must equal the query expectation. All objects reject extra,
missing, or unknown fields and use section 5.1's rational/binary64 JSON forms.

For each finite binary64 `(hue, C, target_y)` slice with
`0 < target_y < 1`, the oracle independently executes the exact
`normalized-degrees-math-radians-v1` sequence from section 5.4. It recomputes
normalized hue, `math.radians` result, cosine, sine, and exact rational direction
norm from the hash-linked request and requires every binary64 bit and the policy
ID to equal production before comparing results. Using those independently
obtained values, it expands with `Fraction.from_float` the Cartesian polynomial:

```text
p(L) = SRGB_D65_Y dot
       raw_linear_sRGB(L, C*cos(hue), C*sin(hue)) - target_y
```

It reconstructs the closed section 5.1 constants binding from its private
literals and owns a separately written coefficient expansion. It may not
import the production/shared constants object, coefficient builder,
projective parameterization, polynomial GCD/Sturm utilities, root isolator,
boundary solver, or their helpers. A parity test compares the oracle constants
record structurally and by the golden digest before computation, but production
and oracle computations remain separate implementations.

After removing exact zero leading coefficients, a nonzero constant has no
roots and an identically zero polynomial is `INDETERMINATE`. Solve a linear
polynomial as an exact rational and count quadratic roots, including
multiplicity, with the exact discriminant. For a cubic
`a*L**3+b*L**2+c*L+d`, compute exactly:

```text
D = 18*a*b*c*d - 4*b**3*d + b**2*c**2
    - 4*a*c**3 - 27*a**2*d**2
```

`D>0` means three distinct real roots; `D<0` means one. When `D=0` and
`b**2-3*a*c=0`, construct the triple root `-b/(3*a)`. Otherwise construct the
double and simple roots exactly as:

```text
double = (9*a*d-b*c)/(2*(b**2-3*a*c))
simple = -b/a - 2*double
```

For distinct irrational roots, compute an exact rational Cauchy bound, enclose
the derivative roots with dyadic intervals using exact square comparisons,
refine until those intervals are disjoint and exact interval evaluation fixes
the sign of `p` at each critical point, then isolate roots on the resulting
monotone intervals by exact rational bisection. The final dyadic intervals must
be mutually disjoint, each contain exactly one root, match the discriminant-
derived distinct-root count, carry explicit multiplicity, and have width at
most `2**-96`.

At each isolated root, require `L>=0` and decide all six raw-channel face
inequalities by exact rational interval evaluation. If a channel-face
polynomial shares that root, an independently implemented exact resultant/GCD
classification establishes equality; otherwise refinement must exclude the
face. Overlapping intervals, undecidable critical-point or channel sign, root-
count mismatch, or 1024-refinement exhaustion returns `INDETERMINATE` and fails
the characterization. Tangent and repeated roots are never inferred only from
sign changes.

For each production result, construct oracle queries in the following exact
order, omitting only the explicitly conditional rows:

| Production result | Query role and chroma | Expected |
|---|---|---|
| global boundary | `global-lower` at `boundary_chroma_lower_bound` | feasible |
| global boundary | `global-upper-successor` at `math-nextafter-positive(boundary_chroma_upper_bound)` | infeasible |
| requested equality | `requested-equality` at `requested_chroma` | feasible |
| requested equality | `equality-witness` at `mapped_chroma`, only when its binary64 bits differ from the request | feasible |
| constrained reduction | `constrained-lower` at `constrained_chroma_lower_bound` | feasible |
| constrained reduction | `constrained-request` at `requested_chroma` | infeasible |
| constrained reduction | `constrained-upper-successor` at `math-nextafter-positive(constrained_chroma_upper_bound)`, only when that value is no greater than the request | infeasible |

`query_input_sha256` is SHA-256 of
`b"dartwork-mpl-cartesian-oracle-query-v1\0"` plus canonical JSON with exactly
`oracle_algorithm_id`, `target_y`, `requested_hue_deg`, `role`, `chroma`, and
`expected_feasibility`; the hash field itself is not part of that object. These
values must equal the containing result, direction, and query fields. Sharing a
result across chroma slices is forbidden. The global upper successor must be
finite. Endpoint-policy results are excluded and use
`EndpointPolicyVerification`. The fixed-Y oracle establishes these named
interior sample-slice facts only; the continuum-wide maximum still belongs to
the production certificate.

The oracle record includes exact coefficients, degree, discriminant, distinct-
root count, multiplicities, dyadic intervals, feasibility classifications, and
refinement counts. `Decimal` may format display text only; it has no correctness
role. Complete root isolation establishes feasibility for each sampled fixed-
`C` Cartesian slice. It does not by itself prove a continuum-wide global
maximum; that guarantee belongs to the production outward interval certificate
in section 5.4.

#### 5.6.2 Projective proof checker

Fixed-chroma Cartesian queries are independent cross-parameter checks, but an
infeasible immediate upper successor alone cannot exclude a more distant
feasible island. Every interior fixed-Y result therefore also passes a
separately written exhaustive proof checker. Its closed result is:

```python
@dataclass(frozen=True, slots=True)
class ProjectiveProofVerification:
    schema: Literal["oklab-projective-proof-verification-v1"]
    checker_algorithm_id: Literal["projective-proof-checker-v1"]
    production_result_sha256: str
    proof_sha256: str
    objective_kind: Literal[
        "global-boundary", "requested-equality", "request-bounded-maximum"
    ]
    polynomial_count: int
    distinct_root_count: int
    root_cluster_count: int
    cell_count: int
    candidate_count: int
    verified_chroma_lower_bound: float
    verified_chroma_upper_bound: float
    verified_abs_error_bound: float
    witness_recomputation: ScalarWitnessRecomputation
    verdict: Literal["PASS"]
```

The three verified fields map respectively to boundary lower/upper/error,
equality mapped/request/shortfall, or constrained lower/upper/error according
to `objective_kind`.

The checker imports no production/shared constants object, polynomial, GCD,
Sturm, isolation, feasibility, candidate, selection, or interval-bound helper.
From `DirectionEvidence`, target Y, optional requested chroma, and its own
private reconstruction of the closed section 5.1 constants binding, it first
recomputes the complete
versioned hue conversion from the hash-linked request and bit-compares every
direction field and exact norm. It then independently reconstructs the base
`ExactRationalCoefficientRecord` and first requires structural field-for-field
equality with `production.model.coefficient_record`. Only after that equality
does it independently hash both records and require both hashes to equal
`production.model.coefficient_sha256`. It then reconstructs every derived
rational polynomial. Its own exact Sturm
implementation proves the total `[0,1]` distinct-root count and one root in
each declared interval; exact GCD/resultant checks validate multiplicity and
cluster equality and reproduce every `equality_proof_sha256`. It rejects
overlapping unmerged roots, merged roots without a common-factor proof, and any
interval not accounted for.

The checker then verifies the alternating cells cover all of `[0,1]`, evaluates
every rational anchor and algebraic point sign, derives the complete feasible
set, independently enumerates all component-boundary/stationary/cap candidates,
derives each complete ordered `roles` union from the merged sources, orders
candidates by source-identity tuples, verifies every ordinal, and compares that
set with the certificate. It recomputes every exact
`C**3` interval, directed binary64 bound, objective admission, exact total key,
selected ordinal, aggregate upper bound, outward gap, and applicable absolute/
relative budget. Counts and three verified bounds must equal the production
result and certificate bit-for-bit. Any missing feasible island, root,
candidate, or outward contribution fails; PASS is the only publishable record.
For requested equality it also recomputes the exact distinct feasible equality-
root count and requires the production count to match.

Algebraic agreement alone cannot produce `PASS`. After selecting the certified
root/component, the checker performs
`scalar-witness-recompute-from-certified-coordinate-v1` without importing any
production raw RGB, encoded RGB, modeled-Y, residual, neutral-witness, or
scalar-conversion value as a numeric input. Production fields are read only
after the independent recomputation, for comparison. It first proves that the
stored production `L` and `C` are the binary64 coordinate selected by the
verified certificate. Independently, from the checker-owned exact neutral
coefficient and target Y, it derives the algebraic neutral root, rounds it
nearest-ties-even by exact cube comparison, and requires three-way bit identity
among that result, `production.neutral_reference_l`, and
`witness_recomputation.neutral_reference_l`. For a projective result it also
executes exactly:

```text
projective_coordinate_algorithm_id = "projective-u-from-l-c-binary64-v1"
denominator = float(L + C)
projective_u = float(C / denominator)
```

`projective_u` is null only when `L` and `C` are both exact positive zero; in
every other case its bits must equal the production witness. The checker then
computes `a=float(C*cos_h)` and `b=float(C*sin_h)` using the frozen direction,
runs its private no-clamp inverse/OETF/modeled-Y kernel, and runs the verified
nearest-ties-even algebraic neutral `L` with `C=0` through the same kernel. It
bit-compares both `a,b` with `production.witness.oklab_ab`, all three raw
channels, all three encoded channels, achieved modeled Y, the one
left-associated residual subtraction, and both neutral triples with the
production witness. Anti-collapse comparisons use only this recomputed
neutral. The recomputation's environment hash must equal the producer's
accepted `base_runtime_environment_sha256`; otherwise rational certificate
checks may pass, but a bit-replay `PASS` may not.

The complete `ScalarWitnessRecomputation` is serialized in the result. Its
`constants_sha256` is the golden section 5.1 digest; its bit-replay scope and
three association IDs equal the constants record; its projective-coordinate ID
equals the literal above; `coordinate_kind="projective-fixed-y"`; and its
`target_y`, `projective_u`, and residual are non-null. Every listed comparison,
association-ID check, runtime-scope check, and the algebraic checks above is a
necessary conjunct of `verdict="PASS"`.

The checker output and the ordered Cartesian slice results are both required.
The checker establishes exhaustive proof coverage; the Cartesian oracle tests
the same modeled-Y slices through an independently transcribed coordinate
formulation. Neither substitutes for the scalar witness postconditions.

#### 5.6.3 Direct fixed-L face oracle

The Cartesian fixed-Y oracle does not validate direct fixed-`L` authoring. A
second independent oracle uses this frozen identity:

```text
direct_oracle_algorithm_id = "direct-fixed-l-face-isolation-v1"
direct_oracle_root_interval_width = 2**-96
direct_oracle_refinement_limit = 1024
```

For interior `0<L<1`, it independently executes
`normalized-degrees-math-radians-v1` from the request, bit-compares every
direction field and exact norm with production, separately transcribes the
conversion constants, and expands the six fixed-`L`, fixed-hue channel-face cubics in `C`, isolates every root in
`[0,requested_chroma]`, merges only proven common roots, partitions the whole
domain, classifies each open cell from its exact rational interior anchor, and
classifies each point cell by exact algebraic sign determination at its merged
root. Point classification uses the independently isolated root together with
exact GCD/resultant and Sturm/subresultant sign proofs; it never consumes an
interior or neighboring-cell anchor. It may not import production coefficient,
root, gamut, or selection helpers. Its closed records are:

```python
@dataclass(frozen=True, slots=True)
class DirectOracleSourceIdentity:
    source_rank: int
    polynomial_id: PolynomialId
    distinct_root_ordinal: int

@dataclass(frozen=True, slots=True)
class DirectOracleChromaInterval:
    coordinate: Literal["chroma"]
    lower: ExactRational
    upper: ExactRational

@dataclass(frozen=True, slots=True)
class DirectOracleRoot:
    source_identity: DirectOracleSourceIdentity
    oracle_interval: DirectOracleChromaInterval
    multiplicity: Literal[1, 2, 3]
    refinements: int

@dataclass(frozen=True, slots=True)
class DirectOracleFacePolynomial:
    face: ActiveFace
    coefficients: tuple[ExactRational, ...]
    coefficient_sha256: str
    degree: Literal[0, 1, 2, 3]
    roots: tuple[DirectOracleRoot, ...]

@dataclass(frozen=True, slots=True)
class DirectOracleComponent:
    lower_source_identities: tuple[DirectOracleSourceIdentity, ...]
    upper_source_identities: tuple[DirectOracleSourceIdentity, ...]
    interior_anchor: ExactRational | None
    classification: Literal["feasible", "out-of-gamut"]

@dataclass(frozen=True, slots=True)
class DirectMaximumSourceMatch:
    source_identity: DirectOracleSourceIdentity
    production_interval: CertifiedInterval
    oracle_interval: DirectOracleChromaInterval
    intersection_interval: DirectOracleChromaInterval

@dataclass(frozen=True, slots=True)
class DirectMaximumRootEquivalence:
    schema: Literal[
        "oklab-direct-oracle-maximum-root-equivalence-v1"
    ]
    production_result_sha256: str
    reconstructed_coefficient_sha256: str
    source_matches: tuple[DirectMaximumSourceMatch, ...]
    common_factor_coefficients: tuple[ExactRational, ...]
    common_root_interval: DirectOracleChromaInterval
    equivalence_sha256: str

@dataclass(frozen=True, slots=True)
class DirectOracleQuery:
    role: Literal[
        "direct-lower", "direct-request", "direct-upper-successor"
    ]
    chroma: float
    expected_feasibility: Literal["feasible", "infeasible"]
    observed_feasibility: Literal["feasible", "infeasible"]
    query_input_sha256: str

@dataclass(frozen=True, slots=True)
class DirectFaceOracleResult:
    schema: Literal["oklab-direct-face-oracle-result-v1"]
    oracle_algorithm_id: Literal["direct-fixed-l-face-isolation-v1"]
    production_result_sha256: str
    request: DirectOklchPoint
    direction: DirectionEvidence
    reconstructed_coefficient_sha256: str
    face_polynomials: tuple[DirectOracleFacePolynomial, ...]
    components: tuple[DirectOracleComponent, ...]
    maximum_chroma_interval: CertifiedInterval
    oracle_maximum_chroma_lower_bound: float
    oracle_maximum_chroma_upper_bound: float
    maximum_source_identities: tuple[DirectOracleSourceIdentity, ...]
    maximum_root_equivalence: DirectMaximumRootEquivalence
    maximum_active_faces: tuple[ActiveFace, ...]
    maximum_candidate_kind: Literal[
        "request", "neutral", "component-endpoint", "face-root",
        "stationary-root", "cap-root", "cluster"
    ]
    queries: tuple[DirectOracleQuery, ...]
    total_refinements: int
    witness_recomputation: ScalarWitnessRecomputation
    verdict: Literal["PASS"]
```

Face polynomials are in section 5.1 face order; roots, source identities, and
components are in exact coordinate order. `maximum_chroma_interval.coordinate` is
`chroma`, encloses the greatest feasible point no greater than the request, and
has width at most `2**-96`. Each face-root list must match the independently
derived exact domain root count.

The oracle independently forms one exact merged-boundary sequence
`R_0 < ... < R_(m-1)` from every face root in the closed request domain plus
the `C=0` and requested-`C` endpoint sources. Sources are merged only when exact
common-root proof establishes coordinate equality. For every `R_i`, `U_i` is
the non-empty, duplicate-free, complete union of every source identity naming
that coordinate, sorted by `(source_rank, distinct_root_ordinal)`; the rank's
closed polynomial-ID mapping makes that pair a total key. An endpoint tuple
therefore also contains every face source proven coincident with it. Omitting,
adding, duplicating, or reordering an identity fails even when the coordinate
and all outer hashes agree.

`components` is exactly the `2*m-1`-element alternating decomposition of that
sequence. Element `2*i` is the point with
`lower_source_identities == upper_source_identities == U_i` and a null
`interior_anchor`. Element `2*i+1` is the open cell from `R_i` to `R_(i+1)`,
with lower tuple `U_i`, upper tuple `U_(i+1)`, and exactly one reduced rational
anchor strictly between the two coordinates. Thus adjacent cells repeat their
shared boundary tuple byte-for-byte and the array covers the entire closed
domain once, without a gap, overlap, omitted cluster, or alternative ordering.
When requested chroma is zero, `m=1`: zero, request, and any coincident face
sources form one union and exactly one point component. Proven-distinct
algebraic roots remain distinct boundaries and cells even if they round to the
same binary64 value.

Component classification is independently derived from all six face signs
rather than trusted. Open-cell signs are evaluated at the stored strict
rational anchor. Point-cell signs are evaluated exactly at `R_i` by the
algebraic proof above; neither adjacent open-cell anchor may substitute. Null
on an open component, any non-null point anchor—including at rational `C=0` or
the requested-`C` endpoint—or a non-strict/out-of-interval anchor fails. Always emit
`direct-lower` at the production `mapped_chroma` and require feasible. Emit
`direct-request` and require infeasible for `constrained-reduced`. Emit
`direct-upper-successor` and require infeasible when
`math-nextafter-positive(constrained_chroma_upper_bound)` is no greater than the request.
The query tuple uses that order and each observed result must equal its
expectation. `query_input_sha256` is SHA-256 of
`b"dartwork-mpl-direct-oracle-query-v1\0"` plus canonical JSON having exactly
`oracle_algorithm_id`, the containing complete `request`, `role`, `chroma`, and
`expected_feasibility`; the hash field and observed result are not in that
preimage.

Every direct oracle source identity has exactly the three displayed fields and
uses only `direct-chroma-zero-v1`, `direct-requested-chroma-v1`, or the six
direct face polynomial IDs. Rank and distinct-root ordinal are the canonical
non-Boolean nonnegative values derived from those independently reconstructed
polynomials. A face record's roots must name its own face polynomial; the
zero/request identities use respectively the exact polynomials `C` and
`C-F(Cr)`. Every oracle interval has exactly the three displayed fields,
reduced rational endpoints, `lower <= upper`, and width at most `2**-96`; every
production interval used by an equivalence match must have coordinate
`chroma`. Extra projective, stationary, or cap IDs fail strict parsing.

The oracle finishes root isolation, component classification, and maximum
selection before production source intervals become available to the
comparison layer. Its roots and component endpoints carry only
`DirectOracleSourceIdentity` plus independently derived oracle intervals. The
ordered production source tuple is projected to the same three identity fields
and must equal `maximum_source_identities` exactly. Rank, polynomial ID, or
ordinal disagreement is fatal even when the rounded chroma agrees.

A direct face's coefficient-hash preimage has exactly
`schema="oklab-direct-oracle-face-coefficients-v1"`, `face`, and the complete
trimmed ascending `coefficients`. No field is omitted, and its hash is SHA-256
of `b"dartwork-mpl-direct-oracle-face-coefficients-v1\0"` plus that canonical
object. Cartesian and direct coefficient domains are not interchangeable.

Before deriving those six face records, the oracle independently expands the
complete production-shaped coefficient object with schema
`oklab-exact-rational-coefficients-v1` from its separately transcribed OKLab-to-
linear-sRGB constants, the exact binary64 request `L`, and the independently
recomputed direction. It serializes every RGB polynomial row in the production
field order and hashes that complete object with the production coefficient
domain. Before comparing hashes it requires structural field-for-field equality
with the actual complete `production.model.coefficient_record`.
`reconstructed_coefficient_sha256` is the independent hash and both that value
and a separately recomputed hash of the production object must equal
`production.model.coefficient_sha256`. Each zero-face polynomial must then
equal the corresponding reconstructed RGB row, and each one-face polynomial
must equal that row with exact rational `1` subtracted from its constant term.
The six separately domain-separated face hashes do not replace this aggregate
cross-check.

After independent maximum selection, the comparison layer constructs
`maximum_root_equivalence`. For every source identity it independently
reconstructs the named exact polynomial: `C` for
`direct-chroma-zero-v1`, `C-F(Cr)` for
`direct-requested-chroma-v1`, and the matching independently expanded face
polynomial for a face ID. Using the oracle's Sturm implementation, it proves
that both the production interval and oracle interval contain exactly the
identity's ordinal-th distinct root, and that their exact intersection contains
exactly that root. `source_matches` follows canonical identity order.

For a singleton, `common_factor_coefficients` is the trimmed ascending monic
square-free form of that source polynomial and `common_root_interval` is the
source-match intersection. For a multi-source cluster, the coefficients are
the independently computed trimmed ascending monic square-free GCD of every
source polynomial; the GCD must have exactly one distinct root in
`common_root_interval`, which is the exact intersection of every source-match
intersection. Empty intersections, interval overlap without the ordinal and
polynomial proof, or a GCD that does not prove one shared root fail. The proof
self-hash is:

```text
equivalence_sha256 = SHA256(
    b"dartwork-mpl-direct-oracle-maximum-root-equivalence-v1\0" +
    canonical_json(
        complete maximum_root_equivalence with only
        equivalence_sha256 omitted
    )
)
```

Its `production_result_sha256` and `reconstructed_coefficient_sha256` equal
the containing result. The proof relates two independently valid witnesses; it
does not narrow or otherwise feed the production interval into oracle
selection, components, or `maximum_chroma_interval`.

Only after the direct maximum and its root equivalence have been selected does
the oracle perform the same closed scalar recomputation. It establishes that
the production `L` is the request's exact fixed `L`. It does **not** equate the
binary64 witness chroma with the exact algebraic maximum `M`: it first proves
the directed-containment chain below, then requires production `C` to be the
conservative coordinate `Plo == production.mapped_chroma ==
production.constrained_chroma_lower_bound == production.witness.chroma` and
recomputes scalar output at that `Plo`. It independently forms `a,b` and runs
its private no-clamp inverse/OETF/modeled-Y kernel. It separately runs the
direct neutral `(same request L,C=0)` through that kernel and requires
three-way bit identity among request `L`, production-witness `oklab_l`, and
`witness_recomputation.neutral_reference_l`. It bit-compares recomputed
direction-scaled `a,b` with `production.witness.oklab_ab`, then compares the raw
and encoded triples, achieved modeled Y, and both neutral triples;
anti-collapse uses only the recomputed neutral. Here
`coordinate_kind="direct-fixed-l"`,
`projective_coordinate_algorithm_id`, `projective_u`, `target_y`, and
`relative_y_residual` are null. The constants, association IDs, bit-replay
scope, accepted base-runtime hash, and every scalar comparison are necessary
conjuncts of `verdict="PASS"`; a self-consistent production witness cannot
validate itself.

For a nonnegative exact rational `q`, define `down64(q)` as the greatest finite
binary64 `x` with `Fraction.from_float(x) <= q` and `up64(q)` as the least finite
binary64 `x` with `Fraction.from_float(x) >= q`. Implement each by nearest
binary64 conversion plus exact integer-ratio comparison. `down64` makes zero
trace calls when the nearest value is already no greater than `q`; otherwise it
makes exactly one `math-nextafter-negative` call. `up64` makes zero calls when
the nearest value is already no less than `q`; otherwise it makes exactly one
`math-nextafter-positive` call. A generic nextafter, swapped direction, loop,
non-finite result, or need for a second step fails. Calls occur at the exact
`down64`/`up64` evaluation position in the displayed oracle recomputation, so
contextual replay determines their order. Let `Ilo,Ihi` be the
rational oracle maximum interval, `Blo,Bhi` its stored directed binary64 bounds,
`Plo,Phi` the production constrained bounds, `Cr` the binary64 request, and `M`
the unique greatest feasible chroma proved by exhaustive component
classification. A publishable result must recompute and prove exactly:

```text
Blo == down64(Ilo)
Bhi == up64(Ihi)

F(Plo) <= F(Blo) <= Ilo <= M <= Ihi
    <= F(Bhi) <= F(Phi) <= F(Cr)
Ihi - Ilo <= 2**-96

production.mapped_chroma
    == production.constrained_chroma_lower_bound
    == production.witness.chroma              # bit identity
production.constrained_abs_error_bound
    == outward_gap(Phi, Plo)
certified_gap_ok(
    production.constrained_abs_error_bound,
    production.constrained_chroma_upper_bound,
    production policy,
)
```

It also recomputes the exact-ratio `requested_minus_mapped_chroma`. In
`mapping_mode="unchanged"`, the request is feasible,
`Ilo == Ihi == F(Cr)`, mapped/lower/upper/request are bit-identical, and both
difference and error fields are zero. In `constrained-reduced`, the request is
infeasible and the rightmost feasible component supplies `M`; the full
containment chain is mandatory. `oracle_maximum_chroma_lower_bound` is `Blo`
and the upper field is `Bhi`. `verdict` is `PASS` exactly when every schema,
hash, direction, root, component, query, canonical witness-Y association,
direct achieved-Y bit identity, directed conversion, mode,
containment, gap, and budget check succeeds; PASS is the only serializable
value. Any disagreement fails characterization. Direct endpoint mode is
excluded and uses `EndpointPolicyVerification`.

The oracle derives the exact rightmost feasible maximum cluster from exhaustive
component classification. `maximum_source_identities`,
`maximum_active_faces`, and `maximum_candidate_kind` are respectively its
sorted algebraic-identity union, exact shared-root face set, and section 5.1
derived kind. Before PASS, the projected production identity tuple, active
faces, and candidate kind must equal them exactly, and the complete
`maximum_root_equivalence` proof must validate. Production and oracle interval
bytes are deliberately allowed to differ. The producer may not select a
different source cluster whose rounded chroma happens to tie. The unchanged
branch's maximum cluster contains the request source. The constrained branch's
maximum cluster is the rightmost feasible cluster strictly below the
analytically infeasible request. An analytically feasible request that fails
scalar postconditions has no serializable direct result and therefore no
oracle PASS record.

## 6. Direct-OKLCH authoring policy

Direct authoring uses actual `L`, not `NeutralTone`. Its geometric gamut
operation is the request-bounded, all-component fixed-`L`, fixed-`h` chroma
search specified in section 3.3. It has no arbitrary geometric upper endpoint:
the requested chroma bounds the optimization. Its semantic gamut tolerance is
zero and remains separate from the shipped mapper's `1e-6` compatibility
tolerance.

`render_direct_oklch()` accepts only `DirectOklchPoint` and
`DirectOklchGamutPolicy`; `render_fixed_relative_y_oklch()` accepts only
`FixedRelativeYPoint` and `RelativeYBoundaryPolicy`. New-family direct recipes
name `lightness_top` and `lightness_floor`. They do not reuse a `tone_floor`
field whose compatibility-migration value is defined as `cbrt(target_Y)` by
section 3.1.1. The predecessor Fourier family-derivation curves remain retired
migration provenance; they are neither copied into the operational
compatibility recipe nor reused as universal direct-OKLCH design laws.

## 7. New-family multi-hue discrete selection

### 7.1 Lifecycle

The selector is private authoring/build tooling, for example in
`_discrete_design.py`. A family has an explicit lifecycle:

- `derive-v1`: an explicitly named new family may run the authoring selector;
- `frozen`: every `n=1..8` result must exist in the SSOT manifest and runtime
  only replays it.

Missing frozen data is fatal. The system must not infer `derive-v1` because a
name or `n` row is absent.

Before release, an accepted `derive-v1` proposal is copied into the SSOT and
the family switches once to `frozen`. Proposal creation rejects shipped and
already-frozen names before running selection. Promotion is atomic create-only
under section 3.5's durable immutable-leaf/barrier contract. An existing byte-
identical frozen file is reverified/resynchronized as a no-op and a different
one is an error, never an update path.

### 7.2 Candidate domain

Selection operates on one validated final quantized 256-entry 24-bit RGB LUT
because those are the bytes that users receive and the indices that the
manifest stores. The selector algorithm ID is `oklab-maximin-v1`. It has no
universal candidate-domain default.

Every proposal supplies a frozen `DiscreteCandidatePolicy` with these fields:

```python
@dataclass(frozen=True, slots=True)
class DiscreteCandidatePolicy:
    policy_id: str
    selector_algorithm_id: str
    scalar_kernel_constants_sha256: str
    lightness_min: float
    lightness_max: float
    min_peak_chroma_fraction: float
    achromatic_peak_chroma_max: float
    max_search_states: int
```

All numeric fields reject booleans and non-finite values. Validation requires
`0 <= lightness_min < lightness_max <= 1`,
`0 < min_peak_chroma_fraction <= 1`,
`achromatic_peak_chroma_max >= 0`, and a positive integer
`max_search_states`. `selector_algorithm_id` must equal
`"oklab-maximin-v1"`, and `scalar_kernel_constants_sha256` must equal
`3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`;
neither has a default, and an unknown or omitted value fails before candidate
derivation. There is no omitted-field default, policy
relaxation, or fallback to another family's policy.

Decode each distinct RGB value once through the canonical sRGB-to-OKLab kernel.
Candidate identity is the 24-bit RGB value; if it occurs more than once, only
its lowest original LUT index is eligible. Peak chroma is the maximum
`hypot(a, b)` over all 256 positions. The row fails as achromatic when peak
chroma is at most the policy's `achromatic_peak_chroma_max`. Otherwise a unique
candidate is admitted exactly when its actual OKLab `L` is inside the inclusive
policy band and its chroma is at least
`min_peak_chroma_fraction * peak_chroma`. Fewer than `n` candidates is an
error, never a reason to widen the domain.

These fields are versioned project art direction, not psychophysical laws,
accessibility thresholds, or selector constants. Before a policy can be named
for production, a separately reviewed characterization artifact must bind its
LUT SHA-256 and generation-policy ID and include all 256 `L`/`C` values,
duplicate positions, admitted indices and count, results and integer scores for
`n=1..8`, a visual strip, and the design rationale for every threshold. A field
change requires a new policy ID and never recomputes a frozen family. The
characterization and sequential A/B/maintainer approval must occupy a verified
entry in section 3.5's tracked policy registry before a preselection envelope
can name the policy. This spec
approves the selector algorithm and explicit-policy mechanism; it does not
approve the previously conjectured `[0.45, 0.90]`, `0.60`, or `1e-6` values as
a production policy. Implementation tests use an explicitly named test-only
policy until a real new-family characterization is reviewed.

### 7.3 Selection objective

For decoded OKLab triples `x=(Lx,ax,bx)` and `y=(Ly,ay,by)`, the only distance
primitive is evaluated in this exact order:

```text
dL = float(Lx-Ly)
da = float(ax-ay)
db = float(bx-by)
squared = math.fsum((dL*dL, da*da, db*db))
delta_e_ok_100(x,y) = 100.0 * math.sqrt(squared)
```

Every intermediate must be finite and `squared` nonnegative. No `math.dist`,
NumPy norm, CIELAB distance, or alternative association is conforming.

De-duplication does not alter path geometry. Let `x_i` be the decoded OKLab
value at every original LUT position, including repeated values, and define the
full-row prefix arc in increasing index order:

```text
A[0] = 0
A[i] = math.fsum(delta_e_ok_100(x[k-1], x[k]) for k=1..i)
```

Each `A[i]` is evaluated as `math.fsum` over that complete prefix. Duplicate
steps therefore remain as zero-length steps in the 256-position arc.

All compared score components use the following exact integer conversion:

```text
q9(x):
    require finite x >= 0
    let (p, d) = x.as_integer_ratio()
    let (q, r) = divmod(p * 1_000_000_000, d)
    return q when 2*r < d, q+1 when 2*r > d,
    and q + (q % 2) when 2*r == d
```

For `n=1`, choose the admitted candidate minimizing
`(q9(abs(A[i] - A[255]/2)), i)`. This is the candidate nearest the midpoint of
the full 256-stop arc, with the lower original index as the final tie-break.

For `n>=2`, let `I=(i_0, ..., i_(n-1))` be a strictly increasing admitted-index
tuple and define:

```text
pair_q(i, j) = q9(delta_e_ok_100(x[i], x[j]))
minimum_q    = min(pair_q(i, j) for every selected pair)
coverage_q   = q9(A[i_(n-1)] - A[i_0])
gaps         = (A[i_1]-A[i_0], ..., A[i_(n-1)]-A[i_(n-2)])
mean         = fsum(gaps) / len(gaps)
cv           = sqrt(fsum((gap-mean)**2 for gap in gaps) / len(gaps)) / mean
gap_cv_q     = q9(cv)
rank(I)      = (-minimum_q, -coverage_q, gap_cv_q, I)
```

Choose the lexicographically smallest `rank`. The CV is the population CV;
for `n=2` its one gap gives exactly zero. A non-positive mean is an internal
arc/input error and fails rather than receiving a sentinel score. `1e-9` is
only the versioned deterministic comparison and serialization unit. It is not
a just-noticeable difference, an sRGB code-step estimate, or an accessibility
threshold.

The frozen normative record contains the LUT digest, complete candidate-domain
record and digest, candidate-policy ID, selector algorithm ID,
`max_search_states`, candidate count, selected indices, and integer objective
scores. Proposal creation derives the domain once; promotion re-derives it
before replay; runtime only validates the accepted stored record. Actual
`states_charged` is a non-normative build diagnostic. Changing search mechanics
requires a new selector algorithm ID but does not change already frozen assets.

### 7.4 Search behavior

For `n>=2`, compute each `pair_q` once. Let `thresholds` be the strictly
increasing sorted unique pair-score integers. At threshold `t`, admitted
candidates are vertices in original-index order and `(i, j)` is an edge exactly
when `pair_q(i, j) >= t`.

Binary-search the largest feasible threshold using
`lo=0`, `hi=len(thresholds)-1`, and `mid=lo+(hi-lo)//2`. A feasible midpoint
moves `lo` to `mid+1`; an infeasible midpoint moves `hi` to `mid-1`. No floating
epsilon participates.

Feasibility uses ascending DFS over greater-index adjacency bitsets. It creates
a fresh memo for each threshold with key `(mask, need)`. A cache hit is free; a
cache miss charges one state before base or cardinality checks. The only pruning
is `mask.bit_count() < need` and exhaustion of the ascending suffix; there is no
heuristic, dominance, or objective pruning. Once the maximum threshold is
known, an uncached ascending DFS enumerates every size-`n` clique and selects
the smallest full `rank`. Every final-enumeration recursion entry, including a
terminal tuple, charges one state; only cardinality pruning is allowed.

The normative feasibility transition is:

```text
feasible(mask, need):
    key = (mask, need)
    if key in memo: return memo[key]
    charge one state
    if need == 0:
        result = true
    else if bit_count(mask) < need:
        result = false
    else:
        result = false
        for v in the set bits of mask from lowest to highest:
            if feasible(mask & greater_neighbor_mask[v], need-1):
                result = true
                break
    memo[key] = result
    return result
```

Every charged state is inserted before returning, including base, pruned,
successful, and exhausted-false states. Therefore cache-hit accounting cannot
depend on an implementation's choice of which outcomes to memoize.

Final enumeration uses the same ascending transition without memoization or
early success; it carries the selected prefix and evaluates `rank` only when
`need==0`.

The counter starts at zero per selector invocation and is shared by every
threshold feasibility probe and the final enumeration. Exactly
`max_search_states` charges are permitted; the next attempted charge raises
`DiscreteSelectionError`. Distance and graph construction do not charge a
state. `n=1` charges zero states. Exhaustion returns and writes no partial best.
There is no greedy fallback, CIE-driven retry, band relaxation, or
borrowed-family result.

## 8. Independent admission validation

The selector must not import or call `_metrics`, `_compatibility_metrics`,
`_gates`, CIEDE2000, or CVD simulation.

The finished-output oracle is not selected by arbitrary strings. Its exact
recognized policy is:

```python
@dataclass(frozen=True, slots=True)
class ValidationOraclePolicy:
    policy_id: str
    truth_id: str
    ciede2000_policy_id: str
    delta_e_ok_policy_id: str
    protan_policy_id: str
    deutan_policy_id: str
    tritan_policy_id: str
    cvd_roundtrip_id: str
    pair_enumeration_id: str
    minimum_tie_id: str
    reference_suite_id: str

VALIDATION_ORACLE_V1 = ValidationOraclePolicy(
    policy_id="finished-output-validation-oracle-v1",
    truth_id="finished-output-validation-oracle-truth-v1",
    ciede2000_policy_id="ciede2000-legacy-d65-unit-weights-v1",
    delta_e_ok_policy_id="delta-e-ok-math-dist-times-100-v1",
    protan_policy_id="machado-2009-protan-severity-1-linear-srgb-v1",
    deutan_policy_id="machado-2009-deutan-severity-1-linear-srgb-v1",
    tritan_policy_id="bvm-1997-tritan-libdaltonlens-linear-srgb-v1",
    cvd_roundtrip_id="linear-project-clamp-encode-srgb8-v1",
    pair_enumeration_id="lexicographic-row-pairs-v1",
    minimum_tie_id="exact-binary64-value-then-pair-v1",
    reference_suite_id="compatibility-metrics-reference-suite-v1",
)
```

For this top-level ID, the exact eleven-key serialized record and every value above
are mandatory; unknown IDs, component mixing, aliases, and omitted or extra
fields fail. Before validating a proposal, the independent standard-library
oracle runs its pinned reference suite. Normal mode parses the final quantized
hex directly. Protan and deutan use the pinned Machado 2009 severity-1 matrices;
tritan uses the pinned project-adapted BVM 1997 separation vector and selects
the high matrix when the left-to-right binary64 dot product is `>=0.0`, otherwise
the low matrix.

The exact eleven keys are also a role boundary: V1 admission has no WCAG
extension. A WCAG helper, coefficient, ratio, foreground/background resolver,
threshold label, rounded display value, or policy-shaped extra field is an
unknown admission-policy input and fails strict parsing rather than becoming an
implicit twelfth component.

V1 truth is not defined by the current oracle run. It is the create-only tracked
asset
`src/dartwork_mpl/asset/color/validation_oracle_truth_v1.json`, with exactly:

```text
schema, truth_id, policy, policy_sha256, source, constants,
reference_vectors, expected_reference_results, truth_payload_sha256
```

`schema` is `oklab-validation-oracle-truth-v1` and `truth_id` is the value
above. `policy` is the complete eleven-key V1 policy and its hash uses the
validation-policy domain. `source` has exactly `role`, `path`, and
`raw_sha256`. `constants` has exactly `constants_record` and
`constants_sha256`; the record contains every ordered matrix, transfer
constant, white point, separation vector, branch constant, and reference value,
and its hash uses the constants domain above. `reference_vectors` has exactly
`path`, `raw_sha256`, `semantic_sha256`, and positive `case_count`.
`expected_reference_results` has exactly `case_results_sha256` and
`verdict="PASS"`. The self-hash is SHA-256 of
`b"dartwork-mpl-validation-oracle-truth-v1\0"` plus the complete asset with
only `truth_payload_sha256` omitted.

The truth asset receives one durable preinstall bootstrap before any admission
policy can reference V1. A second postinstall review is intentionally absent:
this lifecycle installs curated, reviewed authority bytes from an archive; it
does not make fixed-Y's independent-regeneration claim. The canonical ignored
producer tree is:

```text
build/color-authoring/validation-oracle-truth-v1/
  candidate.json
  review-subject.json
  reviews/reviewer-a.json
  reviews/reviewer-b.json
  input-bundles/<external_input_bundle_sha256>/manifest.json
  input-bundles/<external_input_bundle_sha256>/blobs/<raw_sha256>
  review-controls/<review_control_bundle_sha256>/manifest.json
  review-controls/<review_control_bundle_sha256>/blobs/<raw_sha256>
  review-evidence/<review_evidence_bundle_sha256>/manifest.json
  review-evidence/<review_evidence_bundle_sha256>/blobs/<raw_sha256>
```

The durable authority is:

```text
docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/
  validation-oracle-truth-review-v1/
    acceptances/bootstrap.json
    archive/
      subjects/<subject_manifest_sha256>/manifest.json
      reports/<reviewer_report_sha256>.json
      input-bundles/<external_input_bundle_sha256>/manifest.json
      input-bundles/<external_input_bundle_sha256>/blobs/<raw_sha256>
      review-controls/<review_control_bundle_sha256>/manifest.json
      review-controls/<review_control_bundle_sha256>/blobs/<raw_sha256>
      review-evidence/<review_evidence_bundle_sha256>/manifest.json
      review-evidence/<review_evidence_bundle_sha256>/blobs/<raw_sha256>
      execution-snapshots/<execution_snapshot_archive_sha256>/manifest.json
      execution-snapshots/<execution_snapshot_archive_sha256>/blobs/<raw_sha256>
```

The review kind is exactly `validation-oracle-truth-bootstrap` and the subject
ID is exactly `finished-output-validation-oracle-truth-v1`. Its generic
`ReviewSubjectManifest` contains exactly these three records in the universal
UTF-8 tuple sort order:

```text
candidate-truth               external-input  build/color-authoring/validation-oracle-truth-v1/candidate.json
validation-oracle-source      source-snapshot <candidate.source.path>
validation-reference-vectors source-snapshot <candidate.reference_vectors.path>
```

The evidence requirement has exactly `kind`, `truth_id`,
`truth_target_path`, `truth_raw_sha256`, and `truth_payload_sha256`.
`kind` equals the review kind, `truth_id` equals the subject ID, target path is
the literal tracked truth path above, raw hash covers the canonical candidate
file including its one terminal LF, and payload hash is independently
recomputed. The rubric requires independent reference-result recomputation
without importing or calling the candidate finished-output oracle, exact
policy/source/constants/vector/result linkage, target and acceptance absence in
the reviewed snapshot, and exclusion of authoring recipes, proposal/selector
rows, frozen families, and candidate-construction imports.

The truth-specific generic reviewer schemas are
`oklab-validation-oracle-truth-bootstrap-reviewer-a-v1` and
`oklab-validation-oracle-truth-bootstrap-reviewer-b-v1`; their domains are
their exact schema prefixed by `dartwork-mpl-` and followed by one NUL. They use
section 3.6's generic report keys, independent-instance rules, completion
token, and restart rule. The role table in section 10 closes their exact input
sets.

The tracked `bootstrap.json` has exactly:

```text
schema, review_kind, subject_id, subject_manifest_sha256,
truth_id, truth_target_path, truth_raw_sha256, truth_payload_sha256,
reviewer_a_report_sha256, reviewer_b_report_sha256,
reviewer_a_external_input_bundle_sha256,
reviewer_b_external_input_bundle_sha256,
reviewer_a_execution_inputs_sha256, reviewer_b_execution_inputs_sha256,
reviewer_a_control_bundle_sha256, reviewer_b_control_bundle_sha256,
reviewer_a_evidence_bundle_sha256, reviewer_b_evidence_bundle_sha256,
review_sequence_sha256, reviewed_source_fingerprint,
reviewed_execution_snapshot_sha256,
reviewed_execution_snapshot_archive_sha256,
archive_promotion_provenance, maintainer_approval, acceptance_sha256
```

Its schema is `oklab-validation-oracle-truth-review-acceptance-v1`; kind,
subject, truth ID, and target path are the literals above. Every hash is
recomputed from the archived subject, reports, input/control/evidence closure,
sequence, snapshot archive, or candidate bytes. `maintainer_approval` uses the
same exact four keys and independence requirement as fixed-Y acceptance. Its
walkthrough subject hash is:

```text
SHA256(
    b"dartwork-mpl-validation-oracle-truth-bootstrap-walkthrough-v1\0" +
    canonical_json({
        "review_kind": review_kind,
        "subject_id": subject_id,
        "subject_manifest_sha256": subject_manifest_sha256,
        "truth_id": truth_id,
        "truth_target_path": truth_target_path,
        "truth_raw_sha256": truth_raw_sha256,
        "truth_payload_sha256": truth_payload_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "review_sequence_sha256": review_sequence_sha256,
        "common_execution_snapshot_sha256":
            reviewed_execution_snapshot_sha256,
        "common_execution_snapshot_archive_sha256":
            reviewed_execution_snapshot_archive_sha256,
    })
)
```

Approval reference, promotion input/provenance, and acceptance hash are
deliberately absent from that exact preimage. Define `acceptance_sha256` as
SHA-256 of
`b"dartwork-mpl-oklab-validation-oracle-truth-review-acceptance-v1\0"` plus
the complete canonical acceptance with only that field omitted.

The bootstrap lifecycle is fail-closed and ordered:

1. require both the tracked truth target and `bootstrap.json` to be absent,
   then write the ignored candidate;
2. capture the preinstall snapshot and exact subject, then obtain fresh
   sequential Reviewer A and Reviewer B PASS on that unchanged snapshot;
3. capture the four-key maintainer approval, promote the complete subject,
   A/B input/control/evidence/token closure and common snapshot archive, and
   durably barrier that archive before writing tracked `bootstrap.json` with
   `publish_immutable_100644`, then barrier the acceptance; and
4. install the tracked truth create-only from the archived `candidate-truth`
   blob only with the same durable primitive and final directory barrier,
   never from the live ignored producer.

An acceptance-without-truth crash is recoverable only by exact installation
from that archived blob. A byte-identical complete repetition is a verified
no-op; a differing existing acceptance or truth is fatal. The truth asset does
not contain an acceptance hash, so there is no cycle. An admission run accepts
V1 only when both tracked files and the complete archived closure validate and
the acceptance's raw and semantic truth hashes equal the installed truth. It
then reads the truth only from the captured source snapshot and requires
current implementation bytes, complete constants, reference vectors, case
count, and exact expected result hash to match before PASS. Any formula,
constant, vector, implementation byte, or expected-result change requires a
new policy ID, truth ID, path, bootstrap acceptance, and review; a
self-consistent current implementation cannot refresh V1 truth.

Every named CVD mode uses this exact round trip:

```text
final lowercase 8-bit hex
-> independent encoded-sRGB byte/255 parser
-> independent pinned sRGB gamma decode
-> named linear-RGB projection
-> clamp each projected linear channel to [0,1]
-> independent pinned sRGB gamma encode
-> Python round(channel*255), ties to even
-> lowercase 8-bit hex
-> parse simulated hex
-> CIELAB/CIEDE2000 and DeltaEOK*100
```

CIEDE2000 uses the oracle's legacy D65 XYZ matrix, D65 white
`(0.95047,1.0,1.08883)`, and unit weights. Validation `DeltaEOK*100` is the
V1 oracle's normative
`math.dist(srgb_to_oklab(a), srgb_to_oklab(b))*100.0`; it is
intentionally independent from the selector-only `math.fsum` primitive in
section 7.3. Every CIEDE2000 radian-to-degree conversion routes through the
finite unary `math-degrees` trace operation and its hue-rotation exponential
routes through finite unary `math-exp`; direct `math.degrees`, `math.exp`, or an
untraced algebraic substitute outside those adapters is forbidden in an
authoritative oracle run. The
oracle source path and raw-byte hash are required proposal
source records. Reusing any V1 ID after changing a listed formula, constant,
branch, round trip, or reference vector is forbidden.

For each mode and each metric independently, enumerate selected-row-position
pairs exactly `(0,1),(0,2),...,(0,n-1),(1,2),...,(n-2,n-1)`. Choose the minimum
by `(binary64_value, first_position, second_position)`: exact-equal values use
the lexicographically smallest pair, with no epsilon, `q9`, or display rounding.
Mode order is `normal`, `protan`, `deutan`, `tritan`. The common CIEDE2000
record is chosen by `(minimum_value, mode_rank, pair)`, where normal, protan,
and deutan have ranks 0, 1, and 2. Admission compares raw unrounded values with
`>=`.

After selection, the independent oracle evaluates final quantized hex rows for:

- normal, protan, deutan, and tritan pairwise CIEDE2000 minima;
- common-mode minima;
- parallel `DeltaEOK×100` diagnostics.

V1 has no topology-specific policy or result extension. A use case that needs
one must introduce a new recognized validation-policy ID and a closed tagged
result schema; implementations may not append an ad hoc record to V1 rows.

A new family has no frozen baseline. Before proposal generation, its admission
policy identifier and per-`n` normal/common/tritan floors for `n=2..8` must be
declared. Floors may be chosen from the intended use and reviewed reference
sets, but may not be derived from the candidate after selection. The exact
policy bytes and reference characterization require a tracked registry entry
and completed A/B/maintainer approval before the separate preselection command;
proposal mode accepts only the already sealed entry hash. `n=1`
legitimately has null pairwise metrics.

The strict serialized schema is:

```python
@dataclass(frozen=True, slots=True)
class AdmissionFloorRow:
    n: int
    normal_min_delta_e00: float
    common_min_delta_e00: float
    tritan_min_delta_e00: float

@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    policy_id: str
    floor_rows: tuple[AdmissionFloorRow, ...]
```

The ID is non-empty; every floor is a finite nonnegative non-boolean number;
rows must be in ascending `n` order with exact unique values `2..8`, and
missing/extra rows or fields fail. JSON serializes this tuple as an array of
objects, never an object with integer keys. `common_min_delta_e00` preserves the
accepted oracle definition: the minimum of the independently recorded normal,
protan, and deutan minima, with the exact mode/pair tie rule above. There is no
default policy or inherited floor. The frozen `n=1` record stores null metrics
and does not synthesize a pairwise score.

The historical Octave common/tritan 10/8 criteria are not universal and must
not become defaults.

Admission workflow:

1. author selects a coordinate policy, discrete policy, and predeclared
   admission policy;
2. proposal mode compiles the LUT and selects indices using only OKLab/OKLCH;
3. the independent oracle emits the CIEDE2000/CVD/OKLab report;
4. any failed floor rejects the proposal and writes no generated runtime data;
5. a human reviews the visual comparison and the bounded model diagnostics;
6. acceptance freezes indices, final hex rows, admission metrics, policy IDs,
   and provenance in the SSOT; and
7. future releases apply exact replay plus per-asset non-regression.

## 9. Failure taxonomy

| Condition | Required behavior |
|---|---|
| malformed coordinate, policy, LUT, or `n` | `TypeError` or `ValueError` with the invalid field |
| no strict fixed-Y boundary witness | internal boundary error; no approximate success |
| analytic root exists but scalar Y/gamut or certificate postcondition fails | `RelativeYBoundaryError`; no rounded or endpoint substitution |
| direct interior witness collapses to black/white or positive chroma collapses to its neutral baseline | direct boundary error; no false preserved-coordinate success |
| achromatic/insufficient discrete domain | `DiscreteSelectionError` with counts and policy ID |
| exact selector node budget exhausted | `DiscreteSelectionError`; no fallback |
| frozen family missing an index row | SSOT/build validation error; selector is not invoked |
| independent admission floor failure | normal `GateViolation`, build exit 1, no write |
| ambiguous, multiply claimed, site-unowned, or unresolved module origin | environment-provenance failure; publish no owner/completion envelope |
| target filesystem lacks effective atomic no-replace/replace or file/directory synchronization | fail before an authority transition; no weaker fallback |
| pre-existing immutable final leaf differs, is torn/aliased/wrong-type | fatal and untouched; no repair or overwrite |
| sync/barrier fails after an exact new leaf/tree became visible | fatal for this attempt; retain at most the declared exact resumable prefix, publish no later marker/index, and require full retry revalidation/resynchronization |
| authority marker/index exists without every exact durable prerequisite | corruption; fail rather than heal or infer authority |
| final exact compatibility mismatch | comparison failure, build/release failure |

## 10. Comparison and evidence

Compatibility migration must create the before/after report from the accepted
baseline and current candidate. The accepted baseline plus the strict
comparator artifact are authority; HTML is deterministic presentation, not an
inherited evidence source. Add an explicitly non-shipped authoring section
rather than mixing generic changes into the compatibility mismatch count.

The side-by-side space must show:

- all required exact shipped panels and totals;
- compatibility-probe versus globally certified modeled-relative-Y boundary curves over a documented
  hue/tone grid, labeled as algorithm diagnostics rather than catalog changes;
- direct-OKLCH versus explicit fixed-Y previews for representative new-family
  recipes; and
- proposed discrete candidates, selected rows, and independent validation
  summaries.

Boundary characterization runs exactly as:

```bash
uv run python scripts/characterize_oklab_authoring.py \
  --output-dir \
  build/color-system-comparison/oklab-authoring-characterization
```

Its boundary grid uses every integer hue `0..359` and integer `k=1..19`. For
each `k`, it executes exactly once and in this order
`tone_seed=float(k)/20.0`,
`target_y=(tone_seed * tone_seed) * tone_seed`,
`compatibility_neutral_tone=neutral_tone(tone_seed)`, and
`compatibility_effective_target_y=relative_y_from_tone(compatibility_neutral_tone)`.
The effective target must be bit-identical to `target_y`; the exact retained
seed bits, rather than a cube-root reconstruction, are passed to both shipped
compatibility boundary/render entry points. Endpoints repeat the same sequence
with seeds `0.0` and `1.0`. It additionally records the four compatibility
trace fixtures with `tone_seed=0.5`, hence `target_y=0.125`, at hue
`16,99,238,298`, and compiles the canonical 43×256
catalog twice with only boundary routing changed. The scalar parity grid uses
hue `j/4` for `j=0..1439` and `u=k/1024` for `k=0..1024`, plus every
solver-produced root. The fixed-Y characterization oracle uses
`cartesian-cubic-derivative-isolation-v1`, root width `2**-96`, and the fail-
closed query/result contract in section 5.6. Direct-family proposal comparisons
use the separate `direct-fixed-l-face-isolation-v1` contract from that section;
the two oracle IDs are never interchangeable. `Decimal` is permitted only for
displayed text. Grid order is target, then hue, and all arrays retain that
order.

`changed_map_count` means named rows having at least one unequal index;
`changed_position_count` means unequal `(map_name, index)` pairs. The
scientific payload stores sorted changed names, every mismatch index, row and
aggregate hashes, and every binary64 value as both JSON number and
`float.hex()`. The separate public evidence stores normalized environment
identity and repo-relative script/kernel/recipe/SSOT hashes. Counts and displayed
decimal values are derived from those records and are never script inputs.

The generator writes two different schemas. The reproducible scientific payload
`fixed-y-characterization-payload.json` has exactly these top-level keys:

```text
schema, scalar_kernel_constants, policies, boundary_grid, endpoint_records,
trace_fixtures, scalar_parity, catalog_counterfactual, payload_sha256
```

`schema` is `oklab-fixed-y-characterization-payload-v1`. It contains no command,
worktree fingerprint, execution snapshot/input bundle, full or invocation-
specific environment, source path, or source hash: those facts vary by
invocation and belong to the evidence envelope below. The sole runtime-related
scalar is each recomputation record's normalized
`base_runtime_environment_sha256`; it is a semantic precondition for a bit-
replay PASS, is identical across all records, and must equal both phase
evidence envelopes' accepted base-runtime hash. It carries no host/path or
invocation-specific runtime closure. `scalar_kernel_constants` is exactly the complete two-key
section 5.1 binding and appears once in the payload. `policies` has exactly
`shipped_compatibility`, `relative_y_boundary`, `endpoint_verifier`,
`projective_proof_checker`, and `cartesian_oracle`. The first two are their
complete closed policy records. `endpoint_verifier` has exactly `algorithm_id`,
and `constants_sha256`.
`projective_proof_checker` has exactly `algorithm_id`,
`comparison_refinement_limit`, and `constants_sha256`. `cartesian_oracle` has
exactly `algorithm_id`, `root_interval_width`, `refinement_limit`, and
`constants_sha256`. All three hashes equal
`3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`,
resolve to the one embedded binding through section 5.6's closed registry, and
are independently recomputed. Unknown or omitted fields, per-policy duplicate
records, or a hash without the complete top-level binding fail.

`boundary_grid` has exactly `hue_rule`, `neutral_tone_seed_rule`,
`target_y_rule`, `sample_order`, and `samples`; the four rule strings are the
literal rules above and samples are the interior `k=1..19` points in target-
then-hue order. Each sample has exactly `tone_seed`, `target_y`,
`compatibility_neutral_tone`, `compatibility_effective_target_y`, `hue_deg`,
`compatibility_probe`, `global_boundary`,
`projective_proof_verification`, and `cartesian_oracle_queries`. The
first two and every other binary64 scalar use a record with exactly `number`
and `float_hex`; those two representations must have identical binary64 bits.
`compatibility_probe` has exactly `policy_id`, `probe_chroma`,
`compatibility_neutral_tone`, `compatibility_effective_target_y`,
`solved_oklab_l`, `rendered_chroma`, `raw_linear_srgb`, `encoded_srgb`,
`achieved_relative_y`, and `residual`. Each scalar is a binary64 record and each
RGB value is exactly three such records in red/green/blue order. The policy ID
and probe chroma equal the shipped compatibility policy. The two compatibility
coordinate fields must bit-equal the containing sample, and the generic
boundary's `target_y` must bit-equal
`compatibility_effective_target_y`. No `numpy.cbrt`, decimal reconstruction,
displayed value, or generic target-Y inversion participates. The boundary
record is the complete closed section 5.1 result serialization.
`cartesian_oracle_queries`
is the exact ordered
array required by section 5.6; every element contains one complete closed
`CartesianOracleResult`, including the chroma slice and expected/observed
feasibility. `projective_proof_verification` is the linked exhaustive checker
PASS for that result. RGB records are three-element arrays in red, green, blue
order.

`endpoint_records` contains every `(target_y,hue_deg)` pair for target order
`0.0,1.0` and integer hue order `0..359`. Each record has exactly `target_y`,
`tone_seed`, `compatibility_neutral_tone`,
`compatibility_effective_target_y`, `hue_deg`, `compatibility_probe`,
`global_boundary`, and `endpoint_verification`; the last field is one closed
`EndpointPolicyVerification` linked to that boundary result. Seeds are exactly
`0.0` then `1.0`; construction and all bit-equality rules are identical to an
interior sample. No Cartesian-oracle field is allowed in an endpoint record.

`trace_fixtures` is an array in hue order `16,99,238,298`, each at
`tone_seed=0.5` and `target_y=0.125`, with exactly `accepted_trace_id`,
`tone_seed`, `target_y`, `compatibility_neutral_tone`,
`compatibility_effective_target_y`, `hue_deg`, `compatibility_probe`,
`global_boundary`, `projective_proof_verification`, and
`cartesian_oracle_queries`. The identifier is a non-empty string and the other
fields obey the grid-sample schemas and bit-equality rules; no result field is
implicitly omitted.

`scalar_parity` has exactly `hue_rule`, `u_rule`, `sample_order`,
`grid_record_count`, `grid_records_sha256`, `root_record_count`,
`root_records_sha256`, `root_records`, `max_abs_raw_channel_difference`, and
`max_abs_y_difference`. A parity record has exactly `sample_kind`,
`root_identity`, `hue_deg`, `projective_u`,
`polynomial_raw_linear_srgb`, `scalar_raw_linear_srgb`,
`abs_raw_channel_differences`, `polynomial_relative_y`, `scalar_relative_y`, and
`abs_y_difference`. `sample_kind` is `grid` or `solver-root`; `root_identity`
is null exactly for grid and otherwise has exactly:

```text
production_result_sha256, proof_sha256, root_cluster_ordinal,
coordinate_interval, sources, equality_proof_sha256, root_identity_sha256
```

It is copied from one complete `ProjectiveRootCluster` in the hash-linked
interior production result: ordinal maps to `cluster_ordinal`, all interval,
source, and equality-proof bytes match exactly, and the interval coordinate is
`projective-u`. Its self-hash is SHA-256 of
`b"dartwork-mpl-scalar-parity-root-identity-v1\0"` plus canonical JSON of the
other six fields. A rounded sample coordinate never identifies or merges an
algebraic root.

The canonical grid stream is hue-then-u order under the literal rules; its
count is `1440*1025`, and `grid_records_sha256` uses
`b"dartwork-mpl-scalar-parity-grid-v1\0"` plus the concatenated canonical record
bytes in that order. Emit one root record for each distinct cluster in each
distinct interior production result embedded in `boundary_grid.samples` or
`trace_fixtures`; deduplicate only repeated appearances having the identical
`root_identity_sha256`. Endpoint-policy results contribute none.

For a root record, compute the exact rational midpoint of its certified
interval and choose the nearest finite binary64, ties to even, by exact integer-
ratio distance comparison. That cached value is `projective_u` for both the
polynomial and scalar paths. Distinct roots may therefore share the same
`projective_u.float_hex` and must remain separate records. Sort root records by
`(production_result_sha256,proof_sha256,root_cluster_ordinal)`, reject duplicate
identity hashes, and compute `root_records_sha256` as SHA-256 of
`b"dartwork-mpl-scalar-parity-roots-v1\0"` plus their concatenated canonical
bytes. `root_record_count` is the exact array length. The maxima are recomputed
across both complete streams and use the binary64 record, never a supplied
assertion.

`catalog_counterfactual` has exactly `map_order`, `baseline_policy_id`,
`counterfactual_policy_id`, `baseline_aggregate_sha256`,
`counterfactual_aggregate_sha256`, `changed_map_count`,
`changed_position_count`, and `changed_rows`. `map_order` is the canonical 43-
name order. `changed_rows` is sorted by that order; each record has exactly
`map_name`, `mismatch_indices`, `baseline_row_sha256`, and
`counterfactual_row_sha256`. The counterfactual compiler changes only boundary
routing; recipe input, source SSOT, sampling, quantization, and discrete
selection remain byte-identical inputs. The two counts are recomputed from
`changed_rows` and are never hand-coded assertions.

Each mismatch index is a strictly increasing non-boolean integer in `0..255`.
Row hashes use `b"dartwork-mpl-characterization-row-v1\0"` plus UTF-8 map name,
NUL, and the 256 lowercase hex values joined with NUL in index order. Aggregate
hashes use `b"dartwork-mpl-characterization-catalog-v1\0"` plus the ordered 43
`map_name`, NUL, `row_sha256`, NUL records. Recomputing every row must reproduce
both aggregates, and the changed rows must be exactly the unequal row-hash set;
the mismatch union derives both counts.

`payload_sha256` is SHA-256 of
`b"dartwork-mpl-fixed-y-characterization-payload-v1\0"` followed by canonical
JSON of the complete scientific payload with only `payload_sha256` omitted.
That payload alone occupies the tracked
`docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/fixed-y-characterization.json`
path and is the byte-for-byte reproduction target; copying a displayed summary
is not promotion.

The pre-install candidate run writes
`fixed-y-characterization-generation-evidence.json` last. It has exactly:

```text
schema, characterization_payload_path,
characterization_payload_raw_sha256, characterization_payload_sha256,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot, execution_inputs,
invocation_recipe, environment, source_files, implementation_sources,
generation_phase_manifest, generation_evidence_sha256
```

Its schema is `oklab-fixed-y-characterization-generation-evidence-v1`.
Environment kind is `characterization-generation`; execution inputs have an
empty external bundle and null review-control hash. The generated payload is a
regular non-symlink output file whose raw and semantic hashes reproduce the
strictly parsed candidate. The fingerprints, snapshot, invocation recipe, source files,
and implementation sources obey the same rules below; `invocation_recipe` is
the path-neutral characterization-generation profile and raw command transport
is private. Its self-hash uses
`b"dartwork-mpl-fixed-y-characterization-generation-evidence-v1\0"` plus the
complete envelope with only `generation_evidence_sha256` omitted.

The ignored post-install `fixed-y-characterization-evidence.json` is written
last and has exactly:

```text
schema, characterization_payload_path,
characterization_payload_raw_sha256, characterization_payload_sha256,
tracked_payload_path, tracked_payload_raw_sha256,
source_fingerprint_start, source_fingerprint_end,
source_fingerprint_post_write, execution_snapshot, execution_inputs,
generation_invocation_recipe, verification_invocation_recipe,
generation_environment, verification_environment,
verification_execution_inputs, source_files, implementation_sources,
phase_manifests,
characterization_evidence_sha256
```

Its schema is `oklab-fixed-y-characterization-evidence-v1`. The generated
payload path is relative to the output directory; the tracked path is the exact
repo-relative path above. Both are regular non-symlink files. Their raw-byte
hashes must match, and strict parsing of both must reproduce the same nested
`characterization_payload_sha256`. The three fingerprints use section 10's
seven-field schema and equal one another, the source snapshot, and the current
post-write guard. The top-level `execution_inputs` is the generation phase's
`characterization-generation` record, with no external records.
`generation_invocation_recipe`, generation environment, execution snapshot,
and sorted source files use their closed schemas and cross-link exactly.
`verification_invocation_recipe` and verification environment have kind
`characterization-verification` and bind the verifier's separate
complete `verification_execution_inputs` record, whose self-hash equals the
verification phase-manifest link. Both are complete environment-v3 records and
their `base_runtime_environment_sha256` values must match. Their
invocation-specific project imports, distribution/native closure, arithmetic
trace, complete computation broker-read stream,
`runtime_environment_sha256`, and `environment_sha256` are independently
captured and must not be copied across phases.

`implementation_sources` is a UTF-8-role-sorted array whose records have exactly
`role`, `path`, and `sha256`. Roles are unique non-empty strings, paths are
repo-relative POSIX, and every path/hash occurs exactly once in `source_files`;
it includes the script, construction kernels, compatibility path, proof checker,
both independent oracles, fixtures, recipes/SSOT, and report renderer used by
the run. The evidence self-hash is SHA-256 of
`b"dartwork-mpl-fixed-y-characterization-evidence-v1\0"` plus the complete
canonical envelope with only `characterization_evidence_sha256` omitted.
Evidence bytes are not required to reproduce across invocations.

A phase manifest has exactly `schema`, `phase_id`,
`execution_inputs_sha256`, `declared_source_files`,
`declared_source_files_sha256`, `broker_read_records`,
`broker_read_records_sha256`, and `sealed_output_raw_sha256`.
`schema` is `oklab-fixed-y-characterization-phase-manifest-v1`.
`declared_source_files` is the phase's complete UTF-8-path-sorted array of
exact `path`/`sha256` records and its hash is SHA-256 of
`b"dartwork-mpl-declared-source-files-v1\0"` plus canonical JSON of that array.
For preinstall generation evidence the one `generation_phase_manifest` has
`phase_id="generation"`; the postinstall `phase_manifests` array has exactly
generation then verification. The harness privately verifies that generation
and verification ran in distinct
fresh OS processes, but PID/process-handle values and their hashes are not
public fields.

`broker_read_records` is a byte-identical inline copy of the phase environment's
complete `dependency_discovery.broker_read_records`; its digest equals that
environment's `broker_read_records_sha256`, using the common
`dartwork-mpl-environment-broker-read-records-v1` domain. It therefore retains
the §3.5 dependency-discovery grammar's exact six-key records, global ordinals, repetitions,
interleaving, and all five typed control-handoff/source-snapshot/external-input/
distribution/stdlib ownership variants rather than a source-
only projection. The phase manifest
array length equals the environment count, and strict parsing and all ownership
cross-links must succeed independently in both locations. Hash preimages omit a
newline; the evidence file keeps its one terminal LF.

For every environment profile, not only these phase manifests, the declared-
source array is the UTF-8-path-sorted unique union of exact `path`/`sha256`
records from these six sources and no others:

1. every computation broker record with `root="source-snapshot"`;
2. `python_startup.bootstrap_source`;
3. `control_preparation.base_handoff.preparer.python_startup.bootstrap_source`;
4. `runtime_import_manifest.registry_source` and
   `project_execution_policy.registry_source`;
5. every `required_modules` and `optional_modules` record in the selected
   project-execution policy plus every selected `data_files` record; and
6. every shell record in sealed-package-shell mode.

The union collapses byte-identical repeated paths but rejects one path with two
hashes. Items 2–6 are path/hash cross-linked through startup or
`control_preparation`; an optional policy module remains declared even if this
invocation does not execute it. Shell records are empty for ordinary mode, and
any ordinary initializer execution is both a policy module and an ordinary
computation source read/event. The computation bootstrap has exactly its one
pre-broker read, bound by `python_startup.bootstrap_source`, the native pre-
broker input/module/path records, `source_files`, and the source snapshot. It
never has a computation-broker row. After `broker-ready`, any open, read,
import, reload, or alias request resolving to that bootstrap path or leaf ID is
fatal rather than converted into a repeated source record. The
set of external-root reads equals the phase bundle's required records, while
distribution and stdlib rows equal the same environment's used-distribution
and stdlib ownership partition. These two
characterization phases may write scratch/output files but may not reopen them
as inputs; the verifier receives the sealed generation output only through its
captured external-input bundle. Generation evidence's top-level `source_files`
equals its phase array. Postinstall evidence's top-level array is the sorted
unique union of both phase arrays, and the common execution snapshot binds that
union. Both phase `ExecutionInputs` name that snapshot while their lists narrow
authority. The generation subset and read log exclude the tracked expected
payload path. Its process is the only phase allowed to import
construction, solver, oracle, catalog, and rendering code. After it writes the
candidate, the harness flushes and `fsync`s it, closes its descriptor, seals it
read-only, hashes it, terminates the generator, and captures those sealed bytes
as the verifier's exact `sealed-generated-characterization-payload` external
input.

The verifier starts as a different isolated two-child transaction. Both phase
source subsets contain the two bound startup bootstraps and registry leaves
because those bytes establish the control/computation brokers and closed
execution policies. In shell mode the two captured initializer leaves occur
only as preparer hash-only shell identities; they are never computation reads,
imports, or project events. Beyond those common leaves, the verifier subset
contains only its exact verification entry module/harness/parser plus the
tracked expected payload from the source snapshot; it may not import a
generation, solver, selector, renderer, oracle, ordinary public-API initializer
branch/dependency, color loader/registrar, semantic catalog, font, or Matplotlib
module. It reads only
the sealed external blob and tracked expected file,
checks raw byte identity, strictly parses both, and recomputes the same payload
self-hash. Its `sealed_output_raw_sha256` equals the sealed generator hash.
Both phase manifests with their full preimage arrays, both environment records,
both input records, and every read are hash-bound into the reproduction
evidence. The preinstall/postinstall review subjects carry the real phase input
manifests and blobs; acceptance promotion archives and reparses them, resolves
source reads against the execution-snapshot archive, and resolves external
reads against those phase bundles without consulting the ignored producer tree.
A generator that reads or copies the expected asset therefore cannot produce
valid evidence.

Bootstrap is explicit and create-only:

1. generate an ignored candidate payload, generation evidence, and its real
   zero-record generation input manifest;
2. freeze that complete closure in a
   `fixed-y-characterization-preinstall` subject and obtain sequential fresh
   Reviewer A then Reviewer B PASS on the unchanged preinstall snapshot;
3. promote that complete reviewed closure into the tracked preinstall archive
   and, only after its durable barrier, publish and barrier
   `acceptances/preinstall.json` last;
4. only then install the payload from the archived `candidate-payload` blob at
   the tracked path using `publish_immutable_100644` and the final directory
   barrier (a byte-identical complete existing file is reverified/resynchronized
   as a validated no-op; differing bytes are fatal);
5. capture a new post-install source snapshot, independently regenerate in the
   sealed generation phase, verify in the separate phase above, and publish the
   reproduction evidence plus both real phase input manifests/blobs; and
6. freeze the tracked payload, regenerated payload, reproduction evidence, and
   phase-input closure in a `fixed-y-characterization-postinstall` subject and
   obtain another fresh sequential A→B PASS on that exact snapshot; then
7. promote that complete closure and write `acceptances/postinstall.json` last.

Step 7 likewise barriers every postinstall archive prerequisite before
publishing and barriering its acceptance. No acceptance, payload, or truth
marker may survive durably without all earlier phase prerequisites.

Only the two completed tracked acceptances described below support a normative
quantitative claim.
Any preinstall finding is fixed in ignored output before installation and
restarts at A. Any postinstall finding also resets to A; if its remedy changes
scientific bytes, the installed identity is abandoned and a new schema/versioned
asset path begins again at step 1—existing create-only bytes are never replaced
or deleted. Invocation provenance may change without changing scientific bytes,
but every accepted reproduction must still prove exact byte identity.

Neither ignored A/B pair is durable acceptance by itself. Each stage is
promoted create-only into this tracked review archive:

```text
docs/superpowers/specs/assets/2026-07-27-oklab-authoring-extension/
  fixed-y-review-v1/
    acceptances/
      preinstall.json
      postinstall.json
    archive/
      subjects/<subject_manifest_sha256>/manifest.json
      reports/<reviewer_report_sha256>.json
      input-bundles/<external_input_bundle_sha256>/manifest.json
      input-bundles/<external_input_bundle_sha256>/blobs/<raw_sha256>
      review-controls/<review_control_bundle_sha256>/manifest.json
      review-controls/<review_control_bundle_sha256>/blobs/<raw_sha256>
      review-evidence/<review_evidence_bundle_sha256>/manifest.json
      review-evidence/<review_evidence_bundle_sha256>/blobs/<raw_sha256>
      execution-snapshots/<execution_snapshot_archive_sha256>/manifest.json
      execution-snapshots/<execution_snapshot_archive_sha256>/blobs/<raw_sha256>
```

An execution-snapshot archive manifest has exactly `schema`,
`execution_snapshot_sha256`, `git_object_representation_id`,
`git_index_representation_id`, `records`, and
`execution_snapshot_archive_sha256`; schema is
`oklab-authoring-execution-snapshot-archive-v1` and the representation is
`git-loose-zlib-stored-v1`; the index representation is
`git-index-v2-zero-stat-extension-free-v1`. Its directory is keyed by its own archive self-hash,
while that self-hash uses
`b"dartwork-mpl-oklab-authoring-execution-snapshot-archive-v1\0"` plus
canonical JSON with only `execution_snapshot_archive_sha256` omitted. Every
tracked leaf is a regular stage-0 Git blob with Git mode `100644`; executable
mode, symlink mode, nonzero stage, extra path, or alternate manifest name fails.
Git does not store directory modes, and checkout write bits, ACLs, ownership,
timestamps, and umask do not participate in archive identity.

Publication constructs the canonical manifest/blobs in private same-filesystem
staging, computes the archive self-hash, publishes every `blobs/*` leaf with
section 3.5's atomic no-replace primitive, crosses the complete bottom-up
durability barrier, then publishes and barriers `manifest.json` as the sole
completion marker. Directory existence has no authority. An exact blob subset
without a manifest is resumable; a manifest with any missing/differing blob is
fatal. Existing byte-identical complete bytes are reverified/resynchronized as
an idempotent no-op; any difference at that hash path is a collision failure. A snapshot-keyed
directory is invalid. Both representation IDs and their canonical encoders
make repeated capture of one V1 snapshot produce the same archive hash, path,
manifest, and blob set.

Each record has exactly `role`, `logical_path_hex`, `file_type`, `git_mode`,
`byte_count`, `raw_sha256`, and `blob_path`; file type is `regular` or
`symlink`, git mode is `100644`, `100755`, or `120000`, a symlink blob contains its
raw target bytes, and blob path is exactly `blobs/<raw_sha256>`. Logical paths
are raw-byte hex because valid Git paths need not be safe UTF-8. These singleton
roles occur exactly once:

```text
execution-snapshot-manifest
git-capsule-manifest
git-tool-manifest
git-operational-config
git-argv-policy
declared-source-files
source-fingerprint-status-records
source-fingerprint-untracked-path-records
source-fingerprint-untracked-blob-records
source-fingerprint-index-manifest-records
source-fingerprint-index-patch
source-fingerprint-worktree-patch
source-fingerprint-raw-worktree-records
head-tree-manifest-records
snapshot-root-manifest-records
```

In that same order, their `logical_path_hex` values are the lowercase hex of
these exact UTF-8 byte paths:

```text
preimages/execution-snapshot-manifest.json
preimages/git-capsule-manifest.json
preimages/git-tool-manifest.json
preimages/git-operational-config.json
preimages/git-argv-policy.json
preimages/declared-source-files.json
preimages/source-fingerprint/status-records.bin
preimages/source-fingerprint/untracked-path-records.bin
preimages/source-fingerprint/untracked-blob-records.bin
preimages/source-fingerprint/index-manifest-records.bin
preimages/source-fingerprint/index.patch
preimages/source-fingerprint/worktree.patch
preimages/source-fingerprint/raw-worktree-records.bin
preimages/head-tree-manifest-records.bin
preimages/snapshot-root-manifest-records.bin
```

Every singleton is `file_type="regular"`, `git_mode="100644"`, and stores the
exact canonical byte preimage used by section 10's formula; a JSON preimage
includes exactly one terminal LF. The singleton records are followed by one
`capsule-file` record for every regular file or symlink in the closed capsule.
Its logical path is lowercase hex of `b"capsule/" + raw_capsule_relative_path`,
and capsule records are sorted by raw logical-path bytes. Git metadata, refs,
index, config, and loose-object files use logical `git_mode="100644"`; worktree
records preserve their source `100644`/`100755`/`120000` mode. No directory
receives a record; its existence derives from the closed path set. The tracked
blob representing a symlink target remains an ordinary Git-`100644` archive
leaf. Blobs deduplicate by raw hash. For detached verification, materialize
these records into a private ignored capsule with physical directories `0555`,
logical `100644` files as `0444`, logical `100755` files as `0555`, and logical
`120000` records as symlinks. Those physical permissions harden execution but
are not tracked identity. The archive
forbids report, sequence, walkthrough, acceptance, and promotion-snapshot
hashes. Source/capsule bytes independently produce both the canonical archive
hash and the A/B report sequence; those sibling hashes then enter the
walkthrough and acceptance. No report points backward to the archive.

Only the synthetic canonical `capsule/git/config` defined below is a capsule
file. Raw common/worktree Git config bytes, their hashes or byte counts,
`config.worktree`, the old `git-effective-config` singleton, and serialized
remote/branch names or values are forbidden from the durable archive. Live raw
config is transient validation input, not publishable provenance.

Each acceptance file has exactly:

```text
schema, review_kind, subject_id, subject_manifest_sha256,
characterization_payload_raw_sha256, characterization_payload_sha256,
reviewer_a_report_sha256, reviewer_b_report_sha256,
reviewer_a_external_input_bundle_sha256,
reviewer_b_external_input_bundle_sha256,
reviewer_a_execution_inputs_sha256, reviewer_b_execution_inputs_sha256,
reviewer_a_control_bundle_sha256, reviewer_b_control_bundle_sha256,
reviewer_a_evidence_bundle_sha256, reviewer_b_evidence_bundle_sha256,
review_sequence_sha256, reviewed_source_fingerprint,
reviewed_execution_snapshot_sha256,
reviewed_execution_snapshot_archive_sha256,
archive_promotion_provenance, maintainer_approval, acceptance_sha256
```

Its schema is `oklab-fixed-y-characterization-review-acceptance-v1`;
`review_kind` is exactly `fixed-y-characterization-preinstall` or
`fixed-y-characterization-postinstall` and must match the canonical filename.
Every hash is reparsed from the archived subject, reports, historical external-
input bundles, controls, evidence, and sequence—not copied from an unchecked
string. `maintainer_approval` has exactly `approval_ref`,
`walkthrough_subject_sha256`, `review_sequence_sha256`, and
`independence_attested`; its sequence equals the record and independence is
Boolean true, and its approval reference matches the same harness-generated
`maintainer-approval-[0-9a-f]{32}` grammar. Define the walkthrough hash as:

```text
SHA256(
    b"dartwork-mpl-fixed-y-characterization-review-walkthrough-v1\0" +
    canonical_json({
        "review_kind": review_kind,
        "subject_id": subject_id,
        "subject_manifest_sha256": subject_manifest_sha256,
        "characterization_payload_raw_sha256":
            characterization_payload_raw_sha256,
        "characterization_payload_sha256":
            characterization_payload_sha256,
        "reviewer_a_report_sha256": reviewer_a_report_sha256,
        "reviewer_b_report_sha256": reviewer_b_report_sha256,
        "review_sequence_sha256": review_sequence_sha256,
        "common_execution_snapshot_sha256":
            reviewed_execution_snapshot_sha256,
        "common_execution_snapshot_archive_sha256":
            reviewed_execution_snapshot_archive_sha256,
    })
)
```

`acceptance_sha256` is SHA-256 of
`b"dartwork-mpl-oklab-fixed-y-characterization-review-acceptance-v1\0"` plus
canonical JSON with only that field omitted. The acceptance hash is
deliberately absent from the walkthrough preimage.

Acceptance promotion uses section 3.5's closed
`archive_promotion_provenance`, with kind matching the acceptance filename. Its
promotion bundle contains the complete role closure and canonical approval
blob; its tracked path is exactly this archive's
`input-bundles/<external_input_bundle_sha256>/manifest.json`, and its full
`ExecutionInputs` has null control and the reviewed common snapshot. The
approval raw hash/value must equal the surrounding object.

Acceptance promotion strictly resolves the snapshot archive only at
`execution-snapshots/<reviewed_execution_snapshot_archive_sha256>/manifest.json`,
requires its nested snapshot hash to equal
`reviewed_execution_snapshot_sha256`, validates both representation IDs and
the canonical index hash,
record cardinality/order/logical Git modes/blobs/self-hash, and recomputes the complete historical
hash DAG without consulting the current worktree. It reparses the execution
snapshot, Git capsule/tool/operational-config/argv policy, publication
eligibility proof, and source-file
records; recomputes HEAD/index/root manifests, both patch hashes, raw-worktree
and tracked hashes, status count/hash, untracked path/blob hashes, all seven
fingerprint fields, and the execution snapshot; validates every capsule
HEAD/ref/object/index/synthetic-config/worktree byte, mode, and symlink target; and
requires the result to equal the subject, both scopes/reports/ExecutionInputs,
review sequence, and acceptance. It also requires B's embedded historical A
input/control/evidence/token copies to be byte-identical to the independently
archived A closure.

For every archived environment owner, offline verification also reconstructs
the exact selected-artifact projection from the complete embedded
`runtime_distributions` rows, recomputes its domain-separated hash, then
recomputes each used-distribution, runtime, environment, and enclosing hash in
dependency order. For a policy entry, it first resolves the unique
`policy-characterization-verification-evidence` record in the archived
Reviewer-A input manifest, checks its raw/semantic hashes against the entry,
both reports/scopes, and walkthrough, and treats that evidence as the exact
  environment owner rather than inventing an archive-promotion environment. It
  strict-parses the complete inline computation
`dependency_discovery.broker_read_records`, requires contiguous ordinals and
the exact handoff/source/external/distribution/stdlib tagged variants, validates every
source snapshot, external bundle, used-distribution/trigger, stdlib, and phase-
manifest cross-link, and recomputes its count, domain-separated digest, runtime
hash, environment hash, and enclosing owners. It also slices at the retained
base-ready boundary, recomputes the inline base-prefix count/digest and common
base hash, and rejects a hash without that inline prefix. Repetition and interleaving remain
observable after the private broker ledger is destroyed; an ordinal without
the retained record preimage is invalid. It then strict-parses the complete
computation `python_startup` and the complete control-preparation/base-handoff/
preparer startup and runtime-import manifest, recomputes each
argv/input/module/path-stage/tree/closure count and digest, validates the optional
zero-member `stdlib_archive` byte-count/hash binding, and proves every bootstrap,
stdlib, finder/hook, source-file, and dependency cross-link. It strict-parses
`control_policy_id`, `package_dispatch`, and project-execution policy/event
records, cross-links dispatch mode and entry module to the invocation recipe/
profile, and recomputes the project-policy/event/import count/hash chain. In
shell mode it requires the two initializer records in `source_files` and the
control invocation handoff in exact root-then-`_colors` order while requiring
zero computation read/event/import for either body; in ordinary mode shell
records are empty and any initializer execution is an ordinary policy/event
row. It rejects a shell-mode claim for any ordinary registry row and recomputes the
complete `dependency_discovery.module_records` array/count/domain hash. Every
base module row must be a byte-identical retained subset; every manifest-backed
stdlib/distribution row must match its binding, broker receipt, used-file row,
and native mapping; every project row must match its event/source/import; and
the only new fileless rows are the exact shell or `scripts` namespace exception.
It recomputes the complete retained module-guard transition array/count/domain
hash, resolves every authority index against the manifest, reviewed project
policy, shell records, or sole namespace record, and requires exact occurrence
order and one transition for every successful post-base logical module
authorization completion, after the stock success tail for an ordinary import. It
also requires the final-module triplet to equal the retained
`FinalRuntimeClosureTransferV1` projection and rejects a missing preimage,
transient-fileless-guard capability, unknown origin kind, or shallowly rehashed
owner. It validates every manifest module's exact loader, origin/file, explicit
source/sourceless present-cache and extension null-spec/absent-module-cache rule,
package fields, immutable path
sequence, and protected-metadata guard transitions. It then recomputes the
base/runtime/environment/enclosing
hashes that bind those public consequences. It does not claim to recreate the
destroyed private request/platform/control ledger; historical singleton-read
occurrence is the narrower supervisor-attested claim, while the retained
recipe, dispatch, platform, and ownership records are its offline-checkable
typed outputs. It then locates
the complete inline `arithmetic_trace.records` array through the environment-
owner table, validates every operation/shape/canonical float string, recomputes
`record_count`, `records_sha256`, the complete environment hash, and the
enclosing completion/archive hashes. A hash-only startup, broker-read stream,
distribution, or arithmetic trace without its public preimage is invalid. No
raw `uv.lock`, complete package entry, installer receipt, selected-archive
locator, cache metadata, URL, filename, or any hash of those excluded private
values is an archive role. If a tracked lock file independently occurs in the
ordinary Git/source capsule, that does not authorize its raw bytes or digest as
environment identity. The verifier also strict-parses every complete
`native_execution` mapping record, recomputes its count/order/hash, proves the
exact role-to-mapping links and the complete base stdlib/module/dependency/
mapping closures, and then recomputes the
runtime/environment cascade. A physical capsule manifest, leaf path map,
retained descriptor, inode/address witness, namespace transaction, or a hash of
unused capsule contents is not an archive role.

Historical verification proves the archived public DAG and review acceptance;
it does not claim to preserve or replay the destroyed private installer or
native-capsule transaction. Once the process and private witness are gone, it
cannot independently re-prove the historical kernel inode-to-VM association.
That fact is admitted only through the captured public mapping projection, its
content leaves, the unchanged-snapshot A/B evidence, the hash-bound VM-policy/
supervisor capability, and the live continuous guards required at production
time. Offline verification does not claim to replay the destroyed ptrace/
seccomp stops, subordinate-ID or namespace leases, descriptor/mount closure,
post-exec dumpability transaction, or private VM ledger. It likewise strict-parses
each archived
scalar-kernel constants binding, checks its complete 4,121-byte canonical
preimage and golden digest, and follows every endpoint, projective, Cartesian,
and direct-oracle reference to that binding before recomputing outer scientific
hashes.

This reconstructs the historical public hash preimages; it does not claim
portable re-execution of the historical OS Git binary, private provisioning
transport, privileged supervisor, OS mapping transaction, or the private
terminal-output manifest. Its public authority for that handoff is the exact
policy/supervisor identity plus the primary's independently rehashed complete
ordinary-output references, never an invented archived manifest hash.

Acceptance promotion validates the unchanged reviewed closure, including both
phase input manifests/blobs and the promotion's canonical approval; copies its
subject, reports, every input/control/evidence manifest/blob, its own promotion
bundle, and the one common snapshot archive; and rehashes the tracked copies.
It constructs the nested promotion provenance and writes the stage acceptance
last, only after the tracked archive passes its durable prerequisite barrier;
the acceptance then passes its own barrier. For preinstall, installation reads `candidate-payload` only
from the archived input-bundle blob bound by `preinstall.json`, never from the
live ignored producer path. For postinstall, a normative claim requires both
acceptances and requires their raw and semantic payload hashes to equal one
another and the tracked scientific payload. Archive and acceptance paths are
create-only under section 3.5's shared publication contract; byte-identical
repetition is reverified/resynchronized as a no-op and differing bytes are
fatal.

Machine-readable evidence records:

- policy IDs and all numeric policy fields;
- boundary witnesses and maximum error bounds;
- selected indices and objective diagnostics;
- admission floors and raw oracle results;
- hashes for the comparator, construction kernels, validation oracle, fixtures,
  and report renderer in the invocation evidence; and
- the complete candidate worktree fingerprint in that evidence, not in the
  reproducible scientific payload.

The canonical source fingerprint is a closed seven-field record in this exact
order: `head_sha`, `entry_count`, `status_sha`, `tracked_sha`,
`untracked_paths_sha`, `untracked_blobs_sha`, and `combined_sha`. It is produced
by a Python byte-mode helper, not shell command substitution: shell variables
cannot preserve NUL, and line-delimited path hashing is not valid for arbitrary
Git paths. Let `H(bytes)` be lowercase hexadecimal SHA-256 and `NUL=b"\0"`.

Resolve one absolute Git executable before capture and invoke it only as
`<absolute-git> --no-replace-objects -C <resolved-root> ...`. Its subprocess
environment discards every inherited variable and contains exactly `LC_ALL=C`,
`LANG=C`, `GIT_OPTIONAL_LOCKS=0`, `GIT_CONFIG_NOSYSTEM=1`,
`GIT_CONFIG_SYSTEM=<os.devnull>`, `GIT_CONFIG_GLOBAL=<os.devnull>`,
`GIT_ATTR_NOSYSTEM=1`, `GIT_NO_REPLACE_OBJECTS=1`, and `HOME`,
`XDG_CONFIG_HOME`, and `TMPDIR` pointing to one freshly created empty private
directory. It supplies no `PATH`, loader, object-directory, worktree, diff,
index, Python, or extra `GIT_*` variable. Snapshot verification alone may set
`GIT_INDEX_FILE` to the canonical read-only index and names that exception
in the tool manifest.

Every invocation also carries exactly these config overrides:

```text
-c core.quotePath=true
-c core.autocrlf=false
-c core.safecrlf=false
-c core.fileMode=true
-c core.symlinks=true
-c core.ignoreCase=false
-c core.precomposeUnicode=false
-c core.attributesFile=<os.devnull>
-c core.excludesFile=<os.devnull>
-c core.fsmonitor=false
-c core.untrackedCache=false
-c diff.algorithm=myers
-c diff.indentHeuristic=false
-c diff.renames=false
-c diff.interHunkContext=0
-c diff.suppressBlankEmpty=false
-c status.renames=false
```

Before any object resolution, require `for-each-ref refs/replace/` to be empty
and reject `.git/info/grafts`, a linked-worktree equivalent, or a non-empty
replacement namespace. Both the environment variable and global option remain
mandatory even after that rejection.

Read `<common-git-dir>/config` and, only when the extension enables it,
`<git-dir>/config.worktree` transiently under the same no-follow regular-file
before/after identity guard as source bytes. Includes, conditional includes,
stdin/blob origins, symlinks, and every origin other than those files or the
fixed command-line overrides fail. Raw config bytes, byte counts, hashes,
comments, subsection names, and values remain in private process memory only;
they must not enter a manifest, log, diagnostic, capsule, archive, or tracked
Git object. A failure reports only a closed reason ID and origin role, never raw
path or value bytes.

Parse `git config --null --show-origin --show-scope --list` as repeated raw
`scope NUL origin NUL key LF value NUL` records, requiring the terminal NUL and
splitting key/value only at the first LF. Live config is admitted only when
local/worktree keys decode as ASCII and are one of
`core.repositoryformatversion`, `core.filemode`, `core.bare`,
`core.logallrefupdates`, `core.ignorecase`, `core.precomposeunicode`,
`extensions.objectformat`, or `extensions.worktreeconfig`, or match exactly
`remote.<nonempty>.{url,pushurl,fetch}` or
`branch.<nonempty>.{remote,merge,rebase,vscode-merge-base}`. Dots in a
non-empty subsection are data and do not relax the terminal field match.
`core.bare` must parse false. Live repository format is `0` or `1`; SHA-256
requires format `1` plus exactly `extensions.objectformat=sha256`, SHA-1
forbids that extension, and worktree-config presence must agree with its
Boolean extension. The verified storage object format must agree with that
live parse. Command-scope keys must equal the ordered fixed `-c` sequence.
Every other key or origin fails, including aliases, includes, hooks, filters,
attributes, excludes, alternate/object directories, promisor/partial-clone
state, diff drivers, and command options.

Remote and branch entries are admitted only so normal local repository metadata
does not block capture. Registered operations never use them, and their names,
values, multiplicity, ordering, and raw hashes are deliberately discarded.
Comments and insignificant formatting are discarded as well. Credential-like
string detection is not a security boundary: even a URL with user information,
query secrets, an SSH target, or a file URL can never reach durable bytes.

Instead, serialize one closed operational projection with exactly `schema`,
`object_format`, `capsule_repository_format_version`, `bare`,
`canonical_config_raw_sha256`, `argv_policy_sha256`, and
`operational_config_sha256`. Its schema is
`dartwork-mpl-git-operational-config-v1`; object format is `sha1` or `sha256`,
repository format is respectively integer `0` or `1`, and `bare` is false. The
canonical capsule config bytes `C` are exactly:

```python
# SHA-1 repository
b"[core]\n\trepositoryformatversion = 0\n\tbare = false\n"

# SHA-256 repository
b"[core]\n\trepositoryformatversion = 1\n\tbare = false\n" \
b"[extensions]\n\tobjectformat = sha256\n"
```

`canonical_config_raw_sha256` is `H(C)` and `argv_policy_sha256` is the
independently recomputed closed policy below. Define
`operational_config_sha256` as SHA-256 of
`b"dartwork-mpl-git-operational-config-v1\0"` plus canonical JSON with only
that field omitted. The live and detached `config-dump` operations compare
this operational projection, not raw stdout or entry arrays. Consequently a
comment or remote/branch metadata change is intentionally identity-neutral;
an object-format, repository-format, bare-state, argv-policy, or canonical
config-byte change is not. The capsule always contains exactly `C` at
`git/config` and forbids `git/config.worktree`.

This correction retains the draft V1/V2 outer identifiers because, at
acceptance, no truth/fixed-Y snapshot archive or producer fixture existed
outside the design documents. If any old-format artifact has escaped this
worktree, implementations must instead bump the entire unsafe chain together:
Git tool V3, Git capsule V3, source fingerprint V3, execution snapshot V2,
snapshot archive V2, fixed-Y/truth acceptance V2, and both tracked review roots
to V2. A partial bump that can admit an old raw-config archive is forbidden.

The same in-place-draft rule applies to environment-v3 and the newly closed
Python-startup, arithmetic-trace, and terminal-output-set contracts: at
acceptance, no authoritative artifact existed under those identifiers.
Discovery of an escaped artifact requires one coordinated version closure. It
begins with the scalar-kernel constants; selected-artifact and complete
used-distribution projections; environment and base/runtime/full hashes;
Python startup/argv/pre-broker/path-stage domains; arithmetic-trace schema and
14-row operation/shape/call set and domain; dependency-discovery, private-
control process-split/transfer policy, both startup and handoff schemas, sealed-
wheel parser/provisioning/witness and private computation-input inventory,
runtime-import manifest/module-binding tree, package-dispatch/project-execution
registry/policy/event/namespace/import contract, receipt and sticky module-table
capabilities, computation broker-read array/count/domain, complete base/final
module-closure and base/final closure-transfer domains, complete base-closure
and prefix domains, and every phase-manifest/
ownership-trigger cross-link;
native-execution, seal, VM, credential-policy, supervisor,
launch-environment, mapping, and vDSO domains and capabilities; and the
terminal-handoff policy, manifest, output profiles, and output capabilities.
It continues through every affected scientific payload, validation-oracle
truth/result, comparison, policy-characterization and verification-evidence
record, policy-review external-input/control/evidence bundle, scope,
walkthrough, report and completion domain, policy entry, tool identity,
fingerprint, Git capsule/config/argv policy, execution snapshot and archive,
proposal, frozen artifact, review root, acceptance, and tracked archive owner.
All raw/semantic cross-links and transitive enclosing owners receive their
corresponding new versions; mixing any old subordinate domain with a corrected
outer owner, or retaining an old outer owner around a corrected subordinate, is
forbidden.

The closed argv-policy object has exactly `schema`, `live_prefix`,
`detached_prefix`, `config_overrides`, `environment_overrides`,
`operations`, and `snapshot_index_override_policy`, with schema
`dartwork-mpl-git-argv-policy-v2`. An argument token is exactly either
`{"kind":"literal","value_hex":<raw token bytes>}` or
`{"kind":"operand","name":<recognized name>}`. Recognized operand names are
`repository-root`, `git-dir`, `work-tree`, `captured-index`, `devnull`, `oid`,
`raw-path-list`. Config overrides have exactly `key` and `value` token in
the order printed above. `live_prefix` expands exactly to
`[--no-replace-objects,-C,<repository-root>]`; `detached_prefix` expands
exactly to
`[--no-replace-objects,--git-dir,<git-dir>,--work-tree,<work-tree>]`.
`environment_overrides` is the exact mode-ordered array
`[{"mode":"live","set":[]},{"mode":"detached","set":[{"name":"GIT_INDEX_FILE","value":<captured-index>}]}]`;
there is no other environment addition. `<...>` in this paragraph and table is
expository shorthand for the operand token above; every other displayed token
becomes a literal token containing its exact ASCII bytes.

Each operation record has exactly `operation_id`, `suffix`,
`operand_cardinality`, and `stdin_policy`. Cardinality is a canonical object
from used operand name to its exact positive non-Boolean count, or `{}`;
stdin policy is `none` except the one stated row. The complete operation
registry, in this exact order, is:

| Operation ID | Exact suffix token array | Cardinality / stdin |
|---|---|---|
| `version` | `[--version]` | `{}` / none |
| `object-format` | `[rev-parse,--show-object-format=storage]` | `{}` / none |
| `common-git-dir` | `[rev-parse,--git-common-dir]` | `{}` / none |
| `git-dir` | `[rev-parse,--git-dir]` | `{}` / none |
| `config-dump` | `[config,--null,--show-origin,--show-scope,--list]` | `{}` / none |
| `replace-refs` | `[for-each-ref,refs/replace/]` | `{}` / none |
| `head-commit` | `[rev-parse,--verify,HEAD^{commit}]` | `{}` / none |
| `head-tree` | `[rev-parse,--verify,HEAD^{tree}]` | `{}` / none |
| `status` | `[status,--porcelain=v1,-z,--untracked-files=all,--ignore-submodules=none,--no-renames,--]` | `{}` / none |
| `untracked-standard` | `[ls-files,-z,--others,--exclude-standard,--full-name,--]` | `{}` / none |
| `untracked-gitignore-only` | `[ls-files,-z,--others,--exclude-per-directory=.gitignore,--full-name,--]` | `{}` / none |
| `flags-v` | `[ls-files,-v,-z,--full-name,--]` | `{}` / none |
| `flags-f` | `[ls-files,-f,-z,--full-name,--]` | `{}` / none |
| `stage` | `[ls-files,--stage,--abbrev=64,-z,--full-name,--]` | `{}` / none |
| `ita-visible` | `[diff,--cached,--raw,-z,HEAD,--full-index,--abbrev=64,--no-renames,--no-ext-diff,--no-textconv,--ignore-submodules=none,--ita-visible-in-index,--]` | `{}` / none |
| `ita-invisible` | same as `ita-visible` with only `--ita-invisible-in-index` substituted | `{}` / none |
| `check-attributes` | `[check-attr,-z,--stdin,filter,working-tree-encoding,text,eol]` | `{"raw-path-list":1}` / `raw-path-list-nul-v1` |
| `cat-commit` | `[cat-file,commit,<oid>]` | `{"oid":1}` / none |
| `cat-tree` | `[cat-file,tree,<oid>]` | `{"oid":1}` / none |
| `cat-blob` | `[cat-file,blob,<oid>]` | `{"oid":1}` / none |
| `diff-index` | `[diff,--cached,HEAD,<PATCH_OPTIONS>,--]` | `{"devnull":1}` / none |
| `diff-worktree` | `[diff,<PATCH_OPTIONS>,--]` | `{"devnull":1}` / none |

`PATCH_OPTIONS` is not serialized as a macro: during canonical policy
construction it is replaced in place by exactly
`[--binary,--full-index,--no-ext-diff,--no-textconv,--no-color,--no-renames,--no-relative,--default-prefix,--line-prefix=,--unified=3,--inter-hunk-context=0,--diff-algorithm=myers,--no-indent-heuristic,-O,<devnull>,--ignore-submodules=none,--submodule=short,--ita-visible-in-index,--ws-error-highlight=none,--output-indicator-new=+,--output-indicator-old=-,--output-indicator-context= ]`;
the final context-indicator token ends in one ASCII space. Likewise the
`ita-invisible` row is serialized as its fully expanded token array, not the
words “same as”. The raw path list is sent as sorted path plus NUL records and
never appears in argv.

Actual argv is exactly the absolute Git executable, the selected mode prefix,
each ordered pair of tokens `-c`, `key=value` (with the `devnull` value
substituted before concatenation), then one fully expanded registered suffix.
There is no optional `--` or trailing operand beyond the array. A token,
operand count, stdin byte, environment override, or operation not represented
above fails. Live and detached filesystem locations occupy operand tokens and
are not path bytes in the policy. `argv_policy_sha256` is SHA-256 of
`b"dartwork-mpl-git-argv-policy-v2\0"` plus the complete canonical policy.

Record a closed `git_tool_manifest` with exactly `executable_role`,
`executable_sha256`, `version`, `object_format`,
`operational_config_sha256`, `canonical_config_raw_sha256`,
`argv_policy_sha256`, and
`live_index_resolution_policy`, `git_index_representation_id`, and
`snapshot_index_override_policy`. `executable_role` is the literal `git`;
the resolved absolute executable path is private collection state and is never
serialized or hashed into public evidence. Version is exact `git version`
stdout without its terminal newline, and object format is the verified
`rev-parse --show-object-format=storage` value. Both config hashes equal the
strict operational projection above; no raw live config hash or source record
is permitted. Any live entry outside the closed origin/key/override rules is
rejected rather than recorded.
`live_index_resolution_policy` is the literal
`resolve-link-ignore-optional-reject-sparse-v1` and
`git_index_representation_id` is
`git-index-v2-zero-stat-extension-free-v1`.
`snapshot_index_override_policy` is the literal
`canonical-read-only-index-only-v1`; live capture has no override and detached
verification must use the canonical index derived from the resolved stage-0
state, never a byte-identical copy of a live index file. Hash the complete
manifest with `b"dartwork-mpl-git-tool-v2\0"` to obtain
`git_tool_manifest_sha256`.

Derive the fields as follows, sorting path and status records by raw bytes:

```text
head_sha = verified output of `rev-parse --verify HEAD^{commit}`

S = raw NUL-delimited records from:
    status --porcelain=v1 -z --untracked-files=all
           --ignore-submodules=none --no-renames --
entry_count = len(S)
status_sha = H(concat(record + NUL for record in sorted(S)))

P = raw NUL-delimited paths from:
    ls-files -z --others --exclude-standard --full-name --
untracked_paths_sha = H(concat(path + NUL for path in sorted(P)))

untracked_blobs_sha = H(concat(
    path + NUL + git_mode(path) + NUL + H(blob_bytes(path)).encode("ascii") + NUL
    for path in sorted(P)
))
```

`git_mode(path)` is ASCII `100644` or `100755` for a regular file according to
its executable bits, and `120000` for a symlink. `blob_bytes(path)` is the raw
regular-file content or raw link-target bytes, opened with no symlink following;
the helper rejects a file whose type, identity, size, or timestamps change
during capture. It therefore uses SHA-256 of source bytes directly rather than
nesting the repository's possibly SHA-1 Git object ID. The helper rejects any
other untracked filesystem kind, duplicate record, missing terminal NUL,
malformed porcelain prefix, unmerged index, or gitlink/submodule. The `??`
paths in `S` must equal `P`. A second untracked enumeration using only
`--exclude-per-directory=.gitignore` must equal `P`; otherwise machine-local
ignore state affected the result and fingerprinting fails. Effective
`.git/info/attributes` content is likewise rejected. `git ls-files -v -z`
and `git ls-files -f -z` must report the ordinary uppercase cached `H` tag for
every index path; assume-unchanged, skip-worktree, sparse, fsmonitor-valid, or
other exceptional state fails. Intent-to-add is checked separately: raw
`diff --cached --raw -z HEAD --` output under
`--full-index --abbrev=64 --no-renames --no-ext-diff --no-textconv
--ignore-submodules=none --ita-visible-in-index` must equal a second invocation
with only the ITA option changed to `--ita-invisible-in-index`. A difference is
an ITA marker and fails; `H` alone is not treated as proof of its absence.

The live index is semantic input, not a publishable byte artifact. Under
`resolve-link-ignore-optional-reject-sparse-v1`, open the resolved index and
any one referenced shared-index file with no-follow before/after identity and
checksum guards. Parse index versions 2 through 4, verify the repository-format
SHA-1/SHA-256 trailer, expand v4 path compression, and reconstruct the complete
stage-0 entry set. A split index may contain exactly one `link` extension; its
delete/replace bitmaps are applied to one guarded shared-index base. A nested
`link`, missing/shared checksum disagreement, or more than one shared layer
fails. The raw index, shared-index name/path/bytes/hash, stat cache, extension
order, and optional-extension payloads remain private and are neither archived
nor named by public evidence.

An uppercase extension signature is optional/nonsemantic and may be ignored
only after its length and index trailer have been validated. An unknown
lowercase mandatory extension, `sdir`, sparse-directory entry, nonzero stage,
intent-to-add, assume-valid, extended/skip-worktree/fsmonitor flag, gitlink,
illegal mode, duplicate path, or malformed padding/bitmap/path fails. Resolve
the semantic entries independently of `git ls-files`, then cross-check their
raw paths, modes, stages, and full object IDs against the registered `stage`,
`flags-v`, `flags-f`, and ITA views. Semantically identical full, split,
stat-refreshed, or optional-extension indexes must therefore resolve to the
same public state.

Independently parse raw NUL records from
`ls-files --stage --abbrev=64 -z --full-name --`. Each must contain an allowed
mode `100644`, `100755`, or `120000`, a full object ID of the recorded object
format, stage exactly zero, and one raw path. Duplicate paths, other stages,
gitlinks, or malformed records fail. Read every named index blob with
`cat-file blob <oid>` under the same no-replace policy and compute raw SHA-256.
The canonical index record is:

```text
path + NUL + mode + NUL + b"0" + NUL +
object_format + NUL + oid + NUL + raw_blob_sha256 + NUL
```

Sort by raw path and define `index_manifest_sha256` as SHA-256 of
`b"dartwork-mpl-index-manifest-v1\0"` plus their concatenation. This directly
binds stage, mode, Git identity, and source bytes even in a SHA-1 repository.

From that resolved stage-0 array build the sole archived index representation,
`git-index-v2-zero-stat-extension-free-v1`. Let `h` be 20 bytes for SHA-1 and
32 bytes for SHA-256. Emit, in raw-path `memcmp` order:

```text
b"DIRC" + be32(2) + be32(entry_count)
for each entry:
    be32(0) repeated 6 times             # ctime, mtime, dev, ino
    + be32(git_mode)                     # 0100644, 0100755, or 0120000
    + be32(0) repeated 3 times           # uid, gid, size
    + raw_object_id_bytes
    + be16(min(len(raw_path), 0x0fff))   # stage/extended bits are zero
    + raw_path
    + zero_bytes(8 - ((42 + h + len(raw_path)) mod 8))
then repository-format digest of every preceding byte
```

`be32(git_mode)` uses the numeric Git mode, paths contain no NUL, and the
padding expression deliberately yields eight bytes when the remainder is zero
so every entry includes its NUL terminator. No extension follows the entries.
Parse the result again and require exact semantic equality, zero stat fields,
zero stage/extended flags, no extension, and a valid trailer.
`canonical_index_raw_sha256` is ordinary SHA-256 of these canonical bytes.
Neither it nor any outer identity depends on live stat fields, split-index
layout, optional extensions, or a shared-index filename.
For every tracked path, effective `filter`, `working-tree-encoding`, `text`, and
`eol` attributes must be unspecified so the worktree patch represents raw
source bytes rather than a machine-configured clean conversion.

Hash two independent canonical patches so an intermediate staged blob cannot
hide behind identical final working-tree bytes. For both `diff --cached HEAD --`
and `diff --`, use exactly:

```text
--binary --full-index --no-ext-diff --no-textconv --no-color
--no-renames --no-relative --default-prefix --line-prefix=
--unified=3 --inter-hunk-context=0 --diff-algorithm=myers
--no-indent-heuristic -O <os.devnull> --ignore-submodules=none
--submodule=short --ita-visible-in-index --ws-error-highlight=none
--output-indicator-new=+ --output-indicator-old=-
--output-indicator-context=<one ASCII space>
```

Let `T` be exactly the raw paths in the parsed index manifest. For every sorted
path, hash raw worktree bytes and Git mode exactly as for an untracked path; use the literal
mode `deleted` and no content hash when absent. Reject type/identity/timestamp
changes during capture. This complete raw manifest is deliberately redundant
with `git diff`: it prevents stat-cache or conversion behavior from hiding final
worktree bytes.

Let `I` and `W` be the resulting raw patch bytes and let:

```text
raw_worktree_sha = H(concat(
    path + NUL + mode_or_deleted + NUL +
    (H(raw_bytes).encode("ascii") + NUL if present else NUL)
    for path in sorted(T)
))
```

Before any durable snapshot-archive publication, seal the declared-source list
and authorize exact states rather than paths alone. In this paragraph `H[p]`,
`I[p]`, `W[p]`, and `R[p]` are file states, unrelated to the `H(bytes)` hash
helper. A state is either `ABSENT` or exactly `(git_mode, raw_sha256)`. Derive
`H` from the complete HEAD tree, `I` from the resolved stage-0 index, and `W`
from the captured worktree across the union of all three path sets. Let `A` be
the raw-path set of the reviewed `source_files`. For each `p in A`, require a
present worktree state whose raw hash equals its source-file record and define
`R[p] = W[p]`; `R` is undefined outside `A`. Let the actual non-HEAD set be
`D = {p | I[p] != H[p] or W[p] != H[p]}`. `A` is the complete declared source
set and may include unchanged imported/read project files; `D` is only its
proposed deviation subset.

The archive-eligibility policy is exactly
`head-or-exact-declared-source-state-v1` and requires, for every path:

```text
I[p] != H[p]  =>  p in A and I[p] == R[p]
W[p] != H[p]  =>  p in A and W[p] == R[p]
D == {p in A | R[p] != H[p]}
```

There is no glob, directory-prefix, generated-file exception, supplemental
allowlist, or hash-only waiver. Four-tuples here are explicitly `(H,I,W,R)`.
The policy admits `(H,H,H,H)` (unchanged declared source), plus the four
deviation forms `(H,H,R,R)` (unstaged reviewed edit), `(H,R,R,R)` (staged
reviewed edit), `(ABSENT,ABSENT,R,R)` (reviewed untracked source), and
`(ABSENT,R,R,R)` (reviewed staged add). It rejects `(H,secret,R,R)`, where a staged private blob occupies a
declared path while the reviewer sees safe worktree bytes, as well as a
deletion, index-only addition, undeclared edit, or any mode/content mismatch.
Newline and non-UTF-8 paths remain valid Git inputs but cannot enter `A`, whose
review paths are canonical UTF-8 POSIX. Failure precedes every archive write
and reports only closed counts/reason IDs, never path or content bytes.

The offline verifier reconstructs `H/I/W/R` independently from the archived
HEAD/index/status/patch/raw-worktree/untracked preimages, reparses the declared
source array, and repeats both implications for the entire path union. The
later environment audit must still prove that `A` exactly matches the closed
six-source union of broker source-snapshot records (a subset of the declared
policy leaves), both startup bootstraps, both
control-registry leaves, selected required/optional execution-policy modules,
selected policy `data_files`, and shell identities. An optional permitted
module/data row or control-only leaf need
not be observed, but a path outside that union is an invalid unrelated
declaration.

Every review/promotion run uses a dedicated clean review capsule. It is a new,
isolated, ordinary Git repository with no alternates, shared object store,
linked-worktree administrative files, remote, replace/graft state, or local
configuration inherited from the source checkout. Its detached HEAD, complete
tree, and initial stage-0 index are reconstructed and independently verified
from the exact `source_fingerprint.head_sha`; its index and worktree are clean
before reviewed bytes are copied in. The publisher then guardedly copies the
proposed Git mode and raw bytes for exactly the declared `source_files`,
requires every resulting `R` hash to equal its source-file record, and
recaptures the full fingerprint. Review starts only if the resulting complete
path union satisfies both implications and the `D` equality above. Thus every
deviation is one exact declared reviewed state, while a declared source that
still equals HEAD remains valid and does not enter `D`. The capsule is frozen
read-only for Reviewer A and Reviewer B, except for their detached output
bundles outside the capsule.

A live feature/main worktree with any unrelated staged, dirty, deleted, or
untracked state is only a guarded byte source for declared files; it is never
the review root, archive authority, or baseline. The harness must refuse to
start there even if its seven-value fingerprint is stable. It also must not
hash, archive, allowlist, or otherwise publish the unrelated state: the clean
baseline is the already content-addressed HEAD commit, not a digest of the
pre-batch dirty worktree. For the current two-document batch the clean capsule
therefore proves `D=A` with exactly two `(ABSENT,ABSENT,R,R)` paths and no other
deviation; that current-batch equality is not a rule for general implementation
source sets.

Then:

```text
tracked_sha = H(
    b"dartwork-mpl-tracked-v2" + NUL +
    b"git-tool" + NUL + git_tool_manifest_sha256.encode("ascii") + NUL +
    b"index-manifest" + NUL + index_manifest_sha256.encode("ascii") + NUL +
    b"index-representation" + NUL +
        b"git-index-v2-zero-stat-extension-free-v1" + NUL +
    b"canonical-index" + NUL +
        canonical_index_raw_sha256.encode("ascii") + NUL +
    b"index-patch" + NUL + H(I).encode("ascii") + NUL +
    b"worktree" + NUL + H(W).encode("ascii") + NUL +
    b"raw-worktree" + NUL + raw_worktree_sha.encode("ascii") + NUL
)

combined_sha = H(
    b"dartwork-mpl-source-fingerprint-v2" + NUL +
    concat(
        field_name.encode("ascii") + NUL +
        ascii(field_value) + NUL
        for the first six fields in schema order
    )
)
```

`entry_count` is encoded as canonical unsigned decimal ASCII and is deliberately
included in `combined_sha`; all other values are their lowercase ASCII hashes.
This binds the Git executable/config policy, HEAD, status and path spelling,
stage-0 index mode/OID/raw blob bytes, the canonical semantic index,
index-to-worktree contents, and every
untracked blob without assuming that a valid Git path lacks newlines.

Fingerprint equality is a guard, not the execution source. Every evidence run
first creates a coherent captured source execution snapshot and subsequently
imports and reads project source bytes only from it. Non-source lifecycle inputs
use the separate bundle contract below. The closed snapshot record has exactly:

```text
schema, source_fingerprint, git_tool_manifest_sha256,
head_manifest_sha256, index_manifest_sha256,
git_index_representation_id, canonical_index_raw_sha256,
git_capsule_sha256,
root_manifest_sha256, source_files_sha256, import_read_policy_id,
archive_eligibility_policy_id,
execution_snapshot_sha256
```

Its schema is `oklab-authoring-execution-snapshot-v1` and import/read policy is
`captured-project-bytes-only-v1`. `archive_eligibility_policy_id` is exactly
`head-or-exact-declared-source-state-v1`, and the snapshot is serializable only
after the exact-state implications above pass. The index representation/hash
equal the independently rebuilt canonical index and the Git-tool manifest.
`root_manifest_sha256` hashes, with domain
`b"dartwork-mpl-snapshot-root-v1\0"`, every raw-path record in the union of the
stage-0 index and standard untracked set. A tracked record is raw path, literal
`tracked`, index mode/blob SHA-256, worktree mode-or-`deleted`, and worktree raw
SHA-256-or-empty, all NUL-delimited; an untracked record is raw path, literal
`untracked`, mode, and raw SHA-256. Records are raw-path sorted. The declared
`source_files` subset must be surrogate-free repo-relative POSIX paths that map
one-to-one to those raw records; `source_files_sha256` uses
`b"dartwork-mpl-declared-source-files-v1\0"` plus its canonical ordered
path/hash array. `execution_snapshot_sha256` uses
`b"dartwork-mpl-execution-snapshot-v1\0"` plus the complete snapshot record with
only that field omitted.

`head_manifest_sha256` uses the following one byte-exact preimage. Enumerate
all and only recursive non-directory blob leaves of the HEAD root tree in
unsigned raw-path byte order; tree entries themselves are not records and
gitlinks are rejected. Each leaf record is exactly:

```text
raw_path + NUL +
ascii_git_mode + NUL +
lowercase_full_blob_oid + NUL +
lowercase_raw_blob_sha256 + NUL
```

`ascii_git_mode` is exactly `100644`, `100755`, or `120000`. For mode `120000`,
the blob bytes—and therefore `lowercase_raw_blob_sha256`—are the raw symlink-
target bytes. `raw_path` is the unmodified Git path byte string; the other
three fields are ASCII, the object ID is full-width for the recorded object
format, and the raw SHA-256 is exactly 64 lowercase hexadecimal digits. The
manifest preimage is
`b"dartwork-mpl-head-tree-v1\0"` followed by the concatenated records, with no
count, JSON, LF, directory record, or trailing byte beyond the final record's
shown NUL. The HEAD closure is exactly the resolved HEAD commit plus its
recursively reachable root-tree trees and blobs, excluding parent history. A
closure object has exactly `type`, `oid`,
`byte_count`, and `payload_sha256`; type is `commit`, `tree`, or `blob`, the OID
matches the recorded object format, and the payload hash covers raw
`cat-file <type>` bytes. Objects are sorted by type rank commit/tree/blob and
then raw ASCII OID.

The closed Git-capsule manifest has exactly:

```text
schema, object_format, git_tool_manifest_sha256,
operational_config_sha256, canonical_config_raw_sha256,
argv_policy_sha256, archive_eligibility_policy_id,
head_commit_oid, head_commit_payload_sha256, head_root_tree_oid,
head_objects, index_objects, authority_closures, authority_objects,
head_manifest_sha256,
git_index_representation_id, canonical_index_raw_sha256,
index_manifest_sha256, index_patch_sha256, worktree_patch_sha256,
raw_worktree_sha256, root_manifest_sha256, git_capsule_sha256
```

Its schema is `dartwork-mpl-git-capsule-v2`; the representation ID and
`canonical_index_raw_sha256` cover only the deterministic semantic index above,
patch fields cover the raw `I` and `W` diff streams, and all manifest fields
equal their independently recomputed values. No live index/shared-index byte,
stat field, extension payload, filename, or hash is a valid field.
`archive_eligibility_policy_id` equals the execution snapshot and both
exact-state implications are rederived before serialization. Neither raw
config nor a config-source array is a valid field. `git_capsule_sha256` is
SHA-256 of `b"dartwork-mpl-git-capsule-v2\0"` plus canonical JSON of the
complete manifest with only that field omitted. Thus every raw payload is bound
through an executable, ordered preimage rather than an unspecified container.
The capsule is separate from the project import root and read-only.

`index_objects` is the full-ASCII-OID-sorted array of unique stage-0 index blob
objects not already present in `head_objects`; each has exactly `type="blob"`,
`oid`, `byte_count`, and `payload_sha256`. Its identities/payloads equal the
parsed index manifest.

`authority_closures` is the authority-commit-OID-sorted unique array required
by this invocation's strict authority inputs; it is empty only when no such
input exists. Each record has exactly:

```text
schema, authority_commit_oid, authority_commit_payload_sha256,
authority_root_tree_oid, head_to_authority_commit_path,
authority_tree_manifest_sha256, authority_closure_sha256
```

Its schema is `dartwork-mpl-git-authority-closure-v1`. The commit path is a
non-empty full-lowercase-OID array beginning with `head_commit_oid`, ending
with `authority_commit_oid`, and containing no duplicate. For each adjacent
pair, the verifier parses the current raw commit payload and requires the next
OID to equal its first literal `parent` header. The array is therefore the
unique iterative first-parent sequence from HEAD through the first occurrence
of authority; it may neither choose a later merge parent nor skip an
intermediate commit. A one-element path is valid only when authority equals
HEAD. If a parentless commit appears before authority, or authority is reachable
only through a second-or-later merge parent, capture fails. The authority
payload/tree fields equal the parsed final commit, and every OID uses the
capsule's one `object_format`.
`authority_tree_manifest_sha256` uses the same
path/mode/full-blob-OID/raw-SHA record algorithm and domain as
`head_manifest_sha256`, but over the complete authority root tree. The closure
self-hash is SHA-256 of
`b"dartwork-mpl-git-authority-closure-v1\0"` plus canonical JSON with only
`authority_closure_sha256` omitted. Refs, replacement/graft mechanisms, and an
ambient object database are never ancestry inputs.

`authority_objects` is the type-rank/OID-sorted unique array of commit objects
needed for every captured path and every tree/blob recursively reachable from
each authority root, excluding objects already in `head_objects` or
`index_objects`. Each row has the same exact object schema. Its membership is
rederived from the closures: no missing or extra object is allowed. Therefore
the capsule object set is exactly `head_objects union index_objects union
authority_objects`—neither only HEAD nor an open set of extras. This supplies
only the reviewed authority chains and trees, not unrestricted parent history.

Its filesystem layout is also closed. Relative to one private `capsule/` root
it contains exactly:

```text
git/HEAD
git/config
git/refs/snapshot/head
git/objects/<first-two-oid-hex>/<remaining-oid-hex>
git/index
worktree/
```

`git/HEAD` is exactly `b"ref: refs/snapshot/head\n"`; the ref file is the
lowercase captured HEAD OID plus one LF. `git/config` is exactly the canonical
synthetic `C` selected by object format; `git/config.worktree` is forbidden.
Every
object in the exact union of `head_objects`, `index_objects`, and
`authority_objects` is
stored as one ordinary loose Git object at its object-format path. Let
`U = type + b" " + ascii_decimal(len(payload)) + NUL + payload`. The exact
`git-loose-zlib-stored-v1` bytes are zlib header `78 01`, followed by consecutive
maximal 65,535-byte DEFLATE stored blocks: block byte `00` for every non-final
block or `01` for the final block, unsigned 16-bit little-endian `LEN`, its
one's-complement `NLEN`, then the block payload. Append Adler-32 of complete
`U` as unsigned 32-bit big-endian. A dictionary, alternate block segmentation,
compressed block, trailing byte, or compressor-dependent encoding is forbidden.
Inflation must reproduce `U`; the repository's configured Git digest of `U`
must equal the path OID; and the payload hash must equal the manifest. The raw
loose-object file must also equal this canonical encoder byte-for-byte, so two
conforming captures of one snapshot produce the same capsule/archive bytes.
`git/index` is exactly the canonical version-2, zero-stat, extension-free index
whose SHA-256 is `canonical_index_raw_sha256`; no live or shared index file is
copied into the capsule.

`worktree/` contains exactly the snapshot root manifest, with directories mode
`0555`, regular non-executable/executable files mode `0444`/`0555`, and
symlinks preserving raw target bytes. Capsule Git metadata files are `0444`;
metadata directories are `0555`. No `commondir`, alternates, hooks, logs,
packed refs, grafts, or replace refs exist, and no loose object lies outside
that exact union. Detached operands are
exactly `git-dir=capsule/git`, `work-tree=capsule/worktree`, and
`captured-index=capsule/git/index`. Verification uses the detached prefix and
environment row above and must reproduce every registered live invocation's raw
stdout, stderr, and exit status where equality is required by the fingerprint
algorithm. `config-dump` is the sole deliberate stdout exception: both sides
must validate and produce the same operational projection, while raw live
config output is discarded and detached output reflects synthetic `C`. The
original checkout is then inaccessible, so no omitted path can
be consulted.

Capture runs as one fail-closed transaction:

1. acquire the tool's repo-scoped cooperative read guard and take two
   immediately consecutive live fingerprints; both must match;
2. seal the declared-source array, derive complete `H/I/W/R` states from the
   guarded manifests, enforce both archive-eligibility implications, and
   publish nothing on failure. Strict-parse the invocation's sealed authority-
   bearing inputs and derive the unsigned-ASCII-sorted unique set of required
   `authority_commit_oid` values; an ambient ref or caller-supplied extra OID
   cannot add to that set. For each required `A`, begin at captured `H`, parse
   raw commit payloads, and capture the unique first-parent sequence through
   `A`; fail if a parentless commit occurs first. Capture `A`'s complete
   recursive root-tree closure and construct its byte-exact tree manifest and
   `authority_closure`. Then capture the resolved HEAD commit/tree/blob closure,
   canonical index, and every distinct stage-0 index blob absent from that
   closure as ordinary loose objects, together with every required authority-
   path commit and authority tree/blob not already present, both patch streams,
   and every tracked or standard-untracked path into a fresh private Git
   capsule plus worktree. Use `lstat`, no-follow opens, before/after
   identity/size/time checks, and raw byte hashes; preserve allowed modes and
   symlink target bytes, but put no `.git` metadata in the import root and copy
   no ignored output. Before proceeding, derive `head_objects`, `index_objects`,
   `authority_closures`, and `authority_objects` from those captured payloads
   and require their exact schemas, sort orders, self-hashes, and three-array
   object-union membership;
3. materialize only canonical synthetic config `C`, make the capsule,
   canonical index, and tree read-only, then run the
   same fingerprint algorithm with that index, capsule Git directory,
   and snapshot worktree; normalize the physically different config origins to
   the same operational projection and require the Git-tool manifest,
   seven fields, HEAD/index manifests, patches, and root bytes to equal both
   live guards. In a fresh isolated verifier namespace, make the original
   checkout, common Git directory, refs, and ambient object database
   inaccessible while the parent capture process retains the guarded checkout
   solely for step 4; then reparse only capsule bytes,
   reconstruct every first-parent authority path and complete authority tree,
   recompute both tree manifests and every closure self-hash, and rederive the
   exact `head_objects union index_objects union authority_objects` set with no
   missing or extra object. The complete verification must succeed in that
   state; merely having captured hashes that cannot be replayed offline fails;
4. after the isolated offline verifier exits, take two more consecutive live
   fingerprints in the still-guarded parent and require both to equal the
   authoritative snapshot fingerprint; otherwise destroy the snapshot and
   publish nothing. The offline verifier never shares that parent namespace or
   gains a descriptor to the live checkout.

A change-and-restore during copying cannot substitute a hybrid input: the
authoritative fingerprint is recomputed from the canonical index/tree bytes, then
must equal the guards. Execution launches the fresh, sequential two-child
transaction inside the Linux sealed native root, with every captured source and
external-input leaf copied and fully sealed before either launch. The supervisor
materializes distinct role-filtered source views from the one captured snapshot.
The preparer view contains its bootstrap and only the reviewed registry/control
leaves it may read, plus shell initializer leaves in shell mode; it receives
sealed identities, but not readable bytes, for every computation-brokered
required/optional project module and policy `data_files` leaf. The computation view contains its separate bootstrap
and only the policy-authorized project/data leaves. It excludes the preparer
bootstrap, both raw registries, and dispatch shell initializer leaves; an
initializer explicitly listed as an ordinary `scripts.*` policy module is an
ordinary computation leaf instead. Neither view has
an executable source leaf, `PYTHONPATH`, or an original-worktree path, and no
descriptor or mount crosses between them. The native roots are private runtime
transport and are not part of the project source snapshot or external-input
bundle.

Both startup bootstraps are nevertheless declared project source leaves:
CPython reads each before its lifecycle's Python audit hook can exist, so each
path/hash is bound by that lifecycle's `bootstrap_source`, native pre-broker
input record, `source_files`, and the snapshot rather than by a fabricated
computation broker-read event. The computation Python audit hook and no-follow,
dirfd-relative input broker reject every later project-local import/read not
present with the declared hash in `source_files`; symlink resolution outside
the snapshot fails. The exact declared set is the six-source union defined by
the phase-manifest rule above, not the computation bootstrap plus observed
reads alone. An optional policy module or control-only registry/shell identity
therefore remains declared without becoming a computation read. The bootstrap
has exactly one pre-broker consumption: every post-`broker-ready` open, read,
import, reload, or alias of its path or leaf ID is rejected before a broker
record can be emitted. Reads from the
private output tmpfs, the presealed verified external-input bundle defined
below, and the exact environment-v3 ownership partition are the only
exceptions.
That partition applies the closed `P/D/I/S/N` decision table above: a project
source must match one declared project record, a distribution byte must match
one verified `Distribution.files`/`locate_file()` entry and its retained
ownership trigger, a residual site-root path fails, and only an otherwise
unowned source/bytecode origin beneath exactly one coalesced stdlib group or an
  extension bound to exactly one sealed native mapping is admitted. No directory prefix
grants distribution or stdlib authority. Authoring
modules are reviewed TCB whose execution contract forbids subprocesses, the
enumerated FFI/debug surfaces, and broker bypass; architecture tests enforce
those ordinary interface and syscall constraints without claiming exhaustive
same-process memory isolation. Both pre-broker startup
records, the two registry and shell projections, the complete selected project-
execution policy, and the inline computation broker-read records together must
reproduce the exact six-source declared union without double-counting repeated
reads. The latter begins with base handoff ordinal zero before every base
import, crosses the stopped base-ready boundary, then retains invocation-
handoff, source-snapshot, external-input, distribution, and permitted stdlib
reads with one global ordinal space through terminal stop; a source/
external-only phase projection or trigger ordinal without that record is
invalid. Rehash the
read-only snapshot after execution and fail on any mutation.

The execution snapshot above contains project source only. Every non-source
input, including an ignored artifact produced by an earlier lifecycle stage, is
captured into a separate content-addressed external-input bundle before the
consumer starts. The closed bundle has exactly `schema`, `invocation_kind`,
`records`, and `external_input_bundle_sha256`; its schema is
`oklab-authoring-external-input-bundle-v1`. Each record has exactly `role`,
`source_path`, `blob_path`, `byte_count`, and `raw_sha256`. `source_path` is the
one canonical repo-relative POSIX producer path; absolute paths, empty or `..`
components, aliases, and duplicate role/path pairs fail. `blob_path` is exactly
`blobs/<raw_sha256>`, byte count is a non-boolean nonnegative integer, and every
blob is a regular file with matching length and raw hash. Symlinks and all other
file types fail. Records are sorted by the UTF-8 byte tuple `(role,source_path)`.
The bundle self-hash is SHA-256 of
`b"dartwork-mpl-oklab-authoring-external-input-bundle-v1\0"` plus canonical JSON
of the complete bundle with only `external_input_bundle_sha256` omitted.

Publish a bundle create-only at
`<output-root>/input-bundles/<external_input_bundle_sha256>/manifest.json`. An
existing path is accepted only through
`publish_live_bundle_0444_0555`'s complete revalidation, inode/link check, and
bottom-up resynchronization; any difference is fatal and nothing is replaced or
deleted. There is no visible blob-only live-bundle prefix: construction writes
and synchronizes blobs before `manifest.json` in private staging, seals the
tree, and atomically installs the whole directory. A staging subset has no
authority, and a visible manifest always arrives with the complete sealed blob
set. Capture holds the same
repo-scoped cooperative read guard as source capture. For every live input it
uses `lstat`, no-follow open, and before/after device, inode, type, mode, size,
mtime, and ctime checks. It computes two consecutive complete live manifests
before copying and two after; all four and the privately staged bundle must
agree before the atomic install. A change-and-restore or hybrid copy destroys
the temporary bundle and publishes nothing. After install, rehash the sealed
bundle before and after execution and allow the consumer to read only its
captured blob—not the original ignored path.

Allowed roles and cardinalities are closed by `invocation_kind`:

| Invocation | Required external-input records |
|---|---|
| `legacy-baseline-extractor-a` | none |
| `legacy-baseline-extractor-b` | none |
| `legacy-baseline-cross-extraction` | exactly `baseline-extractor-a-candidate`, `baseline-extractor-a-evidence`, `baseline-extractor-b-candidate`, and `baseline-extractor-b-evidence` |
| `policy-preselection` | none |
| `proposal` | exactly `policy-preselection` |
| `comparison` | exactly `proposal` |
| `discrete-policy-characterization-verification` | none; the tracked characterization, visual strip, recipe, and policy dependencies are declared source-snapshot reads |
| `admission-policy-characterization-verification` | none; the tracked characterization, truth/acceptance, and authority assets are declared source-snapshot reads |
| `characterization-generation` | none |
| `characterization-verification` | exactly `sealed-generated-characterization-payload`; the tracked expected payload is a declared source-snapshot read |
| `reviewer-a` | `proposal`, `comparison-report`, and exactly every declared `comparison-artifact/<relative-path>` |
| `reviewer-b` | all Reviewer-A inputs plus `reviewer-a-report`, `reviewer-a-execution-input-manifest`, every `reviewer-a-execution-input-blob/<role>`, `reviewer-a-control-manifest`, every `reviewer-a-control-blob/<role>`, `reviewer-a-evidence-manifest`, every `reviewer-a-evidence-blob/<role>`, and `reviewer-a-completion-token` |
| `semantic-reviewer-a` | exactly `review-subject-manifest` and every subject-manifest record whose location is `external-input`; the documents-only batch has no such records |
| `semantic-reviewer-b` | all semantic-A inputs plus A report, A's historical input manifest/blobs, control manifest/blobs, evidence manifest/blobs, and completion token |
| `legacy-v5-baseline-promotion` | exactly the preinstall `review-subject-manifest`, all six preinstall output roles (`baseline-extractor-a-candidate`, `baseline-extractor-a-evidence`, `baseline-extractor-b-candidate`, `baseline-extractor-b-evidence`, `candidate-compatibility`, `baseline-cross-extraction-manifest`), both reviewer reports, both historical external-input manifests and every declared blob, both review-control manifests and every declared blob, both review-evidence manifests and every declared blob, the A-completion token, one `reviewed-execution-snapshot-archive-manifest`, one `reviewed-execution-snapshot-archive-blob/<raw_sha256>` per distinct archive blob, and one `maintainer-approval` |
| `legacy-v5-baseline-authority-finalization` | exactly the promotion `review-subject-manifest`, both promotion reviewer reports, both historical external-input manifests and every declared blob, both review-control manifests and every declared blob, both review-evidence manifests and every declared blob, the A-completion token, one `reviewed-execution-snapshot-archive-manifest`, one `reviewed-execution-snapshot-archive-blob/<raw_sha256>` per distinct archive blob, and one post-promotion `maintainer-approval`; the reviewed preinstall archive, compatibility, and acceptance remain exact source-snapshot reads |
| `fixed-y-reviewer-a` | exactly `review-subject-manifest` and every subject-manifest record whose location is `external-input` |
| `fixed-y-reviewer-b` | all fixed-Y-A inputs plus A report, A's historical input manifest/blobs, control manifest/blobs, evidence manifest/blobs, and completion token |
| `fixed-y-acceptance-promotion` | exactly the stage `review-subject-manifest`, both reviewer reports, both historical external-input manifests and every declared blob, both review-control manifests and every declared blob, both review-evidence manifests and every declared blob, the A-completion token, one `reviewed-execution-snapshot-archive-manifest`, one `reviewed-execution-snapshot-archive-blob/<raw_sha256>` per distinct archive blob, and one `maintainer-approval` |
| `validation-truth-reviewer-a` | exactly `review-subject-manifest` and every subject-manifest record at `external-input`; V1 has exactly `candidate-truth` |
| `validation-truth-reviewer-b` | all validation-truth-A inputs plus A report, A's historical input manifest/blobs, control manifest/blobs, evidence manifest/blobs, and completion token |
| `validation-truth-acceptance-promotion` | exactly the truth `review-subject-manifest`, both reviewer reports, both historical external-input manifests and every declared blob, both review-control manifests and every declared blob, both review-evidence manifests and every declared blob, the A-completion token, one `reviewed-execution-snapshot-archive-manifest`, one `reviewed-execution-snapshot-archive-blob/<raw_sha256>` per distinct archive blob, and one `maintainer-approval` |
| `promotion-replay` | exactly `policy-preselection`, `proposal`, `comparison-report`, every `comparison-artifact/<relative-path>`, `reviewer-a-report`, `reviewer-b-report`, every `execution-input-manifest/<stage>` and its `execution-input-blob/<stage>/<role>`, every `review-control-manifest/<reviewer>` and its `review-control-blob/<reviewer>/<role>`, every `review-evidence-manifest/<reviewer>` and its `review-evidence-blob/<reviewer>/<role>`, and one `maintainer-approval` |
| `policy-reviewer-a` | exactly one `policy-characterization-verification-evidence`; tracked policy/characterization/artifacts come from the common source snapshot |
| `policy-reviewer-b` | exactly A report, A's historical execution-input manifest and every distinct declared blob, A control manifest/blobs, A evidence manifest/blobs, and A completion token |
| `policy-registry-promotion` | exactly both policy-review reports; A and B historical execution-input manifests and every distinct declared blob; A and B control manifests/blobs; A and B evidence manifests/blobs; one A-completion token; and one `maintainer-approval`; policy, characterization, current registry index, and referenced entries remain source-snapshot reads |

For policy promotion, each `(reviewer,kind)` pair where reviewer is A/B and
kind is execution-input/control/evidence contributes exactly one manifest role
and one blob role per distinct raw hash referenced by that manifest. Thus fixed
cardinality is two reports, six manifests, one completion token, and one
maintainer-approval record; blob count is derived, shared bytes within one
manifest occur once, and no other role is allowed. Reviewer A's execution-input
manifest has exactly the one captured verification-evidence record and is a
real content-addressed object with a non-null hash.

Truth-bootstrap promotion uses the same six historical manifest categories and
derived distinct-blob rule, plus its subject, snapshot archive, token, two
reports, and approval exactly as its table row states. Its A bundle has the one
candidate external input; B contains the complete historical A closure. No
policy, fixed-Y, proposal, or family artifact may enter either truth role set.

Role suffixes use already validated canonical relative paths and are unique. An
extra, missing, stale, or hash-only record is fatal. In particular, proposal,
comparison, Reviewer A, Reviewer B, and promotion never read the live ignored
tree. Every B-stage external completion-token blob must be byte-identical to
the predecessor token in B's independently captured control bundle. The
analogous policy-review sequence obeys the same predecessor rule.

For `promotion-replay`, `<stage>` occurs exactly once for
`policy-preselection`, `proposal`, `comparison`, `reviewer-a`, and `reviewer-b`;
`<reviewer>` occurs exactly once for `reviewer-a` and `reviewer-b`; every
derived blob role occurs exactly once per record in its named manifest, and no
other role is permitted. This historical closure lets promotion recompute all
five prior `ExecutionInputs` objects rather than trusting their hash strings.
Canonical producer paths are exactly:

```text
build/color-authoring/<family>/policy-preselection.json
build/color-authoring/<family>/proposal.json
build/color-authoring/<family>/comparison/report.json
build/color-authoring/<family>/comparison/<relative-path>
build/color-authoring/<family>/reviews/reviewer-a.json
build/color-authoring/<family>/reviews/reviewer-b.json
```

Every nested input/control/evidence manifest and blob uses the universal
`manifest.json`/`blobs/<raw_sha256>` layout above.

In this table, `none` always means a real, non-null, hashed zero-record external-
input manifest. It never means a null bundle hash or absent manifest. This rule
applies to preselection, both policy-characterization verification profiles,
and characterization generation. Policy Reviewer A instead has exactly its
one verification-evidence input.

Every invocation embeds a closed `ExecutionInputs` record with exactly
`schema`, `execution_snapshot_sha256`, `external_input_bundle_sha256`,
`review_control_bundle_sha256`, and `execution_inputs_sha256`. Its schema is
`oklab-authoring-execution-inputs-v1`; the source snapshot hash names the
record above, the external hash names the verified content-addressed subject or
lifecycle manifest, and the control hash names the verified pre-run
review-control manifest for review invocations and is exactly null for every
non-review invocation. Under the invocation's declared bundle store, the
external hash resolves only to
`input-bundles/<external_input_bundle_sha256>/manifest.json`; a control hash
resolves only to
`review-controls/<review_control_bundle_sha256>/manifest.json`,
and its self-hash is SHA-256 of
`b"dartwork-mpl-oklab-authoring-execution-inputs-v1\0"` plus the complete
canonical record with only `execution_inputs_sha256` omitted. Source fingerprint
and source-snapshot equality are common across a sequential A→B pair; their
external bundles and execution-input hashes are stage-specific and form the
predecessor chain. The input broker's only project-data roots are the declared
source subset and verified external blobs. Reads from a fresh output temporary
directory remain write/read scratch and cannot satisfy an input role.

Evidence completion hashing is schema-specific. There is no generic
`report_payload_sha256` or `dartwork-mpl-report-v1` rule. The selected schema row
completely determines the field, domain, hashed object, and omission; the
proposal row deliberately hashes its exact family/payload identity rather than
claiming an outer-envelope self-hash:

| Schema | Completion-hash field | Domain tag | Hashed object / omitted field |
|---|---|---|---|
| `dartwork-mpl.color-compatibility/v2` | `compatibility_payload_sha256` | `dartwork-mpl-color-compatibility-v2\0` | complete compatibility asset / that field only |
| `dartwork-mpl.color-ssot/v6` | `ssot_payload_sha256` | `dartwork-mpl-color-ssot-v6\0` | complete compatibility SSOT / that field only |
| `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1` | `evidence_sha256` | `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1\0` | complete extractor evidence / that field only |
| `dartwork-mpl-legacy-v5-baseline-cross-extraction-v1` | `cross_extraction_sha256` | `dartwork-mpl-legacy-v5-baseline-cross-extraction-v1\0` | complete cross-extraction manifest / that field only |
| `dartwork-mpl-legacy-v5-baseline-acceptance-v1` | `acceptance_sha256` | `dartwork-mpl-legacy-v5-baseline-acceptance-v1\0` | complete tracked baseline acceptance / that field only |
| `dartwork-mpl-legacy-v5-baseline-authority-v1` | `authority_marker_sha256` | `dartwork-mpl-legacy-v5-baseline-authority-v1\0` | complete tracked post-promotion authority marker / that field only |
| `oklab-authoring-proposal-v1` | `payload_sha256` | `dartwork-mpl-oklab-authoring-payload-v1\0` | exact `{"family":family,"payload":payload}` object / no omission |
| `oklab-authoring-frozen-v1` | `frozen_envelope_sha256` | `dartwork-mpl-oklab-authoring-frozen-v1\0` | complete frozen envelope / that field only |
| `oklab-authoring-comparison-report-v1` | `comparison_report_payload_sha256` | `dartwork-mpl-oklab-authoring-comparison-report-v1\0` | complete envelope / that field only |
| `oklab-fixed-y-characterization-payload-v1` | `payload_sha256` | `dartwork-mpl-fixed-y-characterization-payload-v1\0` | complete scientific payload / that field only |
| `oklab-fixed-y-characterization-generation-evidence-v1` | `generation_evidence_sha256` | `dartwork-mpl-fixed-y-characterization-generation-evidence-v1\0` | complete invocation envelope / that field only |
| `oklab-fixed-y-characterization-evidence-v1` | `characterization_evidence_sha256` | `dartwork-mpl-fixed-y-characterization-evidence-v1\0` | complete invocation envelope / that field only |
| `oklab-authoring-discrete-policy-characterization-v1` | `characterization_payload_sha256` | `dartwork-mpl-oklab-authoring-discrete-policy-characterization-v1\0` | complete artifact / that field only |
| `oklab-authoring-admission-policy-characterization-v1` | `characterization_payload_sha256` | `dartwork-mpl-oklab-authoring-admission-policy-characterization-v1\0` | complete artifact / that field only |
| `oklab-authoring-discrete-policy-characterization-verification-v1` | `verification_evidence_sha256` | `dartwork-mpl-oklab-discrete-policy-characterization-verification-v1\0` | complete evidence / that field only |
| `oklab-authoring-admission-policy-characterization-verification-v1` | `verification_evidence_sha256` | `dartwork-mpl-oklab-admission-policy-characterization-verification-v1\0` | complete evidence / that field only |
| `oklab-validation-oracle-truth-v1` | `truth_payload_sha256` | `dartwork-mpl-validation-oracle-truth-v1\0` | complete create-only truth asset / that field only |
| `oklab-authoring-oracle-results-v1` | `oracle_results_sha256` | `dartwork-mpl-oklab-authoring-oracle-results-v1\0` | complete object / that field only |
| `oklab-authoring-review-terminal-result-v1` | `terminal_result_sha256` | `dartwork-mpl-oklab-authoring-review-terminal-result-v1\0` | complete terminal result / that field only |
| `dartwork-mpl-shipped-exact-surfaces-v1` | `evidence_sha256` | `dartwork-mpl-shipped-exact-surfaces-v1\0` | complete comparison artifact / that field only |
| `dartwork-mpl-authoring-side-by-side-v1` | `side_by_side_manifest_sha256` | `dartwork-mpl-authoring-side-by-side-v1\0` | complete four-role manifest / that field only |
| `oklab-authoring-reviewer-a-report-v1` | `reviewer_a_report_sha256` | `dartwork-mpl-oklab-authoring-reviewer-a-report-v1\0` | complete envelope / that field only |
| `oklab-authoring-reviewer-b-report-v1` | `reviewer_b_report_sha256` | `dartwork-mpl-oklab-authoring-reviewer-b-report-v1\0` | complete envelope / that field only |
| `oklab-authoring-policy-reviewer-a-v1` | `reviewer_a_report_sha256` | `dartwork-mpl-oklab-authoring-policy-reviewer-a-v1\0` | complete envelope / that field only |
| `oklab-authoring-policy-reviewer-b-v1` | `reviewer_b_report_sha256` | `dartwork-mpl-oklab-authoring-policy-reviewer-b-v1\0` | complete envelope / that field only |
| `oklab-semantic-batch-reviewer-a-v1` | `reviewer_a_report_sha256` | `dartwork-mpl-oklab-semantic-batch-reviewer-a-v1\0` | complete envelope / that field only |
| `oklab-semantic-batch-reviewer-b-v1` | `reviewer_b_report_sha256` | `dartwork-mpl-oklab-semantic-batch-reviewer-b-v1\0` | complete envelope / that field only |
| `oklab-fixed-y-characterization-reviewer-a-v1` | `reviewer_a_report_sha256` | `dartwork-mpl-oklab-fixed-y-characterization-reviewer-a-v1\0` | complete envelope / that field only |
| `oklab-fixed-y-characterization-reviewer-b-v1` | `reviewer_b_report_sha256` | `dartwork-mpl-oklab-fixed-y-characterization-reviewer-b-v1\0` | complete envelope / that field only |
| `oklab-validation-oracle-truth-bootstrap-reviewer-a-v1` | `reviewer_a_report_sha256` | `dartwork-mpl-oklab-validation-oracle-truth-bootstrap-reviewer-a-v1\0` | complete envelope / that field only |
| `oklab-validation-oracle-truth-bootstrap-reviewer-b-v1` | `reviewer_b_report_sha256` | `dartwork-mpl-oklab-validation-oracle-truth-bootstrap-reviewer-b-v1\0` | complete envelope / that field only |
| `oklab-fixed-y-characterization-review-acceptance-v1` | `acceptance_sha256` | `dartwork-mpl-oklab-fixed-y-characterization-review-acceptance-v1\0` | complete tracked acceptance / that field only |
| `oklab-validation-oracle-truth-review-acceptance-v1` | `acceptance_sha256` | `dartwork-mpl-oklab-validation-oracle-truth-review-acceptance-v1\0` | complete tracked bootstrap acceptance / that field only |
| `oklab-authoring-execution-snapshot-archive-v1` | `execution_snapshot_archive_sha256` | `dartwork-mpl-oklab-authoring-execution-snapshot-archive-v1\0` | complete durable snapshot archive / that field only |
| `oklab-authoring-policy-preselection-v1` | `preselection_envelope_sha256` | `dartwork-mpl-authoring-policy-preselection-v1\0` | complete envelope / that field only |
| `oklab-authoring-policy-approval-entry-v1` | `entry_sha256` | `dartwork-mpl-authoring-policy-approval-entry-v1\0` | complete immutable entry / that field only |
| `oklab-authoring-policy-registry-index-v1` | `registry_payload_sha256` | `dartwork-mpl-authoring-policy-registry-index-v1\0` | complete membership index / that field only |
| `oklab-authoring-external-input-bundle-v1` | `external_input_bundle_sha256` | `dartwork-mpl-oklab-authoring-external-input-bundle-v1\0` | complete manifest / that field only |
| `oklab-authoring-execution-inputs-v1` | `execution_inputs_sha256` | `dartwork-mpl-oklab-authoring-execution-inputs-v1\0` | complete record / that field only |
| `oklab-authoring-archive-promotion-provenance-v1` | `promotion_provenance_sha256` | `dartwork-mpl-oklab-authoring-archive-promotion-provenance-v1\0` | complete nested promotion record / that field only |
| `oklab-authoring-review-subject-v1` | `subject_manifest_sha256` | `dartwork-mpl-oklab-authoring-review-subject-v1\0` | complete manifest / that field only |
| `oklab-authoring-review-control-bundle-v1` | `review_control_bundle_sha256` | `dartwork-mpl-oklab-authoring-review-control-bundle-v1\0` | complete manifest / that field only |
| `oklab-authoring-review-evidence-bundle-v1` | `review_evidence_bundle_sha256` | `dartwork-mpl-oklab-authoring-review-evidence-bundle-v1\0` | complete manifest / that field only |
| `oklab-authoring-public-review-log-v1` | `public_review_log_sha256` | `dartwork-mpl-oklab-authoring-public-review-log-v1\0` | complete public structured log / that field only |

Every row hashes `domain_tag.encode("ascii") + canonical_json(hashed_object)`;
the table writes `\0` as the one terminal NUL byte. Canonical hash input never
contains a terminal newline. Serialized JSON files contain exactly one terminal
newline. Nested entry/result hashes retain their separately stated domains and
are not replaced by this table. In particular,
`arithmetic_trace.records_sha256` uses
`dartwork-mpl-authoring-arithmetic-trace-v1\0` over its inline complete records
array; it is a nested environment preimage, not an omitted sibling completion
artifact.

The external-input, review-control, review-subject, and review-evidence bundle
rows, durable execution-snapshot archive, nested `ExecutionInputs`, and nested
archive-promotion provenance follow their stated capture/publication algorithms
rather than the primary-report sequence below. Terminal results are embedded in
public structured review logs; private provider transcripts are not evidence
objects. Oracle results, shipped exact surfaces, and the side-by-side
manifest are comparison subordinates, not independent primary completions.
The legacy compatibility asset, baseline acceptance and authority marker, frozen envelopes,
fixed-Y scientific payloads, validation truth, other tracked acceptances,
snapshot archives, policy entries, and the membership index use
their explicit create-only/guarded-index-replacement lifecycles. Archive promotions intentionally
mutate tracked state and are exempt from the ignored-output post-write
fingerprint-equality sequence.

Primary completion output inventory is closed by schema profile; the same
ordinary set applies to ignored and explicitly tracked create-only producers:

| Profile | Schemas | Ordinary non-primary outputs |
|---|---|---|
| `artifact-map` | `oklab-authoring-comparison-report-v1` | every comparison artifact through exact `artifacts` |
| `named` | `dartwork-mpl-legacy-v5-baseline-extractor-evidence-v1` | exactly `compatibility_asset_path` |
| `named` | `dartwork-mpl-legacy-v5-baseline-cross-extraction-v1` | exactly `candidate_compatibility.path` |
| `named` | `oklab-fixed-y-characterization-generation-evidence-v1` | exactly `characterization_payload_path` |
| `named` | `oklab-fixed-y-characterization-evidence-v1` | exactly `characterization_payload_path`; tracked payload is an input |
| `named` | `oklab-authoring-discrete-policy-characterization-v1` | exactly `visual_strip.path` |
| `none` | `oklab-authoring-proposal-v1`, `oklab-authoring-frozen-v1`, `oklab-authoring-policy-preselection-v1`, `oklab-authoring-discrete-policy-characterization-verification-v1`, `oklab-authoring-admission-policy-characterization-verification-v1`, `oklab-authoring-admission-policy-characterization-v1`, and every A/B outer reviewer-report schema | none |

Content-addressed `input-bundles/`, `review-controls/`, and `review-evidence/`
stores are governed separately and excluded from ordinary output inventory.
No schema outside the comparison report acquires an implicit `artifacts` key.

Every evidence invocation begins with this common prefix:

1. parse arguments, select the recognized schema, producer profile, canonical
   primary path, ordinary-output profile, and tracked/ignored lifecycle, and
   reject every unknown or mixed row;
2. for an ignored lifecycle, require output outside the worktree or exactly
   Git-ignored, take the exclusive canonical-output-root writer lease, remove
   and directory-sync the stale primary, and create a fresh private output
   tmpfs; for a tracked lifecycle, perform only the existing-target exact early
   no-op/fatal check and never delete a tracked leaf. Create the private tmpfs
   without taking or upgrading to a repository writer lock;
3. acquire one repo-scoped cooperative source-read guard. Under it, complete
   the source-snapshot transaction and capture the exact external-
   input bundle before importing candidate modules; for a review, also publish
   its immutable control bundle before launching the reviewer. Record
   `source_fingerprint_start` and construct `execution_inputs` from the
   applicable hashes. An ignored lifecycle retains this guard through handoff,
   both live end checks, publication, and post-write validation. A tracked
   lifecycle retains it through handoff and both live end checks, then releases
   it before separately acquiring the repository writer guard below. A
   cooperative read guard is never upgraded in place.

A native non-review producer then follows this branch:

4. launch only from the immutable snapshot, verified input bundle, closed
   startup contract, and broker. The child writes only profile-declared scratch
   and ordinary leaves. After its operation, it closes ordinary leaves,
   enumerates and validates the exact `artifact-map`/`named`/`none` set,
   constructs the complete public primary with every schema-defined
   end/post-write fingerprint field set to the expected start value, closes it, removes all scratch, and
   writes/closes the private terminal manifest last. Immediately before stop,
   the tmpfs contains only structural parent directories, the declared ordinary
   regular leaves, the one primary, and the one private manifest; an empty or
   extra directory/file is fatal;
5. at the one terminal stop, the supervisor never resumes user space. It
   kills/reaps, copies and fully seals every manifest member, rehashes and proves
   exact profile/primary/manifest set equality, and destroys tmpfs. The child
   cannot inspect the live checkout; its expected fingerprint copies gain
   meaning only from the following outer checks;
6. still under the source-read guard, rehash the snapshot and input bundle, take two
   consecutive real live end fingerprints, and require both to equal the start
   value stored in the sealed primary. On mismatch, publish no final member and
   exit 2;
7. for an ignored lifecycle, under the still-held output-root writer lease and
   source-read guard, invoke only the static hash-bound byte publisher over
   sealed leaves. It installs, fsyncs, rehashes, and bottom-up-directory-syncs
   every ordinary output first, then publishes and syncs the primary last.
   Immediately take a real post-write live fingerprint and rehash the external
   input bundle. Unless both equal the stored start values, unlink and sync the
   primary, exit 2, and leave subordinate bytes non-authoritative;
8. for a tracked lifecycle, release the source-read guard after step 6, then
   acquire the repository exclusive writer guard in a new lock acquisition.
   Reconstruct and require the same start snapshot/input closure and target
   absence under that guard; a changed non-target or unexpected target fails
   without writing. Use the existing durable create-only primitive over sealed
   leaves, ordinary targets first and primary marker last. The final fingerprint
   must equal the exact reviewed start state overlaid with precisely the
   declared target mode/bytes, not the pre-write start fingerprint. Recovery
   admits only the lifecycle's already specified subordinate-prefix states and
   retries them under the writer guard. Release-order is the reverse of
   acquisition; no execution may hold a repository read lock while requesting
   its writer lock. Promotion independently repeats every
   source/input/control/evidence guard.

A reviewer/`ReviewExecution` invocation instead retains the existing separate
provider lifecycle: it runs from its immutable subject/control bundles, seals
the one terminal result in the public structured log, publishes the post-run
review-evidence bundle through its content-addressed transaction, derives the
outer report from that terminal result, performs the same two live end guards,
publishes the report primary last, and performs the real post-write guard.
Reviewer schemas have ordinary profile `none`; their provider log, control, and
evidence bundles never become ordinary terminal-manifest members. No reviewer
process is retroactively described as an environment-v3 computation.

Ignored files are output or cache only unless their canonical paths, roles, and
raw bytes were captured into the verified external-input bundle before the
consumer started. A live ignored path is never an input root. Merely finding an
old HTML/JSON file is never evidence that the current invocation passed.

## 11. Tests and independent oracles

### 11.1 Baseline bootstrap

- Materialize exact predecessor commit
  `6be8cb56b8752e03515101caa7ae2f6c52cc13dc` with candidate and dirty-
  worktree paths unavailable. Assert the mixed CIELAB/OKLCH generator and
  runtime multi-hue selector are present and every claimed target-only symbol
  and asset is absent.
- Hash the raw predecessor commit payload, parse its literal root-tree OID, and
  recursively reproduce every raw tree/blob object and the exact root
  `af45c52a5f56091bed9cea7609cb67d74852a0e5` independently of the 942-leaf
  manifest. Create a physical empty directory solely by removing an
  absent-at-HEAD overlay file and prove it contributes no tree entry; injecting
  Git's empty-tree OID, using worktree stat modes, or changing raw Git basename
  ordering must fail even when the leaf manifest still agrees.
- Run two independently implemented extractors over that materialization and
  require byte-identical canonical values for every one of the 18 surfaces,
  including all 72 multi-hue result/index rows. Extractor A must exercise and
  instrument the predecessor public/runtime path; extractor B must derive the
  same contract through an independently implemented static/data parser and
  selector replay. They may share the sealed predecessor bytes and canonical
  output schema, but no extraction helper, intermediate result, imported
  candidate module, or computed selector row.
- Make candidate migration modules import-fatal and prove baseline extraction
  still succeeds. Mutating any predecessor literal or extractor result must
  change the relevant baseline hash or fail cross-extraction.
- Exercise the two special semantic-batch evidence variants. Preinstall must
  reject shipped/side-by-side evidence and require exactly all six preinstall
  output roles. Prove the two extractor candidates are distinct non-aliased
  regular files produced without cross-read access, reject any candidate byte
  mismatch, and independently reconstruct the cross-extraction manifest before
  accepting the copied candidate. Promotion must require the complete reviewed
  preinstall closure, snapshot archive, approval, byte-identical promoted
  asset, and acyclic acceptance. Reject a promotion acceptance that embeds or
  purports to predict its own promotion-review hashes.
- Recompute the baseline four-key approval and its domain-separated walkthrough
  from the candidate, cross-extraction record, both extractor evidence files,
  preinstall subject/A/B sequence, and snapshot archive. Mutate or omit each
  input, use an approval for another lifecycle, add an acceptance/promotion
  self-reference, or change the approval blob/path and require atomic failure.
- Complete promotion A then B on one frozen subject, archive the full promotion
  subject/report/input/control/evidence/token/snapshot closure, recompute the
  post-promotion approval and finalization provenance, publish the authority
  marker last, and verify the whole graph offline. A commit containing the
  exact preinstall archive and pair before B or without the marker must fail.
  Substitute a valid A/B closure for different pair bytes; mutate, omit, or
  stale either report, terminal public log, historical input manifest/blob,
  control/evidence manifest/blob, A token, sequence field, snapshot leaf,
  approval, finalization provenance, or marker; and require failure even when
  an attacker rehashes an enclosing object but cannot reproduce the unchanged
  subject and all predecessor links. Reject an authority marker containing its
  own Git tree/commit, `baseline_authority_commit`, or a future review edge.
- Cut power before and after every promotion-review archive leaf/manifest,
  tracked approval, prerequisite barrier, marker install, and marker-directory
  barrier. Only an exact archive prefix or complete archive-plus-approval with
  marker absent may resume; any surviving marker without every exact durable
  prerequisite is fatal. Re-running finalization over the complete exact state
  must be an idempotent no-op.
- Reject a compatibility or authoring review whose source snapshot creates and
  consumes a baseline asset in the same semantic batch. The consuming batch
  must name a later exact HEAD in which the separately A/B-accepted baseline
  marker and every marker-reachable leaf are already present. For every
  accepted baseline path, mutate authority or
  current tree mode/OID/bytes, add an index/worktree overlay, break `H -> A`
  first-parent ancestry (including second-parent-only reachability), or
  substitute `baseline_commit`/`baseline_git_tree_oid` for the
  distinct baseline-authority commit/tree and require failure.
- Add uncommitted earlier specs, ADRs, prototype source, and prototype JSON to
  the live source worktree and prove none enters the document-review capsule,
  baseline inputs, authority set, or public hash.

### 11.2 Compatibility isolation

- Rebuild the complete migration `source_records`, AST/JSON literal inventory,
  `tone_mappings`, and closed catalog recipe from exact predecessor objects.
  Require one-to-one ownership of every operational `Tone` leaf; non-tone
  recipe leaves remain governed by their separate closed reconstruction
  grammar. Mutate a source bit, locator, operation ID, mapping branch,
  intermediate float-hex, `tone_mapping_plan_sha256`, retired-mechanism ID, or
  catalog field and fail before compilation.
- Require all 58 actual mappings to use the upper branch: their minimum source
  L* is `12.0`, above the `8.0` toe. Cover the lower branch with separate
  synthetic below/at/above-toe fixtures, and cover values whose forward tone
  does not return the exact original L* bit after a cube/cube-root inverse.
  Acceptance must use
  exact forward-replay equality and must reject an implementation that replaces
  it with inverse-round-trip equality. Prove no legacy L* field or retired
  Fourier curve is reachable from the operational recipe accessor.
- Recompute the shipped observation from mapped encoded RGB produced after the
  exact final linear-channel clamp and predecessor OETF, then use
  the exact predecessor scalar decode, left-associated legacy-row dot, and
  divide-after-dot normalization. Exercise a vector for which dotting the raw-
  linear channels with the separately normalized row differs by one ULP; that
  generic association, observing pre-map channels, or changing clamp/OETF/
  decode order must fail compatibility replay even if its own metadata is
  rehashed.
- Preserve predecessor v5 golden/value tests, add compatibility trace/value
  tests during migration, and preserve those thereafter.
- Prove structurally that shipped `_generate`, `_cmaps`, and `_catalog` imports
  reach only the three named compatibility functions and the named shipped
  diagnostic renderer, never an authoring module.
- Monkeypatch `render_direct_oklch`, `render_fixed_relative_y_oklch`,
  `solve_max_chroma_for_relative_y`, `compile_authoring_family`, and
  `select_discrete_candidates` to raise. Compiling and querying every exact
  shipped surface must still pass. The non-shipped diagnostic branch may report
  a diagnostic-only error, but cannot alter an exact surface.
- Delete or mutate one frozen index row in a test fixture; build/runtime must
  fail without invoking selection.
- Run the exact 18-surface comparator after every semantic batch.

### 11.3 Polynomial and fixed-Y properties

- Compare polynomial evaluation with the canonical scalar conversion kernel
  over hue and `u` grids.
- Verify exact-rational coefficient hashes, square-free/GCD repeated-root
  handling, Sturm counts, and fail-closed bisection limits against an
  independently written oracle.
- Cover all six active sRGB faces, corners, endpoints, tangent/repeated roots,
  hue periodicity, and synthetic disconnected feasible intervals.
- Cover interior direct fixed-`L` disconnected components and prove the greatest
  request-bounded feasible chroma is selected.
- Exercise positive-normal/subnormal direct `L` and `C`; an interior scalar
  collapse to black/white or a positive-chroma bitwise neutral result must fail.
- Sweep the pinned hue set to enforce the direction-norm guard and verify that
  certificate units remain the canonical authoring `C` parameter.
- Mutate the hue-conversion ID and every requested/normalized/radians/cosine/
  sine/norm field independently; production, Cartesian oracle, projective
  checker, direct oracle, and endpoint verifier must all recompute the
  normalized-`math.radians` sequence and reject each mutation.
- Recompute `achieved_relative_y` through the exact five-operation association
  in production, strict loading, and both applicable independent oracles. Use
  the fixed vector
  `(0x1.c787db4043bdap-2, 0x1.12adb3735ac6ep-2,
  0x1.264ac77bf0110p-5)`, whose canonical result is
  `0x1.27f894954cca1p-2` while right association/`fsum` produces the next
  binary64 value; the alternate association and a self-consistently rehashed
  forged achieved-Y field must fail.
- Walk every authoring request/policy/result/oracle schema and require each
  binary64 leaf to have exactly one signed-zero class. Inject `-0.0` into
  lightness, target Y, requested chroma, every zero-admitting policy/bound/error
  and RGB leaf, and require rejection before branching, rational conversion,
  or hashing. In particular, negative-zero lightness/target Y cannot enter an
  endpoint branch and negative-zero RGB cannot manufacture a bitwise
  anti-collapse difference. Accept signed zero evidence only when its input or
  independently recomputed bits require that sign; canonical exact-zero fields
  accept only positive zero. At endpoint mapped `C=+0.0`, exercise negative
  direction components and require production plus endpoint-verifier
  `oklab_ab` to preserve exactly the multiplication-derived zero signs.
- Assert raw gamut with semantic tolerance zero and both absolute and relative
  Y residual guards, including crafted positive-normal and positive-subnormal
  cases whose available witness misses the relative guard and therefore must
  fail rather than collapse to the black endpoint.
- Craft positive fixed-Y chroma that disappears in scalar arithmetic; bitwise
  equality with the stored neutral raw or encoded baseline must fail.
- Construct distinct algebraic candidates whose binary64 witnesses tie; prove
  exact objective ordering, and merge only coordinates proven equal while
  retaining the complete sorted source union.
- Exercise merged neutral+cap, face+cap, face+stationary, and multi-face
  candidates. Independently derive the complete ordered `roles` tuple and
  source-identity candidate order; reject the old singular `role` key and any
  empty, duplicate, missing, extra, reordered-role, reordered-candidate, or
  wrong-ordinal certificate even after all enclosing hashes are recomputed.
- Mutate every field of the stored `ExactRationalCoefficientRecord` while
  retaining its old digest, and mutate a digest while retaining the record;
  production loading, the projective checker, and the direct oracle must first
  reject structural disagreement and then independently reject hash mismatch.
- Construct two proven-distinct `ProjectiveRootCluster` identities whose exact
  midpoints round to the same `projective_u.float_hex`. Both parity records must
  survive with different identity hashes in cluster-ordinal order and
  contribute independently to root count/hash; rounded `u` must not merge them.
- Use the independent exact-rational Cartesian cubic oracle in section 5.6 to
  count, isolate, classify, and record every real `L` root without importing
  production polynomial or root code.
- Require every fixed-Y oracle query to bind its own chroma slice and exercise
  lower, request, upper-successor, equality, and constrained roles.
- Verify direct and fixed-Y black/white endpoint results only with the separate
  scalar endpoint verifier, including production-result hash linkage and exact
  mapped-chroma, `oklab_ab`, raw/encoded/Y, and reduction fields; polynomial-
  oracle dispatch must be rejected.
- Compare interior direct results with the separately transcribed fixed-`L` face oracle;
  prove complete component classification and request-bounded maxima without
  importing production helpers.
- Mutate each direct face-coefficient preimage/domain, direct query input hash,
  reconstructed aggregate coefficient hash/row, maximum source-identity union,
  production or oracle interval, intersection, common factor, equivalence hash,
  active face, candidate kind, oracle directed lower/upper bound, side of the
  exact rational containment chain, mapping mode, production gap/budget, and
  PASS verdict independently; every mutation must fail.
- Give production and oracle byte-different valid `2**-48` and `2**-96`
  brackets for the same irrational root and require PASS; mutate rank,
  polynomial ID, root ordinal, or either bracket to name another/no root and
  require failure. Overlap without same-polynomial ordinal proof or a valid
  common-factor proof must fail.
- Cover a coincident multi-face root with a trimmed monic square-free GCD, exact
  singleton `C=0` and requested-`C` sources, and distinct algebraic roots that
  round to one binary64 value. Changing a valid production bracket must leave
  oracle isolation/components/maximum bytes unchanged except for the later
  cross-equivalence proof. Architecture tests make production intervals
  unavailable until oracle maximum selection is complete. Independently
  reconstruct every complete canonical boundary-source union; delete, add,
  duplicate, or reorder one identity at a coincident face/endpoint, mismatch a
  tuple across neighboring components, or insert/delete/reorder a component,
  and require failure after recomputing every outer hash. Reject wrong
  `2*m-1` length or point/open parity, a two-point encoding for the degenerate
  zero-chroma request, and merging proven-distinct roots merely because their
  binary64 values agree. Require null `interior_anchor` for every rational or
  irrational point component and one strict rational anchor for every open
  component. For a crossing and a tangent irrational boundary, independently
  verify exact point signs and reject an implementation that copies either
  adjacent open-cell classification. Inject a rational endpoint as its own
  anchor, null into an open interval, or an endpoint/out-of-interval rational
  and require failure even after recomputing outer hashes.
- Construct an analytically feasible direct request whose scalar witness violates
  a postcondition and require a closed error with no inward or oracle result.
- Prove the global lower/upper boundary relation and its outward gap on the
  oracle grid and targeted face cases. Separately test requested-equality
  witness shortfall and constrained-reduction lower/upper certificates; never
  compare a deliberate gamut-reduction amount with a numerical-error budget.

### 11.4 Offline generation, discrete selector, and frozen replay

- Compare `authoring-family-lut-v1` with a separately written reference on
  synthetic direct and fixed-Y recipes: all 4097 dense positions, arc prefixes,
  inverse-resampled parameters, re-rendered points, endpoint order, and all 256
  lowercase hex values must match exactly.
- Cover zero/non-finite arc, an exact prefix target, zero-length dense segments,
  half-even channel quantization, typed renderer mismatch, and policy-field
  mutation.
- For small synthetic LUTs, brute-force every combination and compare the full
  objective/tie-break key.
- Cover L/chroma boundaries, duplicates, achromatic rows, insufficient domains,
  invalid/bool `n`, `n=1`, and search-budget exhaustion.
- Repeat in fresh processes and require byte-identical result serialization.
- Cover exact half-even `q9` cases, non-contiguous duplicate RGB values without
  shortening the full-row arc, `n=2` CV zero, non-positive gap-mean failure,
  cache-hit accounting, and the exact budget boundary before and after
  exhaustion.
- Prove selector source has no CIELAB/CIEDE2000/CVD imports or identifiers.
- Mutate each independent admission floor and require a fail-closed result.
- Mutate the selector algorithm ID, candidate-domain count, record, ordering,
  and digest independently; the captured discrete policy verifier and later
  `promotion-replay` must independently rederive and reject each change.
- Exercise exact validation-oracle component IDs, CVD round trips, reference-
  suite failure, per-metric pair ties, and common mode/pair ties.
- Prove `ValidationOraclePolicy` remains exactly eleven keys and V1 emits no
  WCAG policy/result/threshold field or accessibility verdict. Inject
  `_luminance`, WCAG role/ratio/threshold helpers, `ensure_contrast`, rounded
  WCAG coefficients, or a policy-shaped twelfth component into coordinate,
  gamut, selector, validation input, admission, or `all_machine_checks_passed`
  and require strict architectural failure. Separately run the unchanged
  predecessor public-API/validation tests to prove existing `ensure_contrast`
  and `TEXT_CONTRAST` behavior was preserved, without treating that regression
  pass as a new replayable WCAG policy or a general accessibility certificate.
- Mutate validation-oracle source/constant/reference-suite roles, paths, hashes,
  counts, and verdicts; `validation_input_sha256` and replay must reject each.
- Reject any bootstrap-acceptance path/hash added to the four-key scientific
  truth record. Construct two valid approval histories over byte-identical
  truth and require identical oracle evidence, `validation_input_sha256`, and
  `payload_sha256` but distinct policy-approval/public-reproducibility/proposal
  identities. Conversely, mutate or break either governance copy of the
  acceptance hash, the fixed-path acceptance/archive, or its truth cross-link
  and require proposal creation/promotion to fail without changing the
  scientific hashes.
- Mutate the create-only validation truth's complete constants, vector bytes,
  expected result hash, source hash, ID, path, or self-hash while making the
  current oracle agree with the mutation; admission must still fail against the
  separately accepted truth rather than accept a self-consistent rewrite.
- Reject V1 admission when either truth or fixed-path bootstrap acceptance is
  absent. Reject bootstrap if either target already exists in the reviewed
  snapshot; if acceptance exists alone after a crash, permit only exact truth
  installation from its archived candidate blob. Differing overwrite is fatal
  and byte-identical replay is a validated no-op.
- For truth bootstrap, mutate, omit, add, reorder, or mislocate any subject,
  A/B historical input/control/evidence/token, snapshot archive, sequence,
  promotion, approval, candidate, source, vector, raw/self-hash, or exact role;
  every case must fail. Prove the reviewer and installer cannot import/read
  authoring construction, selectors, proposals, frozen families, candidate
  rows, or the live ignored candidate during installation.
- Mutate source, constants, vectors, expected results, and current oracle
  consistently while leaving the tracked bootstrap authority unchanged; the
  original rewrite attack must fail. Mutate every field of the truth
  acceptance walkthrough/self-hash and downstream acceptance cross-link and
  require failure, then rerun all 18 shipped-surface comparisons unchanged.
- For each reference member, verify the exact 12-key validation-result golden
  preimage, domain's single terminal NUL, and absence of a terminal newline.
  Mutate each field, add/remove a key, swap the domain, reorder/change one
  derived reference hex, or reuse equal metrics for a different member; the
  nested hash and enclosing characterization must fail.
- Reject selection before a valid prior policy-preselection envelope; mutate
  registry order, policy bytes under a reused ID, characterization/review links,
  maintainer attestation, or either approval-entry hash independently.
- Mutate each preselection component's exact preimage or domain and every field,
  order, nested digest, rationale/reference row, forbidden candidate field, and
  self-hash in both closed policy-characterization schemas.
- Decode and reconstruct all 256 characterization hex rows, coordinates,
  duplicates, peak, admitted domain, and all `n=1..8` selector results; mutate
  each recipe/generation/renderer/LUT input, actual LUT hash, and derivation
  independently. Strictly parse every admission-reference authority asset,
  reject inline/caller-supplied rows and a candidate copied or renamed as a
  reference, replay every derived member through `VALIDATION_ORACLE_V1`, and
  derive member counts and all minima. Run those two replays only through their
  exact environment-v3 verification profiles; mutate either evidence schema,
  replay field/hash, raw/self-hash, provenance, owner, startup, trace, source
  snapshot, or terminal handoff and require no policy review or promotion.
- Mutate independently every registry-to-characterization-to-review equality for
  family, kind, policy ID/hash, and characterization hash, plus the
  verification-evidence raw/semantic hashes and common execution snapshot, the
  preselection-to-discrete generation ID and preselection-to-admission complete
  validation policy/hash; each break must fail.
- For policy promotion, omit Reviewer A's one verification-evidence input or
  null either evidence hash; substitute a zero-record manifest; mutate, omit,
  duplicate, or add any A/B historical input,
  control, or evidence manifest/blob role; mismatch B's embedded A closure or
  either recomputed `ExecutionInputs`; every case must fail. Prove the archive
  promoter performs strict hash/schema/DAG verification only and cannot import
  the generator, selector, OKLab conversion, CIEDE2000/CVD, NumPy, or a color
  arithmetic helper.
- Exercise registry guarded compare-then-replace with stale expected bytes, two
  concurrent guard-obeying writers, guard acquisition/release failure, and an
  injected non-cooperating write at each comparison/rename/postcheck boundary.
  The two conforming writers must serialize and the stale one must fail; the
  hostile fixture must never be described as atomic CAS and must fail the first
  postcondition that observes it, while acknowledging that an intervening
  hostile write can be overwritten. Also cover crash-before-switch immutable
  orphans, tuple/hash collisions, byte-identical replay, invalid reference
  ordering/revision, missing linked bundles, and post-install archive mutation.
  Only immutable entries plus the one validated guarded index replacement may
  gain authority.
- Reject every duplicate/unknown/missing proposal and frozen key; mutate each
  subordinate digest, family/filename binding, LUT/index/hex linkage, review
  reference, and frozen-envelope hash independently.
- Mutate comparison/A/B roles, public attempt/instance IDs, verdicts, findings, family paths,
  start/end/post-write fingerprints, snapshots, harness/prompt/scope/public-log
  hashes, completion token, proposal/comparison links, A predecessor, artifact
  map, and every domain-separated self-hash independently. Reused instances,
  B creation before a valid guarded A PASS, and promotion after any later
  finding must fail.
- For every review kind and both roles, reject a missing, duplicate, non-final,
  or non-canonical-JSON public terminal result; independently mutate its
  self-hash, containing-event hash, public-log ordinal/hash pointer,
  attempt/instance/role/control cross-link, or closed fields. Mutating only
  terminal verdict/findings or only outer verdict/findings—even after
  recomputing shallow hashes—must fail, and the dependency order must remain
  control → terminal result/public log → evidence → report with no backward
  hash.
- Inject provider run/session IDs, raw conversation/tool output, hostname,
  absolute paths, PIDs, approval text, and each value's SHA-256/hex/base64 into
  private review transport. Require the public log/report/archive to remain
  free of every canary; any attempted public projection of one fails before
  publication.
- Attempt to construct review control bytes after reviewer execution, mutate a
  pre-run control after capture, omit B's token blob, mismatch subject/control
  bundle hashes, or change a control byte only in post-run evidence; all fail.
  Exercise the closed semantic-batch, both fixed-Y, and validation-truth-
  bootstrap review kinds, exact subject manifests, A/B envelopes, role tables,
  and restart behavior.
- Attempt alternate bundle manifest names, extra paths, symlinks, wrong file or
  directory modes in an ignored live materialization, hard-link any leaf to a
  sibling or outside path, non-`100644` tracked leaves, ambiguous root-vs-
  manifest paths, and missing/extra shared blobs for every input/control/
  evidence bundle. Cut power around every live-tree write, file/mode `fsync`,
  directory seal/sync, atomic root install, and final-parent sync; a visible
  live bundle must be absent or complete, and an exact existing tree must be
  re-synchronized before no-op. Canonical `manifest.json`, the exact content-
  addressed layout, live `0555`/`0444` sealing, and tracked Git-mode rules must
  each fail closed under the wrong representation; no tracked directory-mode
  assertion is permitted.
- For both fixed-Y stages, mutate or omit an archived subject/report/historical
  input/control/evidence blob, sequence link, maintainer walkthrough, raw or
  semantic payload hash, or acceptance self-hash. Installation must read only
  the preinstall archive, and no normative claim may pass without two complete
  tracked acceptances binding the tracked payload.
- Verify each fixed-Y acceptance after changing and then making the original
  checkout inaccessible. Mutate, omit, add, reorder, or remode every snapshot-
  archive singleton, capsule file, logical path, blob, and hash; recompute outer
  hashes after corrupting a status/index/patch/root/config/object/source
  preimage; deep offline reconstruction must still fail. Cover staged-only
  blobs, deleted tracked files, executables, symlinks, newline and non-UTF-8 Git
  paths, untracked files, A/B snapshot divergence, and missing/extra promotion
  roles.
- Encode the same loose Git object with a different valid zlib compression
  level, dynamic/fixed Huffman block, non-maximal stored-block split, alternate
  zlib header, dictionary flag, bad `LEN`/`NLEN`, wrong Adler-32 byte order, or
  trailing bytes. Every variant must fail byte comparison with
  `git-loose-zlib-stored-v1`, while repeated canonical capture produces the
  identical snapshot-archive hash and self-addressed path.
- For every lifecycle stage, reject an external-input bundle with an extra or
  missing role, path alias, raw-byte/length/blob mismatch, omitted blob,
  symlink, capture race, overwrite collision, or post-execution mutation. Reject
  a review report without its complete manifest/blobs or with mutated
  harness/prompt/scope/public-log bytes, and prove B's bundle contains A's exact
  report, historical input/control/evidence bundles, and completion token.
- Delete, duplicate, reorder, or add one oracle-result entry; change one sample
  kind/index/result hash/query role, summary count/ID/boolean, or raw artifact
  hash; exact 256-sample derived coverage and promotion must fail.
- Rebuild the scalar-kernel constants record with exactly 49 binary64 leaves
  and require its canonical
  encoding to be exactly 4,121 bytes with golden digest
  `3e06097b73e567486ef929ce55bff8fd88011f049b8d6f034860398e438da0db`.
  Mutate every leaf independently; inject negative zero, a number/hex bit
  mismatch, shape/order/key drift, a validation/coefficient-domain record, or
  a self-consistent forged record plus outer hashes. Require failure against
  the frozen literals/golden digest. Require one binding per standalone
  artifact, all four oracle/verifier algorithm references to resolve to it,
  independent private
  transcription by each implementation, no producer/shared-constants import,
  and complete downstream hash-cascade recomputation.
- For projective and direct oracle records, independently mutate/re-hash each
  certified-coordinate link, direction component, production or recomputed
  `oklab_ab` element, independently derived or stored `neutral_reference_l`,
  raw RGB channel, encoded RGB channel, neutral raw/encoded channel, achieved
  Y, applicable residual, scalar association ID, projective-u algorithm ID,
  runtime hash, or replay-scope ID; every mutation must make PASS impossible
  even when the production witness and all outer hashes are made
  self-consistent. Include `C=+0.0` with a negative direction component and
  require the operation-derived `oklab_ab=-0.0` bit to pass while a caller-
  chosen opposite zero sign fails. A static import gate forbids either oracle
  from importing production conversion or
  constants objects.
- Exercise values immediately below/at/above both transfer breakpoints, a
  negative-LMS real-cube-root case, signed-zero cube root, the stored OETF
  exponent versus recomputed `1/2.4`, structural inverse `L` versus `L*1.0`,
  left-associated versus reassociated dot/Y operations, and mismatched accepted
  base-runtime hashes. Only the frozen association on the same accepted base
  runtime can claim bit replay.
- Delete, reorder, rename, or mutate any of the ordered 18 shipped surfaces or
  eight inventory totals; a true Boolean with one mismatch must fail. Mutate
  any required side-by-side role/reference or use stale docs assets; review and
  promotion must reject it.
- For fixed-Y recipes, mutate the topology contract, any dense/final target bit,
  a modeled-Y residual, or the direct-counterfactual link. For direct recipes,
  inject topology evidence. Both must fail, while a zero direct-vs-fixed visual
  difference remains valid because the counterfactual has no admission floor.
- For every characterization grid/trace/endpoint row, change retained
  `tone_seed`, `NeutralTone`, effective target, or one cross-link; reconstruct
  with `numpy.cbrt` or another inverse and require bit-level failure.
- Promote a fixture proposal, require exact LUT/selection/validation replay and
  a canonically unchanged payload, then prove runtime never imports or invokes
  generation, rendering, selection, or admission.
- Freeze a proposal, change the selector policy/implementation, and prove the
  frozen runtime output remains unchanged.
- Attempt a differing frozen overwrite and require no byte change; repeat the
  exact frozen bytes and require leaf plus bottom-up directory
  re-synchronization before an idempotent no-op. Crash after the complete
  tracked bundle but before the envelope, then require retry to revalidate and
  re-synchronize that prefix before installing the envelope. Shipped/frozen
  family-name collisions must fail before renderer or selector import.

### 11.5 Whole-system gates

- focused unit/property/architecture tests;
- full test suite;
- source-fingerprint path validation, start/end/post-write mutation injection,
  ignored input hashing, generated-artifact tampering, every schema-specific
  self-hash/domain swap, and completion-marker atomicity;
- fingerprint fixtures with newline paths, symlinks, staged-intermediate `MM`
  blobs, textconv/diff configuration, machine-local ignore/attribute state,
  replace refs/grafts, a changed Git executable/config, nonzero stages,
  intent-to-add, semantic index blob/mode changes, and independently changed
  index/worktree bytes;
- parse guarded index v2/v3/v4 and one-level split-index fixtures, verify
  trailers/bitmaps/path compression, and require full-index, split-index,
  stat-refreshed, and reordered/changed optional-extension forms of one stage-0
  state to produce byte-identical
  `git-index-v2-zero-stat-extension-free-v1`, fingerprint, capsule, and archive.
  Reject nested/missing `link`, bad checksum/padding/bitmap, unknown mandatory
  extension, `sdir`/sparse entries, special flags, nonzero stage, and any
  mismatch with registered `ls-files` views. Assert that neither live index nor
  shared-index bytes/name/path/hash occurs in any archive or Git object;
- exercise linked and ordinary worktrees with the original checkout hidden;
  inject canary comments, credential-bearing URL/pushurl values, and branch
  values into common/worktree config and prove no canary, raw config byte/hash,
  or old effective-config record exists anywhere in the successful archive or
  resulting Git objects. Comment/whitespace/remote-only changes must preserve
  the operational projection, fingerprint, and archive identity; object-format
  or bare-state changes, unknown keys, includes, filters, promisor/partial-clone
  state, and projection/synthetic-config hash mutation must fail;
- mutate every exact argv token/order/cardinality/stdin/environment row, every
  operation-registry expansion, and every Git-capsule path/mode/field, object
  payload, or sort position; require the capsule object set to be the exact
  union of the HEAD closure, every distinct stage-0 index blob, and the
  precisely required authority-chain/tree objects, including a staged-only
  object absent from HEAD. Exercise `A==H`, a later first-parent descendant
  `H`, a merge whose first-parent chain reaches `A`, a merge where `A` is
  reachable only through a second parent, a path that chooses a valid but
  non-first merge parent, a missing intermediate commit, a malformed/non-parent
  chain step, a missing authority tree/blob, an extra parent-history object,
  and an unrelated `H` with copied byte-identical authority paths; only the
  first three may pass, and the two conforming captures of the merge fixture
  must serialize the same unique first-parent path and capsule bytes;
- Recompute HEAD or authority tree manifests after swapping any record field,
  adding a count/LF/tree-entry record, sorting decoded text instead of unsigned
  raw paths, hashing a symlink's dereferenced target, truncating an OID, or
  admitting a gitlink; each alternate preimage must fail the one shared
  `dartwork-mpl-head-tree-v1` algorithm even if its own outer hashes are
  self-consistent;
- introduce undeclared staged, unstaged, deleted, executable, symlink,
  newline/non-UTF-8, or standard-untracked paths and require failure before any
  durable manifest/blob publication with no raw path/content in diagnostics.
  At a declared path, stage secret bytes while leaving reviewed safe worktree
  bytes and require the `I != H => I == R` implication to fail before any
  publication. Exercise an unchanged declared `(H,H,H,H)` source alongside the
  four admitted deviation forms `(H,H,R,R)`, `(H,R,R,R)`,
  `(ABSENT,ABSENT,R,R)`, and `(ABSENT,R,R,R)` forms, plus deletion and index-only-add
  rejection. A declared untracked source may pass; after hiding the original checkout and
  common Git directory, offline verification must rederive the seven-field
  fingerprint, complete `H/I/W/R` relation, canonical index, and hash DAG. Old raw-config or
  undeclared-worktree archive records must fail promotion;
- for the current spec/ADR subject, attempt to start review directly in a
  feature worktree containing the two documents plus any one unrelated tracked
  edit or untracked path and require rejection before review or archive output.
  Reconstruct an isolated no-alternates capsule from the exact HEAD, overlay
  only the two regular `100644` document bytes, and require its complete union
  to satisfy `D=A` with exactly two
  `(H,I,W,R)=(ABSENT,ABSENT,R,R)` deviations and every
  other path at `(H,I,W)=(H,H,H)` with `R` undefined. Adding, staging, deleting, remoding, or mutating any third path in
  the capsule must fail; changing an unrelated byte only in the live source
  worktree must neither enter nor change the frozen capsule or any public hash;
- inject change-and-restore races during source capture, mutate the detached
  Git capsule,
  and attempt original-worktree, undeclared source, escaping symlink,
  subprocess, and FFI reads; snapshot validation must publish nothing;
- environment-provenance mutation of the native supervisor/seal/VM/process-
  split, either Python startup, control-preparation/base/invocation handoff,
  runtime-import manifest, receipt/event, terminal-handoff, or launch-
  environment policy,
  process executable/loader, Python runtime, NumPy wheel/core/build/CPU
  dispatch, every scalar extractor, frozen stdlib-module barrier/root/alias,
  base loaded-image callback history, two-namespace debugger-rendezvous union,
  continuous-VM capability/ledger and
  exec-persistent credential/writer-boundary reconciliation, mapping
  projection, and multi-role binding,
  libm provider, every literal subnormal record/vector shape/extractor,
  determinism variables, base-runtime hash, invocation-specific runtime hash,
  selected-artifact projection, invocation profile, project execution policy/
  namespace/event/import records, complete computation broker-read array/count/
  digest, base-prefix boundary/digest, and complete base stdlib/module/
  dependency/mapping closures,
  used-
  distribution manifest, and arithmetic trace; copying a full proposal
  closure/trace into comparison or a producer closure into verification must
  fail. Exercise built-in, frozen, stdlib-file, and sealed-file native
  math origins. For stdlib math, mutate any four-field projection member,
  substitute a different closure row, omit the `math` alias, or add aliases to
  `math_origin`; for native math, break any origin-to-no-load-handle-to-
  `PyInit_math`-address-to-mapping-to-tagged-identity link. Inject legacy
  `math_module_sha256`, wrong/null `process_executable_role`,
  `process_loader_role`, `runtime_library_role`, `math_provider_role`,
  `numpy.multiarray_role`, `math_module_role`, or nested `math_origin.role`,
  including a different existing role with all shallow hashes consistently
  rebuilt, and require strict failure for every origin-inconsistent role
  combination;
- launch both preparer and computation children from a hostile inherited
  environment containing
  alternate `PYTHONHASHSEED` values including `random`, `LD_PRELOAD`, multiple
  `LD_AUDIT` entries, other `LD_*`, `GLIBC_TUNABLES`, locale, allocator,
  Python-path/site, NumPy-feature, and thread overrides. Require each child to
  receive only its exact from-empty behavior record plus the one role-resolved
  sealed `startup-audit` leaf; mutate any behavior value, role/identity, behavior hash,
  raw private audit path resolution, or add/duplicate a key and require failure
  before Python. Two accepted launches must use the same fixed integer hash
  seed and byte-identical public launch-environment record;
- for both no-site startup fixtures, mutate, remove, duplicate, or reorder every
  argv literal/role; substitute `-I`, `-E`, `-c`, `-m`, stdin/interactive mode,
  an operand/trailing token, wrong bootstrap, or nonempty/wrong cwd. Add a
  second bootstrap-directory leaf or alias, `.pth`, `sitecustomize`,
  `usercustomize`, `PYTHONSTARTUP`, `PYTHONPATH`, `PYTHONHOME`, or shadow module
  in hostile cwd/bootstrap/site roots and require that no sentinel executes or
  file byte is consumed before the broker. Mutate every flags, pre-broker
  input/module, path-stage, finder/hook/cache record, preparer stdlib/native
  closure, count, order, and digest;
  invoke `site.main`, attempt a non-cached pre-broker import/read, reorder a
  stage, change import state after broker-ready, or alter it before handoff and
  require no owner. Prove actual `hash_randomization=0`/UTF-8/no-site flags,
  each one-bootstrap-script exception to broker reads, and that any open/read/
  import/reload/alias of either bootstrap path or leaf after its `broker-ready`
  barrier fails without a broker row. Prove exact empty startup cwd
  `/proc` identity, stdlib/archive/root ordering, distribution-root coalescing,
  source-root-last, zero child-lifetime overlap, and byte-identical startup/base evidence across two accepted
  launches. Exercise both null and non-null `stdlib_archive`; for the latter,
  mutate its role/count/hash, remove or alter the matching container read, add
  a ZIP member/trailing byte, or load one module from it and require failure;
- attempt `invocation-request`, platform raw/attestation, both reviewed policy
  leaves, distribution metadata enumeration, `Distribution.files`,
  `locate_file()`, `uv.lock`, selected-wheel, installed-entry, stdlib-entry,
  shell-source, or private-index access before preparer broker-ready and require
  no owner. After broker-ready, require every such control read to resolve to a
  role-bound sealed preparer input and private append-only ledger. Require the
  first eight singleton roles in exact order: request, OS-release, CPU-info,
  platform attestation, project-execution policy, base-runtime-import policy,
  computation-input inventory, and provisioning witness. Require each later
  lock/wheel/metadata/located-entry/inventory leaf to open once, only fixed-import
  stdlib leaves to repeat, every role to use its exact policy, and the shell pair
  to be final and adjacent; mutate,
  omit, alias, repeat, reorder, read late, or substitute any leaf and require no
  owner. Mutate the private transfer manifest/index schema, count, hash, public
  template, or terminal set and require failure;
- strict-parse `ComputationInputInventoryV1`; mutate an exact key, availability,
  leaf-ID grammar/ordinal, source/external role/path/count/hash, array order,
  union membership, count, or digest and require failure. Exercise required,
  unused optional, and used/unused `data_files` rows; reject an uncategorized or
  multiply categorized source, a control-only/computation-pre-broker row in the
  computation index, a future observed read added after preparation, a brokered
  read outside inventory, a post-startup computation-bootstrap reopen by path
  or leaf alias, or a realized non-module read outside `data_files`.
  Reconcile the final realized stream to the exact static six-source union;
- feed the memory-safe wheel provisioner golden stored and raw-DEFLATE wheels,
  then adversarially mutate every EOCD/disk/count/offset/size boundary, central
  and local signature/field agreement, flag, method, CRC, compressed/uncompressed
  size, local range order/overlap/gap/prefix/trailer, extra/comment/descriptor,
  UTF-8/name/case/path/type attribute, expansion/member/total quota, and final-
  block/padding condition. Exercise truncation, ZIP64, encryption, malformed and
  quadratic DEFLATE, bombs at/beyond each exact bound, and checked-integer
  overflow under sanitizers/fuzzing; no malformed archive may escape the parser,
  allocate/write beyond quota, or produce two installed trees. Positive-golden
  both locked NumPy 2.2.6 CPython-3.12 manylinux wheels—x86-64
  `fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249`
  and AArch64
  `f2618db89be1b4e05f7a1a847a9c1c0abd63e63a1607d892dd54668dd92faf87`—
  whose RECORD members contain respectively 876 and 875 uniform CRLF-delimited
  rows, plus bounded folded `License`/`Description` and LF-delimited RECORD
  fixtures. Strict-parse LF-only metadata headers and per-file uniform LF-or-
  CRLF RECORD delimiters/CSV quoting; reject orphan continuation lines,
  continuation/count/physical-line/logical-field/header-block quota overflow,
  duplicate or folded `Metadata-Version`, `Name`, `Version`, or
  `Root-Is-Purelib`, CR/NUL/disallowed control, malformed/missing header/body
  separator, bare/mixed/missing-terminal RECORD delimiters, field count/quote, path alias,
  algorithm/base64/size, missing/extra/directory/self row, `.data`, generated
  script/bytecode, symlink/special member, collision, and wheel/lock identity.
  For `uv-lock-toml-parser-v1`, cover TOML-1.0 duplicate/redefined keys/tables,
  malformed ignored values, wrong version/revision/source type, duplicate used
  package tables, zero/two guarded archives, multiple same-digest mirror rows,
  and distinct unselected platform-wheel hashes; only the unique guarded hash
  match may select while unselected rows remain private.
  Mutate every `WheelProvisioningWitnessV2` key/order/count/hash/member mapping,
  installed byte, root role, public artifact identity, or selected-profile
  cross-link and require failure. Mutate/omit the request's
  `base_import_profile_id`, select a row whose Python/platform key does not match,
  or provision a missing/extra artifact and require failure. Prove no external installer/cache/index/network
  or preexisting root is observed and that parser semantics are bound to the
  exact self-sealed supervisor executable/capability;
- keep the preparer alive, share one fd/mapping/tmpfs/credential, launch
  computation before reap, or expose any raw control/index/ledger leaf to it and
  require failure before computation Python. Inject NumPy/target code that
  scans frames/GC, guesses raw paths, lists/stats private roots, or attempts
  control reads; prove only the public handoffs/synthesized tree are
  reachable. Mutate either handoff/self-hash/cross-link, preparer startup/stdlib/
  mapping closure, runtime-import manifest/tree/listing/negative lookup, process-
  split/receipt policy, or base-ready closure and require the common-base chain
  to fail. For every manifest module binding mutate name/kind/loader/file-kind,
  suffix/package spelling, global uniqueness, fixed origin/spec/package path,
  explicit source/sourceless `cached`/present-`__cached__` value, extension
  null `ModuleSpec.cached`/absent module `__cached__` presence state,
  directory child order, virtual stat/DirEntry field, or data-null pairing;
  exercise declared Matplotlib font/style/data lookups through exact `os`/
  `os.path`/`pathlib` wrappers and reject bytes paths, `dir_fd`, dot/dot-dot,
  symlink, unsorted listing, physical inode/time metadata, raw libc syscall, or
  wrapper/frozen-hook mutation. Reject directory namespaces,
  loader fallback, bytecode generation, physical scans, and two specs from one
  manifest. Exercise a first post-base manifest import and require only its
  observed-use/module/native closure to be runtime-specific while its unchanged
  prospective bytes stay common-base-bound. Only an artifact absent from both
  selected base profile and used closure is private/hash-neutral; an omitted
  member of a selected whole wheel remains indirectly archive-bound;
- attempt to import/recover each exact denied hygiene surface—`ctypes`,
  `_ctypes`, `numpy.ctypeslib`, `_testcapi`, and every profile-enumerated FFI/
  debug helper—and require ordinary import failure. On profile-pinned CPython
  3.12+, exercise a normal source import with authorization before
  `module_from_spec`, create, attribute freeze, `spec._initializing=true`,
  initial insertion, exec, stock success-tail pop/reinsert, V1 initial-object
  identity check, `spec._initializing=false`, and exactly one logical completion record. Exercise
  source/sourceless/project `create_module`, multi-phase
  extension broker-receipt/prospective-authority-before-create, actual mapping-
  before-constructor/`PyInit_*`, create-before-insert, and freeze-before-
  `Py_mod_exec`, legacy single-
  phase post-create freeze, and absence rather than null for extension
  `__cached__`. Require synthetic shells to omit a fictitious success tail and
  the ordinary `scripts` namespace to execute its real no-op success tail.
  Exercise outer failures before and after initial insertion, including a
  successful nested import during outer create, and require no outer target-slot
  mutation before insertion, only the authorized same-object unwind after it,
  no outer completion record, and no
  publication. Mutate/remove the exact C dict watcher through its guarded API,
  insert/replace/delete/restore a base or fileless module through ordinary
  mapping/import APIs, call `_imp` outside an authorization, substitute the
  tail-reinsert object/name, add an extra pop/reinsert, or enter an unbound/
  early/late/nonnested state and require the ordinary-API fatal path. Exercise
  legitimate manifest, project, synthetic-shell, and `scripts` logical timing,
  pre-exec-before-opcode ordering, and exact transition kind/name/authority
  index/order/count/digest/final-module reconciliation. Mutate and restore any
  protected module/spec presence or value through guarded APIs outside its exact
  transition and require synchronous failure; reject missing/extra/reordered/
  aliased logical completions and stock 3.10/3.11 as diagnostic-ABI mismatches.
  Separately verify that the threat-model text, source/runtime hashes, and review
  closure treat project code, CPython, NumPy, and all reachable native code as
  TCB and never report the watcher as an arbitrary-memory sandbox;
- exercise the exact one-way receipt pipe: wrong fd/direction/capacity/flags,
  second channel, frame over 4,096 bytes, too-long component, partial write,
  `EAGAIN`, two pending frames, wrong kind, stolen/missing/extra/reordered frame,
  raw open outside the sealed wrapper, fabricated project stop, or disagreement
  between framed logs, decoded supervisor arrays, and child arrays must publish
  nothing. Prove nested import opens drain synchronously without blocking;
- exercise the exact registered 8-MiB control buffer and both two-stop
  transfers. For base and final child projections and supervisor transfers,
  mutate schema/key set, canonical length prefix, zero tail, buffer address/
  size/first-registration, control magic/ordinal/state, array/count/domain/hash,
  base/final policy ID, common-base cross-link, or child/supervisor copy. Reject
  short/partial/third/out-of-range `process_vm_writev`, changed mapping, alias,
  oversized payload, capture/commit reorder/duplication/skip, import/read/dlopen/
  signal/finalizer/output mutation between the pair, changed loader traversal,
  resume without ACK, or terminal disagreement. For
  `BaseReadyClosureTransferV1`, independently mutate all broker/stdlib/module/
  dependency/mapping triplets. For `FinalRuntimeClosureTransferV1`, independently
  mutate the complete final-module/mapping/dependency triplets and every primary-
  environment copy. Add a post-base built-in/frozen/null/no-origin module and
  require failure; admit only byte-identical base fileless records, the exact
  two synthetic shells, or sole `scripts` namespace. Prove exactly two and only
  two supervisor memory writes and that neither transfer wrapper/address/hash is
  public;
- for `dependency_discovery.broker_read_records`, exercise all five handoff,
  source, external, distribution, and stdlib variants plus repeated and interleaved
  opens. Mutate, omit, add, reorder, duplicate, or renumber a record; alter its
  tagged role/path/count/hash, handoff/source/external/distribution/stdlib cross-link,
  distribution trigger ordinal, array count/digest, runtime/environment/enclosing
  hash, base-prefix boundary/count/digest/common-base hash, or fixed-Y phase-
  manifest copy and require failure. Delete the private
  broker ledger and original checkout and require offline verification to
  reconstruct the exact retained stream; a source/external-only projection,
  hash-only stream, distribution ordinal without a record, or permitted stdlib
  data read without its tagged record must fail;
- for arithmetic traces, cover explicit empty and nonempty golden arrays and
  the one terminal-NUL/no-LF digest vector. Mutate/add/delete/duplicate/reorder
  a record, operation, input, output, arity/shape, count, or digest; inject an
  unknown key, Boolean/non-string/noncanonical/non-finite hex, private path/env/
  callsite canary, untraced vector call, or exception and require no valid
  owner. Rebuild shallow outer hashes after a mutation and require the
  authoritative environment/owner DAG to fail. Delete the original worktree
  and all private runtime/native evidence and require the offline verifier to
  reconstruct every retained trace/count/digest/environment/enclosing hash.
  For every one of the 14 operation rows, cover the exact outer arity, every
  inner length, output length, positional order, materialized operand type, and
  named call. Reject variadic `hypot`, non-3D `dist`, empty or 4097-element
  `fsum`, a wrong algorithm-local fsum length/order, vector `cbrt`, a non-
  `numpy.float64` cbrt result, keyword/broadcast input, and caller-type-
  dependent power. Bit-test both integral-exponent and nonintegral-exponent
  `float-pow` branches and all fsum boundary/context lengths.
  Add bit-exact unary golden vectors for `math-degrees` and `math-exp`, and
  positive/negative finite-success and finite-to-infinity rejection vectors for
  the two fixed-direction nextafter operations. Reject generic/two-operand
  nextafter, caller-selected direction, serialized infinity, swapped direction,
  non-finite output, or any authoritative CIEDE2000 `degrees`/`exp` call outside
  its trace adapter. For direct-oracle `down64`/`up64`, test zero-call exact-
  containment cases and one-call correction cases, require respectively
  negative/positive operation IDs at the recomputation's actual call-order
  position, and reject a second step, walk, or reversed mapping;
- exercise standard dotted-import parent initialization with HEAD-like eager
  public-API, Matplotlib, font-load, color-load/register, and `_discrete`
  sentinels. In each of the eight authoring-shell profiles, require the preparer
  to hash-read both initializer sources exactly once in root/`_colors` order and
  the computation child to mount/read/compile/execute neither body. Exercise
  reload, spec refinding, direct compile/exec, delete/rebind, remove/reinsert,
  alias, third shell, caught-and-restored mutation, protected metadata changes,
  balanced and unbalanced `_uninitialized_submodules`, permitted direct-child
  bindings, and forbidden attributes; every sticky attempt must invalidate the
  owner. Select shell mode for a `scripts.*` row, ordinary mode for an authoring
  row, or mutate dispatch/handoff/enclosing hashes and require no owner. In
  ordinary fresh processes require
  the predecessor public import behavior unchanged, including exports,
  registrations, fonts, manual colors/palettes, and every shipped 43×256 LUT
  byte/index/metadata surface. For `scripts.*`, explicitly allow real
  initializer execution only through policy/event pairs;
- mutate the reviewed project-execution registry's exact top-level schema,
  eleven-row set/order/uniqueness, invocation/table/entry/operation binding,
  namespace/required/optional/data arrays, row/top count or digest, selected
  module/path/hash projection, `ComputationInputInventoryV1` category/leaf ID,
  or final policy copy. Exercise a missing/extra/twelfth profile, required-entry
  omission, array overlap, unused optional module/data row, and future read
  absent from the predeclared inventory. Exercise strict LIFO nested events, success without top
  pre-exec, unmatched/reentrant/duplicate execution, direct/manual exec,
  forbidden module, initializer under shell mode, source alias, module deletion/
  replacement after success, and child/supervisor event-log disagreement.
  Require `project_imports` to equal the unique success projection and terminal
  module objects. Exercise the sole `scripts` namespace parent and reject every
  second/file-backed/aliased namespace;
- exercise every environment-v3 profile after its real operation, including
  exact empty traces only for `legacy-baseline-extractor-a`,
  `legacy-baseline-extractor-b`, `legacy-baseline-cross-extraction`,
  `policy-preselection`, and `characterization-verification`, and require all
  other six traces nonempty; prove preselection never imports selection and the
  verifier never imports producer code. Require base hashes equal across kinds
  but full hashes equal only for same-kind replay. Reject a missing, duplicate,
  detached, wrong-kind, or inferred owner for any of the eleven profiles;
  require both policy-characterization verifiers to own their numeric replay,
  complete preselection and frozen-promotion owners, exact frozen
  `promotion_provenance`, and the early existing-target no-op before any new
  promotion invocation;
- enumerate the installed NumPy ownership index from exactly the direct regular
  wheel members. Reject every `.data` relocation, generated entry-point script,
  installed-RECORD rewrite, dot/dot-dot or symlink path, and parent-prefix
  authority, but publish only actually imported/read records plus
  their selected-wheel content identity. Reconstruct the canonical projection
  from the exact complete runtime rows; mutate, omit, add, reorder, or shallow-
  rehash an identity, the projection hash, either
  `numpy.distribution_records`, or the runtime NumPy row and require every
  name/version/artifact/used-file cross-link to fail. Different invocation
  NumPy or non-NumPy used sets must retain the common base hash while changing
  runtime/full hashes; mutating any retained `base_numpy` field must change the
  base hash;
- privately seed the lock with an unused package, source/dependency row,
  credential-bearing direct URL, local file path, unselected Windows wheel,
  filename, size, upload time, and cache/receipt locator. Mutating any such row,
  including an unselected artifact hash, must preserve every public byte and
  environment hash. A selected wheel mirror/URL change with byte-identical
  archive must also be neutral. Changing any profile-selected archive byte must
  change base/runtime/full hashes; if that distribution is actually used it
  must additionally change the selected-artifact projection, whereas an unread
  selected candidate remains absent from that invocation projection. Missing archive bytes or selected digest,
  a stale witness, conflicting associations, or a used sdist/direct/editable/
  path/Git/VCS distribution must fail before publication. No raw whole-lock or
  complete-package-entry hash may appear;
- seed unused `direct_url.json`, installer metadata, scripts, and cache paths
  with private canaries and prove neither their bytes nor hashes enter public
  evidence. Delete the live lock, private selection witness, cache, and original
  worktree after capture and require the archived public DAG to remain fully
  recomputable from embedded runtime rows;
- exercise coincident `stdlib`/`platstdlib` roots, a distinct `platstdlib`
  containing `site-packages`, equal `purelib`/`platlib`, and distribution-owned
  files nested beneath either stdlib root. Require exact distribution ownership
  to win before site exclusion or stdlib classification, coalesce equal stdlib
  roots to one `stdlib-root`, reject an unowned site path, reject ambiguous
  distinct stdlib matches, and mutate every retained module/broker ownership
  trigger independently;
- exercise the supervisor launch itself. Reject a dynamic supervisor,
  `PT_INTERP`, `DT_NEEDED`, constructor/TLS/rseq runtime, changed stage-zero
  bytes, group/other-writable file or ancestor, unsealed self-exec, dirty
  environment, extra descriptor, supplementary group, nonzero dumpability, or
  hash mismatch. At stage-zero, final-supervisor, capture, child-bootstrap,
  authoring, and handoff stops, have a governed peer attempt signal, ptrace,
  `process_vm_writev`, `/proc/<pid>/mem`, pidfd access, shared-alias writes, and
  supervisor-output mutation; every route must fail. Independently reject a
  final supervisor with an extra thread, pre-existing seccomp filter or
  USER_NOTIF/ADDFD listener, inherited `MAP_SHARED`/SysV-shm/mutable-file
  private map, userfaultfd, io_uring/AIO, socket/device handle, rseq
  registration, or unexpected FD before `clone3`; prove a peer cannot mutate
  the inherited bootstrap stack/data between clone and exec. Exercise exactly
  two sequential clone/exec/reap lifecycles, distinct credentials/roots, the
  preparer private terminal transfer, the computation base-ready stop, and the
  sole computation fd-3 receipt exception; any overlap, reuse, third child, or
  preparer object surviving into computation fails;
- exercise the private terminal-output protocol for every native producer and
  every `artifact-map`, `named`, and `none` profile with zero, one, and many
  ordinary members. Mutate/miss/add/reorder/alias a profile/member/path/kind/
  hash/byte count, primary kind/schema/completion field/hash, output role, producer ID,
  or manifest self-hash; leave scratch or an extra/empty directory; substitute
  a symlink, hardlink, FIFO, device, socket, or duplicate inode; retain a
  writable output descriptor/mapping; write after the manifest; stop early;
  copy before reap; resume after stop; or omit/change a memfd seal, and require
  no authoritative primary. For ignored output only, fault-cut stale-primary
  unlink and directory sync, every subordinate stage/write/fsync/rename/rehash/parent sync, primary
  stage/fsync/rename/parent sync, and post-write guard/unlink. Prove retry from
  every subordinate-only prefix, exact tracked start-plus-target overlay under
  a fresh writer lock, no read-to-write lock upgrade, no content-addressed
  bundle in ordinary inventory, and no public reference to the private manifest
  or its hash. Assert that tracked recovery never deletes or replaces a tracked
  leaf and that its failed final guard is fatal. A surviving primary must always
  imply the exact durable declared set;
- exercise Linux sealed-memfd launch on real x86-64 and AArch64 with the process
  executable, `PT_INTERP` loader, recursive DSO/extension closure, every
  readable runtime/source/input leaf, startup audit leaf and its recursive
  audit-only dependency closure, one-file bootstrap directory, sealed private
  invocation-request leaf, empty startup cwd, private output tmpfs,
  and exact `/proc/<pid>/maps`/`AT_PHDR`/`AT_BASE` association. Require direct
  `clone3` creation with exactly the four `CLONE_NEWUSER`, `CLONE_NEWIPC`,
  `CLONE_NEWNS`, and `CLONE_NEWNET` flags, no sharing flags, a one-entry
  subordinate UID/GID map, and its
  exclusive lease through reap. Verify the private mount contains no procfs,
  `/dev`, `/dev/shm`, mqueue, hugetlbfs, sysfs, FUSE/device mount, or host-
  writable bind; all input leaves are fully sealed; `/proc/<pid>/cwd` is the
  unique empty startup directory. For preparer exec, `close_range` leaves only
  immutable-EOF fd 0 and write-only sink fds 1/2. For computation exec it leaves
  exactly those plus read-only nonblocking `broker-receipt` at fd 3; every fd
  at or above 4 is closed. No other control/receipt, directory, namespace,
  pidfd, socket, shm, memfd, userfaultfd, io_uring, device, PTY, or mutable-file
  descriptor reaches either exec. Start with hostile inherited cwd and
  directory descriptors and require recursive-private propagation, successful
  `pivot_root`, cwd/root equality, complete old-root detach, exact mountinfo,
  and failed old-root traversal before credential drop and exec;
- exercise the x86-64 and AArch64 seccomp/ptrace syscall-entry and syscall-exit
  state machine, single-thread guard, compiled filter identity/default-kill,
  and exactly the four `PTRACE_O_TRACESECCOMP`, `PTRACE_O_TRACESYSGOOD`,
  `PTRACE_O_TRACEEXEC`, and `PTRACE_O_EXITKILL` options. Require the seccomp
  stop, sole permitted intervening exec event, `SIGTRAP|0x80` exit stop, and
  `PTRACE_SYSCALL_INFO_EXIT` pending-state match. Removing
  `PTRACE_O_TRACESYSGOOD`, accepting plain `SIGTRAP`/`NONE`, admitting an
  unknown/compat ABI or syscall, tracer death, signal delivery/restart, filter
  replacement, event loss, or any state permutation must fail. Separately
  on x86-64 require real-host `vsyscall=none`, no `[vsyscall]` range, and
  faulting legacy fixed-address probes; the default x-only/emulated mode must
  fail preflight. On both architectures require the exact rseq-disabling glibc
  tunable, fixed-`ENOSYS` raw `rseq` behavior, zero
  `PTRACE_GET_RSEQ_CONFIGURATION`/`__rseq_size` at every guard, and no kernel
  writes under forced context switches and CPU migration. Then
  require the one exact harness-range self-`tgkill(SIGSTOP)` syscall exit and
  matching final signal-delivery stop after all output handles close; any other
  sender, target, signal, instruction range, ordering, or post-stop user-space
  resume fails, and publication occurs only after supervisor kill/reap and
  sealed-copy hash verification;
- prove the loader-order claim with native fixtures whose IFUNC,
  `DT_PREINIT_ARRAY`, `DT_INIT`, and `DT_INIT_ARRAY` hooks each run before
  `la_preinit`. Every hook must already be under the same seal, namespace,
  descriptor, seccomp, ptrace, credential, and writer boundary. Require the
  audit leaf's exact-range `PR_SET_DUMPABLE=0`/`PR_GET_DUMPABLE==0` sequence
  after those hooks but before executable `main` and Python interpreter entry;
  an earlier-order claim, a call from another image/state, or release before
  the checked syscall exit fails. Link the freestanding audit leaf to one
  unique freestanding private `DT_NEEDED` helper and require the stopped
  supervisor to observe exactly base then audit `r_debug_extended` nodes with
  version 2 and `RT_CONSISTENT`, enumerate the leaf and helper from the audit
  `link_map` chain, and assign exactly `startup-audit` and
  `audit-transitive/00000000`. The base `dl_iterate_phdr` stream must omit those
  audit-only images yet equal the normalized base chain. Require a conventional
  libc-linked auditor that remaps the base libc identity at another address to
  fail preflight. Mutate `DT_DEBUG`, add an `_r_debug` copy relocation, add
  `DT_AUDIT`/`DT_DEPAUDIT` to any captured ELF, mutate either
  `r_version`/`r_state`, `r_ldbase`, `r_brk`, node address, `r_next`, `r_map`,
  `l_next`/`l_prev`, load bias, dynamic address, startup-audit membership,
  namespace order/count, retain an empty namespace node, alter the header/link
  topology between the before/after reads, or add an orphan mapping/callback; every case must
  fail. The audit chain must be identical at `la_preinit`, base-ready capture,
  base-ready commit, operation-closure capture, operation-closure commit, and
  pre-exit;
- through both libc and raw syscalls, test anonymous private RW-to-RX, direct
  executable map/unmap of an otherwise unused sealed leaf, every
  `mprotect`/`pkey_mprotect`/`mremap`/`remap_file_pages`/`munmap` route, raw and
  libc `brk` query/grow/shrink/overlap attempts, and re-exec. Valid heap changes
  must be entry/exit ledgered and reconciled; an untraced, executable,
  cross-range, or surprising `brk` result fails. The anonymous execute
  transition is synchronously denied; a direct
  sealed executable map enters the private ledger but fails loader correlation
  even if immediately unmapped. Reject a missing seal,
  `F_SEAL_FUTURE_WRITE` substitution, writable alias, ever-W/ever-X transition,
  read-only-bind-only or fs-verity-only claim, mapping outside a declared
  `PT_LOAD`, duplicate base, unload, and post-barrier add. Deleting or replacing
  an original pathname after capture is neutral; unreadable pre-seal bytes or a
  read/mapping not backed by its retained leaf fails;
- exercise the complete mutable-alias matrix while a peer repeatedly changes
  sentinel bytes: mode-0666 System V shm plus every `shmat` flag; POSIX
  `shm_open`; `MAP_ANONYMOUS|MAP_SHARED`; read-only and writable
  `MAP_SHARED`; `MAP_SHARED_VALIDATE`; and `MAP_PRIVATE` over a mutable regular
  file. Include concurrent external `pwrite` against source, input, output, and
  result-file candidates. Every shared/mutable route must be unavailable or
  synchronously denied, while anonymous-private and retained-fully-sealed-file
  private mappings remain admitted. Neither unchanged final bytes nor a zero
  observed-event count may turn a reachable route into PASS;
- exercise inherited regular/directory/shm descriptors, pipe/socketpair/TCP/
  UDP/AF_UNIX endpoints, `SCM_RIGHTS`, pidfds, PTYs, and device/driver handles,
  then attempt socket creation, descriptor passing,
  `process_vm_readv`/`process_vm_writev`, `/proc/<pid>/mem`, ptrace,
  `pidfd_getfd`, userfaultfd through both syscall and `/dev/userfaultfd`,
  io_uring, legacy AIO, `splice`/`vmsplice`/`tee`, perf/BPF, and device mmap/
  DMA. Each inherited handle must be absent and each acquisition route denied;
  operation and terminal guards require no pending async writer context or
  completion;
- during blocked bootstrap, the post-exec dumpability-reset interval, every
  constructor, after the `la_preinit` barrier, authoring, and handoff, have an
  untrusted original-credential process attempt process, proc-mem, ptrace,
  shared-backing, socket, signal, and asynchronous writes to executable pages
  and writable NumPy/result buffers. All must fail while the supervisor retains
  access. Reject creation outside the four namespaces followed by `unshare`, a
  reused/colliding or ordinarily delegated subordinate ID, concurrent
  `newuidmap`/`newgidmap` or container mapping, caller-UID mapping, leaked
  namespace descriptor, missing setgroups denial, nonempty capability set,
  failed dumpability set/get, later `PR_SET_DUMPABLE`/`PR_SET_PTRACER`, any
  credential/capability/namespace mutation, or early lease release;
- on Darwin x86-64 and arm64, and on every other non-Linux platform, require
  native preflight failure before a Python child is created. Assert that no
  environment record, candidate owner, public provenance, partial output, or
  unsupported-placeholder `native_execution` record exists. Merely supplying
  Endpoint Security, Hardened Runtime, App Sandbox, task-right authorization,
  an APFS snapshot, or a custom/deprecated Seatbelt profile must not enable V1;
- before any future positive Darwin lane is specified, require a separately
  reviewed boundary and real-machine rejection tests for mutable-file shared
  maps, anonymous shared maps plus fork, POSIX and System V shm, Mach memory
  entries, XPC shared memory, IOSurface, inherited descriptors/Mach rights,
  AF_UNIX/`SCM_RIGHTS` and IP sockets, IOKit/device/DMA maps, POSIX AIO and
  dispatch/device completions, signals, descendants, task rights, remote
  threads, and every executable-map route. This matrix is a future admission
  prerequisite, not evidence that Darwin V1 exists;
- mutate every native mapping field, header/program-header hash, segment
  ordinal/range/protection, record count/order/hash, identity link, supervisor
  capability, and every complete base-ready mapping/dependency/module/stdlib
  closure. Require an unused artifact absent from both selected profile and used
  closure to change no public byte. Require a changed manifest member (including
  a member of a selected whole wheel), executable, loader, or arithmetic core
  leaf to change base/runtime/full hashes. With manifest bytes fixed, changing
  only whether/when a post-base member is actually used must change the final
  module/used-trigger closure and runtime/full hashes but not the base hash;
- on real Linux x86-64 and AArch64, capture the `AT_SYSINFO_EHDR` vDSO and
  prove equal bytes at different synthetic bases have equal identities.
  Mutate its ELF header, PHDR order, `PT_LOAD` bytes/tail, architecture,
  candidate count, or pre-exit bytes and require failure or a changed digest.
  Reject `R_X86_64_RELATIVE`, `R_AARCH64_RELATIVE`, `DT_RELR`, a named ordinary
  DSO pretending to be vDSO, a missing vDSO, and every attempt to give it one
  of the six core roles;
- cover multi-role image reuse, every closed scalar/nullability boundary, each
  gradual-underflow probe failure, and two import aliases resolving to one
  stdlib file. Prove public native records contain no loader/install/path,
  inode/address/mount, or GNU-build-ID value/hash and fail when an image lacks
  its one sealed-file or unique-vDSO encoding. Link two
  byte-different ordinary Linux DSOs with the same caller-selected GNU build
  ID: require distinct `file-sha256` identities after sealing and reject build
  ID as a fallback even after rebuilding every outer hash;
- run an otherwise identical fixture under different hostname, home, repository,
  venv, temp, Python/Git/sysconfig/loader/capsule paths, mount/namespace IDs,
  inode values, subordinate UID/GID and user-namespace IDs, VM load bases, and
  private provider IDs. Require
  identical scientific/public provenance, snapshot/archive, and frozen bytes;
  scan the complete proposed tracked tree, filenames, decoded hex/base64,
  PNG/PDF/HTML metadata, and newly reachable Git objects for every raw canary
  and its SHA-256. Include raw-lock URLs/paths, installer receipts, artifact
  filenames, and cache locators in that canary set. Any occurrence must publish
  nothing;
- regenerate and strictly parse every nested characterization record, mutate
  grid/root stream hashes, trace-fixture fields, mismatch indices, row or
  aggregate hashes, and require exact count/max/digest recomputation;
- install the tracked scientific payload create-only, take a new source
  snapshot, require the generation phase's source subset and broker log to omit
  the expected asset, seal its output, compare only in a separate verifier
  process, require payload byte identity, and prove that changed invocation
  provenance does not alter or invalidate those scientific bytes;
- v6 SSOT rebuild and byte comparison;
- comparison report and complete side-by-side asset inventory;
- docs build with warnings as errors;
- static typing, Ruff, format, asset determinism, explorer/theory builders, and
  visual regression;
- all final commands on one recorded source snapshot with matching live guards
  and independently verified role-complete invocation-input bundles.

## 12. Adversarial review protocol

Every semantic change batch follows this exact protocol:

1. implementation and local verification;
2. reconstruct the exact HEAD plus declared-source clean review capsule from
   section 10, reject the live dirty worktree as a review root, prove the full
   `H/I/W/R` path union, and freeze that capsule;
3. a fresh, independent Reviewer A examines the frozen capsule adversarially;
4. any finding resets the review count to zero; fix and restart with a new A;
5. only after A passes, a new independent Reviewer B examines the exact same
   unchanged source snapshot and subject bytes captured through its successor
   input bundle; and
6. any B finding also resets the count to zero.

Reviewer B may not run concurrently with Reviewer A. Start/end worktree
fingerprints and the post-write guard use section 10's seven-value formula and
must match the one clean-capsule source snapshot shared by both reviews. A and B have
distinct role-complete subject-input and immutable pre-run control bundles, and
B's subject bundle contains A's report, complete historical execution-input,
control, and evidence bundles, plus the completion token. Every sealed public
review log has exactly one final terminal result, and the outer
report derives its verdict/findings and terminal pointer only from it. Section
3.6's fresh-instance `ReviewExecution`, A-completion token,
B-predecessor link, and
maintainer independence attestation are mandatory. They audit and enforce the
declared harness procedure but do not purport to cryptographically prove a
reviewer's real-world identity. The spec/ADR batch, implementation batches,
evidence batch, and final integration snapshot each require their own A-then-B
sequence.

## 13. Non-goals

- No changes to shipped hex, LUTs, indices, names, order, registration, typing,
  MCP discovery, semantic colors, or vendor values.
- No migration of the existing catalog to direct OKLCH.
- No automatic replacement of frozen discrete indices.
- No CIEDE2000 or CVD construction objective.
- No claim of observer-wide accessibility or physical display luminance.
- No public arbitrary-family registration API in this change.
- No new runtime dependency for polynomial solving or discrete selection.
- No aesthetic retuning of existing families.

## 14. Delivery batches

1. **Spec/ADR:** accept this contract and ADR 0002; independent A then B.
2. **Baseline preinstall:** from the exact normative predecessor, independently
   produce two non-aliased sealed candidates and evidence records, then use the
   separately captured cross-extraction invocation to copy one byte-identical
   final candidate and publish its manifest; review all six outputs, A then B.
3. **Baseline promotion:** in a separate batch, byte-transfer the reviewed
   candidate and complete review/snapshot/approval closure into the create-only
   tracked archive and compatibility/acceptance pair; fresh A then B. After B,
   run the closed non-semantic finalizer to archive that promotion-review
   closure, capture the post-promotion approval, and publish the authority
   marker last. Only a later exact HEAD containing every marker-reachable leaf
   makes that complete set authority. The next batch reruns the
   unchanged predecessor validation/gate suite from accepted bytes; it does not
   trust a sibling quality golden or create separately pinned observations.
4. **Compatibility migration:** from a new HEAD containing that accepted
   baseline, implement and freeze the isolated OKLab/OKLCH shipped-replay lane,
   v6 SSOT, discrete indices, exact comparison, side-by-side report, and
   architecture gates; A then B.
5. **Boundary isolation:** from a new HEAD containing the accepted migration,
   implement the projective generic boundary and typed authoring policies with
   TDD; A then B.
6. **Offline authoring:** implement deterministic LUT generation, strict
   proposal/promotion/frozen schemas, discrete selection, and fail-closed
   admission with TDD; A then B.
7. **Evidence and documentation activation:** add authoring diagnostics,
   self-binding report provenance, reconcile stale execution records, and only
   then activate present-tense user documentation; A then B.
8. **Final freeze:** run every required verifier on one captured execution
   snapshot and perform a final fresh A then B before any integration decision.

No commit, rebase, merge, push, or remote integration is authorized by this
spec. The user receives a walkthrough before any such action.

## 15. Acceptance criteria

This migration is complete only when all of the following are proven:

1. the compatibility candidate has been independently extracted from exact
   predecessor commit `6be8cb56b8752e03515101caa7ae2f6c52cc13dc`, promoted with
   its complete tracked preinstall archive and acceptance in a separate reviewed
   batch, bound afterward to that promotion's complete A/B closure and
   post-promotion approval by the tracked authority marker, integrated with
   every marker-reachable leaf into the exact HEAD used by compatibility
   migration, and all 18 shipped
   surfaces remain exactly equal to that accepted baseline;
2. no shipped call graph can reach the generic boundary or selector;
3. the generic fixed-Y boundary satisfies its global constrained objective
   within its returned lower/upper certificate and outward absolute gap;
4. direct OKLCH and fixed-Y coordinate policies cannot be confused by a boolean
   or shared ambiguous field name;
5. a new unpinned family can produce a deterministic OKLab/OKLCH proposal,
   undergo independent admission, and become a frozen manifest;
6. a missing frozen manifest entry always fails and never triggers optimization;
7. the comparison space distinguishes shipped compatibility from non-shipped
   authoring diagnostics and binds results to one source snapshot;
8. shipped diagnostics derived from exact output bytes pass the unchanged
   predecessor validation definitions and thresholds, new authoring families
   pass their separately accepted validation policy, and no validation model
   enters construction;
9. every semantic batch has an unchanged-snapshot Reviewer A pass followed by a
   fresh Reviewer B pass;
10. the final whole-system evidence is produced from one recorded source
    snapshot whose live guards all match, plus verified stage-specific
    invocation-input bundles;
11. fixed-Y is admitted only by its explicit nominal D65-sRGB modeled-Y-fiber
    topology contract, with no perceived-brightness, physical-luminance, or
    accessibility claim;
12. admission uses authoritative candidate-excluding reference assets and the
    immutable validation-oracle truth only through its complete tracked
    preinstall bootstrap acceptance;
13. both fixed-Y review stages have tracked create-only acceptances resolving
    complete canonical archives and binding identical raw/semantic payload
    hashes to the tracked scientific asset;
14. direct-oracle equivalence compares algebraic source identity and exact root
    proofs while allowing independent valid production/oracle brackets; and
15. durable snapshot archives admit non-HEAD index/worktree state only when it
    equals the exact reviewed source mode/hash, contain a canonical zero-stat
    extension-free index and synthetic Git config, and never contain raw local
    config/index/shared-index or unrelated dirty/untracked bytes. Every review
    runs from an isolated clean capsule reconstructed from exact HEAD plus only
    the declared source states; unchanged declared sources remain valid while
    the actual deviation set equals exactly the declared states unequal to
    HEAD. The current two-document batch proves `D=A` with exactly two
    `(ABSENT,ABSENT,R,R)` paths and rejects the live dirty worktree as a review
    root;
16. direct/fixed-Y witnesses bind the canonical achieved-Y association,
    authoring signed-zero classes fail closed before rational/branch use, and
    merged candidates retain their complete ordered role union;
17. scientific payload identity, including validation-oracle evidence and
    validation-input hashes, is independent of approval/invocation history,
    while the admission-entry/preselection acceptance chain remains mandatory
    and a separate public reproducibility root binds that path-neutral
    governance;
18. hostname, absolute roots, raw argv/cwd/env, loader/capsule paths,
    descriptors, inode/mount/namespace/address/load-base facts, PIDs, provider
    identifiers, subordinate UID/GID/user-namespace facts, transcripts/tool
    output, arbitrary approval text, and every
    derivative hash/encoding are absent from all tracked files, archives,
    metadata, filenames, and reachable Git objects;
19. every environment binds exactly the canonical selected-wheel projection of
    its complete used-distribution closure, while raw whole-lock/package-entry
    hashes, URLs/paths/filenames, receipts/cache locators, unselected artifacts,
    unsupported direct/editable/source installs, and derivatives of those
    private values remain unpublishable;
20. endpoint, projective, Cartesian, and direct-oracle constant references all
    resolve to one archived closed scalar-kernel preimage with exactly 49
    binary64 leaves, its exact canonical byte length, and golden digest, and
    each independent implementation reconstructs that record from private
    literals before computation;
21. V1 environment publication is available only on Linux x86-64 and AArch64;
    Darwin and every other platform fail native preflight before Python and
    emit no environment, candidate, provenance, partial output, or placeholder
    native record. The supervisor itself is the byte-identical, fully static,
    self-sealed, nondumpable ELF64-little artifact named in provenance and has
    no governed external writer. Immediately before `clone3`, it has one
    thread, no prior seccomp/filter listener, shared or mutable-file mapping,
    rseq registration, asynchronous/device/IPC state, unexpected descriptor,
    or executable pseudo range other than the admitted vDSO. Every child-
    readable runtime/source/input leaf and every
    filesystem-backed native mapping, including the process executable and
    loader, comes from a prelaunch fully sealed memfd. Each invocation contains
    exactly two sequential children: a no-site Python control preparer is
    terminally stopped, copied, killed, and reaped before a fresh no-site Python
    computation child is created. Each is created directly inside distinct
    private user/IPC/mount/network namespaces with a unique subordinate
    credential, verified recursive-private `pivot_root` with the old root/cwd
    detached, closed descriptor and mount surfaces, and an exact default-kill
    seccomp/ptrace state machine. Each environment is constructed
    from empty with a fixed integer hash seed, exact behavior record, rseq-
    disabling glibc tunable, and one sealed `LD_AUDIT` `startup-audit` role; no inherited or
    unbound variable exists, and every captured ELF is free of `DT_AUDIT` and
    `DT_DEPAUDIT`. Both CPython lifetimes start with their exact no-site argv,
    one-file bootstrap directory, empty sealed cwd, closed pre-broker input/
    module/path records, optional bound zero-member stdlib archive, and no
    ambient site/path hook; each broker precedes every non-cached import. Before
    them the same supervisor uses its executable-bound memory-safe bounded wheel
    parser to provision a fresh root from exactly the request-selected reviewed
    base profile, retaining the private witness and public whole-wheel
    projection without an external installer, `.data`, generated script,
    RECORD rewrite, packaged bytecode, or symlink. The
    preparer alone consumes the exact first-eight request/platform/two-policy/
    computation-inventory/provisioning-witness sequence and later lock/wheel/metadata/
    stdlib and shell-control leaves, builds the private index with captured
    `importlib.metadata` semantics, emits the exact public handoffs/runtime-
    import/project-execution policies, and transfers its private manifest. No
    raw control byte, heap, descriptor, mapping, or namespace survives its reap.
    The computation receives only the two public handoff leaves, exact public
    synthesized runtime trees, sealed source/external leaves, and the sole
    one-way receipt-pipe exception. Broker-read ordinal zero precedes every base
    import; at the exact base-ready capture and commit stops, the supervisor
    transfers and freezes the complete
    base stdlib/module/dependency/mapping closure before invocation handoff and
    source-root append. Post-base imports are possible only through exact manifest
    module bindings/specs. At the exact operation-closure capture and commit
    stops, the supervisor transfers the complete final module/mapping/dependency
    closure; the CPython-3.12+
    evidence profile's dict-watcher/import-core instrumentation enforces the
    exact stock create/insert/exec/success-tail logical transaction and makes
    unauthorized ordinary import/mapping transitions fatal. It does not claim
    an arbitrary same-process memory sandbox: the exact reviewed project source,
    CPython, NumPy, and complete reachable native/runtime closure are hashed and
    reviewed TCB. Each shell-mode authoring target uses two nonexecuting synthetic
    parents whose real initializers were hash-read only by the preparer and are
    permanently denied in computation; exact project policy and well-nested
    supervisor-retained execution events account for every project body reached
    through the conforming reviewed-TCB import path.
    Ordinary public imports retain predecessor behavior. From each child creation through
    verified handoff, no non-TCB writer route exists through shared mappings or
    shm, mutable files, IPC/network descriptor transfer, process/task handles,
    userfaultfd, asynchronous I/O, or devices. The supervisor-only write end of
    the computation receipt pipe is the exact evidence-channel exception and
    carries no private authority. `MAP_SHARED*`, every `shmat`,
    mutable-file mappings, anonymous/W-to-X code, and uncorrelated executable
    maps are synchronously denied or make the run terminal. `brk` is traced and
    limited to the private non-executable heap; rseq registration is absent at
    every guard; and x86-64 requires `vsyscall=none` with no fixed executable
    region. glibc constructors
    run under that complete boundary; the verified `la_preinit` dumpability
    barrier is accurately post-constructor and pre-`main`/Python-entry. Final
    snapshots or absence of observed writes are never authority. Because
    glibc's `dl_iterate_phdr` reports only its caller's namespace, completeness
    comes from the stopped supervisor's version-2 `r_debug_extended` traversal:
    exactly one base and one audit namespace, every `link_map` correlated with
    the sealed VM ledger, and zero orphan nodes, callbacks, or mappings. The
    audit leaf is `startup-audit`; its unique audit-only dependency closure is
    ordinally `audit-transitive`; base callbacks are only a base-chain cross-
    check, and both namespaces remain reconciled through pre-exit. The base hash
    binds both startup/control-base/preparer closures, provisioning artifacts,
    the process split, receipt, synthesized runtime tree, seal/VM/writer/credential/supervisor/
    launch-environment and complete terminal-output-set policies,
    `base_numpy` without invocation used-file fields, the complete base-ready
    stdlib/module/dependency/mapping arrays, and the inline NumPy/base broker-
    read prefix/count/digest, while the runtime hash binds the complete NumPy/
    distribution used-file, complete final-module, and native-mapping projections plus the inline
    globally ordinalled handoff/source/external/distribution/stdlib broker-read
    preimage, count, digest, and ownership cross-links. The uniquely
    `AT_SYSINFO_EHDR`-identified whole-memory vDSO is
    the only fileless transitive image. A pathname rehash, read-only bind,
    fs-verity result, or GNU build ID alone is never authority. Every math-
    origin variant has exactly one closed stdlib four-field projection or
    private address-bound sealed-file identity and the literal Python/NumPy
    core-role references, with no redundant or undefined module SHA field. Every
    arithmetic trace retains its complete inline call-order preimage and the
    exact 14-row arity/shape/call grammar, including
    finite `math-degrees`/`math-exp` and fixed-direction finite nextafter
    operations with no serialized infinity, and every
    native producer transfers the exact closed primary-plus-subordinate set
    through the private acyclic manifest, fully seals all members after
    kill/reap, and durably publishes subordinates before the primary commit
    marker; and
22. every direct-oracle result carries the unique complete merged-boundary
    source unions and exact `2*m-1` alternating topology; every point component
    has a null anchor and exact algebraic point-sign proof, while every open
    component has exactly one strict rational interior anchor and is classified
    only from that anchor;
23. every shipped-baseline consumer proves, from the closed Git capsule, the
    unique literal first-parent chain from current `H` to immutable authority
    `A`, exact authority/current mode-OID-byte equality for the complete
    acceptance-or-authority-marker-reachable path set, including the full
    promotion A/B archive and approval, and absence of index/worktree overlays;
    copied bytes in an unrelated history or authority reachable only through a
    later merge parent fail;
24. every durable create-only/guarded-index-replacement lifecycle passes the
    shared staged atomic no-replace/replace, bottom-up directory
    synchronization, phase-barrier, and power-loss recovery matrix; no
    surviving marker or new index can lack a durable prerequisite, and
    unsupported filesystem semantics fail closed without claiming lock-free
    CAS against non-cooperating writers;
25. every interior projective/direct oracle independently links the certified
    coordinate and neutral-reference `L`, and recomputes direction-scaled
    `a,b`, raw/encoded/neutral RGB, modeled Y, and applicable residual with the
    complete scalar kernel; all bits, association IDs, and same-base-runtime
    scope must agree before PASS;
26. V1 defines no WCAG authoring/admission policy or result: no WCAG
    coefficient, threshold, role-layer helper, ratio, policy-shaped extension,
    or standalone “accessible color” classification can influence coordinate,
    gamut, selector, validation input, admission, or the machine-check
    conjunction, while the predecessor public helpers remain exact-surface
    compatibility obligations; and
27. the 58-row tone migration plan is one-to-one and hash-bound, all real rows
    use the upper branch, the lower branch is tested synthetically, and the
    blue/red derived endpoint is reproduced from its exact accepted colors,
    predecessor metric path, association, and source order.
