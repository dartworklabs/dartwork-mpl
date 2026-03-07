"""
Decimal Formatting
==================

``dm.set_decimal`` controls the number of decimal places on tick
labels. This is especially useful for financial data where you need
consistent precision (e.g. prices to 2 decimals, percentages to 1).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Stock price with 2-decimal precision
# --------------------------------------
np.random.seed(42)
days = 120
price = 150 + np.cumsum(np.random.randn(days) * 2)
dates = np.arange(days)

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(dm.cm2in(13), dm.cm2in(11)), dpi=300
)

# Top: default tick formatting (matplotlib auto)
ax1.plot(dates, price, color="oc.blue5", lw=1)
ax1.set_title("Default Tick Format", fontsize=dm.fs(0.5))
ax1.set_ylabel("Price ($)", fontsize=dm.fs(0))

# Bottom: explicit 2-decimal formatting
ax2.plot(dates, price, color="oc.green5", lw=1)
dm.set_decimal(ax2, yn=2)
ax2.set_title("dm.set_decimal(ax, yn=2)", fontsize=dm.fs(0.5))
ax2.set_ylabel("Price ($)", fontsize=dm.fs(0))
ax2.set_xlabel("Trading Day", fontsize=dm.fs(0))

dm.simple_layout(fig)
plt.show()

# %%
# Percentage axis with 1-decimal precision
# ------------------------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

quarters = ["1Q24", "2Q24", "3Q24", "4Q24", "1Q25"]
margins = [23.4, 25.1, 22.8, 26.7, 28.3]

ax.bar(quarters, margins, color="oc.teal5", edgecolor="white",
       linewidth=0.3, width=0.6)
ax.set_ylim(0, 35)

# Format y-axis to 1 decimal
dm.set_decimal(ax, yn=1)

ax.set_title("Operating Margin (%)", fontsize=dm.fs(1))
ax.set_ylabel("Margin (%)", fontsize=dm.fs(0))
ax.set_xlabel("Quarter", fontsize=dm.fs(0))

# Add value labels on bars
for i, v in enumerate(margins):
    ax.text(i, v + 0.5, f"{v:.1f}%", ha="center",
            fontsize=dm.fs(-0.5), color="oc.gray7")

dm.simple_layout(fig)
plt.show()
