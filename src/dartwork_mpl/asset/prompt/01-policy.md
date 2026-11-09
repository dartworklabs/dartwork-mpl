# dartwork-mpl Policy

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

Rules in this document are split into two tiers:

- **Enforced** — there is a matching entry in
  `asset/prompt/02-anti-patterns.yaml` and the lint engine flags
  violations.
- **Recommended** — followed by all bundled templates and assumed by
  the design, but not currently checked by the lint engine. Treat
  these as guidance for human authors and AI agents both.

Critical lint gates and data/trust constraints remain binding. Supported
explicit aesthetic choices (including colormap or rotation) take priority over
aesthetic warning recommendations: explain/report warnings without silently
normalizing the user's choice. Warning/info findings are not critical gates.

## Purpose, preset and default size

What the request names wins: explicit user width/height/style, then
journal/template constraints, then prior project context. What it leaves
unnamed comes from the library, so every agent and every run draws the same
figure: the purpose picks the preset and `dm.figsize_for()` gives that
preset's canvas. Keep a selected preset (including `scientific` or `report`)
during geometry-only edits; preserve the data and other style choices. Do not
replace explicit sizes with template dimensions or a default.

| Purpose keywords (examples) | Existing preset | Canvas when no size is named |
|---|---|---|
| paper, journal, 논문 | `scientific` | `dm.figsize_for()`: one column (9 cm), two columns (17 cm) for dense data or a grid; the venue's column width wins |
| report, document, dashboard, 보고서, 문서 | `report` | `dm.figsize_for()`: 9 / 12 / 14.5 / 17 cm by data density, 4:3 |
| talk, slides, presentation, 발표 | `presentation` | `dm.figsize_for()`: 10.5 cm tall under a 16:9 slide's title; wide 11.4 cm for up to 4 x positions, 15.4 cm up to 6, 23.4 cm for more, 4+ series or a second y axis; `"compact"` 11.4 cm for two charts side by side; `dm.figsize_for("full_slide")` (25.4 × 14.29 cm) only for a whole 16:9 slide with no title |

These are defaults, not caps or journal/slide standards: any size the user, a
journal or a template names wins, through `dm.figsize`. `dm.figsize_for(kind,
n_points=, n_series=, labels=, dual_axis=, nrows=, ncols=)` picks the width from
the kind (`"barh"`, `"matrix"`, `"slide"`, ...) and the data density, given the
category names (`labels=names`) the narrowest of its widths that keeps them
flat half an em apart, and
`dm.grid_shape(n)` lays out `n` small multiples; both are provisional
(`dm.EXPERIMENTAL`). Reuse the recommender/templates for the chart type.
`presentation` is `scientific` with every point size × 2.6 (text, lines,
markers, ticks, pads): a slide chart looks like a column figure enlarged to
the slide, and every slide chart has the same text size whatever its width.
Plot text is English unless the user asks for another language; a Korean
conversation alone does not make it Korean. Korean text on the figure,
requested or from the data, takes a `-kr` preset. Edits keep the figure's language.

A requested element keeps the preset's style for every detail the request
does not name: "add a title" is `ax.set_title(text)` with the preset's title
size and weight; "add gridlines" is `ax.grid(True, axis=...)` with the
preset's grid colour and width; "20 cm wide" is `dm.figsize("20cm")` at the
default 4:3 (an edit keeps the existing height). Named details win exactly.

Details nobody named are the library's, so every agent draws the same figure:
no value labels on bars or lines unless asked; axis limits stay matplotlib's
(bars start at 0, lines keep the data margins);
bars are vertical, `ax.barh` with `dm.figsize_for("barh")` only when the
category names would overlap side by side; dates under bars go through
`dm.format_axis_dates(ax, dates)`, not rotated labels; an axis label is the
column name word for word (`margin_pct` → `Margin (%)`), also when the request
words it otherwise; only a value with no column takes the request's noun
word for word and in its order (`수출 증가율` → `Export growth rate`, "the share of
online orders" → `Share of online orders`), with no unit the data or request does not
state (a rate the data gives stays bare, no `(%)`; a share you compute and
scale by 100 says `(%)`); a bare year (2012) stays a number, not a date; a legend added, moved
or merged (a twin pair's two into one) is `dm.place_legend(ax)`, with `loc=`
only for a side the user names, not `ax.legend(...)` with `bbox_to_anchor`,
and a legend nobody asked about stays as it is unless the edit makes it
overlap other text (`LEGEND_OVERLAP` the original did not have; one it had
stays and is reported): then `dm.place_legend(ax)` on its axes,
with its own arguments, moves it (not wider spacing or a smaller font) and
the change list says so. A "look better" pass that shrinks touching value labels to
`dm.fs(-1)` also gives them `dm.fw(1)` when their call writes no weight, and
keeps the axis limits. Moving a figure to slides takes `dm.figsize_for(...)`
and multiplies pt values written in its code by 2.6, unrounded.

Ask **one short, self-contained question** only when missing information
materially affects the result, for example “Is this paper figure single- or
double-column, and what is its target width?” for a final publication figure.
Reuse context already given. For a draft, use the default, say which preset
and size you used and invite correction instead of blocking.

## Width

- Use native `plt.subplots(figsize=dm.figsize(width, aspect))` or
  `plt.figure(figsize=dm.figsize(width, aspect))`, including native GridSpec
  and nested GridSpec for row-specific panel allocations. Figure/Axes remain
  native matplotlib objects. `dm.subplots` and `dm.figure` were removed
  (lint critical: `dm-subplots-removed`).
- **Enforced.** Raw `figsize=(w, h)` tuples are forbidden — always
  go through `dm.figsize` (lint critical: `figsize-direct`).
- `width` accepts:
  - a unit-suffixed string: `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"`,
    `"24pt"`
  - a `Length` value: `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)`,
    `dm.pt(24)` (these return a `Length` instance with multi-unit
    views; `dm.cm(9) * 2` preserves the `Length` tag and round-trips
    through `parse_width`)
  - a parsed unit string via `dm.length("13cm")` (mirrors
    `dm.hex("#abc")` for colors)
  - the academic sugar constants `dm.col1` (= 9 cm) or `dm.col2`
    (= 17 cm).
- **Enforced.** Bare `int` / `float` widths are rejected (lint
  critical: `raw-width-number`) — the unit must always be explicit.
- Width and height are freely chosen physical dimensions; 17 cm is not an
  API maximum. The `oversize-width` lint warning flags literal cm widths above
  17 cm for a page-fit review. Retain explicitly requested or template-required
  dimensions; only reduce/split a figure when the intended page requires it.
- **Recommended.** For a coordinated set of page figures, a 0.5 cm grid and
  a small set of widths can improve consistency. These suggestions do not
  override requested dimensions.

## Aspect or height (the second `dm.figsize` argument)

The second argument picks the figure's height in one of five
equivalent forms; the first matching form wins:

1. **Aspect token** (str, default `"standard"`): height = width × ratio.
   Tokens listed below.
2. **Ratio string** `"W:H"` (`"16:9"`, `"4:3"`): width first, so
   height = width × H / W.
3. **Numeric ratio** (positive `int`/`float`, non-`bool`): treated as
   height / width.
4. **Unit-suffix string** (`"12cm"`, `"5in"`, `"170mm"`, `"24pt"`):
   literal height. Width and height units may differ.
5. **`Length` value** (`dm.cm(12)`, `dm.col1`, …): literal height.

Bare numeric strings (`"0.5"`) raise `ValueError` with a
"drop the quotes" hint so quoted ratios fail loudly. Pixel sizes
(`"1080px"`) raise with a note that pixels need a DPI: convert with
`dm.inch(px / dpi)` and save with the same `dpi=`.

### Aspect tokens

- Default: `"standard"` (= 3 / 4). `dm.list_aspect_tokens()` returns the
  registry as `{token: height / width}`.
- Tokens (height / width):
  - `"tall"` — 3 / 2
  - `"portrait"` — 5 / 4
  - `"square"` — 1.0
  - `"standard"` — 3 / 4
  - `"a4"` — 1 / 1.4142
  - `"wide"` — 2 / 3
  - `"golden"` — 1 / 1.618
  - `"slide"` — 9 / 16
  - `"cinema"` — 1 / 2
  - `"panoramic"` — 1 / 3
- Or pass a positive float directly. Extreme aspects (< 0.3 or > 4.0)
  trigger a `validate_figure` warning.

## Layout

- `dm.simple_layout(fig)` is the default. Call it after data is plotted.
- The default `margin=0` snaps axes content (labels, ticks, title)
  flush against the figure edges. For a uniform buffer pass
  `margin="2%"`, `dm.mm(2)`, `dm.cm(0.5)`, etc. For per-side overrides
  use `ml`, `mr`, `mt`, `mb` — each accepts the same forms as `margin`.
- `dm.auto_layout(fig)` was removed in 0.5.4 — call `simple_layout`
  directly (the legacy `padding` inches arg maps to `margin`).
- `dm.figsize_grid` computes a whole-figure size estimate from panel/gap
  inputs; it does not set GridSpec spacing or guarantee exact Axes sizes or
  cm gaps. Render and measure final bounds (see `03-recipes`).
- MCP `compose_layered_plot` supplies template source/comments and a lexical
  annotation checklist, not execution, panel allocation or spacing repair.
  #209's bounded margin/convergence correction is separate: `simple_layout`
  returns `None`, not proof of convergence or a clean validation report.
  Inspect full validation findings and actual PNG/PDF; explain infeasible
  geometry rather than silently deleting data or shrinking fonts.
- `tight_layout()` is **forbidden** (lint critical).
- For nested GridSpec, this helper updates root outer margins; it does not
  solve nested local margins. `SubFigure` is not accepted (missing
  `get_size_inches`). For exact whole-canvas allocations use native SubFigure
  containers, zero inter-container gaps and native local GridSpec margins.
  Measure container bounds, Axes data bounds and content extents separately;
  do not silently alter allocations. See the executable `03-recipes` guide.

## Color

- Prefer named palette defaults: `oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`,
  `cu.*`, `pr.*`. User-specified hex/native matplotlib colors remain valid.
  Raw hex may trigger advisory lint info (`raw-hex-color`); retain explicit colors.
- **Advisory warning.** For unspecified colormap choices, prefer perceptually
  uniform `viridis`, `magma`, `cividis`, `plasma` or `inferno`. `jet`, `hsv`,
  `gist_rainbow`, `gist_ncar`, `nipy_spectral` and `rainbow` trigger `jet-cmap`
  for risks to ordinal interpretation. Retain an explicit supported choice;
  explain/report the warning instead of silently substituting another map.
  See `dm.list_colors()` for domain-specific maps.
- For eight ordered signed `blue_orange` bins, opt in locally:
  `original8 = dm.colors("blue_orange", n=8)`;
  `centered8 = original8[:4] + original8[4:][::-1]`.
  Use a Matplotlib `ListedColormap(centered8)` with a `BoundaryNorm` and
  nine symmetric bin edges. Zero is a boundary, with no neutral bin; the
  arms retain unequal brightness. Do not register the local map or change
  existing `n` selection rules. The continuous `dc.blue_orange` map already
  has a light center. See `docs/color_system/palettes.md` for the recipe.

### Color construction and validation

- The dartwork core catalog has one construction model: OKLab L for
  construction lightness and OKLCH C/h for chroma and hue. ΔEOK arc-length
  spacing applies to the 19 chromatic family ladders and to sequential or
  closed twilight continuous paths that declare it. Discrete gray, diverging
  maps, and `hue` keep their documented topology-specific placement rules.
  These coordinates support useful perceptual regularity; they do not promise
  perfectly uniform appearance for every observer, medium, or surrounding
  context.
- Modeled relative Y is an optional **output lock**, not an authoring
  coordinate. The shipped catalog enables it where required to keep exact hex
  output, compatibility, and ordered/cyclic topology unchanged.
- A direct OKLCH rule without the Y lock is valid for a new, intentionally
  incompatible palette. Do not apply it to the current catalog unless its
  exact-output contract is explicitly retired.
- CIELAB/CIEDE2000 and CVD simulation are model-specific validation
  diagnostics only; they do not choose construction coordinates. WCAG
  contrast luminance is a separate pairwise text-contrast calculation and
  must not be confused with the catalog's modeled-relative-Y lock.

## Native customization, fonts and strokes

Presets supply defaults, not a closed property schema. Native matplotlib
artists support line width/color/custom dashes, spines, ticks, tick labels,
axis labels, grids and other valid properties; 18 templates are starters, not
chart limits. Discover properties with `type(artist)`, getters, `properties()`,
`help(type(artist))` or official docs for the installed matplotlib version.
Resolve the panel/series/artist; ask one short question only if material target
ambiguity remains. Change only requested properties. Preserve data, unrelated
style, canvas, legend and preset; do not add unsolicited palette/legend changes.
Apply the preset first, then retained overrides, then local artist edits.

- For preset-relative defaults use `dm.fs(n)`, `dm.lw(n)`, `dm.fw(n)`.
  `fs` = global `font.size` + `n` steps; `lw` = global `lines.linewidth` + `n`
  steps. A step is 1 pt, 2.6 pt under `presentation` (`dm.fs(1) - dm.fs(0)`);
  `fw` = global `font.weight` + `100*n`. Fractional offsets are accepted.
  These helpers do not read an artist's current value or a role-specific base.
- For relative-to-current edits use the target's getter plus the requested
  delta. Repeated “one more step” increments the retained current override,
  rather than resetting to `dm.fs(1)`. Axis-label-only changes edit label Text
  objects, preserving tick labels; do not change global `font.size`.
- Explicit absolute values win, including `fontsize=12` or `linewidth=1.5`.
  `fontsize-literal` / `linewidth-literal` still produce advisory warnings:
  review and report them; preserve explicit values rather than hiding warnings
  or replacing them with base defaults. The auto-fixer does not rewrite them.
- Keep true hairlines literal (`linewidth=0.3` / `0.5`); `dm.lw(-1)` can become
  zero on presets with a 1 pt base and disable the edge. `linewidth=0` disables
  a border. Custom dash lengths scale with line width by default; if exact
  physical on/off lengths are requested, use local `lines.scale_dashes=False`
  before creation and setters that rescale dashes. See scoped recipes.

## Save and display

- Prefer `dm.save_and_show(fig, "name")` for notebooks (saves +
  inline preview).
- Prefer `dm.save_formats(fig, "name", formats=("png","pdf"),
  bbox_inches=None)` for scripts (multi-format, no preview). `None` is already
  the default and preserves the requested canvas; `bbox_inches="tight"` crops
  to content and can change exported dimensions. Layout changes axes margins,
  not the canvas. DPI controls raster pixel density, not physical width/height;
  PNG dimensions quantize to whole pixels, while PDF keeps physical page size.
- **Enforced.** Direct `fig.savefig(...)` / `plt.savefig(...)`
  bypasses the dartwork save preset (lint warning: `savefig-direct`).
- Never end a figure with just `plt.show()` — the rendered artifact
  must be persisted.

## Style presets

- Call `dm.style.use(...)` (or `dm.style.stack([...])`) before building the
  figure and applying retained user overrides; a later preset reset can
  replace rcParams overrides. Local artist edits follow the preset.
- Available presets: `scientific`, `report`, `presentation`,
  `minimal`, `poster`, `web`, `dark`, plus their `-kr` Korean variants
  (`dm.style.presets` lists all of them).
- Korean plot text (requested by the user or present in the data) → `*-kr`
  variants (`scientific-kr`, `report-kr`, `presentation-kr`, …); conversation
  language alone keeps English plot text and the plain preset.
- Use `dm.style.context("preset")` when a single block needs a
  different look — it restores the previous style on exit so the
  preset does not leak into later figures.
- Never call `plt.style.use(...)`.

## Installed Python validation and handoff

Read `dm.get_agent_doc("AGENTS")`, policy/recipes with `dm.get_prompt`, then
retrieve basic/advanced template source via `importlib.resources` as shown in
`00-index` (`find_template.source_path` is repository-relative metadata).
`dm.validate_data` defaults to filtering NaN/Inf rows; preserve meaningful
blank/NaN line gaps with `allow_nan=True` plus separate shape/alignment and
infinity checks. This is distinct from MCP `validate_plot_data`.
Run `dm.lint_code(code)` and capture the full `dm.validate_figure(fig)` warning
objects, including detail and `CHECK_FAILED`; save exact source/full reports
and PNG/PDF, open the actual images, then revise to a new stem and review again.
`save_formats` returns `None` and still saves on warnings; it cannot certify
clean validation. Report retained advisories and any unavailable image review.
