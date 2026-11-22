"""The real cases of #810 and #812, before and after, for the contact sheet.

``uv run python -m spike.split_text.cases [out_dir]`` writes PNGs (and a
PDF and an SVG of the forest plot and the wind rose) and ``index.html``.
The default folder is git-ignored in the main checkout; nothing is
committed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

from . import columns, legible
from .columns import text_columns
from .sheet import write_sheet

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.figure import Figure
    from matplotlib.text import Text

OUT = Path("/Users/lsw91/Workspace/dartwork-mpl/evals/runs/review/split-text")
DPI = 200

# -- #812: columns -------------------------------------------------------------

STUDIES = "ABCDEFGHIJ"
YEARS = [2014, 2014, 2015, 2016, 2016, 2017, 2018, 2019, 2021, 2022]
EFFECT = [9.4, 0.8, -2.1, 12.6, 4.3, -0.4, 6.9, 15.2, 3.0, -5.7]
SE = [3.55, 2.25, 1.9, 5.3, 1.4, 3.1, 2.6, 6.1, 0.9, 4.2]


def forest_axes() -> tuple[Figure, plt.Axes, np.ndarray]:
    """The forest plot's marks, shared by before and after."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("14cm", "6.5cm"))
    ypos = np.arange(len(STUDIES))[::-1]
    eff, se = np.array(EFFECT), np.array(SE)
    ax.errorbar(
        eff,
        ypos,
        xerr=1.96 * se,
        fmt="s",
        color="dc.gray8",
        markersize=3.5,
        linewidth=dm.lw(0),
        capsize=0,
    )
    ax.axvline(0, color="dc.gray5", linewidth=dm.lw(-1), linestyle="--")
    ax.set_xlabel("Mean difference (mmHg)")
    ax.set_ylim(-0.7, len(STUDIES) - 0.3)
    ax.spines["left"].set_visible(False)
    return fig, ax, ypos


def forest_before() -> Figure:
    """As the issue drew it: one string per side."""
    fig, ax, ypos = forest_axes()
    names = [f"Study {c} ({y})" for c, y in zip(STUDIES, YEARS, strict=True)]
    ax.set_yticks(ypos, names)
    ax.tick_params(axis="y", length=0)
    trans = ax.get_yaxis_transform()
    for yy, e, s in zip(ypos, EFFECT, SE, strict=True):
        ax.text(
            1.02,
            yy,
            f"{e:.1f} [{e - 1.96 * s:.1f}, {e + 1.96 * s:.1f}]",
            transform=trans,
            va="center",
            ha="left",
        )
    dm.simple_layout(fig)
    return fig


def forest_after() -> Figure:
    """Name and year columns on the left, the estimate on the right."""
    fig, ax, ypos = forest_axes()
    names = [f"Study {c}" for c in STUDIES]
    text_columns(
        ax,
        ypos,
        [names, [str(y) for y in YEARS]],
        side="left",
        header=["Study", "Year"],
    )
    cells = [
        f"{e:.1f} [{e - 1.96 * s:.1f}, {e + 1.96 * s:.1f}]"
        for e, s in zip(EFFECT, SE, strict=True)
    ]
    text_columns(ax, ypos, [cells], header=["Effect [95% CI]"])
    dm.simple_layout(fig)
    return fig


REGIONS = ["Seoul", "Gyeonggi", "Busan", "Incheon", "Daegu", "Jeju"]
SALES = [1240.5, 987.0, 412.3, 96.8, 1012.4, 8.6]


def bars_axes(names: list[str], preset: str) -> tuple[Figure, plt.Axes]:
    """Sorted horizontal bars whose values go in a column."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "6cm"))
    order = np.argsort(SALES)
    ax.barh([names[i] for i in order], [SALES[i] for i in order])
    ax.set_xlabel("Revenue (USD m)" if preset == "report" else "매출 (억 원)")
    return fig, ax


def bar_cells() -> list[str]:
    """``value (share)`` per bar, in drawn order (smallest at the bottom)."""
    total = sum(SALES)
    return [f"{v:,.1f} ({v / total:.1%})" for v in sorted(SALES)]


def bars_before() -> Figure:
    """A ``value (share)`` string at each bar end."""
    fig, ax = bars_axes(REGIONS, "report")
    for i, (v, cell) in enumerate(zip(sorted(SALES), bar_cells(), strict=True)):
        ax.text(v + 15, i, cell, va="center", ha="left")
    ax.set_xlim(0, 1700)
    dm.simple_layout(fig)
    return fig


def bars_after() -> Figure:
    """The same strings as one decimal-aligned column."""
    fig, ax = bars_axes(REGIONS, "report")
    text_columns(ax, range(len(SALES)), [bar_cells()], header=["USD m (share)"])
    ax.set_xticks([])  # the column carries the values
    ax.spines["bottom"].set_visible(False)
    ax.set_xlabel("")
    dm.simple_layout(fig)
    return fig


KR_REGIONS = ["서울", "경기", "부산", "인천", "대구", "제주"]


def korean_before() -> Figure:
    """Korean preset: one string per bar."""
    fig, ax = bars_axes(KR_REGIONS, "report-kr")
    for i, (v, cell) in enumerate(zip(sorted(SALES), bar_cells(), strict=True)):
        ax.text(v + 15, i, cell, va="center", ha="left")
    ax.set_xlim(0, 1700)
    dm.simple_layout(fig)
    return fig


def korean_after() -> Figure:
    """Korean preset: names, values and shares as three columns."""
    fig, ax = bars_axes(KR_REGIONS, "report-kr")
    order = np.argsort(SALES)
    total = sum(SALES)
    text_columns(
        ax,
        range(len(SALES)),
        [[KR_REGIONS[i] for i in order]],
        side="left",
        header=["지역"],
    )
    text_columns(
        ax,
        range(len(SALES)),
        [
            [f"{SALES[i]:,.1f}" for i in order],
            [f"{SALES[i] / total:.1%}" for i in order],
        ],
        header=["매출", "비중"],
    )
    dm.simple_layout(fig)
    return fig


# -- #810: one text over several backgrounds -----------------------------------


def wind_rose() -> tuple[Figure, Text]:
    """Polar stacked bars; the note on the busiest direction runs from the
    white canvas over the pale and the dark bars."""
    dm.style.use("report")
    rng = np.random.default_rng(14)
    n = 16
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    base = 3.2 + 2.6 * np.cos(theta - np.deg2rad(315)) ** 2
    bins = ["0-2 m/s", "2-4 m/s", "4-6 m/s", "6-9 m/s", "> 9 m/s"]
    share = np.array([0.26, 0.28, 0.22, 0.15, 0.09])
    hours = base[None, :] * share[:, None] * rng.uniform(0.85, 1.15, (5, n))
    fig, ax = plt.subplots(
        figsize=dm.figsize("11cm", "square"), subplot_kw={"projection": "polar"}
    )
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    bottom = np.zeros(n)
    shades = matplotlib.colormaps["dc.blue"](np.linspace(0.15, 1.0, len(bins)))
    for row, label, colour in zip(hours, bins, shades, strict=True):
        ax.bar(
            theta,
            row,
            width=2 * np.pi / n * 0.9,
            bottom=bottom,
            color=colour,
            label=label,
        )
        bottom += row
    ax.set_xticks(theta[::2], ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    ax.set_yticks([2, 4, 6], ["2%", "4%", "6%"])
    ax.set_rlabel_position(100)
    peak = int(np.argmax(bottom))
    note = ax.annotate(
        f"NW: {bottom[peak]:.1f}% of hours",
        xy=(theta[peak], bottom[peak] * 0.86),
        ha="center",
        va="center",
        fontsize=dm.fs(1),
        fontweight=dm.fw(1),
    )
    dm.place_legend(ax, loc="below")
    dm.simple_layout(fig)
    return fig, note


def pareto() -> tuple[Figure, Text]:
    """A semi-transparent cloud of designs with the chosen one named on it."""
    dm.style.use("report")
    rng = np.random.default_rng(16)
    cost = rng.gamma(5.0, 22.0, 900) + 40
    loss = 900 / cost + rng.gamma(2.0, 1.6, 900)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    life = 30 - 0.06 * cost + rng.normal(0, 3, 900)
    points = ax.scatter(
        cost, loss, s=14, alpha=0.6, linewidths=0, c=life, cmap="viridis"
    )
    fig.colorbar(points, ax=ax, label="Service life (years)")
    pick = int(np.argmin(np.hypot((cost - 120) / 100, (loss - 9.5) / 10)))
    ax.scatter(cost[pick], loss[pick], s=28, color="dc.red6", zorder=3)
    note = ax.annotate(
        "Chosen design: 121 k USD, 9.4 % loss",
        xy=(cost[pick], loss[pick]),
        xytext=(6, 6),
        textcoords="offset points",
        zorder=4,
    )
    ax.set(xlabel="Cost (k USD)", ylabel="Energy loss (%)", xlim=(40, 300))
    dm.simple_layout(fig)
    return fig, note


def contour() -> tuple[Figure, list[Text]]:
    """The issue's reproduction: contour labels across pale and dark bands."""
    dm.style.use("report")
    T, P = np.meshgrid(np.linspace(10, 30, 200), np.linspace(20, 100, 200))
    Z = 7.2 - 0.12 * (T - 10) - 2.4 * ((P - 70) / 50) ** 2
    fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "standard"))
    lv = np.arange(3.0, 7.6, 0.5)
    ax.contourf(T, P, Z, levels=lv, cmap="dc.teal")
    cs = ax.contour(
        T, P, Z, levels=lv[::2], colors="dc.gray8", linewidths=dm.lw(-1)
    )
    labels = ax.clabel(cs, fmt="%.1f", fontsize=dm.fs(-2))
    ax.set(xlabel="Wet-bulb (°C)", ylabel="Part load (%)")
    dm.simple_layout(fig)
    return fig, list(labels)


def rotated() -> tuple[Figure, Text]:
    """A vertical note up a stacked bar: pale, mid and dark segments."""
    dm.style.use("report")
    years = ["2021", "2022", "2023", "2024"]
    parts = np.array(
        [[22, 24, 25, 27], [18, 21, 26, 30], [9, 12, 19, 31], [4, 6, 9, 14]]
    )
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    bottom = np.zeros(4)
    shades = matplotlib.colormaps["dc.indigo"](np.linspace(0.2, 1.0, 4))
    for row, colour in zip(parts, shades, strict=True):
        ax.bar(years, row, bottom=bottom, color=colour, width=0.62)
        bottom += row
    note = ax.text(
        3,
        bottom[-1] / 2,
        "Record year: 102 GWh shipped",
        rotation=90,
        ha="center",
        va="center",
        fontweight=dm.fw(1),
    )
    ax.set_ylabel("Shipments (GWh)")
    dm.simple_layout(fig)
    return fig, note


def korean_note() -> tuple[Figure, Text]:
    """Korean preset: a note from the canvas onto a brand-navy bar."""
    dm.style.use("report-kr")
    names = ["1분기", "2분기", "3분기", "4분기"]
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    ax.bar(
        names,
        [62, 78, 131, 96],
        color=["dc.gray3"] * 2 + ["#0b2a5b", "dc.gray3"],
    )
    note = ax.text(
        1.72,
        110,
        "3분기 매출 131억 원으로 최고",
        ha="center",
        va="center",
        fontweight=dm.fw(1),
    )
    ax.set_ylabel("매출 (억 원)")
    dm.simple_layout(fig)
    return fig, note


SCENES: dict[str, Callable[[], tuple[Figure, Text | list[Text]]]] = {
    "windrose": wind_rose,
    "pareto": pareto,
    "contour": contour,
    "rotated": rotated,
    "korean-note": korean_note,
}


def forest_bold() -> Figure:
    """The issue's wording: a bold header row."""
    columns.BOLD_HEADER = True
    try:
        return forest_after()
    finally:
        columns.BOLD_HEADER = False


def forest_fixed() -> Figure:
    """The other bracket look: every bracket in a column of its own."""
    columns.HUG_BRACKETS = False
    try:
        return forest_after()
    finally:
        columns.HUG_BRACKETS = True


COLUMNS: dict[str, tuple[Callable[[], Figure], Callable[[], Figure]]] = {
    "forest": (forest_before, forest_after),
    "bars": (bars_before, bars_after),
    "korean-bars": (korean_before, korean_after),
}


def save(fig: Figure, out: Path, stem: str, formats: tuple[str, ...]) -> str:
    """Save ``fig`` as ``stem`` and say what ``dm.check`` sees in it."""
    found = dm.check(fig)
    dm.save_formats(fig, str(out / stem), formats=formats, dpi=DPI)
    plt.close(fig)
    return str(found)


def main(out: Path) -> None:
    """Render every case and write the contact sheet."""
    out.mkdir(parents=True, exist_ok=True)
    dm.quiet()
    reports: dict[str, str] = {}
    for name, (before, after) in COLUMNS.items():
        vector = ("png", "pdf", "svg") if name == "forest" else ("png",)
        reports[f"{name}-before"] = save(
            before(), out, f"{name}-before", ("png",)
        )
        reports[f"{name}-after"] = save(after(), out, f"{name}-after", vector)
    for how, variant in (("bold", forest_bold), ("fixed", forest_fixed)):
        reports[f"forest-{how}"] = save(
            variant(), out, f"forest-{how}", ("png",)
        )
    for name, scene in SCENES.items():
        for how in legible.CANDIDATES:
            fig, texts = scene()
            group = texts if isinstance(texts, list) else [texts]
            note = legible.apply(how, fig, group)
            vector = (
                ("png", "pdf", "svg")
                if (name, how)
                in {("windrose", "knockout"), ("contour", "auto")}
                else ("png",)
            )
            key = f"{name}-{how}"
            reports[key] = note + save(fig, out, key, vector)
    write_sheet(out, reports)
    print(f"wrote {out / 'index.html'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
