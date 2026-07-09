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
| `dc.*`  | **dartwork Color (recommended)** — 20 v5 families × 10 perceptual steps, plus Octave as `dc.octave`; see the [palette catalog](../color_system/categorical-palettes.md) | `dc.teal3`     |
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
> The `dc.*` namespace also holds 43 continuous **colormaps** plus the two
> Octave cycle colormaps — see the
> [Colormap catalog](../color_system/colormaps.md). Colormap names like
> `dc.aurora` only work as `cmap=` arguments, not as `color=` strings;
> the named-colors above are the ones you pass to `color=`.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("presentation")

fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
ax.plot([0, 1, 2], [1, 2, 1.5], marker="o", color="dc.green2", label="dc.green2")
ax.plot([0, 1, 2], [1.2, 1.6, 2.1], marker="s", color="dc.teal3", label="dc.teal3")
highlight = dm.mix_colors("dc.orange1", "white", alpha=0.45)
ax.fill_between([0, 1, 2], 0.9, 1.3, color=highlight, label="Mixed shade")
muted_line = dm.pseudo_alpha("dc.violet3", alpha=0.65, background="white")
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
    "dc.teal3", "dc.teal1", "dc.teal5",
    "dc.teal0", "dc.teal2", "dc.teal4",
])
```

### Picking a `dc.*` swatch

The v5 `dc.*` surface is 19 chromatic hue families plus gray, each with 10
perceptually equalized steps. Index 0 is the light end and index 9 is the dark
end. For unrelated categories use Octave via `dm.set_colors()` or
`dc.octave`; for related tones pick a family and sample the steps you need.

| Palette             | Use it for                                                     |
| ------------------- | -------------------------------------------------------------- |
| `dc.octave`         | Octave, for everyday unrelated categories                      |
| `dc.blue` / `dc.teal` / `dc.indigo` | Cool analytical series and ordered data        |
| `dc.green` / `dc.red` | Positive/negative states and status colors                  |
| `dc.coral` / `dc.tangerine` / `dc.orange` / `dc.amber` | Warm emphasis, thresholds, and call-outs |
| `dc.cobalt` / `dc.violet` / `dc.purple` / `dc.fuchsia` / `dc.pink` | Editorial accents and qualitative groups |
| `dc.gray`           | Grid lines, baselines, secondary fills                         |
| `dc.blue_red` / `dc.teal_amber` | Diverging ± data — change, correlation              |
| `dc.hl`             | Semantic highlight token                                       |

→ The full 20-family catalog with an interactive picker lives on the
[Categorical palettes](../color_system/categorical-palettes.md) page.

**Coming from `oc.*`?** A rough drop-in mapping:

| If you were reaching for…                       | Try…                                |
| ----------------------------------------------- | ----------------------------------- |
| `oc.blue6` / `oc.indigo6` / `oc.cyan6`          | `dc.teal3`                         |
| `oc.red6` / `oc.pink6`                          | `dc.red5` or `dc.rose5`           |
| `oc.orange5` / `oc.yellow5`                     | `dc.orange1` / `dc.orange0`         |
| `oc.green6` / `oc.teal6` / `oc.lime6`           | `dc.green2` or `dc.red0`           |
| `oc.violet6` / `oc.grape6`                      | `dc.violet3`                         |
| `oc.gray3..7` (light → dark)                    | `dc.gray2..7`                     |

## Color class

For most plots, named color strings like `"dc.teal3"` are all you need. When
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

dartwork-mpl provides utilities to discover and explore available color families:

```python
import dartwork_mpl as dm

# List Model B family records
families = dm.list_colors()
print(families[:2])  # [{'name': 'amber', 'kind': 'sequential', ...}, ...]

# Fetch a registered colormap or a designed discrete list
cmap = dm.colors("aurora")
cols = dm.colors("blue_red", n=5)

# Preview specific families
dm.show_colors(names=["blue", "blue_red"], n=5)

# Classify a colormap by type (takes a Colormap object)
import matplotlib as mpl
from dartwork_mpl.diagnostics import classify_cmap

cmap_type = classify_cmap(mpl.colormaps['dc.aurora'])
print(cmap_type)  # 'Multi-Hue'
```

## Color interpolation

```python
import dartwork_mpl as dm

# Perceptual interpolation between colors (OKLCH by default)
palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
for i, c in enumerate(palette):
    ax.bar(i, 1, color=c.to_hex())

# Also supports 'oklab' and 'rgb' spaces
gradient = dm.cspace(dm.color('dc.red1'), dm.color('dc.teal3'), n=10)
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
    <div class="dm-compare-toggle dm-seg no-thumb" role="group" aria-label="Interpolation comparison mode">
      <button class="dm-compare-toggle-btn dm-opt is-active" data-mode="both" aria-pressed="true">Side by Side</button>
      <button class="dm-compare-toggle-btn dm-opt" data-mode="oklch" aria-pressed="false">OKLCH Only</button>
      <button class="dm-compare-toggle-btn dm-opt" data-mode="rgb" aria-pressed="false">RGB Only</button>
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
from dartwork_mpl.diagnostics import classify_cmap

cmap = plt.colormaps["dc.aurora"]
print(cmap.name)                       # 'dc.aurora'
print(classify_cmap(cmap))             # 'Multi-Hue' (tells you the type)
```

Add `_r` to reverse any colormap (e.g., `dc.aurora_r`). Browse all available
colormaps on the [Colormaps](../color_system/colormaps.md) page.

## See also

- **Next →** [Layout and Typography](layout.md) — physical-width geometry, aspect tokens, and `simple_layout`
- [Design System → Palettes / Colormaps / Color Space](../design_system/index) — the visual catalogs
- [API › Color Utilities](../api/color) and [Visualization Tools](../api/visualization)
- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
