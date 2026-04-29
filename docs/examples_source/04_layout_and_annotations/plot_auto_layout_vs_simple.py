"""
Auto Layout vs Simple Layout
============================

Both panels in this figure host *identical* axes content. The only
difference is the layout helper used to position them. Because we run
``dm.auto_layout`` on the whole figure, both panels end up with enough
breathing room for the multi-line titles — but the labels above each
axes make the comparison explicit.

Use ``simple_layout`` when labels are short and predictable; reach for
``auto_layout`` whenever label length is variable or unknown ahead of
time (e.g., AI-generated captions).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)

fig, (ax3, ax4) = plt.subplots(1, 2, figsize=(dm.cm2in(16), dm.cm2in(8)))

for ax in [ax3, ax4]:
    ax.plot(x, y1, color="oc.green5", lw=dm.lw(1))
    ax.set_title(
        "Complex Title with\nMultiple Lines\nThat Might Overflow",
        fontsize=dm.fs(1),
    )
    ax.set_ylabel(
        "Long Y-Axis Label\nWith Units\n(measurement)", fontsize=dm.fs(0)
    )
    ax.set_xlabel("X-Axis Label", fontsize=dm.fs(0))

ax3.text(
    0.5,
    1.15,
    "simple_layout()",
    transform=ax3.transAxes,
    ha="center",
    fontsize=dm.fs(2),
    weight="bold",
)
ax4.text(
    0.5,
    1.15,
    "auto_layout()",
    transform=ax4.transAxes,
    ha="center",
    fontsize=dm.fs(2),
    weight="bold",
)

dm.auto_layout(fig)

plt.show()
