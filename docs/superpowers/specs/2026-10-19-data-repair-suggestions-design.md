# Reviewable plot-data repair suggestions

Status: **Implemented — local acceptance and whole-branch review passed; fix-wave re-review and remote CI pending** (2026-10-19).
User approval: **“이 설계로 구현 진행 (권장)”**, 2026-10-19, approves this exact design.
User direction: propose concrete repairs for length/type errors, preserve the original, and expose before/after for review.

## Outcome and boundary

An agent calling the existing `validate_plot_data` can request a machine-readable report
that names bad locations, offers narrowly defined numeric representation candidates,
and explains the manual choices that remain. A caller can inspect the original and a
separate candidate before choosing what data to use. The tool never applies a change.
Success means an actionable, honest report; it does not mean manufacturing valid data.

This is validation of a declared template-data contract, not a general matplotlib
validity oracle. Templates are standalone Python examples, not JSON renderer adapters.
No plots, files, artifacts, approval tokens, execution endpoints, network calls, stored
payloads, pandas/CSV inputs, extra dependencies, or CI workflows are introduced.
The existing artifact feature and every shipped color/baseline remain outside this work.

## Existing authority and preserved context

No Handbook exists; do not initialize one. Current authority is the following source/test map.

### 현재 권위와 상태

- role: purpose; path: `AGENTS.md`, `README.md`; native matplotlib design system; MCP validation is advisory; templates are examples.
- role: runtime-data-validation; path: `src/dartwork_mpl/mcp/tools.py` (`validate_plot_data`, `_validate_*`); two required strings, JSON parsing, 18-validator dispatch; many legacy checks are permissive.
- role: wire-contract; path: `src/dartwork_mpl/mcp/server.py`, `tests/test_mcp_tool_hardening.py`, `tests/test_mcp_validators_complete.py`, `.superpowers/data-repair-2026-10-19/contract-audit/actual-tools.json`; actual discovery is 18 tools / 10 resources / 9 templates / 2 prompts; installed FastMCP 3.4.2 wraps string output as `{result:string}`.

### 지켜야 할 현재 불변식

- role: frozen-color; path: `tests/test_shipped_colors_hash.py`, `tests/test_color_v6_comparison.py`, `src/dartwork_mpl/_colors/_catalog.py`; shipped values, digests, historical baseline, exact legacy discovery projection and full runtime identities/order stay fixed.
- role: accepted-decision; path: `docs/adr/0001-oklab-centered-color-construction.md`, `docs/adr/0003-allow-scoped-mcp-artifact-discovery.md`; ADR 0003 permits exactly its two tools/five artifact templates; another identity requires separate approval. Optional arguments on an existing identity do not alter this frozen surface.
- role: docs-policy; path: `AGENTS.md`; design <=200 lines; executable completion criteria; use a mechanical decider before adversarial review.

### 설계 이유와 제약

- role: compatibility-evidence; path: `.superpowers/data-repair-2026-10-19/contract-audit/report.md`; optional `report: bool` with `-> str` preserves old framing/output schema; native structured union broadens published output schema.
- role: dependency-and-CI; path: `pyproject.toml`, `.github/workflows/ci.yml`; Python >=3.10, FastMCP >=2.13.3,<4; installed evidence is 3.4.2. User requested light tests/CI; add no dependency or redundant pipeline.

### 충돌·미확인

- role: missing-handbook; path: none; no initialization authorized; source/tests and accepted scoped ADRs govern.
- role: contract-gaps; path: `.superpowers/data-repair-2026-10-19/case-audit/recommendation.txt`, `current-behavior.json`, `proposed-cases.json`, `src/dartwork_mpl/mcp/tools.py`; metadata/validators differ; a legacy checkmark cannot establish new validity. Line/category/time ambiguity, grouped aliases and contour meshes are deferred.

## Public surface and compatibility

Recommend `validate_plot_data(plot_type: str, data_json: str, report: bool = False) -> str`.
Omitted calls retain exact existing parser, dispatch, strings, precedence and MCP framing (62 audited requests).
Prechange explicit `report=False` was an unexpected keyword; the additive argument intentionally replaces that refusal.
New false calls with both required fields match old omitted responses exactly (60 audited requests).
For two missing-required false calls, the same framework error category/location/full envelope matches
after removing only its echoed `report:False` input flag. Existing frameworks own argument validation; no override.
True returns one versioned JSON report encoded in that string; clients decode `result` once.
This preserves the output schema, at the cost of a second JSON decode for report consumers.
A native typed-object union is rejected for this milestone because it broadens that schema.
The input schema gains only optional `report`; no registration identity/category/order changes.
Plot names retain existing `.lower()` normalization, without trimming or guessed aliases.

## Initial report coverage

Required vectors/rows are nonempty JSON arrays. Numbers exclude booleans/null and must
map to finite binary64 without overflow or nonzero underflow to zero. Reports preserve
original number tokens; converting for range checks must not rewrite unchanged numbers.

| Plot type | Declared fields and relationships |
| --- | --- |
| `scatter` | numeric `x`, numeric `y`; equal lengths; preserve observation order |
| `bar`, `bar_horizontal` | string `categories`, numeric `values`; equal lengths; numeric-looking labels remain strings |
| `histogram` | numeric `values`; optional `bins`: positive JSON integer token (`10`, not `10.0`, `1e1` or `"10"`), or >=2 finite numeric edges in nondecreasing order; duplicate edges are permitted |
| `heatmap` | numeric `matrix`: nonempty rows, equal nonzero row lengths; no rectangularization |

Only these five named types are supported. All other 13 recognized types return
`unsupported`, distinct from an unknown name; defaults still offer all 18 legacy validators.
Unknown top-level fields are preserved and listed as `unvalidated_paths`; none is inspected
for numeric conversion or consumed downstream. Supported optional `bins` is checked only when present.
The report labels all validity as scoped to the fields above, never whole-renderer validity.

## Proposal and manual-action policy

The sole candidate operation is string-to-number at a declared numeric element path,
including histogram edge elements (never the scalar bin count). A whole string must match
`-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?` with no trimming, units, separators or locale guessing.
Require finite conversion, no nonzero underflow, equal mathematical decimal value after
shortest JSON serialization, and integer-valued results within `±(2**53-1)`.
Decimal comparison uses the original lexeme, not an already rounded float. Standard
binary64 representation is still approximate; the rationale states this and the type change.
Reject conversion of negative-zero strings to avoid losing sign. Unsafe strings require manual input.
Every candidate remains review-required: numeric strings can otherwise mean categories;
never describe this transformation as lossless or approved.

Missing fields, wrong containers, empty vectors, bool/null, invalid label types, unsafe
numbers, length mismatch, ragged rows and decreasing bins receive locations, observed
shape/type/counts and a concrete action. For example, paired length 2 versus 1 asks the
caller to restore intended aligned observations from the source; it never chooses which
observation to add/remove. Ragged rows name each participating row and its length.
No truncation, sorting, padding, dropping, averaging, transposing, imputation, bool coercion,
label inference, merging representations or implicit application is allowed.

## Report contract v1

All output is strict JSON. Omit inapplicable fields; absence is never a fake null payload.
Use explicit typed internal outcomes for admitted, syntax-rejected, encoding-rejected and limit-rejected inputs;
encode these at the boundary, rather than treating arbitrary exceptions as public outcomes.

| Field | Meaning / presence |
| --- | --- |
| `version`, `plot_type`, `recognized`, `supported` | always: `1`, normalized name, catalog membership, repair coverage |
| `status` | `rejected` for parser/encoding/limit refusal; `unsupported` for no coverage; `valid` for no scoped issues/changes; `needs_input` for issues without changes; `proposal` whenever changes exist |
| `scope` | always: supported field names, `unvalidated_paths`, and `validity: "declared_fields_only"`; empty paths if input cannot be inspected |
| `original` | admitted input: `{raw_json, data}`; valid-UTF8 syntax rejection within limits: `{raw_json}`; encoding/limit refusal: omitted |
| `issues` | original-input diagnostics: stable `code`, RFC 6901 `path`, `message`, concrete `action`; optional `related_paths`, `observed` (types/counts or numeric token) |
| `changes` | ordered records `{path, before, after, reason, requires_review:true}`; JSON type is evident in before/after; never an executable patch |
| `candidate` | present only with changes: `{data, valid, remaining_issues}`; detached copy; `valid` is scoped revalidation, not approval |
| `requires_review`, `effects` | always: whether changes exist; constant `"none"` |

Stable issue codes: `invalid_json`, `duplicate_key`, `nonfinite_token`, `limit_exceeded`,
`unsupported_plot_type`, `missing_field`, `expected_object`, `expected_array`, `empty_array`,
`expected_string`, `expected_number`, `numeric_range`, `numeric_string`, `unsafe_conversion`,
`length_mismatch`, `ragged_matrix`, `invalid_bins`. `numeric_string` is an issue resolved
by its candidate change. Remaining issues are newly checked against the candidate with
these same strict rules, never inferred from legacy validator text. A partial candidate
can have `valid:false`; `proposal` does not promise a successful repair.

Order issues/changes by the table's declared field order, then array index, with parent
shape issues before children; list unknown field pointers lexically. Escape `~`/`/` in
pointers. Pair/ragged issues use the first participant as `path`, others as `related_paths`.
No timestamps, random IDs or environment-dependent explanations occur in the report.

## Parsing, limits and responsibility

The opt-in boundary parses once, rejecting duplicate members, trailing content, malformed
JSON and nonstandard NaN/Infinity tokens rather than choosing a replacement. Keep exact
input text; use decimal/token-aware parsing and strict serialization so `original.data`
and unchanged candidate numbers retain their mathematical values even for `1e309`.
Such an out-of-range value receives a numeric token diagnostic, never JSON Infinity.
For syntax rejection use root pointer `""` plus a character offset where available.

Agent-chosen admission limits: 65,536 UTF-8 bytes, nesting depth 16, 10,000 value/key tokens,
100 issue records total across `issues` plus `candidate.remaining_issues`, 100 changes,
and 1,048,576 serialized report bytes. Enforce byte/depth/
token budgets before semantic decoding, then record/output limits during traversal/encoding.
A lexical resource scan is not a second semantic parse. Invalid-UTF8 Python strings cannot
meet byte admission: use a typed encoding refusal (`rejected` / `invalid_json`) without
`original`; strict JSON escaping could recombine literal paired surrogates and misstate raw
preservation. Valid UTF-8 syntax errors within limits retain exact raw text.
When any limit is exceeded, return a small `rejected`/`limit_exceeded` report with the
limit and observed count (or lower bound); omit payloads/candidate/changes and never claim valid.
No silent truncation. Exact-original preservation applies to inputs admitted within these budgets.
Bounded-refusal clarification (2026-10-19): if echoing a normalized `plot_type` would
itself exceed the existing report-byte budget, use `plot_type:""`, `recognized:false`,
`supported:false` and bounded issue metadata identifying `field:"plot_type"` and its
byte count/lower bound. Handle escaping and invalid Unicode safely; normal names retain
their exact normalized value. Candidate/output overflow uses the same payload-free refusal.

Place report rules and typed outcomes in public `src/dartwork_mpl/mcp/data_repair.py`;
private `_data_repair_json.py` beside it owns pure token parsing/encoding, imported one-way
within the same MCP data-validation capability; the three public exports stay unchanged. `tools.py` only
selects the old/new path and serializes the result; existing legacy validators remain there.
Reuse the existing dispatch's catalog membership instead of maintaining another 18-name list.
This is one capability, no new slice/shared abstraction; the pure module imports no transport,
artifact, plotting, filesystem or network code. No new cross-capability dependency is needed.
Principal/scope is the existing caller and only its supplied string: there is no new identity,
shared lookup or stored asset. Return request data only to that caller; add no payload logging.
Candidate review is a caller action; this feature defines no execute/approval-server protocol.

## Two review examples (selected report members)

`bar`, original `{"categories":["01","02"],"values":["1","2.5"]}`:

```json
{"status":"proposal","changes":[{"path":"/values/0","before":"1","after":1,"reason":"Declared numeric value; JSON type changes, review meaning.","requires_review":true},{"path":"/values/1","before":"2.5","after":2.5,"reason":"Declared numeric value; JSON type changes, review meaning.","requires_review":true}],"candidate":{"data":{"categories":["01","02"],"values":[1,2.5]},"valid":true,"remaining_issues":[]},"requires_review":true,"effects":"none"}
```

`scatter`, original `{"x":[1,2],"y":[3]}`:

```json
{"status":"needs_input","issues":[{"code":"length_mismatch","path":"/x","related_paths":["/y"],"observed":{"lengths":[2,1]},"message":"Paired vectors have unequal lengths.","action":"Restore the intended aligned observations from the source; choose which measurement is missing or extra."}],"changes":[],"requires_review":false,"effects":"none"}
```

Both full reports also include the unchanged raw original and parsed original data.

## Executable acceptance criteria and review decider

Before adversarial review, pin report examples/expected outcomes as independent fixtures.
Use focused pytest output/contract tests in `tests/` (`pyproject.toml` excludes source tests),
seeded generated properties instead of a dependency, and existing CI pytest; no new job.

1. Both examples match fixture paths, changes, actions, preservation and scoped candidate validity; all five shapes have clean, candidate and manual-error examples where applicable.
2. Generated bounded inputs preserve raw input, unchanged data/tokens/order/lengths and extra fields; original/candidate share no mutable state. Identical calls produce identical reports; submitting a clean candidate proposes no further changes.
3. Mixed candidate/manual failures revalidate honestly (`valid:false`, remaining paths); removing the recheck or accepting legacy checkmarks fails a focused test.
4. Strict grammar, precision/portable integer bounds, overflow/underflow, bool/null, duplicates, nonfinite tokens, ragged/empty/wrong containers, bin decreases/duplicate acceptance and every budget boundary yield expected strict-JSON outcomes; arbitrary generated text never leaks an exception.
5. Real FastMCP Client checks on 2.13.3 and installed 3.4.2 pin all 62 omitted and 60 required-fields-present false calls exactly, plus two missing-required false calls under the echoed-flag rule above; all 18 types, malformed/unknown/argument-type cases and unchanged string output schema/framing are covered.
6. Existing discovery/color gates (`tests/test_color_v6_comparison.py`, `tests/test_shipped_colors_hash.py`) pass with untouched baselines; all registered identities and order remain unchanged.
7. Existing MCP validation/hardening tests and focused new tests pass under `uv run pytest <affected files>`; changed rule tests first fail without the behavior or under a targeted mutation, then pass; run existing formatter/type checks only as required by the repository.
8. Public MCP documentation states the JSON-string report, exact five-type scope, manual limits and no effects; no render/apply/store path or extra registration is introduced.

Local acceptance: 409 integrated tests; 199 per FastMCP runtime; Ruff, mypy, Sphinx `-W`, real docs Client example and rendered Tailnet PoC passed. Whole-branch review approved; M1/M2 fixes passed 153 contract checks and focused probes. [Evidence ledger](../plans/2026-10-19-data-repair-suggestions.md#local-validation-ledger); fix-wave re-review, updated docs build/PoC and remote CI remain pending; no merge claimed.
