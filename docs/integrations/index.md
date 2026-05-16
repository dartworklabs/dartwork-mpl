---
# Keep the legacy /integrations/index.html URL working but redirect
# visitors to the new top-level /ai/ hub. The deep pages
# (mcp_server.md, ai_assisted.md, why_ai_ready.md) keep their existing
# URLs and are linked from the hub.
tocdepth: 2
---

# AI Integration

```{note}
This page moved. AI integration is now a **top-level section** in the
navigation — visit **[AI & Agent-Assisted Plotting](../ai/index.md)**
for the hub (30-second setup, IDE compatibility matrix, prompt
corpus, plot templates).

The deep pages below kept their existing URLs:
[MCP Server](mcp_server.md) · [AI-Assisted Development](ai_assisted.md) · [Why AI-Ready?](why_ai_ready.md).
```

## Agent intent → top-level call

For agents that import `dartwork_mpl as dm` directly: every
high-value composition helper is reachable as `dm.<name>`.

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

```{toctree}
:hidden:

Why AI-Ready? <why_ai_ready>
AI-Assisted Development <ai_assisted>
MCP Server <mcp_server>
```
