"""
Beat Pattern Sequencer
======================

A drum-machine-style step sequencer. Each instrument owns a custom
``dm.oklch`` base hue and its on-cells are blended with white via
``dm.mix_colors`` so that hit intensity reads as colour brightness.
Strong beats also receive a glowing outline rectangle for emphasis.

Highlights:

- ``dm.oklch(L, C, h)`` constructs perceptually balanced base colours.
- ``dm.mix_colors(hex_a, hex_b, alpha=...)`` blends them on the fly.
- Rectangle patches give precise control over per-cell styling.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("20cm", "golden"))

instruments = [
    "Kick",
    "Snare",
    "Hi-Hat",
    "Open Hat",
    "Clap",
    "Ride",
    "Crash",
    "Tom",
]
n_beats = 32
pattern = np.random.choice(
    [0, 0.3, 0.7, 1], size=(len(instruments), n_beats), p=[0.5, 0.2, 0.2, 0.1]
)

# Reinforce the basic groove
pattern[0, ::4] = 1  # Kick on downbeats
pattern[1, 2::4] = 1  # Snare on 2 and 4
pattern[2, :] = np.where(np.random.rand(n_beats) > 0.3, 0.7, 0)  # Hi-hat

instrument_colors = [
    dm.oklch(0.5, 0.3, 10),
    dm.oklch(0.6, 0.3, 60),
    dm.oklch(0.7, 0.2, 200),
    dm.oklch(0.7, 0.2, 180),
    dm.oklch(0.6, 0.3, 300),
    dm.oklch(0.65, 0.25, 120),
    dm.oklch(0.5, 0.35, 40),
    dm.oklch(0.55, 0.3, 350),
]

for i, color in enumerate(instrument_colors):
    for j in range(n_beats):
        intensity = pattern[i, j]

        if intensity > 0:
            rect_color = dm.mix_colors(
                color.to_hex(), "white", alpha=1 - intensity
            )
            ax.add_patch(
                Rectangle(
                    (j, i),
                    0.9,
                    0.9,
                    facecolor=rect_color,
                    edgecolor="white",
                    linewidth=1 if intensity == 1 else 0.5,
                    alpha=0.8 + 0.2 * intensity,
                )
            )
            if intensity == 1:
                ax.add_patch(
                    Rectangle(
                        (j - 0.05, i - 0.05),
                        1,
                        1,
                        facecolor="none",
                        edgecolor=color.to_hex(),
                        linewidth=2,
                        alpha=0.3,
                    )
                )
        else:
            ax.add_patch(
                Rectangle(
                    (j, i),
                    0.9,
                    0.9,
                    facecolor="dc.nordic5",
                    edgecolor="dc.nordic3",
                    linewidth=0.3,
                    alpha=0.5,
                )
            )

for i, instrument in enumerate(instruments):
    ax.text(
        -0.5,
        i + 0.45,
        instrument,
        ha="right",
        va="center",
        fontsize=dm.fs(0),
        color="white",
        weight="bold",
    )

for j in range(0, n_beats, 4):
    ax.text(
        j + 1.5,
        -0.5,
        f"{j + 1}-{j + 4}",
        ha="center",
        va="center",
        fontsize=dm.fs(-1),
        color="dc.nordic2",
    )
    ax.axvline(j, color="white", lw=0.5, alpha=0.3)

ax.set_xlim(-2, n_beats)
ax.set_ylim(-1, len(instruments))
ax.set_aspect("equal")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_facecolor("black")

ax.text(
    n_beats / 2,
    len(instruments) + 0.5,
    "Beat Pattern Sequencer",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
