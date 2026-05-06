# `Length` Class — Color-Pattern Multi-Unit Wrapper

- **Date**: 2026-05-06
- **Issue**: [#152](https://github.com/dartworklabs/dartwork-mpl/issues/152)
- **Status**: Draft (awaiting maintainer review)

## 1. Context

The 0.4 cycle introduced `dartwork_mpl.units.Inches`, a `float`
subclass acting as a phantom-type marker for "this value is already
in inches". It exists to plug a unit-corruption hole in
`parse_width`: bare `int`/`float` are rejected so a user cannot
silently feed a cm-shaped number into matplotlib's inch-shaped
`figsize=`. See [`docs/migration.md`](../../migration.md) and
PR #147.

The marker works, but the design has three rough edges:

1. **Internal representation leaks into the type name.** `Color`'s
   canonical store is OKLab, yet the public class is named `Color`,
   not `OkLab`. `Inches` does the opposite — it tells callers what
   the storage format is rather than what the value *means*. A user
   writing `dm.col1 = cm(9)` thinks "9 cm", not "3.5433 inches".
2. **No multi-unit access.** `Color` exposes `.oklab / .oklch /
   .rgb` views so callers can read the same color in any space they
   want. `Inches` only exposes the inch view (because it *is* a
   float). To get cm back from `dm.col1` you have to multiply by
   `2.54` inline.
3. **Single matplotlib unit.** matplotlib also speaks **points**
   (font sizes, line widths). Inches-only is a coincidence of which
   API we hit first, not a principled scope.

This spec records the redesign that lands `Length` as a Color-pattern
wrapper, with the breaking rename treated as an in-flight 0.4 fix
(the deprecated `Inches` was added on the unreleased `[Unreleased]`
section of `CHANGELOG.md`, so external usage is effectively zero).

## 2. Decision

Replace `Inches(float)` with `Length`, a class whose **interface**
mirrors the `Color` design (multi-unit views, classmethod
constructors, str init parsing) while **structurally** remaining a
`float` subclass so matplotlib accepts tuples of `Length` directly
in `figsize=` (and similar APIs that internally call
`np.isfinite(...)` / `np.array(...) < 0` on the input). An earlier
draft of this spec proposed an opaque, non-`float` wrapper; that was
walked back during implementation when the cost of migrating ~30
existing `figsize=(dm.cm(W), dm.cm(H))` call sites in
`docs/`, `docs/examples_*/`, and the Sphinx gallery generators
turned out to dwarf the safety win. The cm/inch guard the original
`Inches` design exists to close lives at the **parser boundary**
(`Length(...)` and `parse_width`), not on every arithmetic op
against an already-typed value, so a `float`-shaped Length is
indistinguishable from an opaque one for the failure modes that
actually matter.

### 2.1 Canonical storage and unit views

- **Internal store**: inches — `Length` *is* the inch value via
  `float.__new__`. No separate `_inch` slot.
- **Unit views as properties**, not methods, because all four are
  pure dimensional facts independent of any rendering context:

  | View       | Definition                |
  |---         |---                        |
  | `.cm`      | inches × 2.54             |
  | `.mm`      | inches × 25.4             |
  | `.inch`    | inches (identity)         |
  | `.pt`      | inches × 72 (1 pt = 1/72 in) |

### 2.2 Out of scope: pixels

`px` is the only matplotlib unit that depends on a rendering context
(figure DPI). An earlier draft of this spec proposed
`length.px(dpi=, fig=)` plus a `fig=` binding at construction. We
discarded that surface because:

- It introduces a context-dependent method into an otherwise
  context-free wrapper, blurring the abstraction.
- The rare caller who needs a pixel count can write
  `length.inch * fig.dpi` — a one-liner that makes the dependency
  explicit at the call site instead of hiding it inside the class.
- Removing `px` collapses ~80 lines of internal helpers (`from_px`,
  `with_fig`, `_resolve_dpi`, `fig` slot/property) and leaves a
  uniform property-only surface.

If a real demand for `px` surfaces later, it can be added as a free
function (`dm.length_to_px(length, fig_or_dpi)`) without disturbing
the core class.

### 2.3 Constructors

```python
class Length:
    def __init__(self, value: str | Length): ...

    @classmethod
    def from_cm(cls, value: float) -> Length: ...
    @classmethod
    def from_mm(cls, value: float) -> Length: ...
    @classmethod
    def from_inch(cls, value: float) -> Length: ...
    @classmethod
    def from_pt(cls, value: float) -> Length: ...
```

- `Length("13cm")` parses the same unit-suffix grammar as
  `parse_width` (`cm | in | mm | pt`). Bare numeric strings default
  to cm, matching the existing parser.
- `Length(other_length)` is an idempotent copy.
- Bare `int`/`float`/`bool` is rejected with `TypeError` — the
  cm/inch guard the original `Inches` design existed to enforce.
- Classmethods take a positive number; `_validate_positive` raises
  `ValueError` on non-finite or non-positive values. This matches
  the existing `parse_width` contract.

### 2.4 Top-level wrapper functions

Mirrors the `Color` module's `oklab / oklch / rgb / hex / named`:

| Top-level     | Equivalent classmethod        | Existing? |
|---            |---                            |---        |
| `dm.cm(13)`   | `Length.from_cm(13)`          | ✓ (rebound to return `Length`) |
| `dm.inch(5)`  | `Length.from_inch(5)`         | ✓ (rebound) |
| `dm.mm(170)`  | `Length.from_mm(170)`         | ✓ (rebound) |
| `dm.pt(24)`   | `Length.from_pt(24)`          | new       |
| `dm.length("13cm")` | `Length("13cm")`        | new (parser, parallels `dm.hex`) |

`dm.col1` and `dm.col2` keep their values (9 cm and 17 cm) but are
re-typed from `Inches` to `Length` automatically — they're
constructed via `dm.cm(...)` which now returns `Length`.

### 2.5 Arithmetic contract

| Operation              | Result                  | Rationale                            |
|---                     |---                      |---                                   |
| `Length + Length`      | `Length`                | Sum of two physical lengths.         |
| `Length + scalar`      | `Length`                | Inherited from `float`; tag preserved via `__add__`. Strict "TypeError on scalar" was considered and rejected — see *Why scalar arithmetic is lax* below. |
| `Length - Length`      | `Length`                | Difference of two physical lengths.  |
| `Length - scalar`      | `Length`                | Same rationale as `+`.               |
| `Length * scalar`      | `Length`                | Scaling a length is still a length.  |
| `scalar * Length`      | `Length`                | Symmetric.                           |
| `Length / scalar`      | `Length`                | Division by dimensionless scalar.    |
| `Length / Length`      | `float`                 | Ratio is dimensionless.              |
| `-Length` / `abs(...)` | `Length`                | Sign manipulation preserves type.    |
| `Length * Length`      | `TypeError`             | `area = length × length` has no representation at this layer. |

Equality, ordering, and hashing inherit from `float` — equal
canonical inch values compare equal regardless of which constructor
produced them. This matches `Inches(float)`'s previous behaviour.

`__array_ufunc__ = None` opts `Length` out of numpy's universal-
function dispatch so that `np.float64(2) * cm(9)` falls back to
`Length.__rmul__` and the tag survives the round-trip. Without it,
arithmetic at numpy boundaries silently decays to a bare
`np.float64` and re-opens the cm/inch corruption hole at array
boundaries.

**Why scalar arithmetic is lax.** The earlier draft of this spec
made `Length + scalar` raise `TypeError` to "preserve unit safety".
Implementation surfaced two costs: (1) matplotlib internals do
`0 + width` to compute bbox extents, so strict rejection breaks
`plt.figure(figsize=(dm.cm(15), dm.cm(9)))` even with a `float`
subclass; (2) the `Inches(float)` predecessor was lax in this same
way, so the strictness would be a *new* burden, not a continuation.
The cm/inch guard sits at the parser boundary (`Length(...)` /
`parse_width`); arithmetic on already-typed values is safe by
construction.

### 2.6 `parse_width` contract change

```diff
- def parse_width(value: str | Inches) -> float:
+ def parse_width(value: str | Length) -> float:
```

The function still returns a plain `float` (inches) — its consumers
(`figsize`) need a number, not a `Length`. Internally it short-circuits
on `Length` (already-canonical) and parses unit strings via the same
shared `_parse_unit_string` helper used by `Length("...")`.

## 3. Compatibility policy

`Inches` was added to the `[Unreleased]` section of `CHANGELOG.md` —
it has never shipped on a tagged release. The package follows the
same hard-removal policy used for `dm.subplots` / `dm.figure`
(see PR #147): the symbol is gone, accessing `dm.Inches` raises
`AttributeError`, no `DeprecationWarning` grace period.

## 4. Out of scope

- Pixel conversion (`length.px`) — discussed in §2.2; deferred until
  a concrete caller demand surfaces.
- Length-aware setters for matplotlib font sizes / line widths.
  Those continue to go through `dm.fs / dm.fw / dm.lw` (style-aware
  offsets), not `Length`. `Length.pt` exists for callers who need
  the raw point value but does not register a new sizing channel.
- New lint rules. The existing `raw-width-number` rule still fires on
  bare-number widths; only the message text needs updating.

## 5. References

- Color class (the prototype this design copies): [`src/dartwork_mpl/color/_color.py`](../../../src/dartwork_mpl/color/_color.py)
- Inches definition (to be replaced): [`src/dartwork_mpl/units.py`](../../../src/dartwork_mpl/units.py)
- 0.4 width/aspect rationale: PR #147, [`docs/superpowers/plans/2026-04-29-pr1-core-width-aspect-lint.md`](../plans/2026-04-29-pr1-core-width-aspect-lint.md)
- API audit policy (hard removal, unreleased symbols): [`2026-05-05-prune-low-value-utils-design.md`](2026-05-05-prune-low-value-utils-design.md)
