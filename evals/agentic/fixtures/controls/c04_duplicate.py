"""Control: a panel label drawn twice and a title repeated by suptitle."""
# expect: duplicate_text

from pathlib import Path

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([1, 2, 3], [2, 1, 3])
ax.set_title("Monthly revenue")
fig.suptitle("Monthly revenue")
ax.text(0.02, 0.92, "(a)", transform=ax.transAxes)
ax.text(0.02, 0.92, "(a)", transform=ax.transAxes)
fig.subplots_adjust(top=0.8)
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
