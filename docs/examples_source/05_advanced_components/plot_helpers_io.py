"""
helpers.io — Create a Styled Figure in One Call
================================================

``dm.helpers.io.create_figure_with_style`` creates a ``Figure`` with a
preset already applied, sidestepping the usual
``dm.style.use("…"); plt.figure(...)`` two-step. Pass any preset name
(``"scientific"``, ``"report"``, ``"web"``, …) via the ``style``
argument.

This example creates a single figure with the ``scientific`` preset
and plots two reference signals. A companion ``save_figure`` helper
(commented out below) can be chained in to write the result to disk
with optimised settings.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Create a figure with the style preset already applied.
fig = dm.helpers.io.create_figure_with_style(
    style="scientific", figsize=(8, 6), dpi=100
)
ax = fig.add_subplot(111)

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color="oc.blue5", lw=dm.lw(1.5), label="sin(x)")
ax.plot(x, np.cos(x), color="oc.red5", lw=dm.lw(1.5), label="cos(x)")
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("y", fontsize=dm.fs(0))
ax.set_title("Created with Style Helper", fontsize=dm.fs(2))
ax.legend(fontsize=dm.fs(-1))
dm.minimal_axes(ax)
dm.simple_layout(fig)

# Companion save helper — left commented out so this script has no
# side effects. Uncomment and point `filename` at a writable location.
#
# dm.helpers.io.save_figure(
#     fig,
#     filename="output_optimized.png",
#     dpi=300,
#     transparent=False,
#     optimize=True,
# )

print("Figure created with style helper.")
print(f"Figure size: {fig.get_size_inches()}")
print(f"DPI: {fig.dpi}")

plt.show()
