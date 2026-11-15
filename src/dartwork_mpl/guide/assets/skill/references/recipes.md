# Native customisation recipes

Presets supply defaults, not a closed list of properties: every matplotlib
artist property stays available. Find the artist (panel, series, label),
change only what was asked, and keep the data, canvas, colours and legend.
Discover a property with `type(artist)`, its getters, `artist.properties()` or
`help(type(artist))`. Order: preset first, then the figure, then local edits.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
x = np.linspace(0, 10, 101)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
(line,) = ax.plot(x, np.sin(x), label="Model")
ax.set(xlabel="Time (s)", ylabel="Signal")
dm.simple_layout(fig)
```

## Sizes relative to the preset or to the current value

`dm.fs(n)` is the preset's `font.size` plus `n` steps, `dm.lw(n)` its
`lines.linewidth` plus `n` steps (a step is 1 pt, 2.6 pt under
`presentation`), `dm.fw(n)` its `font.weight` plus 100 per step. They read the
preset, never an artist. "One step larger than now" is the getter plus one,
and a second "one more" adds to that again:

```python
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)   # current + 1 pt
ax.yaxis.label.set_fontweight(dm.fw(1))            # preset weight + 100
```

An absolute request (`fontsize=12`, `linewidth=1.5`) is used exactly; the
`fontsize-literal` / `linewidth-literal` lint warnings are then reported, not
"fixed". Hairlines stay literal (`linewidth=0.3`): `dm.lw(-1)` is 0 on a
preset whose base is 1 pt, and `linewidth=0` means no border.

## One line: width, colour and dash spacing

Edit the existing `Line2D`; do not draw another one. Dash lengths scale with
the line width unless `lines.scale_dashes` is off around the setters:

```python
with plt.rc_context({"lines.scale_dashes": False}):
    line.set_linewidth(2.5)
    line.set_color("dc.blue6")
    line.set_linestyle((0, (4, 2, 1, 2)))   # offset, then on/off lengths in pt
```

A legend sample is its own artist: after editing a line that a legend shows,
apply the same setter to `ax.get_legend().legend_handles[i]` (the entry with
that label) instead of calling `ax.legend()` again.

## One spine, the ticks of one axis, one grid

Apply only the line that matches the request:

```python
ax.spines["left"].set_linewidth(0.7)
ax.tick_params(axis="x", which="major", length=4, width=0.7)
ax.tick_params(axis="y", which="major", labelcolor="dc.blue6")
ax.grid(True, axis="y", color="dc.gray3", linewidth=0.3)
plt.close(fig)
```

Axis labels (`ax.xaxis.label`) are not tick labels (`ax.get_xticklabels()`).

## Exact canvas width and height

Width and height are physical and may use different units. `bbox_inches=None`
(the default) keeps the canvas; `"tight"` crops it. DPI sets pixel density,
never the physical size. The `oversize-width` lint above 17 cm is page-fit
advice: a requested 24 cm stays 24 cm.

```python
for name, size in (
    ("cm", dm.figsize("24cm", "12cm")),
    ("mm", dm.figsize("240mm", "120mm")),
    ("in", dm.figsize(dm.inch(24 / 2.54), dm.inch(12 / 2.54))),
):
    fig, ax = plt.subplots(figsize=size)
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set(xlabel="Time", ylabel="Value")
    dm.simple_layout(fig, margin="2%")
    dm.save_formats(fig, f"output/canvas-{name}", formats=("png", "pdf"))
    plt.close(fig)
```

File-only scripts run with `MPLBACKEND=Agg python plot.py`: a GUI backend can
round the canvas at creation. Check `fig.get_size_inches()` and the PDF page
size (72 pt per inch) against the request and report any mismatch.

## Whole-canvas regions

GridSpec ratios split the space inside the margins and gaps, so a 7:3 grid is
not 70 % / 30 % of the canvas. For exact regions that include their own labels,
use SubFigures with zero gaps and local margins in centimetres, and do not call
`dm.simple_layout` (it fits each SubFigure's grid in its box, but the local
margins here are the layout):

```python
fig = plt.figure(figsize=dm.figsize("20cm", "16cm"))
rows = list(fig.subfigures(2, 1, height_ratios=[7, 3], hspace=0))
for i, panel in enumerate(rows):
    width_cm = panel.bbox.width / fig.dpi * 2.54
    height_cm = panel.bbox.height / fig.dpi * 2.54
    local = panel.add_gridspec(
        1, 1, left=1.15 / width_cm, right=1 - 0.45 / width_cm,
        bottom=1.05 / height_cm, top=1 - 0.80 / height_cm,
    )
    ax = panel.add_subplot(local[0])
    ax.plot(x, np.sin(x + i))
    ax.set(xlabel="Time (s)", ylabel="Response")
dm.save_formats(fig, "output/regions", formats=("png",))
plt.close(fig)
```

Different column splits per row (40:60 above, 70:30 below) nest
`row.subfigures(1, 2, width_ratios=[4, 6], wspace=0)` in each row. The
padding above fits these labels; render, look and adjust it for others.

## Presets side by side

`dm.style.context(name)` scopes a preset to one block and restores the
previous one on exit:

```python
for preset in ("scientific", "report", "presentation"):
    with dm.style.context(preset):
        fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=4, n_series=1))
        ax.bar(["A", "B", "C", "D"], [3, 5, 2, 4])
        ax.set(xlabel="Group", ylabel="Count")
        dm.simple_layout(fig)
        dm.save_formats(fig, f"output/preset-{preset}", formats=("png",))
        plt.close(fig)
```

## Saving

`dm.save_formats(fig, "output/figure", formats=("svg", "png", "pdf"), dpi=300)`
writes every format from one call. A figure that ends with only `plt.show()`
leaves no file.

## When to ask

Ask one short question only when a missing fact changes the result, for
example the column width of a final journal figure. For a draft, use the
default, say which preset and size you used and invite correction.
