# dartwork-mpl Library Usage Guide

## 1. Installation and Basic Setup

### Installation

#### Using pip

```bash
pip install git+https://github.com/dartworklabs/dartwork-mpl
```

#### Using uv (Recommended)

```bash
# Add to project
uv add git+https://github.com/dartworklabs/dartwork-mpl

# Or specify a specific branch/tag
uv add git+https://github.com/dartworklabs/dartwork-mpl@main
```

### Basic Import

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

# Apply default style (recommended)
dm.style.use('scientific')  # Default style for papers
```

## 2. Main Features

### 2.1 Style Management

#### Check Available Styles

```python
# List all individual styles
dm.list_styles()
# ['base', 'dmpl', 'dmpl_light', 'font-report', 'font-presentation',
#  'font-scientific', 'lang-kr', 'spine-no', 'spine-yes']

# Check available presets
dm.style.presets_dict()
# {'scientific': ['base', 'font-scientific'],
#  'report': ['base', 'font-report'],
#  'presentation': ['base', 'font-presentation'],
#  'scientific-kr': ['base', 'font-scientific', 'lang-kr'],
#  'report-kr': ['base', 'font-report', 'lang-kr'],
#  'presentation-kr': ['base', 'font-presentation', 'lang-kr']}
```

#### Apply Styles

```python
# Use presets (recommended)
dm.style.use('scientific')  # For papers
dm.style.use('presentation')  # For presentations
dm.style.use('scientific-kr')  # For Korean papers

# Combine individual styles (for advanced users)
dm.style.stack(['base', 'spine-no', 'font-presentation'])
```

#### Check Style Contents

```python
# Check style file contents
style_dict = dm.load_style_dict('font-presentation')

# Check style file path
path = dm.style_path('base')

# Preset definition file path
preset_path = dm.style.presets_path()
```

### 2.2 Color System

#### dartwork-mpl Custom Colors

```python
# Use with dm. prefix
ax.plot(x, y, color='oc.red5')
ax.scatter(x, y, c='oc.blue2')
```

#### Tailwind CSS Colors

```python
# Use tw. prefix
# Format: tw.{color}{weight}
ax.plot(x, y, color='tw.blue500')
ax.fill_between(x, y1, y2, color='tw.gray200')
```

#### Color Utilities

```python
# Mix two colors
mixed = dm.mix_colors('oc.red5', 'oc.blue5', alpha=0.5)

# Apply pseudo-transparency (mix with background color)
transparent = dm.pseudo_alpha('oc.red5', alpha=0.3, background='white')
```

### 2.3 Layout Utilities

#### Recommended Figure Creation Pattern

```python
# Create figure for papers (unit conversion: cm → inch)
# Single column figure: 9cm width
fig = plt.figure(
    figsize=(dm.cm2in(9), dm.cm2in(7)),
    dpi=200
)

# Double column figure: 17cm width
fig = plt.figure(
    figsize=(dm.cm2in(17), dm.cm2in(7)),
    dpi=200
)

# Set layout with GridSpec
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17,
    hspace=0.3, wspace=0
)
ax = fig.add_subplot(gs[0, 0])
```

#### Automatic Layout Adjustment

`simple_layout` is an improved version of `plt.tight_layout()` that provides more precise margin control and predictable results.

```python
# Basic usage (recommended)
dm.simple_layout(fig)

# Adjust margins (in inches: left, right, bottom, top)
dm.simple_layout(fig, margins=(0.1, 0.05, 0.1, 0.05))

# Apply only to specific GridSpec
dm.simple_layout(fig, gs=gs, margins=(0.08, 0.02, 0.08, 0.02))

# Partial region optimization using bbox (figure coordinates: left, right, bottom, top)
# Entire figure (default)
dm.simple_layout(fig, bbox=(0, 1, 0, 1))

# Optimize only left half of figure
dm.simple_layout(fig, bbox=(0, 0.5, 0, 1))

# Optimize only right half of figure
dm.simple_layout(fig, bbox=(0.5, 1, 0, 1))

# Optimize only top half of figure
dm.simple_layout(fig, bbox=(0, 1, 0.5, 1))

# Apply to all axes (when multiple GridSpecs exist)
dm.simple_layout(fig, use_all_axes=True)
```

**Key Parameters:**

- `margins`: Margins in inches (left, right, bottom, top)
- `bbox`: Target region for optimization in figure coordinates (left, right, bottom, top)
- `gs`: Specify a GridSpec (uses first GridSpec if None)
- `use_all_axes`: If True, considers all axes (default: False)

**bbox Usage Example:**
When there are multiple subplots, you can optimize the layout of specific regions individually. For example, setting `bbox=(0, 0.5, 0, 1)` will perform layout optimization only for the left half of the figure.

### 2.4 Font Utilities

```python
# Adjust relative font size
title_size = dm.fs(2)   # base font size + 2
label_size = dm.fs(-1)  # base font size - 1

# Adjust font weight (in units of 100)
bold_weight = dm.fw(2)  # base weight + 200

# Usage example
ax.set_title('Title', fontsize=dm.fs(2), fontweight=dm.fw(1))
ax.legend(fontsize=dm.fs(-2))
```

### 2.5 Save and Display

#### Save in Multiple Formats

```python
# Save in multiple formats simultaneously
dm.save_formats(
    fig,
    'output/figure',  # without extension
    formats=('svg', 'png', 'pdf', 'eps'),
    bbox_inches='tight',
    dpi=600
)
```

#### Save and Display in Jupyter

```python
# Use instead of plt.show() - saves to temp file and displays immediately (recommended)
dm.save_and_show(fig, size=600)

# Save to specific path and display
dm.save_and_show(fig, 'output/figure.svg', size=600)

# Display existing file
dm.show('output/figure.svg', size=600)
```

### 2.6 Subplot Labeling

```python
# Add subplot labels (a, b, c...)
axs = [ax1, ax2]
for ax, label in zip(axs, 'ab'):
    # Always use make_offset function when setting text offset
    offset = dm.make_offset(4, -4, fig)  # x=4pt, y=-4pt
    ax.text(
        0, 1, label,
        transform=ax.transAxes + offset,
        weight='bold',
        verticalalignment='top'
    )
```

**Important**: Always use the `dm.make_offset()` function when adjusting text position. This function provides accurate offsets in point (pt) units, ensuring consistent results regardless of DPI.

### 2.7 Colormap Visualization

```python
# Check available colormaps
fig, axs = dm.plot_colormaps(
    cmap_list=['viridis', 'dc.spectral'],  # None for all
    ncols=3,
    group_by_type=True  # Group by type
)

# Check color palette
fig = dm.plot_colors()  # Display all colors

# Check fonts
fig = dm.plot_fonts()  # Display available fonts
```

## 3. Agent Best Practices

### 3.1 For AI Agents and Automated Code Generation

When using dartwork-mpl in automated contexts (AI agents, code generators, etc.), follow these guidelines:

#### Quick Start Template

```python
# Standard imports and setup
import matplotlib
matplotlib.use("Agg")  # Required for headless environments
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm
from pathlib import Path

# Apply style first
dm.style.use("report-kr")  # Choose appropriate style

# Create output directory
OUTPUT_DIR = Path("figures/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Generate chart
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.6), dpi=200)
gs = fig.add_gridspec(1, 1, left=0.15, right=0.95, top=0.9, bottom=0.15)
ax = fig.add_subplot(gs[0, 0])

# Your plotting code here...

# Save and close
dm.auto_layout(fig)
dm.save_formats(fig, OUTPUT_DIR / "chart_name", formats=("png",), dpi=300)
plt.close(fig)
```

#### Using Helper Functions

```python
from dartwork_mpl.agent_utils import (
    validate_data,
    auto_select_colors,
    format_axis_labels,
    save_figure,
    check_figure_quality
)

# Validate input data
x, y = validate_data(x_data, y_data, allow_nan=False)

# Auto-select appropriate colors
colors = auto_select_colors(n_series=3, color_type="categorical")

# Apply consistent formatting
format_axis_labels(ax, "Time", "Revenue", y_unit="억원")

# Check quality before saving
issues = check_figure_quality(fig)
if issues:
    print("Warning: Quality issues detected:", issues)
```

#### Using Chart Templates

```python
from dartwork_mpl.templates.financial import (
    create_dual_axis_chart,
    create_waterfall_chart
)

# Use pre-built templates for common patterns
fig, (ax1, ax2) = create_dual_axis_chart(
    quarters, revenue, margins,
    bar_label="Revenue", line_label="Margin"
)
```

### 3.2 Common Agent Pitfalls to Avoid

1. **Forgetting to set style**: Always apply style before creating figures
2. **Using matplotlib defaults**: Never use 'b', 'r', 'g' colors
3. **Missing units**: Always include units in axis labels
4. **Low DPI**: Always use at least 200 DPI
5. **Using tight_layout**: Use `dm.auto_layout()` instead
6. **Not validating data**: Always check for NaN/Inf values
7. **Hardcoding positions**: Use GridSpec for layout management

### 3.3 Refer to Additional Resources

- **Coding Rules**: See `coding-rules.md` for detailed agent guidelines
- **Templates**: Check `templates/` module for ready-to-use chart patterns
- **Utilities**: Use `agent_utils.py` for common helper functions

## 4. Recommended Workflow (Manual)

### Steps for Creating Publication-Quality Graphs

1. **Separate Data Preparation and Plot Code**

```python
# Data preparation cell
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Plot cell (separate)
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)))
# ...
```

2. **GridSpec-Based Layout**

```python
gs = fig.add_gridspec(
    nrows=2, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17,
    hspace=0.3
)
```

3. **Handle-Based Legend**

```python
line1, = ax.plot(x, y1, color='oc.red5', lw=0.7)
scatter1 = ax.scatter([], [], c='oc.red5', s=1)  # dummy for legend
ax.legend([scatter1, line1], ['Data', 'Model'])
```

4. **Explicit Tick Settings**

```python
ax.set_xticks([0, 2, 4, 6, 8, 10])
ax.set_yticks([-1, -0.5, 0, 0.5, 1])
```

5. **Verify Based on Saved File**

```python
# Use instead of plt.show() - can verify actual saved result
dm.save_and_show(fig)
```

## 4. Korean Language Support

```python
# Apply Korean font
dm.style.stack(['base', 'lang-kr'])

# Or use preset (recommended)
dm.style.use('scientific-kr')
```

## 5. Preset Styles

Available presets:

- `scientific`: For papers (small font)
- `report`: For reports and dashboards
- `presentation`: For presentations (large font)
- `scientific-kr`, `report-kr`, `presentation-kr`: Korean versions

## 6. Notes

1. **Avoid tight_layout**: Use `dm.simple_layout()` instead
2. **Work based on savefig**: Work based on saved files, not `plt.show()`
3. **Check units**: matplotlib uses various units (inch, point, pixel)
4. **Color naming**: Use prefix `oc.`, `tw.`, `dc.`, `md.`, etc.

## 7. Complete Example

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# Style setup
dm.style.use('scientific')

# Data generation
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)
y1_data = y1 + np.random.normal(0, 0.1, size=len(y1))
y2_data = y2 + np.random.normal(0, 0.1, size=len(y2))

# Figure creation
fig = plt.figure(
    figsize=(dm.cm2in(9), dm.cm2in(7)),
    dpi=200
)

# GridSpec layout
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17
)
ax = fig.add_subplot(gs[0, 0])

# Data plotting
line1, = ax.plot(x, y1, c='oc.red5', lw=0.7)
line2, = ax.plot(x, y2, c='oc.blue5', lw=0.7)
ax.scatter(x, y1_data, c='oc.red2', s=0.7)
ax.scatter(x, y2_data, c='oc.blue2', s=0.7)

# Dummy plots for legend
scatter1 = ax.scatter([], [], c='oc.red5', s=10)
scatter2 = ax.scatter([], [], c='oc.blue5', s=10)

# Labels and legend
ax.set_xlabel('X value [Hour]')
ax.set_ylabel('Y value [kW]')
ax.legend(
    [scatter1, line1, scatter2, line2],
    ['Sin data', 'Sin model', 'Cos data', 'Cos model'],
    loc='upper right',
    fontsize=dm.fs(-1),
    ncol=2
)

# Tick settings
ax.set_xticks([0, 2, 4, 6, 8, 10])
ax.set_yticks([-1, -0.5, 0, 0.5, 1])
ax.set_ylim(-1.2, 1.2)

# Layout optimization
dm.simple_layout(fig)

# Preview in Jupyter
dm.save_and_show(fig)

# Save in multiple formats for paper submission
dm.save_formats(
    fig,
    'figures/example_figure',  # base filename without extension
    formats=('svg', 'png', 'pdf', 'eps'),  # Save all 4 formats
    bbox_inches='tight',
    dpi=600
)
```
