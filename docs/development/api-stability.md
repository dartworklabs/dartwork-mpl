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
`axis_unit` / `axis_unit_of` (the axis unit in its label) and `label_bars`
(value labels on bars): their kinds, width tiers, density hints, layouts,
the note's placement, the labels' spacing and colour, the review summary's
fields, the unit ladders, label template and unit rules, and the bar
labels' placement, crowding and stacked-total rules may still change. The
interactive UI exists as the `dartwork_mpl.ui` subpackage, but it is not
currently an advertised top-level `dm.ui` attribute.

## Deprecation cycle

To remove a public name, first announce the deprecation in `CHANGELOG.md`
and in the name's docstring, and have the name emit a `DeprecationWarning`
at its definition (a function wrapper, a module-level `__getattr__` on the
owning module) while it keeps working. Keep it that way for at least 2
minor releases before moving it to `_REMOVED_NAMES`. Removed names no
longer resolve; accessing one raises `AttributeError` with the version
removed and a migration hint. The package root has no deprecated-name
registry: none is in use, so add one only together with the first name that
needs it.

## Registries

`__all__`
: Advertised public surface. Every function or class listed here must have
  a non-empty docstring.

`_REMOVED_NAMES`
: Hard-removed names. They raise `AttributeError` with a migration hint.

A name lives in exactly one of these states: advertised or removed.

## Adding a public name

Add the name to `__all__`, make sure the object is importable as
`dartwork_mpl.<name>`, and give every public function or class a docstring.
If the surface is provisional, add the name to `EXPERIMENTAL` and document
what may still change.
