# Sizing and layout

## Canvas size

`dm.figsize(width, second)` returns the inch tuple for matplotlib's
`figsize=`. Width and height are physical; their units may differ.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("scientific")
x = np.linspace(0, 10, 101)

dm.figsize(dm.col1, "golden")    # paper, one column (9 cm)
dm.figsize(dm.col2, 0.45)        # two columns, height = 0.45 x width
dm.figsize("24cm", "12cm")       # exact width and height
dm.figsize("25.4cm", "16:9")     # a full 16:9 slide
dm.figsize_grid("6cm", "square", ncols=3, nrows=2, gap="0.6cm")  # panel-sized
print(dm.list_aspect_tokens())   # {token: height / width}
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
sets the outer margins so content meets the canvas edge. Call it once, after
drawing. It never changes the gaps between panels.

- `margin="2mm"` (or `"2%"`, `dm.mm(2)`) adds a uniform buffer.
- `ml`, `mr`, `mt`, `mb` set one side: `mr="1cm"` for right-side notes.
- With one main GridSpec pass it: `dm.simple_layout(fig, gs=gs)`.
- A `SubFigure` is not accepted; pass the parent `Figure`.

## Equal grid with panel labels

```python
fig, axes = plt.subplots(
    2, 2, figsize=dm.figsize("17cm", "standard"), sharex=True,
    gridspec_kw={"hspace": 0.35, "wspace": 0.3},
)
for i, ax in enumerate(axes.flat):
    ax.plot(x, np.sin(x + i))
    ax.set_ylabel("Response")
for ax in axes[-1]:
    ax.set_xlabel("Time (s)")
dm.label_axes(axes)              # a, b, c, d; labels=["(a)", ...] for others
dm.simple_layout(fig)
plt.close(fig)
```

Panels with both a title and an x label need `hspace` about 0.5 or more.

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
needs `fig.subfigures` with local margins instead of `simple_layout`; the
runnable recipe is in `dm.get_prompt("03-recipes")`, "Whole-canvas".

## Twin axes, legends outside, colorbars

```python
fig, ax1 = plt.subplots(figsize=dm.figsize("13cm", "wide"))
ax2 = ax1.twinx()
ax1.bar(range(6), [3, 4, 6, 5, 4, 2], color="dc.blue3")
ax2.plot(range(6), [12, 15, 21, 19, 14, 9], color="dc.red5", marker="o")
ax1.set(xlabel="Month", ylabel="Rain (mm)")
ax2.set_ylabel("Temperature (°C)")
dm.simple_layout(fig)
plt.close(fig)

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
for i in range(3):
    ax.plot(x, np.sin(x + i), label=f"Run {i + 1}")
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
dm.simple_layout(fig)            # makes room for the outside legend
plt.close(fig)

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
im = ax.imshow(np.outer(np.sin(x), np.cos(x)), cmap="viridis")
fig.colorbar(im, ax=ax, label="Value")
dm.simple_layout(fig)
plt.close(fig)
```

- Legend below everything: `fig.legend(loc="lower center", ncol=3,
  bbox_to_anchor=(0.5, 0))`, then `dm.simple_layout(fig)`.
- Legend inside, away from the data: `dm.place_legend(ax)`.
- A twin pair may report `CROSS_AXES_OVERLAP` for its shared x ticks; that
  finding is a false positive for twins.
