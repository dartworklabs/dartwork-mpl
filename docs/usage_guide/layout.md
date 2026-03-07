# Layout, Typography, and Annotations

## Layout optimization

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np
dm.style.use("scientific")

fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.9, bottom=0.12,
                      hspace=0.35, wspace=0.25)
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
for ax in axes:
    ax.plot(np.linspace(0, 1, 40), np.random.rand(40), color="oc.blue6", lw=0.8)

# Panel labels (a, b, c, d)
dm.label_axes(axes)

# Decimal formatting
dm.set_decimal(axes[0], xn=2, yn=1)

# Layout optimization
dm.simple_layout(fig, gs=gs, margins=(0.05, 0.08, 0.06, 0.08))
```

**Key functions:**

- [`simple_layout(fig, gs=gs)`](../api/layout) — respects your GridSpec margins
- [`label_axes(axes)`](../api/layout) — adds standardized panel labels with auto-positioning
- [`arrow_axis(ax, 'x', 'Cost')`](../api/layout) — creates `Low ◄── Cost ──► High` annotations
- [`make_offset`](../api/layout) — gives consistent point-based text offsets
- [`set_decimal(ax, xn, yn)`](../api/layout) — formats tick labels neatly
- [`get_bounding_box`](../api/layout) — merges multiple axes bounds

## Typography

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use("scientific-kr")  # English/Korean fonts set together

fig, ax = plt.subplots(figsize=(dm.cm2in(10), dm.cm2in(6)), dpi=300)
ax.plot([0, 1, 2], [0, 1, 0.4], color="oc.green6", lw=dm.lw(0.5))
ax.set_title("Experiment result", fontsize=dm.fs(2), fontweight=dm.fw(1))
ax.set_xlabel("Time", fontsize=dm.fs(0))
ax.set_ylabel("Response", fontsize=dm.fs(0))
dm.simple_layout(fig)

# Preview bundled fonts
dm.plot_fonts(ncols=4, font_size=12)
```

**Scaling helpers:**

- `fs(delta)`: font size relative to the active preset
- `fw(delta)`: weight relative to the preset default
- `lw(delta)`: line width relative to `lines.linewidth`

See [Font Families](../fonts/families) for the full font catalog and
[Font Utilities](../fonts/utilities) for detailed usage.
