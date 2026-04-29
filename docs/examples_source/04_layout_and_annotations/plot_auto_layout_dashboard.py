"""
Auto Layout: Mixed-Complexity Dashboard
=======================================

Real dashboards rarely have homogeneous labels. Here a 3×3 grid mixes
short, medium, and very long titles. ``dm.auto_layout`` inspects each
panel and grows margins independently so the longest labels never
clip — without wasting whitespace around the simpler panels.

The two important parameters:

- ``padding``: minimum padding around text (in inches).
- ``max_iter``: cap on the convergence loop to keep things bounded.

For predictable labels, ``simple_layout`` is faster. Reach for
``auto_layout`` whenever overflow is unacceptable (publications) or
labels are variable length (generated dashboards).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

fig = plt.figure(figsize=(dm.cm2in(20), dm.cm2in(15)))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

axes = []
for i in range(3):
    for j in range(3):
        ax = fig.add_subplot(gs[i, j])
        axes.append(ax)

        data = np.random.randn(50).cumsum()
        ax.plot(
            data,
            color=f"oc.{['blue', 'red', 'green'][j]}{4 + i}",
            lw=dm.lw(0.8),
        )

        if i == 0 and j == 0:
            ax.set_ylabel(
                "Very Long Label\nWith Multiple\nLines of Text\n(Complex Units)"
            )
            ax.set_title(
                "Panel with Extremely Long Title\nThat Would Normally Overflow"
            )
        elif i == 1 and j == 1:
            ax.set_ylabel("Medium Label\n(units)")
            ax.set_title("Moderate Title")
        else:
            ax.set_ylabel("Value")
            ax.set_title(f"Panel {i * 3 + j + 1}")

        ax.set_xlabel("Time" if i == 2 else "")

dm.label_axes(axes)

dm.auto_layout(
    fig,
    padding=0.08,
    max_iter=10,
    verbose=False,
)

plt.suptitle("Dashboard with Auto Layout", fontsize=dm.fs(3), y=1.02)

plt.show()
