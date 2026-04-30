# dartwork-mpl

[![PyPI version](https://img.shields.io/pypi/v/dartwork-mpl.svg)](https://pypi.org/project/dartwork-mpl/)
[![Python versions](https://img.shields.io/pypi/pyversions/dartwork-mpl.svg)](https://pypi.org/project/dartwork-mpl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/ci.yml/badge.svg)](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/ci.yml)
[![Docs](https://github.com/dartworklabs/dartwork-mpl/actions/workflows/docs.yml/badge.svg)](https://dartworklabs.github.io/dartwork-mpl/)

Enhanced matplotlib styling, color management, and utility library engineered by dartwork.

`dartwork-mpl` is a utility collection designed to elevate matplotlib visuals to publication-level elegance. Instead of wrapping matplotlib with a new API layer, it provides **thin utilities** that enhance matplotlib's native capabilities while keeping you in full control.

<br/>

## Features

- **Style Presets**: Apply curated themes (`scientific`, `report`, `presentation`) with one call.
- **Width × Aspect Geometry**: `dm.subplots(width="13cm", aspect="standard")` — pick a physical width (cm/in/mm) and one of six aspect tokens (`square / portrait / standard / golden / wide / cinema`); height is derived. No more `figsize` math.
- **Advanced Color System**: Named color palettes (`oc.*`, `tw.*`, `md.*`, `ad.*`, `cu.*`, `pr.*`) plus a `Color` class supporting OKLab / OKLCH / RGB / hex color spaces with perceptual interpolation via `cspace()`.
- **Smart Layout**: `auto_layout(fig)` is the default content-aware margin pass; `simple_layout(fig, gs=gs)` is the L-BFGS-B optimizer for advanced GridSpec cases. Both replace `tight_layout()`.
- **Scaling Helpers**: Relative font size (`fs`), font weight (`fw`), and line width (`lw`) that respect the active style preset.
- **Icon Fonts**: Built-in Material Design Icons (7,448+) and Font Awesome 6.
- **Visual Validation**: Automatic detection of overflow, text overlap, legend overflow, tick crowding, and empty axes via `validate_figure()`.
- **Extended Plots**: Ready-to-use plot templates like `plot_diverging_bar()`.
- **Interactive Viewer**: FastAPI-powered web UI (`dartwork_mpl.ui`) for real-time parameter tuning.
- **Multi-format Export**: Save figures in SVG, PNG, PDF, and EPS simultaneously.
- **Prompt System**: Bundled prompt guides for AI coding assistants, with `get_prompt()` and `copy_prompt()`.
- **MCP Server**: AI coding assistant integration via Model Context Protocol (12 resources + 3 resource templates / 7 tools / 2 prompts).
- **LLM Integration**: Install usage guides to `.claude/` and `.cursor/` with `install_llm_txt()`.

<br/>

## Getting Started

### Installation

#### Using uv (Recommended)

```shell
# Add to your project
uv add git+https://github.com/dartworklabs/dartwork-mpl

# Or install directly
uv pip install git+https://github.com/dartworklabs/dartwork-mpl
```

#### Using pip

```shell
pip install git+https://github.com/dartworklabs/dartwork-mpl
```

### Quick Start

```python
import dartwork_mpl as dm

dm.style.use('scientific')

# Pick the physical width (cm/in/mm) and an aspect token. height
# follows from aspect, so you never hand-tune figsize.
fig, ax = dm.subplots(width='13cm', aspect='standard')
ax.plot(x, y, color='oc.blue5', lw=dm.lw(0))
ax.set_xlabel('Time [s]')

dm.auto_layout(fig)
dm.save_formats(fig, 'output/figure', formats=('svg', 'png'))
```

`width=` accepts unit-suffixed strings (`"13cm"`, `"6.7in"`, `"170mm"`),
helper calls (`dm.cm(11.3)`, `dm.inch(4.6)`), or a raw number (cm).
The academic-column shortcuts `dm.col1` (9 cm) and `dm.col2` (17 cm)
are also available. `aspect=` is one of `square / portrait / standard /
golden / wide / cinema`, or any positive float.

<br/>

## Core Modules

### Style Management

Ready-to-use presets with `style.use()`, or stack individual styles for fine-grained control with `style.stack()`.

```python
dm.style.use('scientific')                     # apply preset
dm.style.stack(['base', 'font-scientific', 'lang-kr'])  # stack custom
dm.list_styles()                               # list available .mplstyle files
dm.load_style_dict('font-presentation')        # inspect style params
```

### Color System

#### Named Colors

Importing `dartwork_mpl` registers palettes with `oc.*`, `tw.*`, `md.*`, `ad.*`, `cu.*`, `pr.*` prefixes:

```python
ax.plot(x, y, color='oc.blue5')       # Open Color
ax.bar(x, y, color='tw.emerald500')   # Tailwind CSS
lighter = dm.mix_colors('oc.blue5', 'white', alpha=0.35)
muted = dm.pseudo_alpha('oc.blue7', alpha=0.6)
```

#### Color Class

The `Color` class provides perceptually uniform color manipulation across OKLab, OKLCH, RGB, and hex:

```python
# Create from any color space
color = dm.oklch(0.7, 0.15, 150)      # L, C, h (degrees)
color = dm.rgb(66, 133, 244)          # auto-detects 0-255 range
color = dm.hex('#4285F4')
color = dm.named('oc.blue5')

# Read/write via views (mutable references)
color.oklch.C *= 1.2                  # boost chroma
r, g, b = color.rgb                   # unpack RGB

# Perceptual interpolation
palette = dm.cspace('#FF0000', '#0000FF', n=5, space='oklch')
```

### Layout & Annotation

```python
dm.auto_layout(fig)                     # default content-aware margin pass (0.4+)
dm.simple_layout(fig, gs=gs)            # L-BFGS-B optimizer for advanced GridSpec cases
dm.label_axes(axes)                     # add (a), (b), (c) panel labels
dm.arrow_axis(ax, 'x', 'Cost')         # Low ◄── Cost ──► High
dm.set_decimal(ax, xn=2, yn=1)         # format tick decimals
offset = dm.make_offset(4, -4, fig)    # point-based translation
```

### Scaling Helpers

```python
dm.fs(2)     # base font size + 2pt
dm.fw(1)     # base font weight + 100
dm.lw(-0.3)  # base line width - 0.3
```

### Width Helpers

```python
dm.cm(13)        # 13 cm (returned as Inches; safe to pass to width=)
dm.inch(4.6)     # 4.6 in
dm.mm(170)       # 170 mm
dm.col1          # 9 cm  — academic single-column sugar
dm.col2          # 17 cm — academic two-column sugar
```

> **Migrating from 0.3?** `dm.SW / MW / TW / DW`, `FS_*`, `cm2in`,
> `agent_utils`, and `xplot` are deprecated and emit a lint warning.
> Replace `figsize=(dm.cm2in(13), dm.cm2in(9.75))` with
> `dm.subplots(width="13cm", aspect="standard")`.

### Visual Validation

Automatic detection of rendering issues invisible in stdout-only environments (e.g., AI agent pipelines):

```python
warnings = dm.validate_figure(fig)
# Checks: overflow, overlap, legend_overflow, tick_crowding, empty_axes
# Integrated into save_formats() by default
```

### Icon Font System

```python
mdi = dm.icon_font('mdi')              # Material Design Icons
fa  = dm.icon_font('fa-solid')         # Font Awesome 6 Solid
ax.text(0.5, 0.5, "\U000F050F", fontproperties=mdi, fontsize=20)
dm.list_icon_fonts()                   # ['fa-brands', 'fa-regular', 'fa-solid', 'mdi']
```

### File I/O & Prompts

```python
dm.save_formats(fig, 'output/fig', formats=('png', 'svg', 'pdf'), dpi=300)
dm.save_and_show(fig, size=720)        # save + inline preview

# Prompt guides for AI assistants
dm.list_prompts()                      # available guides
dm.get_prompt('00-index')              # read the entry-point index (0.4 SSOT)
dm.copy_prompt('01-policy', '.cursor/rules/')
```

### Extended Plots (templates)

Ready-to-use specialized visualization templates:

```python
from dartwork_mpl.templates import plot_diverging_bar

fig, ax = plot_diverging_bar(
    categories=['A', 'B', 'C'],
    negatives=[-30, -15, -25],
    positives=[40, 55, 35],
)
```

### Interactive Viewer (UI)

FastAPI-powered web UI for real-time parameter tuning:

```python
from dartwork_mpl.ui import ParamModel, run
from pydantic import Field

class Params(ParamModel):
    n: int = Field(default=100, ge=10, le=1000)
    alpha: float = Field(default=0.5, ge=0, le=1)

def my_plot(params: Params):
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.scatter(range(params.n), np.random.randn(params.n), alpha=params.alpha)
    return fig

run(my_plot)  # opens browser at localhost:8501
```

### LLM Integration

```python
dm.install_llm_txt()      # install usage guides to .claude/ and .cursor/
dm.uninstall_llm_txt()    # remove installed guides
```

<br/>

## Available Presets

| Preset         | Description                                       |
| -------------- | ------------------------------------------------- |
| `scientific`   | Compact fonts for academic papers and journals    |
| `report`       | Reports and dashboards, cleaner spines            |
| `minimal`      | Tufte-style, data-ink focus — no spines or ticks  |
| `presentation` | Large fonts for projected slides                  |
| `poster`       | Extra-large fonts and thick lines for posters     |
| `web`          | On-screen readability for docs and notebooks      |
| `dark`         | Dark backgrounds for Jupyter and dark-mode slides |

All presets have a `-kr` Korean variant (e.g., `scientific-kr`, `report-kr`).

<br/>

## Documentation

📚 **[Full Documentation](https://dartworklabs.github.io/dartwork-mpl/)** — Sphinx docs with:

- **[Installation](https://dartworklabs.github.io/dartwork-mpl/installation/index.html)** — Setup guide
- **[Design Philosophy](https://dartworklabs.github.io/dartwork-mpl/philosophy/index.html)** — Why thin utilities, not wrappers
- **[Usage Guide](https://dartworklabs.github.io/dartwork-mpl/usage_guide/index.html)** — Workflows and patterns
- **[Color System](https://dartworklabs.github.io/dartwork-mpl/color_system/index.html)** — Colors and colormaps reference
- **[API Reference](https://dartworklabs.github.io/dartwork-mpl/api/index.html)** — Function-level docs
- **[Example Gallery](https://dartworklabs.github.io/dartwork-mpl/examples_gallery/index.html)** — Interactive examples

<br/>

## AI-Assisted Development

dartwork-mpl provides an **MCP (Model Context Protocol) server** that enables AI coding assistants to automatically access documentation and guidelines.

### MCP Setup

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/dartwork-mpl",
        "dartwork-mpl-mcp"
      ]
    }
  }
}
```

> **Note:** Replace `/path/to/dartwork-mpl` with the actual path to your local clone.
> Install MCP dependencies with `uv pip install -e ".[mcp]"`.

Supported clients: **Claude Code**, **Cursor**, **Windsurf**, **Antigravity (Gemini)**.
For detailed setup per client, see the [MCP Server docs](https://dartworklabs.github.io/dartwork-mpl/integrations/mcp_server.html).

<br/>

## Project Structure

```
src/dartwork_mpl/
├── __init__.py             # Public API exports + lazy 0.3 alias shim
├── py.typed                # PEP 561 type marker
├── figure.py               # subplots(), figure() with width/aspect API
├── units.py                # cm/inch/mm, col1/col2, parse_width/parse_aspect
├── style.py                # Style class + preset management
├── color/                  # Color class (OKLab/OKLCH/RGB/hex) + palettes
├── layout.py               # auto_layout(), simple_layout(), label_axes()
├── annotation.py           # arrow_axis(), label_axes()
├── scale.py                # fs(), fw(), lw()
├── spines.py               # hide_spines(), add_grid(), minimal_axes()
├── formatting.py           # format_axis_*(), rotate_tick_labels()
├── io.py                   # save_formats(), save_and_show()
├── prompt.py               # get_prompt(), copy_prompt(), list_prompts()
├── validate.py             # validate_figure() — visual checks
├── validate_enhanced.py    # validate_with_fixes() — auto-fix helpers
├── lint.py                 # lint() against the anti-pattern catalog
├── diagnostics.py          # plot_colormaps/plot_colors/plot_fonts
├── explore.py              # list_palettes/list_colormaps/show_palette
├── icon.py                 # Icon font system (MDI, Font Awesome)
├── font.py                 # Font registration (lazy, locked)
├── cmap.py                 # Custom colormap registration (lazy, locked)
├── helpers/                # Stable helper utilities (data, labels, …)
├── templates/              # Extended plot templates (plot_diverging_bar)
├── install.py              # LLM integration installer
├── cli.py                  # console-script entry (dartwork-mpl-mcp)
├── util.py                 # Legacy re-exports (deprecated cm2in, etc.)
├── constant.py             # Deprecated 0.3 width constants (SW/MW/TW/DW)
├── ui/                     # Interactive FastAPI viewer
├── mcp/                    # MCP server for AI assistants
│   ├── server.py           #   FastMCP instance + wiring
│   ├── resources.py        #   12 resources + 3 templates
│   ├── tools.py            #   7 tools (color, linting, validation, info)
│   └── prompts.py          #   2 prompts (create_plot, style_review)
└── asset/                  # Bundled styles, colors, fonts, icons, prompts
```

<br/>

## Reporting Issues

Encountered a bug or have a feature request? Please open an issue through our [GitHub issue tracker](https://github.com/dartworklabs/dartwork-mpl/issues).
