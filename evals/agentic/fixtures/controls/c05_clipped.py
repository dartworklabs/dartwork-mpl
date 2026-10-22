"""Control: a y label cut by the left edge of the canvas."""
# expect: text_clipped

from pathlib import Path

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([1, 2, 3], [100, 400, 900])
ax.set_ylabel("Revenue (thousand USD)")
fig.subplots_adjust(left=0.12)
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
