"""Line plot with SI-prefix axis formatting.

Two sinusoidal signals plotted on a shared axis, demonstrating:

- ``dm.style.use("scientific")`` for a compact scientific preset
- ``plt.subplots(figsize=dm.figsize(...))`` for the dartwork sizing API
- ``dm.format_axis_si`` for automatic SI-prefix tick labels (k, M, G…)
- ``dm.minimal_axes`` and ``dm.add_grid`` for a clean academic look

Run with:
    uv run python examples/plot_line_signals.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

x = np.linspace(0, 10, 100)
y1 = np.sin(x) * 1e6
y2 = np.cos(x) * 1e6

ax.plot(x, y1, label="Signal A", linewidth=2)
ax.plot(x, y2, label="Signal B", linewidth=2)

dm.format_axis_si(ax, axis="y")
dm.minimal_axes(ax)
dm.add_grid(ax, which="major", alpha=0.2)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")
ax.set_title("Signal Analysis")
ax.legend()

dm.auto_layout(fig)
dm.save_formats(fig, OUTPUT_DIR / "line_signals", formats=("pdf",), dpi=300)
plt.close(fig)
print(f"Saved: {OUTPUT_DIR / 'line_signals.pdf'}")
