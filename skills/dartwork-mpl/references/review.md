# Render, check, inspect, revise

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

found = dm.check(fig)  # changes nothing in the figure
print(found)           # one line per defect, its fix under it
dm.save_formats(fig, "output/figure-v1")
```

`dm.check` measures the drawn figure and points at what a reader would
stumble on; it changes nothing and it does not judge. Each finding has `rule`, `message`, `fix`,
and the `artists` and `panels` involved; `found.rules` lists the rules that
found something. `NOT RUN` in the report means a rule could not measure
this figure: look at it yourself and say so.

## Look at the image

Open `output/figure-v1.png` with your image-viewing tool and read it as the
reader would. First: does the point land in five seconds? Then check that:

- every title, label, tick label and legend entry is inside the canvas and
  readable at the printed size;
- nothing overlaps: text on text, legend on data, labels between panels;
- the plotted data matches the input (count, gaps, order, units);
- tick and value labels carry no meaningless decimals (`200`, `1k`, not
  `200.0`, `1.0k`) and one axis uses one unit;
- every axis of numbers says what they count, and text on a coloured fill
  stays readable;
- no glyph boxes: every Korean, Japanese or other non-Latin character shows;
- panel sizes and empty space look intended.

If you cannot view images, say so in your answer instead of claiming the
figure was reviewed.

## Read the findings

Look at every finding in the image. It may be what you meant; when it is
not, the `try` line names what usually helps.

| rule | Means |
|---|---|
| `OVERFLOW` | text cut off by the canvas edge |
| `OVERLAP`, `CROSS_AXES_OVERLAP` | text on text, in one panel or between panels; a title or axis text running into another panel's plot (a colorbar) |
| `TEXT_CROWD` | a value beside a name on one row reads as one phrase |
| `LEGEND_ON_DATA` | a legend over data, a title or other text, or another legend |
| `TEXT_CONTRAST` | a text you placed, under 3:1 against the bar, cell or background behind it |
| `VALUE_LABEL_DECIMAL` | whole numbers printed as `12.0` |
| `VALUE_LABEL_ON_DATA` | a value label on a line, a marker or an error bar |
| `TICK_OVERLAP` | neighbouring tick labels collide |
| `MISSING_AXIS_LABEL` | an axis or colorbar of numbers that nothing names (dates, an x axis of whole years and names need none; one label per grid row or column is enough) |
| `EMPTY_AXES` | a framed panel that draws nothing, left over from a grid |

An "only X" edit keeps the warnings the original already had: report them,
do not fix them.

## Revise

1. Change only what the image, a finding or the user asked for.
2. Save under the next stem (`figure-v2`) and keep v1, but only when nobody
   named a path. If the user or caller named an output path or format, the
   final version goes to exactly that path, with no `-vN` and no extra files.
3. `dm.check` again and look at the new PNG.
4. Report what changed, which findings remain and why.

Lint a script before running it: `dm.lint_code(Path("plot.py").read_text())`
returns findings with `rule_id`, `severity`, `line`, `message` and `fix`; fix
every `critical` one. Explicit user values flagged as `fontsize-literal` or
`linewidth-literal` stay as the user set them.
