:orphan:

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

The current set is empty. The interactive UI exists as the
`dartwork_mpl.ui` subpackage, but it is not currently an advertised
top-level `dm.ui` attribute.

## Deprecation cycle

To remove a public name, first move it out of `__all__` and add it to
`_DEPRECATED_NAMES`. Deprecated names keep working, emit a
`DeprecationWarning`, and alias to the replacement target.

Keep a name in `_DEPRECATED_NAMES` for at least 2 minor releases before
moving it to `_REMOVED_NAMES`. Removed names no longer resolve; accessing
one raises `AttributeError` with the version removed and a migration hint.

## Registries

`__all__`
: Advertised public surface. Every function or class listed here must have
  a non-empty docstring.

`_DEPRECATED_NAMES`
: Soft-deprecated names. They are not advertised, still work, emit
  `DeprecationWarning`, and point to their replacement.

`_REMOVED_NAMES`
: Hard-removed names. They raise `AttributeError` with a migration hint.

A name lives in exactly one of these states: advertised, deprecated, or
removed.

## Adding a public name

Add the name to `__all__`, make sure the object is importable as
`dartwork_mpl.<name>`, and give every public function or class a docstring.
If the surface is provisional, add the name to `EXPERIMENTAL` and document
what may still change.
