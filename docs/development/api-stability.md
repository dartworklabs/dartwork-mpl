---
orphan: true
---

# API stability

This page defines the public API contract for `dartwork_mpl` development.
It is intentionally orphaned for now; another docs session may own the
development toctree.

## Stable core

The stable core is every name in `dartwork_mpl.__all__` that is not listed
in `dartwork_mpl.EXPERIMENTAL`. Stable names are backwards-compatible within
a major version. Breaking changes to stable names must follow the
deprecation cycle below.

## Experimental surface

Names in `dartwork_mpl.EXPERIMENTAL` are provisional. Their shape may change
in a minor release without the full deprecation cycle.

The current set is `figsize_for` (the active preset's default canvas),
`grid_shape` (the layout of small multiples), `add_note` (a source line in
the preset's note style), `label_line_ends` (line names instead of a
legend), `review` (save, findings, figure summary and baseline diff),
`axis_unit` / `axis_unit_of` (the axis unit in its label), `label_bars`
(value labels on bars) and `figure_legend` (one legend for every panel):
their kinds, width tiers, density hints, layouts, the note's placement, the
labels' spacing and colour, the review summary's fields, the unit ladders,
label template and unit rules, the bar labels' placement, crowding and
stacked-total rules, and the figure legend's side rule and the panel
legends it removes may still change. The
interactive UI exists as the `dartwork_mpl.ui` subpackage, but it is not
currently an advertised top-level `dm.ui` attribute.

### Leaving the experimental surface

A name is taken out of `EXPERIMENTAL` when a release is cut, one name at a
time, and only if all three hold:

1. A published release already contains it. A name added since the last
   release waits for the next one.
2. Its signature and documented defaults are the same as in that release:
   the *Changed* section of `CHANGELOG.md` since that tag does not name it.
3. An agent smoke round (`evals/smoke/`) run since that release used it, and
   no defect from those rounds was filed against it.

The release's `CHANGELOG.md` entry lists each name that left. From then on
the name is stable core and changes through the deprecation cycle below.
Nothing leaves between releases, and a name that fails a condition stays
without a note.

## Deprecation cycle

To remove a public name, first announce the deprecation in `CHANGELOG.md`
and in the name's docstring, and have the name emit a `DeprecationWarning`
while it keeps working. Keep it that way for at least 2 minor releases
before moving it to `_REMOVED_NAMES`; the count starts at the minor that
first shipped the warning (a first warning in 0.8 allows removal in 0.10 at
the earliest). Removed names no longer resolve; accessing one raises
`AttributeError` with the version removed and a migration hint.

Where the warning comes from depends on the name. A function or class warns
at its definition (a wrapper), or through a module-level `__getattr__` on
the module that owns it. A name the package root imports from a submodule
and re-exports is already bound in the root, so the owning module's
`__getattr__` never runs for `dm.X`; the warning then fires at import time
only. Such a name needs a warning path on the root side.

## Registries

`__all__`
: Advertised public surface. Every function or class listed here must have
  a non-empty docstring.

`_REMOVED_NAMES`
: Hard-removed names. They raise `AttributeError` with a migration hint.

The root registry records only advertised and removed names. Deprecated is
a separate lifecycle state between the two: the name keeps working and warns
for at least two minor releases.

Deprecated today (first warning, earliest removal; replacements in
[migration.md](../migration.md)). Both first warned in 0.7.1, a patch
release: on 2026-11-14 the owner released the whole of `main` as 0.7.1
rather than 0.8. The earliest removal stays 0.10, the version planned when
the warnings were written:

| Name | First warning | Earliest removal | Use instead |
|---|---|---|---|
| module `dartwork_mpl.util` (warns per access) | 0.7.1 | 0.10 or later | the owner module of each name (table in migration.md) |
| `FontFamily.tnum`, `FontMeasurement.tnum`, `FontFaceMeasurement.tnum` | 0.7.1 | 0.10 | `.tnum_available` (same value) |

### Removing a name

`src/dartwork_mpl/_compat.py` is the only place removed-name metadata is
edited. A removed name goes into three tables there:

- `_REMOVED_NAMES`: the release that removed it and its replacement, which
  `dm.<name>` reports in its `AttributeError`;
- `_CODEMOD_HINTS`: the `# TODO(dm-migrate):` comment that
  `dm.migrate_legacy_code` writes above a use of it;
- `_LINT_RULES`: the anti-pattern rule that `dm.lint_code` reports it under.

Then run `uv run python scripts/generate_removed_name_rules.py`, which
writes `_LINT_RULES` into `asset/prompt/02-anti-patterns.yaml`; do not edit
those rules in the YAML. The catalog is part of `llms-full.txt`, so
regenerate that too: `generate_llms_full_txt(app, write=True)` in
`docs/_ext/build_hooks.py`. `tests/contracts/test_deprecation_registry_parity.py`
fails until every consumer reports the new name and the catalog matches the
registry. `tests/contracts/test_removed_names_golden.py` pins the published
wording of the names removed so far against a record of the earlier output;
a wording change there is a separate decision.

## Adding a public name

Add the name to `__all__`, make sure the object is importable as
`dartwork_mpl.<name>`, and give every public function or class a docstring.
If the surface is provisional, add the name to `EXPERIMENTAL` and document
what may still change.
