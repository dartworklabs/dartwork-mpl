"""
Blue-orange for Signed Bins
================================

Opt in to a local ordering of the existing eight ``blue_orange`` colors for
signed bins. Reversing only the orange half puts pale colors next to zero and
dark colors at both extremes. The same signed fields and bin edges appear
side by side below. The continuous reference is identical in both panels.

This recipe has no neutral bin: zero is the boundary between two pale bins.
The arms retain unequal brightness. It adds no registration and changes no
existing color values, defaults, or ``dm.colors(..., n=...)`` outputs.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

import dartwork_mpl as dm

dm.style.use("scientific")

# The opt-in recipe uses the same eight values; only the orange order changes.
original8 = dm.colors("blue_orange", n=8)
centered8 = original8[:4] + original8[4:][::-1]
cmap = ListedColormap(centered8)
norm = BoundaryNorm(np.linspace(-1, 1, 9), cmap.N)

# Reuse the flat field and signed peaks from the approved comparison.
x = np.linspace(-1, 1, 72)
y = np.linspace(-1, 1, 48)
X, Y = np.meshgrid(x, y)
signed_flat = X
signed_peaks = 0.91 * np.exp(
    -((X - 0.4) ** 2 / 0.10 + (Y - 0.1) ** 2 / 0.22)
) - 0.91 * np.exp(-((X + 0.4) ** 2 / 0.10 + (Y + 0.1) ** 2 / 0.22))

fig = plt.figure(figsize=dm.figsize("34cm", "12.5cm"))
outer = fig.add_gridspec(1, 2, wspace=0.12)

for column, (colors, title) in enumerate(
    [
        (original8, 'Stored order · dm.colors("blue_orange", n=8)'),
        (centered8, "Opt-in recipe · centered 8-bin order"),
    ]
):
    grid = outer[0, column].subgridspec(
        5, 2, height_ratios=[0.25, 1, 0.16, 0.65, 0.13], hspace=0.65
    )
    heading = fig.add_subplot(grid[0, :])
    heading.axis("off")
    heading.text(0, 0.5, title, fontsize=dm.fs(1), fontweight=dm.fw(1))

    panel_cmap = ListedColormap(colors)
    panel_norm = BoundaryNorm(norm.boundaries, panel_cmap.N)
    for position, (data, label) in enumerate(
        [
            (signed_flat, "Equal-width signed bins"),
            (signed_peaks, "Signed peaks · same ±1 scale"),
        ]
    ):
        ax = fig.add_subplot(grid[1, position])
        ax.imshow(
            data,
            cmap=panel_cmap,
            norm=panel_norm,
            origin="lower",
            interpolation="nearest",
            aspect="auto",
        )
        ax.set(xticks=[], yticks=[])
        ax.set_title(label, fontsize=dm.fs(-1))

    strip = fig.add_subplot(grid[2, :])
    strip.imshow(
        np.arange(8)[None, :],
        cmap=panel_cmap,
        vmin=-0.5,
        vmax=7.5,
        interpolation="nearest",
        aspect="auto",
        extent=(-1, 1, 0, 1),
    )
    strip.set(yticks=[], xticks=[-1, 0, 1], xticklabels=["−1", "0", "+1"])
    strip.tick_params(length=0)

    reference = fig.add_subplot(grid[3, 0])
    reference.imshow(
        signed_peaks,
        cmap="dc.blue_orange",
        vmin=-1,
        vmax=1,
        origin="lower",
        interpolation="nearest",
        aspect="auto",
    )
    reference.set(xticks=[], yticks=[])
    reference.set_title("Existing continuous blue_orange", fontsize=dm.fs(-1))
    note = fig.add_subplot(grid[3, 1])
    note.axis("off")
    note.text(
        0,
        0.95,
        "Continuous reference stays unchanged.\n"
        "8-bin recipe has no neutral bin.\n"
        "Arms retain unequal brightness.",
        fontsize=dm.fs(-1),
        va="top",
        linespacing=1.4,
    )
    gradient = fig.add_subplot(grid[4, :])
    gradient.imshow(
        np.linspace(-1, 1, 256)[None, :],
        cmap="dc.blue_orange",
        vmin=-1,
        vmax=1,
        interpolation="nearest",
        aspect="auto",
        extent=(-1, 1, 0, 1),
    )
    gradient.set(yticks=[], xticks=[-1, 0, 1])
    gradient.set_xlabel("Continuous reference", fontsize=dm.fs(-1))

dm.simple_layout(fig)
plt.show()
