# Save, Export, and Validation

## Save and preview

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np
dm.style.use("investment")

fig, ax = plt.subplots(figsize=(dm.cm2in(11), dm.cm2in(7)), dpi=300)
ax.plot(np.arange(50), np.cumsum(np.random.randn(50)) + 20, color="oc.blue6")
dm.simple_layout(fig)

dm.save_formats(
    fig,
    "output/forecast",
    formats=("png", "svg", "pdf"),
    dpi=300,
    bbox_inches="tight",
    validate=True,   # runs validate_figure() before saving
)
dm.save_and_show(fig, size=720)  # preview + plt.show()
dm.show("output/forecast.svg", size=540)
```

**Key points:**

- `save_formats` writes multiple formats in one call, with optional visual validation
- `save_and_show` emits a small preview (PNG/SVG) and shows the figure
- `show` reuses an existing SVG for notebooks or reports
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

# Automatically called by save_formats() (validate=True by default)
```

Checks include: overflow detection, text overlap, legend overflow,
tick crowding, and empty axes. See [API › Visual Validation](../api/validate)
for details.

## Extended plots

dartwork-mpl provides ready-to-use plot templates in `dartwork_mpl.xplot`:

```python
from dartwork_mpl.xplot import plot_diverging_bar

fig, ax = plot_diverging_bar(
    categories=['Revenue', 'Costs', 'Profit'],
    negatives=[-30, -55, -10],
    positives=[60, 20, 45],
    neg_label='Decrease',
    pos_label='Increase',
)
```

See [API › Extended Plots](../api/xplot) for the full parameter list.

## Interactive viewer

For rapid parameter exploration, use the FastAPI-powered interactive viewer:

```python
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

Install the optional `ui` extra: `uv add "dartwork-mpl[ui]"`.
See [API › Interactive Viewer](../api/ui) for details.

## Diagnostics & previews

```python
import dartwork_mpl as dm

dm.plot_colors(ncols=5, sort_colors=True)          # inspect each color library
dm.plot_colormaps(group_by_type=True, ncols=4)     # compare sequential/diverging sets
dm.plot_fonts(font_size=11, ncols=3)               # audit bundled fonts
```

See [API › Visualization Tools](../api/visualization) for full details.
