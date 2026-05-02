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
physical-width API, six aspect tokens, curated style presets, an
OKLCH-aware color system, content-aware layout, validation, and an
MCP server for AI agent integration. It does **not** wrap matplotlib
with a new API — `Figure` / `Axes` stay native.

## First-call rules (always do these)

```python
import dartwork_mpl as dm

dm.style.use("scientific")                       # 1. pick a preset
fig, ax = dm.subplots(width="13cm", aspect="standard")  # 2. physical width + aspect token
# ... draw on ax ...
dm.auto_layout(fig)                              # 3. content-aware margins (replaces tight_layout)
dm.save_formats(fig, "out", formats=("png", "pdf"))     # 4. multi-format save
```

- **Width unit**: must be a string with `cm` / `mm` / `in` (`"13cm"`,
  `"5in"`). Bare numbers / floats are rejected.
- **Aspect tokens**: one of `square / portrait / standard / golden /
  wide / cinema`. Numeric ratios (e.g. `0.66`) are also accepted.
- **Never call**: `plt.figure(figsize=...)`, `plt.tight_layout()`,
  `plt.subplots()` directly. Use `dm.subplots(...)` and
  `dm.auto_layout(...)`.

## Anti-patterns (top 3)

The full SSOT lives in
[`src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`](src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml).
Run the lint engine via the MCP tool `lint_dartwork_mpl_code` (see
below) for the complete list. The most common ones AI agents trip on:

1. **`figsize=(...)` literal** — use `width=...` + `aspect=...` instead.
2. **`plt.tight_layout()`** — use `dm.auto_layout(fig)` instead.
3. **0.3-era width tokens** (`dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`,
   `dm.FS_*`, `dm.WIDTHS`) — removed in 0.4.1+; use `dm.col1` /
   `dm.col2` or `dm.subplots(width="9cm", ...)`.

## MCP server

For Claude Code / Cursor / any MCP client, see the step-by-step setup
in [`docs/integrations/mcp_server.md`](docs/integrations/mcp_server.md).
The server exposes 7 tools (lint, validate, color lookup, info) and
12 resources (the prompt corpus + 18 plot templates). The tools you'll
use most:

- `lint_dartwork_mpl_code(code)` — anti-pattern detection.
- `validate_plot_data(plot_type, data)` — input shape checks.
- `dartwork_mpl_info()` — package version + capability summary.

When MCP is unavailable, the same anti-pattern catalog is reachable
through `dm.list_prompts()` + `dm.get_prompt("02-anti-patterns")`
inside Python.

## Migrating from 0.3.x

dartwork-mpl 0.4.1+ removed the deprecated 0.3 names (`dm.SW`,
`dm.FS_*`, `dm.cm2in`, `dm.agent_utils`, `dm.xplot`, the `figsize=`/
`dpi=` arguments on `dm.subplots`/`dm.figure`). Each old access path
now raises `AttributeError` / `ModuleNotFoundError` / `TypeError`
with a message naming the new API. Full mapping table:
[`docs/migration.md`](docs/migration.md).

## Where to read more

| If you want… | Open |
|---|---|
| 5-minute hands-on tour | [`docs/usage_guide/quickstart.md`](docs/usage_guide/quickstart.md) |
| Width / aspect / layout deep dive | [`docs/usage_guide/layout.md`](docs/usage_guide/layout.md) |
| Color system & palettes | [`docs/color_system/index.md`](docs/color_system/index.md) |
| 18 ready-to-use plot templates | [`docs/examples_gallery/09_ai_templates/`](docs/examples_gallery/09_ai_templates/) (rendered) or [`src/dartwork_mpl/asset/prompt/05-templates/`](src/dartwork_mpl/asset/prompt/05-templates/) (source) |
| Why this design exists | [`docs/philosophy/ai_native.md`](docs/philosophy/ai_native.md) |
| AI integration overview | [`docs/integrations/index.md`](docs/integrations/index.md) |
