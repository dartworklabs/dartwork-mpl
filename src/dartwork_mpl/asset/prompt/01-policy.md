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
- **Enforced.** Keep widths at or below 17 cm — most page layouts
  break beyond that (lint warning: `oversize-width`).
- **Recommended.** Snap widths to the 0.5 cm grid (9.0, 9.5, 10.0…)
  for cross-figure consistency.
- **Recommended.** Within one project, keep the number of distinct
  widths ≤ 5; many small variations make multi-figure reports look
  ragged.

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
- `dm.auto_layout(fig)` is a deprecated alias of `simple_layout`; new
  code should call `simple_layout` directly.
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
  style's base size, or rely on style defaults. Typical offsets:
  `dm.fs(-1)` for tick / legend / annotation text, `dm.fs(0)` for
  body, `dm.fs(1)` for emphasized labels, `dm.fs(2..4)` for titles
  and section headings.
- **Enforced.** Do **not** pass `linewidth=<literal>` / `lw=<literal>`
  with an integer-part ≥ 1 (lint warning: `linewidth-literal`). Use
  `dm.lw(n)` instead — typical offsets: `dm.lw(0)` for the body line,
  `dm.lw(1)` for emphasized strokes, `dm.lw(2..)` for poster work.
- Sub-1 **hairline literals** (`linewidth=0.3` for separator edges,
  `linewidth=0.5` for dashed reference lines) are explicitly allowed
  by the lint engine *and recommended* for elements that must keep a
  small positive width regardless of preset. ``dm.lw(-1)`` is *not*
  a drop-in replacement for these — most presets set
  ``rcParams['lines.linewidth'] = 1.0``, which makes ``dm.lw(-1)``
  resolve to ``0.0`` and collapses the edge into the "no border"
  idiom (often invisibly).
- `linewidth=0` is always fine — the canonical "no border" idiom.
- Same recommendation for `dm.fw(n)` (weight). Each step is +100; use
  `dm.fw(1)` for "bold" relative to the preset, `dm.fw(-1)` for a
  lighter accent.
- **Bundled templates always call `dm.style.use(...)` first and pipe
  fonts/weights/data-line widths through `dm.fs` / `dm.fw` /
  `dm.lw`.** Edge hairlines stay as literal `0.3` so they remain
  visible across presets. Treat this split as the recommended idiom
  for new agent-authored scripts — a literal font size or line width
  pinned to a single preset will look wrong as soon as the user
  switches to `presentation` or `*-kr`, but hairline separators
  *should* stay at a fixed pixel width.

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

- **Always call `dm.style.use(...)` (or `dm.style.stack([...])`) before
  building the figure.** A figure that relies on whatever style was
  active by accident will look inconsistent across notebooks. Every
  bundled template in `05-templates/` opens with
  `dm.style.use("scientific")` for exactly this reason.
- Available presets: `scientific`, `report`, `presentation`,
  `minimal`, plus their `-kr` Korean variants.
- Korean text → `*-kr` variants (`scientific-kr`, `report-kr`,
  `presentation-kr`).
- Use `dm.style.context("preset")` when a single block needs a
  different look — it restores the previous style on exit so the
  preset does not leak into later figures.
- Never call `plt.style.use(...)`.
