# Bar value labels and twin-axis colours

Date: 2026-11-06. Status: defaults decided by the user on the review site
(`2026-11-06-b3-labels`); API choice A is the controller's call, recorded here.
Ships after 0.7.0 (the release is cut from 508e6109 first).

## Why

The largest downstream user hand-writes bar value labels in 418 files (`va="bottom"`
texts, 177 files looping over bars): 10+ font sizes, `"bold"` 147 times against the
rule `dm.fw(1)` 3 times, mixed greys, `{v:,.0f}`/`{v:.1f}%` formats that repeat the
axis unit (`$38B` above `(USD B)`), and `set_ylim(0, max*1.12…1.6)` headroom guesses.
`ax.bar_label` appears in 49 files and `dm.annotate_value` in 30. dm's own advanced
`stacked_bar` template hand-writes the same pattern (white ink on light segments:
3 TEXT_CONTRAST). On twin axes, 39 hand merges put the legend on the lower axes (the
line draws over it) and 29 `labelcolor=` calls paint tick text in the raw series
colour (2.39:1, fails contrast); downstream fix commits 287e6e55, 6aa7365e, c0cc9234,
681cf08fd5 chase both.

## Principle

Good defaults, every alternative one keyword away, explicit requests always win
(arguments, later `Text.set_*`/`tick_params` calls), agent-neutral single defaults,
future-oriented (no private matplotlib API, no legacy-compat machinery).

## Decisions

| id | decision | default |
|---|---|---|
| API | new `dm.label_bars` (controller: A) | one call per axes |
| ① | crowded bars | `crowded="rotate"` (all labels kept, vertical) |
| ② | stacked bars | segment labels centred + total on top |
| ③ | label colour | preset text colour |
| ④ | twin-axis decorations | series colour on twin pairs only (ink darkened to 4.5:1) |

Controller calls (not asked): value labels never repeat the axis unit by default
(`fmt=` adds one); decimals follow the rule below; twin legends stay with the existing
`dm.place_legend(ax)` (already merges twins onto the top axes, #523) — no new name.

## API

```python
dm.label_bars(
    ax, bars=None, *,
    where="auto",        # "auto" | "outside" | "inside" | "center"
    total="auto",        # stacks: "auto" (segments + total) | "only" | False
    crowded="rotate",    # "rotate" | "skip" | "inside"
    decimals=None, fmt=None, size=None, color=None,   # color: None | "series" | colour
) -> list[Text]
```

- `bars=None` labels every `BarContainer` on `ax` (incl. `barh`, grouped, stacked);
  a container or list narrows it. Returns the created `Text` artists.
- Built on matplotlib's public `ax.bar_label` geometry (edge/center, the container's
  orientation and datavalues); text, fit and headroom settle in the draw pass that
  `dm.simple_layout` already runs, so later limit changes keep labels consistent.
- EXPERIMENTAL in 0.8 (listed in `dm.EXPERIMENTAL`), documented in docs/api.

## Label rules (defaults)

- Look: `dm.fs(-1)`, `dm.fw(1)`, preset text colour, offset 3 pt (as `annotate_value`).
- Unit: printed like the axis — divide by `dm.axis_unit_of(ax)` when `dm.axis_unit`
  scaled it, add no unit, U+2212 minus like the ticks.
- Decimals: 3 significant digits on the largest |value|, then the fewest decimals that
  print every value exactly; one count per call; never a meaningless `.0`.
- Placement: outside the bar end; negative bars below (vertical) / left (barh); stacks:
  segment labels centred (hidden when the segment is shorter than its label) plus a
  total on top; inside ink by `dm.readable_text_color(bar)`.
- Crowding: a label wider than the bar pitch − 1.5 pt triggers `crowded` for the
  whole call (rotate / skip / inside).
- Headroom: the limit grows only by the measured label extent + 3 pt (no `*1.15`).

## Twin-axis decorations (④)

On an axes pair created by `twinx`/`twiny` where each side draws one series family,
`dm.simple_layout` (through `apply_default_tick_format`'s sibling) colours each side's
spine and tick marks with the series colour and its tick labels and axis label with
that hue darkened to 4.5:1 (`dm.ensure_contrast`). Single axes stay neutral. Applies
only while the colours are matplotlib defaults; any explicit `tick_params(colors=…)`,
`labelcolor=`, `set_color` wins. Option to turn it off: `dm.config.twin_colors =
"neutral"` (new field, default `"series"`).

## place_legend fix

`dm.place_legend(ax)` repositions an existing legend instead of rebuilding it when its
entries match, so a title, `handler_map` and tuple handles survive (the #427/681cf08
loss). A lint rule flags the hand-merge pattern (`h1 + h2 → ax.legend(...)`) and
suggests `dm.place_legend`.

## Non-goals

`annotate_value` / `label_line_ends` behaviour unchanged; no change to MCP (frozen);
no colour token changes; no new validation checks in this change (follow-ups below).

## Tests (executable here)

- The six PoC charts (quarterly, grouped with negatives, stacked, horizontal, 24 dense,
  twin) reproduce the approved captures' label texts, positions class and colours;
  0 label-label overlaps, 0 labels on bars, `validate_figure` 0 findings.
- Unit/decimals with `dm.axis_unit` (max/whole, Korean), negatives, zero, NaN bars.
- Each keyword alternative; explicit later edits survive `simple_layout` repeats.
- Twin colours: series default, explicit colours win, single axes untouched,
  `twin_colors="neutral"`.
- place_legend keeps title/handler_map/tuple handles; lint rule finds the hand merge.
- Pixel baselines: none contain bar labels or twin pairs except `dual_axis_timeseries`
  (twin) — regenerate only after the user approves its before/after.

## Follow-ups (separate)

`VALUE_LABEL_ON_DATA` check (label box over bars/lines), UNIT_DUP for value labels,
converting downstream `plot_design` and dm's `stacked_bar` template to `dm.label_bars`.

## Calls after the builder check (controller, not asked)

1. Labels print like the ticks: when `dm.axis_unit` put the unit in the label, labels
   are plain scaled numbers; when the tick formatter carries a suffix (default SI `35G`,
   `format_axis_*`, percent), labels use the same unit decision and suffix (`33G`, `31%`).
2. `fmt=`: a `str` is a `{}` template around the number text after the decimals rule
   (`fmt="${}B"` → `$38.5B`); a callable gets the value scaled to the axis unit and
   returns the whole text (decimals rule not applied).
3. Stacks are containers at the same positions whose bottoms equal the running top of
   the previous containers. Floating/waterfall bars are not stacks (no totals). Mixed
   signs: the total is the net sum, placed beyond the side the net points to.
4. Headroom never overrides a limit the caller set (autoscale off): a label that does
   not fit sits outside the axes and `simple_layout` reserves the margin.
5. On a twin pair, labels are added to the top-most twin with the bar axes' data
   transform, so the twin's line never draws over them (crossing avoidance is the
   `VALUE_LABEL_ON_DATA` follow-up).
6. Twin colours: a side qualifies when all its data artists share one hue (one line,
   one container, or same-colour artists); grouped/multi-hue sides stay neutral; each
   side decides alone; when both sides resolve to the same hue, both stay neutral.
   Spines and tick marks use the colour as it shows (alpha composited) with at least
   3:1 against the background; text is darkened to 4.5:1.
7. `place_legend(ax)` on a twin pair rebuilds the legend on the top twin keeping its
   title and `handler_map` when every entry is a plain artist; a legend with handles it
   cannot rebuild faithfully (tuple handles) is left untouched — the explicit legend wins.
8. `barh` never rotates: when rows are thinner than the text, `crowded="rotate"` falls
   back to hiding labels that would overlap (alternate rows), and the docs point to a
   taller figure.

## Left to the builder

Module placement (annotation slice; respect `scripts/check_boundaries.py`), how the
draw-pass hook is registered, the exact crowding measurement.
