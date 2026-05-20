"""
Particle Flow Dynamics
======================

Particles seeded on a 15×15 grid are integrated through a hand-built
flow field (sin/cos product). Every particle keeps a 20-step trail and
is coloured by its current polar coordinates so the flow direction is
visually encoded along the gradient.

The streamplot underneath shares the same vector field but is given a
muted indigo→teal colormap, so the foreground particles read clearly
against the background motion.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "square"))


def flow_field(x, y, t=0):
    u = np.sin(np.pi * x * 0.4) * np.cos(np.pi * y * 0.4) + 0.5 * np.sin(t)
    v = -np.cos(np.pi * x * 0.4) * np.sin(np.pi * y * 0.4) + 0.5 * np.cos(t)
    return u, v


grid_size = 15
x_grid = np.linspace(-3, 3, grid_size)
y_grid = np.linspace(-3, 3, grid_size)

particles = [
    {
        "x": x + np.random.randn() * 0.1,
        "y": y + np.random.randn() * 0.1,
        "trail": [],
    }
    for x in x_grid
    for y in y_grid
]

n_steps = 50
dt = 0.05
for step in range(n_steps):
    for particle in particles:
        u, v = flow_field(particle["x"], particle["y"], step * 0.1)
        particle["trail"].append((particle["x"], particle["y"]))
        particle["x"] += u * dt
        particle["y"] += v * dt
        if len(particle["trail"]) > 20:
            particle["trail"].pop(0)

# Background flow field
x_bg = np.linspace(-4, 4, 30)
y_bg = np.linspace(-4, 4, 30)
X_bg, Y_bg = np.meshgrid(x_bg, y_bg)
U_bg, V_bg = flow_field(X_bg, Y_bg)
speed = np.sqrt(U_bg**2 + V_bg**2)

colors_flow = dm.cspace("dc.ocean1", "dc.forest3", n=256)
flow_cmap = LinearSegmentedColormap.from_list(
    "flow", [c.to_hex() for c in colors_flow]
)

ax.streamplot(
    X_bg,
    Y_bg,
    U_bg,
    V_bg,
    color=speed,
    cmap=flow_cmap,
    linewidth=dm.lw(-1),
    density=1,
)

for particle in particles:
    r = np.sqrt(particle["x"] ** 2 + particle["y"] ** 2)
    hue = (np.arctan2(particle["y"], particle["x"]) + np.pi) / (2 * np.pi) * 360
    color = dm.oklch(0.7 - r * 0.05, 0.3, hue)

    if len(particle["trail"]) > 1:
        for i in range(len(particle["trail"]) - 1):
            alpha = i / len(particle["trail"]) * 0.6
            ax.plot(
                [particle["trail"][i][0], particle["trail"][i + 1][0]],
                [particle["trail"][i][1], particle["trail"][i + 1][1]],
                color=color.to_hex(),
                alpha=alpha,
                lw=dm.lw(-1),
            )

    ax.scatter(
        particle["x"],
        particle["y"],
        s=30,
        c=[color.to_hex()],
        edgecolors="white",
        linewidths=0.5,
        alpha=0.9,
        zorder=10,
    )

vortices = [(0, 0), (2.5, 0), (-2.5, 0), (0, 2.5), (0, -2.5)]
for vx, vy in vortices:
    ax.add_patch(
        Circle(
            (vx, vy),
            0.2,
            color="white",
            alpha=0.3,
            edgecolor="dc.ocean2",
            linewidth=dm.lw(-1),
        )
    )

ax.set_xlim(-4, 4)
ax.set_ylim(-4, 4)
ax.set_aspect("equal")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_facecolor("dc.nordic0")

ax.text(
    0,
    4.5,
    "Particle Flow Dynamics",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
