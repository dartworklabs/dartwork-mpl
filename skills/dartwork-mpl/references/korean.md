# Plot text language and Korean presets

Read this when Korean (or another non-Latin script) appears on the figure.

Text on the figure follows the document the figure goes into: a Korean report
gets Korean labels, a paper for an English journal gets English ones. When
that is unknown, follow the language of the request's own labels and data.
Data values (city names, categories) stay as given, and an edit keeps the
language the figure already has.

Pick a `-kr` preset when any label, title, legend, annotation or data value
on the figure is Korean: `scientific-kr`, `report-kr`, `presentation-kr`,
`minimal-kr`, `poster-kr`, `web-kr`, `dark-kr`. It keeps the base preset's
sizes and draws Hangul in Paperlogy, numerals and Latin letters in Inter
(both bundled).

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report-kr")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(["1월", "2월", "3월"], [-2.4, 0.6, 6.1])
ax.set(xlabel="월", ylabel="평균 기온 (°C)", title="1분기 서울 기온")
dm.simple_layout(fig)
dm.save_formats(fig, "output/temperature-kr", formats=("png", "pdf"))
plt.close(fig)
```

- Apply the `-kr` preset before creating the figure; switching later leaves
  existing text in the old font.
- Mixed Korean and English text in one label is fine.
- Write a unit's symbol itself next to Korean: `"면적 (m²)"`, `"효율 η (%)"`.
  Mathtext draws a whole string in one font, so `dm.simple_layout` sets
  `"면적 (m$^2$)"` in Paperlogy, numerals included, and says so; drawn
  without `dm.simple_layout`, that label loses its Hangul.
- See [role colours](colors.md#named-colours) for the Korean gain and loss convention.
- `dm.style.context("report-kr")` scopes the preset to one block; save the
  figure inside it.
- Do not set `font.family` by hand; the preset's family list holds the
  bundled math and symbol fallbacks.
- Korean numbers: `dm.format_axis_myriad(ax)` counts the ticks in 만/억/조
  (`50만 … 250만`); a Korean (`-kr`) preset already does from 1,000,000 on
  an axis you do not format.

## Other languages

Latin, Greek, Cyrillic, Korean and common Japanese text render with the
bundled fonts. Chinese, Arabic, Thai, Devanagari and other scripts can lack
glyphs: matplotlib warns `Glyph … missing from font(s)` and the PNG shows
boxes. Tell the user which text cannot render and ask which installed font
to use.
