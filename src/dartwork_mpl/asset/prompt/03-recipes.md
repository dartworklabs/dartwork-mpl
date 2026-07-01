# Recipes — Intent → Function Call

A short cookbook keyed by user intent. Each entry shows the canonical
0.4 invocation. For full templates see
`dartwork-mpl://templates/{plot}`.

> **Before any recipe**, pick and apply a style preset:
>
> ```python
> dm.style.use("scientific")   # or "report" / "presentation" / "minimal" / "*-kr"
> ```
>
> Font sizes and *data* line widths are expressed as `dm.fs(n)` /
> `dm.lw(n)` / `dm.fw(n)` offsets from the active preset so the same
> code re-targets cleanly when you swap presets.
>
> Sub-1 **hairline literals** (`linewidth=0.3` for separator edges,
> `linewidth=0.5` for dashed reference lines) are kept as raw numbers
> on purpose — the lint policy explicitly allows them, and they need
> a stable positive value across presets. ``dm.lw(-1)`` would resolve
> to ``0`` for most presets, collapsing edges into the "no border"
> idiom.

## "Bar chart"

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(categories, values, color="oc.blue5", edgecolor="white",
       linewidth=0.3)
ax.set_ylabel("Value")
ax.set_title("…", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
```

## "Horizontal bar comparison"

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.barh(categories, values, color="oc.blue5", edgecolor="white",
        linewidth=0.3)
ax.set_xlabel("Value")
ax.invert_yaxis()
dm.simple_layout(fig)
```

## "Grouped/dodged bar (multiple categories per group)"

```python
import numpy as np
x = np.arange(len(categories))
w = 0.27
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "standard"))
ax.bar(x - w, series_a, w, color="oc.blue5", label="A",
       edgecolor="white", linewidth=0.3)
ax.bar(x, series_b, w, color="oc.green5", label="B",
       edgecolor="white", linewidth=0.3)
ax.bar(x + w, series_c, w, color="oc.orange5", label="C",
       edgecolor="white", linewidth=0.3)
ax.set_xticks(x); ax.set_xticklabels(categories)
ax.legend(fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

## "Waterfall (incremental change)"

```python
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "standard"))
ax.bar(labels, heights, bottom=baselines, color=colors,
       edgecolor="white", linewidth=0.3)
ax.axhline(0, color="oc.gray7", linewidth=0.3)
dm.simple_layout(fig)
```

## "Line chart, time series"

```python
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
ax.plot(t, y, color="oc.blue6", linewidth=dm.lw(0))
ax.set_xlabel("Time"); ax.set_ylabel("Signal")
dm.simple_layout(fig)
```

## "Scatter with trend"

```python
fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.scatter(x, y, color="oc.blue5", edgecolor="white",
           linewidth=0.3, s=20)
dm.simple_layout(fig)
```

## "Heatmap / correlation matrix"

```python
fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
im = ax.imshow(matrix, cmap="viridis", aspect="auto")
cbar = fig.colorbar(im, ax=ax)
cbar.ax.tick_params(labelsize=dm.fs(-1))
dm.simple_layout(fig)
```

## "Stacked bar"

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(x, a, color="oc.blue5", label="A",
       edgecolor="white", linewidth=0.3)
ax.bar(x, b, bottom=a, color="oc.green5", label="B",
       edgecolor="white", linewidth=0.3)
ax.legend(fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

## "Twin axis"

```python
fig, ax1 = plt.subplots(figsize=dm.figsize("15cm", "wide"))
ax2 = ax1.twinx()
ax1.bar(x, precip, color="oc.blue3", alpha=0.7,
        edgecolor="white", linewidth=0.3)
ax2.plot(x, temp, color="oc.red6", marker="o", markersize=3,
         linewidth=dm.lw(0))
dm.simple_layout(fig)
```

## "Korean labels"

Apply the language preset before creating the figure:

```python
dm.style.use("report-kr")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.set_xlabel("월")
ax.set_ylabel("값")
dm.simple_layout(fig)
```

## "Small multiples / faceted panels"

```python
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"),
                         sharex=True, sharey=True)
for ax, (label, y) in zip(axes.flat, panels, strict=False):
    ax.plot(x, y, color="oc.blue6", linewidth=dm.lw(0))
    ax.text(0.02, 0.95, label, transform=ax.transAxes,
            ha="left", va="top",
            fontsize=dm.fs(0), fontweight=dm.fw(1))
dm.simple_layout(fig)
```

## "Polar / radar / wind rose"

```python
fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"),
                       subplot_kw={"projection": "polar"})
ax.plot(theta_closed, values_closed, color="oc.blue6", linewidth=dm.lw(0))
ax.fill(theta_closed, values_closed, color="oc.blue3", alpha=0.3)
ax.set_xticks(theta)
ax.set_xticklabels(categories, fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

## "3D scatter / surface"

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "square"),
                       subplot_kw={"projection": "3d"})
ax.scatter(xs, ys, zs, color="oc.blue5", edgecolor="white",
           linewidth=0.3, s=20)
ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
dm.simple_layout(fig)
```

## "Multi-panel grid (a/b/c labels)"

```python
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"))
for ax, panel in zip(axes.flat, "abcd"):
    ax.text(0, 1, panel, transform=ax.transAxes + dm.make_offset(4, -4, fig),
            fontweight=dm.fw(1), va="top")
dm.label_axes(axes)
dm.simple_layout(fig)
```

## "Compare style presets side by side"

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

presets = ["scientific", "report", "presentation", "minimal"]
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("16cm", "standard"))
for ax, preset in zip(axes.flat, presets):
    with dm.style.context(preset):       # scoped — does not leak
        ax.plot(x, y, color="dc.teal2", linewidth=dm.lw(0))
        ax.set_title(f"'{preset}'",
                     fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
```

## "Save in multiple formats"

```python
dm.save_formats(fig, "output/figure", formats=("svg", "png", "pdf"),
                bbox_inches="tight", dpi=300)
```
