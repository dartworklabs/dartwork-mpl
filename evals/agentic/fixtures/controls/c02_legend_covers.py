"""Control: a legend placed on top of the lines."""
# expect: legend_covers_data

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 50)
fig, ax = plt.subplots(figsize=(4, 3))
ax.plot(x, x, label="rising")
ax.plot(x, 10 - x, label="falling")
ax.legend(loc="center")
Path("out").mkdir(exist_ok=True)
fig.savefig("out/figure.png")
fig.savefig("out/figure.pdf")
