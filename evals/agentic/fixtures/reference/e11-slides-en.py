"""Dose-response, slide version (presentation)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("presentation")

df = pd.read_csv("data/dose_response.csv")

fig, ax = plt.subplots(figsize=dm.figsize("25.4cm", "slide"))
ax.errorbar(
    df["dose_uM"],
    df["response_pct"],
    yerr=df["sem"],
    marker="o",
    markersize=6,
    capsize=4,
    color="dc.blue5",
    label="Compound X",
)
ax.set_xscale("log")
ax.set_xlabel("Dose (µM)")
ax.set_ylabel("Response (%)")
ax.set_ylim(0, 100)
ax.legend(loc="upper left")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
