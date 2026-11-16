"""Online against store orders with hand-set 12 pt text, a bold left title, end values and a legend pinned to the top centre."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
online = [120, 135, 150, 149, 170, 182, 190, 205]
store = [200, 190, 185, 170, 168, 160, 158, 150]

plt.rcParams.update({"font.size": 12})
fig, ax = plt.subplots(figsize=(10, 5))
for data, color, label, marker in [
    (online, "#2A6FDB", "Online", "o"),
    (store, "#E8743B", "Store", "s"),
]:
    ax.plot(
        months,
        data,
        marker=marker,
        color=color,
        linewidth=2.5,
        markersize=7,
        markerfacecolor="white",
        markeredgewidth=2,
        label=label,
        zorder=3,
    )
    ax.annotate(
        f"{data[-1]}",
        (months[-1], data[-1]),
        xytext=(10, 0),
        textcoords="offset points",
        color=color,
        fontweight="bold",
        va="center",
    )
ax.set_title(
    "Orders per month", fontsize=18, fontweight="bold", loc="left", pad=16
)
ax.set_ylabel("Orders")
ax.set_ylim(100, 220)
ax.grid(axis="y", color="#E5E5E5", linewidth=1)
ax.tick_params(length=0)
ax.legend(
    loc="upper center",
    ncol=2,
    frameon=False,
    fontsize=12,
    bbox_to_anchor=(0.5, 1.0),
)

dm.simple_layout(fig)
dm.save_formats(fig, "output/prettier_edit", formats=("png",))
