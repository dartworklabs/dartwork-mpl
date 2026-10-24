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
only when the user asks ("제목은 한국어로"). Korean on the figure, asked for or
from the data, takes `-kr` (`report-kr`); edits keep its language and preset.

## Size, layout, save

- No size asked: `dm.figsize_for(kind, n_points=, n_series=)` (report 9/12/
  14.5/17 cm by density, paper columns, slides scaled); count x points and
  series; `dual_axis=True` with `twinx`; kind `"barh"`, `"matrix"`, `"slide"`
  (whole 16:9 slide); n panels: `dm.grid_shape(n)` → `figsize_for(nrows=, ncols=)`.
- A size the user names wins, any size: `dm.figsize(width, second)`. width
  `"13cm"`, `"5in"`, `dm.col1` (9 cm), `dm.col2` (17 cm), never a bare number;
  second `standard` 4:3, `wide` 3:2, `slide` 16:9, `"16:9"`, a ratio or `"8cm"`.
  A width alone: a new figure is 4:3; an edit keeps the old height in cm.
- `dm.simple_layout(fig)` after everything is drawn sets outer margins
  (`margin="2mm"`) and tick numbers; `dm.save_formats` keeps the canvas.
- Never `figsize=(w, h)`, `plt.tight_layout()`, `plt.style.use()`, bare
  `fig.savefig()`, `dpi=` on `plt.subplots`, `dm.subplots`/`dm.figure` (removed).

## Look: the preset's, plus what was asked

Spines, grid, ticks, fonts, background and margins are the preset's; change them
only on request. Tick numbers and dates are the library's (`1,750`, `0.5M`,
`2024, Mar`): no formatter, locator or tick list unless asked or naming
categories. No figure title, subtitle, source note, extra panel or one-series
legend unless asked (small multiples name each panel); a vague ask gets one
panel. An asked-for element keeps the preset's style in every detail not named:
`ax.set_title(t)`, `ax.grid(True, axis="y")`, `dm.add_note(fig, t)`,
`dm.place_legend(ax)` (no `loc=`/`ncols=` unless named). A generic chart skill
gives chart choice and honest axes; the output is static: no hover, tooltips,
rounded bar ends, placeholder palettes.

## Data

Plot the user's values as given. Never drop, fill, sort, aggregate, clip or
invent rows silently; state every transformation. Missing values stay visible
gaps (`dm.validate_data` drops NaN/Inf rows unless `allow_nan=True`). A preview
is not the dataset; template numbers are placeholders, never data. Read dates
as dates; "A against B" puts A on y. Labels are column names, translated word
for word (`week_start` → `Week start`, `leaf_length_cm` → `Leaf length (cm)`);
a value axis without one takes the request's noun (`Energy`). No invented units.

## Values

- Leave `color=` out so the preset cycle applies; name one when asked or to
  emphasise (`dc.blue6`: family + step 0–9). More: `references/colors.md`.
- `dm.fs(n)`/`dm.lw(n)`: preset font size/line width + n pt; `dm.fw(n)`: weight
  + 100·n (the preset, not an artist: `t.set_fontsize(t.get_fontsize() + 1)`).
- Explicit user values win exactly (`fontsize=12`, `"#235fa4"`), even when
  lint flags literals. Hairlines stay literal (`linewidth=0.3`).
- k/M or 만/억 asked: `dm.format_axis_si` / `_myriad`. One unit per axis, the
  largest tick's unit (`0.25억 … 1.75억`), `unit="whole"` (`2,500만 … 17,500만`);
  `decimals=` is exact. No meaningless decimals: `200`, `1k`, not `200.0`, `1.0k`.
- Numeric value labels on bars and lines (`ax.bar_label`, `ax.text`) use
  `fontweight=dm.fw(1)` and the preset size (no `fontsize=`).

## Edits

"Only X" requests: find that artist (panel, series, label, title), change only
the asked property; keep data, preset, canvas, colours, legend (a highlight
keeps it too) and the rest; keep the original, write the revision as a
new script and stem. Broad asks ("make it look better"): keep data, preset,
canvas, chart type and axes (no new twin), limits, text and its size, title
and legend; fix only defects the image shows (`references/editing.md`), list each.

## Review loop (every figure and revision; script: `references/review-loop.md`)

1. Save `output/figure-v1` (a path the user names gets the final version).
2. Open the PNG with your image-viewing tool and look: clipped or
   overlapping text, legend over data, crowded ticks, wasted space, wrong data.
   If you cannot view images, say the figure was not visually reviewed.
3. Read `dm.validate_figure(fig, quiet=True)`: fix WARNING, weigh INFO.
   `CHECK_FAILED` means a check did not run: report validation as incomplete.
4. Change only what is needed or requested; save `figure-v2`, keep v1, look
   again. Report changes and kept warnings.

## References

| Need | Read |
|---|---|
| tokens, pixels, grids, ratios, mosaics, twin axes, panel labels | `references/sizing-and-layout.md` |
| finding the artist, one-target edits, "make it better" | `references/editing.md` |
| colour names, palettes, colormaps, one highlighted series | `references/colors.md` |
| plot text language, Korean presets, other scripts | `references/korean.md` |
| render, inspect, revise script; findings; lint | `references/review-loop.md` |
| bundled templates; the full cookbook, policy, lint catalog | `references/templates.md`; `dm.get_prompt("03-recipes")`, `"01-policy"`, `"02-anti-patterns"` |
