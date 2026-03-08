# Colormaps

Single-column, wide gradients for every colormap bundled with dartwork-mpl. The
panels below stay legible on narrow viewports and match the naming used inside
matplotlib.

## Use them at a glance

- Any matplotlib name works (`viridis`, `plasma`, `twilight`, etc.) plus
  dartwork-mpl's own curated set prefixed with `dc.`.
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

```{raw} html
:file: images/colormaps_categorical.html
```

## Colorbar and rendering notes

- Prefer perceptually uniform ramps for quantitative data; reserve categorical
  bars for truly discrete labels.
- Align colorbars with the plot width and hide outlines to keep the single
  column clean (`cb.outline.set_visible(False)`).
- For diverging data, pick symmetric limits and set `extend="both"` so extreme
  values remain visible without clipping.
- Use `imshow(..., interpolation="nearest")` when you want hard edges; drop the
  argument for smooth gradients.
