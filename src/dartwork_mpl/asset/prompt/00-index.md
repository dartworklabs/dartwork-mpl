# dartwork-mpl Agent Entry Point

You are working with **dartwork-mpl**, a publication-quality matplotlib
design system. This file is the routing index — start here, then
fetch the specific guide you need.

## Decision tree

| If the user asked for… | Read this resource |
|---|---|
| A specific plot type (bar, line, heatmap, scatter, …) | `dartwork-mpl://templates/{plot}` |
| Width / aspect / layout / color / save policy | `dartwork-mpl://guide/policy` |
| "How do I do X with dartwork-mpl" cookbook | `dartwork-mpl://guide/recipes` |
| Anti-patterns to avoid (machine-readable YAML) | `dartwork-mpl://guide/anti-patterns` |
| List of every public dartwork-mpl name | `dartwork-mpl://api/index` |
| A specific function signature + docstring | `dartwork-mpl://api/{name}` |
| All available plot template types | `dartwork-mpl://templates/list` |
| Color name → hex code | call `get_color_value(name)` |
| Sanity-check a generated script | call `lint_dartwork_mpl_code(code)` |

## Always-true facts

- `import dartwork_mpl as dm` is the only import path you need.
- Use `dm.subplots(width=..., aspect=...)` to create figures.
  `width` is free-form: `"13cm"`, `"6.7in"`, `dm.cm(11.3)`, or a raw
  number (interpreted as cm). `aspect` is one of `square`, `portrait`,
  `standard`, `golden`, `wide`, `cinema`, or a positive float.
- Use named colors: `oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`, `cu.*`,
  `pr.*`. Raw hex is allowed but discouraged.
- After creating a figure, call `dm.auto_layout(fig)` and save with
  `dm.save_formats(fig, "name")` or `dm.save_and_show(fig, "name")`.
- Never call `tight_layout()`, `plt.style.use()`, or set `figsize=`
  / `dpi=` directly — those are lint criticals.

## Standard agent loop

1. Read this file.
2. Pick width and aspect from the user's intent.
3. Read the relevant template (`05-templates/{plot}.py`) and start
   from it.
4. Customize the template (data, colors, labels).
5. Pass the final code through `lint_dartwork_mpl_code` and fix any
   `[CRITICAL]` issue before rendering.
6. Render, then call `dm.validate_figure(fig)`.
7. Save with `dm.save_formats` or `dm.save_and_show`.
