# Extended Plots & Tools

## Extended plots

dartwork-mpl provides ready-to-use plot templates in `dartwork_mpl.xplot`:

```python
from dartwork_mpl.xplot import plot_diverging_bar

fig, ax = plot_diverging_bar(
    categories=['Accuracy', 'Recall', 'F1-Score'],
    negatives=[-30, -55, -10],
    positives=[60, 20, 45],
    neg_label='Decrease',
    pos_label='Increase',
)
```

:::{figure} images/save_diverging_bar.svg
:alt: Diverging bar chart from xplot module
:width: 100%
:::

See [API › Extended Plots](../api/xplot.rst) for the full parameter list.

## Interactive viewer

dartwork-mpl includes a powerful interactive viewer powered by FastAPI for rapid parameter exploration, real-time plotting, and automated reproducible code generation.

See the dedicated [Interactive UI Guide](interactive.md) or the [API Reference](../api/ui.rst) for full details.

## Diagnostics & previews

```python
import dartwork_mpl as dm

dm.plot_colors(ncols=5, sort_colors=True)          # inspect each color library
dm.plot_colormaps(group_by_type=True, ncols=4)     # compare sequential/diverging sets
dm.plot_fonts(font_size=11, ncols=3)               # audit bundled fonts
```

:::{figure} images/save_diagnostics.svg
:alt: OpenColor palette preview from plot_colors diagnostic tool
:width: 100%
:::

See [API › Visualization Tools](../api/visualization.rst) for full details.
