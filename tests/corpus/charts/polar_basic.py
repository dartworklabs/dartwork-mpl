"""Two plans scored on six criteria as a radar chart."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["Speed", "Cost", "Quality", "Reach", "Trust", "Service"]
values_a = [4.0, 3.2, 4.5, 2.8, 4.1, 3.5]
values_b = [3.0, 4.5, 3.0, 4.0, 3.2, 4.2]

theta = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
# Close the loop for radar plotting.
theta_closed = np.concatenate([theta, theta[:1]])
a_closed = values_a + values_a[:1]
b_closed = values_b + values_b[:1]

fig, ax = plt.subplots(
    figsize=dm.figsize_for("matrix"), subplot_kw={"projection": "polar"}
)
ax.plot(
    theta_closed, a_closed, color="dc.teal3", linewidth=dm.lw(0), label="Plan A"
)
ax.fill(theta_closed, a_closed, color="dc.teal1", alpha=0.3)
ax.plot(
    theta_closed,
    b_closed,
    color="dc.orange3",
    linewidth=dm.lw(0),
    label="Plan B",
)
ax.fill(theta_closed, b_closed, color="dc.red1", alpha=0.3)
ax.set_xticks(theta)
ax.set_xticklabels(categories)
ax.set_ylim(0, 5)
dm.place_legend(ax, loc="below")

dm.simple_layout(fig)
dm.save_formats(fig, "output/polar_basic", formats=("png",))
