# dartwork-mpl: matplotlib utilities and assets library engineered by dartwork

`dartwork-mpl` is a sophisticated utility collection designed to elevate `matplotlib` visuals to publication-level elegance with added convenience features. It is being developed to resolve personal inconveniences in visualization using matplotlib and to provide more intuitive customization especially to beginners.
<br/>

## Features

`dartwork-mpl` enriches plotting experience with:

- **Enhanced Aesthetics**: Apply our curated themes to make your charts visually appealing.
- **Easy Customization**: Effortlessly adjust plot styles to fit your publication's needs.
- **Advanced Color System**: Use custom colors with simple prefixes (`oc.`, `tw.`) and extended Tailwind CSS palette.
- **Icon Font System**: Built-in Material Design Icons (MDI) and Font Awesome 6 for data-rich visualizations.
- **Streamlined Workflow**: Simplify your plotting code with our intuitive interface, saving time and reducing complexity.
- **Publication-Ready Layout**: Automatic layout optimization with `simple_layout()` for professional results.
  <br/>

## Getting Started

### Installation

#### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. To install `dartwork-mpl` with uv:

```shell
# Add to your project
uv add git+https://github.com/dartworklabs/dartwork-mpl

# Or install directly
uv pip install git+https://github.com/dartworklabs/dartwork-mpl
```

#### Using pip

```shell
pip install git+https://github.com/dartworklabs/dartwork-mpl
```

### Quick Start

After installation, import and apply a style preset:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# Apply scientific publication style
dm.style.use('scientific')

# For Korean text support
dm.style.use('scientific-kr')
```

<br/>

## Core Features

### Style Management

- **Preset Styles**: Ready-to-use presets for scientific papers, presentations, and reports
- **Flexible Customization**: Combine individual styles for fine-grained control
- **Korean Language Support**: Built-in Korean font support with `-kr` presets

### Color System

- **dartwork-mpl Colors**: Custom color palette with `oc.red5`, `oc.blue2`, etc.
- **Tailwind CSS Integration**: Full Tailwind palette with `tw.blue500`, `tw.gray200`, etc.
- **Color Utilities**: Mix colors and apply pseudo-transparency

### Layout & Utilities

- **Smart Layout Optimization**: `simple_layout()` replaces `tight_layout()` with better control
- **Unit Conversion**: `cm2in()` for precise figure sizing
- **Multi-format Export**: Save figures in SVG, PNG, PDF, and EPS simultaneously
- **Font Utilities**: Relative font size (`fs()`) and weight (`fw()`) adjustments

### Icon Font System

- **Material Design Icons (MDI)**: 7,448+ icons built-in as the default icon library
- **Font Awesome 6**: Solid, Regular, and Brands variants included as fallback
- **Simple API**: `icon_font('mdi')` returns a ready-to-use `FontProperties` object
- **Path Access**: `icon_font_path('mdi')` for direct file path when needed

### Visualization Tools

- **Colormap Explorer**: Preview and classify colormaps by type
- **Color Palette Viewer**: Display all available colors with names
- **Font Gallery**: Preview available fonts

<br/>

## Example Usage

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# Set style
dm.style.use('scientific')

# Create figure with precise sizing (single-column paper figure)
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# Set up layout
gs = fig.add_gridspec(nrows=1, ncols=1,
                      left=0.17, right=0.95,
                      top=0.95, bottom=0.17)
ax = fig.add_subplot(gs[0, 0])

# Plot with custom colors
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), c='oc.red5', lw=0.7, label='Sin')
ax.plot(x, np.cos(x), c='tw.blue500', lw=0.7, label='Cos')

# Customize
ax.set_xlabel('X value')
ax.set_ylabel('Y value')
ax.legend(fontsize=dm.fs(-1))

# Optimize layout and save
dm.simple_layout(fig)
dm.save_and_show(fig)  # Display in Jupyter

# Export in multiple formats
dm.save_formats(fig, 'output/figure',
                formats=('svg', 'png', 'pdf', 'eps'),
                dpi=600)
```

<br/>

## Documentation

📚 **[Full Documentation](https://dartworklabs.github.io/dartwork-mpl/)** - Complete Sphinx documentation with:

- **[Usage Guide](https://dartworklabs.github.io/dartwork-mpl/DARTWORK_MPL_USAGE_GUIDE.html)** - Comprehensive guide to all features
- **[Example Gallery](https://dartworklabs.github.io/dartwork-mpl/gallery/index.html)** - Interactive examples with code and plots
- **[Color System](https://dartworklabs.github.io/dartwork-mpl/COLOR_SYSTEM.html)** - Full-width Colors and Colormaps reference
- **[API Reference](https://dartworklabs.github.io/dartwork-mpl/API_REFERENCE.html)** - Detailed API documentation

<br/>

## Example Gallery

Explore our comprehensive [example gallery](https://dartworklabs.github.io/dartwork-mpl/gallery/index.html) featuring:

- **Basic Usage** - Getting started with dartwork-mpl
- **Color System** - Custom colors and Tailwind CSS integration
- **Layout Optimization** - Advanced layout control with `simple_layout()`
- **Scientific Figures** - Multi-panel publication-ready plots
- **Statistical Plots** - Probability density, violin, and box plots
- **Advanced Visualizations** - Heatmaps, contours, streamplots, and 3D plots

Each example includes complete source code and rendered output.

<br/>

## Available Presets

| Preset            | Description                            |
| ----------------- | -------------------------------------- |
| `scientific`      | Small fonts for academic papers        |
| `presentation`    | Large fonts for presentations          |
| `investment`      | Style for investment reports           |
| `scientific-kr`   | Scientific style with Korean support   |
| `presentation-kr` | Presentation style with Korean support |
| `investment-kr`   | Investment style with Korean support   |

### Icon Fonts

```python
import dartwork_mpl as dm

# Load icon font (returns FontProperties)
mdi = dm.icon_font('mdi')          # Material Design Icons (default)
fa  = dm.icon_font('fa-solid')     # Font Awesome 6 Solid

# Render icon in a plot
ax.text(0.5, 0.5, "\U000F050F",    # MDI: thermometer
        fontproperties=mdi, fontsize=20)

# List available icon fonts
dm.list_icon_fonts()  # ['fa-brands', 'fa-regular', 'fa-solid', 'mdi']
```

<br/>

## AI-Assisted Development

dartwork-mpl provides an **MCP (Model Context Protocol) server** that enables AI coding assistants like Cursor, GitHub Copilot, and Claude Code to automatically access the latest dartwork-mpl documentation and guidelines.

### Why Use MCP?

- **Automatic access**: AI assistants can directly access the latest dartwork-mpl documentation
- **No manual updates**: Documentation updates are automatically available to your AI assistant
- **Seamless integration**: Works seamlessly with Cursor and other MCP-compatible AI assistants
- **Always up-to-date**: Your AI assistant always has access to the latest library information

### Setup Instructions

To use dartwork-mpl's MCP server with Cursor, add the following configuration to your MCP settings file:

```json
{
  "mcpServers": {
    "dartwork-mpl": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/dartworklabs/dartwork-mpl.git#egg=dartwork-mpl[mcp]",
        "mcp"
      ]
    }
  }
}
```

After adding this configuration, your AI assistant will have automatic access to dartwork-mpl's documentation and guidelines.

For more details on AI-assisted development best practices, see the [AI-Assisted Development Guide](https://dartworklabs.github.io/dartwork-mpl/usage_guide/ai_assisted.html).

<br/>

## Reporting Issues

Encountered a bug or have a feature request? Please open an issue through our [GitHub issue tracker](https://github.com/dartworklabs/dartwork-mpl/issues). We appreciate your feedback and contributions.
