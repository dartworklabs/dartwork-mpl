# Usage Guide

dartwork-mpl bundles stylistic presets, curated colors/colormaps, and layout/font helpers so you get **predictable results** fast. The snippets below keep only the core code—check the Examples Gallery if you need to see the rendered figures.

```{toctree}
:maxdepth: 1
:titlesonly:
:hidden:

AI-Assisted Development <ai_assisted>
```

## Quick start

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")  # preset keys: see API › Style Management
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)
x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="oc.blue5", label="signal")
ax.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
dm.simple_layout(fig)           # API › Layout Utilities
dm.save_and_show(fig, size=720) # API › File I/O
```

- `style.use` configures palette, fonts, and line weights in one shot (API › Style Management)
- `cm2in` and `fs` keep figures to scale and fonts relative to the active preset (API › Font Utilities)
- `simple_layout` and `save_and_show` handle margin cleanup plus preview/export (API › Layout Utilities, File I/O)

## Styles and presets

```python
import dartwork_mpl as dm

dm.style.use("scientific")             # papers/technical (recommended)
dm.style.use("presentation")           # slides/reports
dm.style.use("investment")             # finance decks
dm.style.use("scientific-kr")          # includes KR fonts
dm.style.stack(["base", "font-modern"])  # stack multiple styles (advanced)

available_styles = dm.list_styles()
style_dict = dm.load_style_dict("font-presentation")
```

- Style files: `asset/mplstyle/*.mplstyle`
- Preset definitions: `asset/mplstyle/presets.json`
- See **API › Style Management** for every helper and argument

## Colors and colormaps

### Named colors

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use("presentation")

fig, ax = plt.subplots(figsize=(dm.cm2in(8), dm.cm2in(5)), dpi=300)
ax.plot([0, 1, 2], [1, 2, 1.5], marker="o", color="oc.green5", label="oc.*")
ax.plot([0, 1, 2], [1.2, 1.6, 2.1], marker="s", color="tw.blue500", label="Tailwind")
highlight = dm.mix_colors("md.orange600", "white", alpha=0.45)  # API › Color Utilities
ax.fill_between([0, 1, 2], 0.9, 1.3, color=highlight, label="Mixed shade")
muted_line = dm.pseudo_alpha("pr.blue5", alpha=0.65, background="white")
ax.plot([0, 1, 2], [0.8, 1.1, 1.4], color=muted_line, label="Pseudo alpha")
ax.legend(fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

### Color class

The `Color` class provides perceptually uniform color manipulation across OKLab, OKLCH, RGB, and hex color spaces:

```python
import dartwork_mpl as dm

# Create colors from any color space
color = dm.oklch(0.7, 0.15, 150)       # OKLCH (L, C, h°)
color = dm.rgb(66, 133, 244)           # auto-detects 0-255 range
color = dm.hex('#4285F4')              # hex string
color = dm.named('oc.blue5')           # matplotlib color name

# Read/write via views (mutable references to internal state)
color.oklch.C *= 1.2                   # boost chroma in-place
L, C, h = color.oklch                  # unpack OKLCH
r, g, b = color.rgb                    # unpack RGB

# Convert to any representation
print(color.to_hex())                  # '#...'
print(color.to_rgb())                  # (r, g, b)
print(color.to_oklch())               # (L, C, h)

# Copy to avoid mutation
brighter = color.copy()
brighter.oklab.L += 0.1
```

### Color interpolation

```python
# Perceptual interpolation between colors
palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
for i, c in enumerate(palette):
    ax.bar(i, 1, color=c.to_hex())

# Also supports 'oklab' and 'rgb' spaces
gradient = dm.cspace(dm.named('oc.red5'), dm.named('oc.blue5'), n=10)
```

### Colormaps

```python
# Check colormap name/category (API › Color Utilities)
import matplotlib.pyplot as plt
import dartwork_mpl as dm
cmap = plt.colormaps["dm.mint"]
print(cmap.name, dm.classify_colormap(cmap))
```

- Color sources: `asset/color/*.txt` + Tailwind/Material/Ant/Chakra/Primer/opencolor JSON
- Palette/colormap previews: `images/colors_*.png`, `images/colormaps_*.png`
- Diagnostic helpers live in **API › Color Utilities** and **Visualization Tools**

## Layout and annotations

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np
dm.style.use("scientific")

fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
gs = fig.add_gridspec(2, 2, left=0.08, right=0.98, top=0.9, bottom=0.12, hspace=0.35, wspace=0.25)
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
for ax in axes:
    ax.plot(np.linspace(0, 1, 40), np.random.rand(40), color="oc.blue6", lw=0.8)

# Panel labels (a, b, c, d)
dm.label_axes(axes)

# Decimal formatting
dm.set_decimal(axes[0], xn=2, yn=1)

# Layout optimization
dm.simple_layout(fig, gs=gs, margins=(0.05, 0.08, 0.06, 0.08))
```

- `simple_layout(fig, gs=gs)` respects your GridSpec margins (API › Layout Utilities)
- `label_axes(axes)` adds standardized panel labels with auto-positioning
- `arrow_axis(ax, 'x', 'Cost')` creates `Low ◄── Cost ──► High` annotations
- `make_offset` gives consistent point-based text offsets
- `set_decimal(ax, xn, yn)` formats tick labels neatly
- `get_bounding_box` merges multiple axes bounds

## Typography

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use("scientific-kr")  # English/Korean fonts set together

fig, ax = plt.subplots(figsize=(dm.cm2in(10), dm.cm2in(6)), dpi=300)
ax.plot([0, 1, 2], [0, 1, 0.4], color="oc.green6", lw=dm.lw(0.5))
ax.set_title("Experiment result", fontsize=dm.fs(2), fontweight=dm.fw(1))
ax.set_xlabel("Time", fontsize=dm.fs(0))
ax.set_ylabel("Response", fontsize=dm.fs(0))
dm.simple_layout(fig)

# Preview bundled fonts before exporting (API › Visualization Tools / Font Utilities)
dm.plot_fonts(ncols=4, font_size=12)
```

- `fs(delta)`: font size relative to the active preset
- `fw(delta)`: weight relative to the preset default
- `lw(delta)`: line width relative to `lines.linewidth`
- Fonts: `asset/font/*` (auto-registered on import)
- API details: **Font Utilities** and **Visualization Tools**

## Save and preview

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np
dm.style.use("investment")

fig, ax = plt.subplots(figsize=(dm.cm2in(11), dm.cm2in(7)), dpi=300)
ax.plot(np.arange(50), np.cumsum(np.random.randn(50)) + 20, color="oc.blue6")
dm.simple_layout(fig)

dm.save_formats(
    fig,
    "output/forecast",
    formats=("png", "svg", "pdf"),
    dpi=300,
    bbox_inches="tight",
    validate=True,   # runs validate_figure() before saving
)
dm.save_and_show(fig, size=720)  # preview + plt.show()
dm.show("output/forecast.svg", size=540)
```

- `save_formats` writes multiple formats in one call, with optional visual validation
- `save_and_show` emits a small preview (PNG/SVG) and shows the figure
- `show` reuses an existing SVG for notebooks or reports
- Argument details live in **API › File I/O**

## Visual validation

Detect common rendering issues automatically — especially useful in
AI agent pipelines where visual inspection is not available:

```python
import dartwork_mpl as dm

# Run all checks manually
warnings = dm.validate_figure(fig)
for w in warnings:
    print(w)

# Run specific checks only
warnings = dm.validate_figure(fig, checks=('overflow', 'tick_crowding'))

# Automatically called by save_formats() (validate=True by default)
```

Checks include: overflow detection, text overlap, legend overflow,
tick crowding, and empty axes. See **API › Visual Validation** for details.

## Extended plots

dartwork-mpl provides ready-to-use plot templates in `dartwork_mpl.xplot`:

```python
from dartwork_mpl.xplot import plot_diverging_bar

fig, ax = plot_diverging_bar(
    categories=['Revenue', 'Costs', 'Profit'],
    negatives=[-30, -55, -10],
    positives=[60, 20, 45],
    neg_label='Decrease',
    pos_label='Increase',
)
```

See **API › Extended Plots** for the full parameter list.

## Interactive viewer

For rapid parameter exploration, use the FastAPI-powered interactive viewer:

```python
from dartwork_mpl.ui import ParamModel, run
from pydantic import Field

class Params(ParamModel):
    n: int = Field(default=100, ge=10, le=1000)
    alpha: float = Field(default=0.5, ge=0, le=1)

def scatter(params: Params):
    fig, ax = plt.subplots()
    ax.scatter(range(params.n), np.random.randn(params.n), alpha=params.alpha)
    return fig

run(scatter)  # opens browser at http://127.0.0.1:8501
```

Install the optional `ui` extra: `uv add "dartwork-mpl[ui]"`.
See **API › Interactive Viewer** for details.

## Prompt system

Bundled prompt guides help AI coding assistants produce better
dartwork-mpl code:

```python
import dartwork_mpl as dm

dm.list_prompts()                        # available guides
content = dm.get_prompt('layout-guide')  # read guide content
dm.copy_prompt('layout-guide', '.cursor/rules/')  # copy to IDE folder
```

## Where things live

- Styles: `asset/mplstyle/*.mplstyle`, presets: `asset/mplstyle/presets.json`
- Colors/colormaps: `asset/color/*.txt`
- Fonts: `asset/font/*` (loaded by `dartwork_mpl.font`)
- Icons: `asset/icon/*` (loaded by `dartwork_mpl.icon`)
- Prompts: `asset/prompt/*.md`
- Utilities: `simple_layout`, `cm2in`, `make_offset`, `set_decimal`, `save_formats`, `save_and_show`, `label_axes`, `arrow_axis`, `validate_figure` (all in `dartwork_mpl`)
- Color class: `dartwork_mpl.Color`, `dm.oklab`, `dm.oklch`, `dm.rgb`, `dm.hex`, `dm.named`, `dm.cspace`
- Constants: `dm.SW`, `dm.DW`
- Every function/argument is cataloged in `docs/api/index.rst`

## AI-Assisted Development

dartwork-mpl is designed to work seamlessly with AI coding assistants. Learn how to efficiently create publication-quality graphs with AI assistance:

- **[AI-Assisted Graph Development](ai_assisted.md)**: Best practices for using AI assistants with dartwork-mpl
  - Setting up context prompts for Cursor IDE and other tools
  - Creating plot functions with configurable arguments
  - Rapid iteration in autoreload-enabled notebooks

## See more

- Examples Gallery for finished plots by category
- [Color System](../color_system/index.md) for naming rules and weight choices
- [API Reference](../api/index.rst) for detailed call signatures across styles, layout, colors, fonts, I/O, validation, and extended plots

## Diagnostics & previews

```python
import dartwork_mpl as dm

dm.plot_colors(ncols=5, sort_colors=True)          # inspect each color library
dm.plot_colormaps(group_by_type=True, ncols=4)     # compare sequential/diverging sets
dm.plot_fonts(font_size=11, ncols=3)               # audit bundled fonts
```

- For quick asset audits, lean on **API › Visualization Tools** (`plot_colors`, `plot_colormaps`, `plot_fonts`).
