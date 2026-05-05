"""Scatter plot with a linear regression overlay.

Synthetic correlated data fit with ``numpy.polyfit``. Demonstrates:

- ``dm.style.use("scientific")`` for a compact science preset
- ``dm.add_grid`` at low alpha for a subtle background
- Legend with the fitted equation

Run with:
    uv run python examples/plot_scatter_with_fit.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("scientific")

fig, ax = dm.subplots(width="9cm", aspect="square")

rng = np.random.default_rng(42)
x = rng.standard_normal(50)
y = 2 * x + rng.standard_normal(50) * 0.5

ax.scatter(x, y, alpha=0.6, s=50)

z = np.polyfit(x, y, 1)
p = np.poly1d(z)
x_line = np.linspace(x.min(), x.max(), 100)
ax.plot(
    x_line, p(x_line), "r--", alpha=0.8, label=f"y = {z[0]:.2f}x + {z[1]:.2f}"
)

dm.add_grid(ax, alpha=0.15)
ax.set_xlabel("X Variable")
ax.set_ylabel("Y Variable")
ax.set_title("Correlation Analysis")
ax.legend()

dm.auto_layout(fig)
dm.save_formats(fig, OUTPUT_DIR / "scatter_with_fit", formats=("pdf",), dpi=300)
plt.close(fig)
print(f"Saved: {OUTPUT_DIR / 'scatter_with_fit.pdf'}")
