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

## Purpose, preset and initial size

Use this priority: explicit user width/height/style and journal/template
constraints, then prior project context, then inferred purpose defaults.
Keep a selected preset (including `scientific` or `report`) during geometry-only
edits; preserve the data and other style choices. Do not replace explicit
sizes with template dimensions or a 17 cm suggestion.

| Purpose keywords (examples) | Existing preset | Provisional size guidance |
|---|---|---|
| paper, journal, 논문 | `scientific` | `dm.col1` (9 cm) or `dm.col2` (17 cm) are rough candidates; confirm venue/column width for final publication |
| report, document, dashboard, 보고서, 문서 | `report` | 13–17 cm is a rough starting range; fit the page/content width and panel complexity |
| talk, slides, presentation, 발표 | `presentation` | fit the slide ratio and full-slide/inset placement; a slide-sized canvas is not implied by the preset |

These are draft suggestions, not universal journal/slide standards or caps.
Choose an initial height using `dm.figsize` and the panel/label complexity.
Choose defaults from data, chart purpose, panel density and categorical text;
there is no universal ratio or numeric font size. Reuse the recommender/templates.
Use `-kr` only for Korean plot text, not merely a Korean conversation.

Ask **one short, self-contained question** only when missing information
materially affects the result. Reuse context already given. For example:
“Is this paper figure single- or double-column, and what is its target width?”;
“Is the slide 16:9 or 4:3, and is this a full-slide chart or an inset?”;
“For this report, what page/content width or preferred figure size should I use?”
Do not require a setup form for every plot or silently assume ambiguous final
publication sizing. For a quick draft, state a reasonable provisional
preset/size and invite correction instead of blocking.

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

The second argument picks the figure's height in one of four
equivalent forms; the first matching form wins:

1. **Aspect token** (str, default `"standard"`): height = width × ratio.
   Tokens listed below.
2. **Numeric ratio** (positive `int`/`float`, non-`bool`): treated as
   height / width.
3. **Unit-suffix string** (`"12cm"`, `"5in"`, `"170mm"`, `"24pt"`):
   literal height. Width and height units may differ.
4. **`Length` value** (`dm.cm(12)`, `dm.col1`, …): literal height.

Bare numeric strings (`"0.5"`) raise `ValueError` with a
"drop the quotes" hint so quoted ratios fail loudly.

### Aspect tokens

- Default: `"standard"` (= 3 / 4).
- Tokens:
  - `"square"`  — 1.0
  - `"portrait"` — 5 / 4
  - `"standard"` — 3 / 4
  - `"golden"` — 1 / 1.618
  - `"wide"` — 2 / 3
  - `"cinema"` — 1 / 2
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
  `fs` = global `font.size` + `n` pt; `lw` = global `lines.linewidth` + `n` pt;
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
  `minimal`, plus their `-kr` Korean variants.
- Korean plot text → `*-kr` variants (`scientific-kr`, `report-kr`,
  `presentation-kr`); conversation language alone does not select a variant.
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
