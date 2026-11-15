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

`dm.check` measures the drawn figure and reports what makes it ugly or
unreadable; it fixes nothing. Each finding has `rule`, `severity`,
`message`, `fix`, and the `artists` and `panels` involved;
`found.of("OVERLAP")` picks one rule. `NOT RUN` in the report means a rule
could not measure this figure: it is not proven clean, say so.

## Look at the image

Open `output/figure-v1.png` with your image-viewing tool. Check that:

- every title, label, tick label and legend entry is inside the canvas and
  readable at the printed size;
- nothing overlaps: text on text, legend on data, labels between panels;
- the plotted data matches the input (count, gaps, order, units);
- tick and value labels carry no meaningless decimals (`200`, `1k`, not
  `200.0`, `1.0k`) and one axis uses one unit;
- no glyph boxes: every Korean, Japanese or other non-Latin character shows;
- panel sizes and empty space look intended.

If you cannot view images, say so in your answer instead of claiming the
figure was reviewed.

## Read the findings

Fix every WARNING; weigh each INFO. The fix line names the usual remedy.

| rule | Means |
|---|---|
| `OVERFLOW` | text cut off by the canvas edge |
| `TEXT_AT_EDGE` (INFO) | text flush with the canvas edge: `dm.simple_layout(fig, margin="1mm")` |
| `OVERLAP`, `CROSS_AXES_OVERLAP` | text on text, in one panel or between panels |
| `TEXT_CROWD` | a value beside a name on one row reads as one phrase |
| `LEGEND_OVERFLOW`, `LEGEND_OVERLAP`, `LEGEND_ON_DATA` | legend too big, over a title or label, over data |
| `VALUE_LABEL_ON_DATA`, `VALUE_LABEL_DECIMAL` | a value label hides data, or prints `120.0` |
| `TICK_OVERLAP`, `TICK_CROWD`, `TICK_CORNER_OVERLAP` | tick labels collide or crowd |
| `TICK_DECIMAL` | ticks print `2.0`, mixed or repeated decimals |
| `MISSING_AXIS_LABEL` (INFO) | numbers on an axis nothing names |
| `TEXT_CONTRAST` | text too faint on its background |
| `EMPTY_AXES` (INFO), `MARGIN_ASYMMETRY` | an empty panel, one wide empty margin |

An "only X" edit keeps the warnings the original already had: report them,
do not fix them.

## Revise

1. Change only what the image, a WARNING or the user asked for.
2. Save under the next stem (`figure-v2`) and keep v1. If the user named an
   output path, write the final version there too.
3. `dm.check` again and look at the new PNG.
4. Report what changed, which findings remain and why.

Lint a script before running it: `dm.lint_code(Path("plot.py").read_text())`
returns findings with `rule_id`, `severity`, `line`, `message` and `fix`; fix
every `critical` one. Explicit user values flagged as `fontsize-literal` or
`linewidth-literal` stay as the user set them.
