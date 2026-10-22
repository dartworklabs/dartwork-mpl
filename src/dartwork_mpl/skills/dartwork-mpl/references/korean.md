# Plot text language and Korean presets

Plot text is English by default, whatever language the chat uses: a figure
requested in Korean gets English titles and labels and the plain preset.
Write Korean, or any other language, when the user asks for it. Data values
(city names, categories) stay as given, and an edit keeps the language the
figure already has.

Pick a `-kr` preset when any label, title, legend, annotation or data value
on the figure is Korean: `scientific-kr`, `report-kr`, `presentation-kr`,
`minimal-kr`, `poster-kr`, `web-kr`, `dark-kr`. It keeps the base preset's
sizes and adds bundled Korean fonts (Paperlogy first, Noto Sans CJK KR as
fallback).

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
- `dm.style.context("report-kr")` scopes the preset to one block.
- Do not set `font.family` by hand; the preset's family list holds the
  bundled math and symbol fallbacks.
- Korean number formats: `dm.format_axis_myriad(ax)` (만/억 units) and
  `dm.format_axis_year(ax)` (`25년`).

## Other languages

Latin, Greek, Cyrillic, Korean and common Japanese text render with the
bundled fonts. Chinese, Arabic, Thai, Devanagari and other scripts can lack
glyphs: matplotlib warns `Glyph … missing from font(s)` and the PNG shows
boxes. Tell the user which text cannot render and ask which installed font
to use.
