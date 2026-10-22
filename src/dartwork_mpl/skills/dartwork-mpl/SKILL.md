---
name: dartwork-mpl
description: matplotlib plot, chart, figure, graph, 그래프, 그림, 플롯, 차트 with dartwork-mpl (import dartwork_mpl as dm). Use whenever Python code creates, edits, resizes, restyles, saves or reviews a static figure for a paper, report, document, dashboard or slides in a project where dartwork-mpl is installed. Covers the style preset, physical size with dm.figsize, dm.simple_layout margins, dm.save_formats, keeping data and NaN gaps intact, natural-language edits of one target and the render-inspect-revise loop. Also read it when a generic dataviz skill is active, for how dartwork-mpl figures differ.
license: MIT
---

# dartwork-mpl

A thin layer over matplotlib (presets, physical sizes, margins, checks).
`Figure` and `Axes` stay native: any matplotlib call or property works.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")                                          # 1. preset first
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))  # 2. physical size
ax.plot([0, 1, 2], [1, 3, 2])                                  # preset colours
ax.set(xlabel="Time (s)", ylabel="Response")
dm.simple_layout(fig)                                           # 3. after drawing
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"))  # 4. save
# 5. open output/figure-v1.png and look at it before answering
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

- `dm.figsize(width, second)`. width: `"13cm"`, `"5in"`, `"170mm"`, `dm.cm(13)`,
  `dm.col1` (9 cm), `dm.col2` (17 cm); bare numbers are rejected. second: an
  aspect token (`standard` default 4:3, `wide` 3:2, `slide` 16:9, ...),
  `"16:9"` (width:height), a number (height/width) or a height (`"8cm"`).
- Drafts: paper 9 or 17 cm, report 13–17 cm, slides by ratio and placement.
  Not limits: keep any size the user asks for, wider than 17 cm included.
- `dm.simple_layout(fig)` after everything is drawn (labels, legend,
  colorbar) sets the outer margins; never `plt.tight_layout()`. Room:
  `margin="2mm"` or `mr="1cm"`. Gaps between panels (`hspace`, `wspace`) stay yours.
- `dm.save_formats` keeps the exact canvas and prints `[VISUAL]` findings.

## Data

Plot the user's values as given. Never drop, fill, sort, aggregate, clip or
invent rows silently; state every transformation. Missing values stay visible
gaps (`dm.validate_data` drops NaN/Inf rows unless `allow_nan=True`). A preview
is not the dataset; template numbers are placeholders, never data.

## Values

- Leave `color=` out so the preset cycle applies; name one when asked or to
  emphasise (`dc.blue6`: family + step 0–9). More: `references/colors.md`.
- `dm.fs(n)` = preset font size + n pt, `dm.lw(n)` = preset line width + n pt,
  `dm.fw(n)` = preset weight + 100·n. They read the preset, not an artist.
  One step bigger on an artist: `t.set_fontsize(t.get_fontsize() + 1)`.
- Explicit user values win exactly (`fontsize=12`, `"#235fa4"`), even when
  lint flags literals. Hairlines stay literal (`linewidth=0.3`).
- No meaningless decimals: `200`, `0`, `1k, 2k`, not `200.0`, `0.0`, `1.0k, 2.0k`;
  if one label needs a decimal the axis shares it (`17.5, 20.0`; `0.5M, 1.0M`).
- One unit per axis. `dm.format_axis_si` / `_myriad` use the largest tick's unit
  (`0.25억 … 1.75억`); `unit="whole"` an all-integer one (`2,500만 … 17,500만`),
  `unit="k"` / `"만"` a fixed one. An explicit `decimals=` is exact.
- Numeric value labels on bars and lines (`ax.bar_label`, `ax.text`) use
  `fontweight=dm.fw(1)`; titles, axis labels, ticks and legends keep theirs.

## Edits

"Only X" requests: find that artist (panel, series, label, title), change only
the asked property, keep data, preset, canvas, colours, legend and the rest.
Axis-label edits touch the label Text objects, not `font.size` or ticks. Keep
the original script; write the revision as a new script and stem. Broad asks
("make it look better", "더 보기 좋게") are normal: keep data and preset, fix
what the image shows, list each change. Ask one short question only when the
target is truly ambiguous.

## Review loop (every figure and revision; script: `references/review-loop.md`)

1. Save `output/figure-v1` (a path the user names gets the final version).
2. Open the PNG (Claude Code: Read; Codex: view_image) and look: clipped or
   overlapping text, legend over data, crowded ticks, wasted space, wrong data.
   If you cannot view images, say the figure was not visually reviewed.
3. Read `dm.validate_figure(fig, quiet=True)`: fix WARNING, weigh INFO.
   `CHECK_FAILED` means a check did not run: report validation as incomplete.
4. Change only what is needed or requested.
5. Save `figure-v2`, keep v1, look again. Report changes and kept warnings.

## When /dataviz or other generic chart advice is also active

Use it for chart choice and honest axes. For construction the active preset
is the design system and the output a static file (print, PDF, slides): skip
hover, tooltips, rounded bar ends, placeholder palettes, pixel line widths, a
legend on every chart (2+ series: legend or direct labels). Use `dm.figsize`.

## Never

`figsize=(w, h)` · `plt.tight_layout()` · `plt.style.use()` · `dm.subplots` /
`dm.figure` (removed) · bare `fig.savefig()` · `dpi=` on `plt.subplots`.

## References

| Need | Read |
|---|---|
| tokens, pixels, grids, ratios, mosaics, twin axes, panel labels | `references/sizing-and-layout.md` |
| finding the artist, one-target edits, "make it better" | `references/editing.md` |
| colour names, palettes, colormaps, one highlighted series | `references/colors.md` |
| plot text language, Korean presets, other scripts | `references/korean.md` |
| render, inspect, revise script; findings; lint | `references/review-loop.md` |
| starting from a bundled template | `references/templates.md` |
| the full cookbook, policy, lint catalog | `dm.get_prompt("03-recipes")`, `"01-policy"`, `"02-anti-patterns"` |
