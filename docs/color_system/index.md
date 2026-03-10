# Color System

The color reference hub for dartwork-mpl. Browse complete palette sheets,
explore colormap collections, and dive into the `Color` class for
programmatic manipulation in perceptually uniform color spaces.

> **Looking for a quick how-to?** See the
> [Colors and Colormaps](../usage_guide/colors.md) guide for practical usage
> patterns, named color shortcuts, and mixing utilities.

```{toctree}
:maxdepth: 1
:titlesonly:
:hidden:

Palette Catalog <colors>
Colormap Catalog <colormaps>
Color Space & Manipulation <space>
```

---

## Named palette catalog

All named palettes rendered as full-width sheets — use `library.colorweight`
anywhere matplotlib accepts a color string (e.g. `tw.blue500`, `oc.gray6`).

```{raw} html
:file: images/colors_opencolor.html
```

[Open the full palette sheets →](colors.md)

---

## Colormap catalog

Sequential, diverging, cyclical, and categorical ramps — including
dartwork-mpl's own OKLCH-designed `dc.*` collection.

```{raw} html
:file: images/colormaps_sequential_multi_hue.html
```

[Browse all colormaps →](colormaps.md)

---

## Color class & interpolation

The `Color` class provides perceptually uniform manipulation in OKLab/OKLCH
space — adjust hue, saturation, and lightness with predictable results, and
build smooth custom gradients.

[Learn color space manipulation →](space.md)
