---
name: dartwork-mpl
description: matplotlib plot, chart, figure, graph, 그래프, 그림, 플롯, 차트 with dartwork-mpl (import dartwork_mpl as dm). Use whenever Python code creates, edits, resizes, restyles, saves or reviews a static figure for a paper, report, document, dashboard or slides in a project where dartwork-mpl is installed. Covers the style preset, physical size with dm.figsize, dm.simple_layout margins, dm.save_formats, colour names, Korean text, natural-language edits and the render-inspect-revise loop. For these figures it takes precedence over generic web dataviz advice.
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
ax.plot([0, 1, 2], [1, 3, 2], color="dc.teal3")
ax.set(xlabel="Time (s)", ylabel="Response")
dm.simple_layout(fig)                                           # 3. after drawing
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"))  # 4. save
# 5. open output/figure-v1.png and look at it before answering
```

## Preset by purpose

Explicit user size or style and journal/template rules come first, then
earlier choices in the project, then:

| Purpose | Preset |
|---|---|
| paper, journal, thesis, 논문 | `scientific` |
| report, document, dashboard, 보고서, 문서 | `report` |
| talk, slides, 발표 | `presentation` |
| poster · web page · dark background · sparse | `poster` · `web` · `dark` · `minimal` |

Add `-kr` (`report-kr`) only when the plot text is Korean; the chat language
does not decide it. Keep the chosen preset through later edits.

## Size: `dm.figsize(width, second)`

- width: `"13cm"`, `"5in"`, `"170mm"`, `"24pt"`, `dm.cm(13)`, `dm.col1` (9 cm),
  `dm.col2` (17 cm). Bare numbers are rejected.
- second: an aspect token, `"16:9"` (width:height), a number (height/width)
  or a height (`"8cm"`, `dm.cm(8)`).
- Aspect tokens: `tall` 2:3, `portrait` 4:5, `square` 1:1, `standard` 4:3
  (default), `a4` √2:1, `wide` 3:2, `golden` 1.618:1, `slide` 16:9,
  `cinema` 2:1, `panoramic` 3:1.
- Drafts: paper 9 or 17 cm, report 13–17 cm, slides by ratio and placement.
  Not limits: keep any size the user asks for, wider than 17 cm included.
- Pixels need a DPI: 1920 px at 200 DPI is `dm.inch(1920 / 200)` with
  `dm.save_formats(..., dpi=200)`.

## Layout and save

- `dm.simple_layout(fig)` after everything is drawn (labels, legend,
  colorbar) sets the outer margins. Never `plt.tight_layout()`. More room:
  `margin="2mm"` or one side `mr="1cm"`. Panel gaps stay yours:
  `gridspec_kw={"hspace": 0.5, "wspace": 0.35}`.
- `dm.save_formats` keeps the exact canvas and prints `[VISUAL]` findings.
- Grids, ratios, mosaics, twin axes, panel labels, outside legends:
  `references/sizing-and-layout.md`.

## Values

- Colours by name wherever matplotlib takes one: `dc.teal3`, `dc.blue6`,
  `dc.gray4` (steps 0 light to 9 dark); also `oc.*`, `tw.*`, `md.*`, `ad.*`,
  `cu.*`, `pr.*`. Cycle: `dm.set_colors("dc.octave")`. Colormaps:
  `cmap="viridis"`, `cmap="dc.aurora"`. More: `references/colors.md`.
- `dm.fs(n)` = preset font size + n pt, `dm.lw(n)` = preset line width + n pt,
  `dm.fw(n)` = preset weight + 100·n. They read the preset, not an artist.
  One step bigger on an artist: `t.set_fontsize(t.get_fontsize() + 1)`.
- Explicit user values win exactly (`fontsize=12`, `"#235fa4"`), even when
  lint flags literals. Hairlines stay literal (`linewidth=0.3`).

## Edits

Find the exact target (panel, series, artist, property), change only that,
and keep data, preset, canvas size, colours, legend and every other property.
Axis-label edits touch the label Text objects, not `font.size` or ticks.
Ask one short question only when the target is truly ambiguous. Vague asks
("make it look better", "더 보기 좋게") are normal requests: follow the
checklist in `references/editing.md` and list what you changed.

## Review loop (every figure and revision; script: `references/review-loop.md`)

1. Save under a versioned stem: `output/figure-v1`.
2. Open the PNG and look: clipped or overlapping text, legend over data,
   crowded ticks, wasted space, wrong data.
3. Read `dm.validate_figure(fig, quiet=True)`: fix WARNING, weigh INFO.
4. Change only what is needed or requested.
5. Save `figure-v2`, keep v1, look again. Report changes and kept warnings.

## Next to /dataviz or other generic chart advice

For matplotlib figures here the active preset is the design system and the
output is a static file (print, PDF, slides). Skip web-only advice: hover,
tooltips, rounded bar ends, placeholder palettes, pixel line widths, a legend
on every chart (2+ series get a legend or direct labels). Size with
`dm.figsize` in physical units. Chart-choice and honest-axis advice applies.

## Never

`figsize=(w, h)` · `plt.tight_layout()` · `plt.style.use()` · `dm.subplots` /
`dm.figure` (removed) · bare `fig.savefig()` · `dpi=` on `plt.subplots`.

## References

| Need | Read |
|---|---|
| sizes, grids, ratios, mosaics, twin axes, panel labels | `references/sizing-and-layout.md` |
| natural-language edits, finding the artist, "make it better" | `references/editing.md` |
| colour names, palettes, colormaps, one highlighted series | `references/colors.md` |
| Korean plot text | `references/korean.md` |
| render, inspect, revise script; lint | `references/review-loop.md` |
| starting from a bundled template | `references/templates.md` |

Deeper: `dm.get_prompt("03-recipes")`, `dm.get_prompt("01-policy")`,
`dm.get_prompt("02-anti-patterns")`; signatures via `help(dm.figsize)`.
