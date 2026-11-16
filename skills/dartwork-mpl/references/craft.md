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
| is spread, is typical | histogram, box or violin | box for comparing many groups |
| differs across two dimensions | heatmap | ordered rows and columns, a colormap with meaning |
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
  One mark is read. Five are skipped.
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
| one series, or one bar | only those: `dm.label_bars(ax, bars=actual)` with what that `ax.bar` call returned; one bar in a series `dm.annotate_value(ax, x, y, text)` | stays |
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

## Words on the figure

- **Title.** A paper figure has none: the caption carries the message. A
  report or slide figure may state the point as a sentence. A title that
  only names the variables repeats the axes and can go.
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

Panels share axes so heights compare, each panel is named by a short title,
and one legend serves all (`dm.figure_legend(fig)`). Panel letters
(`dm.label_axes(axes)`) are for paper figures that the caption refers to.
