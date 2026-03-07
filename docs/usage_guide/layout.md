# Layout, Typography, and Annotations

## Layout optimization

For most figures, `simple_layout(fig)` is all you need — it automatically
optimizes margins so labels and titles don't clip or overlap:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(12), dm.cm2in(8)), dpi=300)
ax.plot(np.linspace(0, 10, 100), np.sin(np.linspace(0, 10, 100)), color="oc.blue6")
ax.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax.set_ylabel("Response", fontsize=dm.fs(0))

dm.simple_layout(fig)  # auto-optimizes margins — replaces tight_layout()
```

**Try it — drag the sliders to see how figure dimensions map onto an A4 page:**

```{raw} html
:file: images/ruler_widget.html
```

### Multi-panel figures

For multi-panel layouts, use GridSpec and pass it to `simple_layout`:

```python
fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25)
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]

for ax in axes:
    ax.plot(np.linspace(0, 1, 40), np.random.rand(40), color="oc.blue6", lw=0.8)

dm.label_axes(axes)                    # adds (a), (b), (c), (d) panel labels
dm.set_decimal(axes[0], xn=2, yn=1)    # format tick labels to fixed decimals

# Pass gs so simple_layout respects your GridSpec spacing
dm.simple_layout(fig, gs=gs)
```

:::{figure} images/layout_gridspec.svg
:alt: 2×2 GridSpec layout with panel labels and decimal formatting
:width: 100%
:::

> **Tip:** You generally don't need to set explicit `left`, `right`, `top`,
> `bottom` values on GridSpec — `simple_layout` finds optimal margins
> automatically. Only add manual margins when you need fine positional control
> (e.g., making room for a colorbar or external legend).

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

:::{figure} images/layout_typography.svg
:alt: Typography demo with fs() and fw() font scaling helpers
:width: 100%
:::

**Scaling helpers:**

| Helper  | What it does                                                                  |
| ------- | ----------------------------------------------------------------------------- |
| `fs(n)` | Font size = base size + `n` points. `fs(0)` = base, `fs(2)` = 2pt larger      |
| `fw(n)` | Weight = base weight + `n` × 100. `fw(0)` = Light (300), `fw(4)` = Bold (700) |
| `lw(n)` | Line width relative to `lines.linewidth`. `lw(0)` = default                   |

See [Font Families](../fonts/families) for the full font catalog and
[Font Utilities](../fonts/utilities) for detailed usage.
