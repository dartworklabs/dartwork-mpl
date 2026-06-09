# Colors and Colormaps

This page covers practical usage: picking colors, mixing them, interpolating
gradients, and using colormaps. For full visual catalogs, jump to the
[Palette](../color_system/colors.md) or [Colormap](../color_system/colormaps.md)
catalogs under **Design System**.

## Named colors

dartwork-mpl ships its own curated palette — `dc.*` ("dartwork color")
— and registers six third-party design systems alongside it for
cross-team consistency. Use any of them anywhere matplotlib accepts a
color.

| Prefix  | Library                          | Example         |
| ------- | -------------------------------- | --------------- |
| `dc.*`  | **dartwork Color (recommended)** — 8 mood palettes (`vivid`, `autumn`, `cyber`, `forest`, `nordic`, `ocean`, `pop`, `sunset`) × 6 shades each | `dc.ocean3`     |
| `dm.*`  | Alias of `dc.*` (legacy)         | `dm.ocean3`     |
| `oc.*`  | OpenColor                        | `oc.blue5`      |
| `tw.*`  | Tailwind CSS                     | `tw.blue500`    |
| `md.*`  | Material Design                  | `md.red500`     |
| `ad.*`  | Ant Design                       | `ad.blue6`      |
| `cu.*`  | Chakra UI                        | `cu.teal500`    |
| `pr.*`  | Primer (GitHub)                  | `pr.blue5`      |

> Start with `dc.*` for new figures — the palettes are tuned for
> publication-ready output. Reach for the third-party prefixes when
> you need to match an external brand or design system.
>
> The `dc.*` namespace also holds 100+ curated **colormaps** — see the
> [Colormap catalog](../color_system/colormaps.md). Colormap names like
> `dc.deep_sea` only work as `cmap=` arguments, not as `color=` strings;
> the named-colors above are the ones you pass to `color=`.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("presentation")

fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
ax.plot([0, 1, 2], [1, 2, 1.5], marker="o", color="dc.forest2", label="dc.forest2")
ax.plot([0, 1, 2], [1.2, 1.6, 2.1], marker="s", color="dc.ocean3", label="dc.ocean3")
highlight = dm.mix_colors("dc.sunset1", "white", alpha=0.45)
ax.fill_between([0, 1, 2], 0.9, 1.3, color=highlight, label="Mixed shade")
muted_line = dm.pseudo_alpha("dc.cyber3", alpha=0.65, background="white")
ax.plot([0, 1, 2], [0.8, 1.1, 1.4], color=muted_line, label="Pseudo alpha")
ax.legend()
dm.simple_layout(fig)
```

```{raw} html
:file: ../color_system/images/palette_explorer.html
```

### Interactive palette picker — try one click before committing

Pick a palette below and the demo chart re-renders with that
`prop_cycle`. Swatch chips show the actual hex values you'd get; the
tabs group palettes by namespace (`dc.*` first, then the third-party
design systems). The bar plot's data and labels are byte-identical
across every render — only `axes.prop_cycle` changes.

```{raw} html
:file: ../_static/palette_picker.html
```

Once you've picked one, apply it in your own script:

```python
import matplotlib as mpl
from cycler import cycler

dm.style.use("report")  # base preset (font, line widths, spines, ...)
mpl.rcParams["axes.prop_cycle"] = cycler(color=[
    "dc.ocean3", "dc.ocean1", "dc.ocean5",
    "dc.ocean0", "dc.ocean2", "dc.ocean4",
])
```

### Picking a `dc.*` swatch

The eight families are tuned to evoke different moods, so the family
name is usually a good first filter. Inside each family the index is a
**lightness ramp from 0 (light) → 5 (dark)**:

| Family       | Use it for                                                         |
| ------------ | ------------------------------------------------------------------ |
| `dc.ocean`   | Cool blue primaries — line charts, sequential data, default brand color |
| `dc.forest`  | Cool greens — comparison series, "good"/positive states            |
| `dc.sunset`  | Warm accents — call-outs, highlights, alerts that aren't alarming  |
| `dc.vivid`   | Saturated brand colors — high-contrast primary lines, headlines    |
| `dc.cyber`   | Magenta / purple — secondary brand color, contrast against ocean    |
| `dc.autumn`  | Warm earth tones — segmentations with low-key palette intent       |
| `dc.nordic`  | Neutrals / muted — grid lines, baselines, secondary text, fills    |
| `dc.pop`     | Saturated playful set — categorical data with 4–6 distinct groups  |

**Coming from `oc.*`?** A rough drop-in mapping:

| If you were reaching for…                       | Try…                                |
| ----------------------------------------------- | ----------------------------------- |
| `oc.blue6` / `oc.indigo6` / `oc.cyan6`          | `dc.ocean3`                         |
| `oc.red6` / `oc.pink6`                          | `dc.vivid1` or `dc.sunset3`         |
| `oc.orange5` / `oc.yellow5`                     | `dc.sunset1` / `dc.sunset0`         |
| `oc.green6` / `oc.teal6` / `oc.lime6`           | `dc.forest2` or `dc.pop0`           |
| `oc.violet6` / `oc.grape6`                      | `dc.cyber3`                         |
| `oc.gray3..7` (light → dark)                    | `dc.nordic1..3`                     |

## Color class

For most plots, named color strings like `"dc.ocean3"` are all you need. When
you need to programmatically adjust hue, saturation, or lightness — or
interpolate between colors in a perceptually uniform space — use the `Color`
class:

```python
import dartwork_mpl as dm

color = dm.oklch(0.7, 0.15, 150)    # OKLCH (L, C, h°)
color.oklch.C *= 1.2                 # boost chroma in-place
print(color.to_hex())                # '#...'
```

→ **Full guide:** [Color Space & Manipulation](../color_system/space.md) —
constructors, views, interpolation, and custom colormaps.

## Exploring Available Colors

dartwork-mpl provides utilities to discover and explore available color palettes:

```python
import dartwork_mpl as dm

# List all discrete color palettes
palettes = dm.list_palettes()
print(palettes[:5])  # ['dc.vivid', 'oc.blue', 'oc.red', 'tw.emerald', ...]

# List all colormaps
cmaps = dm.list_colormaps()
print(cmaps[:5])  # ['dc.deep_sea', 'dc.forest', 'dc.sunset', ...]

# Preview a specific palette
dm.show_palette('oc.blue')  # Shows all shades: blue0, blue1, ..., blue9

# Visualize multiple palettes at once
dm.plot_colors(['oc.blue', 'tw.emerald', 'md.purple'])

# Visualize colormaps
dm.plot_colormaps(['dc.deep_sea', 'dc.forest'])

# Classify a colormap by type
cmap_type = dm.classify_colormap('viridis')
print(cmap_type)  # 'sequential'
```

## Color interpolation

```python
import dartwork_mpl as dm

# Perceptual interpolation between colors (OKLCH by default)
palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
for i, c in enumerate(palette):
    ax.bar(i, 1, color=c.to_hex())

# Also supports 'oklab' and 'rgb' spaces
gradient = dm.cspace(dm.color('dc.vivid1'), dm.color('dc.ocean3'), n=10)
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

cmap = plt.colormaps["dc.deep_sea"]
print(cmap.name)                       # 'dc.deep_sea'
print(dm.classify_colormap(cmap))      # 'sequential' (tells you the type)
```

Add `_r` to reverse any colormap (e.g., `dc.sunset_r`). Browse all available
colormaps on the [Colormaps](../color_system/colormaps.md) page.

## See also

- **Next →** [Layout and Typography](layout.md) — physical-width geometry, aspect tokens, and `simple_layout`
- [Design System → Palettes / Colormaps / Color Space](../design_system/index) — the visual catalogs
- [API › Color Utilities](../api/color) and [Visualization Tools](../api/visualization)
- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
