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

The chart demonstrates dartwork-mpl's color palette (``dc.green2`` for
positive contributions, ``dc.red2`` for negative contributions), subtle
connector lines, and value labels via ``dm.label_bars``, printed like the
library's ticks (``1,000`` on both). Each step is drawn with its signed
change as the height, so ``sign="+"`` marks a gain with ``+`` and each
loss's label sits below its bar.
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
values = np.array([1000, -180, -60, 760, -20, -40, 700])
is_total = np.array([True, False, False, True, False, False, True])

# The level after each bar: a total resets it, a step moves it by its
# signed change. A step is drawn from the level before it with its signed
# change as the height, so the bar holds the change.
level = np.zeros(len(values))
current = 0
for i, (value, total) in enumerate(zip(values, is_total, strict=True)):
    current = value if total else current + value
    level[i] = current
x = np.arange(len(categories))
step = ~is_total

fig, ax = plt.subplots(figsize=dm.figsize("17cm", 0.55))

totals = ax.bar(
    x[is_total],
    level[is_total],
    color="tw.slate700",  # Totals: neutral dark.
    width=0.6,
    zorder=3,
)
steps = ax.bar(
    x[step],
    values[step],
    bottom=(level - values)[step],
    color=["dc.green2" if v >= 0 else "dc.red2" for v in values[step]],
    width=0.6,
    zorder=3,
)
ax.set_xticks(x, categories)

# Connector lines at each bar's closing level to the next bar.
for i in range(len(values) - 1):
    ax.plot(
        [i + 0.3, i + 1 - 0.3],
        [level[i], level[i]],
        color="dc.indigo3",
        ls=":",
        lw=dm.lw(0.5),
        zorder=2,
    )

# Value labels: steps signed in their bar's colour, a fall's below it.
dm.label_bars(ax, steps, sign="+", color="series")
dm.label_bars(ax, totals)

ax.set_title("Energy balance bridge (input to useful output)")
ax.set_ylabel("Energy (arbitrary units)")

# Hide x-axis spine for a cleaner baseline, draw an explicit zero line.
ax.spines["bottom"].set_visible(False)
ax.axhline(0, color="tw.slate800", lw=dm.lw(1.5), zorder=1)

# Top margin to fit annotations.
ax.set_ylim(-100, 1150)

dm.simple_layout(fig)
plt.show()
