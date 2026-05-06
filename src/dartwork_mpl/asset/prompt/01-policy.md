# dartwork-mpl Policy

Rules in this document are split into two tiers:

- **Enforced** — there is a matching entry in
  `asset/prompt/02-anti-patterns.yaml` and the lint engine flags
  violations.
- **Recommended** — followed by all bundled templates and assumed by
  the design, but not currently checked by the lint engine. Treat
  these as guidance for human authors and AI agents both.

## Width

- **Enforced.** `plt.subplots(figsize=dm.figsize(width, aspect))` is
  the only legal way to size a figure. `dm.subplots` and `dm.figure`
  were removed (lint critical: `dm-subplots-removed`).
- **Enforced.** Raw `figsize=(w, h)` tuples are forbidden — always
  go through `dm.figsize` (lint critical: `figsize-direct`).
- `width` accepts:
  - a unit-suffixed string: `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"`
  - an `Inches` value: `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)`
    (these return `Inches`, a `float` subclass that `parse_width`
    treats as already-converted, so `dm.cm(9) * 2` stays in inches)
  - the academic sugar constants `dm.col1` (= 9 cm) or `dm.col2`
    (= 17 cm).
- **Enforced.** Bare `int` / `float` widths are rejected (lint
  critical: `raw-width-number`) — the unit must always be explicit.
- **Enforced.** Keep widths at or below 17 cm — most page layouts
  break beyond that (lint warning: `oversize-width`).
- **Recommended.** Snap widths to the 0.5 cm grid (9.0, 9.5, 10.0…)
  for cross-figure consistency.
- **Recommended.** Within one project, keep the number of distinct
  widths ≤ 5; many small variations make multi-figure reports look
  ragged.

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
- **Enforced.** Raw hex strings (`color="#abcdef"`) work but trigger
  a lint info — prefer named tokens (`raw-hex-color`).
- **Enforced.** For colormaps, avoid `jet` and other rainbow
  colormaps (`hsv`, `gist_rainbow`, `gist_ncar`, `nipy_spectral`,
  `rainbow`); they misrepresent ordinal data (lint warning:
  `jet-cmap`). Use perceptually uniform options: `viridis`, `magma`,
  `cividis`, `plasma`, `inferno`. dartwork-mpl also registers
  domain-specific palettes via `dm.cmap` — see
  `dm.list_colormaps()` for the current set.

## Font and weight

- **Enforced.** Do **not** pass `fontsize=<literal>` (lint warning:
  `fontsize-literal`). Use `dm.fs(n)` for an offset from the active
  style's base size, or rely on style defaults.
- **Enforced.** Do **not** pass `linewidth=<literal>` / `lw=<literal>`
  (lint warning: `linewidth-literal`). Use `dm.lw(n)` instead.
  `linewidth=0` is allowed as the canonical "no border" idiom.
- Same recommendation for `dm.fw(n)` (weight).

## Save and display

- Prefer `dm.save_and_show(fig, "name")` for notebooks (saves +
  inline preview).
- Prefer `dm.save_formats(fig, "name", formats=("png","svg"))` for
  scripts (multi-format, no preview).
- **Enforced.** Direct `fig.savefig(...)` / `plt.savefig(...)`
  bypasses the dartwork save preset (lint warning: `savefig-direct`).
- Never end a figure with just `plt.show()` — the rendered artifact
  must be persisted.

## Style presets

- Apply via `dm.style.use("scientific")` (or
  `dm.style.stack([...])` for a stack).
- Korean text → `*-kr` variants (`scientific-kr`, `report-kr`,
  `presentation-kr`).
- Never call `plt.style.use(...)`.
