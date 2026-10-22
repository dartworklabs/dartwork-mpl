"""Control: a left-aligned title pushed above the canvas."""
# expect: text_outside

from pathlib import Path

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 3))
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_title("Headline that is lost", loc="left", y=1.4)
fig.subplots_adjust(top=0.9)
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
