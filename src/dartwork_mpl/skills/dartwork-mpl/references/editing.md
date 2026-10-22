# Editing an existing figure

"Make the axis labels bigger", "move the legend", "only the left panel":
each names artists. Find them, change only the asked property, keep the
data, preset, canvas size, colours, legend and every other property, then
save under a new stem and look at the result.

## Find the target

The figure below stands in for the user's existing script.

```python
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
import dartwork_mpl as dm

dm.style.use("report")
x = np.linspace(0, 10, 101)
fig, (left, right) = plt.subplots(
    1, 2, figsize=dm.figsize("17cm", "7cm"), gridspec_kw={"wspace": 0.35}
)
left.plot(x, np.sin(x), label="Measured")
left.plot(x, np.sin(x) * 0.9, label="Model")
left.set(title="Response", xlabel="Time (s)", ylabel="Signal")
left.legend()
right.plot(x, np.sin(x) * 0.1, color="dc.gray5")
right.set(title="Error", xlabel="Time (s)")
dm.simple_layout(fig)

error_ax = next(a for a in fig.axes if a.get_title() == "Error")
model = next(ln for ln in left.get_lines() if ln.get_label() == "Model")
titles = [t for t in fig.findobj(Text) if t.get_text() == "Response"]
print(type(model).__name__, model.get_linewidth(), model.get_color())
```

`artist.properties()`, the getters and `help(type(artist))` list what an
artist accepts. Axis labels (`ax.xaxis.label`) are not tick labels
(`ax.get_xticklabels()`).

## Common requests

| Request | Change |
|---|---|
| axis labels one step bigger | each label: `t.set_fontsize(t.get_fontsize() + 1)` |
| ticks smaller | `ax.tick_params(labelsize=dm.fs(-1))` |
| one line thicker | `line.set_linewidth(line.get_linewidth() + 0.5)` |
| emphasise one series | others `set_color("dc.gray4")`, target `set_zorder(3)` |
| move the legend | `ax.legend(loc="lower right")` or `dm.place_legend(ax)` |
| label line ends instead of a legend | `ax.annotate(...)` at each last point, remove legend |
| fewer ticks | `ax.xaxis.set_major_locator(MaxNLocator(nbins=5))` |
| 12000 → 12k | `dm.format_axis_si(ax)` |
| bigger or wider figure | rebuild with a new `dm.figsize`; keep the preset |

```python
for t in (left.xaxis.label, left.yaxis.label):
    t.set_fontsize(t.get_fontsize() + 1)
model.set_linewidth(model.get_linewidth() + 0.5)
error_ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
dm.simple_layout(fig)            # text grew: refit with the script's own arguments
dm.save_formats(fig, "output/figure-v2", formats=("png",))
plt.close(fig)
```

Repeated "one more step" adds to the current value again; it does not reset
to `dm.fs(1)`. An absolute request ("12 pt") is set exactly.

## "Make it look better" / "더 보기 좋게"

A vague request is a normal request. Keep the preset's fonts, spines and
grid, the data and the chart type; improve what the figure communicates.

1. Render and look. Name the two or three biggest problems.
2. Fix in this order, only what the image shows:
   - clipped or overlapping text: `dm.simple_layout(fig)`,
     `dm.wrap_axis_labels(fig)`, shorter tick labels (`dm.format_axis_si`),
     fewer ticks, `dm.rotate_tick_labels(ax)` as a last resort;
   - legend over data: `dm.place_legend(ax)`, a legend outside, or direct
     labels at line ends;
   - many competing colours: one accent, the rest `dc.gray4`;
   - unclear labels: add units, "Time (s)";
   - cramped or empty panels: aspect token, `hspace` / `wspace`.
3. Save as the next version, look again, and list each change in one line.

Ask one short question only when the purpose (paper, report or slides) is
unknown and would change the answer.
