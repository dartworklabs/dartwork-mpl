---
orphan: true
---

# Annotation helpers reject keywords they cannot honour (#483, task 2)

Status: implemented on `t3/annotation-kwarg-guard-20261107`.
Policy: confirmed as a project rule by the user on 2026-11-07
(2026-11-07 사용자 승인). Before this change it applied to `label_axes` only.

## Behaviour change

A keyword that had no effect, or that collided inside matplotlib with a
message naming neither the helper nor the fix, now raises a named error
before any artist exists. In one line: **from a silently ignored (or opaquely
colliding) kwarg to an explicit error.** A call that was valid draws exactly
what it drew before.

## The two rules

1. **The helper sets the property itself → `TypeError`.** The caller's value
   would collide inside the matplotlib call (`got multiple values`, `Got both
   'fontsize' and 'size'`) or be overwritten without a word. The message
   names the helper, the keyword and the argument that does the job.
2. **The artist has no such property → `AttributeError`,** the kind a bare
   matplotlib property error already raised. Names go through
   `cbook.normalize_kwargs` first (so `c`, `size`, `ha` resolve), and the
   matplotlib call's own arguments pass: `fontdict` for `Axes.text` /
   `Figure.text`; `xytext`, `xycoords`, `textcoords`, `arrowprops`,
   `annotation_clip` for `Axes.annotate`. Those lists are read from the
   signatures, not typed, so they follow the installed matplotlib.

Both rules live once, in `src/dartwork_mpl/annotation/_kwarg_guard.py`
(`call_parameters`, `kwarg_is_accepted`, `reject_unusable_kwargs`, and
`KwargGuard`, which carries one helper's wording). `label_axes` keeps its
own message text unchanged and calls `reject_unusable_kwargs` directly.

## Owned properties, helper by helper

Line numbers are on this branch. "Owned" is what the guard rejects with
`TypeError`; everything here was checked by calling the helper on
`origin/main` (`ab3e3347`, matplotlib 3.11.2) and reading the result.

### `annotate_value` — `annotation/_point_labels.py`

| Keyword | Why it cannot take effect | Where the helper sets it |
|---|---|---|
| `xy`, `xycoords` | passed explicitly → `got multiple values` | `:316-317` |
| `xytext`, `textcoords` | passed explicitly → `got multiple values` | `:318-319` |
| `transform` | `Axes.annotate` replaces it with `IdentityTransform` (matplotlib `axes/_axes.py:739`); placement is `xycoords`/`textcoords` | `:317`, `:319` |
| `size` | alias of `fontsize`, which the helper passes → `Got both` | `:322` |
| `horizontalalignment`, `verticalalignment` | the helper passes `ha=`/`va=`, which win; the long spelling was dropped silently | `:320-321` |
| `ha`, `va` (only `side="auto"`) | overwritten for every side tried | `_apply_annotation_side` `:248`, called `:346`, `:360`, `:372` |

`ha`/`va` with an explicit `side=` stay the caller's (`kw.pop("ha", ha)`,
`:320-321`). `x`, `y`, `text` are parameters, so Python rejects a duplicate.

### `annotate_corner` — `annotation/_point_labels.py`

| Keyword | Why | Where |
|---|---|---|
| `xy`, `xycoords`, `xytext`, `textcoords` | `got multiple values` | `:453-459` |
| `transform` | replaced by `IdentityTransform` | `:454`, `:459` |
| `x`, `y` | `Annotation` passes the text offset as `Text.__init__(x, y, ...)` → `got multiple values` | `:455-458` (`xytext`) |
| `size` | `Got both` with `fontsize` | `:462` |
| `horizontalalignment`, `verticalalignment` | dropped in favour of `ha=`/`va=` | `:460-461` |
| `ha`, `va` (only `avoid_overlap=True`, the default) | overwritten for every corner tried | `_apply_corner` `:404`, called `:485`, `:499` |

`loc` is the helper's own parameter (the corner), not a rejected keyword.

### `label_hline` — `annotation/_point_labels.py`

| Keyword | Why | Where |
|---|---|---|
| `xy`, `xycoords`, `xytext`, `textcoords` | `got multiple values` | `:617-620` |
| `transform` | replaced by `IdentityTransform` | `:618`, `:620` |
| `size` | `Got both` with `fontsize` | `:623` |
| `horizontalalignment`, `verticalalignment` | dropped in favour of `ha=`/`va=` | `:621-622` |
| `ha` (only `x="auto"`) | overwritten for each end tried | `:645`, `:660` |

`va` is the caller's in every mode. `x`, `y` are parameters.

### `label_line_ends` — `annotation/_line_end_labels.py`

| Keyword | Why | Where |
|---|---|---|
| `xy`, `xycoords`, `xytext`, `textcoords` | `got multiple values` | `:142-145` |
| `transform` | replaced by `IdentityTransform` | `:143`, `:145` |
| `x`, `y` | `Text.__init__` duplicate, as above | `:144` (`xytext`) |
| `horizontalalignment`, `verticalalignment` | the style dict's `ha`/`va` win | `:135-136` |

`color`, `c`, `ha`, `va`, `annotation_clip`, `size`/`fontsize` are the
caller's: the style dict is updated with `kw` (`:139`) and sets no font size.

### `add_note` — `annotation/_figure_text.py`

| Keyword | Why | Where |
|---|---|---|
| `x`, `y` | `fig.text(0.0, 0.0, ...)` → `got multiple values` | `:68` |
| `size` | `Got both` with the style's `fontsize` | `:66` |
| `horizontalalignment`, `verticalalignment` | the style's `ha`/`va` win | `:66` |

`transform`, `fontdict` and `position` take effect and stay allowed; the
message for `x`/`y` points at `position=(x, y)`.

### `label_axes` — `annotation/_panel_labels.py` (unchanged rule)

`ha`, `va`, their long spellings and `transform`, set at `:224-228` and
`:245-246`. Only the probe moved to `_kwarg_guard.py`.

## Hints for the names agents reach for

Each helper maps a few `AttributeError` names to the route that works:
`fmt` → pass the finished text (`label_line_ends`: set the line's
`label=`); `loc` → `side=` / `x=` / `position=` as the helper has them;
`offset`, `gap`, `inset` → the `*_pt=` argument; `fontdict` on the
`annotate` helpers → pass the properties directly (`Axes.annotate` has no
`fontdict`). Every message ends with the plain matplotlib call to write
instead.

## Not applied

- `place_legend`, `optimize_legend`: their keywords go to `Legend`, not a
  `Text`; the probe does not fit.
- `label_bars`: takes no `**kwargs` (every option is a named parameter, `fmt`
  among them), so nothing reaches a `Text` unchecked.
- `arrow_axis`, `wrap_axis_label`, `wrap_axis_labels`: no `**kwargs`
  (`arrow_axis` takes `arrow_kw`, an `arrowprops` dict).

## Known gaps, not changed here

- `position=` on `annotate_value(side="auto")`, `annotate_corner` with
  `avoid_overlap=True` and `label_line_ends` with two or more lines is
  overwritten (measured), but honoured in the other modes; it is left
  allowed rather than given a third mode-dependent rule.
- When the helper's measuring step cannot get an extent (`BBOX_ERRORS`) it
  returns early and a caller's `ha`/`va` would have survived in auto mode;
  the guard rejects them anyway.
- `add_note(..., s=...)` raised a `TypeError` from `fig.text`; it now raises
  the guard's `AttributeError` naming `text` as the route.

## Evidence

- `src/dartwork_mpl/annotation/tests/test_annotation_kwarg_guard.py`: per
  helper, the owned `TypeError` with the fix in the message, the
  `AttributeError` for unknown names, and ordinary `Text` properties
  (`color`, `rotation`, `fontstyle`, `alpha`) plus `arrowprops` /
  `annotation_clip` reaching the artist.
- Eight valid calls (ten labels) across all five helpers, drawn and laid out with
  `simple_layout` on `origin/main` and on this branch: every label's text,
  position, anchor, alignment, colour, size, weight, rotation and window
  extent, and the saved PNG's SHA-256, are identical.
