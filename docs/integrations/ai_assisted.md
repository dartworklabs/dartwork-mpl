# AI-Assisted Development

dartwork-mpl is designed to work seamlessly with AI coding assistants like Cursor, GitHub Copilot, and Claude Code. This guide explains best practices for efficiently creating publication-quality graphs with AI assistance.

> **New here?** Read **[Why AI-Ready?](why_ai_ready.md)** first to understand the design decisions that make dartwork-mpl uniquely suited for AI-assisted workflows.

## Overview

When working with AI assistants to create graphs, follow these three key principles:

1. **Set up MCP server** to provide AI with dartwork-mpl guidelines
2. **Create plot functions** with configurable arguments instead of modifying code directly
3. **Work in an autoreload-enabled notebook** for rapid iteration

## 1. MCP Server Setup (Recommended)

The **recommended way** to provide dartwork-mpl context to AI assistants is through the Model Context Protocol (MCP). MCP allows AI assistants to automatically access the latest dartwork-mpl documentation and guidelines without manual setup or updates.

For detailed setup instructions, client configuration, verification steps, and troubleshooting, see the dedicated **[MCP Server](mcp_server.md)** page.

### Alternative: File-Based LLM Integration

If your AI assistant doesn't support MCP, you can install static guide files directly into IDE integration folders:

```python
import dartwork_mpl as dm

# Install usage guides for AI assistants
dm.install_llm_txt()
# ✅ dartwork-mpl usage guide installed successfully!
# 📁 Claude Code: .claude/commands/dartwork-mpl-usage.md
# 📁 Cursor IDE: .cursor/dartwork-mpl-usage.md

# Remove when no longer needed
dm.uninstall_llm_txt()
```

> **Note:** MCP is preferred over file-based integration because it provides always-up-to-date documentation and richer tool access. Use `install_llm_txt()` only when MCP is not available.

## 2. Create Plot Functions with Arguments

Structure your code as functions with configurable arguments rather than
modifying code directly. This makes AI assistance faster and more reliable.

### Function-Based Approach

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

def plot_signal(
    data: np.ndarray,
    color: str = 'dc.ocean2',
    linewidth: float = 0.7,
    figsize: tuple[float, float] | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot a signal with configurable styling.

    Parameters
    ----
    data : np.ndarray
        Signal data to plot.
    color : str, optional
        Line color. Default is 'dc.ocean2'.
    linewidth : float, optional
        Line width. Default is 0.7.
    figsize : tuple[float, float] | None, optional
        Figure size in inches. If None, uses dm.figsize("9cm", "7cm").
    """
    dm.style.use('scientific')

    if figsize is None:
        figsize = dm.figsize("9cm", "7cm")

    fig, ax = plt.subplots(figsize=figsize)

    x = np.arange(len(data))
    ax.plot(x, data, color=color, linewidth=linewidth)
    ax.set_xlabel('Time [s]', fontsize=dm.fs(0))
    ax.set_ylabel('Amplitude', fontsize=dm.fs(0))

    dm.simple_layout(fig)
    return fig, ax

# Usage: Easy to modify by changing arguments
data = np.random.randn(100).cumsum()
fig, ax = plot_signal(data, color='dc.vivid2', linewidth=1.2)
dm.save_and_show(fig)
```

**Why this works better with AI:**

- "Change the line color to `dc.vivid2`" → AI modifies one argument
- "Make the line thicker" → AI adjusts `linewidth=1.2`
- No risk of breaking other parts of the code

### Function Design Tips

1. **Make visual parameters configurable** with sensible defaults
2. **Use type hints** so AI understands what values are acceptable
3. **Document parameters** — especially dartwork-mpl-specific values like
   color names (`oc.*`, `tw.*`)

### Working with AI: Be Specific

When asking AI to modify your plots, refer to specific parameters:

| ✅ Specific (better results)               | ❌ Vague (slower, error-prone) |
| ------------------------------------------ | ------------------------------ |
| "Change color to `dc.vivid2`"                | "Make it a bit redder"         |
| "Set linewidth to 1.2"                     | "Make the line thicker"        |
| "Resize to `dm.figsize(\"17cm\", \"wide\")`" | "Make the chart bigger"        |
| "Add title `'Signal Response'`"            | "Make it look better"          |

## 3. Rapid Iteration with Autoreload

The fastest way to iterate on plots with AI is to define functions in separate
`.py` files and test them in notebooks with autoreload.

### Setup

**1. Create a Python file** for your visualization functions (`plotting.py`):

```python
# plotting.py
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

def plot_comparison(
    data1: np.ndarray,
    data2: np.ndarray,
    color1: str = 'dc.vivid2',
    color2: str = 'dc.ocean2',
    linewidth: float = 0.7,
    title: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot two signals for comparison."""
    dm.style.use('scientific')
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "7cm"))
    ax.plot(data1, color=color1, linewidth=linewidth, label='Signal A')
    ax.plot(data2, color=color2, linewidth=linewidth, label='Signal B')
    if title:
        ax.set_title(title, fontsize=dm.fs(2))
    ax.legend(fontsize=dm.fs(-1))
    dm.simple_layout(fig)
    return fig, ax
```

**2. Use autoreload in your notebook:**

```python
# notebook.ipynb
%load_ext autoreload
%autoreload 2

import numpy as np
import dartwork_mpl as dm
from plotting import plot_comparison

data1 = np.random.randn(100).cumsum()
data2 = np.random.randn(100).cumsum() + 5
fig, ax = plot_comparison(data1, data2, color1='dc.forest2', title='Comparison')
dm.save_and_show(fig)
```

**3. Edit `plotting.py` → re-run cell → see changes immediately.** No kernel
restart needed.

### Why External Files?

| External `.py` files                       | Functions in notebook cells       |
| ------------------------------------------ | --------------------------------- |
| AI assistants edit reliably                | AI sometimes struggles with cells |
| Clean version control                      | Notebooks mix code with output    |
| Reusable across multiple notebooks         | Locked to one notebook            |
| Notebook stays short (just function calls) | Notebook gets cluttered           |

## Summary

1. **Set up MCP server** for automatic access to dartwork-mpl documentation
2. **Create plot functions** with configurable arguments and sensible defaults
3. **Work in autoreload-enabled notebooks** with functions in external `.py` files
4. **Be specific** when asking AI to modify your plots — use parameter names and values
