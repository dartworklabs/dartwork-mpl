---
orphan: true
---

# Twin right spine at the layout, not at import (D7)

Status: implemented on `t3/twinx-explicit-20261106`, first shipped in 0.8.
Decision: root API decision D7 (2026-11-06). Not a release blocker.

## What import used to do

`import dartwork_mpl` called `style.install_twinx_patch()`, which replaced
`matplotlib.axes.Axes.twinx` with a wrapper. After the native call it ran two
lines on the returned Axes and nothing else:

| Effect | Value | Needed? |
|---|---|---|
| `twin.spines["right"].set_visible(True)` | presets set `axes.spines.right: False`, so the second y scale had no axis line | yes, this is the look |
| `twin.spines["right"].set_linewidth(rcParams["axes.linewidth"])` | a spine is created with that value already | no, a no-op |

`twiny`, the parent Axes, tick colours and the patch (background) were never
touched. Every figure-level feature that reads twins (twin colours, bar label
host, `place_legend`, outside anchors) groups Axes by position and shared
axes, not by this patch, and the layout does not measure spines. Only
`PRESET_OVERRIDE` skips native twins, via matplotlib's private
`_twinned_axes`; it existed before D7 and is unchanged.

## Decision

Import rebinds nothing on matplotlib. `dm.simple_layout` shows the spine.
No `dm.twin` wrapper; `ax.twinx()` stays matplotlib's own.

**When.** Inside `simple_layout`, after every check that can refuse the
call (no axes, no GridSpec, non-finite margins) and after the default tick
formats, immediately before the twin colours, which then colour the spine.
`format_ticks=False` does not skip it (it is not a number format). A refused
call changes nothing, as before.

**What.** `spines["right"].set_visible(True)` on each qualifying Axes. Width,
colour, position and bounds are left as they are.

**Which Axes.** One that draws its own y scale on the right of a shared plot
area. Read from public state only, the same "sides" the twin colours use
(`formatting._twin_colors._own_sides`):

1. *Position*: it is drawn in the same box as another visible rectilinear
   Axes (`get_position()` equal within 1e-9; `same_position_axes`).
2. *Shared axes*: it shares x with such a member and not y
   (`get_shared_x_axes()` / `get_shared_y_axes()`, public groupers).
3. *Placement*: its y axis is visible and its y label sits on the right
   (`yaxis.get_label_position()`), which `twinx()` sets.

**Once.** An Axes is settled the first time a layout finds it drawing its
scale on the right (shown, or already showing), recorded on the Axes, and
never touched again. A spine hidden after that layout stays hidden.

## Controls

The predicate is not the native-twin predicate, by design. Root's probe on
matplotlib 3.11.2 (`shared-axes-contract-probe`): two Axes in one box are not
native twins; a separate `sharex` Axes in one box is not a native twin either;
a real `twinx` is. The private grouper is the only thing that tells the last
two apart, and it says nothing about what is drawn.

| Control | Same box | Shares x only | Label right | Native twin | Spine shown |
|---|---|---|---|---|---|
| Side-by-side panels | no | n/a | n/a | no | no (0.7: no) |
| Two Axes in one box | yes | no | no | no | no (0.7: no) |
| `sharex` overlay | yes | yes | no | no | no (0.7: no) |
| `twinx()` | yes | yes | yes | yes | **yes** (0.7: yes) |
| `twiny()` | yes | shares y | n/a | yes | no (0.7: no) |
| `sharex` overlay moved right | yes | yes | yes | no | **yes** (0.7: no) |
| `twinx()` scale moved left | yes | yes | no | yes | no (0.7: yes) |
| `twinx()` with y axis hidden | yes | yes | n/a | yes | no (0.7: yes) |

The last three rows differ from 0.7: they follow what the figure draws (a
scale on the right gets its line) instead of how the Axes was made.

## Explicit settings and neutral mode

- `dm.config.twin_colors = "neutral"` only stops the colours; the spine
  shows as before.
- Width, colour, position (`set_position(("axes", 1.15))`, `"outward"`),
  tick and label colours, frame off, spines shown on the parent: untouched.
- Hidden after a layout: stays hidden (the "once" record).
- **Hidden between `twinx()` and the first layout: shows.** Under the presets
  the spine is already hidden, so `set_visible(False)` leaves no trace a
  public API can read; telling it apart needs the creation moment, which only
  an import-time hook sees. Escape: hide it after `dm.simple_layout`, or set
  `linewidth=0` (the documented "no border" form). This is the one explicit
  override that 0.7 kept and 0.8 does not. The twin colours have the same
  documented limit for a colour equal to the default.

## Users who never call `simple_layout`

`tight_layout`, constrained layout, `fig.add_axes` figures (refused by
`simple_layout`) and bare `savefig` now keep the preset's hidden right spine
on a twin: ticks, tick labels and axis label stay, the axis line does not.
That already held for every other dartwork rule applied at the layout (twin
colours, tick formats, bar label settling). To get the line without the
layout: `ax2.spines["right"].set_visible(True)`.

## Verification (mechanical, in this repository)

- `tests/contracts/test_init_patch.py`: a fresh interpreter imports and
  reloads the package; every attribute of `Axes`, `Figure`, `SubFigure`,
  `XAxis`, `YAxis` and `Spine` is still the same object.
- `formatting/tests/test_twin_spines.py`: the oracle is 0.7 re-enacted by
  hand (the two lines run after each `twinx()`). For the controls, three y
  axes with an offset spine, neutral mode, four presets and explicit
  settings, the laid-out figure must match the oracle pixel for pixel and
  spine by spine. The documented differences are pinned as such.
- PoC (outside the repository): every accepted figure with `simple_layout`
  (`dual_axis_timeseries`, both `twin_axis` templates, `theory_8_anatomy`,
  `after_dartwork`) renders pixel-identical at 300 dpi; without the layout
  each loses its twin's right spine and nothing else.

## Shipping (0.8) and wording

CHANGELOG, *Changed*:

> **Importing dartwork-mpl no longer changes matplotlib.** `ax.twinx()` is
> matplotlib's own again; `dm.simple_layout` shows the right spine of an
> Axes drawing its own y scale on the right (the one `twinx()` returns),
> which the presets hide. Figures laid out with `dm.simple_layout` look the
> same. Without it the twin keeps the preset's hidden right spine; show it
> with `ax2.spines["right"].set_visible(True)`. A right spine you hide
> before the first `dm.simple_layout` now shows; hide it after the layout.

CHANGELOG, *Removed*: `dartwork_mpl.style.install_twinx_patch` (internal,
never in `__all__`; also reachable as `dm.install_twinx_patch`).

Docs that said "monkey-patched" (`_LAYOUT_RECIPES.md` section 5, the sensor
dashboard example) now say the layout shows the spine; `layout.md` gains one
sentence next to the twin colours.

## Open points (not decided here)

- `twiny` top spine: still hidden by the presets, as in 0.7. Showing it is a
  look change and needs its own PoC and approval.
- `PRESET_OVERRIDE` still identifies twins with `_twinned_axes`; a `sharex`
  overlay moved right gets a shown right spine from the layout and an INFO
  finding from the check. Aligning the check with the public predicate would
  change root's pinned shared-axes contract test, so it is left to root.
