# Colormaps

dartwork-mpl ships 27 custom colormaps — all generated in the perceptually
uniform **OKLCH** color space — plus 31 bundled [Crameri Scientific](https://www.fabiocrameri.ch/colourmaps/) maps.
Every gradient below is interactive: hover for the registered name.

---

## Design philosophy

Most colormap libraries pick colors that "look nice" in sRGB and then
interpolate linearly between them. This creates two hidden problems:

1. **Perceptual non-uniformity** — equal numeric steps produce unequal
   visual steps (grey bands, shimmering artefacts).
2. **Lightness reversals** — parts of the ramp can become darker _then_
   lighter, destroying print/greyscale readability.

dartwork-mpl solves both by **designing entirely in OKLCH space**, the most
modern perceptually uniform colour model (an improvement over CIE-LAB):

| Principle                  | How we enforce it                                                                                                                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lightness monotonicity** | Every sequential map has strictly increasing (or decreasing) OKLCH _L_. This guarantees greyscale readability.                                                                                                       |
| **Smooth hue path**        | Anchor colours are placed along natural hue arcs (no purple-yellow shortcuts that produce muddy brown in RGB).                                                                                                       |
| **Bow-shaped chroma**      | Chroma peaks in the middle and tapers at both ends, avoiding clipping at gamut boundaries.                                                                                                                           |
| **Color-blind awareness**  | All maps are verified under deuteranopia, protanopia, and tritanopia simulations. Maps relying on lightness (Single-Hue, `monochrome`, `ash`) remain fully usable; hue-dependent maps are documented with CVD notes. |

> **Why not just use viridis?** &nbsp; viridis is an excellent default for generic
> scientific plots. But if your work involves financial reports, diverging
> anomalies, multi-panel dashboards, or publication-quality figures, you need
> a _family_ of maps that share the same perceptual integrity: dark-to-light
> bar ramps, symmetric diverging scales, cyclical angle maps, and achromatic
> print-safe options. That is what the `dc.*` lineup provides.

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
- Standard Matplotlib maps (`viridis`, `Blues`, `tab10`, …) continue to work
  without any change.

---

## Colormap reference

### Sequential Single-Hue

One dominant hue ramping from dark to light. Ideal for magnitude, density, and
print-safe applications.

| Name            | Hue family      | Recommended use                                   |
| --------------- | --------------- | ------------------------------------------------- |
| `dc.emerald`    | Green           | Environmental metrics, growth rates               |
| `dc.berry`      | Pink / Rose     | Population density, biological data               |
| `dc.steel`      | Blue            | Temperature (cold), depth maps                    |
| `dc.flame`      | Red / Orange    | Heat intensity, risk scores                       |
| `dc.lavender`   | Purple / Violet | Probability distributions, clustering             |
| `dc.ash`        | Achromatic grey | Print-only figures, lightness reference           |
| `dc.amber`      | Gold / Yellow   | Energy, price heatmaps, warm metrics              |
| `dc.teal`       | Teal / Cyan     | Ocean data, medical imaging, humidity             |
| `dc.copper`     | Brown / Sienna  | Geology, commodities, earthy aesthetics           |
| `dc.prism`      | Cool indigo     | General academic (viridis-style, narrow hue band) |
| `dc.monochrome` | Pure achromatic | B&W printing, accessibility-first figures         |

### Sequential Multi-Hue

Colourful ramps that sweep across two or more hue families while keeping
lightness smooth. Best for heatmaps and false-colour images.

| Name         | Hue path                            | Recommended use                               |
| ------------ | ----------------------------------- | --------------------------------------------- |
| `dc.ocean`   | Navy → teal → mint                  | Bathymetry, fluid dynamics                    |
| `dc.sunset`  | Indigo → crimson → gold             | Spectroscopy, general heatmaps                |
| `dc.nebula`  | Purple → magenta → amber → yellow   | Astronomical imaging                          |
| `dc.marine`  | Navy → teal → sage                  | Oceanography, salinity                        |
| `dc.neon`    | Navy → magenta → orange → yellow    | High-contrast visualizations                  |
| `dc.arctic`  | Dark navy → steel blue → ice white  | Meteorology, cryosphere (viridis alternative) |
| `dc.thermal` | Deep indigo → magenta → red → amber | Infrared imaging, heat transfer               |
| `dc.verdant` | Forest → emerald → lime → cream     | Vegetation indices, agriculture               |
| `dc.dusk`    | Midnight → plum → rose → pale gold  | Time series, astronomical twilight            |

### Diverging

Two saturated hues flanking a neutral midpoint. Perfect for anomalies, signed
values, and comparisons against a reference.

| Name          | Polarity       | Recommended use                                    |
| ------------- | -------------- | -------------------------------------------------- |
| `dc.balance`  | Blue ↔ Red     | Temperature anomaly, generic signed data           |
| `dc.earth`    | Brown ↔ Green  | Land-use change, elevation delta                   |
| `dc.delta`    | Teal ↔ Orange  | Return spreads, correlation matrices               |
| `dc.polar`    | Purple ↔ Green | Valuation score (high / low), bias                 |
| `dc.spectrum` | Navy ↔ Crimson | Refined RdBu alternative for publications          |
| `dc.fiscal`   | Green ↔ Red    | Profit / loss, buy / sell signal ⚠️ _not CVD-safe_ |

### Cyclical

Start colour equals end colour. Use for angles, phases, or any periodic
variable.

| Name                | Hue loop                    | Recommended use              |
| ------------------- | --------------------------- | ---------------------------- |
| `dc.twilight_oklch` | Pink → purple → teal → pink | Wind direction, phase angles |

---

## Provenance badges

Each map in the panels below carries a provenance badge:

- <span style="font-size: 0.85em; padding: 2px 6px; border-radius: 4px; background: #e3f2fd; color: #1565c0;">OKLCH</span> — Custom-designed, interpolated in OKLCH space.
- <span style="font-size: 0.85em; padding: 2px 6px; border-radius: 4px; background: #f5f5f5; color: #666;">Crameri</span> — [Crameri Scientific Colour Maps](https://www.fabiocrameri.ch/colourmaps/) by Fabio Crameri.

---

## Gradient panels

```{raw} html
:file: images/colormaps_sequential_single_hue.html
```

```{raw} html
:file: images/colormaps_sequential_multi_hue.html
```

```{raw} html
:file: images/colormaps_diverging.html
```

```{raw} html
:file: images/colormaps_cyclical.html
```

### Categorical (Qualitative) Maps

For discrete labels, `dartwork-mpl` fully supports the built-in
[Matplotlib Qualitative colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html#qualitative)
(e.g. `tab10`, `Set2`, `Dark2`). No `dc.` prefix needed.

---

## Color-blind safety

All `dc.*` maps are verified under three colour-vision-deficiency (CVD)
simulations — **deuteranopia**, **protanopia**, and **tritanopia** — using the
Brettel 1997 algorithm.

**Key findings:**

- Every sequential map has **strictly monotonic lightness**, so data ordering
  is preserved even when colour perception is reduced.
- Single-hue and achromatic maps (`ash`, `monochrome`, `steel`, `copper`) are
  **inherently CVD-safe** because their discriminability comes from lightness
  differences, not hue.
- `dc.fiscal` deliberately pairs green and red for financial convention (profit / loss).
  If your audience may include colour-blind readers, prefer `dc.delta`
  (teal ↔ orange) or `dc.spectrum` (navy ↔ crimson) instead.

> **Recommendation**: For the highest accessibility, choose maps whose primary
> contrast channel is **lightness** rather than hue. The Single-Hue family
> and `dc.monochrome` are the safest choices.

---

## Rendering tips

- Set `vmin` / `vmax` yourself for stable colorbars across facets or animations.
- Reverse any map with the `_r` suffix (`dc.flame_r`).
- Hide colourbar outlines for a cleaner look: `cb.outline.set_visible(False)`.
- For diverging data, use symmetric limits and `extend="both"`.
- Use `imshow(..., interpolation="nearest")` for hard edges.
