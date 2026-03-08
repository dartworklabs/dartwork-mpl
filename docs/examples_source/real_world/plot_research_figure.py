"""
Research Paper Figure
=====================

A publication-ready 2×2 multi-panel figure using the ``scientific``
style preset. Demonstrates how to combine ``dm.label_axes``,
``dm.save_formats``, and tight spacing for journal submissions.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Use scientific style for paper figures
dm.style.use("scientific")

# %%
# Four-panel experimental results
# --------------------------------
np.random.seed(0)

fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(12)), dpi=300)
gs = fig.add_gridspec(
    2, 2,
    left=0.12, right=0.96,
    top=0.94, bottom=0.10,
    wspace=0.4, hspace=0.5,
)

# Panel (a): Time series
ax_a = fig.add_subplot(gs[0, 0])
t = np.linspace(0, 10, 200)
signal = np.sin(2 * np.pi * 0.5 * t) * np.exp(-0.15 * t)
noise = np.random.normal(0, 0.1, len(t))
ax_a.plot(t, signal + noise, color="oc.gray5", lw=0.3,
          label="Measured", alpha=0.7)
ax_a.plot(t, signal, color="oc.blue6", lw=0.8, label="Model fit")
ax_a.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax_a.set_ylabel("Amplitude [V]", fontsize=dm.fs(0))
ax_a.set_title("Transient Response", fontsize=dm.fs(0.5))
ax_a.legend(fontsize=dm.fs(-1), loc="upper right")

# Panel (b): Scatter with error bars
ax_b = fig.add_subplot(gs[0, 1])
x_data = np.array([1, 2, 3, 4, 5, 6, 7, 8])
y_data = 2.3 * x_data + np.random.normal(0, 1.5, len(x_data))
y_err = np.random.uniform(0.5, 1.5, len(x_data))
ax_b.errorbar(x_data, y_data, yerr=y_err, fmt="o", color="oc.red5",
              markersize=4, capsize=2, elinewidth=0.5, capthick=0.5,
              markeredgecolor="white", markeredgewidth=0.3)
# Linear fit
coeffs = np.polyfit(x_data, y_data, 1)
fit_x = np.linspace(0.5, 8.5, 50)
ax_b.plot(fit_x, np.polyval(coeffs, fit_x), "--", color="oc.gray5",
          lw=0.6, label=f"y = {coeffs[0]:.1f}x + {coeffs[1]:.1f}")
ax_b.set_xlabel("Concentration [mM]", fontsize=dm.fs(0))
ax_b.set_ylabel("Response [mV]", fontsize=dm.fs(0))
ax_b.set_title("Calibration Curve", fontsize=dm.fs(0.5))
ax_b.legend(fontsize=dm.fs(-1), loc="upper left")

# Panel (c): Bar chart comparison
ax_c = fig.add_subplot(gs[1, 0])
methods = ["Baseline", "Method A", "Method B", "Proposed"]
accuracy = [78.2, 84.5, 86.1, 91.3]
colors = ["oc.gray4", "oc.blue4", "oc.green4", "oc.red5"]
bars = ax_c.bar(methods, accuracy, color=colors, edgecolor="white",
                linewidth=0.3, width=0.6)
ax_c.set_ylim(70, 100)
ax_c.set_ylabel("Accuracy (%)", fontsize=dm.fs(0))
ax_c.set_title("Method Comparison", fontsize=dm.fs(0.5))
for bar, val in zip(bars, accuracy, strict=False):
    ax_c.text(bar.get_x() + bar.get_width() / 2, val + 0.5,
              f"{val:.1f}", ha="center", fontsize=dm.fs(-1),
              color="oc.gray7")

# Panel (d): Histogram / distribution
ax_d = fig.add_subplot(gs[1, 1])
data_a = np.random.normal(5.0, 1.2, 500)
data_b = np.random.normal(7.5, 1.0, 500)
ax_d.hist(data_a, bins=25, color=dm.pseudo_alpha("oc.blue5", 0.5),
          edgecolor="oc.blue6", linewidth=0.3, label="Control")
ax_d.hist(data_b, bins=25, color=dm.pseudo_alpha("oc.red5", 0.5),
          edgecolor="oc.red6", linewidth=0.3, label="Treatment")
ax_d.set_xlabel("Value", fontsize=dm.fs(0))
ax_d.set_ylabel("Count", fontsize=dm.fs(0))
ax_d.set_title("Distribution Comparison", fontsize=dm.fs(0.5))
ax_d.legend(fontsize=dm.fs(-1), loc="upper right")

# Add panel labels
dm.label_axes(
    [ax_a, ax_b, ax_c, ax_d],
    fontsize=dm.fs(1),
    fontweight="bold",
)

dm.simple_layout(fig, gs=gs)
plt.show()
