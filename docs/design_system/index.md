# Overview

The color system has one rule: the name is a family, and `n` picks the form.
Use the same family name as a token, a discrete list, or a colormap depending
on the matplotlib surface you are filling.

:::{tip}
New to color? Start with the beginner [Colors and Colormaps usage
guide](../usage_guide/colors.md) to choose between a token, palette, colormap,
and custom `Color` workflow.
:::

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

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

Use this catalog to color one mark, line, or area with `color="..."`. It shows
the generated `dc.*` ramps, semantic aliases, and the six bundled third-party
design systems.
:::

:::{grid-item-card} **Palettes**
:link: ../color_system/palettes
:link-type: doc

Use this catalog to give separate series or categories distinct colors. It
shows Octave, curated qualitative sets, family samples, and
diverging/sequential lists for `dm.set_colors()` and
`dm.colors(name, n=...)`.
:::

:::{grid-item-card} **Colormaps**
:link: ../color_system/colormaps
:link-type: doc

Use this catalog to turn numeric values into colors with `cmap=`. It contains
43 perceptually-designed colormaps, plus 13 qualitative colormaps for class
data: 56 family records in all. Continuous construction is topology-specific:
single-hue, continuous-gray, multi-hue, and twilight paths use the applicable
ΔEOK resampling, while diverging maps and `hue` use their own symmetric-arm or
equal-angle rules. Explicit checks then confirm the required modeled-relative-Y
direction or shape rather than claiming perfect uniformity; `_r` reverses
control direction.
:::

:::{grid-item-card} **Color class**
:link: ../color_system/color-class
:link-type: doc

Use this optional guide when you need to create or adjust a color yourself.
The programmatic color engine can construct, convert, modify, interpolate, and
register custom colormaps in OKLab / OKLCH.
:::

:::{grid-item-card} **Fonts**
:link: ../fonts/index
:link-type: doc

20 publication-ready fonts (262 files across 22 file groups), auto-registered
with matplotlib and wired into the style presets.
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
