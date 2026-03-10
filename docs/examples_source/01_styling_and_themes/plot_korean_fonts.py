"""
Korean Font Support
===================

Adding the ``-kr`` suffix to any preset (e.g., ``report-kr``) instantly loads
Pretendard and appropriate fallback fonts for seamless bilingual (Korean + English)
typesetting — no manual font registration needed.
"""

import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use('report-kr')

fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.6))

categories = ['서울', '부산', '인천', '대구', '광주']
values = [9.4, 3.3, 2.9, 2.3, 1.4]

ax.bar(categories, values, color='tw.blue500', width=0.6)

ax.set_title("대한민국 주요 도시 인구수")
ax.set_ylabel("인구 (백만 명)")

# dm.fs() scales font size relative to the active preset's base
for i, v in enumerate(values):
    ax.text(i, v + 0.15, f"{v}M", ha='center', va='bottom', fontsize=dm.fs(-1))

ax.set_ylim(0, 11)

dm.simple_layout(fig)
