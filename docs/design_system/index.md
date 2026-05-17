# Design System

dartwork-mpl ships with two reference catalogs of design tokens — colors and
typography — that are pre-wired into every style preset. Browse the full
inventories below, or jump straight to a how-to in the
[Usage Guide](../usage_guide/index.md).

::::{grid} 1
:gutter: 3
:margin: 4 4 0 0

:::{grid-item-card} **Colors**
:link: ../color_system/index
:link-type: doc

Named palette sheets (OpenColor, Tailwind, Material), curated colormaps, and
the perceptually uniform `Color` class for programmatic manipulation.

- Palette catalog (140+ swatches, copy-on-click)
- Colormap catalog (sequential, diverging, cyclic)
- `Color` API — OKLCH-aware mixing, lighten / darken / desaturate
:::

:::{grid-item-card} **Fonts**
:link: ../fonts/index
:link-type: doc

130 publication-grade fonts from 9 families, auto-registered with matplotlib
on import. Drop in by name — no manual `font_manager` plumbing.

- Family catalog with live specimens
- Weight + variant matrix
- Per-preset default-font reference (`Roboto`, `Pretendard`, …)
:::

::::

## Why two catalogs, one nav entry?

Colors and fonts are the two leaf-level token systems every other dartwork-mpl
feature depends on — presets pick from them, examples reference them, the
linter enforces them. Grouping them under a single **Design System** entry
keeps the top navigation under seven items while still surfacing both
catalogs prominently.

```{toctree}
:hidden:
:maxdepth: 1

Colors <../color_system/index>
Fonts <../fonts/index>
```
