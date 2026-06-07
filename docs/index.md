# dartwork-mpl

```{raw} html
<div class="dm-landing-hero">
  <p class="dm-landing-tagline">matplotlib, but beautiful.</p>
  <p class="dm-landing-subtitle">
    Publication-quality plots with zero learning curve —
    <strong>built for AI coding agents</strong>.
  </p>

  <div class="dm-landing-cta">
    <div class="dm-landing-install">
      <code>uv add git+https://github.com/dartworklabs/dartwork-mpl</code>
      <button class="dm-landing-copy-btn" onclick="navigator.clipboard.writeText('uv add git+https://github.com/dartworklabs/dartwork-mpl').then(()=>{this.textContent='✓';setTimeout(()=>{this.textContent='⎘'},1500)})">⎘</button>
    </div>
    <a href="usage_guide/quickstart.html" class="dm-landing-btn dm-landing-btn-secondary">Get Started →</a>
    <a href="ai/index.html" class="dm-landing-btn dm-landing-btn-secondary">AI / Agents →</a>
  </div>
</div>
```

## Built for AI-assisted plotting

Most matplotlib code in 2026 is written through an agent — Cursor,
Claude Code, Continue, Windsurf, Zed Agent panel, Aider — not by
typing into a blank notebook. dartwork-mpl is the first design layer
on top of matplotlib that is **built for that workflow**: every API
is unambiguous, every color and width has a name (not a hex or a
float), the bundled MCP server lets agents read the docs live, and a
lint engine catches the patterns LLMs typically get wrong.

::::{grid} 1
:gutter: 2

:::{grid-item-card} 🔌 **MCP-native**
:link: ai/index
:link-type: doc

One JSON snippet wires `dartwork-mpl-mcp` into Claude Code, Cursor,
Windsurf, Continue, or Zed. The agent gets live docs, anti-pattern
lint, color lookup, and plot templates — *inside the chat context*.

```bash
pip install "dartwork-mpl[mcp]"
```
:::

:::{grid-item-card} 📄 **Works with every other agent too**
:link: ai/index
:link-type: doc

No MCP? `llms.txt` (2.5 KB index) and `llms-full.txt` (45 KB full
reference) drop straight into Aider, Copilot Chat, ChatGPT, or
Claude.ai. Resolve them from Python with
`dm.agent_doc_path("llms-full")` / `dm.get_agent_doc("llms-full")`.

→ **[See the IDE compatibility matrix](ai/index.md)**
:::

::::

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

## What's in the box

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} **Style presets**
:link: usage_guide/styles
:link-type: doc
Seven curated themes — `scientific`, `report`, `presentation`,
`poster`, `web`, `dark`, `minimal` — each one tunes fonts, line
weights, spines, and ticks in a single `dm.style.use(...)` call.
:::

:::{grid-item-card} **Deterministic layout**
:link: usage_guide/layout
:link-type: doc
`dm.simple_layout(fig)` measures every visible artist and snaps the
axes to consistent margins — twinx, colorbars, rotated ticks, and
long Korean labels included. No `bbox_inches="tight"` guessing.
:::

:::{grid-item-card} **900+ named colors**
:link: color_system/index
:link-type: doc
Open Color, Tailwind, Material, Ant Design, Chakra, and Primer
shipped as plain color strings — `color="dc.ocean2"` works anywhere
matplotlib accepts a color. Plus 30+ perceptually-uniform colormaps.
:::

:::{grid-item-card} **Validation before you ship**
:link: usage_guide/save_export
:link-type: doc
`dm.validate_figure(fig)` flags overflow, asymmetric margins, and
pie-label cutoffs *before* you save. `validate_with_fixes` patches
the obvious ones for you.
:::

:::{grid-item-card} **Zero API changes**
:link: philosophy/index
:link-type: doc
dartwork-mpl never wraps `Figure` or `Axes`. It sets up the
environment and stays out of your way, so every matplotlib trick
you already know still works.
:::

:::{grid-item-card} **One-line export**
:link: api/io
:link-type: doc
`dm.save_formats(fig, "out", formats=("png", "svg", "pdf"))` writes
all three at the right DPI in a single call — with an optional
`validate=True` to catch problems before they ship.
:::

::::

```{toctree}
:hidden:
:caption: Getting Started

installation/index
usage_guide/quickstart
usage_guide/index
```

```{toctree}
:hidden:
:caption: Reference

design_system/index
examples_gallery/index
ai/index
api/index
```

```{toctree}
:hidden:
:caption: More

philosophy/index
troubleshooting
migration
```

% color_system/index and fonts/index are reachable via design_system/index
% (the merged Design System landing). Including them at the root toctree
% appends them under the previous caption in Shibuya's sidebar, which
% looks like a duplicate entry. Make them orphans of the root toctree —
% Sphinx is still happy because design_system/index links to them.

% integrations/index is a thin "this page moved" redirect to /ai/. It is
% no longer part of the visible navigation; the deep pages
% (mcp_server.md, ai_assisted.md, why_ai_ready.md) remain reachable from
% ai/index.md.
