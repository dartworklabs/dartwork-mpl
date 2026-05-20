# Why AI-Ready?

dartwork-mpl is designed from the ground up to work **with** AI coding
assistants. This page shows the concrete features that make AI-generated
plots reliable.

> **Design rationale:** For the philosophy behind these decisions — why
> thin utilities beat wrappers for AI — see
> [Designed for AI Agents](../philosophy/ai_native.md).

---

## Automatic Validation

AI-generated plots often have subtle issues invisible in text-only
environments: clipped labels, overlapping legends, missing tick marks.
dartwork-mpl catches these automatically:

```python
# After creating your figure
issues = dm.validate_figure(fig)

# Returns a list of detected problems:
# - Clipped text outside figure bounds
# - Overlapping elements
# - Inconsistent font sizes
```

This is especially powerful in **autonomous AI pipelines** where there's no
human to visually inspect every plot. The validation step acts as a quality
gate.

---

## MCP Protocol: Real-Time AI Access

The **Model Context Protocol (MCP)** gives AI assistants **live access** to
dartwork-mpl's documentation, colors, styles, and validation tools:

| Category       | Count | Examples                                                                                 |
| -------------- | ----- | ---------------------------------------------------------------------------------------- |
| **Resources**  | 12 + 3 templated | Agent entry, policy, anti-patterns, recipes, palette/colors, palette/fonts, styles/list, templates/list, `api/{name}`, `styles/{preset}`, `templates/{plot_type}` |
| **Tools**      | 10    | Color lookup + mix + family list, code lint (text & JSON), find template, migrate 0.3 code, data validation, GitHub fetch, package info |
| **Prompts**    | 2     | `create_plot` (guided generation), `style_review` (compliance review)                    |

> Source-of-truth counts derived from `dartwork-mpl-mcp`'s
> ``list_resources`` / ``list_tools`` / ``list_prompts`` handshake.
> The exact catalog ships in
> [`src/dartwork_mpl/mcp/`](https://github.com/dartworklabs/dartwork-mpl/tree/main/src/dartwork_mpl/mcp).

The AI assistant always has **the latest, most accurate documentation** —
no copy-paste, no stale caches, no hallucinated APIs. Tools like
`lint_dartwork_mpl_code` catch antipatterns (e.g., `figsize=`, `tight_layout()`)
automatically, and `validate_plot_data` ensures data structures are correct
before plotting.

→ For the full list and setup instructions, see **[MCP Server](mcp_server.md)**.

---

## Putting It All Together

::::{grid} 1
:gutter: 3
:class-container: w-75 mx-auto

:::{grid-item-card} 🗣️ User Prompt
:class-header: text-primary font-weight-bold

You say: _"Plot the signal response with a red line and save it as SVG for my paper."_
:::

:::{grid-item}
:class: text-center text-muted fs-3

↓
:::

:::{grid-item-card} 🧠 Context Retrieval (MCP)
:class-header: text-info font-weight-bold

AI reads **dartwork-mpl guide** via MCP:

- Knows to use `dm.style.use('scientific')`
- Knows to use `dm.simple_layout()`, not `tight_layout`
- Knows color syntax: `'dc.vivid2'`
- Knows to save with `dm.save_formats()`
  :::

:::{grid-item}
:class: text-center text-muted fs-3

↓
:::

:::{grid-item-card} ✅ Execution & Validation
:class-header: text-success font-weight-bold
:class-card: border-success

- ✨ **AI generates correct code on first attempt**
- 🔍 `dm.validate_figure()` confirms no issues
- 📄 Paper-ready SVG saved
  :::
  ::::

→ Ready to set this up? See **[AI-Assisted Development](ai_assisted.md)**
for the workflow guide, or jump straight to **[MCP Server](mcp_server.md)**
for configuration.
