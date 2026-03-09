# Why AI-Ready?

dartwork-mpl is designed from the ground up to work **with** AI coding assistants. This page explains how each feature specifically helps AI agents produce correct plots.

> **Deep dive:** For the design philosophy behind these decisions, see
> [Designed for AI Agents](../philosophy/ai_native.md).

```{contents} On this page
:local:
:depth: 2
```

---

## Automatic Validation

AI-generated plots often have subtle issues invisible in text-only environments: clipped labels, overlapping legends, missing tick marks. dartwork-mpl catches these automatically:

```python
# After creating your figure
issues = dm.validate_figure(fig)

# Returns a list of detected problems:
# - Clipped text outside figure bounds
# - Overlapping elements
# - Inconsistent font sizes
```

This is especially powerful in **autonomous AI pipelines** where there's no human to visually inspect every plot. The validation step acts as a quality gate.

---

## MCP Protocol: Real-Time AI Access

The **Model Context Protocol (MCP)** gives AI assistants **live access** to dartwork-mpl's documentation:

| Resource                             | What the AI gets                                                  |
| ------------------------------------ | ----------------------------------------------------------------- |
| `dartwork-mpl://guide/general-guide` | Complete usage guide — styles, colors, layout, fonts, save/export |
| `dartwork-mpl://guide/layout-guide`  | Deep-dive into `simple_layout`, GridSpec strategies, edge cases   |
| `fetch_github_document(url)`         | Any raw file from the dartwork-mpl GitHub repo, on demand         |

This means the AI assistant always has **the latest, most accurate documentation** — no copy-paste, no stale caches, no hallucinated APIs.

→ For setup instructions, see **[MCP Server](mcp_server.md)**.

---

## Putting It All Together

```
┌─────────────────────────────────────────────────────┐
│  You say: "Plot the signal response with a red line │
│  and save it as SVG for my paper."                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  AI reads dartwork-mpl guide via MCP                │
│  → Knows to use dm.style.use('scientific')          │
│  → Knows to use dm.simple_layout(), not tight_layout│
│  → Knows color syntax: 'oc.red5'                    │
│  → Knows to save with dm.save_formats()             │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  AI generates correct code on first attempt         │
│  → dm.validate_figure() confirms no issues          │
│  → Paper-ready SVG saved                            │
└─────────────────────────────────────────────────────┘
```

→ Ready to set this up? See **[AI-Assisted Development](ai_assisted.md)** for the workflow guide, or jump straight to **[MCP Server](mcp_server.md)** for configuration.
