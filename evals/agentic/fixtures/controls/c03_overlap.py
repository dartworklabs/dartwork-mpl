"""Control: two different annotations on the same spot."""
# expect: text_overlap

from pathlib import Path

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 3))
ax.bar(["a", "b"], [3, 5])
ax.text(0, 3.1, "peak sales", ha="center")
ax.text(0.05, 3.15, "record month", ha="center")
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
