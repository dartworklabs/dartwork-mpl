"""'Show me the signups': three plans on one axis, the small Team plan flat at the bottom, a default legend and no y label."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
free = [340, 365, 410, 398, 452, 480]
pro = [52, 58, 61, 66, 73, 79]
team = [8, 9, 12, 14, 15, 19]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.plot(months, free, marker="o", label="free")
ax.plot(months, pro, marker="o", label="pro")
ax.plot(months, team, marker="o", label="team")
ax.set_title("Signups")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/vague_show", formats=("png",))
