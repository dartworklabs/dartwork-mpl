"""
Gravitational Particle Swarm
============================

A swarm of 200 particles is integrated forward in time under five
attracting wells with damping. Each particle keeps a 30-step trail and
is coloured by its current angle around the origin via ``dm.oklch``,
giving the swarm a rainbow halo.

Useful in this example:

- Cumulative trail storage in a ``(n_particles, trail_length)`` array.
- Layered ``Circle`` patches at each gravity well to create soft
  outer-glow effects without per-pixel shading.
"""

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("20cm", "square"))

wells = [(0, 0, 1.5), (3, 2, 1.0), (-2, 3, 0.8), (1, -3, 1.2), (-3, -1, 0.9)]

n_particles = 200
particles_x = np.random.randn(n_particles) * 4
particles_y = np.random.randn(n_particles) * 4
particles_vx = np.random.randn(n_particles) * 0.1
particles_vy = np.random.randn(n_particles) * 0.1

trail_length = 30
trails_x = np.zeros((n_particles, trail_length))
trails_y = np.zeros((n_particles, trail_length))

for step in range(trail_length):
    trails_x[:, step] = particles_x
    trails_y[:, step] = particles_y

    fx = np.zeros(n_particles)
    fy = np.zeros(n_particles)
    for wx, wy, strength in wells:
        dx = wx - particles_x
        dy = wy - particles_y
        r = np.sqrt(dx**2 + dy**2) + 0.1
        force = strength / r**2
        fx += force * dx / r
        fy += force * dy / r

    particles_vx += fx * 0.01
    particles_vy += fy * 0.01
    particles_vx *= 0.99
    particles_vy *= 0.99
    particles_x += particles_vx
    particles_y += particles_vy

for i in range(n_particles):
    angle = np.arctan2(particles_y[i], particles_x[i])
    hue = (angle + np.pi) / (2 * np.pi) * 360
    color = dm.oklch(0.6, 0.3, hue)

    for j in range(trail_length - 1):
        alpha = j / trail_length * 0.5
        ax.plot(
            [trails_x[i, j], trails_x[i, j + 1]],
            [trails_y[i, j], trails_y[i, j + 1]],
            color=color.to_hex(),
            alpha=alpha,
            lw=0.5,
        )

    ax.scatter(
        particles_x[i],
        particles_y[i],
        s=20,
        c=[color.to_hex()],
        edgecolors="white",
        linewidths=0.5,
        alpha=0.9,
        zorder=10,
    )

for wx, wy, strength in wells:
    for r, alpha in [(2, 0.1), (1.5, 0.2), (1, 0.3)]:
        ax.add_patch(
            Circle((wx, wy), r * strength, color="white", alpha=alpha, zorder=5)
        )
    ax.add_patch(
        Circle(
            (wx, wy),
            0.3,
            color="white",
            edgecolor="dc.ocean2",
            linewidth=2,
            zorder=15,
        )
    )

ax.set_xlim(-6, 6)
ax.set_ylim(-6, 6)
ax.set_aspect("equal")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_facecolor("black")

title = ax.text(
    0,
    6.5,
    "Gravitational Particle Dynamics",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)
title.set_path_effects(
    [path_effects.withStroke(linewidth=3, foreground="dc.ocean5")]
)

dm.simple_layout(fig)
plt.show()
