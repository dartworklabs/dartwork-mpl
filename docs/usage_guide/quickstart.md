# Quick Start

A minimal end-to-end workflow: apply a style, create a figure, and
export it. Skim this in five minutes — you'll already know enough to
ship a publication-grade plot.

## At-a-glance ROI

| What used to hurt                   | dartwork-mpl                                    |
| ----------------------------------- | ----------------------------------------------- |
| Hand-tuning `figsize` and `dpi`     | `dm.style.use("scientific")` (or pass to `dm.subplots`) |
| `tight_layout` clipping labels      | `dm.simple_layout(fig)` — real optimizer        |
| Reaching for hex codes              | `color="oc.blue5"` (Open Color), `"tw.*"`, `"md.*"`, `"ad.*"`, `"cu.*"`, `"pr.*"` |
| Saving in 3 formats                 | `dm.save_formats(fig, "out", formats=("png", "svg", "pdf"))` |
| Catching margin / overflow problems | `dm.validate_with_fixes(fig)`                   |

Here's a typical matplotlib figure, then the same figure with dartwork-mpl:

::::{tab-set}

:::{tab-item} ✨ With dartwork-mpl

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")  # curated fonts, colors, line weights
fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)

x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="oc.blue5", label="signal", lw=dm.lw(1.5))
ax.set_xticks(np.arange(0, 11, 2))
ax.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax.legend(fontsize=dm.fs(-1))

dm.simple_layout(fig)           # auto-optimize margins
dm.save_and_show(fig, size=720) # preview at 720px wide + save
```

:::

:::{tab-item} 🔧 Vanilla matplotlib

```python
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(2.95, 1.97), dpi=300)

x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="#1c7ed6", label="signal", lw=1.5)
ax.set_xticks(np.arange(0, 11, 2))
ax.set_xlabel("Time [s]", fontsize=7.5)
ax.set_ylabel("Amplitude", fontsize=7.5)
ax.legend(fontsize=6.5)

fig.tight_layout()
fig.savefig("output.png", dpi=300, bbox_inches="tight")
plt.show()
```

:::

::::

:::{figure} images/quickstart_first_figure.svg
:alt: Scientific-style line chart created with dartwork-mpl
:width: 100%

The same chart rendered with `dm.style.use("scientific")` — professional typography, optimized margins, and named colors.
:::

**Drag the slider to compare — same data, different styling:**

```{raw} html
:file: images/compare_slider.html
```

Same data, same plotting logic — the difference is one `dm.style.use()` call, named colors, and `simple_layout`.

**What each dartwork-mpl call does:**

| Call                              | Purpose                                                                            |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| `dm.style.use("scientific")`      | Sets palette, fonts, line weights — see [Styles](styles.md)                        |
| `dm.cm2in(9)`                     | Converts 9 cm to inches for `figsize`                                              |
| `dm.fs(0)`                        | Returns the base font size of the active preset (`fs(2)` = base + 2 pt, and so on) |
| `dm.simple_layout(fig)`           | Auto-optimizes margins (replaces `tight_layout`)                                   |
| `dm.save_and_show(fig, size=720)` | Preview at 720 px wide in the notebook, then call `plt.show()`                     |

## Creating Figures with Styles

dartwork-mpl provides `dm.subplots()` and `dm.figure()` wrappers that apply
styles during figure creation:

```python
# Apply style automatically when creating figure
fig, ax = dm.subplots(style='scientific')

# Stack multiple styles
fig, axes = dm.subplots(2, 2, style=['font-libertine', 'theme-dark'])

# Override style defaults
fig, ax = dm.subplots(style='report', figsize=(10, 6), dpi=150)
```

These functions follow the Zero-Resize Policy: when you specify a style,
figsize and dpi are determined by the style unless explicitly overridden.

**Comparison with standard matplotlib:**

```python
# Standard matplotlib approach
plt.style.use('seaborn')
fig, ax = plt.subplots(figsize=(8, 6), dpi=100)

# dartwork-mpl approach - more concise
fig, ax = dm.subplots(style='scientific', figsize=(8, 6), dpi=100)
```

**Multi-panel figures with automatic styling:**

```python
# Create 2x2 grid with custom ratios
fig, axes = dm.subplots(2, 2,
                       style='scientific',
                       width_ratios=[2, 1],
                       height_ratios=[1, 2])

for ax in axes.flat:
    ax.plot(np.random.randn(100))

dm.simple_layout(fig)
```

## Adding color

dartwork-mpl registers named colors from several design systems. Use them
anywhere matplotlib accepts a color string:

```python
# Named color prefixes
ax.plot(x, y, color="oc.blue5")                    # OpenColor
ax.fill_between(x, y1, y2, color="tw.emerald200")  # Tailwind
ax.bar(categories, values, color="md.red500")      # Material Design
```

**Discover what's available without leaving Python:**

```python
import dartwork_mpl as dm

dm.list_palettes()[:5]   # → ['ad.blue', 'ad.cyan', 'ad.geekblue', ...]
dm.show_palette("oc.blue")  # renders the 9-shade swatch row in Jupyter
dm.plot_colors(ncols=4)     # full library overview, one figure per system
```

See [Colors and Colormaps](colors.md) for the full palette reference,
or open the [interactive palette explorer](../color_system/colors.md)
to click-and-copy color names from your browser.

## Multi-panel layout

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("presentation")

x = np.linspace(0, 10, 100)
fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(8.5)), dpi=300)
gs = fig.add_gridspec(1, 2, wspace=0.3)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

ax1.plot(x, np.sin(x), color="oc.red5")
ax2.plot(x, np.cos(x), color="oc.blue5")

dm.label_axes([ax1, ax2])  # adds (a), (b) panel labels
dm.simple_layout(fig, gs=gs)
```

:::{figure} images/quickstart_multi_panel.svg
:alt: Two-panel layout with label_axes showing sin and cos
:width: 100%
:::

## Saving in multiple formats

```python
dm.save_formats(
    fig,
    "output/my_figure",
    formats=("png", "svg", "pdf"),
    dpi=300,
    validate=True,  # auto-check for overflow, overlap, etc.
)
```

## Catch problems before you export

`validate=True` above runs the same checks as the standalone
`validate_with_fixes` helper, which can also patch the easy issues
in-place:

```python
result = dm.validate_with_fixes(fig)
print(result.report())     # human-readable summary of warnings
# margin_asymmetry → auto-fixed via dm.auto_layout()
# pie_label_offset → auto-adjusted pctdistance
```

Use it in CI to fail a build when a figure breaks; use it locally to
get a one-line health check before you `save_formats`.

## Try the interactive UI

If you'd rather see the effect of every parameter before committing
it to code, dartwork-mpl ships a local web app that wires sliders to
`rcParams` and exports the resulting Python script:

```bash
python -m dartwork_mpl.ui  # opens http://localhost:8765
```

→ [Interactive UI guide](interactive.md)

## Next steps

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} 🎨 Styles and Presets
Choose the right preset for your use case — papers, reports, slides, posters.

→ [Browse presets](styles.md)
:::

:::{grid-item-card} 🌈 Colors and Colormaps
Explore 900+ named palettes and perceptual OKLCH interpolation.

→ [See palettes](colors.md)
:::

:::{grid-item-card} 📐 Layout and Typography
Panel labels, arrows, font scaling, and margin optimization.

→ [Learn layout](layout.md)
:::

:::{grid-item-card} 💾 Save and Validation
Multi-format export + automatic visual quality checks.

→ [Export guide](save_export.md)
:::

:::{grid-item-card} 🛠️ Interactive UI
Tune fonts, line weights, margins with sliders. Export the exact
script that reproduces what you see.

→ [Interactive UI](interactive.md)
:::

:::{grid-item-card} 🔬 Diagnostics & Templates
`dm.plot_colors()` / `plot_colormaps()` / `plot_fonts()` for asset
audit, plus ready-to-use plot templates like `plot_diverging_bar`.

→ [Extras guide](extras.md)
:::

::::
