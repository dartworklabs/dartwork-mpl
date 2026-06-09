# Styles and Presets

dartwork-mpl ships with **7 curated presets** that configure fonts, line
weights, spine visibility, and color scheme in one call — plus Korean (`-kr`)
variants for each, giving **14 presets** total.

## Quick start

```python
import dartwork_mpl as dm

dm.style.use("scientific")     # papers & journals
dm.style.use("report")         # reports & dashboards
dm.style.use("minimal")        # Tufte-style, data-ink focus
dm.style.use("presentation")   # slides
dm.style.use("poster")         # conference posters
dm.style.use("web")            # web pages & documentation
dm.style.use("dark")           # dark backgrounds (Jupyter, dark slides)
dm.style.use("scientific-kr")  # any preset + Korean fonts
```

## Interactive comparison

A live carousel renders the **same** plot — measured battery-capacity
retention plus a forecast band and an annotated end-of-life threshold —
under each preset. The slide advances every five seconds (paused on
hover, focus, or with `prefers-reduced-motion`). Use the arrows, dots,
or ← / → arrow keys for manual control. Watch the title weight, axis
spines, tick density, and palette shift between presets:

```{raw} html
:file: images/preset_compare.html
```

---

## Preset details

All presets share a common **`base` layer** that sets thin lines (`0.5 pt`),
no grid, `Roboto` font family, and `300` font weight. Each preset then
overrides specific values on top.

### Font size comparison

| rcParam           | scientific | report | minimal | presentation | poster | web  | dark |
| ----------------- | ---------- | ------ | ------- | ------------ | ------ | ---- | ---- |
| `font.size`       | 7.5        | 8.0    | 7.5     | 10.5         | 12.0   | 11.0 | 11.0 |
| `axes.titlesize`  | 8.5        | 9.0    | 8.5     | 11.5         | 14.0   | 13.0 | 13.0 |
| `axes.labelsize`  | 7.5        | 8.0    | 7.5     | 10.5         | 12.0   | 11.0 | 11.0 |
| `xtick.labelsize` | 7.0        | 7.0    | 7.0     | 10.0         | 11.0   | 10.0 | 10.0 |
| `legend.fontsize` | 5.5        | 6.0    | 5.5     | 8.5          | 9.0    | 8.5  | 8.5  |

All sizes in **pt**. Every preset uses `font.weight: 300` and
`axes.labelweight: 400` uniformly.

### Axes decoration comparison

| Property         | scientific | report | minimal | presentation | poster | web    | dark      |
| ---------------- | ---------- | ------ | ------- | ------------ | ------ | ------ | --------- |
| Top/right spines | ✓          | ✗      | all off | ✓            | ✗      | ✗      | ✗         |
| Tick marks       | ✓          | ✓      | none    | ✓            | large  | ✓      | ✓         |
| Lines            | 0.5 pt     | 0.5 pt | 0.5 pt  | 0.5 pt       | 1.5 pt | 0.5 pt | 0.5 pt    |
| `axes.linewidth` | 0.3        | 0.3    | 0       | 0.3          | 0.5    | 0.4    | 0.3       |
| Background       | white      | white  | white   | white        | white  | white  | `#1e1e1e` |

---

### `scientific` — papers & journals

The default preset. Compact font sizes designed for single-column journal
figures at 3.5″ width. All four spines are visible to match traditional
academic conventions.

```python
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
```

**Best for:** LaTeX papers, IEEE/Elsevier submissions, technical notes.

---

### `report` — reports & dashboards

Slightly larger fonts than `scientific`, with **top and right spines hidden**
for a cleaner, less boxy feel. Ideal for PDF reports, internal memos, or
dashboard exports.

```python
dm.style.use("report")
```

**Best for:** Business reports, data dashboards, executive summaries.

---

### `minimal` — Tufte-style data focus

Inspired by Edward Tufte's principle of _maximizing the data-ink ratio_.
Removes all spines, tick marks, and grid lines — only the data and labels
remain. Uses compact `scientific` font sizes.

```python
dm.style.use("minimal")
```

**Best for:** Infographics, editorial charts, minimalist data storytelling.

---

### `presentation` — slides

Large fonts (10.5 pt base) so text remains readable when projected. All four
spines are kept to give charts clear boundaries on busy slide backgrounds.

```python
dm.style.use("presentation")
```

**Best for:** PowerPoint/Keynote slides, screen-shared figures, talks.

---

### `poster` — conference posters

The largest font scale (12 pt base, 14 pt titles) with **thicker lines**
(1.5 pt) and larger tick marks (4 pt). Top/right spines hidden for a modern
look. Designed to be readable from 1–2 meters away.

```python
dm.style.use("poster")
fig, ax = plt.subplots(figsize=dm.figsize("20cm", "standard"))  # poster-sized panel
```

**Best for:** A0/A1 conference posters, large wall displays, signage.

---

### `web` — web & documentation

Tuned for on-screen readability at typical browser zoom levels. Fonts are
larger than `scientific` (11 pt) but smaller than `poster`. Top/right spines
hidden. This is the preset used for the dartwork-mpl docs themselves.

```python
dm.style.use("web")
```

**Best for:** Sphinx/MkDocs documentation, blog posts, Jupyter notebooks
shared as HTML, README figures.

---

### `dark` — dark mode

Inverts the color scheme for dark backgrounds (`#1e1e1e`). Uses `web` font
sizes (11 pt) for screen readability, with top/right spines hidden. Spine
and tick colors are set to subtle grays so they don't overpower the data.

```python
dm.style.use("dark")
```

**Best for:** Dark Jupyter themes, dark-mode slides, dark-themed web pages.

---

## Korean variants (`-kr`)

Append `-kr` to any preset name to swap the font family to Korean-capable
typefaces:

| Layer       | Primary font fallback chain                           |
| ----------- | ----------------------------------------------------- |
| **English** | Roboto → Lato → Inter → Open Sans → Arial             |
| **Korean**  | Paperlogy → Noto Sans CJK KR → Pretendard → Gothic A1 |

```python
dm.style.use("report-kr")       # report sizing + Korean fonts
dm.style.use("dark-kr")         # dark theme + Korean fonts
```

All 7 base presets have a `-kr` variant: `scientific-kr`, `report-kr`,
`minimal-kr`, `presentation-kr`, `poster-kr`, `web-kr`, `dark-kr`.

## How presets work

Presets are built by **stacking** style layers — each subsequent layer
overrides only the values it cares about:

```
scientific  =  base  →  font-scientific
report      =  base  →  font-report
minimal     =  base  →  font-minimal   →  theme-minimal
dark        =  base  →  font-web       →  theme-dark
dark-kr     =  base  →  font-web       →  theme-dark    →  lang-kr
```

The `base` layer provides shared defaults (line widths, tick sizes, Roboto
font family). Font layers (`font-*`) configure sizes and spine visibility.
Theme layers (`theme-*`) override colors or chrome. `lang-kr` swaps font
families. You don't need to manage layers manually — `dm.style.use()` handles
the stacking.

## Advanced: custom stacking

For use cases not covered by presets, you can compose layers directly:

```python
# Dark report — report fonts + dark colors
dm.style.stack(["base", "font-report", "theme-dark"])

# Minimal with large fonts — web sizes + no chrome
dm.style.stack(["base", "font-web", "theme-minimal"])

# List all available style layers
dm.list_styles()
# → ['base', 'font-scientific', 'font-report', 'font-minimal',
#     'font-presentation', 'font-poster', 'font-web', 'theme-minimal',
#     'theme-dark', 'lang-kr', 'spine-no', 'spine-yes', ...]

# Inspect any single layer
dm.load_style_dict("font-web")
# → {'font.size': 11.0, 'axes.titlesize': 13.0, ...}
```

## Standalone style layers

Individual layers for use with `style.stack`:

| Layer           | Purpose                                            |
| --------------- | -------------------------------------------------- |
| `base`          | Shared defaults (line widths, Roboto, tick sizes)  |
| `font-*`        | Font sizes + spine visibility for each preset      |
| `theme-dark`    | Dark color scheme (backgrounds, text, tick colors) |
| `theme-minimal` | Removes all spines, ticks, and grid lines          |
| `lang-kr`       | Korean font family override                        |
| `spine-no`      | Hides top + right spines                           |
| `spine-yes`     | Shows all four spines                              |

> **Legacy note:** `dmpl` and `dmpl_light` predate the current preset system
> and are retained for backwards compatibility. For new projects, use a named
> preset instead.

## See also

- **Next →** [Colors and Colormaps](colors.md) — named-color tokens, palettes, and the bundled `dc.*` colormaps
- [API › Style Management](../api/style) for all helper functions and arguments
- [Fonts](../fonts/index) for the complete list of bundled typefaces
