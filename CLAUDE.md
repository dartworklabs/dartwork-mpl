# dartwork-mpl — contributor entry point

You are working **on** dartwork-mpl, a matplotlib design system. This file is
for AI coding assistants changing this repository. The same content is
mirrored in [`AGENTS.md`](AGENTS.md).

## The one criterion

A user turns on the skill, says "draw this", and a beautiful chart comes
out. Code, tools, docs and tests exist only as far as
they serve that. What does not is removed.

## Read the Handbook first

Before changing code, read only the topics you need from
[`docs/handbook/index.md`](docs/handbook/index.md). It owns the purpose, the
structure and its rules, the invariants, the verification gates and who
decides what. When your change alters current state, update the matching
Handbook topic in the same PR.

[`docs/handbook/philosophy.md`](docs/handbook/philosophy.md) is the short version of
how to work here: only real functionality lives in this repository (examples
and galleries belong to the hub), code speaks in types (no strings, enums or
status flags picking behaviour, nothing that silences the type checker),
slices do not import each other, and a commit holds one finished thing.

## What is here

A thin layer on top of matplotlib: `Figure` and `Axes` stay native. The
package is eleven small slices under `src/dartwork_mpl/`:

`style` `size` `color` `font` `layout` `ticks` `labels` `legend` `check`
`save` `guide`

Each slice keeps the same files: `model.py` (domain types and the one place
strings are parsed), `decide.py` (pure decisions, domain types only),
`edges.py` (named edge cases appended to `EDGES` or `<NAME>_EDGES`),
`measure.py` / `apply.py` (thin matplotlib shell), modules named after a
concept when one of those grows, `assets/` (its own data files), `tests/`.

A slice imports no other slice. What two or more slices share lives in a
platform package (`vocab` holds the small shared vocabularies, one module
each; `length`, `colorspace`, `edgecase` are pure too; `geometry` measures
figures).
Where one slice needs another, `compose/<slice>.py` joins them with no
decisions, and only the package root imports it: `dm.simple_layout`,
`dm.figsize_for` and the label functions are composed there, and the role
colours are joined into `dm.style`. `tests/architecture/` enforces all of this.

## Plotting rules live in the bundled skill

Before writing or reviewing plotting code here (skill pages, tests),
read [`src/dartwork_mpl/guide/assets/skill/SKILL.md`](src/dartwork_mpl/guide/assets/skill/SKILL.md)
and the `references/` file it routes to. It is the single source of the
consumer rules: preset by purpose, `dm.figsize`, `dm.simple_layout` (never
`plt.tight_layout()`), `dm.save_formats`, `dm.fs` / `dm.lw` / `dm.fw`, colour
names, and the draw → `dm.check` → fix loop. Change a consumer rule there
first. `uv run dartwork-mpl install` links the skill into a project.

The anti-pattern catalog is
[`src/dartwork_mpl/guide/assets/anti-patterns.yaml`](src/dartwork_mpl/guide/assets/anti-patterns.yaml);
`dm.lint_code(code)` runs it.

## What is held

- **Shipped colour values.** `tests/test_shipped_colors_hash.py` pins them.
  Never regenerate its digests to make a failing test pass: a failure means a
  shipped colour moved, which is the owner's decision.
- **The rendered look.** Fonts, weights, spines, grids and preset looks do not
  change outside a fix whose before/after the owner has seen.
  `tests/visual` holds the pixel baselines (`--mpl`, RMS ≤ 0.5).

Everything else — public names, import paths, wire shapes, old tests — may
change or be deleted when it does not serve the one criterion. Do not add
shims, aliases or compatibility layers.

## Checks

```bash
uv run ruff check && uv run ruff format --check
uv run basedpyright
uv run pytest -q -n auto --mpl
```

Tests are small on purpose: pure `decide` tables, one test per named edge
case, a few realistic charts through the public surface. Do not add tests
that pin implementation details, bytes, prose or tooling.

Every code block in the skill must run
(`src/dartwork_mpl/guide/tests/test_guidance.py`).

## Design documents and agent work

1. **A design document does not exceed 200 lines.** Longer means the work
   needs splitting.
2. **Land a mechanical check before review.** A pinned digest, a golden file,
   a measured threshold. Review against it, not against opinions.
3. **A lock is released by its own ADR**, not by a clause in another document.
   The owner's decisions come first and are recorded that way.
4. **Completion criteria must run in this repository's development
   environment.**
5. **A check that did not run is reported as NOTRUN, never as passed.**

Branches: `develop` and `main` are protected; work on a branch and open a PR
to `develop`. `main` only receives merges from `develop`.
