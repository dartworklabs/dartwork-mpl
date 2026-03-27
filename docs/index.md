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

## Quick Example

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")              # Pick a style
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 2])          # Regular matplotlib
dm.simple_layout(fig)                   # Better layout
dm.save_formats(fig, "output")          # Export SVG + PNG
```

:::{figure} usage_guide/images/quickstart_first_figure.svg
:alt: Scientific-style line chart created with dartwork-mpl
:width: 80%
:::

## Key Features

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} **Style Presets**
:link: usage_guide/styles
:link-type: doc
Professional themes for every context: `scientific`, `report`, `presentation`, `poster`, `web`, `dark`, `minimal`
:::

:::{grid-item-card} **Smart Layout**
:link: usage_guide/layout
:link-type: doc
Advanced optimization algorithms for perfect margins and spacing automatically
:::

:::{grid-item-card} **900+ Colors**
:link: color_system/index
:link-type: doc
Named colors from Open Color, Tailwind, and Material Design palettes
:::

:::{grid-item-card} **Interactive UI**
:link: usage_guide/interactive
:link-type: doc
Web-based parameter tuning with real-time preview and code export
:::

:::{grid-item-card} **Zero API Changes**
:link: philosophy/index
:link-type: doc
Works with your existing matplotlib code — no new syntax to learn
:::

:::{grid-item-card} **Export Formats**
:link: api/io
:link-type: doc
One-line export to SVG, PNG, PDF with optimized settings
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

color_system/index
fonts/index
examples_gallery/index
api/index
```

```{toctree}
:maxdepth: 1
:caption: More

philosophy/index
integrations/index
troubleshooting
migration
```
