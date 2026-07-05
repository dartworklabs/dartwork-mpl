"""
Fireworks Celebration
=====================

Five simulated fireworks burst in mid-air, each composed of 80–150
particles flung outward at random angles and exponential speeds. A
linear gravity term curves the trajectories, and short trails fade
behind every particle for a long-exposure feel.

Each firework owns its own ``dm.cspace`` ramp pulled from random
opening and closing colour names — no two bursts repeat the same
gradient, even on subsequent runs (when the seed changes).
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("14cm", 0.8))

n_fireworks = 5
explosion_data = []

for _fw in range(n_fireworks):
    center_x = np.random.uniform(-8, 8)
    center_y = np.random.uniform(2, 8)
    n_particles_fw = np.random.randint(80, 150)
    explosion_time = np.random.uniform(0, 0.5)

    color_start = (
        f"oc.{np.random.choice(['red', 'blue', 'green', 'yellow', 'purple'])}9"
    )
    color_end = (
        f"oc.{np.random.choice(['orange', 'cyan', 'pink', 'teal', 'violet'])}3"
    )
    colors = dm.cspace(color_start, color_end, n=n_particles_fw)

    angles = np.random.uniform(0, 2 * np.pi, n_particles_fw)
    speeds = np.random.exponential(2, n_particles_fw) + np.random.uniform(1, 3)

    explosion_data.append(
        {
            "center": (center_x, center_y),
            "particles": n_particles_fw,
            "angles": angles,
            "speeds": speeds,
            "colors": colors,
            "time": explosion_time,
        }
    )

for fw_data in explosion_data:
    center_x, center_y = fw_data["center"]
    t = 2 - fw_data["time"]
    gravity = 0.5

    for i in range(fw_data["particles"]):
        angle = fw_data["angles"][i]
        speed = fw_data["speeds"][i]
        x = center_x + speed * np.cos(angle) * t
        y = center_y + speed * np.sin(angle) * t - 0.5 * gravity * t**2

        trail_steps = 10
        for j in range(trail_steps):
            t_trail = t - j * 0.05
            if t_trail > 0:
                x_trail = center_x + speed * np.cos(angle) * t_trail
                y_trail = (
                    center_y
                    + speed * np.sin(angle) * t_trail
                    - 0.5 * gravity * t_trail**2
                )
                alpha = (1 - j / trail_steps) * (1 - t / 3) * 0.5
                size = 3 * (1 - j / trail_steps)
                ax.scatter(
                    x_trail,
                    y_trail,
                    s=size,
                    c=[fw_data["colors"][i].to_hex()],
                    alpha=alpha,
                )

        if y > -2:
            alpha = max(0, 1 - t / 3)
            ax.scatter(
                x,
                y,
                s=10,
                c=[fw_data["colors"][i].to_hex()],
                edgecolors="white",
                linewidths=0.3,
                alpha=alpha,
                zorder=10,
            )

    if fw_data["time"] < 0.1:
        ax.add_patch(
            Circle(
                (center_x, center_y),
                1,
                color="white",
                alpha=0.5 - fw_data["time"] * 5,
            )
        )

# Sparkling background stars
n_stars = 100
ax.scatter(
    np.random.uniform(-10, 10, n_stars),
    np.random.uniform(-2, 10, n_stars),
    s=np.random.exponential(1, n_stars),
    c="white",
    alpha=np.random.uniform(0.2, 0.8, n_stars),
    marker="*",
)

ax.fill_between([-10, 10], -2, -2, color="dc.teal5", alpha=0.3)

ax.set_xlim(-10, 10)
ax.set_ylim(-2, 10)
ax.set_aspect("equal")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_facecolor("dc.indigo5")

ax.text(
    0,
    -3,
    "Fireworks Celebration",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
