"""Two side-by-side panels with long axis names squeezed into a single 9 cm journal column."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

t = np.linspace(0, 50, 200)
fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize(dm.col1, "golden"))
left.plot(t, 300 + 20 * np.exp(-t / 10))
left.set(
    xlabel="Time since injection (min)", ylabel="Plasma concentration (ng/mL)"
)
right.plot(t, 1 - np.exp(-t / 15))
right.set(
    xlabel="Time since injection (min)", ylabel="Cumulative excreted fraction"
)

dm.simple_layout(fig)
dm.save_formats(fig, "output/two_panel_single_column", formats=("png",))
