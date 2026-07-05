"""라인 플롯 (SI 단위 포매팅, 한글).

두 개의 정현파 신호를 같은 축에 표시합니다. 한글 프리셋을 적용하여
라벨·제목·범례가 Paperlogy 폰트로 렌더링되는 것을 확인할 수 있습니다.

실행:
    uv run python examples/plot_line_signals_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

x = np.linspace(0, 10, 100)
y1 = np.sin(x) * 1.5e6
y2 = np.cos(x) * 1.2e6

ax.plot(x, y1, label="신호 A", linewidth=2)
ax.plot(x, y2, label="신호 B", linewidth=2)

dm.format_axis_si(ax, axis="y")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(
    True,
    axis="y",
    color="dc.teal_indigo1",
    alpha=0.2,
    linestyle="--",
    linewidth=0.5,
)
ax.set_axisbelow(True)
for s in ("bottom", "left"):
    ax.spines[s].set_color("dc.teal_indigo3")
    ax.spines[s].set_linewidth(0.5)
ax.grid(True, axis="x", color="dc.teal_indigo1", alpha=0.2, linewidth=0.5)

ax.set_xlabel("시간 (초)")
ax.set_ylabel("진폭")
ax.set_title("신호 분석")
ax.legend(loc="upper right")

dm.simple_layout(fig)
dm.save_formats(fig, OUTPUT_DIR / "line_signals_kr", formats=("png",), dpi=300)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'line_signals_kr.png'}")
