"""
Named Color Palettes
====================

``dartwork-mpl`` automatically registers extensive named color palettes including
Open Color (``oc.*``) and Tailwind CSS (``tw.*``). Use them as native matplotlib
color strings — no additional imports or conversions needed.
"""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "golden"))

categories = ["Group A", "Group B", "Group C", "Group D", "Group E"]
values = [4.2, 7.1, 3.8, 5.5, 8.9]

# Mixing Tailwind (tw.*), Open Color (oc.*), and dartwork core (dc.*)
colors = ["tw.emerald500", "tw.amber500", "oc.grape5", "dc.teal3", "dc.vivid3"]

bars = ax.bar(categories, values, color=colors, edgecolor="none", width=0.6)

ax.set_title("Native Named Palette Support")
ax.set_ylabel("Measured Value")

dm.simple_layout(fig)
plt.show()
