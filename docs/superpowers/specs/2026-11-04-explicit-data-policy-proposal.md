# Explicit native data policy — decision proposal

**APPROVED — 2026-11-04.** Issue [#501, task 7 (P0)](https://github.com/dartworklabs/dartwork-mpl/issues/501).
The user approved option A with “진행해” in this session on 2026-11-04.
Approved proposal SHA256: `e0aba12215cd7b1580eea7490abdf241334d2075b8e32da33f3adf4d44c2a1a6`.

## Purpose and success criteria

Give Python callers an explicit choice to reject, retain or remove nonfinite
observations, with original indices and an auditable removal record. Keep every
call that omits the new policy on the exact historical path, including tuple
return, warnings, exceptions, identity/storage behavior and import/pickle aliases.
Task 7 remains partly open after this increment: object and multidimensional
interpretation need a separate decision supported by a real use case.

## Scope and exclusions

Proposed scope: `dm.validate_data`, its existing aliases and two diagnostic types,
one-dimensional signed/unsigned integer and real floating NumPy dtypes, one or
two vectors, opt-in diagnostics, relevant consumer guidance and focused tests.
No new dependency, configuration singleton, implicit cast, imputation, clipping,
sorting, deduplication, object coercion, matrix flattening or plotting change.
No MCP tool, schema, ordering, description/docstring, report-v1 or repair behavior
change; #523 freezes those surfaces. Implementation is tracked in the linked plan.

## 현재 권위와 상태

- **질문 종류**: current reality / current contract / proposed change.
- **role**: purpose / architecture; **path**: `AGENTS.md`.
  **실제 정본**: repository instructions and exported callable.
  **확인한 현재값**: native matplotlib model, visual/color freeze, MCP freeze,
  executable completion criteria and design documents at most 200 lines.
- **role**: workflow; **path**: `docs/development/structure-refactor/agent-followup-handoff.md`.
  **실제 정본**: handoff plus live issue #501, read 2026-11-04.
  **확인한 현재값**: option A is approved here; prior independent-array fix is shipped.
- **role**: native data contract; **path**: `src/dartwork_mpl/validate/_data.py`.
  **실제 정본**: `validate_data`; **확인한 현재값**: behavior below.
- **role**: verification; **path**: `src/dartwork_mpl/validate/tests/test_data_ownership.py`.
  **실제 정본**: compatibility assertions pin aliases, signature, warning location,
  ndarray identity, object preservation and historical multidimensional behavior.
- **role**: MCP contract; **path**: `src/dartwork_mpl/mcp/plot_data/validate.py`,
  `validators.py`, `repair.py`; `tests/contracts/test_mcp_data_repair_contract.py`.
  **실제 정본**: shape parsers, scoped report-v1 and real-client wire fixtures.
  **확인한 현재값**: these are distinct from the native array cleaner.
- No Handbook is present; this is scoped context from the authorities above,
  not a substitute Handbook or a request to initialize one.

## 지켜야 할 현재 불변식

1. `policy=None` (including omission) preserves every existing data behavior.
2. The five existing positional parameters and `(x_array, y_array_or_None)`
   return remain usable; all exported aliases still resolve to the same function.
3. Original unequal lengths remain independent even if cleanup equalizes them.
4. Input storage is never written; no implicit data replacement or clipping.
5. Existing MCP wire and report-v1 semantics remain unchanged.

## 설계 이유와 제약

- **role / path**: workflow / the handoff above and live #501 task 7.
  **이유·감수한 비용·적용 조건**: cleaning can conceal missing observations;
  explicit policy is needed, but changing the default is not authorized.
- **role / path**: verification / `test_data_ownership.py` above.
  **이유·감수한 비용·적용 조건**: object passthrough and 2-D quirks are pinned
  compatibility facts; preserving them on the legacy path costs two paths.
- **role / path**: purpose / `AGENTS.md`.
  **이유·감수한 비용·적용 조건**: small independently verifiable increments;
  preserve MCP freeze rather than expanding the protocol for this policy.

## 충돌·미확인

- Option A is approved above; broader task 7 policies remain unapproved.
- Exact-signature assertions must be deliberately updated only after approval;
  adding a keyword is an additive API change, not exact signature preservation.
- Broader object, categorical missingness, complex, masked, datetime and N-D
  semantics are unresolved. The first increment rejects them only when opted in.
- Installed-wheel and MCP execution of the native function are proposed gates,
  not completed evidence. Current MCP probes exercise `validate_plot_data` only.

## Current observations (not proposed semantics)

Base: clean HEAD = live `origin/main` = `e70716bb827fed28b318ef6bb31dc5c5e829fae0` before drafting.
Command: `uv run --frozen python ~/scratch/dartwork-followup-20261104/data_policy_probe.py`.
Environment: Python 3.10.20, NumPy 2.2.6, FastMCP 3.4.2; editable source install.
Raw evidence: `~/scratch/dartwork-followup-20261104/data-policy-current.json`; script adjacent.
All 15 native probes left inputs unchanged; six MCP calls used the real
in-process client, without rendering or executing caller source.

| Probe | Observed current result |
| --- | --- |
| Aligned x `[0,NaN,2,3,4]`, y `[10,11,Inf,13,14]` | x `[0,3,4]`, y `[10,13,14]`; two count-only warnings |
| `allow_nan=True`, `[0,NaN,Inf]` | Both NaN and Inf retained; no warning |
| Unequal x/y, `require_same_length=False` | Independently cleaned; no cross-mask after lengths coincide |
| Equal x/y, `require_same_length=False` | Still aligned; x's missing row removes the matching y row |
| Object `[1,None,NaN,Inf,"A"]` | Same array returned, no warning; list with None also passes |
| Numeric 2-D x with NaN | x alone flattens; with 1-D y raises `IndexError` before warning |
| Finite 2-D / scalar / short independent y | 2-D shape retained / `TypeError` / short y accepted |
| x `[1,NaN]` | Warns then raises `ValueError` for one remaining point |
| MCP legacy scatter with NaN / report=True | Shape success / `nonfinite_token` rejection, effects none |
| MCP bar null label / mismatched pair | Legacy null label accepted; v1 asks for label / alignment input |

## Options and recommendation

| Option | Benefit | Cost / decision |
| --- | --- | --- |
| **A. Add opt-in numeric 1-D policies (recommended)** | Solves explicit failure/retention/removal with original indices; legacy untouched | Additive native API; object/N-D remain pending |
| B. Replace default cleanup with strict or expand `allow_nan` | Small apparent surface | Breaks current defaults or overloads a boolean; reject |
| C. Define every dtype and dimension plus a new report API now | Broad uniform model | Unproved categorical/matrix meaning and larger review; defer |

Recommend A: numeric missingness has a reproducible risk and stable row indices.
The separate legacy path costs maintenance. Option A was selected by the user.

## Proposed contract for option A

Add keyword-only `policy=None` after the existing five parameters; accepted
non-None values are exactly `"strict"`, `"preserve"`, `"clean"` (case-sensitive).
No new return mode: every successful call returns the historical two-item tuple.

- `policy=None`: execute the legacy behavior exactly, including permissive flags,
  object passthrough, N-D behavior, warning order/text/location and exceptions.
- Explicit policy: `allow_nan` must be the boolean `False`; `True` with *any*
  explicit policy raises `ValueError` before inspection/cleanup. False remains
  the legacy default placeholder; policy alone selects the opt-in behavior.
  There is no silent precedence rule, including redundant preserve/True.
- Explicit flags: `require_same_length` must be bool; `min_points` must be a
  positive Python/NumPy integer excluding bool. Invalid values raise `ValueError`.
- Apply `np.asarray` without dtype coercion, then require ndim==1 and dtype.kind
  in `iuf` for each supplied vector. Object (including None or boxed NaN/Inf),
  strings, bool, complex, masked arrays and N-D/scalar inputs raise `ValueError`
  identifying the offending argument and supported scope; no flattening or cast.
  Masked inputs must be detected before `np.asarray` could discard their mask.
- Validate shape/dtype, then lengths and original minimum counts before policy
  action. Conversion failures become safe `ValueError` with suppressed chaining.
  Check min_points on **each** supplied independent vector in this opt-in path.
- If y exists and original lengths are equal, vectors are aligned even when
  require_same_length=False. Nonfinite issues use original zero-based positions.
  Unequal lengths raise with require_same_length=True; otherwise stay independent.
- `strict`: any numeric NaN or +Inf/-Inf rejects with `DataPolicyError`, a
  `ValueError` subclass. No removals, returned partial result or cleanup warnings.
- `preserve`: retain all numeric values and order, including Inf and NaN;
  this is retention, not a claim of plot/domain validity or infinity safety.
- `clean`: remove nonfinite observations. For aligned vectors use one union
  mask computed from both original vectors; otherwise each vector has its own
  mask. No clip/impute. Verify all resulting vectors meet min_points **before**
  returning or emitting a success diagnostic; failure is `DataPolicyError`.
- With finite data, strict/preserve/clean retain `np.asarray` identity, dtype,
  strides and memory sharing. Clean copies only vectors requiring row removal.
- With issues, successful preserve/clean emits one `DataPolicyWarning`
  (`UserWarning` subclass, caller stacklevel); finite success emits none.
  Export both types from `dartwork_mpl` and `dartwork_mpl.validate`; define them
  in the native owner. No new exports in the legacy helpers shim are needed.
  Read-only attributes: `policy`, `alignment` (single/aligned/independent),
  `issues`: tuple of `(argument, index, kind)` triples (x then y, ascending index;
  kind nan/posinf/neginf), and `removed_indices`, `kept_indices`,
  `proposed_removed_indices`: tuples of `(argument, tuple[int, ...])` pairs.
  Include every supplied argument, x then y, with indices in original order.
  On successful clean, removed/kept describe the returned arrays, including
  finite aligned partner rows. On preserve or any error, removed is empty per
  argument and kept lists all original indices. Proposed removals is empty per
  argument except on failed clean, where it records the rejected candidate mask.
  Counts derive per vector; aligned row totals count the union once.
  Local structured records are complete and cost O(n) memory when issues exist.
  All explicit-policy diagnostic text is at most 1,024 characters, includes
  policy/counts, shows at most 10 original indices total and counts omitted ones.
  Never interpolate input values, arbitrary reprs or conversion-cause text.
- Invalid policy/options/shape/type/length use descriptive `ValueError` without
  partial cleanup. DataPolicyError carries the above diagnostics for nonfinite
  rejection or insufficient surviving points; no externally visible mutation.

## Structure, validation and approval boundary

Ordinary library work (axis 6); follow [the implementation plan](../plans/2026-11-04-explicit-data-policy.md).
The native owner remains `validate/_data.py`; aliases forward the same callable.
No cross-slice dependency or MCP-to-native validation delegation is proposed.

After approval, focused regression/property tests must verify mask union,
original-index accounting, input immutability, identity without removal, dtype,
conflicts, rejected scope, threshold failures and legacy parity. Check diagnostic
exports/fields, text bounds and a secret-like conversion input absent from text.
Use seeded vectors if needed; tests must fail under a plausible mask/index mutation.
Run inspected safe data tests and existing MCP data-repair contracts only; avoid
docs scans and the restricted legacy design document and all copies.

Bounded acceptance: build/install a wheel into a disposable environment; outside
the checkout run finite, strict failure, preserve gap and aligned clean calls.
Assert installed module path, tuple shape, diagnostics and original inputs.
Through a real MCP client call existing `render_plot` with trusted synthetic
source invoking **that same** `dm.validate_data`; use an intentional sentinel
exception containing the asserted probe outcome to avoid chart output, and
check the existing execution-error envelope. Exercise strict/preserve/clean and
the omitted-policy path; assert the function result inside the executed source.
This validates native execution through MCP without turning `validate_plot_data`
into the native cleaner. Compare discovery/schema/docstrings and existing
validate_plot_data legacy/report fixtures unchanged. In-process transport proves
only that transport; add a bounded stdio invocation for packaged server startup.
After approval, add these checks to existing pytest CI; no new gate is added here.

Approved: A's keyword and diagnostic-type additions, allow_nan conflicts,
numeric scope, warning records and per-vector minima as specified above.
Object/N-D meaning and a separate return-report API remain separate decisions.
