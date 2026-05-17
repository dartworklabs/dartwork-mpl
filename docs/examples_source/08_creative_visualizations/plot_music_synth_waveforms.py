"""
Synthesizer Waveform Display
============================

Three classic synthesizer waveforms — sine, square, and sawtooth —
stacked in a single retro-futuristic dashboard. Each pane gets:

- A gradient fill underneath the wave (``dm.cspace`` per channel).
- A faux-glow drawn by stacking three semi-transparent line copies of
  increasing width before the crisp white line on top.
- Subtle horizontal gridlines for a CRT-style read-out.

Set ``fig.patch.set_facecolor("black")`` to keep the surrounding canvas
matched to the panel backgrounds.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, axes = plt.subplots(
    3, 1, figsize=dm.figsize("20cm", "standard"), gridspec_kw={"hspace": 0.1}
)

t = np.linspace(0, 4 * np.pi, 1000)

waves = [
    ("Sine Wave", np.sin(t) + 0.3 * np.sin(3 * t) + 0.1 * np.sin(7 * t)),
    ("Square Wave", np.sign(np.sin(t)) * 0.8 + 0.2 * np.sin(5 * t)),
    ("Sawtooth Wave", 2 * (t / np.pi % 2 - 1) + 0.15 * np.sin(8 * t)),
]

color_schemes = [
    dm.cspace("dc.cyber5", "dc.vivid1", n=len(t)),
    dm.cspace("dc.ocean5", "dc.forest1", n=len(t)),
    dm.cspace("dc.sunset5", "dc.sunset1", n=len(t)),
]

for ax, (name, wave), colors in zip(axes, waves, color_schemes, strict=False):
    for i in range(len(t) - 1):
        ax.fill_between(
            [t[i], t[i + 1]],
            0,
            [wave[i], wave[i + 1]],
            color=colors[i].to_hex(),
            alpha=0.7,
        )

    for offset, alpha in [(3, 0.1), (2, 0.2), (1, 0.3)]:
        ax.plot(t, wave, color="white", lw=dm.lw(0.5) + offset, alpha=alpha)
    ax.plot(t, wave, color="white", lw=dm.lw(1))

    ax.text(
        0.02,
        0.85,
        name,
        transform=ax.transAxes,
        fontsize=dm.fs(1),
        color="white",
        weight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "black", "alpha": 0.5},
    )

    ax.set_xlim(0, 4 * np.pi)
    ax.set_ylim(-1.5, 1.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_facecolor("black")
    ax.set_xticks([])
    ax.set_yticks([])

    for y in np.linspace(-1.5, 1.5, 7):
        ax.axhline(y, color="dc.nordic4", lw=0.3, alpha=0.3)

fig.suptitle(
    "Synthesizer Waveform Display",
    fontsize=dm.fs(4),
    color="white",
    weight="bold",
    y=0.98,
)
fig.patch.set_facecolor("black")

dm.simple_layout(fig)
plt.show()
