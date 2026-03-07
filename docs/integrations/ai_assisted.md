# AI-Assisted Development

dartwork-mpl is designed to work seamlessly with AI coding assistants like Cursor, GitHub Copilot, and Claude Code. This guide explains best practices for efficiently creating publication-quality graphs with AI assistance.

## Overview

When working with AI assistants to create graphs, follow these three key principles:

1. **Set up MCP server** to provide AI with dartwork-mpl guidelines
2. **Create plot functions** with configurable arguments instead of modifying code directly
3. **Work in an autoreload-enabled notebook** for rapid iteration

Following these practices will dramatically speed up your workflow and reduce errors.

## 1. MCP Server Setup (Recommended)

The **recommended way** to provide dartwork-mpl context to AI assistants is through the Model Context Protocol (MCP). MCP allows AI assistants to automatically access the latest dartwork-mpl documentation and guidelines without manual setup or updates.

- **Automatic access**: AI assistants can directly access the latest dartwork-mpl documentation
- **No manual updates**: Documentation updates are automatically available to your AI assistant
- **Seamless integration**: Works with Claude Code, Cursor, Windsurf, Antigravity, and any MCP-compatible client

For detailed setup instructions, client configuration, verification steps, and troubleshooting, see the dedicated **[MCP Server](mcp_server.md)** page.

### Alternative: File-Based LLM Integration

If your AI assistant doesn't support MCP, you can install static guide files directly into IDE integration folders using `install_llm_txt()`:

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

One of the most important principles for AI-assisted development is to **structure your code as functions with configurable arguments** rather than modifying code directly.

### Why Functions?

When you ask AI to "change the color slightly" or "make the line a bit thicker," the AI must:

1. Parse your vague description
2. Find the relevant code
3. Guess what "slightly" or "a bit" means
4. Modify the code
5. Risk breaking other parts

This process is slow and error-prone. Instead, use functions with clear arguments:

### ✅ Good: Function-Based Approach

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

def plot_signal(
    data: np.ndarray,
    color: str = 'oc.blue5',
    linewidth: float = 0.7,
    figsize: tuple[float, float] | None = None,
    dpi: int = 200
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot a signal with configurable styling.

    Parameters
    ----
    data : np.ndarray
        Signal data to plot.
    color : str, optional
        Line color. Default is 'oc.blue5'.
    linewidth : float, optional
        Line width. Default is 0.7.
    figsize : tuple[float, float] | None, optional
        Figure size in inches. If None, uses (9cm, 7cm).
    dpi : int, optional
        Figure resolution. Default is 200.

    Returns
    ----
    fig : matplotlib.figure.Figure
        The created figure.
    ax : matplotlib.axes.Axes
        The axes containing the plot.
    """
    dm.style.use('scientific')

    if figsize is None:
        figsize = (dm.cm2in(9), dm.cm2in(7))

    fig = plt.figure(figsize=figsize, dpi=dpi)
    gs = fig.add_gridspec(
        nrows=1, ncols=1,
        left=0.17, right=0.95,
        top=0.95, bottom=0.17
    )
    ax = fig.add_subplot(gs[0, 0])

    x = np.arange(len(data))
    ax.plot(x, data, color=color, linewidth=linewidth)
    ax.set_xlabel('Time [s]', fontsize=dm.fs(0))
    ax.set_ylabel('Amplitude', fontsize=dm.fs(0))

    dm.simple_layout(fig)

    return fig, ax

# Usage: Easy to modify by changing arguments
data = np.random.randn(100).cumsum()
fig, ax = plot_signal(data, color='oc.red5', linewidth=1.2)
dm.save_and_show(fig)
```

This approach provides clear, explicit changes (`color='oc.red5'` instead of "change color slightly"), enables fast iteration by changing arguments, and makes it easy for AI to understand and suggest modifications.

### ❌ Bad: Direct Code Modification

```python
# Don't do this!
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)
ax = fig.add_subplot(111)
ax.plot(data, color='oc.blue5', linewidth=0.7)  # Hard to modify
# ... more code ...
```

When you ask AI to "make it a bit redder," it must:

- Find this specific line
- Guess what "a bit redder" means
- Modify the code
- Risk breaking something

### Function Design Best Practices

1. **Make all visual parameters configurable**:

   ```python
   def plot_comparison(
       data1: np.ndarray,
       data2: np.ndarray,
       color1: str = 'oc.red5',
       color2: str = 'oc.blue5',
       linewidth: float = 0.7,
       figsize: tuple[float, float] | None = None,
       title: str | None = None,
       # ... more parameters
   ):
       pass
   ```

2. **Provide sensible defaults**:

   ```python
   # Good defaults that work out of the box
   def plot_data(data, color='oc.blue5', linewidth=0.7):
       pass
   ```

3. **Use type hints**:

   ```python
   # Helps AI understand what values are acceptable
   def plot_data(
       data: np.ndarray,
       color: str = 'oc.blue5',
       linewidth: float = 0.7
   ) -> tuple[plt.Figure, plt.Axes]:
       pass
   ```

4. **Document parameters**:
   ```python
   """
   Parameters
   ----
   color : str, optional
       Line color. Use dartwork-mpl color names like 'oc.red5' or 'tw.blue500'.
       Default is 'oc.blue5'.
   """
   ```

### Working with AI: Argument-Based Changes

When you want to modify a plot, ask AI to change arguments, not code:

**✅ Good prompts:**

- "Change the line color to 'oc.red5'"
- "Increase linewidth to 1.2"
- "Set figsize to (12, 8)"
- "Add a title parameter and set it to 'My Plot'"

**❌ Bad prompts:**

- "Make the line a bit thicker"
- "Change the color slightly"
- "Adjust the figure size"
- "Make it look better"

Clear, argument-based requests are faster, more reliable, and less error-prone.

## 3. Rapid Iteration with Autoreload

The fastest way to develop plots with AI assistance is to work in a notebook environment with autoreload enabled. The key benefit of autoreload is that it **automatically updates changes from external Python files**, allowing you to modify functions in separate `.py` files and see results immediately in your notebook.

### Why Use External Python Files?

While you _can_ define functions directly in notebook cells, it's better to define visualization functions in separate `.py` files outside the notebook:

**Problems with defining functions in notebook cells:**

- AI assistants sometimes struggle to modify code within cells
- Cell-based code is harder to version control effectively
- Mixing function definitions and testing code makes the notebook cluttered
- Difficult to reuse functions across multiple notebooks

**Benefits of external `.py` files:**

- AI assistants work more reliably with separate Python files
- Better version control: track function changes independently
- Cleaner notebooks: notebooks focus on testing and visualization
- Reusable: import the same functions in multiple notebooks
- Easier collaboration: team members can work on functions and notebooks separately

### Recommended Workflow: Separate Files

**1. Create a Python file for your visualization functions** (`plotting.py`):

```python
# plotting.py
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

def plot_signal(
    data: np.ndarray,
    color: str = 'oc.blue5',
    linewidth: float = 0.7,
    figsize: tuple[float, float] | None = None
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot a signal with configurable styling.

    Parameters
    ----
    data : np.ndarray
        Signal data to plot.
    color : str, optional
        Line color. Default is 'oc.blue5'.
    linewidth : float, optional
        Line width. Default is 0.7.
    figsize : tuple[float, float] | None, optional
        Figure size in inches. If None, uses (9cm, 7cm).

    Returns
    ----
    fig : matplotlib.figure.Figure
        The created figure.
    ax : matplotlib.axes.Axes
        The axes containing the plot.
    """
    dm.style.use('scientific')

    if figsize is None:
        figsize = (dm.cm2in(9), dm.cm2in(7))

    fig = plt.figure(figsize=figsize, dpi=200)
    gs = fig.add_gridspec(
        nrows=1, ncols=1,
        left=0.17, right=0.95,
        top=0.95, bottom=0.17
    )
    ax = fig.add_subplot(gs[0, 0])

    x = np.arange(len(data))
    ax.plot(x, data, color=color, linewidth=linewidth)
    ax.set_xlabel('Time [s]', fontsize=dm.fs(0))
    ax.set_ylabel('Amplitude', fontsize=dm.fs(0))

    dm.simple_layout(fig)

    return fig, ax
```

**2. Use autoreload in your notebook to test the function**:

```python
# notebook.ipynb - Cell 1: Setup autoreload
%load_ext autoreload
%autoreload 2

import numpy as np
import dartwork_mpl as dm
from plotting import plot_signal  # Import from external file

# Cell 2: Generate test data
data = np.random.randn(100).cumsum()

# Cell 3: Test the function
fig, ax = plot_signal(data, color='oc.red5', linewidth=1.2)
dm.save_and_show(fig)
```

**3. Modify the function in `plotting.py` and see changes immediately**:

When you modify `plot_signal()` in `plotting.py`, autoreload automatically reloads the module. Just re-run the notebook cell to see the updated function—no kernel restart needed.

### Setup: Enable Autoreload

Enable autoreload at the start of your notebook with `%load_ext autoreload` and `%autoreload 2`. This automatically reloads all modules before executing code, so changes to external `.py` files are immediately reflected when you re-run notebook cells—no kernel restart needed.

### Use `save_and_show()` for Consistent Results

Always use `dm.save_and_show()` instead of `plt.show()` in your notebook cells. This function shows the actual saved result (matching your final exported figure) rather than just a preview, ensuring consistency between what you see in the notebook and what gets saved.

### Complete Workflow Example

Here's a complete example showing how to iterate on a visualization function:

**In `plotting.py`** (external file):

```python
# plotting.py
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

def plot_comparison(
    data1: np.ndarray,
    data2: np.ndarray,
    color1: str = 'oc.red5',
    color2: str = 'oc.blue5',
    linewidth: float = 0.7,
    title: str | None = None,
    figsize: tuple[float, float] | None = None
) -> tuple[plt.Figure, plt.Axes]:
    """Plot two signals for comparison."""
    # ... implementation (same as above) ...
```

**In notebook** (testing and iteration):

```python
# Cell 1: Setup
%load_ext autoreload
%autoreload 2
import numpy as np
import dartwork_mpl as dm
from plotting import plot_comparison

# Cell 2: Test with default arguments
data1 = np.random.randn(100).cumsum()
data2 = np.random.randn(100).cumsum() + 5
fig, ax = plot_comparison(data1, data2)
dm.save_and_show(fig)

# Cell 3: Iterate by changing arguments
fig, ax = plot_comparison(
    data1, data2,
    color1='oc.green5',  # Change argument
    color2='oc.orange5',  # Change argument
    linewidth=1.2,  # Change argument
    title='Comparison Plot'  # Add title
)
dm.save_and_show(fig)
```

When you modify `plot_comparison()` in `plotting.py` (add parameters, change defaults), autoreload automatically picks up the changes. Re-run notebook cells to see updates—no kernel restart needed.

### Benefits of This Workflow

This workflow combines the advantages of external files with rapid iteration:

- **Fast iteration**: Modify functions in external files, autoreload updates automatically, re-run cell to see results immediately
- **Consistent visualization**: `save_and_show()` ensures notebook output matches saved files
- **AI-friendly**: Clear, explicit argument changes that AI can understand and suggest
- **Version control friendly**: Track function changes independently in `.py` files, separate from notebook outputs
- **Reusable**: Import the same functions across multiple notebooks

## Summary: Best Practices

1. **Set up MCP server**: Add dartwork-mpl MCP server to your MCP settings file for automatic access to latest documentation

2. **Create plot functions with configurable arguments**:
   - Make all visual parameters configurable with sensible defaults
   - Use type hints and documentation
   - Define functions in external `.py` files (better AI compatibility and version control)

3. **Work in autoreload-enabled notebooks**:
   - Enable `%autoreload 2` to automatically reload external modules
   - Use `dm.save_and_show()` for consistent visualization
   - Iterate by changing function arguments, not modifying code

4. **Ask AI to change arguments, not code**:
   - ✅ "Change color to 'oc.red5'"
   - ❌ "Make it a bit redder"

Following these practices will make your AI-assisted graph development faster, more reliable, and more enjoyable.
