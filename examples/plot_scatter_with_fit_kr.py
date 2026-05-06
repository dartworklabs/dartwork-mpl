"""회귀선이 있는 산점도 (한글).

합성된 상관 데이터를 산점도로 표시하고 ``numpy.polyfit``으로 선형 회귀선을 겹쳐 그립니다.

실행:
    uv run python examples/plot_scatter_with_fit_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))

rng = np.random.default_rng(42)
x = rng.standard_normal(50) * 10 + 50
y = 2 * x + rng.standard_normal(50) * 15 + 100

ax.scatter(x, y, alpha=0.6, s=50, label="데이터 포인트")

z = np.polyfit(x, y, 1)
p = np.poly1d(z)
x_line = np.linspace(x.min(), x.max(), 100)
ax.plot(
    x_line,
    p(x_line),
    "r--",
    alpha=0.8,
    label=f"회귀선: y = {z[0]:.1f}x + {z[1]:.1f}",
)

dm.add_grid(ax, alpha=0.15)
ax.set_xlabel("독립 변수")
ax.set_ylabel("종속 변수")
ax.set_title("상관관계 분석")
ax.legend()

dm.auto_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "scatter_with_fit_kr", formats=("png",), dpi=300
)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'scatter_with_fit_kr.png'}")
