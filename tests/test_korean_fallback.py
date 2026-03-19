import matplotlib.pyplot as plt
import dartwork_mpl as dm
import os

dm.style.use('report')

fig, ax = plt.subplots(figsize=dm.FS_SINGLE)
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_title("테스트 한글 타이틀 (English mixed)")
ax.set_xlabel("X축 (X-axis)")
ax.set_ylabel("Y축 (Y-axis)")

output_path = "/tmp/test_korean_fallback.png"
fig.savefig(output_path)
print(f"Chart saved to {output_path}")
