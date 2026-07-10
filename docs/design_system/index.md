# Overview

The color system has one rule: the name is a family, and `n` picks the form.
Use the same family name as a token, a discrete list, or a colormap depending
on the matplotlib surface you are filling.

| you want to | you write | catalog |
|---|---|---|
| color one thing | `color="dc.blue6"` | [Colors](../color_system/colors.md) |
| color N series | `dm.set_colors("vivid")` / `dm.colors("vivid", n=6)` | [Palettes](../color_system/palettes.md) |
| color a field | `cmap="dc.aurora"` | [Colormaps](../color_system/colormaps.md) |
| build your own | `dm.color()`, `dm.oklch()`, `dm.cspace()` | [Color class](../color_system/color-class.md) |

The catalog has five kinds: sequential, multi-hue, diverging, cyclic, and
qualitative. Most families have a continuous form for `cmap=` and a designed
discrete form for `dm.colors(name, n=...)`; qualitative families are discrete
sets that also register as qualitative colormaps. `dm.list_colors()` returns
the 56 family records that make those forms explicit.

::::{grid} 1 1 2 3
:gutter: 3
:margin: 4 4 0 0

:::{grid-item-card} **Colors**
:link: ../color_system/colors
:link-type: doc

Static token sheets for `color="..."`: the generated `dc.*` ramps, semantic
aliases, and the six bundled third-party design systems.
:::

:::{grid-item-card} **Palettes**
:link: ../color_system/palettes
:link-type: doc

Discrete forms for series color: Octave, curated qualitative sets, family
samples, and diverging/sequential lists through `dm.set_colors()` and
`dm.colors(name, n=...)`.
:::

:::{grid-item-card} **Colormaps**
:link: ../color_system/colormaps
:link-type: doc

43 perceptually-designed colormaps for `cmap=`, plus qualitative colormaps
for class data and `_r` reverses for direction control.
:::

:::{grid-item-card} **Color class**
:link: ../color_system/color-class
:link-type: doc

The programmatic color engine: construct, convert, modify, interpolate, and
register custom colormaps in OKLab / OKLCH.
:::

:::{grid-item-card} **Fonts**
:link: ../fonts/index
:link-type: doc

230 publication-grade fonts from 20 families, auto-registered with matplotlib
and wired into the style presets.
:::

:::{grid-item-card} **Design rationale**
:link: ../color_system/design-rationale
:link-type: doc

The evidence page for the design system: perceptual color theory today, with
typography rationale reserved for the fonts overhaul.
:::

::::

```{toctree}
:hidden:
:maxdepth: 1

Overview <self>
Colors <../color_system/colors>
Palettes <../color_system/palettes>
Colormaps <../color_system/colormaps>
Color class <../color_system/color-class>
Fonts <../fonts/index>
Design rationale <../color_system/design-rationale>
```
