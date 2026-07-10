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
Math & Special Characters <math_and_symbols>
```

## Overview

dartwork-mpl bundles **220 text font files** organized into **20 documented
file groups** for data visualization and publication figures. Matplotlib
registers those files as **18 matplotlib family names** on
`import dartwork_mpl`, and bundled entries win same-named system-font ties —
no manual font installation or configuration required.

The difference is intentional: file groups describe the shipped assets, while
matplotlib family names describe what you put in `font.family`. Condensed and
SemiCondensed Noto Sans files register as Noto Sans with their width metadata,
so choose them through the style/fallback chain rather than by a separate
family name.

For why these families, roles, and fallback gates ship together, see
[Design rationale › Typography](../color_system/design-rationale.md#typography-rationale).

**Every family in chart context.** The chart-context font explorer below pairs
one real matplotlib chart with a compact browser specimen for every registered
family. The real matplotlib chart uses the selected family in
`dm.style.use("scientific")` defaults; Weight, Size, and Italic controls apply
only to the specimen panel before copying the matching matplotlib idiom.

```{raw} html
:file: ../_static/font_explorer.html
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
family_chain = plt.rcParams["font.family"]
plt.rcParams["font.family"] = [
    "Inter",
    *[family for family in family_chain if family != "Inter"],
]  # optional: lead with any bundled family while preserving fallbacks

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
: All 220 font files are registered with matplotlib's font manager on
`import dartwork_mpl`. Bundled fonts are promoted ahead of same-named
system copies, so figures render with the shipped assets wherever possible.

**Relative Sizing**
: `fs(n)` adjusts font sizes relative to your base style. `fw(n)` adjusts
weights in standardized steps. Both keep typography consistent across
different output formats.

**Math & Symbols**
: Noto Sans Math powers the `$…$` mathtext stack (with STIX fallback), and
the plain-text fallback chain — Noto Sans Math plus Noto Sans Symbols 1/2 —
renders bare symbols (→ ± ℃ ∑ σ ⚠ ✓ ★) in labels without tofu. See
[Math & special characters →](math_and_symbols.md).

**Multi-Language**
: Pretendard and Paperlogy for Korean (한글), Noto Sans CJK for
Japanese/Chinese — all bundled and auto-registered. No system font
installation needed.

**Monospace**
: Four fixed-width families for tabular figures, code, and aligned labels —
IBM Plex Mono, JetBrains Mono, Source Code Pro, and Roboto Mono (each pairs
with its sans sibling).

## Bundled Fonts Summary

Every row below describes a documented file group. Most rows are also exact
matplotlib family names; the two Noto Sans width groups are bundled files that
register under the `Noto Sans` family name. All are SIL Open Font License or
Apache-2.0; the license texts are bundled under `asset/font/licenses/`.

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
| **Noto Sans Symbols**        | 1     | Plain-text symbol fallback (arrows) |
| **Noto Sans Symbols 2**      | 1     | Plain-text symbol fallback (⚠ ✓ ★) |

The last three families (Noto Sans Math, Noto Sans Symbols 1/2) are
symbol-fallback faces — they back the per-glyph fallback chain rather than
being picked as a body typeface. See
[Math & special characters](math_and_symbols.md).

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
