# dartwork-mpl 0.4 Policy

Every rule below has a matching entry in
`asset/prompt/02-anti-patterns.yaml`; the lint engine enforces them.

## Width

- `dm.subplots(width=...)` is the only legal way to set a figure
  width.
- `width=` accepts:
  - a unit-suffixed string: `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"`
  - a helper call: `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)`
    (these return `Inches`, a `float` subclass that `parse_width`
    treats as already-converted)
  - a raw number: `13` (interpreted as cm — lint emits an info-level
    note suggesting an explicit unit)
  - the academic sugar constants `dm.col1` (= 9 cm) or `dm.col2`
    (= 17 cm).
- `figsize=` is **forbidden** (lint critical, removal in 0.5.0).
- The maximum width is 17 cm.
- Prefer the 0.5 cm grid (9.0, 9.5, 10.0…) for cross-figure
  consistency. Lint emits an info if you stray from it.
- Within one project, keep the number of distinct widths ≤ 5.

## Aspect (height / width)

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

- `dm.auto_layout(fig)` is the default. Call it after data is plotted.
- `dm.simple_layout(fig)` is reserved for advanced GridSpec cases
  where `auto_layout` cannot fit the bounding boxes.
- `tight_layout()` is **forbidden** (lint critical).

## Color

- Use named palettes: `oc.*` (Open Color), `tw.*` (Tailwind),
  `dc.*` (dartwork core), `md.*` (Material), `ad.*` (Ant),
  `cu.*` (Chakra), `pr.*` (Primer).
- Raw hex strings work but trigger a lint info (prefer named).
- For colormaps: `viridis`, `magma`, `cividis`, `plasma`, etc. —
  perceptually uniform recommended. Avoid `jet` and other rainbow
  colormaps. dartwork-mpl also registers domain-specific palettes
  via `dm.cmap` — see `dm.list_colormaps()` for the current set.

## Font and weight

- Do **not** pass `fontsize=` literals. Use `dm.fs(n)` for an offset
  from the active style's base size. Same for `dm.fw(n)` (weight)
  and `dm.lw(n)` (line width).

## Save and display

- Prefer `dm.save_and_show(fig, "name")` for notebooks (saves +
  inline preview).
- Prefer `dm.save_formats(fig, "name", formats=("png","svg"))` for
  scripts (multi-format, no preview).
- Never end a figure with just `plt.show()` — the rendered artifact
  must be persisted.

## Style presets

- Apply via `dm.style.use("scientific")` or pass a stack to
  `dm.subplots(style=[...])`.
- Korean text → `*-kr` variants (`scientific-kr`, `report-kr`,
  `presentation-kr`).
- Never call `plt.style.use(...)`.
