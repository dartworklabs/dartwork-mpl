# Preserve state and source when core operations reject inputs

Date: 2026-10-21. Status: accepted after independent review and adopted for bounded restoration work on 2026-10-21.
Intended repository path: `docs/superpowers/specs/2026-10-21-core-failure-preservation.md`.
Evidence root: `/Users/wonjun/scratch/dartwork-mpl-agent-followthrough-2026-10-21/`; evidence paths below are relative to this root.

The user authorized followthrough on the four described #500/#501 repairs with “고”. This candidate makes those bounded restorations reviewable before a task plan and implementation. Neither the previous scope worksheet nor any private design is treated as adopted. The unavailable named brainstorming/writing-plans skills were not invoked; the actual separation is design → independent review → task plan → implementation.

## Authority, scope and invariants

- Current authority: user/AGENTS instructions, frozen installed 0.5.6 source in `core-repro/checked-source/`, measured case receipts and the independent evidence review. Parent attests main `994830f1` provenance; the wheel itself does not identify a commit.
- Handbook-read: no Handbook exists. No role/path/current invariant can be extracted from it; no initialization is proposed. Reasons here are failure preservation and compatibility with the measured controls, rather than an invented Handbook policy.
- Four independent repairs stay in `src/dartwork_mpl/io.py`, `src/dartwork_mpl/_colors/_views.py`, `src/dartwork_mpl/style.py` and `src/dartwork_mpl/lint.py`, with behavior regressions in their existing `tests/` modules. Keep the current owners; introduce no shared framework or parser dependency.
- Freeze public signatures, exceptions except the newly rejected nonfinite setter inputs, Issue/Rule fields, rule IDs/severities, `(fixed_code, applied, unfixed)`, MCP discovery 19/10/9/2, presets, shipped colors/digests, dependencies and CI configuration. No digest regeneration.
- Out of scope: C8 explicit-override/history precedence; C7 cleaning policy/API/default, object None or removal reports; unreproduced registration/catalog/decimal/concurrency claims; arbitrary disk/backend rollback; global-state redesign. Four repairs do not imply all historical issue contents are fixed.

## 1. Preflight effective save formats

Current C4: `formats=("png", "jpgg")` rejects only after a real PNG, parent directory, orphan tick-font adoption and visual diagnostics. Valid PNG/PDF/SVG, `formats=("jpgg",), format="png"`, and an empty tuple succeed and return None.

At `save_formats` entry, prepare the complete ordered output plan without adopting fonts, drawing/validating, emitting stem warnings, creating directories or writing files. Consume the supplied format iterable once and retain that plan for execution; do not require a tuple, reject a currently accepted list/generator, or iterate a one-shot input twice. Keep the existing member `lstrip(".")` behavior and error categories; this is not new container coercion or validation policy.

For each planned call, use its actual savefig format selection, following current Matplotlib resolution [E5]:

1. For ordinary output branches, an explicit caller `format` other than None wins; otherwise infer from the planned filename extension and then `canvas.get_default_filetype()` when absent. SVGZ keeps its explicitly forced inner SVG call described below. Lowercase the resolved format as Matplotlib does. Explicit empty format is not a new default alias.
2. With `backend=`, resolve the selected FigureCanvas class through Matplotlib's backend registry and test the `print_<format>` attribute as Matplotlib does. Without it, accept that attribute on the current canvas first, otherwise require a registered canvas for the format. A missing registration, or explicit backend class missing that attribute, rejects before the dm effects listed above; do not additionally require a registered fallback class to expose a class-level print method. Do not replace this with membership in `get_supported_filetypes()` alone.
3. Resolve without constructing or temporarily attaching a new canvas, drawing, or calling savefig. Preserve custom `module://` backend selection and registered output formats; no built-in-backend allowlist. Backend-module loading may have its own effects, as in savefig; registered/custom canvas instantiation and render failures remain on the original savefig path, outside rollback guarantees.

Preserve the existing branch dispatch: deterministic SVG/PDF metadata and SVG salt, and SVGZ's internal SVG save plus fixed gzip timestamp. Preflight the inner SVG capability for SVGZ; do not silently add support for its existing duplicate-format kwarg error. Keep caller metadata, bbox and other kwargs on their existing paths. This preflight promises format/backend capability rejection, not validation or rollback of arbitrary kwargs, renderer or disk failures.

Only after all planned formats pass, execute the current adoption/diagnostic/stem-normalization/mkdir/save sequence. An empty iterable still reaches its existing successful adoption, diagnostics and directory effects and returns None; do not turn it into an early no-op.

Acceptance in `tests/test_io.py` and `tests/test_orphan_tick_font.py`:

- C4 invalid-later with adoption enabled: ValueError, absent destination, unchanged tick fonts/figure and full rcParams, no visual diagnostic or stem-normalization warning. A failing first or later effective format has the same preservation property.
- Actually save and inspect PNG/PDF/SVG; preserve PNG bytes at `plot.jpgg` with `format="png"`, successful None returns and empty-tuple effects. Preserve leading dots, list and single-use generator order, format=None inference and caller kwargs.
- Exercise current-canvas/registered fallback and an explicit supported/unsupported installed backend pair without custom module execution. Check deterministic SVG/PDF/SVGZ paths and existing metadata/rc isolation tests; do not claim every optional backend was exercised.

## 2. Reject nonfinite component assignments before writes

Current C5: OKLab a=NaN and OKLCH L=Inf store nonfinite coordinates; RGB r=NaN/-Inf instead clamp to finite values and silently change the color. Finite RGB r=2 clamps, finite OKLab L=2 succeeds, and constructor NaN already raises ValueError.

At all nine existing setters (`oklab.L/a/b`, `oklch.L/C/h`, `rgb.r/g/b`), convert the requested numeric input as currently required, then reject NaN/±Inf with constructor-style ValueError before normalization, clamping or any Color coordinate write. Preserve existing rejection of negative chroma and nonnumeric inputs. Compute replacement coordinates before committing writes; do not replace the Color model or change conversions.

Finite values keep the current RGB clamp, hue normalization, allowed finite extreme L and RGB no-op precision guard. No new [0,1] lightness bound, gamut policy, derived-coordinate bound or range policy follows from checking the supplied component's finiteness.

Acceptance in `tests/test_color_view.py`, `tests/test_color_conversion.py` and `tests/test_shipped_colors_hash.py`:

- For every setter and NaN/±Inf, assert ValueError and exact equality of the pre/post canonical OKLab tuple. Preserve C5 finite controls, negative-chroma rejection, conversion tolerance and out-of-gamut RGB no-op precision.
- Add a bounded seeded property over finite starting colors, setter choices and nonfinite inputs: rejection preserves the source tuple. The source tuple is the oracle; do not reimplement color conversion. Keep shipped-color hashes unchanged.

## 3. Validate style requests before applying them

Current C6: invalid option/value on `presentation-kr` leaves 11 rcParams and locale semantics changed after rejection. The next scientific call already equals the fresh control. Integer preset input currently raises AttributeError without measured mutation.

`Style.use` must resolve the entire preset name/list in its current order and resolve every dotted/underscore kwarg before font loading, stack application, live rcParams writes, semantic changes or managed-key bookkeeping. Validate override values against Matplotlib's existing RcParams validators in an isolated candidate, never by changing live rcParams and rolling them back. Only then apply the existing successful stack and caller override path.

Keep unknown-string KeyError behavior and actionable names. Preserve the current rejection path/type for invalid non-string inputs, including measured integer AttributeError; do not add a friendliness TypeError policy. Do not alter valid single/list order, empty-list behavior, kwargs precedence, supported values, or `_dm_managed_keys` history semantics. This repair adds no concurrency or precedence redesign.

Acceptance in `tests/test_style.py` and `tests/test_style_chain_parity.py`:

- Invalid option, invalid rc value, unknown preset and invalid mixed list reject with the applicable existing exception type and leave immediate full rcParams, semantic tokens, and subsequent style behavior equal to the pre-call/control path. Use a mixed valid-then-invalid kwargs case to expose partial update.
- The measured integer case still raises AttributeError without effects. Scientific, presentation-kr, valid ordered lists, empty lists and dotted/underscore kwargs retain existing results, including the already-passing next-scientific control.
- Verify bookkeeping preservation through a subsequent public style transition; keep C8's measured history behavior outside this repair.

## 4. Bound static detection, fixing and migration

Current C1–3: executable-call rules report comments/strings/local methods, miss a pyplot alias, corrupt nested receivers or invent missing names, rewrite ggplot to an unsupported preset, mutate triple-string values, and rewrite malformed input. A canonical Figure fix works. A later unchanged comment is currently reported as both applied and unfixed after its offset moves.

Use the standard-library AST/tokenizer for source spans and small binding facts alongside the existing catalog. Do not execute, import, evaluate or compile-and-run submitted source. No new parser dependency or whole-source AST unparse is required.

Safe autofix and type-dependent detection use this initial proof envelope:

- Recognize ordinary `import matplotlib.pyplot as p`, `from matplotlib import pyplot as p`, `import dartwork_mpl as d`, and `from matplotlib.figure import Figure as F`, including their non-aliased forms where Python binds them. No wildcard/dynamic imports or implicit names establish safe autofix proof.
- Prove a simple-name Figure from `f=p.figure(...)`, `f=F(...)`, or the Figure target of direct `f, ax=p.subplots(...)`. Prove scalar Axes targets only for a statically single-axes subplots call. For safe autofix, imported/direct bindings must dominate the use in the same straight-line lexical scope; do not inherit runtime facts across scopes.
- Parameters, assignments, deletes, declarations and shadowing invalidate affected bindings. Unresolved branch/loop/try flow and writes to a tracked object's relevant attributes invalidate those facts; do not infer types through aliases, arbitrary attributes, returns or dynamic flow. Conservative loss of proof is acceptable; a later explicit unconditional import/constructor may establish a new fact.
- Attribute results such as `self.fig` and `ax.figure` are outside this initial envelope: leave them unchanged and unapplied, with no false critical claim of a matplotlib violation. A proven pyplot/Figure violation whose fix is unavailable remains an unfixed issue with its existing severity.

Detection also preserves the established standalone-snippet convention for unshadowed canonical plt/ax/fig/dm receivers; omitted imports alone must not erase current literal/name, savefig or other applicable diagnostics. This convention is not sufficient autofix proof. Explicit conflicting bindings/reassignment suppress that conventional receiver until re-established; arbitrary unknown names/attributes gain no such convention. Built-in executable-call/name rules inspect actual syntax; definitions and mere string/comment mentions are not calls. Alias p/d and proven ax2 receive the existing applicable rules. Keep deliberate text-only rules such as `zero-resize-mention`, custom rule detector semantics, and actual string-valued argument rules (`invalid-color-name`, colormap/name, raw hex, jet, width) active in their intended contexts. A blanket “ignore every string token” filter is forbidden.

Autofix accepts only complete no-argument calls on a proven simple-name Figure with an existing unshadowed dm alias: `f.tight_layout()` → `d.simple_layout(f)`. Reject argument-bearing, pyplot-only, missing-dm and unknown receiver rewrites; never splice a suffix of `self.fig`/`ax.figure`, invent imports/fig names or select the current figure implicitly.

Style replacement in both fixing and migration needs a proven pyplot owner, a proven dm alias and a single literal supported dm preset. Lists, dynamic values and unsupported names including ggplot remain unchanged; a proven pyplot-style warning remains unfixed. Supported-preset spelling alone must not manufacture a dm binding.

Tokenization or AST failure makes both rewriting functions return the exact original source; autofix reports no applied fixes. Executable rules without valid syntax or a receiver basis under the detection envelope do not fabricate critical issues; deliberate text-only rules may still report. No partial-token or whole-source regex fallback.

Migration preserves every existing comment and literal value, including triple strings and f-string text, plus original CRLF/newline/continuation bytes outside edits. Add hints only at a proven executable logical-statement boundary; defer when insertion would split a continuation or literal. If the proposed complete result is invalid Python, return the original. Reapplication must be idempotent.

Before edits, assign each issue an internal identity from its rule and original occurrence span/ordinal. Plan nonoverlapping edits against that source, map surviving occurrences through edits, and reconcile a result scan through this map. Mark applied only an actually edited original occurrence whose violation is removed; offset movement never implies application. Keep applied locations in original source and unfixed locations in returned source, as currently exposed; the internal identities must be disjoint.

Keep public `column` as the current implementation's zero-based absolute Python-string character offset; convert AST UTF-8 byte columns when needed, without normalizing Unicode or CRLF. The existing Issue docstring's “byte” wording is inconsistent with runtime behavior and may be corrected without changing units or fields.

Acceptance in `tests/test_lint.py` and `tests/test_migrate_legacy.py`:

- Replay saved C1–3 inputs with these accepted/refused outcomes: no comment/string/local-method criticals; p.style is detected; ax2 advisory remains; canonical Figure fix applies; nested/axes-attribute, missing-name and ggplot cases remain byte-identical and unapplied. Preserve existing no-import canonical fragment diagnostics for ax color/font/line widths, fig.savefig, plt.imshow cmap and plt.subplots width; retain their tests rather than rewriting expectations to remove useful diagnostics.
- Original triple-string value and malformed source remain exact; migration's malformed refusal is a new regression expectation, not an already measured baseline result. Accepted edits parse, run as trusted fixed fixtures through actual dm layout/style paths, and are idempotent.
- Mixed fixed/unfixed occurrences, repeated same-line violations, Unicode prefixes, CRLF and continuations retain correct locations and disjoint original identities. Use bounded seeded valid-source/comment/literal variants and malformed mutations to assert preservation, parseability and idempotence without new dependencies.

## Delivery and review sequence

1. Independently review this candidate against [E1–E5] and the frozen compatibility boundaries, then write a task plan before production edits. Record the actual review/task tools; do not claim missing named skills ran or reopen permission for already-authorized restorations.
2. In an authorized implementation workspace, check the intended base against its current target before editing. Keep the protected host checkout and the independent PR513 snippet annotation work untouched. Implement in order: save, setters, style, then static detection/fix/migration, with separate reviewable diffs.
3. For each repair, add its behavior regression in the named existing tests, observe the assertion fail on baseline, implement, and record green plus passing controls. Use bounded seeded properties where stated; do not add dependencies, CI gates or a broad environment matrix.
4. Run the repository's existing focused checks and required gates identified by the task plan; no test command was run or invented by this design task. Inspect actual saved files, state snapshots, returned source and trusted fixed-fixture behavior; green parse/unit output alone is insufficient.
5. Review final diff for design intent and public/color/discovery compatibility; recheck the integration target. If any visible output changes, provide actual before/after renderings at matching scale before merge/deploy, following the project's PoC/access rules.

## Evidence and remaining limits

[E1] `core-repair-scope/scope-proposal.md`, `core-repro-review/review.md`: bounded evidence and controls; audit process exit 0 is not product success, and no whole-machine no-write claim is adopted.
[E2] `core-repro/case-{1,2,3}/result.json` and saved input/output .py pairs: exact static failures, canonical success and malformed-autofix qualification. Parent-read pinned `tests/test_lint.py:122–200` supplies the standalone-fragment compatibility controls.
[E3] `core-repro/case-4/result.json`: real partial PNG SHA256 `f735c6cdfcd51f2830550bb0994bbafbe3772a970ac61c50a028a19c76120c9c`, override and empty controls.
[E4] `core-repro/case-{5,6}/result.json`: exact setter/source-state and style rc/semantic snapshots, exceptions and successful controls.
[E5] `core-repro/source-manifest.json`; `core-design/matplotlib-format-resolution.json` and its excerpt: Matplotlib 3.11.2 `core-env/lib/python3.12/site-packages/matplotlib/backend_bases.py:2094–2245`, excerpt SHA256 `6addbe9f7c1d5b854b712c91a42fd9e50e081d0163069e2d5a930bb9621fa755`. Lookup read source only, without imports/backend execution.

Conclusion: these four bounded restorations have concrete failure and preservation oracles and can proceed through independent review into a task plan under current authorization. They do not decide new data policy, style-history precedence or broader issue completion.

Unresolved coverage: evidence ran on Python 3.12.13/Matplotlib 3.11.2; supported Python >=3.10 and all nine setters, iterable/backend variants and malformed variants still require the targeted implementation checks. Optional/custom backends and arbitrary disk/runtime errors remain unmeasured. No product run, repair PASS, source/test/config change or implementation plan is claimed here.
