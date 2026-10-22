# Korean plot text

Pick a `-kr` preset when any label, title, legend or annotation is Korean:
`scientific-kr`, `report-kr`, `presentation-kr`, `minimal-kr`, `poster-kr`,
`web-kr`, `dark-kr`. It keeps the base preset's sizes and adds bundled
Korean fonts (Paperlogy first, Noto Sans CJK KR as fallback). The chat
language does not decide it: an English figure requested in Korean uses the
plain preset.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report-kr")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(["1월", "2월", "3월"], [-2.4, 0.6, 6.1], color="dc.blue5")
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
