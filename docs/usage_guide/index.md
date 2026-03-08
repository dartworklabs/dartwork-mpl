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
accepts a color string. 1,500+ curated swatches from 6 design systems,
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

::::

```{toctree}
:maxdepth: 1
:titlesonly:

Quick Start <quickstart>
Styles and Presets <styles>
Colors and Colormaps <colors>
Layout and Typography <layout>
Save and Validation <save_export>
Extra Utilities <extras>
```

## Explore more

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} 🖼️ Examples Gallery
Finished plots by category — copy the code and adapt.

→ [Browse examples](../examples_gallery/index)
:::

:::{grid-item-card} 🎨 Color System
Full palette sheets, colormap panels, and the OKLCH color-space guide.

→ [Explore colors](../color_system/index)
:::

:::{grid-item-card} 🔤 Fonts
Bundled typefaces and weight references.

→ [See fonts](../fonts/index)
:::

:::{grid-item-card} 📖 API Reference
Detailed call signatures for every module.

→ [Read the API](../api/index)
:::

::::

:::{admonition} Under the hood
:class: dropdown

For contributors or those curious about where assets are stored:

| Category         | Location                                                   |
| ---------------- | ---------------------------------------------------------- |
| Styles           | `asset/mplstyle/*.mplstyle`                                |
| Colors/colormaps | `asset/color/*.txt`                                        |
| Fonts            | `asset/font/*` (auto-registered on import)                 |
| Icons            | `asset/icon/*`                                             |
| Prompts          | `asset/prompt/*.md`                                        |
| Constants        | `dm.SW`, `dm.DW` — [Figure Constants](../api/constant.rst) |

:::
