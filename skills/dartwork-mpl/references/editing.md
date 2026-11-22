# Editing an existing figure

Read this when the request changes a figure that already exists.

There are two kinds of request, and they want opposite things.

- **"Only X"** ("bigger axis labels", "move the legend", "thicker line for
  Model"). Find that artist, change the asked property and leave everything
  else as it was: data, preset, canvas, colours, other text. Defects the
  original already had stay; report them instead of fixing them.
- **Broad** ("make it look better", "더 보기 좋게", "clean this up"). Keep the
  data, the preset and what the chart is about. Render it, name the two or
  three biggest problems the image shows, fix those, and list every change.

Either way keep the original script and its outputs, write the revision as a
new script and output stem (`figure-v2`), and look at both PNGs side by side.
`dm.check(fig)` on each says which defects the change added or removed.

## Find the target

The figure below stands in for the user's script.

```python
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.text import Text
import dartwork_mpl as dm

dm.style.use("report")
x = np.linspace(0, 10, 101)
fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
left.plot(x, np.sin(x), label="Measured")
left.plot(x, np.sin(x) * 0.9, label="Model")
left.set(title="Response", xlabel="Time (s)", ylabel="Signal")
dm.place_legend(left)
right.plot(x, np.sin(x) * 0.1)
right.set(title="Error", xlabel="Time (s)")
dm.simple_layout(fig)
before = dm.check(fig)

error_ax = next(a for a in fig.axes if a.get_title() == "Error")      # a panel by title
model = next(ln for ln in left.get_lines() if ln.get_label() == "Model")  # a series by label
response = [t for t in fig.findobj(Text) if t.get_text() == "Response"]  # any text by content
print(model.get_linewidth(), sorted(model.properties())[:8])
```

Lines are `ax.get_lines()`, bars `ax.patches`, scatter and images
`ax.collections` / `ax.images`, the legend `ax.get_legend()`, axis labels
`ax.xaxis.label` (tick labels are `ax.get_xticklabels()`). Edit the existing
artist; do not plot a second copy. If two artists match and the request does
not say which, ask one short question.

## Change it

A relative request ("bigger", "thicker") moves one step from the current
value, and a second "one more" moves again from there. An absolute request
("12 pt") is set exactly.

```python
step = dm.fs(1) - dm.fs(0)                    # one font step of this preset
for t in (left.xaxis.label, left.yaxis.label):
    t.set_fontsize(t.get_fontsize() + step)
model.set_linewidth(model.get_linewidth() + 0.5)
dm.simple_layout(fig)                         # text grew: refit
after = dm.check(fig)
print(set(after.rules) - set(before.rules))   # defects this change added
dm.save_formats(fig, "output/figure-v2", formats=("png",))
plt.close(fig)
```

Elements the user asks for use one call each and take only the arguments the
request names, so the preset styles the rest.

| Asked for | Call |
|---|---|
| a title | `ax.set_title("…")`; over several panels `fig.suptitle("…")` |
| gridlines | `ax.grid(True, axis="y")` |
| a legend, or moving one | `dm.place_legend(ax)`; a named side `dm.place_legend(ax, loc="right")` |
| line names instead of a legend | `dm.label_line_ends(ax)` |
| a source or note | `dm.add_note(fig, "Source: …")` |
| emphasis on one series | it keeps its colour, the others `set_color("dc.gray4")`, then `dm.place_legend(ax)` again for fresh handles |
| align existing text beside the plot | `dm.align_texts(texts, "decimal")` |
| values on bars or points | `dm.label_bars(ax)`; `dm.annotate_value(ax, x, y, text)` |
| 12000 → 12k | `ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:g}k")` |
| 만/억 | `dm.format_axis_myriad(ax)` |
| dates under bars | plot against the dates themselves (`ax.bar(dates, values)`), not positions |
| four-digit years on a date axis | `ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y.%m"))` |
| a different size | rebuild with a new `dm.figsize`; a width alone keeps the old height |
| for slides | `dm.style.use("presentation")` and a new `dm.figsize_for(...)`; point sizes written in the code scale by `dm.fs(0)` new over old |

Call `dm.simple_layout(fig)` again after the last change.

## Value labels

`dm.label_bars(ax)` writes the numbers the way the axis prints them, one step
smaller and one weight heavier than body text, with no meaningless decimals.
Stacked bars get centred segment labels and a total. Labels that have no room
are hidden, so count them in the image: make the figure larger, or report
them when the size is fixed.

Pass `bars` (what one `ax.bar` call returns, or some of its bars: `bars[:1]`)
to label only those; `dm.annotate_value` is for a point on a line. Whether to label all, some or
none, and what the value axis does then: `references/craft.md`, "Numbers on
bars". For another text, label with matplotlib instead:

| Asked | Instead of `dm.label_bars` |
|---|---|
| a unit, fixed decimals, a plus on rises | `ax.bar_label(bars, fmt=lambda v: f"{v:+.1f} GWh".replace("-", "−"), padding=3, fontsize=dm.fs(-1))` |
| inside the bar | `ax.bar_label(bars, label_type="center", color="white", fontsize=dm.fs(-1))` |

```python
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.bar(["A", "B", "C"], [12, 30, 21])
dm.label_bars(ax)
dm.simple_layout(fig)
plt.close(fig)
```
