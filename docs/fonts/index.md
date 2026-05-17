# Fonts

A comprehensive hub for typography in dartwork-mpl. All bundled fonts are
automatically registered with matplotlib on import—no manual configuration
required.

```{toctree}
:maxdepth: 1
:titlesonly:
:hidden:

Font Families <families>
Font Utilities <utilities>
```

## Overview

dartwork-mpl includes **130 professional fonts** from **9 font families**, all
optimized for data visualization and publication-quality figures. When you
import the library, these fonts become immediately available to matplotlib.

**All nine families, one click apart.** dartwork-mpl bundles 130 font
variants across 9 families and registers every one with matplotlib on
import. The picker below cycles through them live — each tab swaps the
specimen below to that family's actual rendered samples, with the
correct weights, so what you see is exactly what `dm.style.use(...)`
will produce in a chart.

```{raw} html
:file: ../_static/fonts_picker.html
```

Need the long-form catalog with every weight and variant on a single
sheet? See [all font families →](families.md).

**Font Utilities.** Helper functions `fs()` and `fw()` for relative font sizing
and weighting, plus an interactive playground to test them out.
[Learn about font utilities →](utilities.md)

## Quick Start

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")  # Apply dartwork style (includes Roboto font)

fig, ax = plt.subplots()
ax.set_title("Publication-Ready Title", fontsize=dm.fs(4), fontweight=dm.fw(2))
ax.set_xlabel("X Axis Label", fontsize=dm.fs(0))
ax.set_ylabel("Y Axis Label", fontsize=dm.fs(0))

# Preview all available fonts
dm.plot_fonts(ncols=2, font_size=12)
plt.show()
```

## Key Features

**Auto-Registration**
: All 130 fonts are registered with matplotlib's font manager on import.
No manual font installation or configuration needed.

**Relative Sizing**
: `fs(n)` adjusts font sizes relative to your base style. `fw(n)` adjusts
weights in standardized steps. Both keep typography consistent across
different output formats.

**Math Support**
: Noto Sans Math provides comprehensive mathematical symbol coverage for
scientific notation and equations.

**Multi-Language**
: Paperlogy for Korean (한글), Noto Sans CJK for Japanese/Chinese — all bundled
and auto-registered. No system font installation needed.

## Bundled Fonts Summary

| Family                       | Variants | Primary Use Case                   |
| ---------------------------- | -------- | ---------------------------------- |
| **Roboto**                   | 4        | Default body text, general purpose |
| **Inter**                    | 20       | UI text, presentations             |
| **InterDisplay**             | 20       | Headings, titles                   |
| **Noto Sans**                | 15       | Multi-language documents           |
| **Noto Sans Condensed**      | 20       | Tables, dense layouts              |
| **Noto Sans SemiCondensed**  | 20       | Labels, legends                    |
| **Noto Sans Math**           | 1        | Mathematical expressions           |
| **Paperlogy**                | 4        | Korean (한글) text                 |

## Bundled Icon Fonts

In addition to text fonts, dartwork-mpl bundles **icon fonts** for use in
data visualizations. Icons are rendered as text using Unicode codepoints.

| Identifier       | Font                               | Icons  | Style            |
| ---------------- | ---------------------------------- | ------ | ---------------- |
| **`mdi`**        | Material Design Icons (Templarian) | 7,448+ | Filled + Outline |
| **`fa-solid`**   | Font Awesome 6 Free Solid          | 2,000+ | Filled           |
| **`fa-regular`** | Font Awesome 6 Free Regular        | 160+   | Outline          |
| **`fa-brands`**  | Font Awesome 6 Brands              | 460+   | Brand logos      |

```python
import dartwork_mpl as dm

mdi = dm.icon_font('mdi')          # Material Design Icons
fa  = dm.icon_font('fa-solid')     # Font Awesome 6 Solid

ax.text(0.5, 0.5, "\U000F050F",    # MDI: thermometer
        fontproperties=mdi, fontsize=20)
```

See [API Reference → Icon Font System](../api/icon.rst) for full details.
