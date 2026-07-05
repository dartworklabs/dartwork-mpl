"""값 레이블이 있는 막대 그래프 (한글).

네 개의 일반 범주에 대한 수치를 막대 위에 레이블로 명시합니다.

실행:
    uv run python examples/plot_bar_with_value_labels_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))

# 일반적인 범주형 데이터 — 임의의 네 그룹.
categories = ["그룹 A", "그룹 B", "그룹 C", "그룹 D"]
values = [1_200_000, 1_450_000, 1_380_000, 1_620_000]

bars = ax.bar(categories, values, color="oc.blue5")

dm.format_axis_millions(ax, axis="y")

for bar, value in zip(bars, values, strict=True):
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2.0,
        height,
        f"{value / 1e6:.2f}M",
        ha="center",
        va="bottom",
    )

for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.set_ylabel("측정값")
ax.set_title("그룹별 측정값 비교")

dm.simple_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "bar_with_value_labels_kr", formats=("png",), dpi=300
)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'bar_with_value_labels_kr.png'}")
