"""도넛 차트 스타일의 파이 차트 (한글).

다섯 개의 범주가 전체에서 차지하는 비중을 도넛 형태의 파이 차트로 나타냅니다.

실행:
    uv run python examples/plot_donut_composition_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))

sizes = [35, 30, 20, 10, 5]
labels = ["범주 A", "범주 B", "범주 C", "범주 D", "기타"]
colors = ["oc.blue6", "oc.red6", "oc.teal5", "oc.orange5", "oc.grape6"]

wedges, _texts, autotexts = ax.pie(
    sizes,
    labels=labels,
    colors=colors,
    autopct="%1.1f%%",
    startangle=90,
    pctdistance=0.85,
)

# 도넛 홀.
circle = plt.Circle((0, 0), 0.70, fc="white")
ax.add_artist(circle)

ax.text(
    0, 0, "구성 비율", ha="center", va="center", fontsize=14, fontweight="bold"
)

for autotext in autotexts:
    autotext.set_color("white")
    autotext.set_fontsize(10)
    autotext.set_fontweight("bold")

ax.set_title("범주별 구성")

dm.simple_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "donut_composition_kr", formats=("png",), dpi=300
)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'donut_composition_kr.png'}")
