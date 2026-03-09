# Colormaps

Single-column, wide gradients for every colormap bundled with dartwork-mpl. The
panels below stay legible on narrow viewports and match the naming used inside
matplotlib.

## Use them at a glance

- **Any Matplotlib name works natively**: You don't need `dartwork-mpl` to use standard scales (`cmap="viridis"`, `cmap="Blues"`, `cmap="tab10"`, etc.).
- **Curated DC namespace**: dartwork-mpl provides a focused set of strictly curated or custom-generated colormaps prefixed with `dc.` (e.g., `dc.ocean`, `dc.sunset`, `dc.balance`).
  - **OKLCH Custom Maps**: Interpolated purely in the perceptually uniform OKLCH space (e.g. `dc.emerald`, `dc.berry`, `dc.twilight_oklch`, `dc.steel`, `dc.flame`). Marked with an <span style="font-size: 0.65em; padding: 2px 4px; border-radius: 4px; background: #e3f2fd; color: #1565c0;">OKLCH</span> badge.
  - **Crameri Scientific Maps**: High-quality, perceptually uniform maps for scientific data (e.g. `dc.batlow`, `dc.vik`, `dc.roma`). Marked with a <span style="font-size: 0.65em; padding: 2px 4px; border-radius: 4px; background: #f5f5f5; color: #666;">Crameri</span> badge.
- Add `_r` to reverse a map (`dc.sunset_r`) when dark-to-light needs flipping.
- Set `vmin`/`vmax` yourself for stable colorbars across facets or animations.
- `dm.style.use("scientific")` keeps colorbar labels and ticks consistent with
  the rest of the style.

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

For discrete labels, `dartwork-mpl` fully supports and recommends the built-in [Matplotlib Qualitative colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html#qualitative) (such as `tab10`, `Set2`, `Dark2`, etc.).

Alternatively, you can manually build highly distinct categorical color palettes using discrete hex codes from the `dm.color` palettes.

## Colorbar and rendering notes

- Prefer perceptually uniform ramps for quantitative data; reserve categorical
  bars for truly discrete labels.
- Align colorbars with the plot width and hide outlines to keep the single
  column clean (`cb.outline.set_visible(False)`).
- For diverging data, pick symmetric limits and set `extend="both"` so extreme
  values remain visible without clipping.
- Use `imshow(..., interpolation="nearest")` when you want hard edges; drop the
  argument for smooth gradients.
