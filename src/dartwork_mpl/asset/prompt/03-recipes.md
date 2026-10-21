# Recipes — Intent → Function Call

A short cookbook keyed by user intent. Each entry shows the canonical
native invocation. For full templates see
`dartwork-mpl://templates/{plot}`.

> **Before any recipe**, pick and apply a style preset:
>
> ```python
> dm.style.use("scientific")   # or "report" / "presentation" / "minimal" / "*-kr"
> ```
>
> Presets provide defaults. Use `dm.fs(n)` / `dm.lw(n)` / `dm.fw(n)` for
> preset-relative intent; retain explicit absolute user values and colors.
> Literal-size/width warnings remain advisory: inspect and report them.
> The 18 templates are starters; native matplotlib chart types and properties
> remain available. Choose unspecified defaults from the data and purpose.
>
> Sub-1 **hairline literals** (`linewidth=0.3` for separator edges,
> `linewidth=0.5` for dashed reference lines) are kept as raw numbers
> on purpose — the lint policy explicitly allows them, and they need
> a stable positive value across presets. ``dm.lw(-1)`` would resolve
> to ``0`` for most presets, collapsing edges into the "no border"
> idiom.

## "Report style, only axis labels one step larger"

Agents translate the request into native artist edits; users need not write
plotting code. Apply the preset before creating artists or restoring retained
overrides. On an existing report figure, edit only the selected label Texts:

```python
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)  # one more = current + 1 pt
# Keep the existing axes/layout when the enlarged labels still fit.
```

Keep the existing axes/layout if labels still fit. If a refit is necessary,
reuse the original `simple_layout` kwargs, grid and margin settings; do not
blindly rerun its margin=0 defaults. Disclose any necessary movement of axes
or an anchored legend rather than claiming pixel-position invariance.

For an explicit preset-relative request, `label.set_fontsize(dm.fs(1))` uses
global `font.size + 1 pt`, not `axes.labelsize` or the current label size.
Repeat current-relative edits from the retained current value. For an absolute
request use `label.set_fontsize(12)` exactly. `dm.fw(1)` adds 100 to the global
base weight, while `dm.lw(1)` adds 1 pt to the global base line width.

## "A selected line: exact width, color and dash/dot spacing"

Resolve the series/panel first; `line` below is its saved existing artist
handle. Apply only the requested setters; do not append another `ax.plot` line.
For a request changing its width, color and nominal dash/dot path lengths:

```python
with plt.rc_context({"lines.scale_dashes": False}):
    line.set_linewidth(2.5)
    line.set_color("#235fa4")
    line.set_linestyle((0, (4, 2, 1, 2)))
```

This preserves the cap style. Change caps only when requested. The tuple gives
offset and alternating nominal on/off path lengths in points; round caps
extend visible ink and shorten visible gaps. Without `scale_dashes=False`,
lengths scale with line width by default. Keep that local context around line
creation or any later setter that rescales dashes when physical lengths must
stay fixed. For relative width use `line.get_linewidth() + delta`.
Check the rendered result; no single dash tuple fits every chart purpose.

## "Only the left spine, x ticks, y tick labels or y grid"

These are independent examples: apply only the line(s) matching the request to
the resolved `ax`. Do not execute the whole block for a single-property edit.

```python
ax.spines["left"].set_color("black")
ax.spines["left"].set_linewidth(0.7)
ax.tick_params(axis="x", which="major", length=4, width=0.7)
ax.tick_params(axis="y", which="major", labelcolor="#235fa4", labelsize=10)
ax.grid(axis="y", which="major", visible=True, color="0.8", linewidth=0.3)
```

Axis labels (`ax.xaxis.label`, `ax.yaxis.label`) differ from tick labels
(`ax.get_xticklabels()`, `ax.get_yticklabels()`). Inspect `type(artist)`,
`artist.properties()`, getters or `help(type(artist))`; consult official docs
for the installed matplotlib version for unsupported or unfamiliar properties.
Ask one short question only if panel/series/property scope is materially unclear.

## "Exact canvas width and height (cm, mm or inches)"

Choose the preset by the policy's purpose/context rules first. This complete
example uses `report` as an illustrative selection and writes three equivalent
24 × 12 cm canvases using existing unit forms:

<!-- canvas-units-example -->
```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")
for name, size in (
    ("cm", dm.figsize("24cm", "12cm")),
    ("mm", dm.figsize("240mm", "120mm")),
    ("in", dm.figsize(dm.inch(24 / 2.54), dm.inch(12 / 2.54))),
):
    fig, ax = plt.subplots(figsize=size)
    ax.plot([0, 1, 2], [1, 3, 2], linewidth=dm.lw(0))
    ax.set_xlabel("Time")
    ax.set_ylabel("Value", fontsize=dm.fs(0), fontweight=dm.fw(0))
    dm.simple_layout(fig, margin="2%")
    dm.save_formats(fig, f"output/canvas-{name}", formats=("png", "pdf"),
                    bbox_inches=None)
    plt.close(fig)
```

`bbox_inches=None` (the existing default) retains the canvas; `"tight"`
crops to content. DPI determines raster pixel density, not physical size;
PNG dimensions quantize to whole pixels. The `oversize-width` warning asks for
page-fit review and must not silently shrink an explicit 24 cm request.

For multi-panel work, native `plt.figure` + GridSpec/nested GridSpec are valid.
GridSpec ratios apply inside its assigned bounds: outer margins and
`wspace`/`hspace` mean a 7:3 grid alone does not allocate 70%/30% of the
whole canvas. For exact whole-canvas regions, use native container allocation
(e.g. `SubFigure`), keep titles, labels and local padding inside each container,
and measure the container bounding boxes to verify the requested allocation.
Keep that allocation distinct from row-specific ratios: two 50:50 rows can
contain 40:60 columns above and 70:30 columns below. Retain the selected preset
and data when changing geometry alone. Do not pass a `SubFigure` directly to
`dm.simple_layout`; this helper requires a parent `Figure`.

## Native multi-panel layouts

Use this setup, choose **one** construction below, then run the shared drawing
and export block. These are executable native matplotlib recipes, not another
layout API. Keep the existing preset, data, colors, fonts, legend and retained
scoped overrides when adapting an existing figure. The example uses a provisional
20 × 16 cm canvas; choose physical dimensions for your page or slide.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# Reuse the selected preset for geometry-only revisions.
dm.style.use("scientific")  # report/document: report; talk/slides: presentation
x = np.linspace(0, 12, 121)
fig = plt.figure(figsize=dm.figsize("20cm", "16cm"))
```

### Equal grid

```python
gs = fig.add_gridspec(2, 2, wspace=0.5, hspace=0.65)
axes = {name: fig.add_subplot(gs[i // 2, i % 2])
        for i, name in enumerate("ABCD")}
```

### Global row and column ratios

Every row shares the 2:1 column widths; every column shares the 3:2 row heights.
These ratios concern data rectangles inside the grid, excluding gaps and outer
content margins. They do not partition the entire canvas into percentages.

```python
gs = fig.add_gridspec(2, 2, width_ratios=[2, 1], height_ratios=[3, 2],
                      wspace=0.5, hspace=0.65)
axes = {name: fig.add_subplot(gs[i // 2, i % 2])
        for i, name in enumerate("ABCD")}
```

### Spanning, asymmetric and nested

A spans both rows; D spans the lower right region. B/C share a nested grid.
The shared finish fits outer margins through the root `gs`; nested spacing
remains a native local choice.

```python
gs = fig.add_gridspec(2, 3, wspace=0.75, hspace=0.65)
inner = gs[0, 1:].subgridspec(1, 2, width_ratios=[1, 2], wspace=0.8)
axes = {"A": fig.add_subplot(gs[:, 0]),
        "B": fig.add_subplot(inner[0, 0]),
        "C": fig.add_subplot(inner[0, 1]),
        "D": fig.add_subplot(gs[1, 1:])}
```

### Whole-canvas top 70%, bottom 30%

Here `SubFigure` regions include all local labels and padding. Zero container
spacing makes their heights exactly 70%/30% of the canvas. This explicit 2×1
construction gives each row one full-width plot. Data rectangles become smaller
after local margins.

```python
rows = list(fig.subfigures(2, 1, height_ratios=[7, 3], hspace=0))
panels = rows
axes = {}
for name, panel in zip("AB", panels):
    width_cm = panel.bbox.width / fig.dpi * 2.54
    height_cm = panel.bbox.height / fig.dpi * 2.54
    local = panel.add_gridspec(
        1, 1, left=1.15 / width_cm, right=1 - 0.45 / width_cm,
        bottom=1.05 / height_cm, top=1 - 0.80 / height_cm)
    axes[name] = panel.add_subplot(local[0])
```

For a 2×2 variant with two equal panels per row, replace `panels = rows` with
`panels = [panel for row in rows for panel in row.subfigures(1, 2, wspace=0)]`
and use `zip("ABCD", panels)`. The row containers remain exactly 70%/30%.

### Whole-canvas rows 50:50, top widths 40:60, bottom 70:30

A single global `width_ratios` cannot express this. Allocate independent native
containers within each row. Every percentage includes that panel's labels and
padding; it is not a promise about its Axes data width.

```python
rows = list(fig.subfigures(2, 1, height_ratios=[1, 1], hspace=0))
panels = [*rows[0].subfigures(1, 2, width_ratios=[4, 6], wspace=0),
          *rows[1].subfigures(1, 2, width_ratios=[7, 3], wspace=0)]
axes = {}
for name, panel in zip("ABCD", panels):
    width_cm = panel.bbox.width / fig.dpi * 2.54
    height_cm = panel.bbox.height / fig.dpi * 2.54
    local = panel.add_gridspec(
        1, 1, left=1.15 / width_cm, right=1 - 0.45 / width_cm,
        bottom=1.05 / height_cm, top=1 - 0.80 / height_cm)
    axes[name] = panel.add_subplot(local[0])
```

### Shared drawing, measurement and export

Run this after the chosen construction. For the three ordinary grids use the
`simple_layout` line. For either whole-canvas container recipe **omit that line**:
the explicit native local margins above are the legitimate margin path.
The physical padding is a starting point for these labels, not a universal fit;
render, measure and adjust local margins if content does not fit.

```python
from dataclasses import asdict
from pathlib import Path
import json
from matplotlib.ticker import MaxNLocator

for i, (name, ax) in enumerate(axes.items()):
    ax.plot(x, np.sin(x + i), color="oc.blue9", label="Series 1")
    ax.plot(x, np.cos(x + i), color="oc.orange7", label="Series 2")
    ax.set(title=f"{name} · Signal", xlabel="Time (s)", ylabel="Response")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.legend(loc="upper right", ncol=2)

# Ordinary GridSpec recipes only; omit for either SubFigure recipe.
dm.simple_layout(fig, gs=gs, margin="2mm")
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
geometry = {"canvas_px": list(fig.bbox.bounds),
            "axes_data_px": {k: list(a.bbox.bounds) for k, a in axes.items()},
            "axes_content_px": {k: list(a.get_tightbbox(renderer).bounds)
                                for k, a in axes.items()}}
# For either container recipe, also record the allocated regions:
# geometry["rows_px"] = [list(row.bbox.bounds) for row in rows]
# geometry["panels_px"] = [list(panel.bbox.bounds) for panel in panels]
# Divide row heights by fig.bbox.height; panel widths by their row width.
# Compare those fractions to the requested ratios, separately from Axes bounds.
report = [asdict(item) for item in dm.validate_figure(fig)]
Path("output").mkdir(exist_ok=True)
Path("output/layout-geometry.json").write_text(json.dumps(geometry, indent=2))
Path("output/layout-report.json").write_text(json.dumps(report, indent=2))
dm.save_formats(fig, "output/layout-v1", formats=("png", "pdf"),
                bbox_inches=None)
```

`dm.simple_layout` needs a parent `Figure`; passing a `SubFigure` raises
`AttributeError` for missing `get_size_inches`. Passing a nested GridSpec with a
parent Figure walks to its root GridSpec and adjusts root outer margins; it
does not solve each nested region independently. Calling it on the root Figure
of a SubFigure tree is not a local-margin solution either. Do not insert fake
helper calls or silently change requested allocations to make validation pass.
Read the full report (including `CHECK_FAILED`), inspect the actual PNG and PDF,
and retain heuristic/advisory warnings with any explanation. Save a revision to
a new stem such as `layout-v2`; keep v1, exact source and geometry for review.

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
                bbox_inches=None, dpi=300)
```

## Installed Python: native Figure, full report and review

Save this as `plot.py` and run it with the installed core package. Blank
readings represent gaps here. `validate_data` defaults to filtering NaN/Inf
rows, which can close a line gap; `allow_nan=True` preserves them but also
allows infinity, so check shape/alignment/domain separately. This helper
returns cleaned arrays; MCP `validate_plot_data` is a distinct JSON tool.

```python
from dataclasses import asdict
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# Blank observations represent missing readings, so retain a visible line gap.
x_input = [0, 1, 2, 3, 4, 5]
y_input = [1.0, 1.8, None, 2.1, 1.7, 2.5]
x = np.asarray(x_input, dtype=float)
y = np.asarray([np.nan if v is None else v for v in y_input], dtype=float)
if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
    raise ValueError("Expected aligned one-dimensional x/y observations")
if not np.isfinite(x).all() or np.isinf(y).any() or np.isfinite(y).sum() < 2:
    raise ValueError("Expected finite x and at least two finite y observations")
x, y = dm.validate_data(x, y, allow_nan=True)

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
line, = ax.plot(x, y, color="oc.blue9", label="Observed")
ax.set(xlabel="Time (s)", ylabel="Response", title="Missing reading retained")
ax.legend(loc="upper left")
dm.simple_layout(fig, margin="2mm")

# Save this complete script as plot.py before running it.
source_path = Path(__file__)
code = source_path.read_text(encoding="utf-8")
report = {"lint": [asdict(item) for item in dm.lint_code(code)],
          "visual": [asdict(item) for item in dm.validate_figure(fig)]}
Path("output").mkdir(exist_ok=True)
Path("output/figure-v1.py").write_text(code, encoding="utf-8")
Path("output/figure-v1-report.json").write_text(json.dumps(report, indent=2))
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"),
                bbox_inches=None)
```

Inspect all fields of the report, then open the **actual PNG** and the PDF
(or a rasterized PDF page) at target size. Check the gap, clipping, labels,
fonts and legend. No image reader means this step remains incomplete.
`CHECK_FAILED` is incomplete validation; `save_formats` returning `None` is
not a clean report. Keep advisory/fallback warnings and explain intentional
choices; don't silently change retained user overrides to silence warnings.

After reviewing v1, copy `plot.py` to `plot-v2.py`, replace every `figure-v1`
output stem in the copy with `figure-v2`, and insert the following immediately
before `source_path = Path(__file__)`. Run `python plot-v2.py`, then inspect
v2 PNG/PDF and its full report. This retains v1 source/files while saving the
exact revised script under v2. Keep previous local edits in later revisions.
Repeated “one more step” acts on retained current label values, not the preset
base. Keep the current layout when the enlarged labels fit. If image/content
inspection shows clipping or overlap, refit using the original `simple_layout`
kwargs (`margin="2mm"` here, and the original `gs` if used), then inspect again
and report any necessary movement of axes or anchored legends.

```python
# Insert before the source/report/export block in plot-v2.py.
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)
# Draw and inspect changed labels before deciding whether a refit is needed.
fig.canvas.draw()
# Keep existing axes/legend positions when labels still fit. Only if needed:
# dm.simple_layout(fig, margin="2mm")  # reuse the original margin/grid kwargs
```

Hand off exact source, PNG, PDF and full report for each revision, data/gap
policy, selected preset and canvas, retained warnings and actual image-review
results. Deterministic examples are not proof of autonomous agent success.
