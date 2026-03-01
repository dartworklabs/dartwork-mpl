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

:::{figure} images/fonts_all_families.png
:alt: All available font families preview
:width: 100%

**All Font Families.** Nine curated font families covering everything from
general-purpose body text to mathematical expressions. Each family includes
multiple weights and styles.
[Explore all font families →](families.md)
:::

:::{figure} images/font_utilities.png
:alt: Font utility functions demonstration
:width: 100%

**Font Utilities.** Helper functions `fs()` and `fw()` for relative font sizing
and weighting, plus `plot_fonts()` for previewing all available fonts.
[Learn about font utilities →](utilities.md)
:::

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
dm.plot_fonts(ncols=3, font_size=12)
plt.show()
```

## Key Features

**Auto-Registration**
: All 130 fonts are automatically registered with matplotlib's font manager when
you import dartwork-mpl. No need for manual font installation or configuration.

**Professional Font Selection**
: Curated collection includes Roboto (default), Inter, Noto Sans family, and more—all
chosen for excellent legibility in charts and figures.

**Relative Sizing**
: Use `fs(n)` to adjust font sizes relative to your base style, keeping your
typography consistent across different output formats.

**Weight Flexibility**
: Use `fw(n)` to adjust font weights in standardized steps, perfect for creating
visual hierarchy in your figures.

**Math Support**
: Noto Sans Math provides comprehensive mathematical symbol coverage for
scientific notation and equations.

## Bundled Fonts Summary

| Family                       | Variants | Primary Use Case                   |
| ---------------------------- | -------- | ---------------------------------- |
| **Roboto**                   | 15       | Default body text, general purpose |
| **Inter**                    | 20       | UI text, presentations             |
| **InterDisplay**             | 20       | Headings, titles                   |
| **Noto Sans**                | 15       | Multi-language documents           |
| **Noto Sans Condensed**      | 20       | Tables, dense layouts              |
| **Noto Sans SemiCondensed**  | 20       | Labels, legends                    |
| **Noto Sans ExtraCondensed** | 20       | Axis labels, tight spaces          |
| **Noto Sans Math**           | 1        | Mathematical expressions           |
| **Paperlogy**                | 9        | Academic papers, reports           |

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

## Regenerating the Visuals

- All preview PNGs live in `docs/fonts/images/`.
- Run `python docs/fonts/generate_assets.py` to refresh assets after any changes.
- Exports are high-DPI for crisp rendering when embedded in documentation.
