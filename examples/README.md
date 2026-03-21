# dartwork-mpl Examples

Individual, focused plotting examples using dartwork-mpl - a general-purpose matplotlib wrapper library.

## Philosophy
- **No dashboards**: Each example focuses on a single, well-crafted plot
- **Clean and simple**: Minimal code with maximum clarity
- **Reusable patterns**: Easy to adapt for your own use cases
- **Professional output**: Publication-ready plots with proper formatting

## Available Examples

### English Examples (`single_plot_example.py`)
1. **Line Plot** - SI unit formatting, multiple series
2. **Bar Plot** - Value labels, millions formatting
3. **Scatter Plot** - Regression line overlay
4. **Histogram** - Normal distribution fit
5. **Heatmap** - Color-mapped data visualization

### Korean Examples (`single_plot_korean.py`)
1. **라인 플롯** - SI 단위 포매팅
2. **막대 그래프** - 값 레이블 표시
3. **산점도** - 회귀선 포함
4. **히스토그램** - 정규분포 피팅
5. **파이 차트** - 도넛 스타일
6. **시계열 플롯** - 이중 축

## Running Examples

```bash
# English examples
uv run python examples/single_plot_example.py

# Korean examples (with Paperlogy font support)
uv run python examples/single_plot_korean.py
```

## Output
All plots are saved to `examples/output/` as high-resolution PDF (English) or PNG (Korean) files.

## Key Features Demonstrated

### Formatting Utilities
- `dm.format_axis_si()` - Automatic SI prefix formatting (k, M, G, T)
- `dm.format_axis_millions()` - Million suffix formatting
- `dm.format_axis_percent()` - Percentage formatting
- `dm.format_axis_currency()` - Currency formatting

### Style Utilities
- `dm.minimal_axes()` - Clean, minimal axis appearance
- `dm.hide_spines()` - Selective spine hiding
- `dm.add_grid()` - Configurable grid lines
- `dm.add_frame()` - Add frames/borders

### Figure Presets
- `dm.FS_SINGLE` - Single column width
- `dm.FS_DOUBLE` - Double column width
- `dm.FS_SQUARE` - Square aspect ratio
- `dm.FS_WIDE` - Wide format (timelines)
- `dm.FS_TALL` - Tall format (vertical)
- `dm.FS_GOLDEN` - Golden ratio
- `dm.FS_SLIDE` - 16:9 presentation

### Korean Support
- Use `style="report-kr"` for Korean text
- Paperlogy font family for perfect rendering
- Full Unicode support

## Creating Your Own Plots

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

# Choose a style
dm.style.use("scientific")  # or "report", "report-kr"

# Create figure with preset size
fig, ax = dm.subplots(figsize=dm.FS_SINGLE)

# Plot your data
x = np.linspace(0, 10, 100)
y = np.sin(x) * 1e6
ax.plot(x, y)

# Apply formatting
dm.format_axis_si(ax, axis='y')
dm.minimal_axes(ax)

# Labels and styling
ax.set_xlabel('X Label')
ax.set_ylabel('Y Label')
ax.set_title('My Plot')

# Save
plt.savefig('my_plot.pdf', dpi=300)
plt.close()
```

## Notes
- dartwork-mpl is a general-purpose plotting utility, not a dashboard framework
- Focus on creating individual, high-quality plots
- For complex multi-plot layouts, create separate figures
- Use the appropriate style for your target audience and language