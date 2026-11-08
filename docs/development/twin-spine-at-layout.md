---
orphan: true
---

# Twin scale line at the layout, not at import (D7)

Status: implemented on `t3/twinx-explicit-20261106`, first shipped in 0.8.
Decision: root API decision D7 (2026-11-06). Not a release blocker.
Approved by the user on 2026-11-07, including the look changes 11-1 to 11-5
listed below (2026-11-07 사용자 승인). Revised the same day after the
independent review: inset twins, the tick condition, the twin's line first,
an independent 0.7 oracle and the full import contract. 2026-11-07 사용자
결정 14: 대안 (the counterexample pair below: twins keep 0.7's line, an
overlay drawn like a twin gains one). Re-review the same day: the twin's
line first no longer depends on the spine's place (n11). 2026-11-08 사용자
승인 1-A: a `twiny` member's top spine follows the same rule (I3).

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

**What.** `spines["right"].set_visible(True)`, or `spines["top"]` (item 5);
width, colour, position and bounds stay.

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
3. *Scale on the right*: its y axis is visible and its scale sits on the
   right. An Axes whose x axis shows needs its y ticks and its y label there;
   one whose x axis is hidden shows nothing but its y scale (`twinx()` hides
   the twin's), so its y ticks or its y label there is enough (decision 14).
   Ticks are on the right when the tick labels show there and not on the
   left (`tick_params(right=False)` keeps a scale of labels); an axis with no
   tick labels is read by its tick marks.
4. *The twin's line first*: when an Axes with a hidden x axis draws its
   right spine in a box, no Axes whose x axis shows draws one there,
   wherever its spine sits (a parent moved right, even to `("outward", 30)`,
   keeps the preset's look). Twins of one parent all keep theirs.
5. *The top (1-A)*: items 1 to 4 with x and y swapped, for an Axes drawing
   its own x scale on the top: it shares y and not x, its x axis is visible,
   its x ticks and label are on the top (one of them when its y axis is
   hidden, as `twiny()` hides the twin's), and a member with a hidden y
   axis draws its line first. The two sides are read apart.

**Once.** An Axes side whose line the layout showed (or found showing) is
recorded and not touched again, so a spine hidden after a layout stays
hidden. Right and top have separate records.

## Controls and differences (laid out, scientific)

| Case (review id) | Spine shown in 0.8 | 0.7 |
|---|---|---|
| side-by-side panels, also with shared x and the right panel moved right | no | no |
| two Axes in one box, also moved right (no shared axis) | no | no |
| `sharex` + `sharey` overlay moved right | no | no |
| `sharex` overlay; with only its label moved right (x20) | no | no |
| `twinx()`; with its tick marks off | twin | twin |
| `twinx()` with the parent's label moved right (x01) | twin | twin |
| `twinx()` with the parent moved right too (x22), also to `("outward", 30)` (n11) | twin (twin's line first) | twin |
| three y axes, offset third spine | both twins | both twins |
| inset `twinx()` (x23) | twin | twin |
| x02 / x03 twin with only its ticks / only its label moved left | twin | twin |
| x04 `b.twinx()` of a twin (matplotlib moves `b`'s ticks left) | `b` and `c` | `b` and `c` |
| 11-3 `sharex` overlay, ticks and label moved right (x12) | overlay | no |
| 11-4 twin's ticks and label moved left; parent moved right (x19) or not (x13) | parent (x19), none (x13) | twin |
| 11-5 twin with its y axis hidden (x14) | no | twin |
| 14 `sharex` overlay drawn like a twin (x axis and background hidden), only its ticks or only its label on the right | overlay | no |
| m02 twin's label moved left and its right ticks turned off (decided by delegation, see below) | none | twin |
| 1-A `twiny()`, also beside a `twinx()` of the same parent; its ticks or label moved down | twin's top spine | no |
| 1-A mirrors of x22, 11-3, 11-4 (swap), 11-5, 14 and of the `twiny` with both moved down | as on the right | no |

The first eleven rows match 0.7 pixel for pixel; 11-3 to 11-5, 14 and 1-A
are approved. m02 was decided later the same day by delegation: on its rendered
PoC the user said such a layout is not drawn in practice, then handed the
remaining decision to the implementing session ("너가 해줘"), which kept the
current rule (no line). A y axis with neither ticks nor a label on the right
is the 11-5 case, and drawing 0.7's line would need a private twin test.
Decision 14 settles a pair public state cannot tell apart: the
overlay in the last row and the twin of x02 / x03 with the same half-moved scale
differ only in the private `_twinned_axes`, and 0.7 drew a line on the twin
alone. Any public rule answers both alike; the user chose to keep the twin's
line, so the overlay gains one.

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
bare `savefig` keep the preset's hidden right (top) spine on a twin: ticks
and labels stay, the axis line does not. That already held for the twin
colours, tick formats and bar label settling. Without the layout:
`ax2.spines["right"].set_visible(True)` (`"top"` for a `twiny`).

## PRESET_OVERRIDE

The check is unchanged and still skips native twins. A line the layout shows
on an Axes that is not a native twin is reported as INFO: the overlay in
11-3 and in decision 14 (`axes 1, spines.right`), the parent in 11-4
(`axes 0, spines.right`) and their 1-A mirrors (`spines.top`). It is the
layout's line, not an override to undo.

## Verification (mechanical, in this repository)

- `tests/contracts/test_init_patch.py`: a fresh interpreter imports and
  reloads the package twice; every attribute of nine classes (`Axes`,
  `Figure`, `SubFigure`, `XAxis`, `YAxis`, `Spine`, `Text`, `Line2D`,
  `Legend`) looked up statically over `dir()`, every MRO class namespace and
  every class and callable of the imported matplotlib modules stay the same
  objects.
- `formatting/tests/test_twin_spines.py`: 69 cases (20 builds, each also
  neutral and `format_ticks=False`, three presets, five edits) must equal
  `twin_spines_07_golden.json`, recorded from origin/main (no D7 code) with
  0.7's wrapper, and the pixels of a live 0.7 re-enactment with the new step
  off. 11-1 to 11-5 and 14 are pinned against the live 0.7 run. The three
  `twiny` cases differ in the twin's top spine alone, and every pixel that
  changed lies within that spine's extent (1-A); the file is not re-recorded.
  The 1-A mirrors and the per-side record are pinned, and so is a scale
  moved onto a shared axis (no line), which killed the last 1-A mutant.
- Mutants that survived the review (width overwrite, no box condition, no
  "not y" condition, no "x shared" condition, step inside `format_ticks`,
  inherited rebinding on `Artist` and `FigureBase`) now fail, as do mutants
  of the new parts (inset walk and its recursion, tick condition, tick
  reading on both sides, twin's line first and its place-free form, the
  hidden-x-axis clause either way). Moving the step after the
  colours is equivalent and is not a target.
- PoC (outside the repository): the 21 approved renders are pixel-identical.

## Shipping (0.8) and wording

The user-facing wording is the CHANGELOG *Changed* entry "Importing
dartwork-mpl no longer rebinds any matplotlib class or function" (kept
there, not copied here, so the two cannot drift). *Removed*:
`dartwork_mpl.style.install_twinx_patch` and its root alias (internal,
never in `__all__`).

## Open points (not decided here)

- `PRESET_OVERRIDE` still uses `_twinned_axes`; aligning it with the public
  rule would change root's pinned shared-axes contract test.
