# dartwork-mpl Usage Guide

> A publication-quality matplotlib styling and visualization toolkit.

## Quick Start

```python
import dartwork_mpl as dm

# Apply a style preset
dm.style.use("scientific")          # academic papers
dm.style.use("report-kr")            # Korean reports

# Scale helpers (relative to rcParams base)
font_size = dm.fs(0)    # base font size
bold = dm.fw(1)         # bold weight
line_w = dm.lw(0)       # base line width
```

## Core API

### Styling

```python
dm.style.use("scientific")          # apply preset
dm.list_styles()                    # available presets
dm.load_style_dict("scientific")    # get raw dict
```

### Saving Figures

```python
dm.save_formats(fig, "output/chart", formats=("png", "svg"), dpi=300)
dm.save_and_show(fig, path="output/chart")
dm.simple_layout(fig)               # optimize whitespace
```

### Color System

```python
from dartwork_mpl import Color

# Named colors with library prefixes
c = Color.named("oc.blue5")        # OpenColor
c = Color.named("tw.sky500")       # Tailwind

# Color mixing
blended = dm.mix_colors("oc.blue5", "oc.red5", alpha=0.5)
faded = dm.pseudo_alpha("oc.blue5", 0.3)

# OKLab/OKLCH perceptual color space
dm.oklab(0.6, -0.1, 0.1)
dm.oklch(0.6, 0.15, 250)
```

### Annotations

```python
dm.label_axes(axes, labels="auto")  # (a), (b), (c)...
dm.arrow_axis(ax, direction="right", label="Time")
```

### Unit Conversion

```python
dm.cm2in(16)   # 16 cm → inches for figsize
```

### Colormaps

```python
dm.cmap.ensure_loaded()   # register all custom colormaps
dm.classify_colormap(cmap)
dm.plot_colormaps()        # visual gallery
```

### Colors Visualization

```python
dm.plot_colors()           # show all named colors
dm.plot_fonts()            # show available fonts
```

### Extended Plots

```python
from dartwork_mpl.xplot import plot_diverging_bar

fig, ax = plot_diverging_bar(
    labels=["A", "B", "C"],
    neg_values=np.array([-10, -20, -15]),
    pos_values=np.array([30, 25, 40]),
)
```

### Prompt Guides

```python
dm.list_prompts()                               # list available
dm.get_prompt("chart_generation")               # read content
dm.copy_prompt("chart_generation", "out.md")    # copy to file
```

### Figure Validation

```python
dm.validate_figure(fig)    # check overflow, overlap, crowding
```

## Available Style Presets

| Preset       | Use Case        |
| ------------ | --------------- |
| `scientific` | Academic papers |
| `report`     | English reports |
| `report-kr`  | Korean reports  |

## Tips

- Always call `dm.simple_layout(fig)` instead of `plt.tight_layout()`
- Use `dm.save_formats()` for multi-format export (PNG + SVG)
- Prefix colors: `oc.` (OpenColor), `tw.` (Tailwind), `md.` (Material)
- Use `dm.fs(n)` for relative font sizing (`n=0` is base)
