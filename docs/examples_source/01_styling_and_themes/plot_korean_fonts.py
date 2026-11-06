"""
Korean Font Support
===================

Adding the ``-kr`` suffix to any preset (e.g., ``report-kr``) instantly loads
Pretendard and appropriate fallback fonts for seamless bilingual (Korean + English)
typesetting — no manual font registration needed.
"""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report-kr")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "golden"))

categories = ["서울", "부산", "인천", "대구", "광주"]
values = [9.4, 3.3, 2.9, 2.3, 1.4]

ax.bar(categories, values, color="tw.blue500", width=0.6)

ax.set_title("대한민국 주요 도시 인구수")
ax.set_ylabel("인구 (백만 명)")

# dm.label_bars prints each value above its bar, sized from the preset
dm.label_bars(ax, fmt="{}M")

ax.set_ylim(0, 11)

dm.simple_layout(fig)
plt.show()
