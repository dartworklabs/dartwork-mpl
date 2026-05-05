"""Histogram with a normal-distribution overlay.

A density histogram of synthetic normal data with the analytic Normal PDF
drawn on top. Demonstrates:

- ``dm.style.use("report")``
- Matplotlib's density=True histogram mode
- ``ticker.PercentFormatter`` on the y-axis (a density histogram shown as %
  per bin width only makes sense for normalized data; see note below)

Note: ``PercentFormatter(1.0)`` multiplies by 100 for display. For a true
density with arbitrary y-axis units, remove that call.

Run with:
    uv run python examples/plot_histogram_normal_fit.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report")

fig, ax = dm.subplots(width="9cm", aspect="standard")

rng = np.random.default_rng(42)
data = rng.normal(100, 15, 1000)

ax.hist(
    data, bins=30, density=True, alpha=0.7, edgecolor="black", linewidth=0.5
)

# Analytic Normal PDF overlay.
mu, std = data.mean(), data.std()
xmin, xmax = ax.get_xlim()
xx = np.linspace(xmin, xmax, 100)
pdf = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((xx - mu) / std) ** 2)
ax.plot(
    xx, pdf, "r-", linewidth=2, label=f"Normal fit\nμ={mu:.1f}, σ={std:.1f}"
)

ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))
ax.set_xlabel("Value")
ax.set_ylabel("Density")
ax.set_title("Distribution Analysis")
ax.legend()

dm.auto_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "histogram_normal_fit", formats=("pdf",), dpi=300
)
plt.close(fig)
print(f"Saved: {OUTPUT_DIR / 'histogram_normal_fit.pdf'}")
