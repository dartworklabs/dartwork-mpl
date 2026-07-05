"""Bar chart with value labels above each bar.

Shows four generic categories with numeric values, demonstrating:

- ``dm.style.use("report")`` for a business-report preset
- ``dm.format_axis_millions`` for million-scaled tick labels
- Hiding top/right spines for a cleaner look
- Manual ``ax.text`` above each bar for explicit value annotation

Run with:
    uv run python examples/plot_bar_with_value_labels.py
"""

from pathlib import Path

import matplotlib.pyplot as plt

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))

# Generic categorical data — four arbitrary groups.
categories = ["Group A", "Group B", "Group C", "Group D"]
values = [1_200_000, 1_450_000, 1_380_000, 1_620_000]

bars = ax.bar(categories, values, color="oc.blue5")

dm.format_axis_millions(ax, axis="y")

for bar, value in zip(bars, values, strict=True):
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2.0,
        height,
        f"{value / 1e6:.2f}M",
        ha="center",
        va="bottom",
    )

for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.set_ylabel("Count")
ax.set_title("Grouped Count Comparison")

dm.simple_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "bar_with_value_labels", formats=("pdf",), dpi=300
)
plt.close(fig)
print(f"Saved: {OUTPUT_DIR / 'bar_with_value_labels.pdf'}")
