# AI Integration

**dartwork-mpl** is built for the age of AI-assisted coding. Every API, every default, and every bundled asset is designed so that AI coding assistants produce **correct, publication-quality plots on the first try**.

---

## Agent intent → top-level call

For AI agents that import `dartwork_mpl as dm` without going through the
MCP server: every high-value composition helper is reachable as
`dm.<name>` directly. The same names are also available under
`dm.helpers.<name>`.

| If the agent intends to… | Call |
|---|---|
| Verify input data shape before plotting | `dm.validate_data(...)` |
| Pick a chart type from a data description | `dm.suggest_chart_type(...)` |
| Get a curated palette for N data series | `dm.make_palette(n, kind=...)` |
| Add value labels on top of bars / points | `dm.add_value_labels(ax, ...)` |
| Place the legend without overlapping data | `dm.optimize_legend(ax, ...)` |
| Run heuristic quality checks on a figure | `dm.check_figure_quality(fig)` |
| Create a styled figure in one call | `dm.create_figure_with_style(...)` |
| Save with hi-res presets in multiple formats | `dm.save_figure(fig, "out")` |

Lint and validation entry points keep their existing names:
`dm.validate_figure(fig)`, `dm.validate_with_fixes(fig)`,
`dm.lint_dartwork_mpl_code(code)` (MCP only for now; native
`dm.lint(code)` lands in T4).

---

## How It Works

dartwork-mpl provides three layers of AI integration, each building on the last:

:::{card}
:class-header: sd-bg-light

**Layer 3 — MCP Server** 🔌
: AI reads docs in real time via Model Context Protocol

**Layer 2 — Bundled Guides** 📖
: `get_prompt` · `copy_prompt` · `install_llm_txt`

**Layer 1 — AI-Friendly API** 🎯
: `dm.style.use` · `dm.simple_layout` · `oc.blue5`

_Each layer builds on the one below._
:::

**Layer 1** works out of the box — no setup required. AI assistants naturally produce better code because the API has fewer ways to go wrong.

**Layer 2** adds bundled documentation that AI can read programmatically, even without internet access.

**Layer 3** provides real-time documentation access through the [Model Context Protocol](https://modelcontextprotocol.io), so the AI always has the latest guidelines.

---

## Quick Start

Get up and running with AI-assisted plotting in 30 seconds:

::::{tab-set}

:::{tab-item} With MCP (recommended)
:sync: mcp

Add the dartwork-mpl MCP server to your AI client config, and it will automatically access documentation and guidelines:

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

Then just ask your AI assistant to create a plot — it will know exactly how to use dartwork-mpl.

→ Full setup: **[MCP Server](mcp_server.md)**
:::

:::{tab-item} With IDE Integration
:sync: ide

Install static guide files into your IDE's AI context folders:

```python
import dartwork_mpl as dm
dm.install_llm_txt()
# ✅ Guides installed for Claude Code and Cursor IDE
```

→ Details: **[AI-Assisted Development](ai_assisted.md)**
:::

:::{tab-item} No Setup Needed
:sync: nosetup

Even without any configuration, dartwork-mpl's consistent API makes AI-generated code more reliable. Just install the package and tell your AI assistant to use it:

```python
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use('font-scientific')
fig, ax = plt.subplots(figsize=dm.figsize('13cm', 'standard'))
ax.plot(x, y, color='oc.blue5')
dm.simple_layout(fig)
dm.save_and_show(fig)
```

→ Learn why: **[Why AI-Ready?](why_ai_ready.md)**
:::

::::

---

## What's Inside

```{toctree}
:maxdepth: 1
:titlesonly:

Why AI-Ready? <why_ai_ready>
AI-Assisted Development <ai_assisted>
MCP Server <mcp_server>
```
