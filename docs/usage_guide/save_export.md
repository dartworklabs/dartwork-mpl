# Save and Validation

## Save and preview

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)
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
- See [API › Save & Export](../api/io.rst) for argument details

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
tick crowding, and empty axes. Example output:

```text
⚠ OVERFLOW: Text 'ylabel' extends beyond figure bounds by 3.2 pt
⚠ TICK_CROWDING: X-axis has 24 ticks in 3.5 inches (>6 per inch)
```

See [API › Visual Validation](../api/validate.rst)
for details.
