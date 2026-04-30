# Recipes — Intent → Function Call

A short cookbook keyed by user intent. Each entry shows the canonical
0.4 invocation. For full templates see
`dartwork-mpl://templates/{plot}`.

## "Bar chart"

```python
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="oc.blue5", edgecolor="white",
       linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
```

## "Line chart, time series"

```python
fig, ax = dm.subplots(width="15cm", aspect="wide")
ax.plot(t, y, color="oc.blue6", linewidth=0.8)
ax.set_xlabel("Time"); ax.set_ylabel("Signal")
dm.auto_layout(fig)
```

## "Scatter with trend"

```python
fig, ax = dm.subplots(width="11cm", aspect="square")
ax.scatter(x, y, color="oc.blue5", edgecolor="white", linewidth=0.3,
           s=20)
dm.auto_layout(fig)
```

## "Heatmap / correlation matrix"

```python
fig, ax = dm.subplots(width="11cm", aspect="square")
im = ax.imshow(matrix, cmap="viridis", aspect="auto")
fig.colorbar(im, ax=ax)
dm.auto_layout(fig)
```

## "Stacked bar"

```python
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(x, a, color="oc.blue5", label="A")
ax.bar(x, b, bottom=a, color="oc.green5", label="B")
ax.legend()
dm.auto_layout(fig)
```

## "Twin axis"

```python
fig, ax1 = dm.subplots(width="15cm", aspect="wide")
ax2 = ax1.twinx()
ax1.bar(x, precip, color="oc.blue3", alpha=0.7)
ax2.plot(x, temp, color="oc.red6", marker="o", markersize=3)
dm.auto_layout(fig)
```

## "Korean labels"

Apply the language preset before creating the figure:

```python
dm.style.use("report-kr")
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.set_xlabel("월")
ax.set_ylabel("값")
dm.auto_layout(fig)
```

## "Multi-panel grid (a/b/c labels)"

```python
fig, axes = dm.subplots(2, 2, width="17cm", aspect="standard")
for ax, panel in zip(axes.flat, "abcd"):
    ax.text(0, 1, panel, transform=ax.transAxes + dm.make_offset(4, -4, fig),
            weight="bold", va="top")
dm.label_axes(axes)
dm.auto_layout(fig)
```

## "Save in multiple formats"

```python
dm.save_formats(fig, "output/figure", formats=("svg", "png", "pdf"),
                bbox_inches="tight", dpi=300)
```
