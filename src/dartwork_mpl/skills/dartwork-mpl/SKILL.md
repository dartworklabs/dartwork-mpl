---
name: dartwork-mpl
description: matplotlib plot, chart, figure, graph, 그래프, 그림, 플롯, 차트 with dartwork-mpl (import dartwork_mpl as dm). Use whenever Python code creates, edits, resizes, restyles, saves or reviews a static figure for a paper, report, document, dashboard or slides in a project where dartwork-mpl is installed. Covers the style preset, physical size with dm.figsize, dm.simple_layout margins, dm.save_formats, keeping data and NaN gaps intact, natural-language edits of one target and the render-inspect-revise loop. Also read it when a generic dataviz skill is active, for how dartwork-mpl figures differ.
license: MIT
---

# dartwork-mpl

A thin layer over matplotlib; `Figure` and `Axes` stay native.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

x, y = [0, 1, 2], [1, 3, 2]
dm.style.use("report")                                          # 1. preset first
fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=len(x), n_series=1))
ax.plot(x, y)                                  # 2. the preset's canvas and colours
ax.set(xlabel="Time (s)", ylabel="Response")
dm.simple_layout(fig)                                           # 3. after drawing
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"))  # 4. then look
```

## Preset by purpose

User size or style and journal/template rules first, then earlier project choices:

| Purpose | Preset |
|---|---|
| paper, journal, thesis, 논문 | `scientific` |
| report, document, dashboard, 보고서, 문서 | `report` |
| talk, slides, 발표 | `presentation` |
| poster · web page · dark background · sparse | `poster` · `web` · `dark` · `minimal` |

Plot text you write is English whatever the chat language; another language
only when the user asks ("제목은 한국어로"). Korean on the figure, asked for or from the data,
takes `-kr` (`report-kr`); edits keep its language and preset.

## Size, layout, save

- No size asked, or a figure moved to slides: `dm.figsize_for(kind, n_points=, n_series=)`
  (report 9/12/14.5/17 cm by density, paper columns; `presentation` 10.5 cm tall, 11.4/15.4/
  23.4 cm wide for ≤4/≤6/more x points); count x points and series; category names under x: `labels=names`
  (the narrowest of those widths that keeps them flat, half an em apart); `dual_axis=True` with `twinx`;
  kind `"matrix"`, `"grouped"` for bars side by side (`n_series` bars per group), `"full_slide"` (25.4 × 14.29 cm) for a whole 16:9 slide; bars vertical,
  `"barh"` + `ax.barh` only when names overlap or asked; n panels: `dm.grid_shape(n)` → `figsize_for(nrows=, ncols=)`.
- A size the user names wins, any size: `dm.figsize(width, second)`. width `"13cm"`, `"5in"`,
  `dm.col1` (9 cm), `dm.col2` (17 cm), never a bare number; second `standard` 4:3, `wide` 3:2,
  `slide` 16:9, `"16:9"`, a ratio or `"8cm"`. A width alone: a new figure is 4:3; an edit
  keeps the old height in cm.
- `dm.simple_layout(fig)` after everything is drawn sets outer margins (each SubFigure's in its own box; `margin=0` by default;
  `"2mm"` adds a buffer), tick numbers and thins crowded date labels; where text collides it wraps axis names and tick labels (bottom labels also under half an em apart), widens panel gaps nobody set, turns tick labels that cannot wrap and grows a tick pad where an x and a y label meet at a corner, so leave rotation, tick pads and `hspace`/`wspace` to it; `dm.save_formats` keeps the canvas.
- Never `figsize=(w, h)`, `plt.tight_layout()`, `plt.style.use()`, bare
  `fig.savefig()`, `dpi=` on `plt.subplots`, `dm.subplots`/`dm.figure` (removed).

## Look: the preset's, plus what was asked

Spines, grid, ticks, axis limits (bars start at 0), fonts, background and margins are the
preset's; change them only on request. Tick numbers and dates are the library's (`1,750`,
`0.5M`, `16 … 24` on whole-year ticks (x data all integers in 1900–2099, also elevations; on y only `barh` positions; `tick_years=4`: `2016`), `23.01`, `23.Q1`, Korean `50만`; dates under bars: `dm.format_axis_dates(ax, dates)`, not rotated): no
formatter, locator or tick list unless asked or naming categories; no request, the default; a request, that format. No figure title, subtitle,
source note, value labels, extra panel or one-series legend unless asked (small multiples name each panel);
a vague ask gets one panel. An asked-for element keeps the preset's style in every detail not
named: `ax.set_title(t)`, `ax.grid(True, axis="y")`, `dm.add_note(fig, t)`, `dm.label_line_ends(ax)`.
A legend you add, move or merge (a twin pair's two into one) is `dm.place_legend(ax)`, with `loc=` only for a side the user names; never `ax.legend(...)`, `bbox_to_anchor` or `ncols=` of your own (arguments it had stay); others stay as they are. A new figure of eight or more lines names them with `dm.label_line_ends(ax)`, unless a legend is asked for; panels that share their series get one `dm.figure_legend(fig)`.
A generic chart skill gives chart choice and honest axes; static output: no hover, tooltips,
rounded bar ends, placeholder palettes.

## Data

Plot the user's values as given. Never drop, fill, sort, aggregate, clip or invent rows silently; state every transformation. Missing values stay visible gaps; legacy `dm.validate_data` drops NaN/Inf unless `allow_nan=True`.
Explicit policies require `allow_nan=False`: `references/data-policy.md`. A preview is not the dataset;
template numbers are placeholders. Dates are dates, a bare year (2012) a number; "A against B": A on y ("rent against floor area": rent on y).
A new figure labels both axes. Labels and legend names are column names translated word for word, sentence case, also when the request words
them otherwise (`order_date` → `Order date`, `margin_pct` → `Margin (%)`, `고객수` → `Customer count`); only a value with no column takes the request's noun
word for word, every word kept, in its order (`수출 증가율` → `Export growth rate`, "the share of online orders" → `Share of online orders`); no unit nothing states (a rate the data gives stays bare, no `(%)`; a share you compute × 100 says `(%)`).

## Values

- Leave `color=` out so the preset cycle applies; name one when asked or to emphasise
  (`dc.blue6`: family + step 0–9). More: `references/colors.md`.
- `dm.fs(n)`/`dm.lw(n)`: preset font size/line width + n steps (1 pt; 2.6 pt in
  `presentation` = `scientific` × 2.6); `dm.fw(n)`: weight + 100·n (preset, not an artist).
- Explicit user values win exactly (`fontsize=12`, `"#235fa4"`), even when lint flags
  literals. Hairlines stay literal (`linewidth=0.3`).
- k/M or 만/억 asked: `dm.format_axis_si` / `_myriad`. One unit per axis, the
  largest tick's unit (`0.25억 … 1.75억`), `unit="whole"` (`2,500만 … 17,500만`);
  `decimals=` is exact. No meaningless decimals: `200`, `1k`, not `200.0`, `1.0k`.
- Unit in the label, plain ticks: `dm.axis_unit(ax, "y", label="인구 ({unit}명)")`. Asked for four-digit years, concise date words or k/M in Korean: `with dm.config.override(tick_years=4)` / `(date_style="concise")` / `(number_ladder="si")` from figure creation to the last `dm.simple_layout`.
- Numeric value labels you add: on bars `dm.label_bars(ax)` (no request, its defaults; a request, that keyword: `where=`, `decimals=`, `fmt=`, `sign=` …); on lines and points `dm.annotate_value(ax, x, y, text)` (`fs(-1)`, `fw(1)`, a free side); existing ones keep theirs (broad asks: Edits).

## Edits

"Only X" requests: find that artist (panel, series, label, title), change only the asked property; keep data,
preset, canvas, colours, the legend as it is (a highlight too; a `LEGEND_OVERLAP` the original already has stays, reported; one your
change makes: `dm.place_legend(ax)` on that legend's axes with its own arguments, not spacing or font size; list it) and the rest; keep the original, write the revision as a new script and stem.
A preset switch (paper → slides) multiplies pt values written in the code by the presets' ratio (`scientific` →
`presentation`: × 2.6, unrounded). Broad asks ("look better"): keep data, preset, canvas, chart type and axes (no
new twin), limits (a line crossing value labels too), axis labels as written, text (add none) and its size (touching
value labels larger than `dm.fs(-1)` drop to it and, with no weight written, take `dm.fw(1)`), title and legend; fix only defects the image shows, list each.

## Review loop (every figure and revision; script: `references/review-loop.md`)

1. `r = dm.review(fig, "output/figure-v1")`: PNG + PDF, every finding, a summary (a path the user names gets the final version).
2. Open the PNG with your image-viewing tool: clipped or overlapping text, legend over data,
   crowded ticks, wasted space, wrong data. No image tool: say it was not visually reviewed.
3. Read `r.findings` (an edit: on the original first; "only X" keeps its warnings, reported): fix WARNING, weigh INFO; `CHECK_FAILED` (`r.complete` False): incomplete.
4. Change only what is needed; `dm.review(fig, "output/figure-v2", baseline="output/figure-v1", allow=[paths you meant])`, keep v1; `r.unexpected`: every other change, explain or undo; look again; report changes, warnings.

## References

| Need | Read |
|---|---|
| tokens, pixels, grids, ratios, mosaics, twin axes, panel labels | `references/sizing-and-layout.md` |
| explicit NaN/Inf retention, rejection or cleanup; native vs MCP data checks | `references/data-policy.md` |
| finding the artist, one-target edits, "make it better" | `references/editing.md` |
| colour names, palettes, colormaps, one highlighted series | `references/colors.md` |
| plot text language, Korean presets, other scripts | `references/korean.md` |
| render, inspect, revise script; findings; lint | `references/review-loop.md` |
| bundled templates; the full cookbook, policy, lint catalog | `references/templates.md`; `dm.get_prompt("03-recipes")`, `"01-policy"`, `"02-anti-patterns"` |
