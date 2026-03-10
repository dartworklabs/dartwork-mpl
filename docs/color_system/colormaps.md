# Colormaps

dartwork-mpl ships **16 curated colormaps** — all designed or refined in the
perceptually uniform **OKLCH** color space. Each category offers **3 color-preference
options** so you can match the tone of your visualization.

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
im = plt.imshow(data, cmap="dc.sunset", vmin=-8, vmax=8)
cb = plt.colorbar(im, extend="both", shrink=0.9, pad=0.02)
cb.set_label("normalized signal")
cb.outline.set_visible(False)
plt.show()
```

- Add `_r` to reverse any map: `dc.sunset_r`

---

## Colormap reference

### Sequential Single-Hue

One dominant hue ramping from dark to light. Ideal for magnitude, density, and
print-safe applications. **3 flavors + 1 earth tone:**

| Name            | Flavor     | Hue         | Recommended use                |
| --------------- | ---------- | ----------- | ------------------------------ |
| `dc.steel`      | 🧊 Cool    | Blue-gray   | Temperature (cold), depth maps |
| `dc.flame`      | 🔥 Warm    | Red-orange  | Heat intensity, risk scores    |
| `dc.monochrome` | ⬜ Neutral | Pure gray   | B&W print, accessibility-first |
| `dc.lajolla`    | 🏜️ Earth   | Cream→brown | Terrain, geology, commodities  |

### Sequential Multi-Hue

Colorful ramps sweeping across hue families with smooth lightness.
Best for heatmaps and false-color images. **3 flavors + 1 scientific:**

| Name         | Flavor        | Hue path                     | Recommended use                 |
| ------------ | ------------- | ---------------------------- | ------------------------------- |
| `dc.ocean`   | 🧊 Cool       | Navy → teal → mint           | Bathymetry, fluid dynamics      |
| `dc.sunset`  | 🔥 Warm       | Indigo → crimson → gold      | Spectroscopy, general heatmaps  |
| `dc.thermal` | ⚡ Vivid      | Purple → magenta → amber     | Infrared imaging, heat transfer |
| `dc.batlow`  | 🌈 Scientific | Teal → green → yellow → pink | Rainbow substitute (papers)     |

### Diverging

Two saturated hues flanking a neutral midpoint. Perfect for anomalies,
signed values, and comparisons against a reference. **3 flavors + 1 dark-center:**

| Name         | Flavor         | Polarity          | Recommended use            |
| ------------ | -------------- | ----------------- | -------------------------- |
| `dc.balance` | 🧊 Cool        | Blue ↔ Red        | Temperature anomaly        |
| `dc.earth`   | 🌿 Natural     | Brown ↔ Green     | Land-use change, elevation |
| `dc.delta`   | 🔶 Modern      | Teal ↔ Orange     | CVD-safe, correlations     |
| `dc.berlin`  | 🌑 Dark-center | Blue → dark → Red | Depth-weighted diverging   |

### Cyclical

Start color equals end color. Use for angles, phases, or any periodic variable.

| Name                | Hue loop                    | Recommended use              |
| ------------------- | --------------------------- | ---------------------------- |
| `dc.twilight_oklch` | Pink → purple → teal → pink | Wind direction, phase angles |

### Discrete (Categorical)

OKLCH hue-wheel equispaced colors for labeling distinct categories.
**3 intensity levels** — same hues, different lightness × chroma:

| Name        | Flavor           | Design                           | Recommended use          |
| ----------- | ---------------- | -------------------------------- | ------------------------ |
| `dc.bold`   | ⚡ High-contrast | L=0.55, C=0.19 — vivid, punchy   | Dense plots, many labels |
| `dc.muted`  | 📄 Professional  | L=0.65, C=0.10 — calm, scholarly | Papers, reports          |
| `dc.pastel` | 🎨 Soft          | L=0.85, C=0.07 — light, airy     | Presentations, fills     |

---

## Color-blind safety

All `dc.*` maps are verified under three CVD simulations — **deuteranopia**,
**protanopia**, and **tritanopia**.

- Every sequential map has **strictly monotonic lightness**, preserving data
  ordering even when color perception is reduced.
- Single-hue and achromatic maps (`monochrome`, `steel`) are **inherently
  CVD-safe**.

> **Recommendation**: For highest accessibility, choose maps whose primary
> contrast channel is **lightness** rather than hue.

---

## Rendering tips

- Set `vmin` / `vmax` yourself for stable colorbars across facets or animations.
- Reverse any map with the `_r` suffix (`dc.flame_r`).
- Hide colorbar outlines: `cb.outline.set_visible(False)`.
- For diverging data, use symmetric limits and `extend="both"`.

## See also

- [Colors](colors.md) — full named palette catalog
- [Color Space & Manipulation](space.md) — programmatic color manipulation and custom colormap creation
- [Usage Guide › Colors](../usage_guide/colors.md) — practical color usage patterns
- [API › Color Utilities](../api/color.rst) for all color functions
