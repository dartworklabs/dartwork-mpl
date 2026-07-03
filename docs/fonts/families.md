# Font Families

dartwork-mpl bundles 16 professional font families with a total of 204 font
files. Each family is optimized for different use cases in data
visualization. This page profiles the core families in depth; for a
one-click specimen of **every** family — including Pretendard, Source
Sans 3, IBM Plex Sans, and the four monospace families (IBM Plex Mono,
JetBrains Mono, Source Code Pro, Roboto Mono) — use the
[interactive font picker](../_static/fonts_picker.html) or the
[font explorer](index.md).

## Why fonts matter

The right typeface can transform a chart from amateur to professional. Here's
the same data plotted with default matplotlib fonts (left) and dartwork-mpl fonts (right):

**Compare — default matplotlib (top) vs dartwork-mpl (bottom):**

::::{grid} 1
:gutter: 2

:::{grid-item}
![Default matplotlib](_generated/before_default.svg)
:::

:::{grid-item}
![With dartwork-mpl](_generated/after_dartwork.svg)
:::

::::

## Font Selection Guide

Not sure which font to use? Pick based on your primary need:

| Need                         | Recommended Font           | Why                                         |
| ---------------------------- | -------------------------- | ------------------------------------------- |
| **General chart text**       | Roboto (default)           | Clean, legible at all sizes                 |
| **UI-style dashboards**      | Inter                      | Tall x-height, excellent screen readability |
| **Titles & headings**        | Inter Display              | Tighter spacing optimized for large text    |
| **Dense tables / legends**   | Noto Sans Condensed family | Same readability, narrower footprint        |
| **Korean text (한글)**       | Paperlogy                  | Native Korean design, 9 weights             |
| **CJK (日本語 / 中文)**      | Noto Sans CJK              | Comprehensive CJK glyph coverage            |
| **Math / scientific**        | Noto Sans Math             | Full symbol set: ∑ ∫ √ ∞ π θ α β γ          |
| **Multi-language documents** | Noto Sans                  | Broadest Unicode coverage                   |

To apply any row's font, set matplotlib's `font.family` to the exact
registered name (as it appears in the
[Bundled Fonts Summary](index.md#bundled-fonts-summary) — e.g. `Inter Display`
with a space, not `InterDisplay`):

```python
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Inter"   # or any family name from the table
```

Fine-tune size and weight next → [Font Utilities › Custom Font Configuration](utilities.md#custom-font-configuration).

## Fonts in Chart Context

Each font plays a specific role in a chart. This annotated example shows which
font is used where:

```{image} _generated/chart_context.svg
:alt: Chart fonts in context
:align: center
```

> **Title** uses InterDisplay Bold for maximum impact. **Axis labels** use
> Roboto Regular for clear identification. **Tick marks** use Roboto Light
> for unobtrusive readability.

## Font Pairing Recommendations

Curated combinations for common chart styles:

| Style         | Title                 | Body            | Ticks               | Why it works                                 |
| ------------- | --------------------- | --------------- | ------------------- | -------------------------------------------- |
| **Academic**  | InterDisplay SemiBold | Roboto Light    | Roboto Light        | High contrast between display and body       |
| **Dashboard** | Inter Medium          | Inter Regular   | Noto Sans Condensed | Uniform feel, condensed ticks save space     |
| **Poster**    | InterDisplay Bold     | Roboto Regular  | Roboto Regular      | Large-scale readability                      |
| **Korean**    | Paperlogy SemiBold    | Paperlogy Light | Paperlogy Light     | Native Korean design, consistent weight axis |

## Size Scale

Common size ranges used in charts, mapped to `fs()` offsets:

| Role        | Typical pt | `fs()` offset        | Notes                                      |
| ----------- | ---------- | -------------------- | ------------------------------------------ |
| Tick labels | 5.5–7      | `fs(-2)` to `fs(-1)` | Keep light (300) for minimal distraction   |
| Axis labels | 7.5–10.5   | `fs(0)`              | Base size — matches the active preset      |
| Legend      | 5.5–9      | `fs(-2)` to `fs(1)`  | Smaller than axis labels                   |
| Subtitles   | 9–13       | `fs(2)` to `fs(4)`   | Medium weight (500) adds hierarchy         |
| Titles      | 8.5–14     | `fs(1)` to `fs(6)`   | Use InterDisplay or bold weight for impact |

---

## Multi-Language Support

All fonts below are **bundled** — no system font installation required:

```{raw} html
:file: _generated/multilang.html
```

---

## Font Family Details

Every specimen below is rendered **live in your browser** using the actual
bundled font files — no images, no placeholders.

### Roboto (Default)

```{raw} html
:file: _generated/roboto_showcase.html
```

Google's flagship sans-serif typeface and the **default font in dartwork-mpl**.
Roboto features friendly, open curves while maintaining a mechanical skeleton,
making it highly legible at all sizes.

**Author:** Christian Robertson · **License:** [Apache 2.0](https://fonts.google.com/specimen/Roboto)

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/roboto.html
```

:::

---

### Inter

```{raw} html
:file: _generated/inter_showcase.html
```

A modern sans-serif typeface designed specifically for computer screens. Inter
features a tall x-height for improved readability at small sizes and includes
many OpenType features.

**Author:** [Rasmus Andersson](https://rsms.me/inter/) · **License:** [OFL 1.1](https://github.com/rsms/inter)

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/inter.html
```

:::

---

### InterDisplay

```{raw} html
:file: _generated/interdisplay_showcase.html
```

The display variant of Inter, optimized for larger sizes. Features tighter
letter-spacing and refined details that shine at headline sizes.

**Author:** [Rasmus Andersson](https://rsms.me/inter/) · **License:** [OFL 1.1](https://github.com/rsms/inter)

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/interdisplay.html
```

:::

---

### Noto Sans

```{raw} html
:file: _generated/notosans_showcase.html
```

Google's Noto Sans provides harmonious typography across hundreds of languages.
The name "Noto" comes from "No Tofu"—the goal of eliminating the blank boxes
(tofu) that appear when a font lacks a glyph.

**Author:** Google · **License:** [OFL 1.1](https://fonts.google.com/noto/specimen/Noto+Sans)

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/notosans.html
```

:::

---

### Condensed Variants

The Noto Sans family includes three condensed variants. Choose based on how much
horizontal space you need to save:

```{raw} html
:file: _generated/condensed_comparison.html
```

#### Noto Sans Condensed

```{raw} html
:file: _generated/notosans_condensed_showcase.html
```

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/notosans_condensed.html
```

:::

#### Noto Sans SemiCondensed

```{raw} html
:file: _generated/notosans_semicondensed_showcase.html
```

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/notosans_semicondensed.html
```

:::

---

### Noto Sans Math

```{raw} html
:file: _generated/notosansmath.html
```

A dedicated font for mathematical typesetting. Provides comprehensive coverage
of mathematical symbols, operators, and special characters.

**Variants:** 1 (Regular only)\
**Author:** Google · **License:** [OFL 1.1](https://fonts.google.com/noto/specimen/Noto+Sans+Math)

---

### Paperlogy

```{raw} html
:file: _generated/paperlogy_showcase.html
```

A clean, professional typeface designed for documents. Paperlogy offers excellent
readability in dense text environments. **Includes full Korean (한글) glyph
support.**

**Author:** [Freesentation](https://freesentation.blog/paperlogyfont) · **License:** OFL 1.1

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/paperlogy.html
```

:::

---

### Pretendard

```{raw} html
:file: _generated/pretendard_showcase.html
```

A modern geometric-humanist sans-serif with comprehensive Korean (한글) and
Latin coverage, drawing on the proportions of contemporary system-UI
typefaces. Pretendard keeps its clarity from caption to display sizes, which
makes it a natural first choice for bilingual Korean–English reports and
dashboards. **Full Korean (한글) glyph support across nine weights
(Thin → Black).**

**Author:** [Kil Hyungjin (길형진)](https://github.com/orioncactus/pretendard) · **License:** OFL 1.1

:::{admonition} All weights
:class: dropdown

```{raw} html
:file: _generated/pretendard.html
```

:::

---

## Font Weight Reference

<div class="dm-font-tester">
  <div class="dm-ft-header">
    <div class="dm-ft-title">Interactive Font Tester</div>
    <div class="dm-ft-controls">
      <select class="dm-ft-family" aria-label="Font Family">
        <option value="dm-Roboto">Roboto</option>
        <option value="dm-Inter">Inter</option>
        <option value="dm-InterDisplay">Inter Display</option>
        <option value="dm-NotoSans" selected>Noto Sans</option>
        <option value="dm-NotoSans_Condensed">Noto Sans Condensed</option>
        <option value="dm-Paperlogy">Paperlogy</option>
      </select>
      <select class="dm-ft-weight" aria-label="Font Weight">
        <option value="100">Thin (100)</option>
        <option value="200">ExtraLight (200)</option>
        <option value="300">Light (300)</option>
        <option value="400" selected>Regular (400)</option>
        <option value="500">Medium (500)</option>
        <option value="600">SemiBold (600)</option>
        <option value="700">Bold (700)</option>
        <option value="800">ExtraBold (800)</option>
        <option value="900">Black (900)</option>
      </select>
      <input type="number" class="dm-ft-size" value="28" min="8" max="72" aria-label="Font Size">
    </div>
  </div>
  <textarea class="dm-ft-textarea" rows="2" spellcheck="false">The dartwork designs beautiful data artworks since 2021.
데이터 시각화를 위한 전문 타이포그래피.</textarea>
</div>

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
