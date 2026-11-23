"""Mass against length with a fitted line whose whole equation sits in a long default legend."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

x = np.array(
    [152, 158, 160, 163, 165, 168, 170, 172, 175, 177, 180, 183, 185, 188]
)
y = np.array([48, 55, 53, 60, 58, 66, 64, 70, 72, 71, 79, 82, 80, 88])
m, b = np.polyfit(x, y, 1)
r2 = np.corrcoef(x, y)[0, 1] ** 2

fig, ax = plt.subplots(figsize=(6, 4.5))
ax.scatter(x, y, alpha=0.8, label=f"Bars (n={len(x)})")
xs = np.linspace(x.min(), x.max(), 100)
ax.plot(
    xs,
    m * xs + b,
    color="crimson",
    label=f"Linear fit: y = {m:.2f}x {b:+.1f} (R² = {r2:.2f})",
)
ax.set_xlabel("Length (cm)")
ax.set_ylabel("Mass (kg)")
ax.set_title("Mass vs. Length")
ax.grid(alpha=0.3)
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/scatter_fit", formats=("png",))
