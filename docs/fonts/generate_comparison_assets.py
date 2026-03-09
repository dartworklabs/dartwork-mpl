#!/usr/bin/env python3
"""Generate Before/After and Chart Context demo SVGs for font docs.

Run: uv run python docs/fonts/generate_comparison_assets.py
Output: docs/fonts/_generated/*.svg
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

OUT_DIR = Path(__file__).parent / "_generated"

QUARTERS = ["t=0", "t=1", "t=2", "t=3", "t=4", "t=5", "t=6", "t=7"]
OUTPUT = [820, 870, 910, 980, 1050, 1120, 1190, 1280]
EFFICIENCY = [18.5, 19.2, 20.1, 21.0, 22.3, 23.1, 24.0, 24.8]


def generate_before_after() -> None:
    """Generate Before (default mpl) vs After (dartwork) SVGs."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import dartwork_mpl as dm

    # ── LEFT: Default matplotlib (reset to defaults) ──
    plt.rcdefaults()
    fig_before, ax = plt.subplots(figsize=(5.5, 4))
    ax.bar(QUARTERS, OUTPUT, color="#1f77b4", alpha=0.7)
    ax.set_title("Default matplotlib", fontsize=14)
    ax.set_ylabel("Output (units/s)")
    ax.set_xlabel("Phase")
    ax2 = ax.twinx()
    ax2.plot(QUARTERS, EFFICIENCY, "r-o", markersize=4)
    ax2.set_ylabel("Efficiency (%)")
    ax.tick_params(axis="x", rotation=45)
    fig_before.tight_layout()
    fig_before.savefig(
        OUT_DIR / "before_default.svg", format="svg", bbox_inches="tight"
    )
    plt.close(fig_before)
    print("[comparison] wrote before_default.svg")

    # ── RIGHT: dartwork-mpl styled ──
    dm.style.use("presentation")
    fig_after, ax = plt.subplots(figsize=(5.5, 4))
    ax.bar(
        QUARTERS,
        OUTPUT,
        color="oc.teal5",
        width=0.6,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_title("dartwork-mpl", fontsize=dm.fs(1), fontweight="bold", pad=12)
    ax.set_ylabel("Output (units/s)", fontsize=dm.fs(0))
    ax.set_xlabel("Phase", fontsize=dm.fs(0))
    ax2 = ax.twinx()
    ax2.plot(
        QUARTERS,
        EFFICIENCY,
        "-o",
        color="oc.orange5",
        markersize=5,
        linewidth=2,
    )
    ax2.set_ylabel("Efficiency (%)", fontsize=dm.fs(0))
    ax.tick_params(axis="x", rotation=45, labelsize=dm.fs(-0.5))
    ax.tick_params(axis="y", labelsize=dm.fs(-0.5))
    ax2.tick_params(axis="y", labelsize=dm.fs(-0.5))
    dm.simple_layout(fig_after)
    fig_after.savefig(
        OUT_DIR / "after_dartwork.svg", format="svg", bbox_inches="tight"
    )
    plt.close(fig_after)
    print("[comparison] wrote after_dartwork.svg")


def generate_chart_context() -> None:
    """Generate annotated chart showing font roles in context."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import dartwork_mpl as dm

    dm.style.use("presentation")

    phases = ["t=0", "t=1", "t=2", "t=3", "t=4", "t=5", "t=6"]
    throughput = [450, 480, 520, 560, 610, 670, 720]
    overhead = [320, 340, 350, 370, 390, 410, 430]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    x = np.arange(len(phases))
    w = 0.35
    ax.bar(
        x - w / 2,
        throughput,
        w,
        color="oc.teal5",
        label="Throughput",
        edgecolor="white",
        linewidth=0.5,
    )
    ax.bar(
        x + w / 2,
        overhead,
        w,
        color="oc.gray4",
        label="Overhead",
        edgecolor="white",
        linewidth=0.5,
    )

    # Title — InterDisplay Bold
    ax.set_title(
        "Experimental Throughput vs Overhead",
        fontfamily="Inter Display",
        fontsize=dm.fs(2),
        fontweight="bold",
        pad=16,
    )

    # Axis labels — default (Roboto)
    ax.set_ylabel("Rate (units/s)", fontsize=dm.fs(0))
    ax.set_xlabel("Phase", fontsize=dm.fs(0))

    ax.set_xticks(x)
    ax.set_xticklabels(phases, fontsize=dm.fs(-0.5))
    ax.tick_params(axis="y", labelsize=dm.fs(-0.5))

    ax.legend(fontsize=dm.fs(-0.5), frameon=False, ncol=2, loc="upper left")

    # Annotations pointing to font roles
    anno_kw = {
        "fontsize": 9,
        "color": "#555",
        "bbox": {
            "boxstyle": "round,pad=0.4",
            "fc": "#f8f8f6",
            "ec": "#ccc",
            "lw": 0.8,
        },
    }
    arrow_kw = {"arrowstyle": "->", "color": "#999", "lw": 1.2}

    ax.annotate(
        "Title -> Inter Display Bold",
        xy=(3.5, 740),
        xytext=(5.2, 780),
        arrowprops=arrow_kw,
        **anno_kw,
    )
    ax.annotate(
        "Axis Labels -> Roboto Regular",
        xy=(-0.5, 400),
        xytext=(0.8, 200),
        arrowprops=arrow_kw,
        **anno_kw,
    )
    ax.annotate(
        "Ticks -> Roboto Light",
        xy=(0, 30),
        xytext=(2.0, 100),
        arrowprops=arrow_kw,
        **anno_kw,
    )

    ax.set_ylim(0, 850)
    dm.simple_layout(fig)
    fig.savefig(
        OUT_DIR / "chart_context.svg", format="svg", bbox_inches="tight"
    )
    plt.close(fig)
    print("[comparison] wrote chart_context.svg")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_before_after()
    generate_chart_context()
    print("[comparison] done — 3 SVGs generated")
