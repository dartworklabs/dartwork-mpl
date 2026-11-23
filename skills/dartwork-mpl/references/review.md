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
| `TEXT_AT_EDGE` | manually placed plot text almost touching the canvas edge; a plot title that ends at one canvas edge with room past its other end (it is centred on a plot long names pushed off the canvas centre) |
| `OVERLAP`, `CROSS_AXES_OVERLAP` | text on text, including an inset's axis label on its ticks; axis text running into another plot or across the parent frame |
| `TEXT_TOO_CLOSE` | a text placed near another text on the same panel, with too little space to read them apart; aligned rows of a list are fine |
| `TEXT_CROWD` | a value beside a name on one row reads as one phrase |
| `TEXT_MISALIGNMENT` | Text already forming a column has ragged decimal positions or edges. Select that column’s texts and use `dm.align_texts`. |
| `LEGEND_ON_DATA` | a legend over data, a title or other text, or another legend |
| `TEXT_CONTRAST` | a text you placed with ink under 3:1 on what is drawn behind it: all of it (white numbers on pale bars), or the part that runs from one background onto another (a note from the canvas onto a dark bar, half an em of it is enough). Move it onto one background; where it must cross, `dm.legible(texts)` and check again |
| `MIXED_MINUS` | negative numeric labels use a hyphen while ticks on the figure use a Unicode minus |
| `VALUE_LABEL_DECIMAL` | whole numbers printed as `12.0` |
| `VALUE_LABEL_ON_DATA` | a value label on a line, a marker or an error bar |
| `TEXT_ON_LINE` | a name or note you placed with a line drawn through it (a trend line through a point's name); a text on its own box, a leader ending at its label, or a name turned to run along its line is fine; also an inset's tick or axis labels with its zoom connector (`ax.indicate_inset_zoom`) through them |
| `VALUE_LABEL_ADRIFT` | a value label that stands between its own bar and another bar of the same row or column, nearer the other: it reads as the other's |
| `UNEVEN_OUTLINE` | bars that touch a bar with a narrower outline or none: the outline is drawn half outside, so they stand past their neighbours |
| `BAND_OFF_CENTRE` | a band (`ax.axhspan`, a rectangle) behind one row or column of marks, with that row off the band's middle |
| `TEXT_BOX_ON_DATA` | a text on an opaque box of its own, the box over bars or filled areas: it hides them, and the text may read without it |
| `CONNECTOR_SHORT` | a straight line or connector ending on the corner of a bar or wedge outlined in the colour of the paper: the outline covers the rim, so the line stops in the air beside the visible corner |
| `LETTER_ON_DATA` | a panel letter inside its plot (the titles were too long to follow it) drawn on data |
| `POLAR_TICK_ON_PLOT` | angle tick labels cross into their polar plot (`dm.simple_layout` moves centred ones out; these were placed by hand, or the layout has not run) |
| `RADIAL_TICK_COVERED` | a polar fill paints over radial tick numbers |
| `TICK_OVERLAP` | neighbouring tick labels collide |
| `MISSING_AXIS_LABEL` | an axis or colorbar of numbers that nothing names (dates, an x axis of whole years and names need none; one label per grid row or column is enough) |
| `EMPTY_AXES` | a framed panel left empty by the grid, or whose data draws no visible marks |
| `UNDERUSED_CANVAS` | an axis-less equal-aspect plot leaves a wide blank band on the canvas |
| `SMALL_PANEL` | the largest plot is under 7 tick labels on its shorter side: titles, ticks and axis names take the canvas (a grid moved to slide text) |
| `UNDERUSED_CANVAS` | a large blank band around a frameless plot, beside columns and their descriptions with no x scale, or beside a colorbar whose slot is wider than its scale |

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
