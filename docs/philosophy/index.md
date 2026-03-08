# Design Philosophy

dartwork-mpl takes a fundamentally different approach from typical visualization libraries. Instead of wrapping matplotlib with a new API layer, we provide **thin utilities** that enhance matplotlib's native capabilities while keeping you in full control.

This document explains the reasoning behind this design and how it benefits both human developers and AI coding agents.

## Core Ideas

| Traditional Wrappers                     | dartwork-mpl                                         |
| ---------------------------------------- | ---------------------------------------------------- |
| New API to learn                         | matplotlib API + thin utilities                      |
| Hidden transformations                   | Transparent operations                               |
| Dependency on library internals          | Copy-paste ready code                                |
| AI agents struggle with unfamiliar APIs  | AI agents work efficiently with familiar matplotlib  |
| "What does this function do internally?" | "I can read and understand the source in 30 seconds" |

Our goal is simple: matplotlib knowledge combined with minimal dartwork-mpl familiarity should be enough to create publication-quality visualizations with efficient AI assistance.

We believe the best library is one you could stop using tomorrow—by simply copying the utilities you need into your own codebase.

---

## The Problem with Wrapper Libraries

Most visualization libraries aim to reduce boilerplate by providing high-level abstractions:

```python
# Typical high-level library approach
chart = SomeLib.line_chart(
    data=df,
    x='date',
    y='value',
    theme='modern',
    title='My Chart',
    show_legend=True
)
chart.save('output.png')
```

While this looks convenient for simple cases, it creates several problems:

### Additional Abstraction Layers

Every wrapper library introduces a new layer between you and matplotlib. When you need to customize something beyond the library's API:

1. You must understand both the wrapper's API **and** matplotlib's API
2. You need to find escape hatches to access underlying matplotlib objects
3. The wrapper's design decisions may conflict with your requirements

### Diminishing Returns for Custom Visualizations

The more customized your visualization needs to be, the less value these wrappers provide:

```python
# When you need fine-grained control, wrappers become obstacles
chart = SomeLib.create_chart(data, theme='custom')
# How do I adjust the spine thickness?
# How do I add a secondary y-axis with specific formatting?
# How do I position a legend outside the plot area precisely?

# You end up doing this:
ax = chart.get_underlying_axes()  # escape hatch
ax.spines['top'].set_visible(False)  # back to matplotlib
# ... mixing two APIs becomes confusing
```

### AI Coding Agent Inefficiency

This is perhaps the most critical issue in modern development workflows. AI coding agents face significant challenges with wrapper libraries:

- **Training data scarcity**: Less popular libraries have fewer examples in training data
- **API uncertainty**: Agents may hallucinate non-existent methods or parameters
- **Internal behavior opacity**: Agents cannot reliably predict how wrappers transform their inputs
- **Version sensitivity**: Wrapper APIs change more frequently than matplotlib's stable core

### Dependency Anxiety

Users are often hesitant about third-party chart dependencies:

- What if the library is abandoned?
- What if an update breaks my existing code?
- Do I need to understand the entire codebase to use it safely?
- Can I debug issues without diving into unfamiliar source code?

**No one wants a dependency that requires understanding its entire internal codebase to use safely.**

---

## Why matplotlib Directly?

matplotlib is the foundation of Python visualization for good reasons:

### Predictable Behavior

matplotlib's API is well-documented and behaves consistently. When you write:

```python
ax.plot(x, y, color='red', linewidth=2)
ax.set_xlabel('Time [s]')
ax.set_xlim(0, 10)
```

You know exactly what will happen. There are no hidden transformations or automatic adjustments that might surprise you.

### Low-Level Control

Every aspect of your figure is accessible and adjustable:

```python
# Fine-grained control over every element
fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)
ax.spines['right'].set_visible(False)
ax.tick_params(axis='x', rotation=45, labelsize=8)
ax.annotate('Peak', xy=(5, 100), xytext=(6, 120),
            arrowprops=dict(arrowstyle='->', color='gray'))
```

### Extensive Documentation and Community

- Comprehensive official documentation with thousands of examples
- Decades of Stack Overflow answers
- Established patterns that AI coding agents understand well
- Stable API that rarely introduces breaking changes

### Agent-Friendly Code

Because matplotlib is well-represented in AI training data, coding agents can:

- Generate correct matplotlib code reliably
- Understand and modify existing matplotlib code
- Debug matplotlib issues effectively
- Suggest optimizations based on established patterns

---

## The shadcn/ui Approach

dartwork-mpl draws inspiration from [shadcn/ui](https://ui.shadcn.com/), a revolutionary approach in the frontend world.

### The shadcn/ui Philosophy

shadcn/ui is not a traditional component library. Instead of installing a package and importing components, you **copy the component code into your project**. This gives you:

- Full ownership and control over the code
- No dependency version conflicts
- Freedom to modify without forking
- Components that are just starting points, not black boxes

### Ownable Code

dartwork-mpl utilities are designed to be **ownable**. Consider our `simple_layout` function:

```python
def simple_layout(
    fig: Figure,
    gs: GridSpec | None = None,
    margins: tuple[float, float, float, float] = (0.05, 0.05, 0.05, 0.05),
    bbox: tuple[float, float, float, float] = (0, 1, 0, 1),
    ...
) -> OptimizeResult:
    """
    Optimize figure layout by adjusting GridSpec parameters.

    Uses scipy.optimize.minimize to find optimal margins.
    """
    if gs is None:
        gs = fig.axes[0].get_gridspec()

    def objective(x):
        gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])
        # Calculate bounding box and compare with targets
        ...

    result = minimize(objective, x0=initial_guess, bounds=bounds)
    return result
```

This function:

- Uses only standard libraries (scipy, matplotlib)
- Has no dartwork-mpl internal dependencies
- Can be copied directly into your project and modified
- Is completely transparent in its operation

### Copy-Paste Ready

Many dartwork-mpl utilities can be extracted and used standalone:

```python
# These can be copied into any project without dartwork-mpl

def cm2in(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54

def fs(n: int | float) -> float:
    """Return base font size + n."""
    return plt.rcParams["font.size"] + n

def mix_colors(color1, color2, alpha=0.5):
    """Mix two colors."""
    c1 = mcolors.to_rgb(color1)
    c2 = mcolors.to_rgb(color2)
    return tuple(alpha * a + (1 - alpha) * b for a, b in zip(c1, c2))
```

> **Roadmap:** We plan to add a pure-matplotlib export feature that resolves
> dartwork-mpl utilities (color names, `cm2in` values) into standard matplotlib
> code, so you can completely remove the dependency when needed.

---

## Design Principles

### Thin and Simple

Every utility should be as simple as possible:

```python
# Our approach: thin utility
def cm2in(cm: float) -> float:
    return cm / 2.54

# Not this: over-engineered abstraction
class UnitConverter:
    def __init__(self, source_unit, target_unit, precision=6):
        self.source = source_unit
        self.target = target_unit
        self.precision = precision

    def convert(self, value):
        # ... complex conversion logic
        pass
```

### Minimal Inter-Module Dependencies

Each utility should work independently:

```python
# Good: independent utilities
from dartwork_mpl import cm2in, fs, simple_layout
# Each function works without importing the others

# Avoid: tightly coupled modules where one requires many others
```

### Clarity Over Extensibility

We prioritize code that is easy to understand over code that handles every edge case:

```python
# Our approach: clear and focused
def fs(n: int | float) -> float:
    """Return base font size + n."""
    return plt.rcParams["font.size"] + n

# Not this: extensible but complex
def font_size(delta=0, unit='pt', relative_to='base',
              min_size=None, max_size=None, scale_factor=1.0):
    # ... 50 lines of handling edge cases
    pass
```

### Utilities, Not Wrappers

dartwork-mpl provides utilities that **enhance** matplotlib, not wrappers that **replace** it:

```python
# Wrapper approach (what we avoid):
dm_figure = dm.Figure(width=9, height=7, unit='cm')
dm_figure.plot(x, y, style='modern')
dm_figure.save('output.png')

# Our approach: utilities alongside standard matplotlib
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)))  # utility
ax = fig.add_subplot(111)
ax.plot(x, y, color='oc.red5')  # extended color names
dm.simple_layout(fig)  # utility
fig.savefig('output.png')  # standard matplotlib
```

---

## dartwork-mpl in Practice

### You're Still Writing matplotlib

With dartwork-mpl, your code remains fundamentally matplotlib code:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# Apply style (sets rcParams, nothing more)
dm.style.use('scientific')

# Standard matplotlib figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)
gs = fig.add_gridspec(nrows=1, ncols=1,
                      left=0.17, right=0.95, top=0.95, bottom=0.17)
ax = fig.add_subplot(gs[0, 0])

# Standard matplotlib plotting
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color='oc.red5', linewidth=0.7)  # only color is extended
ax.set_xlabel('Time [s]')
ax.set_ylabel('Amplitude')
ax.legend(fontsize=dm.fs(-1))  # utility for relative font size

# Utility for layout optimization
dm.simple_layout(fig)

# Standard matplotlib or utility for saving
dm.save_and_show(fig)
```

Every line is recognizable matplotlib. The dartwork-mpl additions are clearly utilities, not replacements.

### Minimal Learning Curve

To use dartwork-mpl effectively, you need:

1. **matplotlib knowledge** (which you likely already have)
2. **A few utility functions**: `cm2in`, `fs`, `fw`, `simple_layout`, `save_and_show`
3. **Color name extensions**: `oc.*`, `tw.*` prefixes

That's it. No new plotting paradigm to learn.

### Vibe Coding and AI Assistance

dartwork-mpl is designed for modern AI-assisted development workflows:

**Context prompts over predefined functions**: Instead of memorizing a library of specialized plot functions, you can describe what you want to an AI coding agent:

```
"Create a publication-quality line plot with two y-axes,
use dartwork-mpl's scientific style, and optimize the layout"
```

The agent can generate correct code because:

- The underlying matplotlib API is well-known
- dartwork-mpl utilities are simple and well-documented
- There are no hidden behaviors to account for

**Efficient collaboration with AI agents**:

```python
# AI agents can reliably generate this because it's standard matplotlib
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)))
ax.plot(data['x'], data['y'], color='oc.blue5', label='Measurement')
ax.fill_between(data['x'], data['y_low'], data['y_high'],
                color='oc.blue2', alpha=0.3, label='Confidence')
ax.set_xlabel('Time [hours]')
ax.set_ylabel('Temperature [°C]')
ax.legend(loc='upper right', fontsize=dm.fs(-1))
dm.simple_layout(fig)
```

### No Black Boxes

When something doesn't work as expected, you can:

1. **Inspect the utility source**: Our utilities are short and readable
2. **Debug with standard tools**: Everything is matplotlib under the hood
3. **Copy and modify**: Extract the utility, adjust it for your needs
4. **Skip the utility entirely**: Use pure matplotlib if preferred

---

## Summary

dartwork-mpl is a library you can adopt incrementally and leave at any time.
You keep writing standard matplotlib — we just supply curated styles, named
colors, and a handful of utilities that are simple enough to copy into your
project. This approach works for human developers who want full control and for
AI coding agents that perform best with familiar APIs.
