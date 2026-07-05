"""이중 축 시계열 플롯 (한글).

같은 시간 축 위에서 두 가지 서로 다른 스케일의 계열을 시각화합니다.
막대 계열은 좌측 축, 라인 계열은 우측 축에 표시됩니다.

실행:
    uv run python examples/plot_dual_axis_timeseries_kr.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))

# 월별 합성 데이터 (임의 단위).
dates = np.arange("2024-01", "2025-01", dtype="datetime64[M]")
primary = np.array([120, 135, 128, 142, 155, 148, 162, 175, 168, 182, 195, 210])
rng = np.random.default_rng(0)
secondary = primary * 0.15 + rng.standard_normal(12) * 5

ax.bar(dates, primary, alpha=0.3, label="주 계열", color="oc.blue5")
ax.set_xlabel("월")
ax.set_ylabel("주 계열 (단위)", color="oc.blue7")
ax.tick_params(axis="y", labelcolor="oc.blue7")

ax2 = ax.twinx()
ax2.plot(
    dates,
    secondary,
    color="oc.teal6",
    marker="o",
    linewidth=2,
    label="보조 계열",
)
ax2.set_ylabel("보조 계열 (단위)", color="oc.teal7")
ax2.tick_params(axis="y", labelcolor="oc.teal7")

ax.set_title("월별 이중 축 계열")
ax.grid(True, alpha=0.3)

lines, labels = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines + lines2, labels + labels2, loc="upper left")

dm.simple_layout(fig)
dm.save_formats(
    fig, OUTPUT_DIR / "dual_axis_timeseries_kr", formats=("png",), dpi=300
)
plt.close(fig)
print(f"저장: {OUTPUT_DIR / 'dual_axis_timeseries_kr.png'}")
