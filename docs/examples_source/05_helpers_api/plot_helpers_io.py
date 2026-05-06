"""
Styled Figure Creation
========================

Apply a dartwork style preset and create a figure in two steps:
``dm.style.use("…")`` then ``plt.figure(...)``.  Pass any preset name
(``"scientific"``, ``"report"``, ``"web"``, …) to ``dm.style.use``.

This example creates a single figure with the ``scientific`` preset
and plots two reference signals.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply the style preset, then create the figure.
# Width defaults to 17 cm (two-column figure), height ≈ 60% of width.
dm.style.use("scientific")
fig = plt.figure(figsize=dm.figsize("17cm", 0.6), dpi=200)
ax = fig.add_subplot(111)

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color="oc.blue5", lw=dm.lw(1.5), label="sin(x)")
ax.plot(x, np.cos(x), color="oc.red5", lw=dm.lw(1.5), label="cos(x)")
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("y", fontsize=dm.fs(0))
ax.set_title("Styled Figure", fontsize=dm.fs(2))
ax.legend(fontsize=dm.fs(-1))
dm.minimal_axes(ax)
dm.simple_layout(fig)

# To save to disk, use dm.save_formats:
#   from pathlib import Path
#   Path("output").mkdir(parents=True, exist_ok=True)
#   dm.save_formats(fig, "output/figure", formats=("png",), dpi=300)

print("Figure created with dm.style.use + plt.figure.")
print(f"Figure size: {fig.get_size_inches()}")
print(f"DPI: {fig.dpi}")

plt.show()
