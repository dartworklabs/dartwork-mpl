# Extended Plots & Diagnostics

## Extended plots (`templates`)

dartwork-mpl ships ready-to-use plot templates in `dartwork_mpl.templates`
for chart types that are tedious to build from scratch but show up
constantly in real reports:

```python
import numpy as np
from dartwork_mpl.templates import plot_diverging_bar

fig, ax = plot_diverging_bar(
    labels=["Accuracy", "Recall", "F1-Score"],
    neg_values=np.array([-30, -55, -10]),
    pos_values=np.array([60, 20, 45]),
    neg_label="Decrease",
    pos_label="Increase",
)
```

:::{figure} images/save_diverging_bar.svg
:alt: Diverging bar chart from templates module
:width: 100%
:::

The `templates` module is intentionally narrow — it grows only when a
chart pattern repeats across enough projects to deserve a curated
default. See [API › Extended Plots](../api/templates.rst) for the full
parameter list.

## Diagnostics & previews (`diagnostics`)

Use these to audit what your environment has registered before you commit
to a chart.

```python
import dartwork_mpl as dm

# 1. What colour families are available?
[f["name"] for f in dm.list_colors("qualitative")]

# 2. Are my fonts registered? (sanity-check Korean/CJK installs)
dm.plot_fonts(font_size=11, ncols=3)
```

:::{note}
**Looking for the full palette?** The interactive, copy-on-click swatch
grid (140+ OpenColor / Tailwind / Material colors with search) lives on
the dedicated [Color System → Palette Catalog](../color_system/colors.md)
page. The diagnostic helpers above are aimed at *programmatic* sanity
checks; the catalog page is the place to browse.
:::

:::{tip}
**Lightweight discovery.** If you only need a list (not a full preview figure),
use `dm.list_colors()`; if you need the actual colors, call
`dm.colors("blue", n=5)` or `dm.colors("aurora")`.
:::

<!-- snippet: no-run -->
```python
>>> [record["name"] for record in dm.list_colors()[:5]]
['amber', 'blue', 'cobalt', 'coral', 'cyan']

>>> dm.colors("aurora").name
'dc.aurora'

```

See [API › Visualization Tools](../api/visualization.rst) for full
parameter reference of the four diagnostic helpers.

## See also

- **Next →** [Interactive UI](interactive.md) — launch a local web app to tweak
  parameters with sliders, export plots, and generate reproducible scripts
- [API › Extended Plots](../api/templates.rst) for all `templates` function signatures
- [API › Visualization Tools](../api/visualization.rst) for diagnostic plot functions
