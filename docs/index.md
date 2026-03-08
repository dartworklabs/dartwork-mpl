# dartwork-mpl

```{raw} html
<div class="dm-landing-hero">
  <p class="dm-landing-tagline">Publication-quality matplotlib —<br>one import away</p>
  <p class="dm-landing-subtitle">
    Curated styles, 900+ named colors, and smart layout utilities.<br>
    No new API to learn — you're still writing matplotlib.
  </p>

  <div class="dm-landing-code">
    <pre><code><span class="kn">import</span> <span class="nn">dartwork_mpl</span> <span class="k">as</span> <span class="nn">dm</span>

<span class="n">dm</span><span class="o">.</span><span class="n">style</span><span class="o">.</span><span class="n">use</span><span class="p">(</span><span class="s">"scientific"</span><span class="p">)</span>   <span class="c"># fonts, colors, weights — done</span>
<span class="n">dm</span><span class="o">.</span><span class="n">simple_layout</span><span class="p">(</span><span class="n">fig</span><span class="p">)</span>        <span class="c"># optimized margins — done</span></code></pre>
  </div>

  <div class="dm-landing-cta">
    <a href="installation/index.html" class="dm-landing-btn dm-landing-btn-primary">Install</a>
    <a href="usage_guide/quickstart.html" class="dm-landing-btn dm-landing-btn-secondary">Quick Start →</a>
  </div>
</div>
```

**See the difference — drag to compare:**

```{raw} html
:file: _static/compare_slider.html
```

---

## What you get

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} 🎨 Style Presets
:link: usage_guide/styles
:link-type: doc

One-call themes for every context — `scientific`, `report`, `presentation`, `poster`, `web`, `dark`, and Korean variants.
:::

:::{grid-item-card} 🌈 Named Colors
:link: color_system/index
:link-type: doc

900+ perceptual colors from Open Color, Tailwind, and Material Design — just use `"oc.blue5"` anywhere matplotlib takes a color.
:::

:::{grid-item-card} 📐 Smart Layout
:link: usage_guide/layout
:link-type: doc

`simple_layout()` uses L-BFGS-B optimization for uniform margins — a drop-in `tight_layout()` replacement that actually works.
:::

:::{grid-item-card} 🔍 Visual Validation
:link: api/validate
:link-type: doc

Auto-detect overflow, text overlap, legend overflow, tick crowding, and empty axes — catches issues invisible in terminal-only workflows.
:::

:::{grid-item-card} 🤖 AI-Native Design
:link: integrations/index
:link-type: doc

MCP server + prompt system for AI coding agents. Designed so agents use familiar matplotlib calls, not a custom API.
:::

:::{grid-item-card} 📦 Own Your Code
:link: philosophy/index
:link-type: doc

Inspired by shadcn/ui — every utility is simple enough to copy into your project. No lock-in, no black boxes.
:::

::::

---

## How it works

::::{grid} 1 2 4 4
:gutter: 2

:::{grid-item}
**① Pick a style**

```python
dm.style.use("scientific")
```

:::

:::{grid-item}
**② Add color**

```python
color="oc.blue5"
```

:::

:::{grid-item}
**③ Optimize layout**

```python
dm.simple_layout(fig)
```

:::

:::{grid-item}
**④ Export**

```python
dm.save_formats(fig, "out")
```

:::

::::

---

```{toctree}
:maxdepth: 2
:titlesonly:

Installation <installation/index>
Usage Guide <usage_guide/index>
Examples Gallery <examples_gallery/index>
Color System <color_system/index>
Fonts <fonts/index>
API Reference <api/index>
Design Philosophy <philosophy/index>
AI Integration <integrations/index>
```
