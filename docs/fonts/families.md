# Font Families

dartwork-mpl bundles 9 professional font families with a total of 130 font
variants. Each family is optimized for different use cases in data visualization.

## Font Selection Guide

Not sure which font to use? Pick based on your primary need:

| Need                         | Recommended Font           | Why                                         |
| ---------------------------- | -------------------------- | ------------------------------------------- |
| **General chart text**       | Roboto (default)           | Clean, legible at all sizes                 |
| **UI-style dashboards**      | Inter                      | Tall x-height, excellent screen readability |
| **Titles & headings**        | InterDisplay               | Tighter spacing optimized for large text    |
| **Dense tables / legends**   | Noto Sans Condensed family | Same readability, narrower footprint        |
| **Korean text (한글)**       | Paperlogy                  | Native Korean design, 9 weights             |
| **CJK (日本語 / 中文)**      | Noto Sans CJK              | Comprehensive CJK glyph coverage            |
| **Math / scientific**        | Noto Sans Math             | Full symbol set: ∑ ∫ √ ∞ π θ α β γ          |
| **Multi-language documents** | Noto Sans                  | Broadest Unicode coverage                   |

## Multi-Language Support

All fonts below are **bundled** — no system font installation required:

```{raw} html
:file: _generated/multilang.html
```

---

## Roboto (Default)

```{raw} html
:file: _generated/roboto.html
```

Google's flagship sans-serif typeface and the **default font in dartwork-mpl**.
Roboto features friendly, open curves while maintaining a mechanical skeleton,
making it highly legible at all sizes.

**Variants:** 15 (Thin, Light, Regular, Medium, Bold, Black + Italics)\
**Author:** Christian Robertson · **License:** [Apache 2.0](https://fonts.google.com/specimen/Roboto)

**Best For:**

- General-purpose body text
- Axis labels and tick marks
- Legends and annotations

**Usage:**

```python
import dartwork_mpl as dm

dm.style.use("scientific")  # Roboto Light (300) is already the default
```

---

## Inter

```{raw} html
:file: _generated/inter.html
```

A modern sans-serif typeface designed specifically for computer screens. Inter
features a tall x-height for improved readability at small sizes and includes
many OpenType features.

**Variants:** 20 (Thin through Black, with Italics)\
**Author:** [Rasmus Andersson](https://rsms.me/inter/) · **License:** [OFL 1.1](https://github.com/rsms/inter)

**Best For:**

- UI-style visualizations
- Presentations and slides
- Screen-first publications

**Usage:**

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")
plt.rcParams['font.family'] = 'Inter'  # Override just the font family
```

---

## InterDisplay

```{raw} html
:file: _generated/interdisplay.html
```

The display variant of Inter, optimized for larger sizes. Features tighter
letter-spacing and refined details that shine at headline sizes.

**Variants:** 20 (Thin through Black, with Italics)\
**Author:** [Rasmus Andersson](https://rsms.me/inter/) · **License:** [OFL 1.1](https://github.com/rsms/inter)

**Best For:**

- Figure titles
- Section headings
- Large callout text

**Usage:**

```python
# Use InterDisplay for titles only, keep default font for body
ax.set_title("Main Title", fontfamily='Inter Display', fontsize=dm.fs(6))
```

---

## Noto Sans

```{raw} html
:file: _generated/notosans.html
```

Google's Noto Sans provides harmonious typography across hundreds of languages.
The name "Noto" comes from "No Tofu"—the goal of eliminating the blank boxes
(tofu) that appear when a font lacks a glyph.

**Variants:** 15 (ExtraLight through Black, with Italics)\
**Author:** Google · **License:** [OFL 1.1](https://fonts.google.com/noto/specimen/Noto+Sans)

**Best For:**

- Multi-language documents
- International publications
- Unicode-heavy content

**Usage:**

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")
plt.rcParams['font.family'] = 'Noto Sans'
```

---

## Condensed Variants

The Noto Sans family includes three condensed variants ([Google Noto](https://fonts.google.com/noto), OFL 1.1).
Choose based on how much horizontal space you need to save:

### Noto Sans Condensed

```{raw} html
:file: _generated/notosans_condensed.html
```

**Variants:** 20 (Thin through Black, with Italics)
**Best For:** Tables with many columns, dense data visualizations

### Noto Sans SemiCondensed

```{raw} html
:file: _generated/notosans_semicondensed.html
```

**Variants:** 20 (Thin through Black, with Italics)
**Best For:** Legends with many entries, compact labels

### Noto Sans ExtraCondensed

```{raw} html
:file: _generated/notosans_extracondensed.html
```

**Variants:** 20 (Thin through Black, with Italics)
**Best For:** Very tight axis labels, narrow figure margins

**Usage (condensed for tick labels):**

```python
import dartwork_mpl as dm

dm.style.use("scientific")

fig, ax = plt.subplots()
# Switch to condensed only where space is tight
for label in ax.get_xticklabels():
    label.set_fontfamily('Noto Sans Condensed')
```

---

## Noto Sans Math

```{raw} html
:file: _generated/notosansmath.html
```

A dedicated font for mathematical typesetting. Noto Sans Math provides
comprehensive coverage of mathematical symbols, operators, and special
characters used in scientific notation.

**Variants:** 1 (Regular only)\
**Author:** Google · **License:** [OFL 1.1](https://fonts.google.com/noto/specimen/Noto+Sans+Math)

**Best For:**

- Scientific equations
- Mathematical notation
- Greek letters and symbols

**Usage in dartwork-mpl:**

Noto Sans Math is automatically configured for mathtext rendering by all
dartwork-mpl styles — no manual setup needed:

```python
import dartwork_mpl as dm

dm.style.use("scientific")

# Math text just works
ax.set_xlabel(r'$\alpha = \frac{\Delta x}{\Delta t}$')
ax.set_ylabel(r'$\sum_{i=1}^{n} x_i^2$')
```

---

## Paperlogy

```{raw} html
:file: _generated/paperlogy.html
```

A clean, professional typeface designed specifically for documents and papers.
Paperlogy offers excellent readability in dense text environments typical of
academic and business publications. **Includes full Korean (한글) glyph support.**

**Variants:** 9 (Thin through Black)\
**Author:** [Freesentation](https://freesentation.blog/paperlogyfont) · **License:** OFL 1.1

**Best For:**

- Korean-language charts and reports
- Academic papers
- Professional documents

**Usage:**

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")
plt.rcParams['font.family'] = 'Paperlogy'

fig, ax = plt.subplots()
ax.set_title("분기별 매출 추이", fontweight=dm.fw(4))
ax.set_xlabel("분기")
ax.set_ylabel("매출액 (억원)")
```

---

## Font Weight Reference

All font families (except Noto Sans Math) include multiple weights:

| Weight Name | Numeric Value | Description              |
| ----------- | ------------- | ------------------------ |
| Thin        | 100           | Extremely light          |
| ExtraLight  | 200           | Very light               |
| Light       | 300           | Light (dartwork default) |
| Regular     | 400           | Normal                   |
| Medium      | 500           | Slightly bold            |
| SemiBold    | 600           | Semi-bold                |
| Bold        | 700           | Bold                     |
| ExtraBold   | 800           | Extra bold               |
| Black       | 900           | Maximum weight           |

**Using Weights:**

```python
import dartwork_mpl as dm

dm.style.use("scientific")  # Base weight = 300 (Light)

# Use the fw() helper for relative weight adjustments
ax.set_title("Title", fontweight=dm.fw(4))   # 300 + 400 = 700 (Bold)
ax.set_xlabel("Label", fontweight=dm.fw(0))  # 300 (base, Light)
```
