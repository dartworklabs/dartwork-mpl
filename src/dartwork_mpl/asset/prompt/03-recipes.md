# Recipes — Intent → Function Call

A short cookbook keyed by user intent. Each entry shows the canonical
native invocation. For full templates see
`dartwork-mpl://templates/{plot}`.

> **For a new figure**, pick and apply a style preset:
>
> ```python
> dm.style.use("scientific")   # or "report" / "presentation" / "minimal" / "poster" / "web" / "dark" / "*-kr"
> ```
>
> For a local revision, retain the existing preset and scoped overrides.
> Change the requested artist properties, then fit only if needed as below;
> do not reapply a preset or refit an already-fitting change.
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

## Choose the input version before a revision

For each logical input, keep its name, chosen version, SHA-256, source and
snapshot location visible beside the revision. Explicit requests settle the
choice; do not ask again when the requested version is clear.

| Request | Input choice |
| --- | --- |
| “Keep the previous data; change only the markers/style.” | Verify and reuse the retained bytes used by the previous figure, even if the upstream file changed. |
| “Use the current file.” | Read the authorized current bytes and pin them in a new revision; retain earlier snapshots and prior requested style edits. |
| Data version is materially ambiguous or prior evidence is unknown | Ask one relevant question before choosing; keep the original artifacts. |

Read only user/operator-authorized inputs. For native Python, save copies in
an authorized, user-owned project output area outside `datasets`. MCP instead
uses its operator-authorized private `storage_dir` and existing admission rules.
Never write upstream or collect unrelated files. Consume the pinned bytes/path,
rather than reopening
a mutable upstream path after hashing it. For style-only work, verify every
required input against its previous receipt. A missing/changed snapshot or
unknown input evidence needs clarification, never a silent current-file fallback.
Hashes establish byte identity, not freshness, permission or complete
reproducibility. An old snapshot is not evidence of the latest upstream data.
MCP uses its existing explicit Copy/Retained admission and receipts; native local
copies have no automatic MCP seven-day expiry or deletion guarantee.

## "Report style, only axis labels one step larger"

Agents translate the request into native artist edits; users need not write
plotting code. On an existing report figure, edit only the selected label Texts.
When revising retained source, insert the edit **after the original layout call**
(with its original kwargs), before the report/export block. Inspect the changed
content before deciding whether fitting is necessary.
For an in-memory figure, use its existing layout and artist handles directly.

```python
# Existing fig/ax; the original preset, plotting and layout have already run.
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)  # one more = current + 1 pt
fig.canvas.draw()  # inspect labels and measure actual Axes/legend bounds
# Continue with the existing report/export block, retaining the canvas.
```

An ordinary label enlargement permits necessary content fitting: if labels
clip or overlap, use the existing fitting method and settings as the starting
point, adjusting only the margins/spacing needed to fit. Keep the physical
canvas, panel/container allocations and explicit ratios, data, colors, other
typography and legend's intended location. Reuse the original `simple_layout`
kwargs/grid when applicable; do not reset to margin=0 defaults, introduce a new
layout engine or refit a change that already fits.

An explicit fixed Axes-position request overrides this fitting permission.
Preserve that geometry; disclose any clipping/conflict without claiming a
finished fit. Ask one relevant question only if a protected constraint must
change or the safe existing fitting method is unclear, retaining the original.
Explicit user instructions take precedence over these defaults.

Active native layout engines can move artists during draw/export. Preserve
their configuration, inspect the actual PNG/PDF, and compare bounds after both
drawing and exporting. Report any necessary Axes movement honestly; preserving
panel allocations does not imply fixed Axes data rectangles. Judge fit from
the actual content and requested constraints, not a universal pixel/mm tolerance.

For an explicit preset-relative request, `label.set_fontsize(dm.fs(1))` uses
global `font.size` + one step (1 pt; 2.6 pt under `presentation`), not
`axes.labelsize` or the current label size.
Repeat current-relative edits from the retained current value. For an absolute
request use `label.set_fontsize(12)` exactly. `dm.fw(1)` adds 100 to the global
base weight, while `dm.lw(1)` adds one step (1 pt; 2.6 pt under
`presentation`) to the global base line width.

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

### Keep a known Line2D legend sample in sync

A legend sample is a separate artist: editing a data line after legend creation
does not update its sample. For an existing plain `Line2D` series with a known
one-to-one default-handler legend mapping, apply the same requested dash setter
to its existing sample. Keep the legend object, location, text/order, frame and
all other handle properties. Do not call `ax.legend()` again or copy whole
artists with `update_from` (which can replace transforms and other properties).

This partial example requires the saved data-line handle `line` and the known
label `series_label`, with unique labels and default `Line2D` handlers established
by the original construction. The checks do not prove that a custom handler or
proxy represents the line; resolve such mappings from the original construction
or ask before editing. Do not infer the series from its current array index.

```python
from matplotlib.lines import Line2D

legend = ax.get_legend()
if (legend is None or type(line) is not Line2D or
        line not in ax.lines or line.get_label() != series_label):
    raise ValueError("Resolve the existing series and its known legend mapping")
texts = legend.get_texts()
labels = [text.get_text() for text in texts]
if labels.count(series_label) != 1:
    raise ValueError("Expected one known corresponding legend sample")
sample = legend.legend_handles[labels.index(series_label)]
if type(sample) is not Line2D:
    raise ValueError("Resolve the non-Line2D/custom legend sample explicitly")
# Requested nominal dash sequence; retain the existing scale_dashes policy.
for artist in (line, sample):
    artist.set_dashes((6, 2, 1, 2))
fig.canvas.draw()  # inspect both line and sample, then report/export
```

Place this patch after the original legend/layout construction in retained
source. For requested physical path lengths, use the local
`lines.scale_dashes=False` context described above around both setters; apply
only the requested width/color/cap setters to each corresponding artist. Render
and compare both samples and actual bounds. Do not reconstruct a legend to
repair an uncertain mapping or change unrelated properties to make it fit.

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

## File-only scripts: select the backend before creating figures

For standalone PNG/PDF export, start the process with `MPLBACKEND=Agg`, before
importing pyplot or creating figures: `MPLBACKEND=Agg python plot.py` (likewise
`plot-v2.py` and `pin-input.py`). This is scoped to file-only scripts; keep
interactive/notebook backend choices. `dm.figsize` returns the requested inch
tuple, but a GUI backend can quantize a Figure's size at creation. A local
macOS backend observation is not a universal limitation of `dm.figsize`.

Check `fig.get_size_inches()` after creation and after export against the
requested physical canvas. Keep `bbox_inches=None`, then inspect the saved
PDF page width/height (72 points per inch), not only the PNG pixel dimensions.
Report any mismatch and the backend actually used; do not silently resize the
canvas, change layout or blame the unit conversion. Agg avoids the observed
GUI quantization in these file-export examples; still check the actual PDF.

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

### Whole-figure estimate, template guidance and margin correction

`dm.figsize_grid("6cm", "standard", ncols=3, nrows=2, gap="0.6cm")`
returns a whole-figure size: width `3 * 6 + 2 * 0.6 = 19.2cm` and height
`2 * (6 * 0.75) + 0.6 = 9.6cm`. It does not create Axes or set GridSpec
spacing. The requested panel width and gap are inputs to that arithmetic;
labels, outer margins and native `wspace`/`hspace` determine the final Axes
rectangles and gaps. Neither exact 6cm Axes nor exact 0.6cm rendered gaps
are guaranteed. Render and measure the bounds below when those matter.

MCP `compose_layered_plot` returns a starting template (including its example
comments) and an annotation-layer checklist for the agent to adapt. Its
`applied`/`missing` lists use lexical detection in source, not rendered checks.
It does not rewrite code, execute a plot, allocate panels or repair spacing.
Installed Python users can read the same basic/advanced sources through
`importlib.resources`, as shown in the installed workflow below.

The bounded margin/convergence correction tracked by #209 is a separate
concern from template composition and figure-size arithmetic. The current
`dm.simple_layout` measures content and iteratively updates root GridSpec outer
margins, preserving native internal spacing. It does not solve nested local
spacing or guarantee that every label fits every requested canvas. Historical
`auto_layout` is removed; do not call it as an extra correction pass.
`simple_layout` returns `None`, not a convergence or validation report: inspect
`dm.validate_figure(fig)` findings and the actual PNG/PDF before accepting the
result. If content cannot fit the requested geometry, explain the constraint
and agree on a revision; do not silently delete data or shrink fonts.

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

### Measured presentation text correction

For the two whole-canvas recipes above, a measured 20 × 16 cm render using
`presentation` clipped the leftmost `Response` y-label with the initial
1.15 cm local left margin. Increasing only that margin to 1.70 cm cleared
that overflow in both examples. After inspecting the full report and images,
a revision can replace the `local = panel.add_gridspec(...)` call inside the
existing panel loop with:

<!-- snippet: no-run -->
```python
# This measured example's candidate, not a universal fit value.
local = panel.add_gridspec(
    1, 1, left=1.70 / width_cm, right=1 - 0.45 / width_cm,
    bottom=1.05 / height_cm, top=1 - 0.80 / height_cm)
```

Rebuild the figure with that local edit, then repeat drawing, measurement,
validation and image review, saving to a new output stem. Keep the 20 × 16 cm
canvas, requested container ratios, data, colors, preset fonts and legend
anchors. The larger left margin makes the data Axes narrower; it does not
change the container allocations. The value 1.70 cm is a candidate for these
measured examples, not an automatic preset override. If too little data space
remains or content still clips, explain the constraint and ask which constraint
may change; do not silently shrink fonts, remove data, resize the canvas or
relocate legends. The scientific recipe defaults above remain unchanged.

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

## "Values on the bars"

No request, `dm.label_bars(ax)` with its defaults; a request, that keyword.
The defaults: `dm.fs(-1)` at `dm.fw(1)` in the text colour, 3 pt beyond the
bar end; the number printed like the axis ticks (plain scaled numbers under
`dm.axis_unit`, the ticks' suffix under `dm.format_axis_si` or a
`PercentFormatter`, plain values under a formatter it cannot read, such as
a `FuncFormatter`: pass `fmt=`); three significant digits on the largest
value, then the fewest exact decimals, one count per call, no meaningless
`.0`; stacked bars' segments centred and a total beyond the stack; crowded
labels on vertical bars turned vertical by `dm.simple_layout`, which also
grows autoscaled limits just enough for the labels (limits you set stay; a
bar past them gets no label).

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(["A", "B", "C", "D"], [21.4e9, 18.0e9, 21.5e9, 33.0e9])
dm.axis_unit(ax, "y", label="Energy ({unit}Wh)")
dm.label_bars(ax)            # 21.4, 18.0, 21.5, 33.0 under Energy (GWh)
dm.simple_layout(fig)
```

Requests, one keyword each: `where="inside"` / `"center"` / `"outside"`;
`total="only"` / `False` (stacks); `crowded="skip"` (every other label) /
`"inside"`; `decimals=1`; `fmt="{} GWh"`, `"{:.2f}"` or a callable (a
template wraps the signed number, `$−3.5B`; a callable for `−$3.5B`);
`size=dm.fs(0)`; `color="dc.gray7"`, or `"series"` for labels off their bar.
Stacks need matching bottoms (a waterfall is not one); pad split series with
NaN, not 0. Thin `barh` rows hide every other label: a taller figure shows
them all. On a twin pair the labels go on the top axes.

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

`dm.simple_layout` colours each side like its one series (spine and ticks at
3:1, tick labels and axis label at 4.5:1); colours you set win, and
`with dm.config.override(twin_colors="neutral"):` keeps the preset's. One
legend for both: `dm.place_legend(ax1)`, not `ax1.legend(h1 + h2, l1 + l2)`;
it keeps the legend's title and settings (pass `ncols` again) and leaves a
legend of tuple or custom handles as it is.

## "Korean labels"

Apply the language preset before creating the figure:

```python
dm.style.use("report-kr")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.set_xlabel("월")
ax.set_ylabel("값")
dm.simple_layout(fig)
```

Untouched Korean axes read `50만 … 250만` and `23.01` / `16` dates and years
(no `년`). A unit in the label instead: `dm.axis_unit(ax, "y", label="인구
({unit}명)")` (`0, 0.2 … 1.0`; `dm.axis_unit_of(ax)` for value labels). Other
formats on request, one `dm.config` field each: `tick_years=4` (four-digit
years), `date_style="concise"` (`23, May, Sep`), `number_ladder="si"` (`0.5M`
in Korean figures). The override applies to what runs inside its `with`
block: wrap the code from figure creation to the last `dm.simple_layout`, or
set the field on `dm.config`.

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

`dm.label_axes` accepts `labels` for custom strings and `x` / `y` for
Axes-relative positions (values may extend outside 0–1). With `x="auto"`,
it uses -0.18 when an Axes has a y-label and -0.02 otherwise. `y=None`
(default) is 1.05, except that with `x="auto"` a left title (or a
centre/right one the letter would touch) takes the letter onto the title's
line, just before it. An explicit `y` (even `y=1.05`) keeps that height.
Extra compatible native `Text` properties, such as `color`,
`rotation` and `alpha`, pass through to `ax.text`:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"),
                         gridspec_kw={"hspace": 0.5, "wspace": 0.35})
for ax in axes.flat:
    ax.plot([0, 1, 2], [1, 3, 2], color="oc.blue9")
dm.label_axes(axes, labels=["(a)", "(b)", "(c)", "(d)"], x=-0.02, y=1.05,
              color="black", rotation=0, alpha=0.9)
dm.simple_layout(fig)
```

`fmt`, `loc` and `xy` are not supported `label_axes` arguments. Use
`labels` for text and `x` / `y` for position. The helper supplies the Axes
transform and left/bottom alignment itself; for custom transforms or
alignment, replace the preceding `dm.label_axes(...)` call with the native
calls below over the same Axes collection, before `dm.simple_layout(fig)`. Do not run both label calls:

<!-- snippet: no-run -->
```python
for ax, label in zip(axes.flat, ["(a)", "(b)", "(c)", "(d)"]):
    ax.text(0.02, 0.98, label, transform=ax.transAxes,
            fontsize=dm.fs(1), fontweight=dm.fw(1), ha="left", va="top")
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

## Interpreting optional source auto-fixes

Import `ast` and parse the complete source string with `ast.parse(code)`
before lint/fix. This nonexecuting preflight can detect malformed Python;
repair syntax errors in the source first. Some lint checks skip malformed
source, so empty findings or MCP's “No issues found” do not prove valid
syntax. Parsing and linting do not prove that code can compile, execute or
render correctly, and do not authorize executing arbitrary source.

For a source string named `code`, import `apply_lint_fixes` from
`dartwork_mpl.lint`, then call
`fixed_code, applied, unfixed = apply_lint_fixes(code)`. The MCP tool of the
same name returns a dict with those three keys. Neither route executes the
submitted source. Inspect the diff and every remaining finding: `applied`
locations refer to the original source, `unfixed` to the returned source.

The fixer needs an existing dartwork import binding and locally proven
calls. It can redirect pyplot's `style.use` with one supported literal
preset to that binding, or replace a no-argument `fig.tight_layout()` on a
proven pyplot-created Figure with `simple_layout(fig)`. Not all aliases or
constructors are recognized. It does not invent imports, infer the current
Figure for `plt.tight_layout()`, transfer layout kwargs, or rewrite
unsupported/dynamic styles, bare native Figure layout calls or arbitrary
artist properties. A suggestion alone does not establish an applicable fix.

Unchanged bytes with empty `applied` mean no correction was applied;
nonempty `unfixed` still needs attention, while empty `unfixed` means no
reported findings, not that all checks ran. Changed source can also retain
`unfixed` findings. Preserve the user's style, colors, legend and layout
intent, including intentional overrides. Stop retrying identical source.
Resolve bindings, arguments and intended behavior before making a scoped
source edit, then parse/lint again. For trusted code you choose to execute,
retain the normal runtime validation and actual image-review steps below.

## Native file input: pin the bytes actually consumed

This standalone example expects an authorized UTF-8 `measurements.csv` with
`x,y` columns (blank `y` means a missing reading). Save it as `pin-input.py`
and run `MPLBACKEND=Agg python pin-input.py` for file-only export.
Choose the input and a **new** revision directory in the configuration below.
The small JSON receipt is a local example, not a public schema/API. Treat its
paths as trusted, user-owned project paths, not untrusted service requests.
Keep the receipt, snapshot, exact source, PNG/PDF and full validation findings.

<!-- pinned-input-example -->
```python
import csv
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# User-authorized paths; output must be outside datasets. Never reuse a directory.
choice = "current"  # initial/current-file request; use "previous" for old data
upstream = Path("measurements.csv")
previous_receipt = Path("output/figure-v1/input.json")
revision = Path("output/figure-v1")
logical_name = "measurements"

if choice == "current":
    raw = upstream.read_bytes()  # read upstream once; copy AND parse these bytes
    source = str(upstream.resolve())
    selected_from = None
elif choice == "previous":
    old = json.loads(previous_receipt.read_text(encoding="utf-8"))
    if old["logical_name"] != logical_name:
        raise ValueError("Unknown prior input: clarify the intended version")
    raw = Path(old["snapshot"]).read_bytes()  # missing: stop, do not read upstream
    if hashlib.sha256(raw).hexdigest() != old["sha256"]:
        raise ValueError("Prior snapshot changed: clarify the intended version")
    source = old["source"]
    selected_from = str(previous_receipt.resolve())
else:
    raise ValueError("Choose current or previous explicitly")

rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
x = np.array([float(row["x"]) for row in rows])
y = np.array([float(row["y"]) if row["y"] else np.nan for row in rows])
if not np.isfinite(x).all() or np.isinf(y).any() or np.isfinite(y).sum() < 2:
    raise ValueError("Expected finite x and at least two finite y observations")
x, y = dm.validate_data(x, y, allow_nan=True)

revision.mkdir(parents=True, exist_ok=False)  # refuse overwrite, even on rerun
snapshot = revision / "input.csv"
with snapshot.open("xb") as stream:
    stream.write(raw)
receipt = dict(logical_name=logical_name, choice=choice, source=source,
               sha256=hashlib.sha256(raw).hexdigest(),
               snapshot=str(snapshot.resolve()), selected_from=selected_from)
with (revision / "input.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt, indent=2))  # show the selected version, not only a filename

# Keep the existing construction/overrides when adapting this to a revision.
dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, y, color="oc.blue9", label="Observed")
ax.set(xlabel="Time (s)", ylabel="Response")
ax.legend(loc="upper left")
dm.simple_layout(fig, margin="2mm")
code = Path(__file__).read_text(encoding="utf-8")
with (revision / "plot.py").open("x", encoding="utf-8") as stream:
    stream.write(code)
report = {"lint": [asdict(item) for item in dm.lint_code(code)],
          "visual": [asdict(item) for item in dm.validate_figure(fig)]}
with (revision / "report.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
dm.save_formats(fig, str(revision / "figure"), formats=("png", "pdf"),
                bbox_inches=None)
```

For the next style-only revision, retain the construction and all earlier edits,
set `choice = "previous"`, point `previous_receipt` at the previous revision's
`input.json`, and choose a new directory such as `output/figure-v2`. An explicit
current-file request instead sets `choice = "current"` with the authorized
upstream path and another new directory. Never relabel the old receipt as current.
Missing/unreadable receipts, absent snapshots, mismatched hashes or unknown
required inputs stop this example; disclose the problem and ask which available
version to use. Do not repair evidence or silently substitute another file.
Then follow the full report and actual PNG/PDF review steps below. These local
copies persist until the user manages them; they do not inherit MCP expiry.

## Installed Python: native Figure, full report and review

Save this as `plot.py` and run `MPLBACKEND=Agg python plot.py` with the
installed core package for file-only export. Blank
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

`dm.review(fig, "output/figure-v1")` does the save and the full
`validate_figure` report in one call, adds a summary of the figure and writes
`output/figure-v1.review.json`; for v2, `dm.review(fig, "output/figure-v2",
baseline="output/figure-v1", allow=[...])` lists every summary entry that
changed, and `Review.unexpected` the ones no `allow=` pattern covers. It is
experimental and judges nothing; `complete=True` only means every check ran.

Inspect all fields of the report, then open the **actual PNG** and the PDF
(or a rasterized PDF page) at target size. Check the gap, clipping, labels,
fonts and legend. No image reader means this step remains incomplete.
`CHECK_FAILED` is incomplete validation; `save_formats` returning `None` is
not a clean report. Keep advisory/fallback warnings and explain intentional
choices; don't silently change retained user overrides to silence warnings.

After reviewing v1, copy `plot.py` to `plot-v2.py`, replace every `figure-v1`
output stem in the copy with `figure-v2`, and insert the following immediately
before `source_path = Path(__file__)`. Run `MPLBACKEND=Agg python plot-v2.py`, then inspect
v2 PNG/PDF and its full report. This retains v1 source/files while saving the
exact revised script under v2. Keep previous local edits in later revisions.
Repeated “one more step” acts on retained current label values, not the preset
base. The insertion point is after the original layout call, before report/export.
Follow the local-revision recipe above: ordinary enlargement allows necessary
fitting through the existing method/settings while preserving the canvas,
panel/container allocations and ratios, data, style and legend's intended
location. Keep already-fitting geometry; an explicit Axes-position lock takes
precedence. Ask only when protected constraints must change or the safe existing
fit is unclear. Inspect actual draw/export bounds and PNG/PDF; report necessary
Axes movement. The selected-line recipe also updates its known existing legend
sample in place without rebuilding the legend.

```python
# Insert before the source/report/export block in plot-v2.py.
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)
# Draw and inspect changed labels before deciding whether a refit is needed.
fig.canvas.draw()
# Compare actual axes/legend bounds after draw/export; inspect for clipping.
# If needed and not geometry-locked, fit through the existing method/settings.
```

Hand off exact source, PNG, PDF and full report for each revision, data/gap
policy, selected preset and canvas, retained warnings and actual image-review
results. Deterministic examples are not proof of autonomous agent success.
