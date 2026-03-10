# dartwork-mpl

```{raw} html
<div class="dm-landing-hero">
  <p class="dm-landing-tagline">matplotlib, but beautiful.</p>
  <p class="dm-landing-subtitle">
    One import. No new API to learn.<br>
    Publication-quality plots by default.
  </p>

  <div class="dm-landing-cta">
    <div class="dm-landing-install">
      <code>pip install dartwork-mpl</code>
      <button class="dm-landing-copy-btn" onclick="navigator.clipboard.writeText('pip install dartwork-mpl').then(()=>{this.textContent='✓';setTimeout(()=>{this.textContent='⎘'},1500)})">⎘</button>
    </div>
    <a href="usage_guide/quickstart.html" class="dm-landing-btn dm-landing-btn-secondary">Quick Start →</a>
  </div>
</div>
```

```{raw} html
<div class="dm-landing-proof">
  <p class="dm-landing-proof-label">Drag to compare</p>
</div>
```

```{raw} html
:file: _static/compare_slider.html
```

```{raw} html
<div class="dm-landing-numbers">
  <div class="dm-landing-number-item">
    <span class="dm-landing-number-big">7</span>
    <span class="dm-landing-number-label">Style Presets</span>
  </div>
  <div class="dm-landing-number-sep">·</div>
  <div class="dm-landing-number-item">
    <span class="dm-landing-number-big">900+</span>
    <span class="dm-landing-number-label">Named Colors</span>
  </div>
  <div class="dm-landing-number-sep">·</div>
  <div class="dm-landing-number-item">
    <span class="dm-landing-number-big">0</span>
    <span class="dm-landing-number-label">New APIs to learn</span>
  </div>
</div>
```

---

## All it takes

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("scientific")              # ① Pick a style
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
ax.plot(x, np.sin(x), color="oc.blue5") # ② Use named colors
dm.simple_layout(fig)                   # ③ Optimize layout
dm.save_formats(fig, "out")             # ④ Export SVG + PNG
```

```{raw} html
<p class="dm-landing-code-tagline"><em>You're still writing matplotlib — we just make it look good.</em></p>
```

## Core pillars

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} 🎨 Style in One Call
:link: usage_guide/styles
:link-type: doc

Pick from `scientific`, `report`, `presentation`, `poster`, `web`, `dark`, or `minimal` — each with a `-kr` Korean variant. 900+ named colors from Open Color, Tailwind, and Material Design.
:::

:::{grid-item-card} 📐 Smart Layout
:link: usage_guide/layout
:link-type: doc

`simple_layout()` replaces `tight_layout()` with L-BFGS-B optimized margins. Built-in visual validation catches overflow, text overlap, and tick crowding automatically.
:::

:::{grid-item-card} 🎛️ Interactive UI
:link: usage_guide/interactive
:link-type: doc

Launch a local web app to interactively tweak plot parameters with sliders. Export perfect charts and download reproducible scripts instantly.
:::

:::{grid-item-card} 📦 Zero Lock-in
:link: philosophy/index
:link-type: doc

Every utility is simple enough to copy into your project. No lock-in — leave anytime by taking the code with you.
:::

::::

```{toctree}
:maxdepth: 2
:titlesonly:
:hidden:

Getting Started <installation/index>
Quick Start <usage_guide/quickstart>
Usage Guide <usage_guide/index>
Color System <color_system/index>
Fonts <fonts/index>
Examples Gallery <examples_gallery/index>
API Reference <api/index>
Design Philosophy <philosophy/index>
AI Integration <integrations/index>
```
