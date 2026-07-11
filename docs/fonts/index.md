# Fonts

dartwork-mpl ships **20 publication-ready fonts**, registered
with matplotlib the moment you `import dartwork_mpl`. Browse them below,
preview your own text, and copy a ready-to-paste `font.family` setup.

```{toctree}
:maxdepth: 1
:titlesonly:
:hidden:

Fonts <families>
Font Utilities <utilities>
Math & Special Characters <math_and_symbols>
```

## Font browser

Type your own preview text, narrow by script or style, and open any font
for its weight ladder and a ready-to-paste `rcParams` snippet. Every sample
is drawn by the font's own bundled file — what you see here is exactly
what your chart will render.

```{raw} html
:file: ../_static/fonts_browser.frag.html
```

## How registration works

dartwork-mpl bundles **230 text font files** organized into **20 documented
file groups**. Matplotlib registers those files as **18 matplotlib family names**
on `import dartwork_mpl`, with bundled copies promoted ahead of
same-named system fonts. Condensed and SemiCondensed Noto Sans files register
as Noto Sans with width metadata, so they are documented as file groups rather
than separate `font.family` names.

The family names below are the names to put in `font.family`. For every weight
and specimen sheet, see [Fonts](families.md).

## Quick Start

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")  # Roboto-led default chain
plt.rcParams["font.family"] = ["Inter", "Roboto", "Noto Sans Math"]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.set_title("Publication-ready title", fontsize=dm.fs(3), fontweight=dm.fw(2))
ax.set_xlabel("X axis", fontsize=dm.fs(0), fontweight=dm.fw(0))
ax.set_ylabel("Y axis", fontsize=dm.fs(0), fontweight=dm.fw(0))
dm.simple_layout(fig)
```

Use relative helpers for typography that tracks the active preset:

```python
ax.text(
    0.5,
    0.5,
    "annotation",
    fontsize=dm.fs(-1),
    fontweight=dm.fw(1),
)
```

For monospace Latin plus monospaced Hangul, lead with the Latin mono and keep
D2Coding as the Korean fallback:

```python
plt.rcParams["font.family"] = ["JetBrains Mono", "D2Coding"]
```

Source Serif 4 is deliberately opt-in; use it when a journal, report, or book
needs a serif voice:

```python
plt.rcParams["font.family"] = ["Source Serif 4", "Noto Sans Math"]
```

## Roles

The browser's role badges follow this table; use it as the print-friendly summary.

| Role | Default | Alternates | When to pick |
| --- | --- | --- | --- |
| Body | Roboto | Inter, IBM Plex Sans, Source Sans 3, Noto Sans | General chart labels, ticks, legends, and captions. |
| Display | Inter Display | — | Large titles, section heads, and poster-scale numbers. |
| Korean body | Paperlogy | Pretendard, Noto Sans CJK KR | Hangul-first and bilingual figures. |
| Serif | Source Serif 4 | — | Opt-in journal, report, or book figures that need a serif voice. |
| Mono | JetBrains Mono | IBM Plex Mono, Roboto Mono, Source Code Pro | Code, timestamps, aligned values, and dense numeric columns. |
| Korean mono | D2Coding | — | Monospaced Hangul code blocks and aligned Korean tables. |
| Fallback tail | Noto Sans Math | Noto Sans Symbols, Noto Sans Symbols 2 | Math operators, arrows, signs, and symbol coverage at the end of the fallback chain. |

## Typography Matrix

```{raw} html
:file: ../_static/typography_matrix.html
```

## Full Specimens

The full static specimen catalog lives in [Fonts](families.md). For
the reasoning behind the font roles, fallback chain, and numeric-axis gates,
see [Design rationale › Typography](../color_system/design-rationale.md#typography-rationale).
