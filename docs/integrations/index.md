# AI Integration

**dartwork-mpl** is built for the age of AI-assisted coding. Every API, every default, and every bundled asset is designed so that AI coding assistants produce **correct, publication-quality plots on the first try**.

```{contents} On this page
:local:
:depth: 2
```

---

## How It Works

dartwork-mpl provides three layers of AI integration, each building on the last:

```{mermaid}
graph TB
    subgraph L3["Layer 3 — MCP Server"]
        MCP["🔌 Model Context Protocol<br/>AI reads docs in real time"]
    end
    subgraph L2["Layer 2 — Bundled Guides"]
        PROMPT["📖 Prompt Guides<br/>get_prompt · copy_prompt · install_llm_txt"]
    end
    subgraph L1["Layer 1 — AI-Friendly API"]
        API["🎯 Consistent API Surface<br/>dm.style.use · dm.simple_layout · oc.blue5"]
    end

    L3 --> L2 --> L1

    style L3 fill:#e8f5e9,stroke:#43a047
    style L2 fill:#e3f2fd,stroke:#1e88e5
    style L1 fill:#fff3e0,stroke:#fb8c00
```

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
import dartwork_mpl as dm

dm.style.use('scientific')
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(7)))
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
