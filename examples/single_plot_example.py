"""Example: Simple Individual Plot with dartwork-mpl.

Demonstrates creating clean, professional individual plots
without dashboard/multi-subplot complexity.

Run with:
    uv run python examples/single_plot_example.py
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

def example_line_plot():
    """Create a simple line plot with formatting utilities."""
    dm.style.use("scientific")

    # Create figure
    fig, ax = dm.subplots(figsize=dm.FS_SINGLE)

    # Generate data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) * 1e6
    y2 = np.cos(x) * 1e6

    # Plot
    ax.plot(x, y1, label='Signal A', linewidth=2)
    ax.plot(x, y2, label='Signal B', linewidth=2)

    # Apply formatting
    dm.format_axis_si(ax, axis='y')  # SI prefix formatting
    dm.minimal_axes(ax)  # Clean appearance

    # Labels
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude')
    ax.set_title('Signal Analysis')
    ax.legend()

    # Grid
    dm.add_grid(ax, which='major', alpha=0.2)

    plt.tight_layout()
    plt.savefig('output/line_plot.pdf', dpi=300)
    plt.close()

def example_bar_plot():
    """Create a simple bar plot with value formatting."""
    dm.style.use("report")

    # Create figure
    fig, ax = dm.subplots(figsize=dm.FS_WIDE)

    # Data
    categories = ['Q1', 'Q2', 'Q3', 'Q4']
    values = [1200000, 1450000, 1380000, 1620000]

    # Plot
    colors = dm.helpers.colors.auto_select_colors(1, 'categorical')
    bars = ax.bar(categories, values, color='#1f77b4')

    # Format y-axis with millions
    dm.format_axis_millions(ax, axis='y')

    # Add value labels on bars
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${value/1e6:.1f}M',
                ha='center', va='bottom')

    # Clean up
    dm.hide_spines(ax, ['top', 'right'])
    ax.set_ylabel('Revenue')
    ax.set_title('Quarterly Revenue')

    plt.tight_layout()
    plt.savefig('output/bar_plot.pdf', dpi=300)
    plt.close()

def example_scatter_plot():
    """Create a scatter plot with regression line."""
    dm.style.use("scientific")

    # Create figure
    fig, ax = dm.subplots(figsize=dm.FS_SQUARE)

    # Generate data
    np.random.seed(42)
    x = np.random.randn(50)
    y = 2 * x + np.random.randn(50) * 0.5

    # Scatter plot
    ax.scatter(x, y, alpha=0.6, s=50)

    # Add regression line
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, p(x_line), 'r--', alpha=0.8,
            label=f'y = {z[0]:.2f}x + {z[1]:.2f}')

    # Style
    dm.add_grid(ax, alpha=0.15)
    ax.set_xlabel('X Variable')
    ax.set_ylabel('Y Variable')
    ax.set_title('Correlation Analysis')
    ax.legend()

    plt.tight_layout()
    plt.savefig('output/scatter_plot.pdf', dpi=300)
    plt.close()

def example_histogram():
    """Create a histogram with distribution overlay."""
    dm.style.use("report")

    # Create figure
    fig, ax = dm.subplots(figsize=dm.FS_SINGLE)

    # Generate data
    np.random.seed(42)
    data = np.random.normal(100, 15, 1000)

    # Histogram
    n, bins, patches = ax.hist(data, bins=30, density=True,
                                alpha=0.7, edgecolor='black', linewidth=0.5)

    # Add normal distribution overlay
    from scipy import stats
    mu, std = data.mean(), data.std()
    xmin, xmax = ax.get_xlim()
    x = np.linspace(xmin, xmax, 100)
    p = stats.norm.pdf(x, mu, std)
    ax.plot(x, p, 'r-', linewidth=2, label=f'Normal fit\nμ={mu:.1f}, σ={std:.1f}')

    # Format
    dm.format_axis_percent(ax, axis='y')
    ax.set_xlabel('Value')
    ax.set_ylabel('Probability Density')
    ax.set_title('Distribution Analysis')
    ax.legend()

    plt.tight_layout()
    plt.savefig('output/histogram.pdf', dpi=300)
    plt.close()

def example_heatmap():
    """Create a simple heatmap."""
    dm.style.use("scientific")

    # Create figure
    fig, ax = dm.subplots(figsize=dm.FS_SQUARE)

    # Generate data
    data = np.random.randn(10, 10)

    # Heatmap
    im = ax.imshow(data, cmap='RdBu_r', aspect='auto', vmin=-2, vmax=2)

    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Value', rotation=270, labelpad=15)

    # Labels
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    ax.set_title('Heatmap Example')

    # Ticks
    ax.set_xticks(np.arange(10))
    ax.set_yticks(np.arange(10))

    plt.tight_layout()
    plt.savefig('output/heatmap.pdf', dpi=300)
    plt.close()

if __name__ == "__main__":
    print("Creating individual plot examples...")

    print("1. Line plot with SI formatting...")
    example_line_plot()

    print("2. Bar plot with value labels...")
    example_bar_plot()

    print("3. Scatter plot with regression...")
    example_scatter_plot()

    print("4. Histogram with distribution fit...")
    example_histogram()

    print("5. Heatmap...")
    example_heatmap()

    print("\nAll examples completed!")