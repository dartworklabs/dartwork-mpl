"""
Bridge (Waterfall) Chart
========================

A bridge chart — also known as a waterfall chart — decomposes how a starting
value is transformed into a final value by a sequence of positive and
negative contributions, with optional intermediate totals along the way.

It works for any domain where a sequence of gains and losses between two
endpoints needs to be made legible at a glance: energy accounting, mass
balance, population flow, project scheduling slack, algorithmic step
budgets, and so on. The example below uses a synthetic energy-balance
walk: primary input → end-use consumption.

The chart demonstrates dartwork-mpl's color palette (``dc.forest2`` for
positive contributions, ``dc.spectrum2`` for negative contributions), subtle
connector lines, and tick formatting via ``dm.set_decimal()``.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

# Data: synthetic energy-balance walk (arbitrary units).
# Positive = additions, negative = losses. Three "total" bars anchor
# the walk: primary input, subtotal after losses, and final output.
categories = [
    "Primary\ninput",
    "Conversion\nloss",
    "Transmission\nloss",
    "Net\ndelivered",
    "Standby\nloss",
    "End-use\nloss",
    "Useful\noutput",
]
values = [1000, -180, -60, 760, -20, -40, 700]
is_total = [True, False, False, True, False, False, True]

# Calculate baselines (bottom of each bar).
baselines = np.zeros(len(values))
current = 0
for i in range(len(values)):
    if is_total[i]:
        baselines[i] = 0
        current = values[i]
    else:
        if values[i] >= 0:
            baselines[i] = current
        else:
            baselines[i] = current + values[i]
        current += values[i]

# Determine colors.
colors = []
for i, v in enumerate(values):
    if is_total[i]:
        colors.append("tw.slate700")  # Totals: neutral dark.
    else:
        colors.append("dc.forest2" if v >= 0 else "dc.spectrum2")

fig, ax = plt.subplots(figsize=dm.figsize("17cm", 0.55))

bars = ax.bar(
    categories,
    np.abs(values),
    bottom=baselines,
    color=colors,
    width=0.6,
    zorder=3,
)

# Connector lines between the top of one bar and the bottom of the next.
current_total = values[0]
for i in range(1, len(values)):
    ax.plot(
        [i - 1 + 0.3, i - 0.3],
        [current_total, current_total],
        color="dc.muted3",
        ls=":",
        lw=dm.lw(0.5),
        zorder=2,
    )
    if is_total[i]:
        current_total = values[i]
    else:
        current_total += values[i]

# Value labels above/below each bar.
for i, (b, v, _bar) in enumerate(zip(baselines, values, bars, strict=False)):
    offset = 20
    if v >= 0:
        y_pos = b + abs(v) + offset
        va = "bottom"
    else:
        y_pos = b - offset
        va = "top"

    val_str = str(v) if is_total[i] else (f"+{v}" if v > 0 else str(v))

    ax.text(
        i,
        y_pos,
        val_str,
        ha="center",
        va=va,
        fontsize=dm.fs(-1),
        fontweight="bold",
        color=colors[i],
    )

ax.set_title("Energy balance bridge (input to useful output)")
ax.set_ylabel("Energy (arbitrary units)")
dm.set_decimal(ax, yn=0)

# Hide x-axis spine for a cleaner baseline, draw an explicit zero line.
ax.spines["bottom"].set_visible(False)
ax.axhline(0, color="tw.slate800", lw=dm.lw(1.5), zorder=1)

# Top margin to fit annotations.
ax.set_ylim(-100, 1150)

dm.simple_layout(fig)
plt.show()
