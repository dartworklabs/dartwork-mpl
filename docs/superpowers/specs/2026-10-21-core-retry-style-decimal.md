# CORE #501 items 4–6 — adopted design

Status: adopted for implementation by the parent after CORE-I1 correction; runtime acceptance remains open.
Authorization: user go for bounded #501 items 4–6 restoration; exact adoption receipt is retained outside the product tree.
Base: detached d2b6d0b1ce8897d24398aa5a4de5d97f23ab2a05; parent refreshed origin/main at this identity before source edits.
Independent original review identified CORE-I1; its corrected ownership lifetime policy was adopted by the parent.
Source paths below are repository-relative; original evidence remains frozen in the external task evidence directory.

## 현재 권위와 상태

| role | path | invariant / original baseline at adoption |
| --- | --- | --- |
| architecture | `AGENTS.md` | Native Figure/Axes/GridSpec, public signatures, source contracts and shipped assets are authoritative; preserve native customization and default presets. |
| registration | `src/dartwork_mpl/_colors/_register.py` | 99 dc colormaps; ordinary loaded calls return None; reload fails on dc.afterglow. |
| style | `src/dartwork_mpl/style.py`, `tests/test_style.py` | Incoming declared keys win; explicit kwargs apply afterward; incoming-silent caller settings survive. Historical key exclusion wrongly drops later native edits. |
| ticks | `src/dartwork_mpl/util.py` | set_decimal returns None and uses Python fixed-point formatting; it currently replaces dynamic locators. |
| family errors | `src/dartwork_mpl/_colors/_api.py` | Unknown strings raise ValueError with nearest names; non-string names leak startswith AttributeError. |
| verification | `pyproject.toml`, `.github/workflows/ci.yml`, `tests/test_shipped_colors_hash.py` | Python >=3.10, matplotlib >=3.10.1; CI Python 3.10–3.13; existing tests/Ruff/mypy and immutable color digests; no new gate/dependency. |
| runtime | `src/dartwork_mpl/style.py`, `src/dartwork_mpl/util.py`, `src/dartwork_mpl/_colors/_register.py` | Incoming declared preset priority and native registry/tick APIs remain; recorded probes establish current defects, not issue wording alone. |
| trust boundary | `src/dartwork_mpl/mcp/artifacts/policy.py`, `src/dartwork_mpl/mcp/execution.py`, `src/dartwork_mpl/mcp/tools.py` | Trusted local code retains inherited cwd/OS authority, 512KiB source and finite timeout (0,120]; discovery/retention/privacy/namespace/pyplot fallback unchanged. |

No Handbook exists; the authority table and four sections here preserve current state, invariants, reasons/constraints and unresolved limits.
No Handbook initialization or MCP-policy change is included.
Named Superpowers brainstorming/writing-plans skills were unavailable after bounded parent search.
This explicit worker draft follows diagnosis → scope review → checkbox plan → implementation; it claims no invocation of those skills.

## 지켜야 할 현재 불변식

- Keep signatures, valid calls, None returns, preset files, default values, 99 map names and every shipped color/hash.
- Incoming preset declarations still win over prior rcParams, even if they explicitly declare a matplotlib default value.
- Explicit kwargs on the current use call still apply last; native artist customization remains native.
- Reject external colormap collisions without force/overwrite; no global state framework or new dependency.
- Keep PR #514 invalid-style state preservation, semantic tokens, subsequent successful calls and valid one-shot kwargs.
- Only the bounded source/test files and this spec/plan are authorized; excluded proposal/copies remain inaccessible.

## 설계 이유와 제약

Registration: build the same ordered expected maps locally; mark newly registered maps with a stable private package provenance tag.
The tag is a local package convention, not an unforgeable identity/security control; registry public copies preserve it (verified).
During an unloaded/reload/retry pass, preflight every intended name before registering any missing map.
Reuse an existing name only when the package tag and exact native colormap equality both match the expected map.
Also require the expected name/type/N so native equality cannot equate differently named or typed maps by LUT alone.
Native equality includes the complete lookup table, bad/under/over values and colorbar_extend; visible samples alone are insufficient.
An untagged map is external even with identical LUT bytes; tagged but changed extremes is a conflict.
Reject a collision as ValueError naming the map and safe remedy; preserve that map and every pre-existing entry.
For static pre-existing collisions, add zero maps and leave loaded false; removing the conflict permits a complete retry.
Ordinary successful loaded fast path remains; no ongoing monitoring of later external registry edits.
No transaction promise for unrelated concurrent registry writes or arbitrary later backend failures; own partial maps remain reusable on retry.
Upgrading code in a process containing old untagged maps may require process restart; do not infer provenance from equal colors.

Style: replace lifetime key exclusion with a private snapshot of keys/normalized values written by the last successful preset stack.
Copy mutable values so caller list/Cycler edits cannot mutate the snapshot itself.
Before the next reset, classify a prior-owned value equal to the last preset value as unchanged preset residue.
A value different from that snapshot is a detectable caller edit, including when it equals the matplotlib default.
For keys not owned by that last stack, preserve existing nondefault caller settings as before.
Restore detected caller settings only for keys the incoming stack is silent about; incoming-owned keys still win.
Store preset-produced values before current use kwargs; remove canonical kwarg keys from ownership after application so known caller intent survives the next silent-key switch, including same-value kwargs.
Discard previous ownership when the next stack succeeds; failed use validation leaves bookkeeping and live state unchanged.
A native same-value rewrite cannot be distinguished from untouched preset residue; treat it as residue.
Users needing that exact value after a later switch apply/pass the override after/with that switch.
Context lifetime (CORE-I1): deep-copy the outer ownership at entry before any temporary mutation.
Keep native `plt.style.context` application/restoration semantics; once its temporary preset applies, merge only known preset-written keys and their normalized preset-only values into copied ownership.
Retain inherited ownership for every key the context does not write: a report context still inherits dark-owned silent axes.edgecolor.
Keep kwargs last and known caller intent: capture preset-only values before kwargs, then remove canonical kwarg keys from merged ownership as in use(); equal-value explicit kwargs remain caller intent.
A detectable explicit kwarg/native edit on an incoming-silent key remains a caller override; incoming-declared keys retain priority and the same-value native-write limit remains.
In finally restore the saved outer ownership alongside existing semantic-token restoration and native rcParams rollback, even after body use(), body exceptions and nested contexts.
Each nested entry saves its immediate outer state; exit restores that state so the next public transition behaves like its no-context control.
New bookkeeping exists solely for this repair and must share the context and test-isolation lifetimes; add no public API.
Do not hold a lock across yield, observe assignments, reinterpret all past writes as stronger than incoming declarations, or introduce thread/global-state machinery.

Decimal: install native dynamic fixed-point formatters on requested axes; preserve their existing locators and current view limits.
Formatter text uses Python float fixed-point formatting, preserving half-even, negative zero, requested precision and None return.
A later set_data/relim/autoscale_view or view-limit change must produce labels for the new tick values.
Leave an axis requested as None untouched and preserve custom locators; do not normalize NaN/Inf data or choose new tick density.
Check a supplied format precision with the same formatting operation before that axis's formatter is installed, preserving immediate invalid-precision errors.

Type errors: guard only the proven style-name and family-name boundaries before strip/startswith or live state mutation.
Non-string style scalar/list members, style_path/load_style_dict names, context names, colors names and show_colors name members raise descriptive TypeError.
Keep unknown string use/context KeyError, style_path ValueError and family ValueError with existing suggestion messages.
No coercion to strings, PathLike expansion, container protocol expansion, range policy or whole-API error sweep.

Ownership: registration tests stay in `tests/test_color_v5_register.py`; family-name cases in `tests/test_color_model_b_api.py`.
Style and decimal tests stay in `tests/test_style.py` and `tests/test_util.py` because pytest testpaths is tests; no source-test relocation.
Update `_style_state`, `_restore_style_test_state` and `isolated_style_state` to copy/save/restore the new bookkeeping.
Align affected cleanup with `tests/conftest.py` rcdefaults teardown so new ownership cannot leak across tests/branches; behavioral assertions inspect public state, never its new representation.
No new slice, cross-slice dependency, import-graph gate, public wrapper, CI gate or dependency is required.

## Mechanical acceptance and real-path verification

- Reload/retry: real subprocess registry; unchanged maps exactly equal across successful repeat/reload sequences, including extremes.
- Real external middle/last collision: before/after registry equal and zero package additions; remove only created conflict and retry succeeds.
- Reject same-LUT untagged external maps and tagged maps with changed bad/under/over/colorbar metadata; preserve unrelated maps.
- Style: fresh assignment and dark→same assignment→scientific both retain axes.edgecolor #a1b2c3; untouched dark residue resets.
- Controls: incoming font.size=7.5 overrides prior99; pdf.compression=0 survives; default-valued caller edits and current kwargs remain valid.
- Context body: scientific→context(dark)→use(scientific) matches ordinary dark→scientific: axes.edgecolor is native black, not #555555.
- Context exit: dark→context(report){use(scientific)}→exit→scientific matches the identical no-context control; outer dark residue does not leak.
- Assert full public rcParams and semantic-token restoration at each normal/exception/nested exit, then compare the next transition with controls.
- Cover inherited outer-owned silent keys and detectable caller overrides surviving rollback; copy private state only for isolation, never regression assertions.
- Use native subprocess state, semantic/next-call comparison, mutable-value edit case and bounded seeded sequences only for the stated invariants.
- Decimal: render data [0,1,2] then x[100,200,300]/y[1000,2000,3000]; assert new in-view ticks/labels and unchanged locator contract.
- Compare finite seeded formatter values and exact half ties against Python formatting; existing signatures/None-axis/None-return controls pass.
- Before implementation, observe a new meaningful assertion-red for the bug; retain exact red then green evidence. Context guards may already pass baseline and must not be called reproduced failures.
- Run affected existing tests and immutable shipped-color tests, Ruff/format/mypy in existing environment; do not regenerate digests or repeat whole-suite gates.
- Final real path repeats normal imports, preset switching and actual PNG/PDF render/export; inspect output images and numeric ticks.
- Visible style/tick changes require same-scale current-versus-candidate rendered PoC before merge, with crop if needed; no candidate built this round.
- Browser review, if supplied later, uses existing verified persistent Tailnet HTTPS service; local review images are also permitted artifacts.

## 충돌·미확인

Observed original baseline: reload ValueError; middle dc.haze_r collision leaves43 maps and retry fails; fresh-vs-dark edgecolor differs; changed-data ticks remain old.
Wrong-type style/family AttributeErrors are reproduced; existing style tests currently record AttributeError for two malformed inputs and must change deliberately.
Current shipped-color oracle passes all five surfaces and combined hash on Python3.12.13/matplotlib3.10.9; other supported runtimes were not run here.
Implementation observed meaningful manual-edit/context A assertion-red before repair; normal/exception/nested context B controls were baseline green.
Focused regressions now pass; final parent review and PoC presentation remain separate acceptance steps.
This correction preserves registration, decimal and type-error policies; parent adoption is recorded and this document precedes production edits.
No new data/permission/default policy is proposed.
Unobservable same-value native writes, old untagged live registries and arbitrary concurrent mutations remain explicit limits, not invented fixes.
