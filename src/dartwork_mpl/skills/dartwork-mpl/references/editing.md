# Editing an existing figure

Two kinds of request:

- **"Only X"** ("make the axis labels bigger", "move the legend", "thicker
  line for Model"): find exactly that artist, change only the asked
  property, and leave everything else as it was: data, preset, canvas size,
  colours, legend, other text, layout arguments.
- **Broad** ("make it look better", "더 보기 좋게", "clean this up"): keep
  the data, the preset and the chart type, fix what the rendered image
  shows, and list every change in your answer.

Either way: keep the original script and its outputs, write the revision as
a new script (`plot-v2.py`) with a new output stem (`figure-v2`), render it
and look at the PNG before you answer.

## Find the target with getters

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
left.set_title("Response")
left.set_title("(a)", loc="left")
left.set(xlabel="Time (s)", ylabel="Signal")
left.legend()
right.plot(x, np.sin(x) * 0.1, color="dc.gray5")
right.set(title="Error", xlabel="Time (s)")
dm.simple_layout(fig)

# A panel by its title; titles have three slots: loc="center", "left", "right".
error_ax = next(a for a in fig.axes if a.get_title() == "Error")
panel_a = next(a for a in fig.axes if a.get_title(loc="left") == "(a)")
# A series by its legend label.
model = next(ln for ln in panel_a.get_lines() if ln.get_label() == "Model")
# Any text by its content.
response = [t for t in fig.findobj(Text) if t.get_text() == "Response"]
print(model.get_linewidth(), model.get_color(), model.get_linestyle())
print(sorted(model.properties())[:8])   # every property the artist has
```

- Lines `ax.get_lines()`, bars and patches `ax.patches`, scatter and
  images `ax.collections` / `ax.images`, legend `ax.get_legend()`, axis
  labels `ax.xaxis.label` (not tick labels, which are `ax.get_xticklabels()`).
- `artist.properties()`, getters and `help(type(artist))` say what a
  setter accepts. Edit the existing artist; do not plot a second copy.
- If two artists match and the request does not say which, ask one short
  question.

## Common "only X" requests

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
for t in (panel_a.xaxis.label, panel_a.yaxis.label):
    t.set_fontsize(t.get_fontsize() + 1)
model.set_linewidth(model.get_linewidth() + 0.5)
error_ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
dm.simple_layout(fig)            # text grew: refit with the script's own arguments
dm.save_formats(fig, "output/figure-v2", formats=("png",))
plt.close(fig)
```

Repeated "one more step" adds to the current value again; it does not reset
to `dm.fs(1)`. An absolute request ("12 pt") is set exactly. Keep the
existing layout when the result still fits; refit only with the arguments
the script already used.

## Broad requests: "make it look better"

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
3. Keep the preset's fonts, spines and grid, the data and the chart type.
4. Save as the next version, look again, and list each change in one line.

Ask one short question only when the purpose (paper, report or slides) is
unknown and would change the answer.
