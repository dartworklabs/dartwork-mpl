# Colormaps

dartwork-mpl ships **56 curated colormaps** — all designed or refined in the
perceptually uniform **OKLCH** color space, spanning single-hue and multi-hue
sequentials, diverging, cyclical, and discrete categorical maps (plus a
vibrant tier for high-energy figures).

---

## Design philosophy

Most colormap libraries pick colors that "look nice" in sRGB and then
interpolate linearly between them. This creates two hidden problems:

1. **Perceptual non-uniformity** — equal numeric steps produce unequal
   visual steps (grey bands, shimmering artefacts).
2. **Lightness reversals** — parts of the ramp can become darker _then_
   lighter, destroying print/greyscale readability.

dartwork-mpl solves both by **designing entirely in OKLCH space**, the most
modern perceptually uniform color model (an improvement over CIE-LAB):

| Principle                  | How we enforce it                                                                        |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| **Lightness monotonicity** | Every sequential map has strictly monotonic OKLCH _L_. Greyscale readability guaranteed. |
| **Smooth hue path**        | Anchor colors placed along natural hue arcs (no muddy brown shortcuts).                  |
| **Bow-shaped chroma**      | Chroma peaks mid-ramp and tapers at boundaries, avoiding gamut clipping.                 |
| **Color-blind awareness**  | All maps verified under deuteranopia, protanopia, and tritanopia simulations.            |

> **Why not just use viridis?** &nbsp; viridis is excellent but it's only one
> map. For publication figures you need a _family_: sequential ramps for bars,
> diverging scales for anomalies, categorical sets for labels, and cyclical
> maps for phases — all sharing the same perceptual integrity.
> Standard Matplotlib maps (`viridis`, `Blues`, `tab10`, …) continue to work
> without any prefix.

---

## Quick start

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

dm.style.use("scientific")
data = np.random.randn(50, 50).cumsum(axis=0)
im = plt.imshow(data, cmap="dc.sunset_glow", vmin=-8, vmax=8)
cb = plt.colorbar(im, extend="both", shrink=0.9, pad=0.02)
cb.set_label("normalized signal")
cb.outline.set_visible(False)
plt.show()
```

- Add `_r` to reverse any map: `dc.sunset_glow_r`

---

## Colormap catalog

Explore all 56 built-in colormaps dynamically using the catalog below. Use the tabs to browse by data type.

```{raw} html
:file: images/colormap_explorer.html
```

---

## Creating custom colormaps

If the built-ins don't fit your data, build a colormap by interpolating
in **OKLCH space** with `dm.cspace()`. The lightness ramp stays
strictly monotonic, so you skip the muddy midtones that appear when
RGB hex codes are blended directly. Both panels below use the same
2D Gaussian so you can read the ramps doing their job side-by-side.

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
left = dm.cspace("#1a237e", "#ffffff", n=128, space="oklch")
right = dm.cspace("#ffffff", "#c62828", n=128, space="oklch")
cmap = mpl.colors.ListedColormap(
    [c.to_rgb() for c in (left[:-1] + right)]
)
```
:::

::::

---

## Color-blind safety

All `dc.*` maps are verified under three CVD simulations — **deuteranopia**,
**protanopia**, and **tritanopia**.

- Every sequential map has **strictly monotonic lightness**, preserving data
  ordering even when color perception is reduced.
- Single-hue maps (`dc.obsidian`, `dc.graphite`, `dc.sapphire`, …) are
  **inherently CVD-safe** — their contrast channel is lightness alone.

> **Recommendation**: For highest accessibility, choose maps whose primary
> contrast channel is **lightness** rather than hue.

---

## Rendering tips

- Set `vmin` / `vmax` yourself for stable colorbars across facets or animations.
- Reverse any map with the `_r` suffix (`dc.ice_fire_r`).
- Hide colorbar outlines: `cb.outline.set_visible(False)`.
- For diverging data, use symmetric limits and `extend="both"`.

## See also

- [Colors](colors.md) — full named palette catalog
- [Color Space & Manipulation](space.md) — programmatic color manipulation and custom colormap creation
- [Usage Guide › Colors](../usage_guide/colors.md) — practical color usage patterns
- [API › Color Utilities](../api/color.rst) for all color functions
