# Render, inspect, revise

Run this loop for every figure and again for every revision. A figure is
done when you have looked at the saved PNG, not when the script ran.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
x = np.linspace(0, 10, 101)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, np.sin(x), label="Measured")
ax.plot(x, np.cos(x), label="Model")
ax.set(xlabel="Time (s)", ylabel="Signal")
dm.place_legend(ax)
dm.simple_layout(fig)

r = dm.review(fig, "output/figure-v1")  # PNG + PDF, every finding, a summary
for finding in r.findings:
    print(finding.severity.value, finding.check_id, finding.message)
plt.close(fig)
```

`dm.review` saves with `dm.save_formats`, runs every `dm.validate_figure` check
on the saved figure and keeps the findings as they are, and writes
`output/figure-v1.review.json` with a summary of what the figure shows (titles,
axis labels, ranges, tick labels, series, legend, text outside the canvas).
It fixes nothing. `r.complete` is `False` when a check could not run
(`CHECK_FAILED`); `True` is not a pass, only "every check ran".

## Look at the image

Open `output/figure-v1.png` with your image-viewing tool. Check that:

- every title, label, tick label and legend entry is inside the canvas and
  readable at the printed size;
- nothing overlaps: text on text, legend on data, labels between panels;
- the plotted data matches the input (count, gaps, order, units);
- tick and value labels carry no meaningless decimals: `200`, `0`, `1k, 2k`,
  not `200.0`, `0.0`, `1.0k, 2.0k`; non-integer values get the decimals the
  data need, the same count along an axis (`17.5, 20.0, 22.5` is fine);
- one axis uses one unit (`0.5M, 1.0M`, not `500k, 1M`). The SI, myriad,
  millions and billions formatters choose decimals and the SI and myriad
  ones the largest tick's unit by default; an explicit `decimals=` or
  `unit=` is used exactly, so set it to what the values need;
- no glyph boxes: every Korean, Japanese or other non-Latin character shows;
- panel sizes and empty space look intended.

If you cannot view images, say so in your answer instead of claiming the
figure was reviewed.

## Read the findings

WARNING findings are defects to fix or explain; INFO findings are hints.

| check_id | Means | Usual fix |
|---|---|---|
| `OVERFLOW`, `CLIPPED_TEXT` | text outside the canvas or axes | `dm.simple_layout(fig)` after the last artist; `margin=` |
| `OVERLAP`, `CROSS_AXES_OVERLAP` | text collides | more `hspace`/`wspace`, fewer or rotated ticks |
| `LEGEND_OVERFLOW` | legend too large, off the canvas, or outside at over half the plot's size | many lines: `dm.label_line_ends(ax)`; else fewer columns, shorter names |
| `LEGEND_OVERLAP` | legend covers a title, axis or tick label | `dm.place_legend(ax)` (the side the user named, if any), then `simple_layout` |
| `LEGEND_ON_DATA` | legend covers data, a text, another legend or panel | `dm.place_legend(ax)`, then `simple_layout`; panels sharing series: `dm.figure_legend(fig)`; many lines: `dm.label_line_ends(ax)` |
| `TICK_CROWD`, `TICK_ROTATION` | crowded or rotated tick labels | `MaxNLocator(nbins=5)`, `dm.avoid_tick_overlap(ax)` |
| `TICK_DECIMAL`, `UNIT_DUP` | odd precision, unit repeated | `dm.set_decimal(ax, yn=1)`, unit in the axis label only |
| `VALUE_LABEL_ON_DATA` | a value label sits on a bar, line or marker | bars: `dm.label_bars(ax)`; points: `dm.annotate_value(ax, x, y, text)` |
| `MIN_FONT_SIZE`, `TEXT_CONTRAST` | text too small or faint | `dm.fs(0)` or larger, darker colour |
| `MARGIN_ASYMMETRY`, `EMPTY_AXES` | lopsided margins, empty panel | rerun `simple_layout`, remove the panel |
| `GRAYSCALE_SAFETY` (INFO) | similar grey values | mention it; change colours only when asked |
| `PRESET_OVERRIDE` (INFO) | grid, spines or background differ from the preset | keep the change only if the user asked; else delete the call |
| `CHECK_FAILED` | a check could not run | the check is incomplete; say so |

A twin-axes pair can report `CROSS_AXES_OVERLAP` for its shared x ticks;
that one is a false positive.

## Revise

1. Change only what the image, a WARNING or the user asked for.
2. Review under the next stem against v1 and keep v1. If the user named an
   output path, write the final version there too.
3. Look at the new PNG again.
4. Report what changed, which warnings remain and why.

```python
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, np.sin(x), label="Measured")
ax.plot(x, np.cos(x), label="Model")
ax.set(xlabel="Time (s)", ylabel="Signal (V)")  # the asked change
dm.place_legend(ax)
dm.simple_layout(fig)
r2 = dm.review(fig, "output/figure-v2", baseline="output/figure-v1",
               allow=["axes[0].ylabel.*"])
print([(c.path, c.before, c.after) for c in r2.unexpected])
plt.close(fig)
```

`r2.changes` lists every summary entry that differs from v1 by path
(`axes[0].ylabel.text`, `axes[0].series[1].color`, `figure.size_in`, a
series' `data` digest …); `allow=` names the paths you meant to change (`*`
is the only wildcard) and `r2.unexpected` is the rest. The list judges
nothing: explain or undo each unexpected change.

Lint a script before running it: `dm.lint_code(Path("plot.py").read_text())`
returns issues with `rule_id`, `severity` and `fix_suggestion`; fix every
`critical` one. Explicit user values flagged as `fontsize-literal` or
`linewidth-literal` stay as the user set them.
