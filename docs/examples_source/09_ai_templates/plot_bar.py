"""
Bar
===

Vertical bar chart - basic template.

Source: ``dartwork_mpl/asset/prompt/05-templates/bar.py`` ·
``dm.get_prompt("05-templates/bar")`` · MCP ``dartwork-mpl://templates/bar``.
"""

import dartwork_mpl as dm

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
