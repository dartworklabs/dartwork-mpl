---
name: dartwork-mpl
description: Static charts with matplotlib and dartwork-mpl (import dartwork_mpl as dm) - plot, chart, figure, graph, 그래프, 그림, 플롯, 차트. Use whenever Python code creates, edits, restyles, resizes, saves or reviews a figure for a paper, report, document, dashboard or slides in a project where dartwork-mpl is installed. Gives the four-call skeleton, what makes a chart good, and the draw, check, look loop. Not for interactive web charts (Plotly, D3, Altair).
license: MIT
metadata:
  version: 0.10.1
---

# dartwork-mpl

A thin layer over matplotlib. `Figure` and `Axes` stay native, so everything you know about matplotlib still works. The library owns typography, line weights, spines, colour and margins. You own the message.

**This skill is for dartwork-mpl 0.10.1.** Check once per project: `uv run python -c "import dartwork_mpl as dm; print(dm.__version__)"` (no uv: `python -c ...`). If it prints another version, tell the user, because the calls below may not exist there. `uv run dartwork-mpl install` puts in the skill of the installed version; an older dartwork-mpl without that command needs `uv add "dartwork-mpl>=0.10.1"` first.

This is guidance, not a rulebook. Requests differ. Where it does not cover yours, do what serves the reader of the figure.

## The skeleton

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

years, exports = [2019, 2020, 2021, 2022, 2023], [542, 512, 644, 684, 632]
dm.style.use("report")                                   # 1. preset, before the figure
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))   # 2. physical size
ax.plot(years, exports)
ax.set(xlabel="Year", ylabel="Exports (USD bn)")
dm.simple_layout(fig)                                    # 3. margins, after drawing
print(dm.check(fig))                                     # defects, each with its fix
dm.save_formats(fig, "output/exports-v1", formats=("png", "pdf"))   # 4. then look at the PNG
```

1. **Preset by where the figure goes.** `scientific` for a paper or thesis, `report` for a report, document or dashboard, `presentation` for slides or a deck. Also `poster`, `web`, `dark`, `minimal`. Korean text anywhere on the figure takes the `-kr` twin (`report-kr`), which carries the Korean fonts.
2. **Size in physical units.** `dm.figsize("12cm", "wide")` takes a width and an aspect token, a ratio or a height. With no size in the request, `dm.figsize_for(n_points=, n_series=)` picks one from how dense the chart is. A width of your own stays within the width the preset's text is sized for: 17 cm for `report` and `scientific`, 25 cm for `poster` and `presentation`. The height follows the content. On a wider canvas the same text reads small: a bigger medium takes its preset, not more centimetres. A figure made at its final size keeps its text at the preset's point size on the page.
3. **`dm.simple_layout(fig)` after everything is drawn.** It measures the text and sets the margins, and wraps or turns labels that collide. Leave rotation and panel spacing to it unless the user asks.
4. **`dm.save_formats`** keeps the canvas at the size you set. The stem and formats are the caller's choice: if the user or a calling script names a path or format, use exactly that, with no `output/`, no `-vN` and no extra PDF (`dm.save_formats(fig, "exports", formats=("png",))` writes one `exports.png`). The `output/<name>-v1` stem in the skeleton is only the default when nobody named one.

`figsize=(6, 4)`, `plt.tight_layout()`, `plt.style.use(...)`, `bbox_inches="tight"` and a bare `fig.savefig()` all bypass the physical sizing, so the figure no longer prints at its stated size. Use them only when the user asks.

Sizes written in code stay relative to the preset: `dm.fs(1)` is the preset font size plus one step, `dm.lw(1)` and `dm.fw(1)` the same for line width and weight. Below the base, `dm.lw` takes off a step while half a step is left and halves the width after that, so `dm.lw(-1)` is a thinner line, never a missing one. Colours are strings: `"dc.blue6"` (family, step 0 light to 9 dark). Leave `color=` out and the preset cycle applies.

## What a good chart is

**It makes one point.** Before any plotting code, say in one sentence what the reader should take away: "Exports recovered faster than imports after 2021." That sentence picks the form. A change over time is a line, a ranking is sorted bars, a relationship is a scatter, parts of a whole are stacked bars. If you cannot write the sentence, plot the data plainly and say the figure has no single message yet.

**The point is visible without reading the axes.** Put the series that matters in colour and the rest in grey. Name lines at their ends when there are only a few. Mark the one value, crossing or period the reader must notice. Order categories by value unless they have an order of their own. Nothing hides something else: shapes that overlap are filled, so the one in front covers the one behind it (the ridges of a ridgeline take the background colour), and the smaller goes on top; a label sits beside its mark, and one moved away to clear a neighbour keeps a thin line to it.

**The medium decides where the words go.** A paper figure leaves its message to the caption, so it has no title. A report or slide figure may say its point in the title: "Exports passed the 2019 level in 2021", not "Exports by year". `ax.set_title` centres it on the plot, which is where most charts want it; when long category names push the plot well off the figure's centre, the title ends up against the far edge, and `fig.suptitle(...)`, centred on the canvas, sits better. State only what the data shows.

**Everything on it encodes something.** Colour means a category, a magnitude or emphasis, never decoration. Every number has a unit, in the axis label. Bars start at zero. Text size encodes nothing: text of one kind (the values in cells, the names of rows) has one size across the figure, and what does not fit its mark goes beside it or is left out, not shrunk.

**What belongs together stands together, and what should meet does meet.** A label is read with the mark it stands nearest, so a value sits at its own bar, nearer to it than to any other. Things meant to line up do so exactly: a band is centred on the row it marks, a connector ends on the visible corner it points at, touching segments are the same size, and an axis ends on a tick where the data leaves room for that (`references/craft.md`, "Edges and ends").

## Defaults to steer away from

Generic output looks like this. When the request leaves a choice open, do not spend it here:

- a legend box for two or three lines, where end labels would do
- a different colour on every bar when the bars are one series
- a title that repeats the axis labels
- a number on every bar and point while the axis says the same, so no number stands out
- two y axes, which invent a relationship from the choice of scales
- rotated tick labels, where horizontal bars or a wider canvas would read flat
- a grid, a border and markers on every point competing with the data

The opposite failure is the empty chart: technically clean and saying nothing. Spend your one bold move on the point.

## The user's data and words

**The user's words win.** A named size, colour, title, font size or "no legend" is done exactly, even where this page would choose otherwise. An "only X" edit changes X and nothing else. Free choices are the ones the request leaves open.

**The data is not yours to change.** Never drop, fill, sort, aggregate, clip or invent rows without saying so. A missing value stays a visible gap. Names in the data stay as written. Template numbers are placeholders, never results.

**The script draws the same figure every time it runs.** Seed any randomness you bring in (jitter in a strip plot, a subsample of a large scatter, bootstrap bands, example data when the user gave none): `rng = np.random.default_rng(0)`, then draw from `rng`.

Text on the figure follows the document it goes into. Unknown: follow the language of the request's own labels and data.

## Check, then look

A figure is finished when you have looked at it, not when the script ran. Run the script with `uv run python plot.py` in a uv project (one with `pyproject.toml` or `uv.lock`); elsewhere `uv run --with dartwork-mpl python plot.py` runs it without installing anything.

1. `print(dm.check(fig))` measures the drawn figure: clipped text, overlapping text and tick labels, a legend on data. Each finding is a defect a reader will see, with a line on what to try: fix it and run again. That it still reads is not a reason to keep one; keep one only when the figure needs it that way, and tell the user which and why. `NOT RUN` means a rule could not measure, so say so.
2. Open the PNG and read it as the reader would. Does the point land in five seconds? Is anything cut, crowded or empty? Is the data what the user gave? Check that the visible plot and its supporting elements sit together on the canvas, with room on both sides. What you set in open space inside the plot (an inset, a note, a key) sits in the middle of that space with its own labels counted, not against the frame; a label for a band or region stays inside it or wholly beside it, not across its edge. For placement choices, see `references/layout.md`.
3. Fix what you saw and say what changed. Revising with a user, save as the next version (`-v2`, keep v1); with a path the user or caller named, overwrite that path. If you cannot view images, say the figure was not visually reviewed.

`dm.check` finds the mechanical defects. Whether the chart says anything is up to you.

The library says what it changed on its own: each automatic change (tick labels turned, a name wrapped, a radar's names moved off its circle, a value label gone, a legend moved, `1M` on an axis, whole-number ticks on an axis of months or counts) prints one `dartwork-mpl:` line on stderr with what, on which Axes, why, and what to try. Read those lines after a run and tell the user what they say before you work around one. `dm.quiet()` turns them off.

## Tools for the craft

| To | Call |
|---|---|
| name lines at their ends, no legend box | `dm.label_line_ends(ax)` |
| a legend that avoids the data, or sits on a named side | `dm.place_legend(ax)`, `dm.place_legend(ax, loc="above")` |
| one legend for panels that share series | `dm.figure_legend(fig)` |
| values on bars; one value on a line or point | `dm.label_bars(ax)`; `dm.annotate_value(ax, x, y, text)` |
| a column of names or numbers beside the plot (a net, a share, a table that stands in for a legend) | write the texts on the plot's Axes, then `dm.place_columns(ax, column)`; several: `dm.place_columns(ax, first, second)` |
| align the edges or decimal points inside a column | `dm.align_texts(texts, "left")` or `dm.align_texts(texts, "decimal")` |
| panel letters; a source or note line | `dm.label_axes(axes)`; `dm.add_note(fig, text)` |
| texts `dm.check` reports as `TEXT_CONTRAST` and that cannot move onto one background (a note over bars, contour numbers) | `dm.legible(texts)`, after `dm.simple_layout(fig)`; then check again |
| 만/억 on the ticks | `dm.format_axis_myriad(ax)` |
| 12k on the ticks (from a million the axis prints `1M` by itself) | `ax.yaxis.set_major_formatter(matplotlib.ticker.EngFormatter(sep=""))` |

Call them before `dm.simple_layout`, which makes room for what they add; `dm.legible` alone goes after it and after `dm.check` has named the texts, because it reads the figure as drawn.

## Look things up

Read only the page the task needs. Without this folder, `uv run dartwork-mpl path` (or `dartwork-mpl path`) prints where it is.

| Need | Read |
|---|---|
| finding a reference chart (`search_references`); choosing the form, emphasis, annotation, titles; numbers on bars, distributions, heatmaps, small multiples; outlines, connectors, bands, where an axis ends | `references/craft.md` |
| canvas sizes, margins, grids, twin axes, legends outside, colorbars | `references/layout.md` |
| changing an existing figure, value labels | `references/editing.md` |
| colour names, palettes, colormaps, a ramp between two colours | `references/colors.md` |
| Korean text, fonts and number units | `references/korean.md` |
| what each `dm.check` finding means | `references/review.md` |
| native matplotlib details: dashes, spines, exact canvas regions | `references/recipes.md` |
| every aspect token, colour library or lint rule | `dm.list_aspects()`, `dm.list_color_libraries()`, `dm.lint_rules()` |
