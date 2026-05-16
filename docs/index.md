# dartwork-mpl

```{raw} html
<div class="dm-landing-hero">
  <p class="dm-landing-tagline">matplotlib, but beautiful.</p>
  <p class="dm-landing-subtitle">
    Publication-quality plots with zero learning curve.
  </p>

  <div class="dm-landing-cta">
    <div class="dm-landing-install">
      <code>pip install git+https://github.com/dartworklabs/dartwork-mpl</code>
      <button class="dm-landing-copy-btn" onclick="navigator.clipboard.writeText('pip install git+https://github.com/dartworklabs/dartwork-mpl').then(()=>{this.textContent='✓';setTimeout(()=>{this.textContent='⎘'},1500)})">⎘</button>
    </div>
    <a href="usage_guide/quickstart.html" class="dm-landing-btn dm-landing-btn-secondary">Get Started →</a>
  </div>
</div>
```

## Drag the slider — same data, two worlds

```{raw} html
:file: _static/compare_slider.html
```

Drag the divider to inspect the seam. The left half is what
`plt.savefig()` writes with default rcParams; the right half is the
**same script** plus two dartwork-mpl calls — `dm.style.use("scientific")`
to swap the rcParams listed below the slider, and `dm.simple_layout(fig)`
to handle margins. No new plotting API, no axes wrappers, no opinions
about your data. Just the typography and layout knobs you would have set
yourself if you had the budget.

## Quick Example

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")              # Pick a style
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 2])           # Regular matplotlib
dm.simple_layout(fig)                   # Better layout
dm.save_formats(fig, "output")          # Export SVG + PNG
```

:::{figure} usage_guide/images/quickstart_first_figure.svg
:alt: Scientific-style line chart created with dartwork-mpl
:width: 80%
:::

## Why dartwork-mpl?

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} 🎯 **Zero learning curve**
You already know matplotlib. dartwork-mpl just makes the defaults
beautiful and gives you a few one-liners (`simple_layout`,
`save_formats`, named colors) for the parts that always hurt.
:::

:::{grid-item-card} 🎨 **Curated, not invented**
900+ named colors from real design systems (Open Color, Tailwind,
Material, Ant, Chakra, Primer) and 30+ perceptually-uniform
colormaps. Use them as drop-in color strings everywhere matplotlib
accepts a color.
:::

:::{grid-item-card} 📐 **Layouts that just work**
`simple_layout` and `auto_layout` solve the "labels overflow,
margins look weird" problem properly — including with twinx,
colorbars, and long Korean labels.
:::

:::{grid-item-card} 🧪 **Lint your figures**
`dm.validate_figure(fig)` flags overflow, asymmetric margins, and
pie-label cutoffs *before* you save. `validate_with_fixes` applies
the obvious fixes for you.
:::

:::{grid-item-card} 🤖 **AI-ready**
A built-in [MCP server](integrations/mcp_server.md) lets Claude /
Cursor query palettes, lint chart code, and ask for style review —
without leaving the editor.
:::

:::{grid-item-card} 🛠️ **Interactive UI**
Tweak font sizes, line weights, colors, and margins in a local web
app, then [download the exact Python script that reproduces your
plot](usage_guide/interactive.md).
:::

::::

## Try it without installing — interactive widgets

Drag, click, and hover the live previews below. Everything you see
runs entirely in your browser.

:::{tip}
Press <kbd>?</kbd> anywhere on this site to open the keyboard shortcuts
overlay (`/` focuses search, `g h` jumps home, `g q` to Quick Start, `g c`
to Color System, …). The teal `?` button in the bottom-right corner opens
the same overlay.
:::

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} 🎚️ **Pick a preset**
Toggle through `scientific` / `report` / `presentation` / `poster`
on a real chart and watch the typography and spines respond.

→ [Compare presets live](usage_guide/styles.md#interactive-comparison)
:::

:::{grid-item-card} 🌈 **Browse 900+ colors**
Click any swatch to copy its name, filter by library, or scrub
through OKLCH lightness ramps to see how shades evolve.

→ [Open palette explorer](color_system/colors.md)
:::

:::{grid-item-card} 🗺️ **Inspect colormaps**
Filter by category (Single-Hue, Multi-Hue, Diverging, Cyclical,
Categorical) and preview gradients side-by-side.

→ [Open colormap explorer](color_system/colormaps.md)
:::

:::{grid-item-card} 📏 **See `dm.fs()` in action**
A live ruler maps `dm.fs(-2)` … `dm.fs(+3)` to actual point sizes
under each preset, so you can pick the right offset by eye.

→ [Try the size ruler](usage_guide/styles.md)
:::

::::

## Key Features

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} **Style Presets**
:link: usage_guide/styles
:link-type: doc
Professional themes for every context: `scientific`, `report`, `presentation`, `poster`, `web`, `dark`, `minimal` — each one tunes fonts, line weights, spines, and tick styling in a single call.
:::

:::{grid-item-card} **Smart Layout**
:link: usage_guide/layout
:link-type: doc
`simple_layout` and `auto_layout` use real numerical optimizers to give you uniform margins, even with colorbars and long labels. No more `bbox_inches="tight"` guesswork.
:::

:::{grid-item-card} **900+ Colors**
:link: color_system/index
:link-type: doc
Named colors from Open Color, Tailwind, Material Design, Ant Design, Chakra UI, and Primer. Use them as plain color strings: `color="oc.blue5"`.
:::

:::{grid-item-card} **Interactive UI**
:link: usage_guide/interactive
:link-type: doc
Web-based parameter tuning with real-time preview and one-click code export. Adjust until it looks right, then take the script home.
:::

:::{grid-item-card} **Zero API Changes**
:link: philosophy/index
:link-type: doc
Works with your existing matplotlib code. dartwork-mpl never wraps `Figure` or `Axes`; it just sets up the environment and stays out of your way.
:::

:::{grid-item-card} **Export Formats**
:link: api/io
:link-type: doc
One-line export to SVG, PNG, and PDF with sensible DPI defaults — and an optional `validate=True` pass to catch problems before they ship.
:::

::::

## Documentation

```{toctree}
:maxdepth: 1
:caption: Getting Started

installation/index
usage_guide/quickstart
usage_guide/index
```

```{toctree}
:maxdepth: 1
:caption: Reference

design_system/index
examples_gallery/index
api/index
```

```{toctree}
:hidden:

color_system/index
fonts/index
```

```{toctree}
:maxdepth: 1
:caption: More

philosophy/index
troubleshooting
migration
```

```{toctree}
:hidden:

integrations/index
```
