# Sizing and layout

Read this for canvas sizes, margins, multi-panel grids, twin axes, outside
legends and colorbars.

## Canvas size

With no size in the request, `dm.figsize_for` returns the active preset's
canvas, so the same request gets the same size whoever draws it:

| Preset | Widths |
|---|---|
| `report`, `web`, `minimal`, `dark` | 9 / 12 / 14.5 / 17 cm |
| `scientific` | one panel 9 cm (a column), grids and `dense`/`strip` 17 cm |
| `presentation` | 11.4 / 15.4 / 23.4 × 10.5 cm under a 16:9 slide's title |
| `poster` | report widths × font size / 8 pt |

Pass what you know and it picks from that table.

| Argument | Effect |
|---|---|
| `n_points=`, `n_series=` | sparse charts get the narrow canvas, dense ones the wide |
| `labels=names` | wide enough for category names to stand flat |
| `dual_axis=True` | room for a second y axis |
| `nrows=`, `ncols=` | a grid of panels |
| kind `"barh"`, `"grouped"`, `"matrix"`, `"compact"`, `"dense"`, `"strip"` | horizontal bars, grouped bars, a square heatmap, a small figure, wide time series |
| kind `"slide"`, `"full_slide"` | the body under a 16:9 slide's title (23.4 × 10.5 cm), the whole slide (25.4 × 14.29 cm) |

`presentation` is `scientific` with every point size × 2.6, so a slide chart
is drawn at slide size and its text is readable from the back of the room.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")
quarters, series = ["Q1", "Q2", "Q3", "Q4"], 3
dm.figsize_for(n_points=len(quarters), n_series=series)  # 12 x 9 cm
regions = ["North region", "South region", "East region", "West region", "Central region"]
dm.figsize_for(n_points=len(regions), n_series=1, labels=regions)  # 12 cm, not 9: flat names
dm.figsize_for("barh", n_points=10, n_series=1)  # 14.5 cm, long labels
dm.figsize_for("grouped", n_points=9, n_series=3)  # 12 cm, like "default"
dm.figsize_for(n_points=40, n_series=2, dual_axis=True)  # 14.5 cm
dm.figsize_for("slide")  # 23.4 x 10.5 cm, under a slide title
dm.figsize_for("full_slide")  # 25.4 x 14.29 cm, the whole 16:9 slide
dm.figsize_for(nrows=2, ncols=3)  # 17 x 8.5 cm
dm.style.use("presentation")
dm.figsize_for(n_points=len(quarters), n_series=series)  # 11.4 x 10.5 cm
dm.figsize_for(nrows=1, ncols=3)  # 23.4 x 10.5 cm, one row under the title
dm.figsize_for("full_slide")  # 25.4 x 14.29 cm: a grid of two rows
```

A size the user names goes to `dm.figsize(width, second)`, which returns the
inch tuple for matplotlib's `figsize=`. Width and height are physical; their
units may differ.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("scientific")
x = np.linspace(0, 10, 101)

dm.figsize(dm.col1, "golden")    # paper, one column (9 cm)
dm.figsize(dm.col2, 0.45)        # two columns, height = 0.45 x width
dm.figsize("24cm", "12cm")       # exact width and height
dm.figsize("19.2cm", "12.6cm")   # three 6 cm squares x 2 rows, 0.6 cm gaps
```

Aspect tokens (width:height): `tall` 2:3, `portrait` 4:5, `square` 1:1,
`standard` 4:3 (default), `a4` √2:1, `wide` 3:2, `golden` 1.618:1, `slide`
16:9, `cinema` 2:1, `panoramic` 3:1.

Keep a size the user asked for. The `oversize-width` lint above 17 cm is
page-fit advice, not a limit. DPI changes pixel density, never the physical
size. `dm.save_formats(..., bbox_inches="tight")` crops and changes the size;
the default `None` keeps it.

Pixels are not a physical unit, so `"1920px"` is rejected. Pick the DPI and
convert: 1920 × 1080 px at 200 DPI is
`dm.figsize(dm.inch(1920 / 200), dm.inch(1080 / 200))`, saved with
`dm.save_formats(fig, stem, formats=("png",), dpi=200)`.

## Margins: `dm.simple_layout`

It measures tick labels, axis labels, titles, legends and colorbars, then
sets the outer margins so content sits 1 mm from the canvas edge. Call it once, after
drawing. Where text still collides it fits the labels: an axis name that
runs into another panel or past the figure edge wraps at its spaces
(the same name on the same axis of that grid then wraps the same way),
`wspace` / `hspace` nobody set grow until neighbouring panels' text clears
(up to 1.5 cells), and bottom tick labels that collide or sit closer
than half an em (two names that close read as one) wrap at their spaces
(panels sharing x together) or, when they cannot, turn 30, 45 or 90
degrees; a change that would leave a plot under 30 % of its width or height
is taken back. Nothing is shortened or made smaller. What you set
stays: spacing you set (`gridspec_kw`, `fig.subplots_adjust`) wins, also
when it is too small, and labels you rotate or break yourself are left as
they are, so leave them out unless the user asks.
`fit_labels=False` turns the fitting off; tick
labels that still overlap are reported as `TICK_OVERLAP`, an x label on a
y label at a corner as `TICK_CORNER_OVERLAP`, text over another panel's
text as `CROSS_AXES_OVERLAP`.

- `margin="3mm"` (or `"2%"`, `dm.mm(3)`) sets the buffer; the default is `"1mm"`, `0` is flush.
- `ml`, `mr`, `mt`, `mb` set one side: `mr="1cm"` for right-side notes.
- With one main GridSpec pass it: `dm.simple_layout(fig, gs=gs)`.
- It does not lay out SubFigures: put the panels on one GridSpec (nested
  `subgridspec` is fine) instead.

## Equal grid with panel labels

```python
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"), sharex=True)
for i, ax in enumerate(axes.flat):
    ax.plot(x, np.sin(x + i))
    ax.set_ylabel("Response")
for ax in axes[-1]:
    ax.set_xlabel("Time (s)")
dm.label_axes(axes)              # a, b, c, d; labels=["(a)", ...] for others
dm.simple_layout(fig)            # widens hspace / wspace where panels' text meets
plt.close(fig)
```

Each letter starts at its column's y-axis name and sits on its title's
baseline, in points, so call `label_axes` before `simple_layout`.
Panels with both a title and an x label need no `hspace` of your own: the
layout parts them. A spacing the user asks for goes in
`gridspec_kw={"hspace": 0.5}` and then wins.

## Ratios, mosaics and nesting

Ratios split the space inside the margins and gaps, not the whole canvas.

```python
fig, (main, side) = plt.subplots(
    1, 2, figsize=dm.figsize("17cm", "7cm"),
    gridspec_kw={"width_ratios": [2, 1], "wspace": 0.35},
)
main.plot(x, np.sin(x))
side.hist(np.sin(x), bins=12, orientation="horizontal")
dm.simple_layout(fig)
plt.close(fig)

fig, axd = plt.subplot_mosaic(
    "AAB;CDB", figsize=dm.figsize("17cm", "standard"),
    gridspec_kw={"hspace": 0.5, "wspace": 0.4},
)
for name, ax in axd.items():
    ax.plot(x, np.cos(x))
    ax.set_title(name)
dm.label_axes([axd[k] for k in "ABCD"])
dm.simple_layout(fig)
plt.close(fig)

fig = plt.figure(figsize=dm.figsize("17cm", "9cm"))
gs = fig.add_gridspec(1, 2, width_ratios=[3, 2], wspace=0.3)
left = fig.add_subplot(gs[0])
inner = gs[1].subgridspec(2, 1, hspace=0.6)
top, bottom = fig.add_subplot(inner[0]), fig.add_subplot(inner[1])
for ax in (left, top, bottom):
    ax.plot(x, np.sin(x))
dm.simple_layout(fig, gs=gs)     # outer margins from the root grid
plt.close(fig)
```

An exact whole-canvas split (top 70 % of the canvas including its labels)
needs `fig.subfigures` with local margins instead of `simple_layout`:
`references/recipes.md`, "Whole-canvas regions".

## Twin axes, legends outside, colorbars

```python
fig, ax1 = plt.subplots(figsize=dm.figsize("13cm", "wide"))
ax2 = ax1.twinx()
ax2.spines["right"].set_visible(True)  # the presets hide it
ax1.bar(range(6), [3, 4, 6, 5, 4, 2], color="dc.blue3")
ax2.plot(range(6), [12, 15, 21, 19, 14, 9], color="dc.red5", marker="o")
ax1.set(xlabel="Month", ylabel="Rain (mm)")
ax2.set_ylabel("Temperature (°C)")
dm.simple_layout(fig)
plt.close(fig)

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
for i in range(3):
    ax.plot(x, np.sin(x + i), label=f"Run {i + 1}")
dm.place_legend(ax, loc="right")  # or "above", "below", "left"
dm.simple_layout(fig)            # makes room for the outside legend
plt.close(fig)

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
im = ax.imshow(np.outer(np.sin(x), np.cos(x)), cmap="viridis")
fig.colorbar(im, ax=ax, label="Value")
dm.simple_layout(fig)
plt.close(fig)
```

- One legend for panels that share their series: `dm.figure_legend(fig)`
  (above the panels, right when it does not fit above; `loc="below"` under
  everything), then `dm.simple_layout(fig)`; it removes the panel legends
  it replaces.
- Legend inside, away from the data: `dm.place_legend(ax)`; when every
  inside spot covers data it goes outside by itself: above, else below,
  else right, never onto another panel. `dm.simple_layout(fig)` places it
  again at the laid-out size.
- Legend outside one side ("legend above the plot"):
  `dm.place_legend(ax, loc="above")`; the library sets the gap, the rows and
  the clearance of tick labels; the legend may be wider than its Axes as
  long as it stays on the canvas and off the other columns' panels. It
  breaks names at spaces that would not fit so or (right, left) are wider
  than 40 % of the Axes, and `dm.simple_layout(fig)` keeps a title above
  it. A legend you then move through the returned `Legend` (`set_loc`,
  `set_bbox_to_anchor`) stays where you put it.
- Eight or more lines: `dm.label_line_ends(ax)` names them at their ends;
  `LEGEND_OVERFLOW` reports a legend outside that is more than half the
  plot's size.
- A twin pair: show the twin's right spine yourself, as above; the axis
  colours stay neutral unless you colour a side like its series
  (`ax2.tick_params(axis="y", colors=…)`); one legend for both is `dm.place_legend(ax)`,
  never `ax.legend(h1 + h2, l1 + l2)`; it and `dm.label_bars(ax)` put the
  legend and the bar values on the top twin, so the other twin's data is
  never drawn over them.
- A twin pair may report `CROSS_AXES_OVERLAP` for its shared x ticks; that
  finding is a false positive for twins.
