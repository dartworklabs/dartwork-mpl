# Layout Tool Usage Guide

## 1. Overview and Purpose

This guide explains how to use layout tools when creating publication-quality graphs using the `simple_layout` function in `dartwork-mpl`.

`simple_layout` is an improved version of matplotlib's `tight_layout()` that optimizes GridSpec parameters to automatically adjust axes layout. However, without understanding how this function works and its limitations, you may get unexpected results.

## 2. How simple_layout Works

### 2.1 Basic Operation

The `simple_layout` function works as follows:

1. **GridSpec Parameter Optimization**: Adjusts the `left`, `right`, `bottom`, and `top` parameters of the given GridSpec.

2. **Tightbbox Calculation**: Calculates all `tightbbox` values for axes included in the GridSpec and finds the minimum bounding box that contains them.

3. **Target Bbox Setting**: Calculates the position considering `margins` for the target bbox specified by the `bbox` parameter.

4. **Optimization**: Optimizes GridSpec parameters so that axes tightbbox fits into the target bbox.

### 2.2 Optimization Algorithm

```python
def fun(x: np.ndarray) -> float:
    # x = [left, right, bottom, top] (GridSpec parameters)
    gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])

    # Collect all axes tightbbox
    ax_bboxes = [ax.get_tightbbox() for ax in fig.axes]

    # Calculate minimum bbox containing all tightbbox
    all_bbox = get_bounding_box(ax_bboxes)

    # Calculate target bbox (figure coordinates + margins)
    targets = [
        fbox.width * bbox[0] + margins[0],      # left
        fbox.height * bbox[2] + margins[2],    # bottom
        fbox.width * (bbox[1] - bbox[0]) - 2 * margins[1],   # width
        fbox.height * (bbox[3] - bbox[2]) - 2 * margins[3],  # height
    ]

    # Calculate loss and optimize
    loss = np.square((values - targets) / scales * importance_weights).sum()
    return loss
```

### 2.3 Key Parameters

- **`gs`**: GridSpec object to optimize (uses first GridSpec if None)
- **`margins`**: Margins in inches (left, right, bottom, top)
- **`bbox`**: Target region for optimization in figure coordinates (left, right, bottom, top)
- **`use_all_axes`**: If True, considers all axes; if False, only considers axes in the specified GridSpec
- **`importance_weights`**: Optimization weights for each direction (left, right, bottom, top)

## 3. Basic Usage

### 3.1 Simplest Usage

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# Style setup
dm.style.use_preset('scientific')

# Data generation
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# GridSpec creation
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17
)
ax = fig.add_subplot(gs[0, 0])

# Plot
ax.plot(x, y, color='oc.red5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Layout optimization
dm.simple_layout(fig)

# Check result
dm.save_and_show(fig)
```

### 3.2 Margin Adjustment

```python
# Specify margins in inches (left, right, bottom, top)
dm.simple_layout(fig, margins=(0.1, 0.05, 0.1, 0.05))
```

### 3.3 Specifying a GridSpec

```python
# Optimize only a specific GridSpec when multiple GridSpecs exist
dm.simple_layout(fig, gs=gs, margins=(0.08, 0.02, 0.08, 0.02))
```

### 3.4 Partial Region Optimization Using bbox

```python
# Optimize entire figure (default)
dm.simple_layout(fig, bbox=(0, 1, 0, 1))

# Optimize only left half of figure
dm.simple_layout(fig, bbox=(0, 0.5, 0, 1))

# Optimize only right half of figure
dm.simple_layout(fig, bbox=(0.5, 1, 0, 1))

# Optimize only top half of figure
dm.simple_layout(fig, bbox=(0, 1, 0.5, 1))
```

## 4. Conflict Issues with Hardcoded Elements

### 4.1 Problem Situation

`simple_layout` **only considers tightbbox of axes included in the GridSpec**. Therefore, elements directly placed in figure coordinates (`fig.text()`, `fig.legend()`, `fig.suptitle()`, etc.) are not considered during optimization.

**Example: Problematic Case**

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# GridSpec creation
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17
)
ax = fig.add_subplot(gs[0, 0])

# Plot
ax.plot(x, y, color='oc.red5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Hardcoded title (figure coordinates)
fig.text(0.5, 0.98, 'Title',
         fontsize=dm.fs(2), fontweight=dm.fw(1),
         ha='center', va='top')

# Layout optimization
dm.simple_layout(fig)

# Problem: title may overlap with axes!
dm.save_and_show(fig)
```

### 4.2 Why Optimization is Impossible?

1. **Figure coordinate elements are not included in tightbbox**: Elements placed with `fig.text()` etc. are not included in axes tightbbox calculation.

2. **Only GridSpec parameters are optimized**: `simple_layout` only adjusts GridSpec's `left`, `right`, `bottom`, and `top`, so it cannot change the position of elements directly placed in figure coordinates.

3. **Conflict occurs**: During optimization, axes may expand and overlap with hardcoded elements.

## 5. Solution 1: Set bbox Smaller to Reserve Space for Hardcoded Elements

### 5.1 Basic Principle

Calculate where hardcoded elements will be placed in advance, and set the bbox where GridSpec will be placed smaller than that. This prevents axes from encroaching on hardcoded element areas during optimization.

### 5.2 Example: Case with Title and Legend

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(12), dm.cm2in(12)), dpi=200)

# Cascading layout calculation
# 1. Title position (figure coordinates)
title_y = 0.98

# 2. Legend position (placed below title)
title_to_legend_gap = 0.05
legend_y = title_y - title_to_legend_gap

# 3. Figure top (placed below legend)
legend_to_figure_gap = 0.03
figure_top = legend_y - legend_to_figure_gap

# 4. Figure bottom
figure_bottom = 0.1

# 5. Left and right margins
left_margin = 0.17
right_margin = 0.95

# GridSpec creation (area excluding title and legend space)
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=left_margin,
    right=right_margin,
    top=figure_top,      # below title and legend
    bottom=figure_bottom
)
ax = fig.add_subplot(gs[0, 0])

# Plot
line1, = ax.plot(x, y1, color='oc.red5', linewidth=0.7, label='Sin')
line2, = ax.plot(x, y2, color='oc.blue5', linewidth=0.7, label='Cos')
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Hardcoded title (figure coordinates)
fig.text(0.5, title_y, 'Comparison Plot',
         fontsize=dm.fs(2), fontweight=dm.fw(1),
         ha='center', va='top')

# Hardcoded legend (figure coordinates)
fig.legend([line1, line2], ['Sin', 'Cos'],
           bbox_to_anchor=(0.5, legend_y),
           loc='center', ncol=2,
           fontsize=dm.fs(-1))

# Layout optimization
# Use bbox to optimize only axes area
# Place title and legend areas outside bbox to protect them
dm.simple_layout(
    fig,
    gs=gs,
    bbox=(left_margin, right_margin, figure_bottom, figure_top),
    use_all_axes=False,  # Optimize only axes in this GridSpec
)

dm.save_and_show(fig)
```

### 5.3 Notes

- **Cascading calculation**: Calculate sequentially from top to bottom to determine each element's position.
- **Ensure sufficient margins**: Ensure enough spacing between elements to prevent overlap.
- **bbox range**: The `bbox` parameter specifies the area in figure coordinates where axes can be placed.

## 6. Solution 2: Relative Position Specification Using axes_divider

### 6.1 Basic Principle

Use `make_axes_locatable` from `mpl_toolkits.axes_grid1` to place elements relative to other axes. This way, relative positions are maintained even when axes positions change.

### 6.2 Example: Placing Colorbar Next to Axes

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.linspace(0, 10, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# GridSpec creation
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17
)
ax = fig.add_subplot(gs[0, 0])

# Plot
im = ax.contourf(X, Y, Z, cmap='dc.Spectral', levels=20)
ax.set_xlabel('X value', fontsize=dm.fs(0))
ax.set_ylabel('Y value', fontsize=dm.fs(0))

# Create colorbar axes using axes_divider
# This axes is placed relative to ax, so
# it moves together when simple_layout optimizes ax
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.12)
cbar = fig.colorbar(im, cax=cax)
cbar.set_label('Intensity', fontsize=dm.fs(-1))
cbar.ax.tick_params(labelsize=dm.fs(-1))

# Layout optimization
# Colorbar is placed relative to ax, so
# it moves together when ax is optimized
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

### 6.3 Advantages and Disadvantages

**Advantages:**

- Relative positions are maintained even when axes positions change
- Compatible with `simple_layout` optimization

**Disadvantages:**

- Requires `make_axes_locatable`, so additional import needed
- Cannot be applied to all elements (suitable for colorbar, inset axes, etc.)

## 7. Solution 3: Create Axes Containing Text Inside GridSpec

### 7.1 Basic Principle

Make hardcoded elements into separate axes and include them in GridSpec. This way, those elements are also included in tightbbox calculation and considered during optimization.

### 7.2 Example: Making Title into Axes

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# Split GridSpec into 2 rows
# First row: for title (small height)
# Second row: for plot (remaining space)
gs = fig.add_gridspec(
    nrows=2, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17,
    hspace=0,  # No spacing between rows
    height_ratios=[0.1, 0.9]  # title: 10%, plot: 90%
)

# Title axes
ax_title = fig.add_subplot(gs[0, 0])
ax_title.axis('off')  # Hide axes
ax_title.text(0.5, 0.5, 'Title',
              fontsize=dm.fs(2), fontweight=dm.fw(1),
              ha='center', va='center',
              transform=ax_title.transAxes)

# Plot axes
ax = fig.add_subplot(gs[1, 0])
ax.plot(x, y, color='oc.red5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Layout optimization
# Title axes is also included in GridSpec, so
# it's included in tightbbox calculation and optimized
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

### 7.3 Example: Complex Layout (Title + Legend + Plot)

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(12), dm.cm2in(12)), dpi=200)

# Split GridSpec into 3 rows
# First row: for title
# Second row: for legend
# Third row: for plot
gs = fig.add_gridspec(
    nrows=3, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.1,
    hspace=0,  # No spacing between rows
    height_ratios=[0.08, 0.08, 0.84]  # title: 8%, legend: 8%, plot: 84%
)

# Title axes
ax_title = fig.add_subplot(gs[0, 0])
ax_title.axis('off')
ax_title.text(0.5, 0.5, 'Comparison Plot',
              fontsize=dm.fs(2), fontweight=dm.fw(1),
              ha='center', va='center',
              transform=ax_title.transAxes)

# Legend axes
ax_legend = fig.add_subplot(gs[1, 0])
ax_legend.axis('off')
# Dummy plot (for legend)
line1_dummy, = ax_legend.plot(
    [], [], color='oc.red5', linewidth=0.7, label='Sin'
)
line2_dummy, = ax_legend.plot(
    [], [], color='oc.blue5', linewidth=0.7, label='Cos'
)
ax_legend.legend([line1_dummy, line2_dummy], ['Sin', 'Cos'],
                 loc='center', ncol=2,
                 fontsize=dm.fs(-1))

# Plot axes
ax = fig.add_subplot(gs[2, 0])
line1, = ax.plot(x, y1, color='oc.red5', linewidth=0.7)
line2, = ax.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Layout optimization
# All axes are included in GridSpec, so
# all are included in tightbbox calculation and optimized
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

### 7.4 Advantages and Disadvantages

**Advantages:**

- All elements are included in GridSpec, perfectly compatible with `simple_layout`
- Relative positions between elements are automatically maintained

**Disadvantages:**

- GridSpec structure can become complex
- Need to adjust `height_ratios` or `width_ratios` appropriately

## 8. Solution 4: Using Independent GridSpecs

### 8.1 Basic Principle

Create multiple independent GridSpecs and call `simple_layout` separately for each. This way, each GridSpec is optimized independently without interfering with each other.

### 8.2 Example: Left-Right Split Layout

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(17), dm.cm2in(7)), dpi=200)

# Left GridSpec (uses 60% of total height)
gs_left = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.1, right=0.48,  # left half
    top=0.95, bottom=0.15
)
ax_left = fig.add_subplot(gs_left[0, 0])
ax_left.plot(x, y1, color='oc.red5', linewidth=0.7)
ax_left.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_left.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_left.set_title('Left Plot', fontsize=dm.fs(1))

# Right GridSpec (uses 60% of total height)
gs_right = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.52, right=0.9,  # right half
    top=0.95, bottom=0.15
)
ax_right = fig.add_subplot(gs_right[0, 0])
ax_right.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax_right.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_right.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_right.set_title('Right Plot', fontsize=dm.fs(1))

# Optimize each GridSpec independently
# Optimize left GridSpec
dm.simple_layout(
    fig,
    gs=gs_left,
    bbox=(0.1, 0.48, 0.15, 0.95),  # left area only
    use_all_axes=False
)

# Optimize right GridSpec
dm.simple_layout(
    fig,
    gs=gs_right,
    bbox=(0.52, 0.9, 0.15, 0.95),  # right area only
    use_all_axes=False
)

dm.save_and_show(fig)
```

### 8.3 Example: Top-Bottom Split Layout

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(14)), dpi=200)

# Top GridSpec
gs_top = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.52  # top half
)
ax_top = fig.add_subplot(gs_top[0, 0])
ax_top.plot(x, y1, color='oc.red5', linewidth=0.7)
ax_top.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_top.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_top.set_title('Top Plot', fontsize=dm.fs(1))

# Bottom GridSpec
gs_bottom = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.48, bottom=0.1  # bottom half
)
ax_bottom = fig.add_subplot(gs_bottom[0, 0])
ax_bottom.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax_bottom.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_bottom.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_bottom.set_title('Bottom Plot', fontsize=dm.fs(1))

# Optimize each GridSpec independently
# Optimize top GridSpec
dm.simple_layout(
    fig,
    gs=gs_top,
    bbox=(0.17, 0.95, 0.52, 0.95),  # top area only
    use_all_axes=False
)

# Optimize bottom GridSpec
dm.simple_layout(
    fig,
    gs=gs_bottom,
    bbox=(0.17, 0.95, 0.1, 0.48),  # bottom area only
    use_all_axes=False
)

dm.save_and_show(fig)
```

### 8.4 Advantages and Disadvantages

**Advantages:**

- Each GridSpec is optimized independently without interfering with each other
- Can flexibly handle complex layouts

**Disadvantages:**

- Requires multiple `simple_layout` calls
- Need to accurately calculate bbox for each GridSpec

## 9. Solution 5: Combined Solution (Combining Multiple Methods)

### 9.1 Basic Principle

In practice, multiple solutions are often combined. For example:

- Make Title into axes inside GridSpec
- Make Legend using axes_divider
- Make Colorbar using axes_divider
- Manage everything with a single GridSpec

### 9.2 Example: Combined Layout

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.linspace(0, 10, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(12), dm.cm2in(12)), dpi=200)

# Split GridSpec into 2 rows
# First row: for title
# Second row: for plot
gs = fig.add_gridspec(
    nrows=2, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.1,
    hspace=0,
    height_ratios=[0.1, 0.9]
)

# Title axes
ax_title = fig.add_subplot(gs[0, 0])
ax_title.axis('off')
ax_title.text(0.5, 0.5, 'Contour Plot with Colorbar',
              fontsize=dm.fs(2), fontweight=dm.fw(1),
              ha='center', va='center',
              transform=ax_title.transAxes)

# Plot axes
ax = fig.add_subplot(gs[1, 0])
im = ax.contourf(X, Y, Z, cmap='dc.Spectral', levels=20)
ax.set_xlabel('X value', fontsize=dm.fs(0))
ax.set_ylabel('Y value', fontsize=dm.fs(0))

# Create colorbar axes using axes_divider
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.12)
cbar = fig.colorbar(im, cax=cax)
cbar.set_label('Intensity', fontsize=dm.fs(-1))
cbar.ax.tick_params(labelsize=dm.fs(-1))

# Layout optimization
# Title axes and plot axes are included in GridSpec, so
# they're included in tightbbox calculation and optimized
# Colorbar is created with axes_divider and placed relative to ax, so
# it moves together when ax is optimized
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

## 10. Extensibility: Applicable to All Elements

### 10.1 Applicable Elements

The solutions described above can be applied not only to text but also to all of the following elements:

- **Text**: `fig.text()`, `ax.text()`
- **Title**: `fig.suptitle()`, `ax.set_title()`
- **Legend**: `fig.legend()`, `ax.legend()`
- **Colorbar**: `fig.colorbar()`
- **Inset axes**: `inset_axes()`
- **Annotation**: `fig.annotate()`, `ax.annotate()`
- **Other figure coordinate elements**: All elements created with `fig.*` methods

### 10.2 Example: Complex Layout with Various Elements

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(12), dm.cm2in(12)), dpi=200)

# Split GridSpec into 3 rows
# First row: for title
# Second row: for legend
# Third row: for plot
gs = fig.add_gridspec(
    nrows=3, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.1,
    hspace=0,
    height_ratios=[0.08, 0.08, 0.84]
)

# Title axes
ax_title = fig.add_subplot(gs[0, 0])
ax_title.axis('off')
ax_title.text(0.5, 0.5, 'Complex Layout Example',
              fontsize=dm.fs(2), fontweight=dm.fw(1),
              ha='center', va='center',
              transform=ax_title.transAxes)

# Legend axes
ax_legend = fig.add_subplot(gs[1, 0])
ax_legend.axis('off')
line_dummy, = ax_legend.plot(
    [], [], color='oc.red5', linewidth=0.7, label='Data'
)
ax_legend.legend([line_dummy], ['Data'],
                 loc='center', ncol=1,
                 fontsize=dm.fs(-1))

# Plot axes
ax = fig.add_subplot(gs[2, 0])
line, = ax.plot(x, y, color='oc.red5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Annotation (using axes coordinates - placed inside axes)
ax.annotate('Peak', xy=(np.pi/2, 1), xytext=(np.pi/2, 0.5),
            arrowprops=dict(arrowstyle='->', color='oc.gray5'),
            fontsize=dm.fs(-1), ha='center')

# Layout optimization
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

## 11. GridSpec Strategy Guide

### 11.1 How to Decide Number of GridSpecs

**Using One GridSpec:**

- When spine alignment is important for axes
- When all axes need to be aligned with each other
- For simple layouts

**Using Multiple GridSpecs:**

- When independent layout areas are needed
- When spine alignment is not important
- For complex layouts

### 11.2 Splitting Strategy for Each GridSpec

**Vertical Split (using nrows):**

- When placing Title, Legend, Plot vertically
- When placing multiple subplots vertically

**Horizontal Split (using ncols):**

- When placing multiple subplots horizontally
- When placing Colorbar next to axes

**Combined Split (nrows + ncols):**

- Grid layouts like 2x2, 3x2
- Complex multi-subplot layouts

### 11.3 How to Specify bbox

**Using Entire Figure:**

```python
dm.simple_layout(fig, bbox=(0, 1, 0, 1))  # default
```

**Using Partial Region:**

```python
# Left half
dm.simple_layout(fig, bbox=(0, 0.5, 0, 1))

# Right half
dm.simple_layout(fig, bbox=(0.5, 1, 0, 1))

# Top half
dm.simple_layout(fig, bbox=(0, 1, 0.5, 1))

# Bottom half
dm.simple_layout(fig, bbox=(0, 1, 0, 0.5))

# Custom region
dm.simple_layout(fig, bbox=(0.1, 0.9, 0.2, 0.8))
```

## 12. Spine Alignment Considerations

### 12.1 When Spine Alignment is Important

When spines of multiple axes need to be aligned, it's better to **compose with one GridSpec**.

**Example: Shared x-axis or y-axis**

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(14)), dpi=200)

# Compose with one GridSpec (maintains spine alignment)
gs = fig.add_gridspec(
    nrows=2, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.1,
    hspace=0.3
)

# First axes
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(x, y1, color='oc.red5', linewidth=0.7)
ax1.set_ylabel('Y1 value', fontsize=dm.fs(0))
ax1.set_title('Top Plot', fontsize=dm.fs(1))
ax1.tick_params(labelbottom=False)  # Hide x-axis labels

# Second axes (shares x-axis)
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
ax2.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax2.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax2.set_ylabel('Y2 value', fontsize=dm.fs(0))
ax2.set_title('Bottom Plot', fontsize=dm.fs(1))

# Layout optimization
# One GridSpec maintains spine alignment
dm.simple_layout(fig, gs=gs)

dm.save_and_show(fig)
```

### 12.2 When Spine Alignment is Not Important

When spine alignment is not important, you can **compose with separated GridSpecs**.

**Example: Independent Subplots**

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(17), dm.cm2in(7)), dpi=200)

# Left GridSpec
gs_left = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.1, right=0.48,
    top=0.95, bottom=0.15
)
ax_left = fig.add_subplot(gs_left[0, 0])
ax_left.plot(x, y1, color='oc.red5', linewidth=0.7)
ax_left.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_left.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_left.set_title('Left Plot', fontsize=dm.fs(1))

# Right GridSpec
gs_right = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.52, right=0.9,
    top=0.95, bottom=0.15
)
ax_right = fig.add_subplot(gs_right[0, 0])
ax_right.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax_right.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_right.set_ylabel('Y value [kW]', fontsize=dm.fs(0))
ax_right.set_title('Right Plot', fontsize=dm.fs(1))

# Optimize each GridSpec independently
dm.simple_layout(
    fig, gs=gs_left, bbox=(0.1, 0.48, 0.15, 0.95), use_all_axes=False
)
dm.simple_layout(
    fig, gs=gs_right, bbox=(0.52, 0.9, 0.15, 0.95), use_all_axes=False
)

dm.save_and_show(fig)
```

## 13. use_all_axes Notes

### 13.1 How use_all_axes Works

When `use_all_axes=True` (default):

- **Considers tightbbox of all axes**.
- However, **only parameters of the given GridSpec (or first GridSpec) are optimized**.

### 13.2 Problem Situation

When multiple GridSpecs exist and `use_all_axes=True` is used:

- All axes tightbbox are considered, but
- Only the first GridSpec is optimized, so
- Other GridSpecs' axes are considered but not optimized, which can cause unexpected results.

**Example: Problematic Case**

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(17), dm.cm2in(7)), dpi=200)

# Left GridSpec
gs_left = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.1, right=0.48,
    top=0.95, bottom=0.15
)
ax_left = fig.add_subplot(gs_left[0, 0])
ax_left.plot(x, y1, color='oc.red5', linewidth=0.7)
ax_left.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_left.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Right GridSpec
gs_right = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.52, right=0.9,
    top=0.95, bottom=0.15
)
ax_right = fig.add_subplot(gs_right[0, 0])
ax_right.plot(x, y2, color='oc.blue5', linewidth=0.7)
ax_right.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax_right.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Optimize with use_all_axes=True (may cause problems)
# Both ax_left and ax_right are included in tightbbox calculation, but
# only gs_left is optimized
dm.simple_layout(fig, gs=gs_left, use_all_axes=True)

# Result: Only gs_left is optimized, gs_right is not optimized
dm.save_and_show(fig)
```

### 13.3 Correct Usage

**Unless it's a special case using axes_divider, use `use_all_axes=False`**.

**Example: Correct Usage**

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import dartwork_mpl as dm

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.linspace(0, 10, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# GridSpec creation
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=0.17, right=0.95,
    top=0.95, bottom=0.17
)
ax = fig.add_subplot(gs[0, 0])

# Plot
im = ax.contourf(X, Y, Z, cmap='dc.Spectral', levels=20)
ax.set_xlabel('X value', fontsize=dm.fs(0))
ax.set_ylabel('Y value', fontsize=dm.fs(0))

# Create colorbar axes using axes_divider
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.12)
cbar = fig.colorbar(im, cax=cax)
cbar.set_label('Intensity', fontsize=dm.fs(-1))
cbar.ax.tick_params(labelsize=dm.fs(-1))

# Use use_all_axes=False
# Optimize only axes included in gs
dm.simple_layout(fig, gs=gs, use_all_axes=False)

dm.save_and_show(fig)
```

## 14. Best Practices

### 14.1 Layout Design Principles

1. **Clear Hierarchy**: Arrange Title → Legend → Plot from top to bottom
2. **Sufficient Margins**: Ensure enough spacing between elements
3. **Consistent Style**: Use the same layout pattern consistently

### 14.2 Code Writing Recommendations

1. **Cascading Calculation**: Calculate sequentially from top to bottom
2. **Variableization**: Make hardcoded values into variables for reuse
3. **Add Comments**: Add comments to layout calculation logic

### 14.3 Debugging Tips

1. **Step-by-step Verification**: Check with `dm.save_and_show()` at each step
2. **bbox Visualization**: Visualize bbox area to verify
3. **Verbose Mode**: Check optimization process with `verbose=True`

**Example: Debugging bbox Visualization**

```python
import numpy as np
import matplotlib.pyplot as plt
import dartwork_mpl as dm
from matplotlib.patches import Rectangle

dm.style.use_preset('scientific')

# Data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Figure creation
fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# Layout calculation
title_y = 0.98
legend_y = 0.93
figure_top = 0.87
figure_bottom = 0.1
left_margin = 0.17
right_margin = 0.95

# GridSpec creation
gs = fig.add_gridspec(
    nrows=1, ncols=1,
    left=left_margin,
    right=right_margin,
    top=figure_top,
    bottom=figure_bottom
)
ax = fig.add_subplot(gs[0, 0])

# Plot
ax.plot(x, y, color='oc.red5', linewidth=0.7)
ax.set_xlabel('X value [Hour]', fontsize=dm.fs(0))
ax.set_ylabel('Y value [kW]', fontsize=dm.fs(0))

# Hardcoded element
fig.text(0.5, title_y, 'Title',
         fontsize=dm.fs(2), fontweight=dm.fw(1),
         ha='center', va='top')

# Debugging: Visualize bbox area
bbox_rect = Rectangle(
    (left_margin, figure_bottom),
    right_margin - left_margin,
    figure_top - figure_bottom,
    transform=fig.transFigure,
    fill=False,
    edgecolor='red',
    linewidth=2,
    linestyle='--'
)
fig.patches.append(bbox_rect)

# Layout optimization
dm.simple_layout(
    fig,
    gs=gs,
    bbox=(left_margin, right_margin, figure_bottom, figure_top),
    use_all_axes=False
)

dm.save_and_show(fig)
```

## 15. Summary

### 15.1 Core Principles

1. **simple_layout only optimizes GridSpec parameters**: Figure coordinate elements are not considered
2. **Place hardcoded elements outside bbox**: Or include them inside GridSpec
3. **Use one GridSpec when spine alignment is important**
4. **Use separated GridSpecs for independent layouts**
5. **Use use_all_axes only in special cases**

### 15.2 Solution Selection Guide

| Situation                     | Recommended Solution                   |
| ----------------------------- | -------------------------------------- |
| Simple plot with Title/Legend | Solution 1: Set bbox smaller           |
| Plot with Colorbar            | Solution 2: Use axes_divider           |
| Complex multi-element layout  | Solution 3: Include in GridSpec        |
| Independent subplots          | Solution 4: Independent GridSpecs      |
| Combined layout               | Solution 5: Combine multiple solutions |

### 15.3 Checklist

When designing layouts, check the following:

- [ ] Are there hardcoded elements? → Adjust bbox or include in GridSpec
- [ ] Is spine alignment important? → Use one GridSpec
- [ ] Is independent layout needed? → Use separated GridSpecs
- [ ] Are you using use_all_axes? → Check if it's a special case
- [ ] Are bbox values correctly specified for each GridSpec?
- [ ] Is there sufficient spacing between elements?
- [ ] Is the layout applied consistently?

---

**Last Updated**: 2025

**Note**: This guide explains how to use the `simple_layout` function in `dartwork-mpl`. For more details, refer to the general guide and coding rules.
