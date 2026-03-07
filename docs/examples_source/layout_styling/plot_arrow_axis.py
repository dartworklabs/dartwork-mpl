"""
Arrow Axis Annotations
======================

``dm.arrow_axis`` draws bidirectional arrows with Low/High labels along
a spine edge — perfect for risk-return matrices and conceptual diagrams.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Risk–Return scatter matrix
# --------------------------
# A classic 2D matrix with arrow axes indicating the conceptual
# direction of each dimension.
np.random.seed(42)

fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

# Generate cluster data for four quadrants
categories = {
    "Growth Stocks": (7, 12, "oc.red5"),
    "Value Stocks": (3, 5, "oc.blue5"),
    "Bonds": (1.5, 2, "oc.green5"),
    "Commodities": (5, 8, "oc.yellow6"),
}

for name, (ret, risk, color) in categories.items():
    n = 15
    x = np.random.normal(risk, 1.5, n)
    y = np.random.normal(ret, 2, n)
    ax.scatter(x, y, color=color, s=20, alpha=0.7, label=name,
               edgecolors="white", linewidths=0.3)

ax.set_xlim(-2, 16)
ax.set_ylim(-4, 18)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Risk\u2013Return Matrix", fontsize=dm.fs(1), pad=16)

# Add arrow axes
dm.arrow_axis(ax, "x", "Risk", low="Low", high="High",
              offset=-0.08)
dm.arrow_axis(ax, "y", "Return", low="Low", high="High",
              offset=-0.10)

ax.legend(loc="upper left", fontsize=dm.fs(-0.5), frameon=True,
          framealpha=0.9, edgecolor="oc.gray3")

dm.simple_layout(fig)
plt.show()

# %%
# Horizontal and vertical axes on separate panels
# ------------------------------------------------
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(dm.cm2in(15), dm.cm2in(8)), dpi=300
)

# Left panel: horizontal arrow only
x = np.linspace(0, 10, 50)
ax1.plot(x, np.cumsum(np.random.randn(50) * 0.3), color="oc.blue5",
         lw=1)
ax1.set_xticks([])
ax1.set_title("Horizontal Arrow", fontsize=dm.fs(1), pad=16)
dm.arrow_axis(ax1, "x", "Time", low="Start", high="End",
              offset=-0.10)

# Right panel: vertical arrow only
y = np.sort(np.random.uniform(0, 100, 8))
ax2.barh(range(len(y)), y, color="oc.green4", edgecolor="white",
         linewidth=0.3)
ax2.set_yticks([])
ax2.set_title("Vertical Arrow", fontsize=dm.fs(1), pad=16)
dm.arrow_axis(ax2, "y", "Priority", low="Low", high="High",
              offset=-0.14)

dm.simple_layout(fig)
plt.show()
