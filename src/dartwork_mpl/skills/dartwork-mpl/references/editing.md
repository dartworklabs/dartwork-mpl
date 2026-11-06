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
and look at the PNG before you answer. `dm.review(fig, "output/figure-v2",
baseline="output/figure-v1", allow=[...])` lists every summary entry that
differs from the original (`axes[0].ylabel.size`, `axes[0].series[1].color`,
`figure.size_in`, a series' `data` digest …). `allow=` names the paths you
meant to change (`*` is the only wildcard: `axes[*].position`), and
`r.unexpected` is everything else: for an "only X" edit it should be empty or
explained. The list judges nothing; you do.

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
right.plot(x, np.sin(x) * 0.1)
right.set(title="Error", xlabel="Time (s)")
dm.simple_layout(fig)
original = dm.review(fig, "output/figure-v1")  # the original's files, findings, summary

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

## An asked-for element: named details win, the rest is the preset's

A request that names an element ("add a title", "with gridlines", "legend
above the plot", "20 cm wide") gets the one call below, in a new figure or an
edit. Pass only the arguments the request names: the preset sets size,
weight, colour and spacing, so every agent draws the same element.

| Asked for | Call |
|---|---|
| a title | `ax.set_title("…")`; one title over several panels: `fig.suptitle("…")` |
| gridlines | `ax.grid(True, axis="y")` (horizontal); `axis="x"` vertical; `"both"` |
| a legend, no side named | `dm.place_legend(ax)`: inside where it covers no data, otherwise above the plot by itself; no `loc=` or `ncols=` of your own |
| a legend on a named side | `dm.place_legend(ax, loc="above")`, `"below"`, `"right"`, `"left"` |
| a source or note line | `dm.add_note(fig, "Source: …")`, then `dm.simple_layout(fig)` |
| a width only | new figure `dm.figsize("20cm")` (4:3); an edit keeps the old height in cm, also after a ratio token: `h = dm.figsize("14cm", "golden")[1] * 2.54`, then `dm.figsize("16cm", f"{h:.2f}cm")` |
| bigger or smaller text, no amount | one step, `step = dm.fs(1) - dm.fs(0)` (1 pt; 2.6 pt under `presentation`): `t.set_fontsize(t.get_fontsize() + step)`; all text: `dm.style.use(preset, font_size=dm.fs(0) + step)` |
| a dark background | `dm.style.use("dark")` (Korean text: `"dark-kr"`) |
| black or neutral twin axes (no series colours) | `dm.config.twin_colors = "neutral"` before `dm.simple_layout`; not `tick_params(colors="black")`, which the first layout cannot tell from the default and paints |
| one twin axis (or one part of it) in a named colour | set just that part (`ax2.tick_params(axis="y", colors=…)`, `ax2.yaxis.label.set_color(…)`); that side is then yours, its other parts keep the preset's colours, the other side keeps its series colour |
| values on the bars | `dm.label_bars(ax)`; a named detail is its keyword (`where="inside"`, `decimals=1`, `fmt="{} GWh"` …), see Value labels below |
| a log axis | `ax.set_yscale("log")` |

A detail the user does name wins exactly ("a bold 12 pt title", "dashed grey
gridlines"). `dm.simple_layout(fig)` after the last element keeps a title
above an outside legend and the margins around both.

## Common "only X" requests

| Request | Change |
|---|---|
| axis labels one step bigger | each label: `t.set_fontsize(t.get_fontsize() + step)` |
| ticks smaller | `ax.tick_params(labelsize=dm.fs(-1))` |
| one line thicker | `line.set_linewidth(line.get_linewidth() + 0.5)` |
| emphasise one series or bar | target keeps its colour, `set_zorder(3)`; others `set_color("dc.gray4")` (bars: `set_facecolor`); the legend stays: after recolouring, redraw it with the same call and arguments (`loc=`, `ncols=` …) |
| move the legend | `dm.place_legend(ax)` (inside, away from the data) or a named side `dm.place_legend(ax, loc="right")`; never `ax.legend(loc=...)` or `bbox_to_anchor` |
| legend above (below, right, left) the plot | `dm.place_legend(ax, loc="above")` |
| label line ends instead of a legend | `dm.label_line_ends(ax)` (removes the legend; names in the line colour, readable, spaced) |
| fewer ticks | number and year axes: `ax.locator_params(axis="x", nbins=5)`, year axes stay on whole years (`05, 10, 15`); date axes have no `set_params`: use a date locator coarser than the current ticks, chosen for the span (`import matplotlib.dates as mdates`; the date words stay): decades `ax.xaxis.set_major_locator(mdates.YearLocator(5))` (`95, 00, 05`), a few years of monthly data `ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))` (`23.01, 23.07`; about the span in months / 6), a few months `ax.xaxis.set_major_locator(mdates.MonthLocator())` (`24.01, 24.02`), a few weeks `ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))` (`24.01.01, 24.01.08`); a `MaxNLocator` you set reads years while its ticks are whole years, plain numbers (`2005.0, 2007.5`) when they are not |
| date labels under bars crowd (`2022-07 … 2023-12`) | `dm.format_axis_dates(ax, df["order_month"])`: the library's date words, thinned by `dm.simple_layout` (`22.07, 22.09, 22.11, 23.01 …`); not rotated |
| for slides / for a talk (preset switch) | `dm.style.use("presentation")`, canvas `dm.figsize_for(...)` (`"full_slide"` only for a whole 16:9 slide); pt values written in the code × 2.6 (`scientific` → `presentation`), unrounded: `markersize=3` → `3 * 2.6`; keep data, labels and limits |
| 12000 → 12k | `dm.format_axis_si(ax)` |
| unit in the axis label, plain ticks (`0, 0.2 … 1.0` under `인구 (억명)`) | `dm.axis_unit(ax, "y", label="인구 ({unit}명)")`; `dm.axis_unit_of(ax)` for value labels |
| four-digit years (`2016`, `2023.01`) / concise date words (`23, May, Sep`) / `k, M` in a Korean figure | `with dm.config.override(tick_years=4):` / `(date_style="concise")` / `(number_ladder="si")` around the code from figure creation to the last `dm.simple_layout`, or the field set on `dm.config` |
| show the values on bars or points | bars `dm.label_bars(ax)`; points and line ends `dm.annotate_value(ax, x, y, text)`, see below |
| bigger or wider figure | rebuild with a new `dm.figsize`; keep the preset |

```python
step = dm.fs(1) - dm.fs(0)       # one size step: 1 pt, 2.6 pt under presentation
for t in (panel_a.xaxis.label, panel_a.yaxis.label):
    t.set_fontsize(t.get_fontsize() + step)
model.set_linewidth(model.get_linewidth() + 0.5)
error_ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
dm.simple_layout(fig)            # text grew: refit with the script's own arguments
r = dm.review(fig, "output/figure-v2", baseline="output/figure-v1", allow=[
    "axes[0].xlabel.size", "axes[0].ylabel.size",  # the asked label step
    "axes[0].series[1].width", "axes[1].yticks.*",  # the line, the ticks
    "axes[*].position",                             # the refit
])
print([c.path for c in r.unexpected])  # anything else that moved
plt.close(fig)
```

Validate the original before the change. A WARNING it already has is not
the change's: it stays and goes in the report (an "only X" edit fixes
nothing else). When the asked change itself makes a legend cover text,
its own panel's or another's (a `LEGEND_OVERLAP` WARNING the original did
not have), move only that legend: `dm.place_legend(ax)` on its axes with
the arguments it already had (`fontsize=`, `ncols=` …; no new `loc=`); it may go above the
plot in two columns, which is the decided look (decision L-B). Not wider
`wspace`, a smaller font or fewer columns of your own. List the move; a
legend the change leaves clear stays.

Repeated "one more step" adds to the current value again; it does not reset
to `dm.fs(1)`. An absolute request ("12 pt") is set exactly. Keep the
existing layout when the result still fits; refit only with the arguments
the script already used.

## Value labels

Numbers written on bars or at line points are one size step smaller and one
weight step heavier than body text (`fontsize=dm.fs(-1)`,
`fontweight=dm.fw(1)`; `dm.annotate_value` does both) and carry no
meaningless decimals. Titles, axis labels, ticks and legends keep the preset
size and weight.

Values on bars are `dm.label_bars(ax)`: no request, its defaults; a request,
that keyword. The defaults are that look in the text colour, 3 pt beyond the
bar end; the number printed like the axis ticks (plain under
`dm.axis_unit`, with the ticks' `k` under `dm.format_axis_si`), three
significant digits on the largest value and no meaningless decimals
(`21.4, 18.0, 21.5`; `120, 135`); stacked bars' segments centred with a
total; crowded labels on vertical bars turned vertical by
`dm.simple_layout`; grouped series whose labels meet take turns by bar index
(two alternate), so no series vanishes; a bar past a limit you set shows its
true value just inside the limit. Labels still lost for room (thin `barh`
rows) make `dm.simple_layout` warn with the count: if the rows are thin,
make the figure taller (wider for vertical bars), and report the warning if
the size is fixed.

| Asked | Keyword |
|---|---|
| inside the bar ends, at the middle | `where="inside"`, `where="center"` |
| only the stack totals, no totals | `total="only"`, `total=False` |
| crowded: every other label, or inside the bars | `crowded="skip"`, `crowded="inside"` |
| a fixed decimal count | `decimals=1` |
| a unit or another format on the labels | `fmt="{} GWh"`, `fmt="{:.2f}"`, a callable |
| bigger, another colour, the bar's colour | `size=dm.fs(0)`, `color="dc.gray7"`, `color="series"` (labels off their bar) |

```python
fig, (bar_ax, line_ax) = plt.subplots(
    1, 2, figsize=dm.figsize("17cm", "7cm"), gridspec_kw={"wspace": 0.3}
)
bar_ax.bar(["A", "B", "C"], [12, 30, 21])
dm.label_bars(bar_ax)            # 12, 30, 21 above the bars
days, visits = np.arange(1, 8), np.array([40, 42, 47, 45, 51, 58, 63])
line_ax.plot(days, visits)
dm.annotate_value(line_ax, days[-1], visits[-1], f"{visits[-1]}")  # picks a free side
dm.simple_layout(fig)
plt.close(fig)
```

## Broad requests: "make it look better"

1. Render and look. Name the two or three biggest problems.
2. Fix in this order, only what the image shows:
   - clipped or overlapping text: dates read as dates and the library's tick
     numbers and dates (`dm.simple_layout(fig)`; no formatter or locator of
     your own; dates under bars or other categories:
     `dm.format_axis_dates(ax, dates)`), `dm.wrap_axis_labels(fig)`,
     `dm.rotate_tick_labels(ax)` only when none of these fits;
   - value labels touching each other or their neighbours: those labels to
     `fontsize=dm.fs(-1)` (only when larger) and, when the call writes no
     weight, `fontweight=dm.fw(1)` (the value-label look), named in the change
     list; the axis limits stay, also when a line crosses the labels;
   - legend over data, or two legends on a twin pair: `dm.place_legend(ax)`
     (one legend for both twins; above the plot by itself when nothing inside
     is free);
   - many competing colours: one accent, the rest `dc.gray4`;
   - axis labels stay as written, case and all, and none is added; a label
     that is clipped or overlaps is wrapped (`dm.wrap_axis_labels(fig)`), not
     reworded;
   - cramped panels: `hspace` / `wspace`.
3. Keep the preset's fonts, spines and grid, the data, the chart type and
   its axes (no new twin axis or panel), the axis limits, the canvas size,
   text sizes (but for the value labels above) and what the figure already
   has, adding no text: its title, axis labels, legend and the legend's place
   stay unless the image shows a defect in them (the no-title default is for
   new figures).
4. Save as the next version, look again, and list each change in one line.

Ask one short question only when the purpose (paper, report or slides) is
unknown and would change the answer.
