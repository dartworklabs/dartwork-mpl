# Colors and Colormaps

## Named colors

dartwork-mpl registers named palettes from OpenColor, Tailwind, Material,
Ant Design, Chakra, and Primer. Use them anywhere matplotlib accepts a color.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("presentation")

fig, ax = plt.subplots(figsize=(dm.cm2in(8), dm.cm2in(5)), dpi=300)
ax.plot([0, 1, 2], [1, 2, 1.5], marker="o", color="oc.green5", label="oc.*")
ax.plot([0, 1, 2], [1.2, 1.6, 2.1], marker="s", color="tw.blue500", label="Tailwind")
highlight = dm.mix_colors("md.orange600", "white", alpha=0.45)
ax.fill_between([0, 1, 2], 0.9, 1.3, color=highlight, label="Mixed shade")
muted_line = dm.pseudo_alpha("pr.blue5", alpha=0.65, background="white")
ax.plot([0, 1, 2], [0.8, 1.1, 1.4], color=muted_line, label="Pseudo alpha")
ax.legend(fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

:::{figure} images/colors_named.svg
:alt: Plot showing OpenColor, Tailwind, Material, and Primer named colors in use
:width: 100%
:::

## Color class

The `Color` class provides perceptually uniform color manipulation across
OKLab, OKLCH, RGB, and hex color spaces:

```python
import dartwork_mpl as dm

# Create colors from any color space
color = dm.oklch(0.7, 0.15, 150)       # OKLCH (L, C, h°)
color = dm.rgb(66, 133, 244)           # auto-detects 0-255 range
color = dm.hex('#4285F4')              # hex string
color = dm.named('oc.blue5')           # matplotlib color name

# Read/write via views (mutable references to internal state)
color.oklch.C *= 1.2                   # boost chroma in-place
L, C, h = color.oklch                  # unpack OKLCH
r, g, b = color.rgb                    # unpack RGB

# Convert to any representation
print(color.to_hex())                  # '#...'
print(color.to_rgb())                  # (r, g, b)
print(color.to_oklch())               # (L, C, h)

# Copy to avoid mutation
brighter = color.copy()
brighter.oklab.L += 0.1
```

See [Color Space](../color_system/space) for the full guide on perceptual color
manipulation, including interpolation and custom colormap creation.

## Color interpolation

```python
import dartwork_mpl as dm

# Perceptual interpolation between colors (OKLCH by default)
palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
for i, c in enumerate(palette):
    ax.bar(i, 1, color=c.to_hex())

# Also supports 'oklab' and 'rgb' spaces
gradient = dm.cspace(dm.named('oc.red5'), dm.named('oc.blue5'), n=10)
```

:::{figure} images/colors_interpolation.svg
:alt: Perceptual color interpolation with cspace in OKLCH space
:width: 100%
:::

**Why OKLCH matters:** Interpolating in RGB produces muddy, desaturated midtones.
OKLCH maintains perceptual uniformity — every step looks equally spaced to the
human eye:

:::{figure} images/colors_oklch_vs_rgb.svg
:alt: OKLCH vs RGB interpolation comparison showing muddy RGB midtones
:width: 100%
:::

## Colormaps

dartwork-mpl bundles custom colormaps prefixed with `dc.` — dartwork Color
curated colormaps designed for perceptually uniform gradients. They work like
any matplotlib colormap:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

cmap = plt.colormaps["dc.Crest"]
print(cmap.name)                       # 'dc.Crest'
print(dm.classify_colormap(cmap))      # 'sequential' (tells you the type)
```

Add `_r` to reverse any colormap (e.g., `dc.sunset_r`). Browse all available
colormaps on the [Colormaps](../color_system/colormaps) page.

## Where things live

- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
- Palette/colormap previews: [Color System](../color_system/index)
- API functions: [Color Utilities](../api/color) and [Visualization Tools](../api/visualization)
