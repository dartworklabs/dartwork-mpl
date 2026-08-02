# Colors and Colormaps

This page covers practical usage: picking colors, mixing them, interpolating
gradients, and using colormaps. For full visual catalogs, jump to the
[Colors](../color_system/colors.md), [Palettes](../color_system/palettes.md),
or [Colormaps](../color_system/colormaps.md) catalogs under **Design System**.

## What should I use?

| If you need to... | Use... | Matplotlib surface |
|---|---|---|
| color one mark, line, or area | a named color token | `color="dc.blue6"` |
| color separate series or categories | a palette | `dm.set_colors(...)` |
| turn numeric values into colors | a colormap | `cmap="dc.aurora"` |
| create or adjust a color yourself | the `Color` class | `dm.oklch(...)` |

:::{tip}
Most readers only need the first three rows. You can ignore the color-space
math unless you want to create or adjust colors yourself.
:::

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

## Four ideas

Hue
: Hue is the color family: red, green, and blue are different hues. In a line
  chart, changing hue can distinguish one series from another.

Lightness
: Lightness describes the light-to-dark direction. A sequential heatmap can
  use light colors for low values and dark colors for high values.

Chroma
: Chroma describes how colorful or muted a color is. In a scatter plot, a
  vivid highlight can have more chroma than the muted background points.

Contrast
: Contrast describes how strongly two neighboring colors stand apart. For
  example, a dark annotation on a white chart background has more contrast
  than a pale one.

Palette
: A palette is a finite list of colors. Use one to give the separate series in
  a bar chart distinct colors.

Colormap
: A colormap turns numeric values into colors. Use one to encode temperature
  across a heatmap or the values of points in a scatter plot.

Sequential
: Sequential means one ordered path from low to high. A population-density map
  can run from a light low end to a dark high end.

Diverging
: Diverging means two ordered arms meet at a meaningful center. A change chart
  can show decreases on one side of zero and increases on the other.

Cyclic
: Cyclic means the last color joins the first. It fits a phase or wind-direction
  chart where 360 degrees returns to 0 degrees.

Qualitative
: Qualitative, or categorical, means separate colors for labels with no numeric
  order, such as the species in a grouped scatter plot.

## Named colors

dartwork-mpl ships its own curated palette — `dc.*` ("dartwork color")
— and registers six third-party design systems alongside it for
cross-team consistency. Use any of them anywhere matplotlib accepts a
color.

| Prefix  | Library                          | Example         |
| ------- | -------------------------------- | --------------- |
| `dc.*`  | **dartwork Color (recommended)** — 20 families × 10 perceptual steps, plus Octave as `dc.octave`; see the [palette catalog](../color_system/palettes.md) | `dc.teal3`     |
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
> The `dc.*` namespace also holds 43 continuous **colormaps** and 13
> qualitative colormaps (the two Octave cycles plus 11 curated sets) — see the
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

### Picking a `dc.*` swatch

The `dc.*` surface is 19 chromatic hue families plus gray (20 total), each with
10 steps. Index 0 is the light end and index 9 is the dark end. The ramps are
designed to give neighboring swatches clear separation while keeping a
reliable light-to-dark order.

#### Four separate jobs

Construction
: OKLab and OKLCH are used to construct and adjust colors. Construction uses
  ΔEOK to space neighboring steps. ΔEOK is a color-distance ruler: larger means
  more different.

Modeled output ordering
: Modeled `relative_y` records nominal output ordering, with nominal black at
  0 and nominal reference white at 1 under this software convention.

Independent validation
: CIELAB, ΔE00, and color-vision deficiency (CVD) simulation are independent
  validation checks only. They do not construct colors or define modeled
  relative Y.

Text contrast
: Web Content Accessibility Guidelines (WCAG) contrast is a separate check for
  text against a known background. It does not certify an entire palette.

For the detailed construction, modeled-output, and validation evidence, see
the [Design rationale](../color_system/design-rationale.md).

For unrelated categories use Octave via `dm.set_colors()` or `dc.octave`; for
related tones pick a family and sample the steps you need.

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

→ The full token catalog lives on [Colors](../color_system/colors.md); the
series explorer lives on [Palettes](../color_system/palettes.md).

**Coming from `oc.*`?** A rough drop-in mapping:

| If you were reaching for…                       | Try…                                |
| ----------------------------------------------- | ----------------------------------- |
| `oc.blue6` / `oc.indigo6` / `oc.cyan6`          | `dc.teal3`                         |
| `oc.red6` / `oc.pink6`                          | `dc.red5` or `dc.rose5`           |
| `oc.orange5` / `oc.yellow5`                     | `dc.orange1` / `dc.orange0`         |
| `oc.green6` / `oc.teal6` / `oc.lime6`           | `dc.green2` / `dc.teal2` / `dc.lime2` |
| `oc.violet6` / `oc.grape6`                      | `dc.violet3`                         |
| `oc.gray3..7` (light → dark)                    | `dc.gray2..7`                     |

## Palettes for separate series

To choose a series palette visually, use the
[Palettes explorer](../color_system/palettes.md). It previews Octave, curated
qualitative sets, family samples, black-and-white (B&W) and color-vision
deficiency (CVD) checks, and copyable
`dm.set_colors(...)` / `dm.colors(..., n=...)` calls.

Once you've picked a set, apply it in your own script:

```python
import matplotlib as mpl
from cycler import cycler

dm.style.use("report")  # base preset (font, line widths, spines, ...)
mpl.rcParams["axes.prop_cycle"] = cycler(color=[
    "dc.teal3", "dc.teal1", "dc.teal5",
    "dc.teal0", "dc.teal2", "dc.teal4",
])
```

## Color class

For most plots, named color strings like `"dc.teal3"` are all you need. When
you need to programmatically adjust hue, saturation, or lightness — or
interpolate between colors in a perceptual color space — use the `Color`
class:

OKLab and OKLCH are two views of the same perceptual color model. OKLab is
convenient for color math; OKLCH exposes lightness `L`, chroma `C`, and hue
angle `h` for authoring.

```python
import dartwork_mpl as dm

color = dm.oklch(0.7, 0.15, 150)    # OKLCH (L, C, h°)
color.oklch.C *= 1.2                 # boost chroma in-place
print(color.to_hex())                # '#...'
```

→ **Full guide:** [Color class & manipulation](../color_system/color-class.md) —
constructors, views, interpolation, and custom colormaps.

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

**Why OKLCH matters:** Interpolating in RGB can produce muddy, desaturated
midtones. OKLCH keeps hue and chroma explicit and often produces a smoother,
more vivid path. It improves the interpolation geometry; it does not guarantee
that every step looks exactly equal to every observer:

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
      <div class="dm-compare-row-label">OKLCH<small>perceptual interpolation</small></div>
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

## Exploring Available Colors

dartwork-mpl provides utilities to discover and explore available color families:

```python
import dartwork_mpl as dm

# List available color-family records
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

## Colormaps

dartwork-mpl bundles custom colormaps prefixed with `dc.`. Their OKLab/OKLCH
construction is topology-specific: single-hue, continuous-gray, and multi-hue
sequential paths use ΔEOK arc-length resampling; diverging maps use symmetric
pointwise arms and integer resampling; `hue` uses equal hue angles; and the two
twilight cycles use closed-path ΔEOK resampling. Modeled relative Y is checked
against each map's required direction or shape, followed by independent
finished-output diagnostics. They work like any matplotlib colormap:

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

## Accessibility checklist

:::{important}
1. Do not rely on hue alone for critical distinctions.
2. For ordered values, choose a map that still changes from light to dark.
3. For critical grayscale or print output, add labels, contours, markers,
   hatching, or line styles.
4. Web Content Accessibility Guidelines (WCAG) contrast applies to text
   against a known background; it does not certify an entire palette.
5. A color-vision deficiency (CVD) simulation is a useful model-based check,
   not a guarantee for every individual observer.
:::

## See also

- **Next →** [Layout and Typography](layout.md) — physical-width geometry, aspect tokens, and `simple_layout`
- [Design System → Colors / Palettes / Colormaps / Color class](../design_system/index) — the visual catalogs
- [API › Color Utilities](../api/color) and [Visualization Tools](../api/visualization)
- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
