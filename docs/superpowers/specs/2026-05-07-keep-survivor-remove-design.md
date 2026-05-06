# Removing the keep-Borderline Survivors — Round 4 of #141

- **Date**: 2026-05-07
- **Issue**: [#156](https://github.com/dartworklabs/dartwork-mpl/issues/156)
- **Status**: Draft (awaiting maintainer review)
- **Builds on**: [#141](https://github.com/dartworklabs/dartwork-mpl/issues/141) / [`2026-05-05-prune-low-value-utils-design.md`](2026-05-05-prune-low-value-utils-design.md) / [`docs/development/api_audit.md`](../../development/api_audit.md)

## 1. Context

#141 audited the public API and removed obvious wrappers across three
rounds. A small set of items survived as `keep` despite the
[`utilities_not_wrappers.md`](../../philosophy/utilities_not_wrappers.md)
philosophy — kept on callsite count and "composition value":

| name | LOC | callsites | audit verdict |
|---|---|---|---|
| `style_spines` | 14 | 9 | keep |
| `add_grid` | 11 | 15 | keep |
| `minimal_axes` | 7 | 27 | keep |
| `auto_select_colors` | 63 | 33 | keep |

Three of the four (`style_spines` / `add_grid` / `minimal_axes`) are
1–3 line matplotlib calls with curated default kwargs. The fourth
(`auto_select_colors`) is structurally different: a curated palette
lookup, not a kwarg recipe — its body holds four hard-coded color
lists that *are* the dartwork-mpl recommended palettes for
categorical / sequential / diverging series.

## 2. Pivot from earlier draft

This spec's earlier draft proposed introducing a 4th classification
value `defaults` to keep these functions but segregate them under
`dm.defaults.<name>`. After review the path was rejected:

1. **Naming was the signal.** No candidate (`defaults`, `preset`,
   `recipes`, `curated`) carried the semantics cleanly. When an
   abstraction refuses a name, the abstraction is wrong.
2. **The curated kwargs already live elsewhere.** Color names like
   `oc.gray3` are exposed by the color system; design recipes already
   appear in `docs/usage_guide/` and AI templates. The function form
   was redundant packaging, not the canonical home.
3. **#141 philosophy.** `utilities_not_wrappers.md` says don't wrap
   1–3 line matplotlib calls. A new namespace for them concedes the
   abstraction while admitting it shouldn't sit at the top level —
   half-measure.

## 3. Decision

Three items move from `keep` to `remove`. The fourth
(`auto_select_colors`) stays `keep` but is renamed (§3.1). The audit
framework stays 3-bucket; no new value.

| name | new classification | mechanical test (§2 of [prune spec](2026-05-05-prune-low-value-utils-design.md)) |
|---|---|---|
| `style_spines` | remove | with kwargs supplied, body is `for s in which: ax.spines[s].set_color(c); ax.spines[s].set_linewidth(w)` — pure default-fill |
| `add_grid` | remove | `ax.grid(...)` + `ax.set_axisbelow(True)` — 2 mpl lines |
| `minimal_axes` | remove | 7 LOC composition of two other removals + a 4-line spine-visibility loop — straightforward inline |

Function bodies for the three are deleted in Round 5. The curated
design information they encoded survives through docs recipes (§4).

### 3.1 `auto_select_colors` — keep, renamed to `make_palette`

The function survives. Its body is a curated palette **lookup** — the
algorithm is `base_colors[:n]` plus a highlight-index swap, but the
value is the four hard-coded color lists (categorical 8-color,
sequential blue at two cardinalities, diverging red-blue at two
cardinalities). Removing the function would force every caller to
inline 8-element color tuples; that pushes the curation cost onto
users who reasonably expect "give me 5 series colors" to be one call.

The current name is misaligned with library conventions:

1. The `auto_` prefix collides with `auto_layout` (where "auto" means
   measure-and-adjust); here it just means "use defaults".
2. `select_colors` is a strong action verb for what is structurally
   a slice of a constant list.
3. `colors` ignores the existing domain term `palette` already in use
   by `list_palettes` / `show_palette`.

Rename to **`make_palette`** in Round 5. Pairs with the existing
`make_offset` for the `make_` prefix; uses `palette` for vocabulary
consistency with the discovery functions.

Argument cleanup at rename time:

| old | new |
|---|---|
| `n_series` | `n` |
| `color_type` | `kind` |
| `highlight_index` | `highlight` |

Final signature: `dm.make_palette(n, kind="categorical", highlight=None)`.

The function body — including the four hard-coded palette lists and
the highlight-index swap pattern — stays as it is. The rename is
cosmetic; behavior is unchanged.

## 4. Preserving the design information for the removed three

Removal of the three default-kwarg wrappers is not erasure of their
design information. The kwarg recipes survive through two
non-function vehicles.

### 4.1 Grid / spine / minimal-axes recipes — rendered docs

These survive as **copy-pasteable snippets**, not Python:

- `docs/usage_guide/recipes.md` (new — Round 5) collects the curated
  kwarg combinations under named recipes. Initial entries:
  - **Publication grid** —
    `ax.grid(True, which="major", color="oc.gray3", alpha=0.3, linewidth=0.5); ax.set_axisbelow(True)`
  - **Minimal axes** — top/right hidden + light dashed y-grid +
    thin gray spines (5–6 line snippet)
  - **Thin gray spines** — 2–3 line snippet
- AI templates under `src/dartwork_mpl/asset/prompt/05-templates/` —
  audit each template for the canonical pattern; add the recipes
  inline where they are missing.

Docs and AI templates are the canonical home of design information
in this project (per `philosophy/ai_native.md`). Function form was
duplication.

### 4.2 Lint rule for `ax.grid()` without `set_axisbelow(True)` (optional)

`add_grid` always called `ax.set_axisbelow(True)` — a stylistic flag
that is easy to forget when writing `ax.grid(...)` directly.
Round 5 should:

1. Scan `docs/`, `tests/`, AI templates for bare `ax.grid(` calls
   without a following `set_axisbelow`. If the pattern is rare in
   the codebase already, the lint rule will mostly fire on legacy
   sites; if common, the rule is worth adding.
2. If kept, encode in `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`
   with severity `info` (style hint, not a correctness bug). Pairs
   the `ax.grid(` call with a fix suggestion of `+ ax.set_axisbelow(True)`.

Decision deferred to Round 5 — first scan, then decide.

## 5. Round plan (revised from earlier draft)

| round | scope |
|---|---|
| Round 4 (**this PR**) | spec + audit reclassification (3 items keep→remove; 1 keep + rename note). **No code change.** |
| Round 5 (next PR) | delete the three bodies, inline ~51 callsites (`style_spines:9 + add_grid:15 + minimal_axes:27`), rename `auto_select_colors` → `make_palette` with arg cleanup (~33 callsites updated), write `docs/usage_guide/recipes.md`, AI template sweep, update `migration.md` and `CHANGELOG.md` (`### Removed` for the three; `### Changed` for the rename) |
| Round 5b (optional) | `ax.grid` → `set_axisbelow` lint rule if §4.2 scan confirms value |

## 6. Out of scope

- Code removal and rename themselves (Round 5).
- Resolving remaining audit borderlines (`make_offset`, etc.) on the
  prune track (separate PR).
- General convention for adding new public functions in 0.5+ —
  belongs in a contributor doc, not a removal spec.

## 7. Why the earlier draft's namespace approach was wrong

Recorded for institutional memory: the rejected idea was to introduce
`dm.defaults.<name>` as a re-export namespace, keeping bodies but
moving the access path off top-level. Three reasons it failed the
review:

1. The naming difficulty was diagnostic, not cosmetic. `defaults`
   meant either "default values" (data) or "default behavior"
   (functions); neither read cleanly. `preset` collided with
   `dm.style.use("preset")`. `recipes` was too whimsical for an
   API namespace. When every candidate has a real defect, the
   abstraction itself is the defect.
2. It would have created a permanent two-tier namespace where
   the only rule was "anything under `dm.defaults` could have
   been raw matplotlib" — which also describes anything that's
   `remove`. The bucket would not have stable membership criteria
   across future audits.
3. The "callsite count is too high to remove" argument fails on
   the project's "no external users" assumption (per
   [#141 spec §3](2026-05-05-prune-low-value-utils-design.md#3-classification-3-bucket)).
   ~51 internal callsites is a 1-hour mechanical sweep, not a
   blocker.
