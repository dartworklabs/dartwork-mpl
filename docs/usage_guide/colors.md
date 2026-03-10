# Colors and Colormaps

This page covers practical usage: picking colors, mixing them, interpolating
gradients, and using colormaps. For full visual catalogs of every palette and
colormap, see the [Color System](../color_system/index.md) reference.

## Named colors

dartwork-mpl registers named palettes from OpenColor, Tailwind, Material,
Ant Design, Chakra, and Primer. Use them anywhere matplotlib accepts a color.

| Prefix | Library         | Example      |
| ------ | --------------- | ------------ |
| `oc.*` | OpenColor       | `oc.blue5`   |
| `tw.*` | Tailwind CSS    | `tw.blue500` |
| `md.*` | Material Design | `md.red500`  |
| `an.*` | Ant Design      | `an.blue6`   |
| `ch.*` | Chakra UI       | `ch.teal500` |
| `pr.*` | Primer          | `pr.blue5`   |

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

```{raw} html
:file: ../color_system/images/palette_explorer.html
```

## Color class

For most plots, named color strings like `"oc.blue5"` are all you need. Use the
`Color` class when you want to programmatically adjust hue, saturation, or
lightness — or when you need to interpolate between colors in a perceptually
uniform space (OKLab, OKLCH, RGB, and hex):

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

See [Color Space](../color_system/space.md) for the full guide on perceptual color
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

```{raw} html
<div class="dm-interp-widget">
  <div class="dm-interp-controls">
    <div class="dm-interp-color-input">
      <span class="dm-interp-label">From</span>
      <input type="color" class="dm-interp-picker dm-interp-picker-from" value="#FF6B6B">
      <input type="text" class="dm-interp-hex dm-interp-hex-from" value="#FF6B6B">
    </div>
    <span class="dm-interp-arrow">→</span>
    <div class="dm-interp-color-input">
      <span class="dm-interp-label">To</span>
      <input type="color" class="dm-interp-picker dm-interp-picker-to" value="#4ECDC4">
      <input type="text" class="dm-interp-hex dm-interp-hex-to" value="#4ECDC4">
    </div>
    <div class="dm-interp-slider-group">
      <span class="dm-interp-label">Steps</span>
      <input type="range" class="dm-interp-slider" min="3" max="20" value="5">
      <span class="dm-interp-steps-label">n=5</span>
    </div>
  </div>
  <div class="dm-interp-bar"></div>
  <div class="dm-interp-code">dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')</div>
</div>
```

**Why OKLCH matters:** Interpolating in RGB produces muddy, desaturated midtones.
OKLCH maintains perceptual uniformity — every step looks equally spaced to the
human eye:

```{raw} html
<div class="dm-compare-widget">
  <div class="dm-compare-header">
    <div class="dm-compare-title">OKLCH vs RGB Interpolation</div>
    <div class="dm-compare-subtitle">Why color space matters for gradient quality</div>
  </div>
  <div class="dm-compare-controls">
    <div class="dm-compare-toggle">
      <button class="dm-compare-toggle-btn active" data-mode="both">Side by Side</button>
      <button class="dm-compare-toggle-btn" data-mode="oklch">OKLCH Only</button>
      <button class="dm-compare-toggle-btn" data-mode="rgb">RGB Only</button>
    </div>
    <div class="dm-compare-slider-group">
      <span class="dm-interp-label">Steps</span>
      <input type="range" class="dm-compare-slider" min="5" max="40" value="20">
      <span class="dm-compare-steps-label">n=20</span>
    </div>
  </div>
  <div class="dm-compare-rows">
    <div class="dm-compare-row">
      <div class="dm-compare-row-label">OKLCH<small>perceptually uniform</small></div>
      <div class="dm-compare-bar dm-compare-bar-oklch"></div>
    </div>
    <div class="dm-compare-row">
      <div class="dm-compare-row-label">RGB<small>muddy midtones</small></div>
      <div class="dm-compare-bar dm-compare-bar-rgb"></div>
    </div>
  </div>
  <div class="dm-compare-verdict">
    ↑ <strong>OKLCH</strong> maintains vivid hues through the transition.
    ↓ <strong>RGB</strong> produces muddy, desaturated midtones —
    notice the grey-brown colors in the middle.
  </div>
</div>
```

## Colormaps

dartwork-mpl bundles custom colormaps prefixed with `dc.` — curated for
perceptually uniform gradients. They work like any matplotlib colormap:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

cmap = plt.colormaps["dc.Crest"]
print(cmap.name)                       # 'dc.Crest'
print(dm.classify_colormap(cmap))      # 'sequential' (tells you the type)
```

Add `_r` to reverse any colormap (e.g., `dc.sunset_r`). Browse all available
colormaps on the [Colormaps](../color_system/colormaps.md) page.

## Where things live

- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
- Palette/colormap previews: [Color System](../color_system/index)
- API functions: [Color Utilities](../api/color) and [Visualization Tools](../api/visualization)
