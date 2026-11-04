# The look a request does not name comes from the library (#523, PoC)

Status: decided 2026-10-24. The owner adopted all seven recommendations on
the review page (local branch `t3/library-owned-defaults-20261023`, stacked on
#539 with the agent-neutral change folded in) and added the aim: a basic
framework that responds well to customization requests.

## Problem

The owner wants any agent, on any run, to draw a predictable, consistent
figure for the same request, and no agent distinction in this repository
(2026-10-22). Measured on the phase 0 eval (40 request pairs, Claude Code vs
Codex, no skill): the same canvas 15/40, grid choice 25/40, axis formatter
26/40; Codex overrode the preset in 13/40 figures, Claude in 2/40. With the
skill the canvas still agreed in 4/12 pairs, and one host gave 12 vs 18 cm
for the same request on two runs. The skill gave ranges ("report 13–17 cm")
and the library left canvas, title, grid, spines, colours and margins to the
code author, so each agent filled them by habit.

## Rule

What the request names, the agent does. What it does not name, the library
decides: one answer, not a range.

## Mechanisms

1. **Canvas: `dm.figsize_for(kind, n_points=, n_series=, dual_axis=, nrows=,
   ncols=)`** (provisional, `dm.EXPERIMENTAL`). The active preset's canvas.
   Ported, without financial vocabulary, from company-analysis'
   `plot_design` (2026-07-09 plot-consistency standard): report widths
   9 / 12 / 14.5 / 17 cm, chosen by kind and data density.

   | Kind | Base | Aspect | Density hints |
   |---|---|---|---|
   | `default` (lines, bars, areas, scatter) | 12 cm | 4:3 | yes |
   | `barh` | 14.5 cm | 4:3 | yes |
   | `compact` | 9 cm | 4:3 | yes |
   | `matrix` | 12 cm | 1:1 | no |
   | `dense` | 17 cm | 2:1 | no |
   | `strip` | 17 cm | 0.45 | no |
   | `slide` (one whole 16:9 slide, any preset) | 25.4 cm | 16:9 | no |

   Hints: `n_points <= 6` and `n_series <= 2` on one axis → 9 cm; a twin y
   axis, `n_series >= 4` or `n_points > 12` → 14.5 cm. A grid takes 17 cm
   and keeps each panel at the kind's aspect, at most 24 cm tall.
   `scientific` keeps one panel in one column (9 cm) whatever its density;
   grids and the full-width kinds take two (17 cm). (Revised 2026-10-24:
   mapping 14.5 → 17 cm drew single-panel templates at 17 × 12.75 cm.)
   `presentation` and `poster` scale widths by font size / 8 pt (10.5 pt →
   ×1.31: 12, 16, 19, 22.5 cm), grids at most 16:9. The preset is tracked by
   `dm.style.use` / `context`; a `font_size=` override does not resize.
   `dm.grid_shape(n)` lays out `n` small multiples: one row up to three
   panels, then `ceil(sqrt(n))` columns.
2. **Skill: the preset owns the look.** Spines, grid, ticks, fonts,
   background and margins stay the preset's unless asked; no title,
   subtitle, source note or extra panel unless asked (a caption or the
   slide carries the title; company-analysis bans `ax.set_title` for the
   same reason); a vague request gets one panel. Sizes come from
   `dm.figsize_for`; a size the user names goes to `dm.figsize`.
3. **Validator: `PRESET_OVERRIDE` (INFO).** Grid, spine visibility or
   facecolor that differs from the active preset, so the review loop sees
   unrequested restyling. Advisory: the check cannot see the request.
   Axis-off, polar, 3-D, colorbar, pie and twin Axes are skipped; none of the
   36 bundled templates is flagged (`dm.plot_diverging_bar` is, as it hides
   its own spines).
4. **Metric: agreement, not per-agent scores.** Per case, four units
   (two hosts × two runs) must agree on canvas, preset and look features.

## PoC evidence

Six generate cases (report line, grouped bar, small multiples, paper,
slides, vague), Claude Code (sonnet, high) and Codex (gpt-6-astra, medium),
two runs each, `--hide-grading`; every run passed its task checks.

| Run | Skill | All four runs agree on canvas | Claude = Codex canvas | Same host twice | Distinct canvases |
|---|---|---|---|---|---|
| `p3-before-20261023` | 460c797f | 1 / 6 | 2 / 12 | 6 / 12 | 17 |
| `p3-after-20261023` | v1 (e06a4b6d) | 3 / 6 | 7 / 12 | 10 / 12 | 10 |
| `p3-after2-20261023` | v2 (55125ef9) | 6 / 6 | 12 / 12 | 12 / 12 | 6 |

v1 also brought title, figure text, grid, spines and background to full
agreement (6 / 6; before 3, 3, 1, 4, 5). The remaining canvas splits were
choices the library still left open: a named width with the aspect unstated
(3:2 from `figsize_for` vs 4:3 from `dm.figsize`), a "full 16:9 slide"
(26 cm, 10 in or 13.33 in), and six panels as 2×3 or 3×2. v2 (55125ef9)
closes them with the 4:3 default, kind `slide` and `grid_shape`, and in
`p3-after2-20261023` all four runs drew the same canvas for every case.
Still open: legend placement, line markers, tick label format (`%`, `0.1`
vs `10⁻¹`) and end-value labels; and a whole slide at 25.4 cm makes the
`presentation` 10.5 pt text look small. `agreement.py` computes the table;
figures at physical scale are on the review page.

## Decisions (2026-10-24)

1. Adopted: the library decides what the request does not name.
2. Adopted: the company-analysis widths 9 / 12 / 14.5 / 17 cm.
3. Adopted: 4:3 default aspect.
4. Adopted: font-scaled tiers for charts on a slide; 25.4 cm (10 in) for a
   whole slide.
5. Adopted: no title unless asked; small multiples name their panels.
6. Adopted: templates size with `dm.figsize_for` and drop titles (follow-up
   branch with its own PoC).
7. Adopted: the agent-neutral installer change joins #539.

Follow-up from the owner's aim: a requested element keeps the preset's style
for every detail the request does not name (title, gridlines, legend side,
width only), and requested elements must compose without collisions.

## Not in this PoC

- The MCP guide text still gives ranges (MCP is frozen); the policy and
  quickstart follow decision 2.
- Value labels, legends and formatters are left to the request; the
  agreement table shows whether they still diverge.
- The 17 cm `oversize-width` lint stays page-fit advice.
