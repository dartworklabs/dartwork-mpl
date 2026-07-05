"""정규분포 오버레이가 있는 히스토그램 (한글).

합성 정규분포 데이터의 밀도 히스토그램 위에 해석적 정규분포 PDF를 겹쳐 그립니다.

실행:
    uv run python examples/plot_histogram_normal_fit_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

rng = np.random.default_rng(42)
data = rng.normal(100, 15, 1000)

ax.hist(
    data,
    bins=30,
    density=True,
    alpha=0.7,
    edgecolor="black",
    linewidth=0.5,
    label="관측 데이터",
)

mu, std = data.mean(), data.std()
xmin, xmax = ax.get_xlim()
xx = np.linspace(xmin, xmax, 100)
pdf = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((xx - mu) / std) ** 2)
ax.plot(
    xx,
    pdf,
    "r-",
    linewidth=2,
    label=f"정규분포\n평균={mu:.1f}, 표준편차={std:.1f}",
)

ax.set_xlabel("값")
ax.set_ylabel("확률 밀도")
ax.set_title("분포 분석")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "histogram_normal_fit_kr", formats=("png",), dpi=300
)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'histogram_normal_fit_kr.png'}")
