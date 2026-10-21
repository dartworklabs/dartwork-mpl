# dartwork-mpl — agent entry point

You are working with **dartwork-mpl**, a publication-quality matplotlib
design system. This file is the 30-second onboarding for AI coding
assistants. For human contributors, see [`README.md`](README.md).

The same content is mirrored in [`AGENTS.md`](AGENTS.md) so non-Claude
clients (Aider, Continue, Cursor `.cursorrules`, etc.) can pick it up.
A machine-readable index is in [`llms.txt`](llms.txt) and a single-file
concatenated dump in [`llms-full.txt`](llms-full.txt).

## What is dartwork-mpl

A thin utility layer on top of matplotlib that gives you a free-form
physical-width API, ten aspect tokens, curated style presets, an
OKLCH-aware color system, content-aware layout, validation, and an
MCP server for AI agent integration. It does **not** wrap matplotlib
with a new API — `Figure` / `Axes` stay native.

## First-call rules (always do these)

```python
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")                       # 1. pick a preset
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))  # 2. physical width + aspect token via dm.figsize
# ... draw on ax ...
dm.simple_layout(fig)                            # 3. deterministic content-aware margins (replaces tight_layout)
dm.save_formats(fig, "out", formats=("png", "pdf"))     # 4. multi-format save
```

- Honor explicit width/height/style and journal/template constraints first,
  then prior project context, then purpose defaults: paper/journal →
  `scientific`, report/document/dashboard → `report`, talk/slides →
  `presentation`. Start with a reasonable draft size for the panel complexity:
  paper 9/17 cm (`dm.col1`/`dm.col2`) and report 13–17 cm are suggestions,
  not standards or caps. Slide size depends on ratio and full-slide/inset use.
  Ask one short context/preferred-size question only if missing information
  materially affects the result; don't reask known context. For a quick draft,
  state a provisional preset/size and invite correction. Use `-kr` only for
  Korean plot text. Geometry-only edits preserve the selected preset/data/style.
- Width and height are free physical dimensions: for example,
  `dm.figsize("24cm", "120mm")` or `dm.figsize("10in", "5in")`.
  Native `plt.figure` + GridSpec/nested GridSpec are valid alongside
  `plt.subplots`. The 17 cm lint warning is page-fit advice, not a maximum;
  retain requested dimensions. To preserve export size, use
  `dm.save_formats(..., bbox_inches=None)` (the default); `"tight"` crops.
  DPI changes raster density, not physical canvas size.
- **`dm.figsize(width, aspect)`**: returns the inch tuple matplotlib's
  `figsize=` expects. `width` must be a unit string (`"13cm"`,
  `"5in"`, `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(13)`,
  `dm.col1`, `dm.col2`). Bare `int` / `float` are rejected.
- **Second arg accepts four forms** — pick whichever reads naturally:
  aspect token (`"wide"`), numeric ratio (`0.6`), unit-string height
  (`"12cm"`), or `Length` height (`dm.cm(12)`). Width and height
  units don't have to match — `dm.figsize("13cm", "5in")` is fine.
- **Never call**: `plt.tight_layout()`, raw `figsize=(w, h)` tuples on
  `plt.subplots` / `plt.figure`. Always wrap with `dm.figsize(...)`
  and call `dm.simple_layout(fig)` after plotting ordinary figures. For exact
  whole-canvas SubFigure containers, use native local margins instead; do not
  pass a SubFigure to this helper (missing `get_size_inches`). Nested GridSpec
  calls adjust root outer margins, not independent local regions. Measure
  container and Axes bounds separately; read `dm.get_prompt("03-recipes")` for
  executable equal, ratio, spanning/nested and 70:30 / row-specific recipes.
- **Presets supply defaults; explicit user customization wins.** Use
  native matplotlib artist properties for any chart type, including line
  colors/widths/dashes, spines, ticks, tick labels, axis labels and grids.
  The 18 templates are starters, not a limit. Choose defaults from data,
  purpose, panel density and categorical text; reuse the recommender/templates.
- For preset-relative changes use `dm.fs(n)` / `dm.lw(n)` / `dm.fw(n)`:
  `fs` adds `n` pt to global `font.size`, `lw` adds `n` pt to global
  `lines.linewidth`, and `fw` adds `100*n` weight units. These helpers do
  not read a role's or artist's current value. For “one more step,” use the
  target's getter plus the requested delta; retain explicit absolute values.
  Literal font sizes/line widths may still warn: review and report those
  advisories without replacing an explicit request or hiding the warnings.
- Resolve the requested panel/series/artist and change only its requested
  properties. Preserve data, unrelated style, canvas, legend and preset.
  Apply the preset before retained overrides and local edits. For axis-label
  changes edit label Text objects, not global `font.size` or tick labels.
  Ask one short question only if a materially ambiguous target remains.
  Prefer named palette defaults; user-specified hex and native colors work.
  Discover native properties with `type(artist)`, getters, `properties()`,
  `help(type(artist))` or official docs for the installed matplotlib version.
- **Sub-1 hairline literals stay as literals**: `linewidth=0.3` for
  separator edges, `linewidth=0.5` for dashed reference / grid lines.
  ``dm.lw(-1)`` is *not* a drop-in — it resolves to `0.0` with most
  presets and collapses the edge into the "no border" idiom (often
  invisibly). `linewidth=0` itself is fine as the explicit
  "no border" form.

## Anti-patterns (top 3)

The full SSOT lives in
[`src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`](src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml).
Run the lint engine via the MCP tool `lint_dartwork_mpl_code` (see
below) for the complete list. The most common ones AI agents trip on:

1. **`figsize=(w, h)` literal** — wrap with `dm.figsize("<n>cm", "<aspect>")`.
2. **`plt.tight_layout()`** — use `dm.simple_layout(fig)` instead.
3. **Unrequested fixed `fontsize=` / `linewidth=` literals** — prefer
   `dm.fs(n)` / `dm.lw(n)` for defaults. Literal warnings are advisory;
   preserve explicit absolute user values and report relevant warnings.

## MCP server

For Claude Code / Cursor / any MCP client, see the step-by-step setup
in [`docs/integrations/mcp_server.md`](docs/integrations/mcp_server.md).
The server exposes 19 tools (lint + auto-fix + figure validation + render + color lookup + info
+ chart-type recommender + layered-plot composer + advanced-tier render + durable artifact delivery + retained-input deletion), 10 resources +
9 resource templates (the prompt corpus + 18 basic + 18 tier-2 advanced plot templates + five artifact members), and 2 prompts. The tools you'll
use most:

- `lint_dartwork_mpl_code(code)` — anti-pattern detection.
- `validate_plot_data(plot_type, data)` — input shape checks.
- `dartwork_mpl_info()` — package version + capability summary.
- `render_plot(code)` — execute trusted plotting code once; return PNG, PDF, exact source, report and manifest.
- `get_plot_artifact(artifact_id)` — reopen that bundle without execution for seven days via MCP resources.
- `render_plot(..., revision=...)` — explicitly choose Copy of current authorized bytes or Retained fixed bytes; requires operator input policy for inputs.
- `delete_plot_inputs(artifact_id)` — revoke one retained input set; bundles and independent children remain.

Inputs are kept in the operator-selected private `storage_dir` on the server
host. Unset policy denies Copy/Retained/delete. Historical report receipts do
not prove current availability or upstream freshness; actual Retained admission
checks reuse. Clients handle per-input display and ambiguous data choices. See
the MCP guide for hashes, seven-day child copies and deletion limits.

When MCP is unavailable, the same anti-pattern catalog is reachable
through `dm.list_prompts()` + `dm.get_prompt("02-anti-patterns")`
inside Python.

## Installed Python agents (no MCP or checkout)

Read `dm.get_agent_doc("AGENTS")` and `dm.get_prompt("00-index")` first; the
index shows how to retrieve bundled basic/advanced source with
`importlib.resources` (`find_template.source_path` is repo-relative metadata).
`dm.lint_code(code)` returns source findings; `dm.validate_figure(fig)` returns
full visual findings, including `detail` and incomplete-check `CHECK_FAILED`.
`dm.validate_data` filters NaN/Inf rows by default: keep meaningful line gaps
with `allow_nan=True` plus separate shape/alignment/infinity checks. It is
not the MCP `validate_plot_data` tool. Follow the executable Python review loop
in `dm.get_prompt("03-recipes")` or [installed workflow](docs/ai/installed_python.md):
native Figure → full report → saved PNG/PDF → actual image review → separate
revision stem and handoff. `save_formats` returns `None`, saves on warnings,
and is not clean-validation evidence. Retain exact source, reports, original
artifacts and advisory warnings; report any missing image-review capability.

## Design documents and agent work

These four rules exist because a colour-system refactor stalled for weeks
behind a 13,868-line design document whose completion criteria could not be
met on any developer machine. The full post-mortem is
[ADR 0002](docs/adr/0002-separate-shipped-color-compatibility-from-oklab-authoring.md).

1. **A design document does not exceed 200 lines.** If it wants to be longer,
   the work needs splitting, not a longer document. A design nobody can read
   is not a design.
2. **Adversarial review requires an external decider.** "Reviewer A and B both
   passed" is not a stopping condition on its own — reviewers reading the same
   document can always find one more gap, so the loop diverges. Land a
   mechanical check first (a pinned digest, a golden file, a measured
   threshold), then review against it.
3. **An ADR may not release a preceding ADR's lock.** If an accepted decision
   froze something, superseding it is a separate decision that needs its own
   approval — not a clause inside the document that wants the freedom.
4. **Completion criteria must be executable in this repository's development
   environment.** A criterion that requires hardware, an OS or a tool nobody
   has is not a high standard; it is an unreachable one.

The colour freeze specifically: `tests/test_shipped_colors_hash.py` pins every
shipped colour value. Never regenerate its digests to make a failing test pass
— a failure means a shipped colour moved, which is a decision for a human, not
a test fix.

## Where to read more

| If you want… | Open |
|---|---|
| 5-minute hands-on tour | [`docs/usage_guide/quickstart.md`](docs/usage_guide/quickstart.md) |
| Width / aspect / layout deep dive | [`docs/usage_guide/layout.md`](docs/usage_guide/layout.md) |
| Color system & palettes | [`docs/color_system/colors.md`](docs/color_system/colors.md) (or the [design rationale](docs/color_system/design-rationale.md)) |
| Fonts, math & symbols | [`docs/fonts/index.md`](docs/fonts/index.md) (or the [math/symbol guide](docs/fonts/math_and_symbols.md)) |
| Saving, validation & reproducible output | [`docs/usage_guide/save_export.md`](docs/usage_guide/save_export.md) |
| 18 ready-to-use plot templates | [`docs/examples_gallery/09_ai_templates/`](docs/examples_gallery/09_ai_templates/) (rendered) or [`src/dartwork_mpl/asset/prompt/05-templates/`](src/dartwork_mpl/asset/prompt/05-templates/) (source) |
| Upgrading from v4 | [`docs/migration.md`](docs/migration.md) |
| Why this design exists | [`docs/philosophy/ai_native.md`](docs/philosophy/ai_native.md) |
| AI integration overview | [`docs/ai/index.md`](docs/ai/index.md) |
