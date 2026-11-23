"""Charts whose text runs over more than one background (#810).

Each builder draws one chart and returns its figure with the texts placed
over the data, laid out and as an agent drew them: nothing is fixed here.
The check tests read them, the labels tests mend them with ``dm.legible``
and the pixel scenarios keep two of the mended ones.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.text import Text

import dartwork_mpl as dm

Scene = Callable[[], tuple[Figure, list[Text]]]


def wind_rose() -> tuple[Figure, list[Text]]:
    """Polar stacked bars coloured from a colormap; the note on the busiest
    direction runs from the white canvas over the pale and the dark bars."""
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
    return fig, [note]


def point_cloud() -> tuple[Figure, list[Text]]:
    """A translucent cloud of designs with the chosen one named on it: the
    note reads everywhere (6:1), the points only break it up."""
    dm.style.use("report")
    rng = np.random.default_rng(16)
    cost = rng.gamma(5.0, 22.0, 900) + 40
    loss = 900 / cost + rng.gamma(2.0, 1.6, 900)
    life = 30 - 0.06 * cost + rng.normal(0, 3, 900)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
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
    return fig, [note]


def contour_labels() -> tuple[Figure, list[Text]]:
    """The issue's reproduction: grey contour numbers on bands that run
    from pale to nearly black."""
    dm.style.use("report")
    T, P = np.meshgrid(np.linspace(10, 30, 200), np.linspace(20, 100, 200))
    Z = 7.2 - 0.12 * (T - 10) - 2.4 * ((P - 70) / 50) ** 2
    fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "standard"))
    levels = np.arange(3.0, 7.6, 0.5)
    ax.contourf(T, P, Z, levels=levels, cmap="dc.teal")
    lines = ax.contour(
        T, P, Z, levels=levels[::2], colors="dc.gray8", linewidths=dm.lw(-1)
    )
    labels = ax.clabel(lines, fmt="%.1f", fontsize=dm.fs(-2))
    ax.set(xlabel="Wet-bulb (°C)", ylabel="Part load (%)")
    dm.simple_layout(fig)
    return fig, list(labels)


def vertical_note() -> tuple[Figure, list[Text]]:
    """A note written up a stacked bar: pale, mid and dark segments."""
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
    return fig, [note]


def korean_note() -> tuple[Figure, list[Text]]:
    """Korean preset: a note from the canvas onto a brand-navy bar."""
    dm.style.use("report-kr")
    quarters = ["1분기", "2분기", "3분기", "4분기"]
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    ax.bar(
        quarters,
        [62, 78, 131, 96],
        color=["dc.gray3", "dc.gray3", "#0b2a5b", "dc.gray3"],
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
    return fig, [note]


#: The scenes with ink under 3:1: all of some texts, or part of one.
FAINT: dict[str, Scene] = {
    "wind_rose": wind_rose,
    "vertical_note": vertical_note,
    "contour_labels": contour_labels,
    "korean_note": korean_note,
}
