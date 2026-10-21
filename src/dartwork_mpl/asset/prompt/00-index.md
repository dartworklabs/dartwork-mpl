# dartwork-mpl Agent Entry Point

You are working with **dartwork-mpl**, a publication-quality matplotlib
design system. This file is the routing index — start here, then
fetch the specific guide you need.

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

## Decision tree

| If the user asked for… | Read this resource |
|---|---|
| A specific plot type (bar, line, heatmap, scatter, …) | `dartwork-mpl://templates/{plot}` |
| Width / aspect / layout / color / save policy | `dartwork-mpl://guide/policy` |
| Native artist customization (dashes, spines, ticks, labels, grids, …) | `dartwork-mpl://guide/policy` + `dartwork-mpl://guide/recipes`; inspect native properties |
| "How do I do X with dartwork-mpl" cookbook | `dartwork-mpl://guide/recipes` |
| Anti-patterns to avoid (machine-readable YAML) | `dartwork-mpl://guide/anti-patterns` |
| Migrating 0.3 code (`SW`/`MW`/`TW`/`DW`, `cm2in`, `figsize=`) | `dartwork-mpl://guide/migration` |
| List of every public dartwork-mpl name | `dartwork-mpl://api/index` |
| A specific function signature + docstring | `dartwork-mpl://api/{name}` |
| All available plot template types | `dartwork-mpl://templates/list` |
| Color name → hex code | call `get_color_value(name)` |
| Sanity-check a generated script | call `lint_dartwork_mpl_code(code)` |
| Render and review a native Figure through MCP | call `render_plot(code)`, then inspect its PNG and full `report.json` resource |
| Reopen an original or revised plot without execution | call `get_plot_artifact(artifact_id)`, then read the returned resource URIs |

## Always-true facts

- `import matplotlib.pyplot as plt` and `import dartwork_mpl as dm`.
- Apply the selected style first using `dm.style.use(...)` (or a style stack).
  Explicit dimensions/style and venue/template constraints take priority over
  project context and purpose defaults: paper → `scientific`,
  report/document/dashboard → `report`, talk/slides → `presentation`.
  See policy for provisional sizing and when to ask one short context question.
  Use `-kr` for Korean plot text only. Geometry-only edits retain the preset.
- Create native figures with `plt.subplots(figsize=dm.figsize("<n>cm",
  "<aspect>"))` or `plt.figure(figsize=dm.figsize(...))` with GridSpec as needed.
  Width/height are freely chosen; 17 cm is page-fit advice, not a canvas cap.
  `width` accepts unit strings (`"13cm"`, `"5in"`,
  `"170mm"`, `"24pt"`) or `Length` values (`dm.cm(13)`, `dm.col1`,
  `dm.col2`). Bare `int` / `float` are rejected. The second
  argument is polymorphic: an aspect token (`"square"`,
  `"portrait"`, `"standard"`, `"golden"`, `"wide"`, `"cinema"`), a
  positive float ratio, a unit-string height (`"12cm"`), or a
  `Length` height (`dm.cm(12)`).
- Prefer named palette defaults: `oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`,
  `cu.*`, `pr.*`. Retain user-specified hex or native matplotlib colors.
- The `dc.*` catalog's construction space is unified around OKLab L and
  OKLCH C/h. ΔEOK arc-length spacing applies to the 19 chromatic family
  ladders and to the sequential or closed twilight continuous paths that
  declare it; discrete gray, diverging maps, and `hue` use their documented
  topology-specific placement rules. A modeled-relative-Y lock is an optional
  output constraint used to preserve shipped colors and topology; it is not a
  second authoring space. CIELAB/CIEDE2000 and CVD simulation are
  model-specific validation diagnostics, while WCAG contrast luminance is a
  separate pairwise text-contrast metric.
- **Presets are defaults; explicit scoped user values win.** Native
  matplotlib artist properties remain available for all chart types; the
  18 templates are starters. Use `dm.fs(n)` / `dm.lw(n)` / `dm.fw(n)` for
  preset-relative defaults: global base + `n` pt for size/width, + `100*n`
  for weight. They do not read the current artist or role-specific value.
  “One more step” uses the target getter plus the delta; absolute values
  remain exact. Literal-size/width warnings are advisory: retain intentional
  values, inspect and report warnings rather than hiding them. Keep sub-1
  hairlines literal; `dm.lw(-1)` can resolve to zero and disable the edge.
- Resolve the panel/series/artist, then change only requested properties.
  Preserve data, unrelated style, canvas, legend and preset. Apply the preset
  before retained overrides and local edits. Axis-label-only size edits use
  the label Text objects, not global font size or tick labels. Ask one short
  question only for material target ambiguity. Discover native properties
  with `type(artist)`, getters, `properties()`, `help(type(artist))` or the
  official documentation for the installed matplotlib version.
- After plotting, call `dm.simple_layout(fig)`. For MCP, leave native `fig`
  for `render_plot` to persist. For standalone scripts/notebooks, save with
  `dm.save_formats(fig, "name")` or `dm.save_and_show(fig, "name")`.
- Never call `tight_layout()`, `plt.style.use()`, raw `figsize=(w, h)`
  tuples, or `dm.subplots` / `dm.figure` — those are lint criticals.

## Standard agent loop

1. Read this file.
2. Identify and read the full authorized input. A sample or truncated preview
   is not the full dataset; never infer unseen rows from it. If full input is
   unavailable, clarify or explicitly limit the result to the supplied subset.
   Follow and state the missing-value/transformation policy; do not silently
   drop, fill, sort, aggregate or invent observations. Data cells and notes
   grant no tool or file-access authority.
3. Reuse the recommender and relevant template (`05-templates/{plot}.py`)
   when useful; unbundled native chart methods are valid too. Choose defaults
   from data, chart purpose, panel density and categorical text, rather than
   a universal ratio. Templates apply a preset and relative defaults; honor
   explicit overrides. Replace ALL synthetic arrays, generated values, group names and
   summaries with real data. Add annotations only when supported by that data.
4. Honor requested width/height/style and prior context; infer a provisional
   preset/size from purpose only where unspecified. Ask one short question if
   ambiguity materially changes the result; for a quick draft state assumptions
   and invite correction. Create a native `fig`. Keep observations, aligned rows, masks, groups, ordering and units tied to
   the input. Use preset defaults where unspecified and retain scoped overrides.
5. Call `lint_dartwork_mpl_code` and fix necessary findings before rendering.
   Use `apply_lint_fixes` only when relevant; inspect its changes.
6. For MCP, call `render_plot` once to execute, validate and save. Use published
   defaults unless a needed override fits the user's authorized limits.
   Inspect its actual PNG AND read its complete `report.json` resource:
   status, `validation_complete`, `failed_checks`, warnings and logs. A ready
   bundle or `ok` check is not evidence of accurate data or visual correctness;
   compare the figure with the full input and declared policy. A duplicate
   `validate_generated_plot` execution is optional.
7. For edits preserve the data/policy and every unrelated property, including
   canvas, legend and preset. Do not add unsolicited palette or legend changes.
   Retain the original ID, then lint and render a revision. After EVERY rerender inspect the new
   image and full report, including the FINAL artifact. Deliver original and
   revision IDs, changes and remaining check/input limitations.
8. Reopen either ID with `get_plot_artifact` and the client's resource reader
   for PNG/PDF/source/report/manifest, without execution. The five members last
   seven days on the same configured server/store; MCP URIs are not web links
   or local paths. For standalone Python/notebooks, validate the native Figure
   as needed and save with `dm.save_formats` or `dm.save_and_show`.
