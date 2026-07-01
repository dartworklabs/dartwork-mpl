# Designed for AI Agents

AI coding agents — Cursor, Copilot, Claude, and other LLM-powered assistants — already know matplotlib. It is one of the most heavily represented Python libraries in any LLM's training data, with **40M+ monthly PyPI downloads** and **70k+ Stack Overflow questions**.

dartwork-mpl is built to leverage this fact. This page explains the **design principles** behind our AI-friendly API. For concrete features and setup instructions, see the [AI Integration](../integrations/index) guide.

## One Right Way to Do Things

The most common source of AI errors is **ambiguity**. When there are multiple ways to achieve the same result, LLMs pick different approaches across conversations — leading to inconsistent output.

dartwork-mpl provides **one canonical function** for each task:

| Task          | Raw matplotlib (many ways)                                  | dartwork-mpl (one way)       |
| ------------- | ----------------------------------------------------------- | ---------------------------- |
| Apply a style | `plt.style.use()`, `rcParams`, `with plt.style.context()`   | `dm.style.use('scientific')` |
| Set layout    | `tight_layout()`, `constrained_layout`, `subplots_adjust()` | `dm.simple_layout(fig)`      |
| Save figures  | `savefig()` with many kwargs                                | `dm.save_formats(fig, path)` |
| Set font size | `fontsize=12`, `fontsize='large'`                           | `fontsize=dm.fs(2)`          |

## Semantic Color Names

AI assistants are unreliable with hex codes. Ask for "a nice blue" and you'll get a different `#hex` every time.

dartwork-mpl solves this with **human-readable, deterministic color names**:

```python
# AI can describe and produce these reliably
ax.plot(x, y1, color='dc.bold2')       # OpenColor red, weight 5
ax.plot(x, y2, color='tw.blue500')    # Tailwind blue 500

# Compare with raw matplotlib
ax.plot(x, y1, color='#e03131')       # What color is this? 🤷
```

## Context Prompts over Predefined Functions

Instead of memorizing specialized plot functions, describe what you want in plain language:

```text
"Create a line plot for a Korean research paper with two y-axes,
use dartwork-mpl's scientific-kr style, and optimize the layout"
```

The agent generates correct code because the underlying matplotlib API is well-known, and dartwork-mpl's utilities (`dm.style.use`, `dm.simple_layout`) are simple and predictable.

## Built-in Knowledge Base

dartwork-mpl bundles its documentation **inside the package**, accessible even in air-gapped environments:

```python
dm.list_prompts()                       # ['general-guide', 'layout-guide']
content = dm.get_prompt('general-guide') # read guide programmatically
```

For real-time access, dartwork-mpl also ships a **Model Context Protocol (MCP) server** — see [AI Integration](../integrations/index) for setup.

## See also

- [Why AI-Ready?](../integrations/why_ai_ready.md) — concrete features: validation, MCP, and a worked example
- [MCP Server](../integrations/mcp_server.md) — step-by-step setup
- [AI-Assisted Development](../integrations/ai_assisted.md) — IDE integration and bundled guides
