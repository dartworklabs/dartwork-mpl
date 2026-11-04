# Agent follow-up: three delegated decisions

Base: main `a691e285`. The user delegated all three open decisions in
[the follow-up handoff](../../development/structure-refactor/agent-followup-handoff.md)
to this session ("너가 철저히 진단해서 결정해봐", 2026-11-04). This file records the
diagnosis, the decision and its bounds. It approves nothing beyond the three items.

Peer check: both live sessions reported no dartwork-mpl work. The worktree
`t3-0c3dff26` holds unmerged MCP/viewer commits, so MCP paths stay untouched here.

## Measured current behaviour

`label_axes` kwargs, probed on `a691e285` (one figure per case, both the
`ax.text` and title/`ax.annotate` paths):

| Kwarg class | Example | Today |
| --- | --- | --- |
| Not a `Text` property | `fmt`, `loc` | `AttributeError: 'Text' object has no property 'fmt'` |
| Annotate-only name | `xy` | same `AttributeError` (`ax.text` runs first) |
| Alias of a name `label_axes` passes | `ha`, `va`, `transform` | `TypeError: ...Axes.text() got multiple values for keyword argument 'ha'` |
| Full name of that alias | `horizontalalignment`, `verticalalignment` | **accepted, then silently dropped** — the internal `ha="left"`/`va="bottom"` wins |
| Alias of a dedicated parameter | `size`, `weight` | `TypeError: Got both 'fontsize' and 'size', which are aliases of one another` |
| `Axes.text` argument, not a `Text` setter | `fontdict` | accepted on the `ax.text` path; already `AttributeError: 'Annotation' object has no property 'fontdict'` when a title moves the label |
| Other `Text` properties | `color`, `c`, `rotation`, `fontstyle` | accepted, take effect, as documented |

No partial labels are left on any Axes when a call raises. Not an atomicity defect.

`make_palette(n, highlight=…)` on `a691e285`:

| highlight | Result |
| --- | --- |
| `1`, `1.0`, `True`, `np.int64(1)`, `np.float64(1.0)` | correct, identical to `highlight=1` |
| `9` (out of range) | ignored — the documented behaviour |
| `1.5`, `0.5`, `np.float64(1.5)` | **every series receded, none emphasised** (`blue3, red3, green3, orange3`) |

The fractional in-range case is neither the baseline nor a highlight: it silently
returns a plausible-looking wrong palette.

Branch protection on `main` requires the status context
`Run pre-commit on changed files` (app_id 15368) — the literal job display name.

## Decision 1 — #483 task 2: diagnose, keep exception types

Pre-flight the kwargs and raise before any Artist is built, with a message naming
`label_axes`, the offending argument, the dedicated parameters
(`labels`, `x`, `y`, `fontsize`, `fontweight`) and the native `ax.text` escape.

Exception types stay as measured: `AttributeError` for a name `Text` does not
accept, `TypeError` for a name `label_axes` itself passes. #483 records that
changing exception kind/priority is unapproved, and `except AttributeError`
callers must keep working.

One behaviour does change on purpose. `horizontalalignment`/`verticalalignment`
are accepted today and then dropped, so an explicit styling request produces a
figure that ignores it with nothing reported — the silent-wrong-result the task
exists to remove. They join the rejected set and raise the same `TypeError`,
which points at `ax.text` rather than at a spelling that does not work either.

Everything that takes effect today keeps taking effect: `color`, `c`,
`rotation`, `fontstyle` and the rest of the `Text` surface, plus the dedicated
`fontsize`/`fontweight`. The `size`/`weight` alias clash keeps matplotlib's own
message. No new positioning wrapper, no newly accepted keyword.

The accepted set is read from `Text`'s setters through matplotlib's own alias
table *and* from `Axes.text`'s own signature, because an argument like
`fontdict` is accepted by the call without being a `Text` setter. A review of
the first implementation caught exactly that regression; deriving both sides
keeps the check from drifting as matplotlib changes. `fontdict` reaching
`ax.text` but not `ax.annotate` is pre-existing and left as measured, since
making the title path honour it would change a rendered label.

## Decision 2 — D3: keep the pre-commit job name

Keep `Run pre-commit on changed files` and close D3's remaining cleanup. Renaming
buys a display string and requires a coordinated branch-protection context update;
if the two do not land together the required check never reports and every PR
blocks. The colour-check triplet was already found non-redundant (#545).
Recorded as decided, not as unverified.

## Decision 3 — #501: fractional highlight only

Reject a non-integral `highlight` that would enter the highlighting branch, with a
`ValueError` in the style of the existing `n must be non-negative` guard.

Out of scope and still unapproved, deliberately:

- Out-of-range `highlight` keeps being ignored, including `9.5`. Only inputs that
  produce a wrong figure today change, per task 8's own narrowing rule.
- Invalid recommender selection → `ToolError`: MCP definitions and envelopes are
  frozen (#523) and `t3-0c3dff26` holds unmerged MCP work.
- object/`None`, N-D and complex policies: need their own design and approval, as
  the merged [data-policy plan](2026-11-04-explicit-data-policy.md) stated.

## Invariants

Inputs are never mutated. Integral `highlight` of any numeric type keeps its exact
result. Colour values, shipped digests, fonts, styles, preset looks, MCP
definitions and wire envelopes do not change. Figures keep native
`Figure`/`Axes`, `dm.style.use(...)`, `dm.figsize(...)`, `dm.simple_layout(fig)`
and `dm.fs`/`dm.lw`/`dm.fw`.

Never read, search, hash or copy `docs/superpowers/specs/2026-10-20-agent-contract-repairs-design.md`
or its copies; no broad docs scan that would reach it.

## Tasks

### Task 1 — palette highlight

Files: `_colors/_palette.py`, `_colors/tests/test_make_palette.py`.

- [ ] Step 1: red tests — in-range fractional rejected; `1`/`1.0`/`True`/numpy
      integral unchanged; `9` and `9.5` still ignored; existing `highlight="1"`
      `TypeError` retained.
      `test_boundary_and_highlight_contract` pins the defect as a native quirk
      (`(3, "categorical", 0.5, ["oc.blue3", "oc.red3", "oc.green3"])`). That row
      guarded the mechanical move, not the outcome; this decision replaces it with
      the rejection on purpose. The other pinned rows, including ignored `-1`, stay.
- [ ] Step 2: minimal guard inside the highlighting branch; update the docstring.
- [ ] Step 3: run the colours suite plus the shipped-colour freeze.

### Task 2 — label_axes diagnostics

Files: `annotation/__init__.py`, `annotation/tests/test_label_axes_diagnostics.py`.

- [ ] Step 1: red tests — message content and exception type per kwarg class,
      and the accepted kwargs that must not regress.
- [ ] Step 2: pre-flight check; keep the placement logic untouched.
- [ ] Step 3: run annotation, `tests/contracts/test_util.py`,
      `tests/test_agent_docs_runtime.py`, Ruff and mypy.

### Task 3 — status reconciliation and merge

Files: handoff, structure-refactor README, `CHANGELOG.md`, this plan.

- [ ] Step 1: record #566–#569, the verified branch-protection context, the three
      decisions and the identified receiving sessions. Do not close #483 or #501.
- [ ] Step 2: run the affected checks on the final head; open the PR and require
      its own checks. Error-text changes only, so no render PoC is owed.
