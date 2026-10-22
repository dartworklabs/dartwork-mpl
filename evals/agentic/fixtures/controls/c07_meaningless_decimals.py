"""Control: integer-valued ticks and bar labels printed with a useless '.0'."""
# expect: meaningless_decimals

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

fig, ax = plt.subplots(figsize=(4, 3))
bars = ax.bar(["a", "b", "c"], [100, 200, 300])
ax.bar_label(bars, fmt="%.1f")
ax.set_yticks([0, 100, 200, 300])
ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
