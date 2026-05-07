"""
Simple Layout: Default vs Margin Buffer
=======================================

Both panels host *identical* axes content. The only difference is the
``margin`` argument passed to ``dm.simple_layout``: the left panel
uses the default (axes content snaps flush against figure edges)
while the right panel adds a uniform 2 % buffer.

``simple_layout`` measures every visible artist on every axes and
arithmetically places the GridSpec so the content union sits at the
requested distance from each figure edge — see
:doc:`/usage_guide/layout` for the full margin API
(:class:`~dartwork_mpl.units.Length`, percentage strings, per-side
``ml`` / ``mr`` / ``mt`` / ``mb``).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)

fig, (ax_flush, ax_buffered) = plt.subplots(
    1, 2, figsize=dm.figsize("16cm", "cinema")
)

for ax in [ax_flush, ax_buffered]:
    ax.plot(x, y1, color="oc.green5", lw=dm.lw(1))
    ax.set_title(
        "Complex Title with\nMultiple Lines\nThat Might Overflow",
        fontsize=dm.fs(1),
    )
    ax.set_ylabel(
        "Long Y-Axis Label\nWith Units\n(measurement)", fontsize=dm.fs(0)
    )
    ax.set_xlabel("X-Axis Label", fontsize=dm.fs(0))

ax_flush.text(
    0.5,
    1.15,
    "margin=0 (default)",
    transform=ax_flush.transAxes,
    ha="center",
    fontsize=dm.fs(2),
    weight="bold",
)
ax_buffered.text(
    0.5,
    1.15,
    'margin="2%"',
    transform=ax_buffered.transAxes,
    ha="center",
    fontsize=dm.fs(2),
    weight="bold",
)

dm.simple_layout(fig)

plt.show()
