# Save, Export, and Validation

## Save and preview

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(11), dm.cm2in(7)), dpi=300)
ax.plot(np.arange(50), np.cumsum(np.random.randn(50)) + 20, color="oc.blue6")
dm.simple_layout(fig)

dm.save_formats(
    fig,
    "output/experiment",
    formats=("png", "svg", "pdf"),
    dpi=300,
    bbox_inches="tight",
    validate=True,   # runs visual checks before saving (see below)
)
dm.save_and_show(fig, size=720)  # preview at 720px wide + plt.show()
dm.show("output/forecast.svg", size=540)  # display a saved file in notebooks
```

:::{figure} images/save_scientific.svg
:alt: Scientific-style line chart saved with save_formats
:width: 100%
:::

**Key points:**

- `save_formats` writes multiple formats in one call, with optional visual validation
- `save_and_show` renders a preview (matching the final saved output) and calls `plt.show()`
- `show` displays an existing SVG/PNG for notebooks or reports
- See [API › Save & Export](../api/io) for argument details

## Visual validation

Detect common rendering issues automatically — especially useful in
AI agent pipelines where visual inspection is not available:

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
tick crowding, and empty axes. See [API › Visual Validation](../api/validate)
for details.

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

See [API › Extended Plots](../api/xplot) for the full parameter list.

## Interactive viewer

dartwork-mpl includes an optional interactive viewer powered by FastAPI for
rapid parameter exploration. This is useful when you want to tweak chart
parameters with sliders in a browser instead of re-running code.

> **Requires the `ui` extra:** `uv add "dartwork-mpl[ui]"` (installs FastAPI
> and Pydantic).

```python
import matplotlib.pyplot as plt
import numpy as np
from dartwork_mpl.ui import ParamModel, run
from pydantic import Field

class Params(ParamModel):
    n: int = Field(default=100, ge=10, le=1000)
    alpha: float = Field(default=0.5, ge=0, le=1)

def scatter(params: Params):
    fig, ax = plt.subplots()
    ax.scatter(range(params.n), np.random.randn(params.n), alpha=params.alpha)
    return fig

run(scatter)  # opens browser at http://127.0.0.1:8501
```

See [API › Interactive Viewer](../api/ui) for details.

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

See [API › Visualization Tools](../api/visualization) for full details.
