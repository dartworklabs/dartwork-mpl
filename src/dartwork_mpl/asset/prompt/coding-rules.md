# dartwork-mpl Agent Coding Rules

## 1. Essential Import Pattern

Always start with this standard import pattern:

```python
import matplotlib
matplotlib.use("Agg")  # Required for headless environments
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm
from pathlib import Path

# Apply style BEFORE creating any figures
dm.style.use("report-kr")  # or "scientific", "presentation", etc.
```

## 2. Style Selection Guide

### When to use each preset:

| Preset | Use Case | Font Size | Best For |
|--------|----------|-----------|----------|
| `scientific` | Academic papers, journals | Small | Dense information, multiple subplots |
| `scientific-kr` | Korean academic papers | Small | Korean text with scientific notation |
| `report` | Business reports, dashboards | Medium | Balance readability and density |
| `report-kr` | Korean business reports | Medium | Korean corporate reports |
| `presentation` | Slides, posters | Large | Maximum readability from distance |
| `presentation-kr` | Korean presentations | Large | Korean presentation materials |

## 3. Figure Creation Pattern

### Standard Figure Setup

```python
# Single column figure (9cm width for papers)
fig = plt.figure(
    figsize=(dm.cm2in(9), dm.cm2in(7)),
    dpi=200
)

# Double column figure (17cm width)
fig = plt.figure(
    figsize=(dm.cm2in(17), dm.cm2in(7)),
    dpi=200
)

# Dashboard/report figure (use constants)
fig = plt.figure(
    figsize=(dm.DW, dm.DW * 0.6),  # DW = default width
    dpi=200
)
```

### Always Use GridSpec

```python
# Never use plt.subplots() directly
# Always use GridSpec for precise control
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17,
    hspace=0.3, wspace=0.3
)
ax = fig.add_subplot(gs[0, 0])
```

## 4. Color Usage Rules

### Color Selection Priority

1. **Named colors**: Use dartwork colors with prefixes
   ```python
   color="oc.red5"    # OpenColor palette
   color="tw.blue500" # Tailwind CSS palette
   color="dc.spectral" # Dartwork custom
   ```

2. **Never use**: matplotlib defaults ("b", "r", "g")

3. **Color consistency**:
   - Primary data: `oc.blue5` or `oc.blue6`
   - Secondary data: `oc.red5` or `oc.orange5`
   - Neutral/reference: `oc.gray5` to `oc.gray7`
   - Gridlines: `oc.gray3`

### Semantic Color Mapping

```python
# Financial charts
COLORS = {
    "positive": "oc.blue5",    # Profits, gains
    "negative": "oc.red5",     # Losses, declines
    "neutral": "oc.gray5",     # Reference lines
    "forecast": "oc.orange5",  # Projections
    "highlight": "oc.blue7",   # Emphasis
}
```

## 5. Layout Optimization Rules

### Auto-layout Usage

```python
# ALWAYS use auto_layout instead of tight_layout
dm.auto_layout(fig)  # Content-aware margin adjustment

# For manual fine-tuning after auto_layout
fig.subplots_adjust(bottom=0.15)  # If needed
```

### Never use:
- `plt.tight_layout()`
- `fig.tight_layout()`
- Manual bbox calculations

## 6. Typography Rules

### Font Size Adjustments

```python
# Use relative sizing from base
ax.set_title("Title", fontsize=dm.fs(2))    # base + 2pt
ax.set_xlabel("X Label", fontsize=dm.fs(0)) # base size
ax.legend(fontsize=dm.fs(-1))               # base - 1pt

# Font weight adjustments
ax.text(x, y, "Bold", fontweight=dm.fw(1))  # base + 100
```

### Label Formatting

```python
# Numbers on charts - always include units
ax.set_ylabel("Revenue (억원)")
ax.set_xlabel("Quarter")

# Data labels - use consistent precision
for val in values:
    ax.text(x, y, f"{val:.1f}%")  # One decimal
    ax.text(x, y, f"{val:,.0f}")  # Thousands separator
```

## 7. Axis and Tick Rules

### Always Set Explicit Ticks

```python
# Bad: Let matplotlib auto-decide
# Good: Explicit control
ax.set_xticks([0, 2, 4, 6, 8, 10])
ax.set_yticks([0, 25, 50, 75, 100])

# For time series
quarters = ["Q1'24", "Q2'24", "Q3'24", "Q4'24"]
ax.set_xticks(range(len(quarters)))
ax.set_xticklabels(quarters)
```

### Spine Management

```python
# Default: hide right and top spines
ax.spines["right"].set_visible(False)
ax.spines["top"].set_visible(False)

# Exception: dual y-axis (twinx automatically shows right spine)
ax2 = ax.twinx()
# Right spine is auto-configured by dartwork-mpl
```

## 8. Legend Best Practices

### Positioning

```python
# Priority order for legend placement:
# 1. Outside plot area (for complex charts)
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

# 2. Inside with transparency (for simple charts)
ax.legend(loc="upper right", framealpha=0.9)

# 3. Use dummy plots for custom legends
scatter_dummy = ax.scatter([], [], c="oc.red5", s=50)
line_dummy, = ax.plot([], [], c="oc.blue5", lw=2)
ax.legend([scatter_dummy, line_dummy], ["Data", "Model"])
```

## 9. Data Validation Rules

### Always Validate Input Data

```python
# Check for None/empty
if data is None or len(data) == 0:
    raise ValueError("No data provided")

# Check data alignment
if len(x) != len(y):
    raise ValueError(f"Data length mismatch: x({len(x)}) != y({len(y)})")

# Handle NaN/Inf
if np.any(np.isnan(data)) or np.any(np.isinf(data)):
    # Clean or raise error
    data = np.nan_to_num(data, nan=0.0)
```

## 10. Save and Output Rules

### Standard Save Pattern

```python
# Create output directory
OUTPUT_DIR = Path("figures/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Save in multiple formats
dm.save_formats(
    fig,
    OUTPUT_DIR / "chart_name",  # No extension
    formats=("png", "svg", "pdf"),
    dpi=300,
    bbox_inches="tight"
)

# Always close figure to free memory
plt.close(fig)

# Print confirmation
print(f"✓ Generated: chart_name.png")
```

## 11. Common Mistakes to Avoid

### ❌ DON'T DO THIS:

```python
# Don't use matplotlib defaults
plt.plot(x, y, 'b-')  # Bad

# Don't forget to set style
fig = plt.figure()  # Style not set!

# Don't use tight_layout
plt.tight_layout()  # Use dm.auto_layout instead

# Don't hardcode positions
ax.text(0.5, 0.98, "Title")  # Use GridSpec instead

# Don't forget units
ax.set_ylabel("Revenue")  # Missing unit!

# Don't use low DPI
fig.savefig("chart.png", dpi=72)  # Too low!
```

### ✅ DO THIS INSTEAD:

```python
# Use named colors
ax.plot(x, y, color="oc.blue5", linewidth=0.7)

# Set style first
dm.style.use("report")
fig = plt.figure()

# Use auto_layout
dm.auto_layout(fig)

# Use GridSpec for complex layouts
gs = fig.add_gridspec(...)

# Include units
ax.set_ylabel("Revenue (억원)")

# High quality output
dm.save_formats(fig, "chart", dpi=300)
```

## 12. Chart Type Templates

### Financial Time Series

```python
def create_financial_chart(quarters, revenue, profit):
    fig = plt.figure(figsize=(dm.DW, dm.DW * 0.5))
    gs = fig.add_gridspec(1, 1, left=0.15, right=0.95, top=0.9, bottom=0.15)
    ax = fig.add_subplot(gs[0, 0])

    # Bar for revenue
    bars = ax.bar(quarters, revenue, color="oc.blue5", width=0.6, alpha=0.9)

    # Line for profit margin
    ax2 = ax.twinx()
    ax2.plot(quarters, profit, color="oc.red5", marker="o", linewidth=1.5)

    # Styling
    ax.set_ylabel("Revenue (억원)")
    ax2.set_ylabel("Profit Margin (%)", color="oc.red5")
    ax2.tick_params(axis="y", labelcolor="oc.red5")

    dm.auto_layout(fig)
    return fig, (ax, ax2)
```

### Comparison Charts

```python
def create_peer_comparison(companies, metrics):
    fig = plt.figure(figsize=(dm.DW * 0.8, dm.DW * 0.5))
    gs = fig.add_gridspec(1, 1, left=0.15, right=0.95, top=0.9, bottom=0.2)
    ax = fig.add_subplot(gs[0, 0])

    x = np.arange(len(companies))
    width = 0.6

    colors = ["oc.blue5" if c == "target" else "oc.gray5" for c in companies]
    bars = ax.bar(x, metrics, width, color=colors, alpha=0.9)

    # Add value labels
    for i, val in enumerate(metrics):
        ax.text(i, val + max(metrics)*0.02, f"{val:.1f}",
                ha="center", va="bottom", fontsize=dm.fs(-1))

    ax.set_xticks(x)
    ax.set_xticklabels(companies, rotation=45, ha="right")

    dm.auto_layout(fig)
    return fig, ax
```

## 13. Performance Optimization

### For Large Datasets

```python
# Use rasterization for many points
ax.scatter(x, y, s=0.5, alpha=0.3, rasterized=True)

# Downsample if needed
if len(data) > 10000:
    indices = np.random.choice(len(data), 10000, replace=False)
    data = data[indices]

# Set reasonable limits
ax.set_xlim(data.min() * 0.95, data.max() * 1.05)
```

## 14. Error Handling Pattern

```python
try:
    # Chart generation code
    fig = create_chart(data)
    dm.save_formats(fig, output_path)
except ValueError as e:
    print(f"Data error: {e}")
    # Provide helpful context
    print(f"Data shape: {data.shape if hasattr(data, 'shape') else len(data)}")
except Exception as e:
    print(f"Unexpected error: {e}")
    # Clean up resources
    plt.close("all")
finally:
    # Always close figures
    if 'fig' in locals():
        plt.close(fig)
```

## 15. Testing Your Charts

### Quick Validation Checklist

```python
def validate_chart(fig):
    """Run basic validation checks."""
    checks = []

    # Check DPI
    if fig.dpi < 150:
        checks.append("⚠️ Low DPI detected")

    # Check if style was applied
    if plt.rcParams["font.size"] == 10:  # Default
        checks.append("⚠️ Style may not be applied")

    # Check for labels
    for ax in fig.axes:
        if not ax.get_xlabel() and ax.xaxis.get_visible():
            checks.append("⚠️ Missing x-label")
        if not ax.get_ylabel() and ax.yaxis.get_visible():
            checks.append("⚠️ Missing y-label")

    return checks

# Use it
issues = validate_chart(fig)
if issues:
    print("Chart validation issues:")
    for issue in issues:
        print(f"  {issue}")
```

---

## Quick Reference Card

```python
# Minimal working example
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report-kr")

fig = plt.figure(figsize=(dm.DW, dm.DW * 0.6), dpi=200)
gs = fig.add_gridspec(1, 1, left=0.15, right=0.95, top=0.9, bottom=0.15)
ax = fig.add_subplot(gs[0, 0])

# Your plot code here
ax.plot(x, y, color="oc.blue5", linewidth=0.7)
ax.set_xlabel("X Label")
ax.set_ylabel("Y Label (unit)")

dm.auto_layout(fig)
dm.save_formats(fig, "output/chart", formats=("png",), dpi=300)
plt.close(fig)
```

Remember: **Consistency > Creativity** - Follow these rules for professional, reproducible charts.