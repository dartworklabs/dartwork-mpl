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

dartwork-mpl bundles **204 text font files across 16 families** (sans-serif
plus four monospace), all optimized for data visualization and
publication-quality figures. They are registered with matplotlib's font
manager on `import dartwork_mpl`, so `plt.rcParams["font.family"] = "Inter"`
(or any bundled family) resolves immediately — no manual font installation
or configuration required.

**Every family, one click apart.** The picker below cycles through them
live — each tab swaps the specimen below to that family's actual rendered
samples, with the correct weights, so what you see is exactly what
`plt.rcParams["font.family"] = "..."` will produce in a chart.

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
: All 204 font files are registered with matplotlib's font manager on
`import dartwork_mpl`. No manual font installation or configuration needed.

**Relative Sizing**
: `fs(n)` adjusts font sizes relative to your base style. `fw(n)` adjusts
weights in standardized steps. Both keep typography consistent across
different output formats.

**Math Support**
: Noto Sans Math provides comprehensive mathematical symbol coverage for
scientific notation and equations.

**Multi-Language**
: Pretendard and Paperlogy for Korean (한글), Noto Sans CJK for
Japanese/Chinese — all bundled and auto-registered. No system font
installation needed.

**Monospace**
: Four fixed-width families for tabular figures, code, and aligned labels —
IBM Plex Mono, JetBrains Mono, Source Code Pro, and Roboto Mono (each pairs
with its sans sibling).

## Bundled Fonts Summary

Every family ships a full weight range (plus italics where the upstream
publishes them). All are SIL Open Font License or Apache-2.0; the license
texts are bundled under `asset/font/licenses/`.

| Family                       | Files | Primary use case                   |
| ---------------------------- | ----- | ---------------------------------- |
| **Roboto**                   | 12    | Default body text, general purpose |
| **Inter**                    | 18    | UI text, presentations             |
| **Inter Display**            | 18    | Headings, titles                   |
| **Source Sans 3**            | 14    | Humanist body text                 |
| **IBM Plex Sans**            | 14    | Technical / interface text         |
| **Noto Sans**                | 18    | Multi-language documents           |
| **Noto Sans SemiCondensed**  | 18    | Labels, legends                    |
| **Noto Sans Condensed**      | 18    | Tables, dense layouts              |
| **Pretendard**               | 9     | Korean (한글) + Latin              |
| **Paperlogy**                | 9     | Korean (한글) text                 |
| **Noto Sans CJK KR**         | 1     | CJK (한·중·일) coverage            |
| **IBM Plex Mono**            | 14    | Monospace, tabular figures         |
| **JetBrains Mono**           | 16    | Monospace, code / dense tables     |
| **Source Code Pro**          | 14    | Monospace, pairs with Source Sans  |
| **Roboto Mono**              | 10    | Monospace, pairs with Roboto       |
| **Noto Sans Math**           | 1     | Mathematical expressions           |

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
