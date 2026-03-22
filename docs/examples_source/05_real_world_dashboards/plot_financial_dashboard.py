"""
Financial Performance Dashboard
================================

A comprehensive financial dashboard demonstrating dartwork-mpl's capabilities
for professional business intelligence reporting. This example shows quarterly
performance metrics, revenue trends, and profitability analysis.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Use the report style for professional dashboards
dm.style.use("report")

# Generate sample financial data
np.random.seed(42)
quarters = ["Q1-23", "Q2-23", "Q3-23", "Q4-23", "Q1-24", "Q2-24"]
n_quarters = len(quarters)

# Revenue data (in millions)
revenue = np.array([120, 135, 142, 158, 165, 178])
costs = revenue * 0.65 + np.random.normal(0, 2, n_quarters)
profit = revenue - costs

# Growth rates
revenue_growth = np.concatenate([[0], np.diff(revenue) / revenue[:-1] * 100])
profit_margin = profit / revenue * 100

# Product mix data
products = ["Product A", "Product B", "Product C", "Product D"]
product_revenue = np.random.dirichlet(np.ones(4), n_quarters) * revenue[:, None]

# Create dashboard
fig = plt.figure(figsize=(dm.cm2in(25), dm.cm2in(18)))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.25)

# Title
fig.suptitle(
    "Q2 2024 Financial Performance Dashboard",
    fontsize=dm.fs(2),
    weight="bold",
    y=0.98,
)

# ===============================
# Panel 1: Revenue & Profit Trend
# ===============================
ax1 = fig.add_subplot(gs[0, :2])

# Revenue bars
x = np.arange(n_quarters)
width = 0.35
ax1.bar(
    x - width / 2, revenue, width, label="Revenue", color="oc.blue5", alpha=0.8
)
ax1.bar(
    x + width / 2, profit, width, label="Profit", color="oc.green5", alpha=0.8
)

# Growth rate line
ax1_twin = ax1.twinx()
ax1_twin.plot(
    x,
    revenue_growth,
    "o-",
    color="oc.orange6",
    linewidth=dm.lw(1),
    markersize=5,
    label="Growth %",
)

# Formatting
ax1.set_xlabel("Quarter", fontsize=dm.fs(0))
ax1.set_ylabel("Amount ($M)", fontsize=dm.fs(0))
ax1_twin.set_ylabel("Growth Rate (%)", fontsize=dm.fs(0))
ax1.set_xticks(x)
ax1.set_xticklabels(quarters)
ax1.set_title("Revenue & Profitability Trend", fontsize=dm.fs(1), weight="bold")
ax1.legend(loc="upper left", fontsize=dm.fs(-1))
ax1_twin.legend(loc="upper right", fontsize=dm.fs(-1))
dm.grid_on(ax1, which="major", alpha=0.2)

# ===============================
# Panel 2: Key Metrics
# ===============================
ax2 = fig.add_subplot(gs[0, 2])
ax2.axis("off")

metrics = {
    "Revenue": f"${revenue[-1]:.1f}M",
    "QoQ Growth": f"{revenue_growth[-1]:.1f}%",
    "Profit Margin": f"{profit_margin[-1]:.1f}%",
    "YoY Growth": f"{((revenue[-1] / revenue[0]) - 1) * 100:.1f}%",
}

y_pos = 0.85
for metric, value in metrics.items():
    ax2.text(
        0.1, y_pos, metric + ":", fontsize=dm.fs(0), weight="bold", ha="left"
    )
    ax2.text(
        0.9,
        y_pos,
        value,
        fontsize=dm.fs(0),
        ha="right",
        color="oc.green7" if "+" not in value else "black",
    )
    y_pos -= 0.2

ax2.set_title("Key Metrics", fontsize=dm.fs(1), weight="bold")
ax2.add_patch(
    plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor="gray", linewidth=0.5)
)

# ===============================
# Panel 3: Product Mix
# ===============================
ax3 = fig.add_subplot(gs[1, :2])

# Stacked area chart
bottom = np.zeros(n_quarters)
colors = ["oc.blue4", "oc.blue6", "oc.teal5", "oc.cyan6"]

for i, product in enumerate(products):
    ax3.fill_between(
        x,
        bottom,
        bottom + product_revenue[:, i],
        alpha=0.7,
        color=colors[i],
        label=product,
    )
    bottom += product_revenue[:, i]

ax3.set_xlabel("Quarter", fontsize=dm.fs(0))
ax3.set_ylabel("Revenue ($M)", fontsize=dm.fs(0))
ax3.set_title("Product Revenue Mix", fontsize=dm.fs(1), weight="bold")
ax3.set_xticks(x)
ax3.set_xticklabels(quarters)
ax3.legend(loc="upper left", fontsize=dm.fs(-1), ncol=2)
dm.grid_on(ax3, which="major", alpha=0.2)

# ===============================
# Panel 4: Profit Margin Trend
# ===============================
ax4 = fig.add_subplot(gs[1, 2])

# Profit margin with threshold lines
ax4.plot(
    x,
    profit_margin,
    "o-",
    color="oc.green6",
    linewidth=dm.lw(1.5),
    markersize=6,
)
ax4.axhline(y=35, color="oc.red5", linestyle="--", alpha=0.5, label="Target")
ax4.fill_between(x, 0, profit_margin, alpha=0.2, color="oc.green5")

ax4.set_xlabel("Quarter", fontsize=dm.fs(0))
ax4.set_ylabel("Margin (%)", fontsize=dm.fs(0))
ax4.set_title("Profit Margin", fontsize=dm.fs(1), weight="bold")
ax4.set_xticks(x)
ax4.set_xticklabels(quarters, rotation=45, ha="right")
ax4.legend(fontsize=dm.fs(-1))
dm.grid_on(ax4, which="major", alpha=0.2)

# ===============================
# Panel 5: Regional Performance
# ===============================
ax5 = fig.add_subplot(gs[2, :])

# Regional breakdown
regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
regional_data = (
    np.random.dirichlet(np.array([4, 3, 2, 1]), n_quarters).T * revenue
)

x_regional = np.arange(len(regions))
width_regional = 0.15

for i, quarter in enumerate(quarters[-3:]):  # Last 3 quarters
    offset = (i - 1) * width_regional
    ax5.bar(
        x_regional + offset,
        regional_data[:, -(3 - i)],
        width_regional,
        label=quarter,
        alpha=0.8,
    )

ax5.set_xlabel("Region", fontsize=dm.fs(0))
ax5.set_ylabel("Revenue ($M)", fontsize=dm.fs(0))
ax5.set_title(
    "Regional Revenue Comparison (Last 3 Quarters)",
    fontsize=dm.fs(1),
    weight="bold",
)
ax5.set_xticks(x_regional)
ax5.set_xticklabels(regions)
ax5.legend(fontsize=dm.fs(-1))
dm.grid_on(ax5, which="major", alpha=0.2)

# Apply automatic layout optimization
dm.auto_layout(fig, padding=0.02)

plt.show()
