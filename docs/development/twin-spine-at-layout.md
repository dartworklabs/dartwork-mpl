---
orphan: true
---

# Twin right spine at the layout, not at import (D7)

Status: implemented on `t3/twinx-explicit-20261106`, first shipped in 0.8.
Decision: root API decision D7 (2026-11-06). Not a release blocker.
Approved by the user on 2026-11-07, including the look changes 11-1 to 11-5
listed below (2026-11-07 사용자 승인). Revised the same day after the
independent review: inset twins, the tick condition, one line per place, an
independent 0.7 oracle and the full import contract.

## What import used to do

`import dartwork_mpl` called `style.install_twinx_patch()`, which replaced
`matplotlib.axes.Axes.twinx` with a wrapper running two lines on the
returned Axes: `spines["right"].set_visible(True)` (the presets hide the
right spine, so the second scale had no axis line) and
`set_linewidth(rcParams["axes.linewidth"])` (a no-op: a spine is made with
that width). `twiny`, the parent, colours and backgrounds were not touched.
Twin colours, bar label host, `place_legend` and outside anchors group Axes
by position and shared axes, not by this patch; the layout does not measure
spines. `PRESET_OVERRIDE` skips native twins via the private `_twinned_axes`,
as before D7.

## Decision

Import rebinds no matplotlib class or function; it still registers the
bundled colours, colormaps and fonts. No `dm.twin` wrapper. `dm.simple_layout`
shows the spine (`formatting/_twin_spines.py` holds the one statement).

**When.** Inside `simple_layout`, after every check that can refuse the call
and after the default tick formats, with the twin colours (their order does
not change the figure: the colours paint a spine whether it shows or not).
`format_ticks=False` does not skip it. A refused call changes nothing.

**What.** `spines["right"].set_visible(True)`; width, colour, position and
bounds stay.

**Which Axes.** One that draws its own y scale on the right of a shared plot
area, read from public state only:

1. *Box*: drawn in the same box as another visible rectilinear Axes of its
   figure (`get_position()` within 1e-9; `same_position_axes`, unchanged).
   The spine step walks inset Axes too (`with_insets`: figure order, each
   Axes followed by its insets, depth first): an inset is not in `fig.axes`
   but its `twinx` is, so the inset finds its twin. The twin colours and the
   other consumers keep their own walk over `fig.axes`, so inset pairs still
   get no series colours.
2. *Shared axes*: it shares x with a member and not y (public groupers).
3. *Scale on the right*: its y axis is visible, its y label sits on the
   right and its y ticks too: tick labels shown on the right and not on the
   left (`tick_params(right=False)` keeps a scale of labels); an axis with
   no tick labels is read by its tick marks. `twinx()` leaves all three.
4. *One line per place*: when several such Axes would draw a right spine in
   the same place (`spine.get_position()`), only the last drawn (zorder,
   then figure order) shows it.

**Once.** An Axes whose line the layout showed (or found showing) is
recorded and not touched again, so a spine hidden after a layout stays
hidden.

## Controls and differences (laid out, scientific)

| Case (review id) | Spine shown in 0.8 | 0.7 |
|---|---|---|
| side-by-side panels, also with shared x and the right panel moved right | no | no |
| two Axes in one box, also moved right (no shared axis) | no | no |
| `sharex` + `sharey` overlay moved right | no | no |
| `sharex` overlay; with only its label moved right (x20) | no | no |
| `twinx()`; with its tick marks off | twin | twin |
| `twinx()` with the parent's label moved right (x01) | twin | twin |
| `twinx()` with the parent moved right too (x22) | twin (one per place) | twin |
| `twiny()` | no | no |
| three y axes, offset third spine | both twins | both twins |
| inset `twinx()` (x23) | twin | twin |
| 11-3 `sharex` overlay, ticks and label moved right (x12) | overlay | no |
| 11-4 twin's ticks and label moved left; parent moved right (x19) or not (x13) | parent (x19), none (x13) | twin |
| 11-5 twin with its y axis hidden (x14) | no | twin |
| x02 twin with its ticks moved left | no | twin |
| x03 twin with its label moved left | no | twin |
| x04 `b.twinx()` of a twin (matplotlib moves `b`'s ticks left) | `b`: no | `b`: yes |

Rows 1-10 match 0.7 pixel for pixel. 11-3 to 11-5 are approved. x02-x04 are
not approved and cannot be matched from public state: a `sharex` overlay
whose x axis and background are hidden, with the same half-moved scale, has
the same public state as the twin (only the private `_twinned_axes` differs),
and 0.7 drew no line on it. Any public rule gives both the same answer, so
one side of that pair changes. The current rule (ticks and label) changes
the twin side (x02-x04); "either one" for Axes with a hidden x axis would
change the overlay side instead. That narrow choice is open (PoC in the
report).

## Explicit settings and neutral mode

- `dm.config.twin_colors = "neutral"` only stops the colours.
- Width, colour, position (`("axes", 1.15)`, `"outward"`), tick and label
  colours, frame off, parent spines: untouched (asserted, width 1.2 kept).
- Hidden after a layout: stays hidden.
- **11-2, hidden between `twinx()` and the first layout: shows.** Under the
  presets the spine is hidden already, so `set_visible(False)` leaves no
  public trace; only an import-time hook saw the creation. Hide it after
  `dm.simple_layout`, or give it `linewidth=0` (the "no border" form). The
  twin colours have the same documented limit for a default-equal colour.

## 11-1: users who never call `simple_layout`

`tight_layout`, constrained layout, `fig.add_axes` figures (refused by
`simple_layout`), `simple_layout(subfig)` (refused before any change) and
bare `savefig` keep the preset's hidden right spine on a twin: ticks and
labels stay, the axis line does not. That already held for the twin colours,
tick formats and bar label settling. Without the layout:
`ax2.spines["right"].set_visible(True)`.

## PRESET_OVERRIDE

The check is unchanged and still skips native twins. A line the layout shows
on an Axes that is not a native twin is reported as INFO: the overlay in
11-3 (`axes 1, spines.right`) and the parent in 11-4 (`axes 0,
spines.right`). It is the layout's line, not an override to undo.

## Verification (mechanical, in this repository)

- `tests/contracts/test_init_patch.py`: a fresh interpreter imports and
  reloads the package twice; every attribute of nine classes (`Axes`,
  `Figure`, `SubFigure`, `XAxis`, `YAxis`, `Spine`, `Text`, `Line2D`,
  `Legend`) looked up statically over `dir()`, every MRO class namespace and
  every class and callable of the imported matplotlib modules stay the same
  objects.
- `formatting/tests/test_twin_spines.py`: 51 cases (14 builds, each also
  neutral and `format_ticks=False`, three presets, five edits) must equal
  `twin_spines_07_golden.json`, recorded from origin/main (no D7 code) with
  0.7's wrapper, and the pixels of a live 0.7 re-enactment with the new step
  off. 11-1 to 11-5 and x02-x04 are pinned against the live 0.7 run.
- Mutants that survived the review (width overwrite, no box condition, no
  "not y" condition, no "x shared" condition, step inside `format_ticks`,
  inherited rebinding on `Artist` and `FigureBase`) now fail. Moving the step
  after the colours is equivalent and is not a target.
- PoC (outside the repository): the 21 approved renders are pixel-identical.

## Shipping (0.8) and wording

CHANGELOG, *Changed*:

> **Importing dartwork-mpl no longer rebinds any matplotlib class or
> function.** `ax.twinx()` is matplotlib's own again (0.7 replaced it at
> import); import still registers the bundled colours, colormaps and fonts.
> `dm.simple_layout` shows the right spine, which the presets hide, of an
> Axes drawing its own y scale on the right of a shared plot area, y ticks
> and y label on the right (the Axes `twinx()` returns, of an inset too).
> Figures laid out with `dm.simple_layout` look as in 0.7, except: a
> `sharex` overlay whose y ticks and label you moved to the right gets that
> line; when a twin and its parent swap sides, the line moves to the parent;
> a twin whose y axis is hidden, or whose y ticks or label you moved to the
> left (also `b.twinx()` of a twin, which moves `b`'s ticks), gets none.
> Without the layout a twin keeps the hidden spine; show it with
> `ax2.spines["right"].set_visible(True)`. A right spine you hide before the
> first `dm.simple_layout` now shows; hide it after the layout, or give it
> `linewidth=0`. `dm.validate_figure` reports the line on a moved overlay or
> a swapped parent as `PRESET_OVERRIDE` (INFO); it is the layout's.

CHANGELOG, *Removed*: `dartwork_mpl.style.install_twinx_patch` and its root
alias (internal, never in `__all__`).

## Open points (not decided here)

- x02-x04 (above): which side of the indistinguishable pair changes.
- `twiny` top spine: still hidden, as in 0.7; showing it needs its own PoC.
- `PRESET_OVERRIDE` still uses `_twinned_axes`; aligning it with the public
  rule would change root's pinned shared-axes contract test.
