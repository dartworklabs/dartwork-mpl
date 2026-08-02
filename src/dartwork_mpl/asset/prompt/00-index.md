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
| "How do I do X with dartwork-mpl" cookbook | `dartwork-mpl://guide/recipes` |
| Anti-patterns to avoid (machine-readable YAML) | `dartwork-mpl://guide/anti-patterns` |
| Migrating 0.3 code (`SW`/`MW`/`TW`/`DW`, `cm2in`, `figsize=`) | `dartwork-mpl://guide/migration` |
| List of every public dartwork-mpl name | `dartwork-mpl://api/index` |
| A specific function signature + docstring | `dartwork-mpl://api/{name}` |
| All available plot template types | `dartwork-mpl://templates/list` |
| Color name → hex code | call `get_color_value(name)` |
| Sanity-check a generated script | call `lint_dartwork_mpl_code(code)` |

## Always-true facts

- `import matplotlib.pyplot as plt` and `import dartwork_mpl as dm`.
- Apply a style first: `dm.style.use("scientific")` (or
  `dm.style.stack([...])` for a stack).
- Create figures with `plt.subplots(figsize=dm.figsize("<n>cm",
  "<aspect>"))`. `width` accepts unit strings (`"13cm"`, `"5in"`,
  `"170mm"`, `"24pt"`) or `Length` values (`dm.cm(13)`, `dm.col1`,
  `dm.col2`). Bare `int` / `float` are rejected. The second
  argument is polymorphic: an aspect token (`"square"`,
  `"portrait"`, `"standard"`, `"golden"`, `"wide"`, `"cinema"`), a
  positive float ratio, a unit-string height (`"12cm"`), or a
  `Length` height (`dm.cm(12)`).
- Use named colors: `oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`, `cu.*`,
  `pr.*`. Raw hex is allowed but discouraged.
- The `dc.*` catalog's construction space is unified around OKLab L and
  OKLCH C/h. ΔEOK arc-length spacing applies to the 19 chromatic family
  ladders and to the sequential or closed twilight continuous paths that
  declare it; discrete gray, diverging maps, and `hue` use their documented
  topology-specific placement rules. A modeled-relative-Y lock is an optional
  output constraint used to preserve shipped colors and topology; it is not a
  second authoring space. CIELAB/CIEDE2000 and CVD simulation are
  model-specific validation diagnostics, while WCAG contrast luminance is a
  separate pairwise text-contrast metric.
- **Always size fonts, line widths, and weights relative to the active
  style.** Pass `fontsize=dm.fs(n)`, `linewidth=dm.lw(n)`,
  `fontweight=dm.fw(n)` — never a literal `fontsize=12` or
  `linewidth=1.5`. `n` is an offset from the preset's base value
  (`0` keeps the base, `+1`/`-1` step up/down). `linewidth=0` is
  allowed only as the "no border" idiom. Reserve literal
  `linewidth=0.3` / `0.5` for true hairlines (separator edges, dashed
  reference lines) — `dm.lw(-1)` collapses to `0.0` on most presets and
  silently disables the edge. See `dartwork-mpl://guide/policy` for the
  authoritative rule.
- After creating a figure, call `dm.simple_layout(fig)` and save with
  `dm.save_formats(fig, "name")` or `dm.save_and_show(fig, "name")`.
- Never call `tight_layout()`, `plt.style.use()`, raw `figsize=(w, h)`
  tuples, or `dm.subplots` / `dm.figure` — those are lint criticals.

## Standard agent loop

1. Read this file.
2. Pick width and aspect from the user's intent.
3. Read the relevant template (`05-templates/{plot}.py`) and start
   from it. Each bundled template already calls
   `dm.style.use(...)` and routes fonts/line widths through
   `dm.fs` / `dm.lw` / `dm.fw` — preserve that scaffolding when you
   customize.
4. Customize the template (data, colors, labels). Keep every
   `fontsize=` / `linewidth=` / `fontweight=` expressed as
   `dm.fs(n)` / `dm.lw(n)` / `dm.fw(n)`.
5. Pass the final code through `lint_dartwork_mpl_code` and fix any
   `[CRITICAL]` issue before rendering.
6. Render, then call `dm.validate_figure(fig)`.
7. Save with `dm.save_formats` or `dm.save_and_show`.
