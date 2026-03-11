"""
Named Color Palettes
====================

``dartwork-mpl`` automatically registers extensive named color palettes including
Open Color (``oc.*``) and Tailwind CSS (``tw.*``). Use them as native matplotlib
color strings — no additional imports or conversions needed.
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use('scientific')

fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.6))

categories = ['Group A', 'Group B', 'Group C', 'Group D', 'Group E']
values = [4.2, 7.1, 3.8, 5.5, 8.9]

# Mixing Tailwind (tw.*) and Open Color (oc.*) palettes seamlessly
colors = ['tw.emerald500', 'tw.amber500', 'oc.grape6', 'oc.indigo6', 'oc.pink6']

bars = ax.bar(categories, values, color=colors, edgecolor='none', width=0.6)

ax.set_title("Native Named Palette Support")
ax.set_ylabel("Measured Value")

fig.tight_layout(pad=1.5)
