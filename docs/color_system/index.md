# Color System

A single, scrollable hub for everything color-related in dartwork-mpl. Each
section below is a full-width preview; click through to the dedicated page if
you want the complete sheets and usage details.

```{toctree}
:maxdepth: 1
:titlesonly:
:hidden:

Colors <colors>
Colormaps <colormaps>
Color Space <space>
```

**Colors.** All named palettes ship as weight-aware labels you can drop straight
into matplotlib (`tw.blue500`, `md.red700`, `oc.gray6`, and more).

```{raw} html
:file: images/colors_opencolor.html
```

[Open the full color sheets →](colors.md)

---

**Colormaps.** Sequential, diverging, cyclical, and categorical ramps—plus the
dartwork-specific set prefixed with `dm.`—rendered as wide gradients sized for
slides and exports.

```{raw} html
:file: images/colormaps_sequential_multi_hue.html
```

[Browse the colormap panels →](colormaps.md)

## Quick start

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

dm.style.use("scientific")  # style + fonts
x = np.linspace(0, 10, 200)
signal = np.sin(x) * np.exp(-0.08 * x)

plt.plot(x, signal, color="tw.emerald500", linewidth=2.6, label="Emerald 500")
plt.imshow(np.outer(signal, signal), cmap="dm.sunset")
plt.colorbar(label="normalized response")
plt.legend()
plt.show()
```

## Regenerating the visuals

- All preview PNGs live in `docs/color_system/images/`.
- Sphinx runs `color_system/generate_assets.py` during a build; run it manually to
  refresh assets after editing colors or colormaps.
- Exports are high-DPI so the single-column layouts remain crisp when embedded.
