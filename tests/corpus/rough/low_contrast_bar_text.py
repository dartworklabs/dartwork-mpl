"""Satisfaction scores with white values centred inside pale yellow and light grey bars."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

teams = ["Support", "Billing", "Onboarding", "Sales"]
scores = [4.6, 3.9, 4.2, 3.4]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bars = ax.bar(
    teams, scores, color=["dc.yellow3", "dc.gray2", "dc.yellow3", "dc.lime2"]
)
ax.bar_label(
    bars, fmt="%.1f", label_type="center", color="white", fontsize=dm.fs(1)
)
ax.set_ylabel("Satisfaction (1-5)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/low_contrast_bar_text", formats=("png",))
