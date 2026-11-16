"""Browser share on a 16:9 slide with 22 and 30 pt text set by hand, hand-placed value labels and no x axis."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("presentation")

names = ["Chrome", "Safari", "Edge", "Firefox", "Samsung Internet", "Other"]
vals = [64.7, 18.6, 5.2, 2.8, 2.4, 6.3]

fig, ax = plt.subplots(figsize=(13.33, 7.5))
colors = ["#4C78A8" if n != "Other" else "#B0B0B0" for n in names]
bars = ax.barh(names[::-1], vals[::-1], color=colors[::-1])
for bar, v in zip(bars, vals[::-1], strict=True):
    ax.text(
        v + 0.8,
        bar.get_y() + bar.get_height() / 2,
        f"{v:.1f}%",
        va="center",
        fontsize=22,
    )
ax.set_xlim(0, max(vals) * 1.15)
ax.set_title("Browser market share", fontsize=30, loc="left", pad=20)
ax.tick_params(axis="y", labelsize=22, length=0)
ax.set_xticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

dm.simple_layout(fig)
dm.save_formats(fig, "output/slide_share", formats=("png",))
