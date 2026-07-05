# figsize_grid: per-panel physical sizing — Design (P8)

> Program umbrella #411, pillar EO8. Advisory/design by orchestrator; implementation by codex.

## Problem

`dm.figsize(width, aspect)` sizes the **whole figure**. For an N×M panel grid there is no way to
express "each panel should be 6 cm wide" — the user hand-computes the figure width. matplotlib
already provides the *composition* primitives (`subplots`, `subplot_mosaic`, `inset_axes`,
marginal axes), and dartwork's philosophy is "utilities not wrappers", so P8 does **not** wrap
those. It adds the one missing *sizing* utility: compute the figure size for a grid of panels at a
target per-panel physical width. (The mosaic / inset / marginal *patterns* belong in the P6
cookbook as ownable recipes, not new wrapper functions.)

## Design — `figsize_grid` (in `units.py`, alongside `figsize`)

```python
def figsize_grid(
    panel_width: str | Length,
    aspect: str | int | float = DEFAULT_ASPECT,
    *,
    ncols: int = 1,
    nrows: int = 1,
    gap: str | Length = "0.6cm",
) -> tuple[float, float]:
```
- `panel_width`: physical width of ONE panel (unit string or `Length`; bare int/float rejected,
  reusing `parse_width`'s validation/error — do not reimplement).
- `aspect`: height/width ratio per panel via `parse_aspect` (token like `"standard"` or a positive
  float). Not a Length (`parse_aspect` takes `str|int|float`).
- `gap`: **physical** separation between panels (unit string or `Length`) — unlike matplotlib's
  relative `wspace`/`hspace`, so the result is predictable.
- Returns the figure size in inches:
  `pw = parse_width(panel_width)`, `g = parse_width(gap)`, `panel_h = pw * parse_aspect(aspect)`,
  `fig_w = ncols*pw + (ncols-1)*g`, `fig_h = nrows*panel_h + (nrows-1)*g` → `(fig_w, fig_h)`.
- `ncols < 1` or `nrows < 1` → `ValueError`.

Because matplotlib then applies its own relative spacing, the per-panel width is exact only when the
user pairs it with `dm.simple_layout(fig)` (margin=0) or matching physical spacing — document this,
the same honesty `figsize` carries. Usage:
`fig, axs = plt.subplots(ncols=3, figsize=dm.figsize_grid("6cm","standard",ncols=3)); …; dm.simple_layout(fig)`.

## Scope
- `src/dartwork_mpl/units.py`: `figsize_grid`.
- `src/dartwork_mpl/__init__.py`: export in the `from .units import (...)` block + `__all__`.
- `tests/test_figsize_grid.py`: arithmetic assertions (width/height for ncols/nrows/gap; default gap;
  `ncols=0` ValueError; bare-float `panel_width` rejected; numeric-ratio aspect) — compute expected
  via `dm.cm`/`parse_width` so the test tracks the real unit conversion (`pytest.approx`).
- `docs/development/figsize-grid.md`: orphan MyST page (`---\norphan: true\n---`).

## Acceptance
- `dm.figsize_grid` public; new tests green; ruff + mypy clean; existing rendering unchanged; full
  suite green; docs `-W` clean.

## Non-goals
- No mosaic/inset/marginal wrapper functions (→ P6 cookbook recipes). No change to `figsize`.
