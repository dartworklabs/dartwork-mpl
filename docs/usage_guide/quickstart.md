# Quick Start

A minimal end-to-end workflow: apply a style, create a figure, and export it.

## First figure

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")  # preset keys: see Styles and Presets
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)

x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="oc.blue5", label="signal")
ax.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax.legend(fontsize=dm.fs(-1))

dm.simple_layout(fig)           # optimize margins
dm.save_and_show(fig, size=720) # preview + save
```

**What each call does:**

| Call                         | Purpose                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `dm.style.use("scientific")` | Sets palette, fonts, line weights — see [Styles](styles) |
| `dm.cm2in(9)`                | Converts 9 cm to inches for `figsize`                    |
| `dm.fs(0)`                   | Base font size relative to the active preset             |
| `dm.simple_layout(fig)`      | Margin optimization (replaces `tight_layout`)            |
| `dm.save_and_show(fig)`      | Preview + save in one step                               |

## Adding color

dartwork-mpl registers named colors from several design systems. Use them
anywhere matplotlib accepts a color string:

```python
# Named color prefixes
ax.plot(x, y, color="oc.blue5")       # OpenColor
ax.fill_between(x, y1, y2, color="tw.emerald200")  # Tailwind
ax.bar(categories, values, color="md.red500")       # Material Design
```

See [Colors and Colormaps](colors) for the full palette reference.

## Multi-panel layout

```python
fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
gs = fig.add_gridspec(1, 2, wspace=0.3)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

ax1.plot(x, np.sin(x), color="oc.red5")
ax2.plot(x, np.cos(x), color="oc.blue5")

dm.label_axes([ax1, ax2])  # adds (a), (b) panel labels
dm.simple_layout(fig, gs=gs)
```

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

## Next steps

- **[Styles and Presets](styles)** — choose the right preset for your use case
- **[Colors and Colormaps](colors)** — browse all named palettes
- **[Layout and Typography](layout)** — panel labels, arrows, font scaling
- **[Save, Export, and Validation](save_export)** — multi-format export + visual checks
