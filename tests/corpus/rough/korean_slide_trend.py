"""앱과 웹 방문자 추이 슬라이드: 모든 점에 값, 손으로 놓은 선 이름과 화살표, 왼쪽 정렬 suptitle과 부제."""

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import dartwork_mpl as dm

dm.style.use("presentation-kr")

months = ["1월", "2월", "3월", "4월", "5월", "6월"]
visitors = {
    "앱": [15200, 16800, 18900, 21400, 23800, 26100],
    "웹": [22100, 21500, 20800, 20100, 19700, 19000],
}
colors = {"앱": "#2563EB", "웹": "#F97316"}

fig, ax = plt.subplots(figsize=(13.33, 7.5))
for name, values in visitors.items():
    other = visitors["웹" if name == "앱" else "앱"]
    ax.plot(
        months, values, color=colors[name], lw=4, marker="o", ms=10, label=name
    )
    for i, (x, y) in enumerate(zip(months, values, strict=True)):
        ax.annotate(
            f"{y:,}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 14 if y >= other[i] else -26),
            ha="center",
            fontsize=14,
            color=colors[name],
        )
    ax.text(
        5.12,
        values[-1],
        name,
        color=colors[name],
        fontsize=22,
        fontweight="bold",
        va="center",
    )
ax.set_xlim(-0.3, 5.6)
ax.set_ylim(12000, 28500)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v / 1000)}천"))
ax.tick_params(labelsize=16)
ax.set_ylabel("방문자 수 (명)", fontsize=16)
ax.grid(axis="y", alpha=0.25)
ax.annotate(
    "4월: 앱이 웹을 추월",
    xy=(3, 21400),
    xytext=(1.4, 26200),
    fontsize=18,
    fontweight="bold",
    arrowprops={"arrowstyle": "->", "lw": 2, "color": "#444"},
)
fig.suptitle(
    "앱 방문자는 꾸준히 증가, 웹은 감소 — 4월에 역전",
    fontsize=26,
    fontweight="bold",
    x=0.06,
    ha="left",
    y=0.97,
)
ax.set_title(
    "월별 방문자 수 추이 (1~6월)", fontsize=16, loc="left", color="#555"
)

dm.simple_layout(fig)
dm.save_formats(fig, "output/korean_slide_trend", formats=("png",))
