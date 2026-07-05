# dartwork-mpl

[![PyPI version](https://img.shields.io/pypi/v/dartwork-mpl.svg)](https://pypi.org/project/dartwork-mpl/)
[![Python versions](https://img.shields.io/pypi/pyversions/dartwork-mpl.svg)](https://pypi.org/project/dartwork-mpl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/ci.yml/badge.svg)](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/ci.yml)
[![Docs](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/docs.yml/badge.svg)](https://dartworklabs.github.io/dartwork-mpl/)

**Publication-quality matplotlib — a thin utility layer, not a wrapper.**

`dartwork-mpl` keeps `Figure` / `Axes` 100% native and adds the parts matplotlib
makes tedious: a physical-width geometry API, curated style presets, an OKLCH-aware
color system, deterministic content-aware layout, visual validation, and a
first-class integration for AI coding assistants (an MCP server + a bundled prompt
corpus). You never learn a new plotting API — you keep writing matplotlib, just
without the friction.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")                                       # 1. curated preset
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))   # 2. physical width × aspect
ax.plot(x, y, color="oc.blue5", lw=dm.lw(0))
ax.set_xlabel("Time [s]")
dm.simple_layout(fig)                                            # 3. content-aware margins
dm.save_formats(fig, "figure", formats=("svg", "png", "pdf"))    # 4. multi-format save
```

That four-step pattern — **preset → `figsize(width, aspect)` → `simple_layout` →
`save_formats`** — is the whole workflow. No `tight_layout()`, no hand-tuned
`figsize=(w, h)` arithmetic, no `dpi=` guesswork.

<br/>

## Installation

```shell
pip install dartwork-mpl        # or:  uv add dartwork-mpl
```

Requires Python 3.10+. The core install is intentionally lean; add an extra only
when you need it:

| Extra        | Enables                                   | Pulls in              |
| ------------ | ----------------------------------------- | --------------------- |
| `[notebook]` | `dm.show()` inline SVG display in Jupyter | `ipython`             |
| `[mcp]`      | the MCP server for AI assistants          | `fastmcp`, `httpx`    |
| `[ui]`       | the interactive parameter viewer          | `fastapi`, `uvicorn`  |

```shell
pip install "dartwork-mpl[notebook]"   # or [mcp], [ui]
```

<br/>

## Highlights

- **Geometry, decoupled from inches.** `dm.figsize("13cm", "standard")` takes a
  physical width (cm / in / mm / pt, or `dm.col1` = 9 cm / `dm.col2` = 17 cm) and
  one of ten aspect tokens (`square / portrait / tall / standard / golden /
  wide / a4 / slide / cinema / panoramic`); the height follows. Bare numbers are rejected so the unit is always
  explicit.
- **Deterministic layout.** `simple_layout(fig)` measures every visible artist and
  places the GridSpec arithmetically — reproducible across machines, unlike
  `tight_layout()`'s heuristics. `margin="2%"` (or `dm.mm(2)`) adds a buffer.
- **OKLCH-aware color.** Named palettes (`oc.*` Open Color, `tw.*` Tailwind,
  `md.*`, `ad.*`, `cu.*`, `pr.*`) plus a `Color` class spanning OKLab / OKLCH /
  RGB / hex with perceptual interpolation (`cspace`) and gamut-correct mapping.
- **Curated styling.** Seven presets (`scientific`, `report`, `presentation`, …),
  each with a Korean `-kr` variant, and preset-relative scaling helpers `fs` /
  `fw` / `lw` so literals never drift when you switch themes.
- **Validation & export.** `validate_figure(fig)` flags overflow, text/legend
  overlap, tick crowding, and empty axes — invisible failures in headless agent
  pipelines. `save_formats(fig, ...)` writes SVG / PNG / PDF / EPS at once, with
  deterministic SVG/PDF/SVGZ output for unchanged figures.
- **AI-native.** A bundled [MCP](https://modelcontextprotocol.io) server exposes
  lint + auto-fix, figure validation, color lookup, and the live policy corpus to
  Claude Code / Cursor / Windsurf. No-MCP agents read the same corpus from disk.
- **Batteries included.** Material Design Icons + Font Awesome 6 fonts, ready-made
  plot templates (`plot_diverging_bar`, …), and a FastAPI viewer for live tuning.

<br/>

## Core API at a glance

```python
import dartwork_mpl as dm

# ── Geometry ──────────────────────────────────────────────────────────
dm.figsize("13cm", "wide")          # width × aspect token  → inch tuple
dm.figsize("13cm", 0.6)             # ...or a numeric ratio / "8cm" / dm.cm(8)
dm.cm(13); dm.mm(170); dm.inch(4.6); dm.pt(24)   # Length values
dm.col1; dm.col2                    # 9 cm / 17 cm academic-column sugar

# ── Styling & scaling ─────────────────────────────────────────────────
dm.style.use("scientific")          # apply a preset
dm.style.stack(["base", "font-scientific", "lang-kr"])   # compose
dm.fs(2); dm.fw(1); dm.lw(-0.3)     # preset-relative font size / weight / line width

# ── Color ─────────────────────────────────────────────────────────────
ax.plot(x, y, color="oc.blue5")     # named palettes register with matplotlib
dm.color("oc.blue5")                # parse name / "#4285F4" / "rgb(...)" / "oklch(...)"
dm.oklch(0.7, 0.15, 150); dm.rgb(66, 133, 244); dm.hex("#4285F4")
dm.cspace("#FF0000", "#0000FF", n=5, space="oklch")      # perceptual interpolation
dm.mix_colors("oc.blue5", "white", alpha=0.35)

# ── Layout & annotation ───────────────────────────────────────────────
dm.simple_layout(fig)               # deterministic content-aware margins
dm.simple_layout(fig, margin="2%", gs=gs)   # buffer + target a GridSpec
dm.label_axes(axes)                 # (a) (b) (c) panel labels
dm.arrow_axis(ax, "x", "Cost")      # Low ◄── Cost ──► High

# ── Validate, export, icons ───────────────────────────────────────────
dm.validate_figure(fig)             # overflow / overlap / tick-crowding / empty
dm.save_formats(fig, "fig", formats=("png", "svg", "pdf"), dpi=300)
mdi = dm.icon_font("mdi")           # also "fa-solid" / "fa-regular" / "fa-brands"

# ── Plot templates ────────────────────────────────────────────────────
from dartwork_mpl.templates import plot_diverging_bar
fig, ax = plot_diverging_bar(labels=["A", "B"], neg_values=[-30, -15], pos_values=[40, 55])
```

See the [usage guide](https://dartworklabs.github.io/dartwork-mpl/usage_guide/index.html)
and [API reference](https://dartworklabs.github.io/dartwork-mpl/api/index.html) for
the full surface.

<br/>

## Common pitfalls

Three patterns trip up new users (and AI assistants) more than any others. The
built-in lint engine flags all three; `dm.migrate_legacy_code` rewrites them in
place.

| Pitfall | Why it's wrong | Use instead |
|---|---|---|
| `plt.subplots(figsize=(8, 5))` (raw inch tuple) | dartwork-mpl's geometry is physical (cm/mm) and aspect-driven; raw tuples bypass the preset's typography pairing | `plt.subplots(figsize=dm.figsize("13cm", "standard"))` |
| `plt.tight_layout()` / `fig.tight_layout()` | Non-deterministic outer-margin solver; fights with simple_layout's GridSpec arithmetic | `dm.simple_layout(fig)` |
| `ax.set_title("…", fontsize=14)` (raw font literal) | Becomes wrong the moment you switch from `scientific` to `presentation` or a `*-kr` preset | `ax.set_title("…", fontsize=dm.fs(0))` (same for `dm.lw(n)`, `dm.fw(n)`) |

Full catalog: [`02-anti-patterns.yaml`](src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml).
Reachable at runtime via `dm.get_prompt("02-anti-patterns")` or
`lint_dartwork_mpl_code(code)` over MCP.

Upgrading from v4? See the [Migration Guide](docs/migration.md) for the
palette codemod and removed-name map.

<br/>

## Style presets

| Preset         | Use case                                          |
| -------------- | ------------------------------------------------- |
| `scientific`   | Compact fonts for academic papers and journals    |
| `report`       | Reports and dashboards, cleaner spines            |
| `minimal`      | Tufte-style, data-ink focus — no spines or ticks  |
| `presentation` | Large fonts for projected slides                  |
| `poster`       | Extra-large fonts and thick lines for posters     |
| `web`          | On-screen readability for docs and notebooks      |
| `dark`         | Dark backgrounds for Jupyter and dark-mode slides |

Each has a Korean `-kr` variant (`scientific-kr`, `report-kr`, …) with Korean-aware
fonts. List them with `dm.list_styles()`.

<br/>

## AI-assisted development (MCP)

dartwork-mpl ships a built-in **Model Context Protocol** server so AI coding
assistants pull the current policy guides, color palettes, lint catalog, and
helper tools straight into the chat — no copy-pasting docs. It exposes **16 tools**
(lint + auto-fix, figure validation, render, color lookup, info, chart-type
recommender, layered-plot composer, advanced-tier render), **10 resources +
4 resource templates** (the prompt corpus + 18 basic + 18 tier-2 advanced plot
templates), and **2 prompts**.

```shell
pip install "dartwork-mpl[mcp]"     # installs fastmcp + httpx; adds the dartwork-mpl-mcp script
```

Point your client at the `dartwork-mpl-mcp` console script — e.g. Claude Code
(`~/.claude.json`) or Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "dartwork-mpl": { "command": "dartwork-mpl-mcp" }
  }
}
```

Restart the client and ask it to list its MCP resources to confirm. Windsurf,
Antigravity, generic stdio setups, the full tool/resource catalog, and the
local-clone variant are covered in
[`docs/integrations/mcp_server.md`](docs/integrations/mcp_server.md).

> **No MCP?** The same corpus is bundled in the wheel and reachable from Python —
> `dm.get_agent_doc("llms-full")` (also `"AGENTS"`, `"CLAUDE"`, `"llms"`) returns
> the text, `dm.agent_doc_path(name)` its path. The repo-root
> [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) / [`llms.txt`](llms.txt)
> (per the [llmstxt.org](https://llmstxt.org) spec) are the 30-second onboarding.

<br/>

## Documentation

📚 **[Full documentation](https://dartworklabs.github.io/dartwork-mpl/)**

- [Quickstart](https://dartworklabs.github.io/dartwork-mpl/usage_guide/quickstart.html) — install, first figure, save
- [Usage guide](https://dartworklabs.github.io/dartwork-mpl/usage_guide/index.html) — width/aspect, layout, color, patterns
- [Color system](https://dartworklabs.github.io/dartwork-mpl/color_system/index.html) — palettes, OKLCH, colormaps
- [Example gallery](https://dartworklabs.github.io/dartwork-mpl/examples_gallery/index.html) — rendered, copy-pasteable
- [API reference](https://dartworklabs.github.io/dartwork-mpl/api/index.html) — every public function and class
- [Design philosophy](https://dartworklabs.github.io/dartwork-mpl/philosophy/index.html) — why thin utilities, not a wrapper

<br/>

## Project layout

```
src/dartwork_mpl/
├── units.py / scale.py        # figsize, cm/mm/inch/pt, col1/col2 · fs/fw/lw
├── style.py                   # Style class + preset management
├── colors/                    # Color (OKLab/OKLCH/RGB/hex) + named palettes
├── layout.py / annotation.py  # simple_layout, label_axes, arrow_axis
├── validate.py / lint.py      # validate_figure · lint + migrate_legacy_code
├── io.py / formatting.py      # save_formats, show · format_axis_*
├── icon.py / font.py / cmap.py / diagnostics/   # fonts, colormaps, viz helpers
├── templates/ / helpers/      # plot templates · high-level composition helpers
├── agent.py / prompt.py       # bundled LLM corpus · prompt guides
├── mcp/                       # MCP server (server / resources / tools / prompts)
├── ui/                        # interactive FastAPI viewer
└── asset/                     # bundled styles, colors, fonts, icons, prompts
```

<br/>

## Contributing & issues

Bug reports and feature requests go to the
[GitHub issue tracker](https://github.com/dartworklabs/dartwork-mpl/issues).
Released under the [MIT License](LICENSE).
