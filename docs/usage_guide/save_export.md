# Save and Validation

## Save and preview

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.plot(np.arange(50), np.cumsum(np.random.randn(50)) + 20, color="dc.teal3")
dm.simple_layout(fig)

dm.save_formats(
    fig,
    "output/experiment",
    formats=("png", "svg", "pdf"),
    bbox_inches="tight",
    validate=True,   # runs visual checks before saving (see below)
)
dm.save_and_show(fig, "output/experiment")  # save + inline preview
dm.show("output/experiment.svg", size=540)  # display a saved file in notebooks
```

:::{figure} images/save_scientific.svg
:alt: Scientific-style line chart saved with save_formats
:width: 100%
:::

**Key points:**

- `save_formats` writes multiple formats in one call, with optional visual validation
- `save_and_show` saves and displays the figure inline in Jupyter/IPython, closing it by default (`close_figure=True`)
- `show` displays an existing SVG/PNG for notebooks or reports
- See [API › Save & Export](../api/io.rst) for argument details

The built-in presets and legacy `dmpl` / `dmpl_light` styles embed
TrueType fonts in PDFs by default (`pdf.fonttype: 42`). To use Type 3
fonts instead, set `plt.rcParams["pdf.fonttype"] = 3` after applying the
style, or wrap the save call in `plt.rc_context({"pdf.fonttype": 3})`.

## Reproducible exports

`save_formats` makes SVG, PDF, and SVGZ reproducible by default for an
unchanged figure. SVG element ids are pinned with a `svg.hashsalt` derived
from the output basename, SVG/PDF timestamp metadata (`Date` /
`CreationDate`) is dropped, and SVGZ gzip output is written with `mtime=0`.
That means re-rendering the same chart does not churn version-controlled
artifacts.

Caller intent still wins: pass your own metadata to keep a timestamp
(`metadata={"Date": ...}` for SVG/SVGZ or `metadata={"CreationDate": ...}`
for PDF), or set `matplotlib.rcParams["svg.hashsalt"]` globally when you
want a project-wide salt instead of the output-basename salt.

## Visual validation

Detect common rendering issues automatically — especially useful in
AI agent pipelines where visual inspection is not available.

:::{tip}
**Try the live lint simulator** that appears below this heading — slide
figure dimensions, tick counts, and label lengths to see exactly which
warnings `dm.validate_figure()` would emit. The same heuristics that ship
with the package are running in your browser.
:::

```python
import dartwork_mpl as dm

# Run all checks manually
warnings = dm.validate_figure(fig)
for w in warnings:
    print(w)

# Run specific checks only
warnings = dm.validate_figure(fig, checks=("OVERFLOW", "TICK_CROWD"))
```

When `validate=True` is passed to `save_formats()`, validation runs before
saving. If issues are found, they're printed as warnings — the file is still
saved, but you'll know what to fix.

For a complete native Figure → full JSON report → PNG/PDF → actual image
review → separate-stem revision, use the [installed Python workflow](../ai/installed_python.md).
`save_formats` returns `None` and saves despite warnings; capture the returned
`validate_figure` objects separately, including `detail` and `CHECK_FAILED`.
Opening the actual image is a separate step from reading the report or filename.

**Available checks:** overflow detection, text overlap (within and across
axes), legend overflow, tick crowding, tick-unit duplication, tick rotation,
tick decimal precision, empty axes, margin asymmetry, pie label offsets, and
clipped text. Example output:

```text
⚠ OVERFLOW: Text 'ylabel' extends beyond figure bounds by 3.2 pt
⚠ TICK_CROWD: X-axis labels consume too much of the available span
```

### Static reference: every warning `validate_figure()` can emit

Plain-text fallback for the live lint simulator — useful when
JavaScript is disabled (AI agents, terminal browsers, search-engine
indexing). Each row is one registered `check_id` from
`dartwork_mpl.validate._checks`;
the **Severity** column is the default classification, and the **Fix**
column is the suggestion delivered by
`dm.validate_with_fixes(fig)` / `dm.validate_fixes.get_fix_suggestions`.

| `check_id`           | Severity | What it detects                                    | Suggested fix                                                       |
| -------------------- | -------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| `OVERFLOW`           | warning  | Text or axes content extends past the figure edge  | Re-run `dm.simple_layout(fig, margin="3mm")` or shorten the label   |
| `OVERLAP`            | warning  | Two text labels visually overlap                   | Rotate, abbreviate, or split into multiple panels                   |
| `UNIT_DUP`           | warning  | Axis label declares a unit also shown on ticks     | Keep the unit in the axis label; use bare numeric tick labels       |
| `CROSS_AXES_OVERLAP` | warning  | Text labels from different axes overlap            | Re-run `dm.simple_layout(fig)` (it widens `hspace` / `wspace` nobody set); raise a spacing you set |
| `LEGEND_OVERFLOW`    | warning  | Legend extends past axes / figure edge, or sits outside its plot at more than half its size | Many lines: `dm.label_line_ends(ax)`; else move the legend outside via `bbox_to_anchor` or shrink with `ncols` |
| `LEGEND_OVERLAP`     | warning  | A legend covers a title, axis or tick label, or figure text | `dm.place_legend(ax)` (or the side the user named, `loc="above"`), then `dm.simple_layout(fig)` |
| `LEGEND_ON_DATA`     | warning  | A legend is drawn over bars, lines or markers, across the outline of a filled area (`fill_between`, `stackplot`, violin bodies), over a text in an Axes, another legend or another panel | `dm.place_legend(ax)`, then `dm.simple_layout(fig)`; panels sharing their series: `dm.figure_legend(fig)`; many lines: `dm.label_line_ends(ax)` |
| `TICK_CROWD`         | info     | Tick labels fill the axis span and some neighbours stand closer than half an em | Numbers: fewer ticks (`MaxNLocator`). Names: drop a rotation you set and re-run `dm.simple_layout(fig)`; else `dm.figsize_for(..., labels=names)`, horizontal bars, or fewer categories |
| `TICK_OVERLAP`       | warning  | Neighbouring tick labels of one axis overlap       | Drop a rotation you set and re-run `dm.simple_layout(fig)` (it wraps, then turns, crowded labels); else horizontal bars or a wider canvas |
| `TICK_CORNER_OVERLAP` | warning | An x tick label overlaps a y tick label at a plot corner | Re-run `dm.simple_layout(fig)` (it grows one tick pad); pads you set: the `fig.axes[i].tick_params(axis=..., which=..., pad=...)` the fix names (a twin's Axes, minor ticks when theirs collide) |
| `TICK_ROTATION`      | info     | X tick labels are rotated needlessly (flat, they would stand half an em apart) or overlap | Set `rotation=0`, rotate to 45°, or reduce tick count               |
| `TICK_DECIMAL`       | warn/info | Tick labels have mixed, duplicate, trailing-zero or excessive decimals | Leave `decimals` unset on `dm.format_axis_*`, or match `dm.recommend_tick_decimals(values)` |
| `VALUE_LABEL_DECIMAL` | warning  | Whole-number value labels print trailing zeros (`120.0`) | On bars, `dm.label_bars(ax)` (no meaningless decimals); else format labels without decimals (`dm.annotate_value(ax, x, y, f'{v:,.0f}')`) |
| `VALUE_LABEL_ON_DATA` | warning  | A value label is drawn over a bar, a line or a marker in its plot box (twin Axes included) | On bars, `dm.label_bars(ax)`; on a point or line, `dm.annotate_value(ax, x, y, text)`; by hand, offset in points (`xytext=(0, 3), textcoords='offset points'`) |
| `EMPTY_AXES`         | info     | Axes carry no plotted artist                       | Plot data or remove the empty axes via `fig.delaxes(ax)`            |
| `MARGIN_ASYMMETRY`   | warning  | Left / right or top / bottom margins differ a lot  | Re-run `dm.simple_layout(fig)` (or call it for the first time)      |
| `PIE_LABEL_OFFSET`   | info     | Pie wedge label sits outside its wedge             | Set `pctdistance = 1.0 - wedge_width / 2`                           |
| `CLIPPED_TEXT`       | warning  | A text artist is clipped at its axes boundary      | Disable clipping (`text.set_clip_on(False)`) or move into figure    |
| `SLIDE_OVERSIZE` | warning | Slide preset on a canvas larger than 13.33 × 7.5 in (1% tolerance) shrinks text | Redraw at `dm.figsize_for("full_slide")` or `dm.figsize_for("slide")` under a title |
| `PRESET_OVERRIDE`    | info     | Grid, spines or a background differ from the active preset | Unless the user asked for it, delete the call that changed it |

:::{figure} images/validation_example.svg
:alt: Visual validation error example showing a bounding box overflow overlay
:width: 100%
:::

See [API › Visual Validation](../api/validate.rst)
for details.

## See also

- **Next →** [Extended Plots & Diagnostics](extras.md) — ready-to-use plot templates and inspection tools
- [API › Save & Export](../api/io.rst) for all save/export function arguments
- [Layout and Typography](layout.md) — optimize margins before saving
