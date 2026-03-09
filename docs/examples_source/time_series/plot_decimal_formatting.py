"""
Decimal Formatting
==================

``dm.set_decimal`` controls the number of decimal places on tick
labels. This is especially useful for scientific data where you need
consistent precision (e.g. sensor readings to 2 decimals, percentages to 1).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Sensor reading with 2-decimal precision
# -----------------------------------------
np.random.seed(42)
days = 120
temperature = 22.0 + np.cumsum(np.random.randn(days) * 0.3)
samples = np.arange(days)

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(dm.cm2in(13), dm.cm2in(11)), dpi=300
)

# Top: default tick formatting (matplotlib auto)
ax1.plot(samples, temperature, color="oc.blue5", lw=1)
ax1.set_title("Default Tick Format", fontsize=dm.fs(0.5))
ax1.set_ylabel("Temperature (°C)", fontsize=dm.fs(0))

# Bottom: explicit 2-decimal formatting
ax2.plot(samples, temperature, color="oc.green5", lw=1)
dm.set_decimal(ax2, yn=2)
ax2.set_title("dm.set_decimal(ax, yn=2)", fontsize=dm.fs(0.5))
ax2.set_ylabel("Temperature (°C)", fontsize=dm.fs(0))
ax2.set_xlabel("Sample Index", fontsize=dm.fs(0))

dm.simple_layout(fig)
plt.show()

# %%
# Percentage axis with 1-decimal precision
# ------------------------------------------
fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)

conditions = ["Cond. A", "Cond. B", "Cond. C", "Cond. D", "Cond. E"]
efficiency = [23.4, 25.1, 22.8, 26.7, 28.3]

ax.bar(
    conditions,
    efficiency,
    color="oc.teal5",
    edgecolor="white",
    linewidth=0.3,
    width=0.6,
)
ax.set_ylim(0, 35)

# Format y-axis to 1 decimal
dm.set_decimal(ax, yn=1)

ax.set_title("Conversion Efficiency (%)", fontsize=dm.fs(1))
ax.set_ylabel("Efficiency (%)", fontsize=dm.fs(0))
ax.set_xlabel("Condition", fontsize=dm.fs(0))

# Add value labels on bars
for i, v in enumerate(efficiency):
    ax.text(
        i,
        v + 0.5,
        f"{v:.1f}%",
        ha="center",
        fontsize=dm.fs(-0.5),
        color="oc.gray7",
    )

dm.simple_layout(fig)
plt.show()
