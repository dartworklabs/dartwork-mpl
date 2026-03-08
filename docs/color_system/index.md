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
dartwork Color set prefixed with `dc.`—rendered as wide gradients sized for
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

dm.style.use("scientific")

# Named colors work anywhere matplotlib accepts a color string
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(dm.cm2in(9), dm.cm2in(5)), dpi=300)

x = np.linspace(0, 10, 200)
signal = np.sin(x) * np.exp(-0.08 * x)
ax1.plot(x, signal, color="tw.emerald500", linewidth=2, label="Emerald 500")
ax1.legend(fontsize=dm.fs(-1))

# Custom colormaps prefixed with 'dc.'
data = np.random.randn(50, 50).cumsum(axis=0)
im = ax2.imshow(data, cmap="dc.sunset")
plt.colorbar(im, ax=ax2, label="normalized response")

dm.simple_layout(fig)
```
