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

Named palette sheets for the generative `dc.*` families plus six third-party
design systems (OpenColor, Tailwind, Material, Ant, Chakra, Primer).

- 300+ swatches, copy-on-click
- 20 perceptual families + 11 curated qualitative sets
- Drop names anywhere matplotlib accepts a color
- Interactive picker + `dm.set_colors`/`dm.colors` → [Categorical palettes](../color_system/categorical-palettes)
:::

:::{grid-item-card} **Colormaps**
:link: ../color_system/colormaps
:link-type: doc

43 perceptually-designed colormaps across single-hue, multi-hue,
diverging, and cyclic families.

- Live explorer — tab to category, toggle Color / Mono
- Guaranteed monotonic lightness (greyscale-safe)
- The generation axioms behind them → [Color system design](../color_system/design)
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

206 publication-grade fonts from 18 families, auto-registered with
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
Color system design <../color_system/design>
Color Space <../color_system/space>
Fonts <../fonts/index>
```
