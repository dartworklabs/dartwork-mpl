# Design System

dartwork-mpl ships with four reference catalogs of design tokens —
palettes, colormaps, the OKLCH-aware `Color` class, and typography —
pre-wired into every style preset. Pick the one you need:

::::{grid} 2
:gutter: 3
:margin: 4 4 0 0

:::{grid-item-card} **Palettes**
:link: ../color_system/colors
:link-type: doc

Named palette sheets for the curated `dc.*` family plus six third-party
design systems (OpenColor, Tailwind, Material, Ant, Chakra, Primer).

- 140+ swatches, copy-on-click
- Full sheets, no hub click-through
- Drop names anywhere matplotlib accepts a color
- Interactive picker + `set_cycle`/`get_palette` → [Categorical palettes](../color_system/categorical-palettes)
:::

:::{grid-item-card} **Colormaps**
:link: ../color_system/colormaps
:link-type: doc

56 OKLCH-designed colormaps across single-hue, multi-hue, diverging,
cyclical, and categorical families.

- Live explorer — tab to category, toggle Color / Mono
- Guaranteed monotonic lightness (greyscale-safe)
- Sequential, diverging, cyclic, categorical
:::

:::{grid-item-card} **Color Space**
:link: ../color_system/space
:link-type: doc

The `Color` class for perceptually uniform manipulation in OKLab /
OKLCH space — adjust hue, saturation, and lightness predictably.

- Lighten / darken / desaturate
- Smooth custom gradients in OKLCH
- Cross-color-space conversion utilities
:::

:::{grid-item-card} **Fonts**
:link: ../fonts/index
:link-type: doc

204 publication-grade fonts from 16 families, auto-registered with
matplotlib on import. Drop in by name — no `font_manager` plumbing.

- Family catalog with live specimens
- Weight + variant matrix
- Per-preset default-font reference (`Roboto`, `Pretendard`, …)
:::

::::

## Why one nav entry for four catalogs?

Palettes, colormaps, the color space, and fonts are the four leaf-level
token systems every other dartwork-mpl feature depends on — presets
pick from them, examples reference them, the linter enforces them.
Grouping them under a single **Design System** entry keeps the top
navigation under seven items while still surfacing each catalog as a
direct sidebar link.

```{toctree}
:hidden:
:maxdepth: 1

Palettes <../color_system/colors>
Categorical palettes <../color_system/categorical-palettes>
Colormaps <../color_system/colormaps>
Color Space <../color_system/space>
Fonts <../fonts/index>
```
