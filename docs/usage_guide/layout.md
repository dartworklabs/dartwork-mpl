# Layout and Typography

## Layout optimization

For most figures, `simple_layout(fig)` is all you need — it automatically
optimizes margins so labels and titles don't clip or overlap:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
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
fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(12)), dpi=300)
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

### Content-Aware Layout with `auto_layout`

For figures with complex text elements that might overflow, `auto_layout()` provides
an intelligent alternative that automatically detects and fixes overflow:

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)))
ax.plot(np.linspace(0, 10, 100), np.sin(np.linspace(0, 10, 100)))
ax.set_ylabel("Very Long Label That Might\nOverflow the Figure Bounds")
ax.set_title("Complex Multi-Line Title\nWith Potential Overflow", fontsize=dm.fs(2))

# Auto-adjusts margins to prevent any overflow
dm.auto_layout(fig, padding=0.08, max_iter=5, verbose=True)
```

**How it works:**
1. Applies initial layout with minimal margins
2. Measures actual text overflow on all four sides
3. Increases margins only where needed
4. Repeats until convergence (typically 1-3 iterations)

This is especially useful for:
- Axes with very long y-axis labels
- Multi-line titles that extend beyond figure bounds
- Figures with many annotations
- Automatically generated charts where label length is unknown

### Responsive Margins with `set_xmargin` and `set_ymargin`

Control axis data margins responsively based on data range:

```python
# Add 10% margin to x-axis data range
dm.set_xmargin(ax, margin=0.1)

# Add different margins for y-axis
dm.set_ymargin(ax, margin=0.05)

# Useful for:
# - Preventing data from touching axis edges
# - Creating visual breathing room
# - Ensuring markers aren't clipped at boundaries
```

### Which Layout Function to Use?

| Scenario | Recommended Function | Why |
|----------|---------------------|-----|
| Simple plots with standard labels | `simple_layout()` | Fast, consistent margins |
| Complex multi-line titles/labels | `auto_layout()` | Automatic overflow detection |
| GridSpec with spacing control | `simple_layout(fig, gs=gs)` | Respects hspace/wspace |
| Need exact margin control | `simple_layout(margins=(...))` | Precise inch-based margins |
| Unknown label lengths (AI-generated) | `auto_layout()` | Adapts to content |
| Debugging layout issues | `auto_layout(verbose=True)` | Shows iteration diagnostics |

### `simple_layout` vs `tight_layout`

Simple layouts look fine with either method. The real difference shows up when
figures get more complex — multi-panel grids, long axis labels, colorbars, and
titles all competing for space.

**Interactive visualizer — see how dartwork-mpl calculates margins dynamically:**

```{raw} html
:file: images/layout_debugger.html
```

Below is the **same figure** — a two-panel layout with a multi-line y-label and
a colorbar — rendered with each approach:

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} `tight_layout()`
:class-card: sd-border-secondary
![tight_layout result](images/layout_tight.svg)
:::

:::{grid-item-card} `simple_layout()`
:class-card: sd-border-primary
![simple_layout result](images/layout_simple.svg)
:::

::::

**What's different?**

`tight_layout()` calculates padding heuristically — it tries to prevent
overlap but doesn't guarantee uniform margins or optimal use of space. When
panels have **different label lengths** (e.g., a multi-line ylabel vs. a
short one), or when a **colorbar** shifts the effective axes width, the
heuristic can produce lopsided spacing or wasted whitespace.

`simple_layout()` uses **scipy's L-BFGS-B optimizer** to minimize the gap
between the actual tight bounding boxes and target margins you specify in
inches. This means:

- **Uniform margins** — every figure edge gets exactly the space you request
- **Colorbar-aware** — the optimizer sees the full bounding box, including
  colorbars and legends, not just the axes
- **GridSpec-native** — pass `gs=gs` and it respects your `hspace`/`wspace`
  while only adjusting outer margins

**Key layout functions:**

| Function                      | What it solves                                                |
| ----------------------------- | ------------------------------------------------------------- |
| `simple_layout(fig, gs=gs)`   | Optimizes outer margins via scipy — replaces `tight_layout()` |
| `auto_layout(fig)`            | Content-aware layout that prevents text overflow              |
| `set_xmargin(ax, margin)`     | Sets responsive x-axis margins based on data range            |
| `set_ymargin(ax, margin)`     | Sets responsive y-axis margins based on data range            |
| `label_axes(axes)`            | Adds (a), (b), (c) labels with auto-positioning for ylabels   |
| `arrow_axis(ax, 'x', 'Cost')` | Creates `Low ◄── Cost ──► High` bidirectional annotations     |
| `set_decimal(ax, xn, yn)`     | Fixes tick decimal places for publication-ready labels        |
| `make_offset(x, y, fig)`      | Creates point-based offsets for precise text positioning      |
| `get_bounding_box(boxes)`     | Merges multiple axes bounding boxes into one                  |

## Annotation & Formatting

Dartwork-mpl includes several helpers that automate tedious formatting tasks.

### Auto-aligned panel labels (`label_axes`)

Manually positioning `(a)`, `(b)`, `(c)` labels across panels with different y-axis label lengths often results in misaligned text. `dm.label_axes(axes)` calculates the bounding boxes of your y-labels and perfectly aligns the panel labels to the leftmost edge.

**Interactive visualizer — drag the slider to compare:**

```{raw} html
:file: images/label_axes_slider.html
```

### Consistent tick decimals (`set_decimal`)

Raw matplotlib ticks can sometimes mix integers and floats (e.g. `0.5`, `1`, `1.5`), which looks unprofessional. `dm.set_decimal()` forces consistent decimal places for publication-ready formatting.

```{raw} html
:file: images/set_decimal_slider.html
```

### Bidirectional arrow axes (`arrow_axis`)

For conceptual or qualitative plots (like "Risk vs Return"), drawing bidirectional label axes manually is surprisingly difficult in matplotlib. `dm.arrow_axis()` handles the positioning, offsets, and arrows automatically.

:::{figure} images/arrow_axis_example.svg
:alt: Arrow axis example showing Risk vs Expected Return
:width: 100%
:::

## Typography

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific-kr")  # English/Korean fonts set together

fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)
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

See [Font Families](../fonts/families.md) for the full font catalog and
[Font Utilities](../fonts/utilities.md) for detailed usage.

## See also

- **Next →** [Save and Validation](save_export.md) — multi-format export and automatic visual quality checks
- [API › Layout Utilities](../api/layout.rst) for all layout helper functions and arguments
- [Colors and Colormaps](colors.md) for named colors and gradients

:::{image} images/label_axes_vanilla.svg
:class: d-none
:::
:::{image} images/label_axes_dm.svg
:class: d-none
:::
:::{image} images/set_decimal_vanilla.svg
:class: d-none
:::
:::{image} images/set_decimal_dm.svg
:class: d-none
:::
