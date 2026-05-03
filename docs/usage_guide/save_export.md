# Save and Validation

## Save and preview

```python
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = dm.subplots(width="9cm", aspect="standard")
ax.plot(np.arange(50), np.cumsum(np.random.randn(50)) + 20, color="oc.blue6")
dm.auto_layout(fig)

dm.save_formats(
    fig,
    "output/experiment",
    formats=("png", "svg", "pdf"),
    bbox_inches="tight",
    validate=True,   # runs visual checks before saving (see below)
)
dm.save_and_show(fig, "output/experiment")  # save + inline preview
dm.show("output/forecast.svg", size=540)    # display a saved file in notebooks
```

:::{figure} images/save_scientific.svg
:alt: Scientific-style line chart saved with save_formats
:width: 100%
:::

**Key points:**

- `save_formats` writes multiple formats in one call, with optional visual validation
- `save_and_show` renders a preview (matching the final saved output) and calls `plt.show()`
- `show` displays an existing SVG/PNG for notebooks or reports
- See [API › Save & Export](../api/io.rst) for argument details

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
warnings = dm.validate_figure(fig, checks=('overflow', 'tick_crowding'))
```

When `validate=True` is passed to `save_formats()`, validation runs before
saving. If issues are found, they're printed as warnings — the file is still
saved, but you'll know what to fix.

**Available checks:** overflow detection, text overlap, legend overflow,
tick crowding, and empty axes. Example output:

```text
⚠ OVERFLOW: Text 'ylabel' extends beyond figure bounds by 3.2 pt
⚠ TICK_CROWDING: X-axis has 24 ticks in 3.5 inches (>6 per inch)
```

### Static reference: every warning `validate_figure()` can emit

Plain-text fallback for the live lint simulator — useful when
JavaScript is disabled (AI agents, terminal browsers, search-engine
indexing). Each row is one `check_id` from `dartwork_mpl/validate.py`;
the **Severity** column is the default classification, and the **Fix**
column is the suggestion delivered by
`dm.validate_with_fixes(fig)` / `dm.validate_fixes.get_fix_suggestions`.

| `check_id`           | Severity | What it detects                                    | Suggested fix                                                       |
| -------------------- | -------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| `OVERFLOW`           | warning  | Text or axes content extends past the figure edge  | Increase `dm.auto_layout` padding or reduce label length            |
| `OVERLAP`            | warning  | Two text labels visually overlap                   | Rotate, abbreviate, or split into multiple panels                   |
| `LEGEND_OVERFLOW`    | warning  | Legend extends past axes / figure edge             | Move legend outside via `bbox_to_anchor` or shrink with `ncols`     |
| `TICK_CROWD`         | warning  | Tick labels overlap each other (>6 per inch)       | Reduce tick density (`MaxNLocator`) or rotate labels                |
| `EMPTY_AXES`         | info     | Axes carry no plotted artist                       | Plot data or remove the empty axes via `fig.delaxes(ax)`            |
| `MARGIN_ASYMMETRY`   | info     | Left / right or top / bottom margins differ a lot  | Re-run `dm.auto_layout(fig)`                                        |
| `PIE_LABEL_OFFSET`   | warning  | Pie wedge label sits outside its wedge             | Set `pctdistance = 1.0 - wedge_width / 2`                           |
| `CLIPPED_TEXT`       | warning  | A text artist is clipped at its axes boundary      | Disable clipping (`text.set_clip_on(False)`) or move into figure    |

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
