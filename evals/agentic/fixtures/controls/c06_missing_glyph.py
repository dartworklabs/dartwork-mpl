"""Control: Korean text with a font that has no Hangul glyphs."""
# expect: missing_glyphs

from pathlib import Path

import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([1, 2, 3], [1, 2, 3])
ax.set_title("월별 매출")
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
