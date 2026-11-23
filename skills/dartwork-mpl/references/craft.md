# Chart craft

Read this when you are choosing what to draw, or when a chart is correct but
says nothing. It is about charts in general; the `dm` calls are the short way
to do each thing here.

## From the point to the form

Write the takeaway sentence first. Its verb picks the form.

| The sentence says | Form | Notes |
|---|---|---|
| changed over time | line | bars only for a few periods of totals |
| is larger than, ranks | bars sorted by value | horizontal when names are long |
| is made of | stacked bars | one stack per period; a pie only for two or three parts of one whole |
| is related to | scatter | a fitted line only when the fit is the point |
| is spread, is typical | histogram, box or violin | "Comparing distributions" below |
| differs across two dimensions | heatmap | "Heatmaps" below |
| the same pattern in many groups | small multiples | shared axes, one panel per group |

Sometimes the answer is not a chart: two numbers are a sentence, and twelve
exact values are a table.

One figure makes one point. Two points are two panels or two figures, not one
panel with two y axes.

## Make the point visible

- **Emphasis.** The series the sentence is about keeps its colour and the rest
  turn `"dc.gray4"`. This is the most underused move: a chart of eight
  coloured lines has no subject.
- **Direct labels.** Up to about six lines are named at their ends with
  `dm.label_line_ends(ax)`, in the line's colour, so the eye never travels to
  a legend. A legend box is for many series or for marks that have no end.
- **One annotation.** Mark the value, crossing or period the sentence names
  with `dm.annotate_value(ax, x, y, text)` or a shaded span (`ax.axvspan`).
  One mark is read. Five are skipped. Keep it on one background: a note
  that runs from the canvas onto a dark bar loses the letters on the bar
  ("Text over the data" below).
- **Order.** Categories go by value, largest first, unless they have their own
  order (time, age bands, a survey scale).
- **Numbers on marks.** Every bar gets its number only when the exact values
  are the point, and then the value axis goes; when one value is the point,
  only that bar or series gets one. "Numbers on bars" below.

```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
years = np.arange(2016, 2025)
regions = {
    "North": [41, 43, 44, 46, 45, 47, 49, 50, 52],
    "South": [38, 39, 41, 40, 37, 44, 51, 57, 63],
    "East": [35, 36, 36, 37, 36, 37, 38, 38, 39],
    "West": [44, 44, 45, 45, 43, 44, 45, 46, 46],
}
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
for name, values in regions.items():
    subject = name == "South"                      # the series the point is about
    ax.plot(years, values, label=name,
            color=None if subject else "dc.gray4", zorder=3 if subject else 2)
ax.set(xlabel="Year", ylabel="Revenue (USD m)")
ax.set_title("South overtook every region after 2021")   # a report figure says its point
dm.label_line_ends(ax)
dm.annotate_value(ax, years[-1], regions["South"][-1], "63")
dm.simple_layout(fig)
print(dm.check(fig))
dm.save_formats(fig, "output/regions-v1", formats=("png",))
plt.close(fig)
```

## Numbers on bars

A number on a bar says what the value axis already says. Let the bars or the
axis carry the values, not both.

| The point is | Label | The value axis |
|---|---|---|
| the exact values, and there are few bars (up to about eight) | every bar: `dm.label_bars(ax)` | goes: `ax.set_yticks([])` takes the ticks and their gridlines, `ax.spines["left"].set_visible(False)` the line; the axis label stays and carries the unit |
| one series, or one or a few bars | only those: `dm.label_bars(ax, bars=actual)` for the series an `ax.bar` call returned, `bars[:1]` or `[bars[2]]` for some of its bars | stays |
| the ranking or the shape, or there are many bars | none | stays |

Horizontal bars lose `ax.set_xticks([])` and the bottom spine instead. A paper
figure keeps the unit in the axis label; a report figure may move it into the
title ("Revenue by region (USD m)") and drop the label.

```python
regions, revenue = ["South", "North", "West", "East"], [63.4, 52.1, 46.0, 39.5]
fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=4, n_series=1, labels=regions))
ax.bar(regions, revenue)
dm.label_bars(ax)                         # the four values are the point
ax.set_yticks([])                         # so the axis does not repeat them
ax.spines["left"].set_visible(False)
ax.set_ylabel("Revenue (USD m)")          # the unit stays
dm.simple_layout(fig)
print(dm.check(fig))
plt.close(fig)
```

## Text in columns

A column of names or numbers beside a plot is part of the plot. Write its
texts on the plot's own Axes, each row at the height of the mark it belongs
to, and hand them to `dm.place_columns(ax, column)`: it sets the column one
text size from the plot's edge, the way tick labels sit by their axis, and
each further column (`dm.place_columns(ax, revenue, share)`, left to right)
a text size and a half after the one before. The x you wrote them at only says which
side they are on. A heading goes in its column's list, on the edge the
column is aligned on, and breaks into short lines: the column is as wide as
its widest text, so a long heading pushes its numbers away from the plot. Do not widen the x limits or add an Axes to hold a
column: `dm.simple_layout` makes the room. Rows that follow no marks (a
table that stands in for a legend) are centred on the plot's height, as a
legend on that side is. `dm.check` reports a column left floating
(`TEXT_COLUMN_GAP`).

Inside a column, `dm.align_texts(texts, how)` aligns edges (`"left"`,
`"right"`, `"center"`) or decimal points (`"decimal"`); it returns the rows
to style and to hand on. Keep values belonging to a mark at that mark.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
rows = [(0.8, -3.6, 5.2), (9.4, 2.4, 16.4), (-2.1, -5.8, 1.6), (4.3, 0.9, 7.7)]
ax.set_yticks(range(len(rows)), ["Study D", "Study C", "Study B", "Study A"])
ax.set_xlabel("Mean difference (mmHg)")
beside = ax.get_yaxis_transform()        # x across the plot (1 = right edge), y in data
labels = []
for y, (effect, low, high) in enumerate(rows):
    ax.hlines(y, low, high)
    ax.plot(effect, y, marker="s", color="dc.blue6")
    labels.append(
        ax.text(1, y, f"{effect:.1f} [{low:.1f}, {high:.1f}]", transform=beside, va="center")
    )
head = ax.text(1, len(rows) - 0.4, "Mean [95% CI]", transform=beside, fontweight="bold")
dm.place_columns(ax, [head, *dm.align_texts(labels, "decimal")])
dm.simple_layout(fig)
print(dm.check(fig))
plt.close(fig)
```

## Comparing distributions

| Groups | Form |
|---|---|
| two | overlaid histograms on one set of bin edges; `ax.ecdf(values)` when percentiles are the point |
| three to about eight | a box per group with the raw points over it, ordered by median |
| more, or thousands of points per group | boxes alone (`showfliers=True`); a violin only when the shape (two peaks) is the point |

- **One set of bin edges.** `bins = np.histogram_bin_edges(np.concatenate([a, b]), bins=20)`
  passed to every `ax.hist`. Bins of their own make the bars incomparable.
- **Density when the groups differ in size.** `density=True` and the y label
  says so (`Share per min`); counts only for equal groups or when totals
  matter. Say each group's n, in the legend or the tick label.
- **Overlap.** The subject `histtype="stepfilled", alpha=0.4`, the other
  `histtype="step", color="dc.gray5"`. Two opaque fills hide each other.
- **Raw points.** Jittered sideways, small (`s=6`, `linewidths=0`), drawn
  before the box, and `showfliers=False` so outliers are not drawn twice.
- **Say what the box is.** Matplotlib's box spans the middle half, its
  whiskers reach the furthest point within 1.5 × IQR. Say it in the caption
  or `dm.add_note(fig, text)`.
- **The typical value.** The box's median line; on a histogram an
  `ax.axvline(np.median(values))` in the group's colour, named with
  `dm.annotate_value`. A mean is `showmeans=True` and said in the note.
- **Colour.** The group the sentence is about keeps its colour, the rest
  `"dc.gray4"`; box lines in one dark grey for all groups.

```python
rng = np.random.default_rng(7)
waits = {"North": rng.normal(40, 8, 60), "South": rng.normal(31, 6, 45),
         "East": rng.normal(44, 10, 80), "West": rng.normal(42, 7, 30)}
order = sorted(waits, key=lambda k: np.median(waits[k]))
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
for i, name in enumerate(order, start=1):
    ax.scatter(i + rng.uniform(-0.15, 0.15, len(waits[name])), waits[name], s=6,
               linewidths=0, color=None if name == "South" else "dc.gray4")
box = ax.boxplot([waits[k] for k in order], widths=0.5, showfliers=False)
for part in ("boxes", "whiskers", "caps", "medians"):
    plt.setp(box[part], color="dc.gray8")
ax.set_xticks(range(1, len(order) + 1), [f"{k}\nn={len(waits[k])}" for k in order])
ax.set(ylabel="Wait time (min)", title="South has the shortest waits")
dm.add_note(fig, "Box: middle half; line: median; whiskers: furthest point within 1.5 × IQR.")
dm.simple_layout(fig)
print(dm.check(fig))
plt.close(fig)
```

## Heatmaps

- **Size and order.** A square table such as a correlation matrix takes
  `dm.figsize_for("matrix")`; under `presentation` that is 10.5 cm, so the
  point goes in the slide's title, not over the matrix. Rows and columns go
  in their own order (time, a scale) or grouped so similar ones sit together.
- **Scale.** Magnitudes take a sequential map. Signed values around a
  centre (correlations, anomalies) take a diverging map with symmetric
  limits, `cmap="dc.blue_red", vmin=-1, vmax=1`, so zero is the pale middle.
- **One triangle.** A symmetric matrix shows each pair once and drops the
  diagonal of 1s: rows from the second, columns to the second-last.
- **Values in cells** when the reader will quote them and there are few
  cells (up to about 10 × 10): `dm.fs(-1)`, the fewest decimals that tell
  cells apart (`.2f` for a correlation), and per cell the text colour that
  reads, `dm.readable_text_color(im.cmap(im.norm(v)))`. `dm.check` reports
  a cell text under 3:1 as `TEXT_CONTRAST`.
- **Colorbar.** None when every cell carries its number: the numbers are
  the scale. Otherwise one beside the matrix, named with the quantity and
  unit, `fig.colorbar(im, ax=ax, label="Anomaly (°C)")`, and `aspect="auto"`
  on `imshow` so the cells fill the axes and the bar matches their height.
  Square cells with a side colorbar leave empty bands above and below, and a
  long title can run under the bar: look at the PNG.
- No frame or tick marks around the cells: `ax.spines[:].set_visible(False)`,
  `ax.tick_params(length=0)`.

```python
assets = ["Stocks", "REITs", "Bonds", "Gold", "Oil", "Cash"]
returns = np.random.default_rng(3).normal(size=(200, 6))
returns[:, 1] += 1.4 * returns[:, 0]
returns[:, 2] -= 0.5 * returns[:, 0]
corr = np.corrcoef(returns, rowvar=False)
n = len(assets)
lower = np.ma.masked_array(corr, mask=np.triu(np.ones((n, n), dtype=bool)))[1:, :-1]
fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
im = ax.imshow(lower, cmap="dc.blue_red", vmin=-1, vmax=1)
ax.set_xticks(range(n - 1), assets[:-1])
ax.set_yticks(range(n - 1), assets[1:])
for i in range(n - 1):
    for j in range(i + 1):                         # the shown triangle only
        v = lower[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=dm.fs(-1),
                color=dm.readable_text_color(im.cmap(im.norm(v))))
ax.spines[:].set_visible(False)
ax.tick_params(length=0)
ax.set_title("Stocks and REITs moved together most")
dm.simple_layout(fig)
print(dm.check(fig))
plt.close(fig)
```

## Text over the data

A text reads when its ink has contrast with what is behind every part of
it. Black on a pale bar and white on a dark one both read; a note that
crosses from one to the other, or grey contour numbers on bands from pale
to dark, read in parts.

- **First move it.** A note on one background needs nothing: beside the
  bars, above the plot, in the title. A band or segment too thin for its
  label gets the label outside it, with a short line to it.
- **Where it must cross** (contour numbers, a label along a stacked bar, a
  name on a cloud of points): draw it, lay the figure out, and read
  `dm.check`. It reports a text with ink under 3:1 as `TEXT_CONTRAST`.
- **Then, and only then, `dm.legible(texts)`** on the texts it named, and
  check again. It reads the drawn figure and gives each text the least
  that makes it read: nothing to one that reads, the one colour that
  reads on everything behind it, or an outline in the colour of the
  background it reads best on. It never moves a text, and prints what it
  did to each. A text nothing can mend (it is translucent, or something
  is drawn over it) is left as it was and named: fix that one by hand.
- It takes the texts you placed in an Axes (`ax.text`, `ax.annotate`,
  `ax.clabel`), not titles, tick labels or legend entries: those take
  their colour from the preset.
- A text `dm.check` does not name already reads: leave it as it is. A box
  behind a text hides the data under it (`TEXT_BOX_ON_DATA`), so it is the
  last resort for a text nothing else mends, never a precaution.

```python
T, P = np.meshgrid(np.linspace(10, 30, 60), np.linspace(20, 100, 60))
cop = 7.2 - 0.12 * (T - 10) - 2.4 * ((P - 70) / 50) ** 2
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bands = ax.contourf(T, P, cop, levels=8, cmap="dc.teal")
lines = ax.contour(T, P, cop, levels=4, colors="dc.gray8", linewidths=dm.lw(-1))
labels = ax.clabel(lines, fmt="%d")
fig.colorbar(bands, ax=ax, label="COP")
ax.set(xlabel="Wet-bulb (°C)", ylabel="Part load (%)")
dm.simple_layout(fig)
print(dm.check(fig))              # TEXT_CONTRAST: the numbers on the dark bands
dm.legible(labels)                # mends those; the ones that read stay as they are
print(dm.check(fig))              # again, after the fix
plt.close(fig)
```

## Edges and ends

Small misfits read as carelessness before the reader has seen the data.

- **A label stands at its own mark.** The eye pairs a text with the nearest
  mark. A value far from its bar and next to another one reads as the other
  one's. In a grid of small charts, leave more room between the cells than
  between a mark and its label (`VALUE_LABEL_ADRIFT`).
- **An outline is drawn half outside the shape and half inside it.** One
  outlined segment in a stack therefore stands past its neighbours: give
  touching marks the same outline, each in its own colour, or none
  (`UNEVEN_OUTLINE`). A paper-coloured outline used as a separator paints
  over the rim of every piece, so a line aimed at a piece's corner (the
  connector from a wedge to its breakdown, a bracket) stops short of the
  ink (`CONNECTOR_SHORT`). Pieces a line must meet take no outline, or one
  in their own colour; a gap in the data separates them.
- **A band is centred on what it marks.** The row or column sits in the
  middle of its highlight: the same distance to both edges
  (`BAND_OFF_CENTRE`).
- **An axis ends on a tick when the data leaves room.** A line that runs a
  little past its last tick looks unfinished; a log axis that stops just
  above a decade is the usual case. Set that limit to the tick. Do not
  move a limit the data reaches, and bars keep their zero.

## Words on the figure

- **Title.** A paper figure has none: the caption carries the message. A
  report or slide figure may state the point as a sentence. A title that
  only names the variables repeats the axes and can go. `ax.set_title`
  centres it on the plot, and for most charts that is right. Look at the
  PNG when category names take a third of the width or more: the plot then
  sits well off the figure's centre and its title hangs against the far
  edge over an empty corner, and `fig.suptitle(...)`, centred on the
  canvas, reads better.
- **Axis labels** name the quantity and its unit: `Revenue (USD m)`,
  `Temperature (°C)`. An axis whose ticks are self-evident (years, month
  names, category names) needs no label.
- **Source or note** lines go under the figure with `dm.add_note(fig, text)`.
- Claim only what the data shows. "Rose 23 %" needs the 23 % to be in the
  data.

## Honest axes

- Bars encode length, so they start at zero. Lines encode position and may
  start anywhere.
- One y axis. A second one makes two series cross wherever the scales are
  chosen to make them cross. Use two panels sharing x. Draw a twin axis only
  when the user asks.
- A log scale when the data spans orders of magnitude, said in the axis label
  or obvious from the ticks.
- Missing values stay gaps. A line drawn across a gap claims data that is not
  there.

## Colour

- One series: one colour. Categories that are unrelated: the preset cycle.
  Ordered groups: steps of one family (`dm.colors("dc.teal", n=4)`).
- Magnitudes: a single-hue or perceptual colormap. Values around a centre: a
  diverging map with symmetric limits. Details: `references/colors.md`.
- Never rely on red against green alone. Pair colour with position, a label
  or a dash.

## Small multiples

One panel per group, on the same axes, so heights compare across panels.

- **Share the axes.** `plt.subplots(2, 3, sharex=True, sharey=True)` drops
  the inner tick labels. Name y on the first column only (`axes[:, 0]`) and
  x on the bottom row only (`axes[-1]`); a name on every panel takes width
  from the plots and says nothing new.
- **Titles.** Each panel gets a short name (`ax.set_title("North")`); the
  point goes in one figure title, `fig.suptitle(...)`, in a report or slide
  figure. Both stay centred as the preset draws them. `x=0` does not align
  the figure title with the first panel; it puts it on the canvas edge.
- **One legend.** `dm.figure_legend(fig)` collects every panel's series and
  sits under the figure title, above the panel titles. Two or three lines
  can instead be named at their ends in the last panel,
  `dm.label_line_ends(axes.flat[-1])`.
- Panel letters (`dm.label_axes(axes)`) are for paper figures that the
  caption refers to. Each goes before its panel's title, `a  North`. A
  slide usually needs none: its titles already name the panels.

```python
months = np.arange(1, 13)
fig, axes = plt.subplots(2, 3, figsize=dm.figsize_for(nrows=2, ncols=3),
                         sharex=True, sharey=True)
for i, (ax, name) in enumerate(zip(axes.flat, ["North", "South", "East",
                                               "West", "Central", "Islands"])):
    ax.plot(months, 40 + 2 * i + months, label="Actual")
    ax.plot(months, 43 + 2 * i + 0.5 * months, label="Plan", color="dc.gray4")
    ax.set_title(name)
for ax in axes[:, 0]:
    ax.set_ylabel("Revenue (USD m)")
for ax in axes[-1]:
    ax.set_xlabel("Month")
axes[0, 0].set_xticks([3, 6, 9, 12])        # shared: sets every panel
fig.suptitle("Every region beat plan from July on")
dm.figure_legend(fig)
dm.simple_layout(fig)
print(dm.check(fig))
plt.close(fig)
```
