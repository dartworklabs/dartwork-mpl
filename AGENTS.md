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
  and call `dm.simple_layout(fig)` after plotting.
- **Always size fonts, data-line widths, and weights relative to the
  active preset**: `fontsize=dm.fs(n)`, `linewidth=dm.lw(n)`,
  `fontweight=dm.fw(n)`. Each is an integer offset from the preset's
  base value (`0` = base, `+1` / `-1` = step up/down). Literals like
  `fontsize=12` or `linewidth=1.5` are lint-warning anti-patterns —
  they look wrong as soon as the user swaps to `presentation` or a
  `*-kr` preset.
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
3. **Raw `fontsize=` / `linewidth=` literals** — use `dm.fs(n)` / `dm.lw(n)` so
   they track the active preset.

## MCP server

For Claude Code / Cursor / any MCP client, see the step-by-step setup
in [`docs/integrations/mcp_server.md`](docs/integrations/mcp_server.md).
The server exposes 16 tools (lint + auto-fix + figure validation + render + color lookup + info
+ chart-type recommender + layered-plot composer + advanced-tier render), 10 resources +
4 resource templates (the prompt corpus + 18 basic + 18 tier-2 advanced plot templates), and 2 prompts. The tools you'll
use most:

- `lint_dartwork_mpl_code(code)` — anti-pattern detection.
- `validate_plot_data(plot_type, data)` — input shape checks.
- `dartwork_mpl_info()` — package version + capability summary.

When MCP is unavailable, the same anti-pattern catalog is reachable
through `dm.list_prompts()` + `dm.get_prompt("02-anti-patterns")`
inside Python.

## Where to read more

| If you want… | Open |
|---|---|
| 5-minute hands-on tour | [`docs/usage_guide/quickstart.md`](docs/usage_guide/quickstart.md) |
| Width / aspect / layout deep dive | [`docs/usage_guide/layout.md`](docs/usage_guide/layout.md) |
| Color system & palettes | [`docs/color_system/colors.md`](docs/color_system/colors.md) (or the [design rationale](docs/color_system/design.md)) |
| Fonts, math & symbols | [`docs/fonts/index.md`](docs/fonts/index.md) (or the [math/symbol guide](docs/fonts/math_and_symbols.md)) |
| Saving, validation & reproducible output | [`docs/usage_guide/save_export.md`](docs/usage_guide/save_export.md) |
| 18 ready-to-use plot templates | [`docs/examples_gallery/09_ai_templates/`](docs/examples_gallery/09_ai_templates/) (rendered) or [`src/dartwork_mpl/asset/prompt/05-templates/`](src/dartwork_mpl/asset/prompt/05-templates/) (source) |
| Upgrading from v4 | [`docs/migration.md`](docs/migration.md) |
| Why this design exists | [`docs/philosophy/ai_native.md`](docs/philosophy/ai_native.md) |
| AI integration overview | [`docs/ai/index.md`](docs/ai/index.md) |
