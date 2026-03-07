"""
Visual Assets Preview
=====================

Use the built-in diagnostic functions to preview all bundled assets:
named color palettes, custom colormaps, and installed fonts.
"""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Named colors
# ------------
# ``plot_colors()`` renders every named color registered by dartwork-mpl,
# grouped by library (Open Color, Tailwind CSS, etc.).

dm.plot_colors(ncols=5)
plt.show()

# %%
# Custom colormaps
# ----------------
# ``plot_colormaps()`` shows all custom colormaps shipped with the library,
# optionally grouped by type (sequential, diverging, etc.).

dm.plot_colormaps(group_by_type=True)
plt.show()

# %%
# Installed fonts
# ---------------
# ``plot_fonts()`` previews the fonts registered with matplotlib by
# dartwork-mpl.  Each family shows available weights and a pangram sample.

dm.plot_fonts(ncols=3)
plt.show()
