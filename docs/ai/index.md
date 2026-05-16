---
# H3 questions in the IDE matrix shouldn't crowd the right rail.
tocdepth: 2
---

# AI & Agent-Assisted Plotting

dartwork-mpl is **built for the way Python plots are written in 2026**:
a developer types intent into Cursor / Claude Code / Zed Agent panel,
the agent calls matplotlib through dartwork-mpl, and a
publication-ready figure comes out on the first try. Every API choice,
default, prompt resource, and bundled file in this library exists to
make that loop reliable.

This page is the **hub** — the 30-second setup, the IDE compatibility
matrix, and the deep links into agent-specific guides. New to the
library? Start here, then jump to your tool.

---

## 30-second setup

::::{tab-set}

:::{tab-item} MCP-native client (recommended)
:sync: mcp

If your agent supports the [Model Context Protocol](https://modelcontextprotocol.io)
— Claude Code, Cursor, Windsurf, Continue, Zed Agent panel, and a
growing list of others do — the agent reads dartwork-mpl docs live,
runs the lint engine on your draft code, and looks up colors and
templates *inside the chat context*.

```bash
# 1. Install with the [mcp] extra
pip install "dartwork-mpl[mcp]"          # or:  uv add "dartwork-mpl[mcp]"

# 2. Verify the console entry point
which dartwork-mpl-mcp
```

Then drop the JSON below into your client's MCP config (paths shown
on the **[MCP Server](../integrations/mcp_server.md)** page for each
client). One restart and the agent has dartwork-mpl context.

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "dartwork-mpl-mcp"
    }
  }
}
```

→ Per-client config snippets: **[MCP Server setup](../integrations/mcp_server.md)**
:::

:::{tab-item} File-based fallback (every other agent)
:sync: file

Agents that don't speak MCP yet (Aider, GitHub Copilot Chat, plain
ChatGPT or Claude.ai) still benefit from dartwork-mpl's bundled
**LLM-readable corpus** — anti-patterns, design rules, and 18 ready-to-use
plot templates concatenated into one paste-able file.

```python
import dartwork_mpl as dm

# Drop the entire corpus into your IDE's AI-context folder
dm.install_llm_txt()
# ✅ Installed for Claude Code, Cursor, Continue, …
```

For agents that can read a local file but don't auto-detect a folder:

```bash
# Aider — read the corpus as one big system prompt
aider --read $(python -c "import dartwork_mpl, pathlib; print(pathlib.Path(dartwork_mpl.__file__).parent / 'asset' / 'prompt' / 'llms-full.txt')")
```

For chat-only surfaces (web ChatGPT, Claude.ai), paste the contents
of `llms.txt` (≈ 2.5 KB index) into a system prompt or pinned message.

→ Full instructions: **[AI-Assisted Development](../integrations/ai_assisted.md)**
:::

:::{tab-item} Zero setup
:sync: zero

Even without MCP or file installation, dartwork-mpl's
**one-right-way API** makes any agent's matplotlib output more
reliable. Names like `dm.style.use("scientific")`, `oc.blue5`,
`dm.figsize("13cm", "standard")`, and `dm.simple_layout(fig)` are
unambiguous enough that LLMs reproduce them deterministically across
conversations.

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, y, color="oc.blue5")
dm.simple_layout(fig)
dm.save_formats(fig, "out", formats=("png", "pdf"))
```

→ Design rationale: **[Why AI-Ready?](../integrations/why_ai_ready.md)**
:::

::::

---

(ide-agent-compatibility-2026-q2)=
## IDE & agent compatibility (2026-Q2)

| Tool / Agent | MCP support | Recommended path | Notes |
|---|---|---|---|
| **Claude Code** (Anthropic CLI / VS Code / JetBrains) | ✅ first-class | `claude mcp add dartwork-mpl dartwork-mpl-mcp` | Native — slash commands and tool use both work. |
| **Cursor** | ✅ Settings → Composer → MCP | Drop JSON, restart | Auto-detects local servers on the next chat. |
| **Windsurf** (Cascade) | ✅ JSON config | `~/.codeium/windsurf/mcp_config.json` | |
| **Continue** (VS Code / JetBrains) | ✅ `config.yaml` | `mcpServers:` block | Free + open-source. |
| **Zed** (Agent panel) | ✅ Settings → Agent → Tools | JSON snippet | MCP support shipped 2025-Q3. |
| **Anthropic API / SDK** (custom agents) | ✅ via `tools=` | Wire `dartwork-mpl-mcp` as a sub-process | For people building their own agents. |
| **GitHub Copilot Chat** | ❌ (as of 2026-Q2) | Paste `AGENTS.md` as a workspace instruction | File-based fallback. |
| **Aider** | ❌ | `aider --read llms-full.txt` | File-based fallback. |
| **ChatGPT** (web / desktop) | ❌ | Paste `llms.txt` (≈ 2.5 KB) into system prompt | Chat-only surfaces. |
| **Claude.ai** (web) | ❌ on free tier; ✅ on Teams/Enterprise via Custom MCP | Same JSON as Claude Code | |
| **Other LLMs** | varies | `llms-full.txt` paste-in works for all | Universal fallback. |

> Updated 2026-05-17. Open a PR on this table if your tool's MCP
> support changed — it moves fast.

---

## Why agents work well here

dartwork-mpl is **not an AI wrapper around matplotlib** — it is
matplotlib with the ambiguity removed. The library follows three
rules that compound into reliable AI output:

::::{grid} 1 1 3 3
:gutter: 2

:::{grid-item-card} 🎯 **One canonical call**

For every plotting task, there is one dartwork-mpl function — not
three (`tight_layout` / `constrained_layout` / `subplots_adjust`).
Agents pick the same path across runs, so generated code is
reproducible.
:::

:::{grid-item-card} 🎨 **Semantic names**

Colors are `oc.blue5` and `tw.indigo600`, not `#3b82f6`. Figure
widths are `"13cm"`, not `5.118`. Agents reliably reproduce the
names; they hallucinate the numbers.
:::

:::{grid-item-card} 🧪 **Inline validation**

`dm.validate_figure(fig)` catches overflow, asymmetric margins, and
pie-label cutoffs before the agent hands back a broken plot — and
`validate_with_fixes` applies the obvious repairs automatically.
:::

::::

→ Long-form design rationale: **[Designed for AI Agents](../philosophy/ai_native.md)**

---

## Bundled AI assets

| Asset | Use it for | Entry point |
|---|---|---|
| **MCP server** | Live doc access + lint inside the chat | `dartwork-mpl-mcp` console script ([setup](../integrations/mcp_server.md)) |
| **Prompt corpus** (15 files) | Anti-patterns, style rules, recipes — paste-able | `dm.list_prompts()` / `dm.get_prompt("02-anti-patterns")` |
| **18 plot templates** | Drop-in patterns for bar / line / scatter / heatmap / dashboards | [AI Plot Templates gallery](../examples_gallery/09_ai_templates/index.rst) |
| **`AGENTS.md` / `CLAUDE.md`** | 30-second onboarding for any LLM | Repo root |
| **`llms.txt`** | Lightweight index (≈ 2.5 KB) — fits in any system prompt | Repo root |
| **`llms-full.txt`** | Concatenated full reference (≈ 45 KB) — for tools that read whole files | Repo root |

---

## Agent intent → top-level call

For agents that import `dartwork_mpl as dm` directly: every high-value
composition helper is reachable as `dm.<name>`.

| If the agent intends to… | Call |
|---|---|
| Verify input data shape before plotting | `dm.validate_data(...)` |
| Pick a chart type from a data description | `dm.suggest_chart_type(...)` |
| Get a curated palette for N data series | `dm.make_palette(n, kind=...)` |
| Add value labels on top of bars / points | `dm.add_value_labels(ax, ...)` |
| Place the legend without overlapping data | `dm.optimize_legend(ax, ...)` |
| Run heuristic quality checks on a figure | `dm.check_figure_quality(fig)` |
| Save with hi-res presets in multiple formats | `dm.save_formats(fig, "out")` |
| Lint generated code before returning it | `dm.lint_dartwork_mpl_code(code)` (MCP tool) |

---

## Deep dives

```{toctree}
:maxdepth: 1
:titlesonly:

Why AI-Ready? <../integrations/why_ai_ready>
AI-Assisted Development <../integrations/ai_assisted>
MCP Server <../integrations/mcp_server>
Designed for AI Agents (philosophy) <../philosophy/ai_native>
AI Plot Templates (gallery) <../examples_gallery/09_ai_templates/index>
```
