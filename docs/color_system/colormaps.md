# Colormaps

The colormap surface is the v5 catalog: **43 continuous colormaps**, their
`_r` reverses, and **2 qualitative cycle maps** (`dc.octave`,
`dc.octave_print`) registered for `cmap=` interfaces —
`dm.list_colormaps()` returns the 45 non-reversed names. Every map is generated
by the same perceptual recipe as the `dc.*` palette — designed on CIELAB L\*
and OKLCH, equalized in OKLab ΔE, and checked against hard gates before it
ships.

:::{note}
This page is the **practical catalog** — how the maps are grouped, named, and
applied. For the theory behind them (the generation axioms, the metric
system, the naming grammar, and the benchmarks), see
**[Color system design](design.md)**.
:::

---

## Why not just use viridis?

viridis is excellent — but it is one map. Publication figures need a
*family*: single-hue ramps for density, multi-hue ramps for heatmaps,
diverging scales for signed values, cyclic maps for phase, all sharing the
same perceptual integrity. Standard matplotlib maps (`viridis`, `Blues`,
`tab10`, …) keep working without any prefix; the `dc.` prefix reaches the
dartwork set (and avoids collisions with matplotlib's own `pink`/`gray`
maps — the same convention as cmocean's `cmo.` and Crameri's `cmc.`).

The dartwork set adds what one map cannot: guaranteed **monotonic
lightness** on every sequential map (grayscale-safe), a smooth hue path
with no muddy shortcuts, and CIEDE2000-verified behavior under
color-vision-deficiency simulation.

---

## Quick start

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

dm.style.use("scientific")
data = np.random.randn(50, 50).cumsum(axis=0)
im = plt.imshow(data, cmap="dc.aurora")          # the default multi-hue map
cb = plt.colorbar(im, extend="both", shrink=0.9, pad=0.02)
cb.set_label("normalized signal")
cb.outline.set_visible(False)
plt.show()
```

- Reach any map by name in `cmap=`: `cmap="dc.blue"`, `cmap="dc.blue_red"`.
- Fetch the `Colormap` object with `plt.colormaps["dc.aurora"]`.
- Add `_r` to reverse any map: `dc.aurora_r`, `dc.blue_red_r`.

---

## The catalog

Explore the 43-map continuous v5 catalog below. Pick a map on the left; the true
gradient strip, accessibility chips, and the demo plots on the right
re-render live. Drag **Levels** to quantize, toggle **Reverse** / **B&W**,
switch the demo grid layout, and pick which of the 16 demo types to show.

```{raw} html
:file: ../_static/colormap_explorer.html
```

The continuous set is 43 maps in four groups:

| Group | Names | Count | Direction |
|---|---|--:|---|
| **Sequential** (single-hue) | `red` `rose` `coral` `tangerine` `orange` `amber` `yellow` `lime` `green` `teal` `cyan` `sky` `blue` `cobalt` `indigo` `violet` `purple` `fuchsia` `pink` `gray` | 20 | high = darker |
| **Multi-hue** | `afterglow` `aurora` (default) `blaze` `canopy` `glacier` `haze` `iris` `lagoon` `lava` | 9 | high = brighter |
| **Diverging** | `blue_red` `blue_orange` `cyan_red` `teal_amber` `teal_rose` `indigo_amber` `green_purple` `purple_orange` `violet_lime` `gray_blue` `gray_red` | 11 | anchored at the midpoint |
| **Cyclic** | `hue` `halo` `corona` | 3 | start = end |

Two cyclic members carry a structural note. `corona` and `halo` are
**dark-center phase maps**: pale lobes around a dark neutral middle with
matched endpoints, for angle or phase fields that should wrap without a seam.

Separately, the two qualitative **cycles** `dc.octave` (Octave) and
`dc.octave_print` (Octave Print) are registered for `cmap=` too, but they are
discrete class palettes, **not** part of the 43-map continuous set above —
reach them through `dm.set_cycle(...)` for categorical series.

---

## Naming grammar

The name states color identity; the suffix states a variant. The single rule
runs from color tokens to colormaps:

- **Single-hue** maps take the **family name itself** — `cmap="dc.blue"` is
  the same recipe as the `dc.blue` palette, rendered continuously over a wide
  L\* range.
- **Multi-hue** maps take a **natural-light scene name** — `aurora`, `blaze`,
  `lagoon` — with hue way-points chosen only at family anchors.
- **Diverging** maps take a **`low_high` pair name** — `blue_red`,
  `gray_red` — so the two poles are `dc.{a}6`/`dc.{b}6` and a line chart's
  colors match the heatmap's extremes automatically.
- **Cyclic** maps take a **circular-light-phenomenon name** — `halo`,
  `corona`, plus the structural `hue`.
- **`_r`** reverses any continuous map.

**Direction is an ink/light metaphor.** Ink maps (single-hue, diverging) run
*high = darker* (ink on paper); light maps (multi-hue, cyclic) run
*high = brighter* (light from dark, the viridis convention). See
[Color system design › Colormaps](design.md#colormaps-derived-from-the-palette)
for the full grammar and the anchor graph.

---

## Choosing a map

| Your data | Reach for |
|---|---|
| One magnitude / density | a single-hue map (`dc.blue`, `dc.gray`) |
| A heatmap that needs maximum resolution | a multi-hue map (`dc.aurora` default, `dc.haze` for CVD) |
| Signed values / anomalies around zero | a diverging map (`dc.blue_red`; `dc.gray_red` for risk/drawdown) |
| Angle / phase (0° = 360°) | a cyclic map (`dc.hue`, `dc.halo`, `dc.corona`) |
| Discrete classes | `dc.octave` / `dc.octave_print`, or `dm.set_cycle(...)` |

`aurora` is the default heatmap map: against viridis it is roughly 1.3× as
uniform (OKLab ΔE cv 0.063 vs 0.086) over a wider lightness range (81.9 vs
76.0), measured identically at 32 stops on the shipped 256-LUT. The warm
multi-hue maps divide the
work: `afterglow` runs through magenta (plasma-like), `blaze` starts in dark
violet (magma-like), and `lava` never touches violet at all — a
perceptually uniform replacement for matplotlib's `hot`.

---

## Color-blind safety

Every sequential map is verified under three CVD simulations —
**deuteranopia**, **protanopia**, and **tritanopia**.

- Sequential maps have **strictly monotonic lightness**, so data order
  survives even when hue perception is reduced.
- Single-hue maps (`dc.blue`, `dc.gray`, `dc.teal`, …) are **inherently
  CVD-safe** — their only contrast channel is lightness.
- `dc.haze` is the low-chroma multi-hue map tuned for maximum CVD margin
  (the cividis role).

> **Recommendation.** For the highest accessibility, choose maps whose
> primary contrast channel is **lightness** rather than hue. Diverging maps
> converge to one lightness at the midpoint (an inherent limit of every
> diverging map) — for grayscale print, pair them with contours or hatching.

---

## Creating custom colormaps

If the built-ins don't fit, build a map by interpolating in **OKLCH** with
`dm.cspace()`. The lightness ramp stays monotonic, so you skip the muddy
midtones that appear when hex codes are blended in RGB.

*Full walkthrough — interactive builder plus registration:
[Color Space › Creating custom colormaps](space.md#creating-custom-colormaps).*

::::{grid} 1
:gutter: 3

:::{grid-item-card} **Sequential**
:class-item: dm-cspace-card

```{image} images/color_space_colormap_sequential.svg
:alt: Sequential cspace colormap, indigo to amber, on a smooth 2D Gaussian
:class: dm-cspace-img
```

```python
import dartwork_mpl as dm
import matplotlib as mpl

colors = dm.cspace("#1a237e", "#ff6f00", n=256, space="oklch")
cmap = mpl.colors.ListedColormap([c.to_rgb() for c in colors])
```
:::

:::{grid-item-card} **Diverging**
:class-item: dm-cspace-card

```{image} images/color_space_colormap_diverging.svg
:alt: Diverging cspace colormap, indigo to white to crimson, on the same Gaussian
:class: dm-cspace-img
```

```python
import matplotlib as mpl

left = dm.cspace("#1a237e", "#ffffff", n=128, space="oklch")
right = dm.cspace("#ffffff", "#c62828", n=128, space="oklch")
cmap = mpl.colors.ListedColormap(
    [c.to_rgb() for c in (left[:-1] + right)]
)
```
:::

::::

---

## Rendering tips

- Set `vmin` / `vmax` yourself for stable colorbars across facets or animations.
- Reverse any map with the `_r` suffix (`dc.blue_red_r`).
- Hide colorbar outlines: `cb.outline.set_visible(False)`.
- For diverging data, use symmetric limits and `extend="both"`.

## See also

- [Color system design](design.md) — the axioms, metrics, and naming grammar
  behind every map.
- [Palettes](colors.md) — the full named palette catalog.
- [Color Space](space.md) — programmatic color manipulation and custom colormap creation.
- [API › Color Utilities](../api/color.rst) for all color functions.
