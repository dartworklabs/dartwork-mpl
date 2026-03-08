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

QUARTERS = [
    "Q1'23", "Q2'23", "Q3'23", "Q4'23",
    "Q1'24", "Q2'24", "Q3'24", "Q4'24",
]
REVENUE = [820, 870, 910, 980, 1050, 1120, 1190, 1280]
MARGIN = [18.5, 19.2, 20.1, 21.0, 22.3, 23.1, 24.0, 24.8]


def generate_before_after() -> None:
    """Generate Before (default mpl) vs After (dartwork) SVGs."""
    import dartwork_mpl as dm

    # ── LEFT: Default matplotlib (reset to defaults) ──
    plt.rcdefaults()
    fig_before, ax = plt.subplots(figsize=(5.5, 4))
    ax.bar(QUARTERS, REVENUE, color="#1f77b4", alpha=0.7)
    ax.set_title("Default matplotlib", fontsize=14)
    ax.set_ylabel("Revenue ($M)")
    ax.set_xlabel("Quarter")
    ax2 = ax.twinx()
    ax2.plot(QUARTERS, MARGIN, "r-o", markersize=4)
    ax2.set_ylabel("Margin (%)")
    ax.tick_params(axis="x", rotation=45)
    fig_before.tight_layout()
    fig_before.savefig(
        OUT_DIR / "before_default.svg",
        format="svg", bbox_inches="tight",
    )
    plt.close(fig_before)
    print("[comparison] wrote before_default.svg")

    # ── RIGHT: dartwork-mpl styled ──
    dm.style.use("presentation")
    fig_after, ax = plt.subplots(figsize=(5.5, 4))
    ax.bar(
        QUARTERS, REVENUE, color="oc.teal5",
        width=0.6, edgecolor="white", linewidth=0.5,
    )
    ax.set_title(
        "dartwork-mpl", fontsize=dm.fs(1),
        fontweight="bold", pad=12,
    )
    ax.set_ylabel("Revenue ($M)", fontsize=dm.fs(0))
    ax.set_xlabel("Quarter", fontsize=dm.fs(0))
    ax2 = ax.twinx()
    ax2.plot(
        QUARTERS, MARGIN, "-o", color="oc.orange5",
        markersize=5, linewidth=2,
    )
    ax2.set_ylabel("Margin (%)", fontsize=dm.fs(0))
    ax.tick_params(axis="x", rotation=45, labelsize=dm.fs(-0.5))
    ax.tick_params(axis="y", labelsize=dm.fs(-0.5))
    ax2.tick_params(axis="y", labelsize=dm.fs(-0.5))
    dm.simple_layout(fig_after)
    fig_after.savefig(
        OUT_DIR / "after_dartwork.svg",
        format="svg", bbox_inches="tight",
    )
    plt.close(fig_after)
    print("[comparison] wrote after_dartwork.svg")


def generate_chart_context() -> None:
    """Generate annotated chart showing font roles in context."""
    import dartwork_mpl as dm

    dm.style.use("presentation")

    quarters = [
        "Q1'24", "Q2'24", "Q3'24", "Q4'24",
        "Q1'25", "Q2'25", "Q3'25",
    ]
    revenue = [450, 480, 520, 560, 610, 670, 720]
    opex = [320, 340, 350, 370, 390, 410, 430]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    x = np.arange(len(quarters))
    w = 0.35
    ax.bar(
        x - w / 2, revenue, w, color="oc.teal5",
        label="Revenue", edgecolor="white", linewidth=0.5,
    )
    ax.bar(
        x + w / 2, opex, w, color="oc.gray4",
        label="OpEx", edgecolor="white", linewidth=0.5,
    )

    # Title — InterDisplay Bold
    ax.set_title(
        "Quarterly Revenue vs Operating Expenses",
        fontfamily="Inter Display", fontsize=dm.fs(2),
        fontweight="bold", pad=16,
    )

    # Axis labels — default (Roboto)
    ax.set_ylabel("USD (millions)", fontsize=dm.fs(0))
    ax.set_xlabel("Quarter", fontsize=dm.fs(0))

    ax.set_xticks(x)
    ax.set_xticklabels(quarters, fontsize=dm.fs(-0.5))
    ax.tick_params(axis="y", labelsize=dm.fs(-0.5))

    ax.legend(
        fontsize=dm.fs(-0.5), frameon=False,
        ncol=2, loc="upper left",
    )

    # Annotations pointing to font roles
    anno_kw = dict(
        fontsize=9, color="#555",
        bbox=dict(
            boxstyle="round,pad=0.4", fc="#f8f8f6",
            ec="#ccc", lw=0.8,
        ),
    )
    arrow_kw = dict(arrowstyle="->", color="#999", lw=1.2)

    ax.annotate(
        "Title → Inter Display Bold",
        xy=(3.5, 740), xytext=(5.2, 780),
        arrowprops=arrow_kw, **anno_kw,
    )
    ax.annotate(
        "Axis Labels → Roboto Regular",
        xy=(-0.5, 400), xytext=(0.8, 200),
        arrowprops=arrow_kw, **anno_kw,
    )
    ax.annotate(
        "Ticks → Roboto Light",
        xy=(0, 30), xytext=(2.0, 100),
        arrowprops=arrow_kw, **anno_kw,
    )

    ax.set_ylim(0, 850)
    dm.simple_layout(fig)
    fig.savefig(
        OUT_DIR / "chart_context.svg",
        format="svg", bbox_inches="tight",
    )
    plt.close(fig)
    print("[comparison] wrote chart_context.svg")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_before_after()
    generate_chart_context()
    print("[comparison] done — 3 SVGs generated")
