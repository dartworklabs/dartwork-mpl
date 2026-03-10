# Usage Guide

dartwork-mpl bundles stylistic presets, curated colors/colormaps, and
layout/font helpers so you get **predictable results** fast.

## Typical workflow

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} **1. Pick a style**
`dm.style.use("scientific")` sets fonts, line weights, spines, and tick
styling in one call — 7 presets cover papers, reports, slides, posters,
web, and dark mode. No manual `rcParams` guessing.

→ [Styles and Presets](styles.md)
:::

:::{grid-item-card} **2. Add color**
Use named colors like `"oc.blue5"` or `"tw.emerald500"` anywhere matplotlib
accepts a color string. 900+ curated swatches from 6 design systems,
plus perceptual OKLCH interpolation.

→ [Colors and Colormaps](colors.md)
:::

:::{grid-item-card} **3. Layout & annotate**
`dm.simple_layout(fig)` optimizes margins via L-BFGS-B — uniform spacing
even with colorbars and long labels. `dm.label_axes()` adds panel labels
automatically.

→ [Layout and Typography](layout.md)
:::

:::{grid-item-card} **4. Export**
`dm.save_formats(fig, "output/fig", formats=("png", "svg"))` writes
multiple formats at once. Add `validate=True` to auto-detect overflow,
overlap, and crowding before saving.

→ [Save and Validation](save_export.md)
:::

:::{grid-item-card} **5. Interactive UI**
Launch a local web UI to tweak parameters with sliders, download plots,
and generate reproducible Python scripts on the fly.

→ [Interactive UI](interactive.md)
:::

::::

```{toctree}
:maxdepth: 1
:titlesonly:

Quick Start <quickstart>
Styles and Presets <styles>
Colors and Colormaps <colors>
Layout and Typography <layout>
Save and Validation <save_export>
Extended Plots & Diagnostics <extras>
Interactive UI <interactive>
```

:::{tip}
**Where do assets live?** Style files are in `asset/mplstyle/`, colors in
`asset/color/`, fonts in `asset/font/`, and figure constants in
[`dm.SW`, `dm.DW`](../api/constant.rst). See [Design Philosophy](../philosophy/index)
for the architecture behind these choices.
:::
