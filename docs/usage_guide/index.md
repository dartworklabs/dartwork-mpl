# Usage Guide

dartwork-mpl bundles stylistic presets, curated colors/colormaps, and
layout/font helpers so you get **predictable results** fast.

```{raw} html
:file: ../_static/evolution_widget.html
```

## Choosing the right tools

### Which preset?

| Your context | Preset | Why |
|-------------|--------|-----|
| Academic paper / journal | `scientific` | Compact fonts (7.5 pt), all 4 spines, fits 3.5" column |
| Business report / memo | `report` | Clean look, no top/right spines, 8 pt fonts |
| Infographic / editorial | `minimal` | Tufte-style, no spines/ticks, data-ink focus |
| PowerPoint / Keynote | `presentation` | Large fonts (10.5 pt), readable when projected |
| Conference poster | `poster` | Largest fonts (12 pt), thick lines, 1-2m reading distance |
| Web docs / blog | `web` | Screen-optimized 11 pt, clean for HTML/Jupyter |
| Dark Jupyter / dark slides | `dark` | Inverted colors on `#1e1e1e` background |
| **Any of the above + Korean** | Add `-kr` suffix | Swaps to Paperlogy/Pretendard fonts |

### Which layout function?

| Situation | Function | Notes |
|-----------|----------|-------|
| Most figures (default) | `simple_layout(fig)` | Content-aware margin pass — call after data is plotted |
| Multi-panel with GridSpec | `simple_layout(fig, gs=gs)` | Pass the parent `GridSpec` so margins are computed against it |
| Need exact margin control | `simple_layout(fig, margin="5mm")` | Or per-side `ml="3mm", mr="3mm", mt="2mm", mb="6mm"` |

### Which color palette?

| Style | Prefix | Best for |
|-------|--------|----------|
| dartwork curated | `dc.*` | **Recommended starting point** — 16 v5 families, 10 perceptual steps each, CVD-screened |
| Open Color | `oc.*` | General purpose, well-balanced |
| Tailwind CSS | `tw.*` | Web-style designs, wider shade range (50–950) |
| Material Design | `md.*` | Google-style, vibrant |
| Ant Design | `ad.*` | Enterprise UI aesthetics |
| Chakra UI | `cu.*` | Modern web app colors |
| Primer | `pr.*` | GitHub-style, subtle |

## Typical workflow

::::{grid} 1
:gutter: 3

:::{grid-item-card} **1. Pick a style**
`dm.style.use("scientific")` sets fonts, line weights, spines, and tick
styling in one call — 7 presets cover papers, reports, slides, posters,
web, and dark mode. No manual `rcParams` guessing.

→ [Styles and Presets](styles.md)
:::

:::{grid-item-card} **2. Add color**
Use named colors like `"dc.teal2"` or `"tw.emerald500"` anywhere matplotlib
accepts a color string. 900+ curated swatches from 6 design systems,
plus perceptual OKLCH interpolation.

→ [Colors and Colormaps](colors.md)
:::

:::{grid-item-card} **3. Layout & annotate**
`dm.simple_layout(fig)` walks every visible artist on every axes,
finds the union extent, and snaps the GridSpec edges so the content
sits at the requested margin from the figure edge. Pass `gs=gs` for
multi-panel layouts. `dm.label_axes()` adds panel labels automatically.

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
Recipes <recipes>
Save and Validation <save_export>
Global Defaults (dm.config) <config>
Extended Plots & Diagnostics <extras>
Interactive UI <interactive>
Tutorials <tutorials>
```

:::{tip}
**Where do assets live?** Style files are in `asset/mplstyle/`, colors in
`asset/color/`, and fonts in `asset/font/`. Physical-width helpers live
in `dm.units` (`dm.cm`, `dm.inch`, `dm.mm`, plus the academic-column
sugar `dm.col1` / `dm.col2`). See [Design Philosophy](../philosophy/index)
for the architecture behind these choices.
:::

:::{image} images/evolution_step1.svg
:class: d-none
:::
:::{image} images/evolution_step2.svg
:class: d-none
:::
:::{image} images/evolution_step3.svg
:class: d-none
:::
:::{image} images/evolution_step4.svg
:class: d-none
:::
