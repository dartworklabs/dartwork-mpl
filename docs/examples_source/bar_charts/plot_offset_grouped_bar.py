"""
Offset Grouped Bar Chart
========================

``dm.make_offset`` creates translation transforms for fine-grained
control of label and annotation positioning. This example uses it
to offset data labels on grouped bar charts so they don't overlap.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Grouped bar with offset labels
# --------------------------------
models = ["Model A", "Model B", "Model C", "Model D"]
accuracy = [92.1, 94.5, 93.8, 96.2]
latency = [24, 32, 28, 41]

x = np.arange(len(models))
width = 0.35

fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)

bars1 = ax.bar(
    x - width / 2,
    accuracy,
    width,
    label="Accuracy (%)",
    color="oc.blue5",
    edgecolor="white",
    linewidth=0.3,
)
bars2 = ax.bar(
    x + width / 2,
    latency,
    width,
    label="Latency (ms)",
    color="oc.green5",
    edgecolor="white",
    linewidth=0.3,
)

# Use make_offset for precise label positioning
# Shift accuracy labels slightly left, latency labels slightly right
offset_left = dm.make_offset(-3, 4, fig)
offset_right = dm.make_offset(3, 4, fig)

for bar in bars1:
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        h,
        f"{h:.1f}",
        ha="center",
        va="bottom",
        fontsize=dm.fs(-1),
        transform=ax.transData + offset_left,
    )

for bar in bars2:
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        h,
        f"{h} ms",
        ha="center",
        va="bottom",
        fontsize=dm.fs(-1),
        transform=ax.transData + offset_right,
    )

ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=dm.fs(0))
ax.set_ylabel("Value", fontsize=dm.fs(0))
ax.set_title("Accuracy vs Latency by Model", fontsize=dm.fs(1))
ax.legend(fontsize=dm.fs(-0.5), loc="upper left", framealpha=0.9)
ax.set_ylim(0, 120)

dm.simple_layout(fig)
plt.show()

# %%
# Triple-group comparison
# ------------------------
# Three series with offset labels for clarity.
optimizers = ["SGD", "Adam", "AdamW"]
dataset_a = [88.5, 91.2, 92.1]
dataset_b = [90.3, 93.0, 94.5]
dataset_c = [91.8, 94.7, 95.8]

x = np.arange(len(optimizers))
w = 0.25

fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)

ax.bar(
    x - w,
    dataset_a,
    w,
    label="Dataset A",
    color="oc.blue3",
    edgecolor="white",
    linewidth=0.3,
)
ax.bar(
    x,
    dataset_b,
    w,
    label="Dataset B",
    color="oc.blue5",
    edgecolor="white",
    linewidth=0.3,
)
ax.bar(
    x + w,
    dataset_c,
    w,
    label="Dataset C",
    color="oc.blue7",
    edgecolor="white",
    linewidth=0.3,
)

ax.set_xticks(x)
ax.set_xticklabels(optimizers, fontsize=dm.fs(0))
ax.set_ylabel("Accuracy (%)", fontsize=dm.fs(0))
ax.set_title("Optimizer Comparison Across Datasets", fontsize=dm.fs(1))
ax.legend(fontsize=dm.fs(-0.5), loc="upper left", framealpha=0.9)
ax.set_ylim(80, 100)

# Add improvement annotations with make_offset
for i in range(len(optimizers)):
    improvement = dataset_c[i] - dataset_a[i]
    offset = dm.make_offset(0, 8, fig)
    ax.text(
        x[i] + w,
        dataset_c[i],
        f"+{improvement:.1f}",
        ha="center",
        va="bottom",
        fontsize=dm.fs(-1),
        color="oc.green7",
        fontweight="bold",
        transform=ax.transData + offset,
    )

dm.simple_layout(fig)
plt.show()
