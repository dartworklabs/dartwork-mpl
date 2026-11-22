"""The same charts with and without aligning their existing text."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm


def forest_alignment(aligned=True):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("14cm", "6.5cm"))
    effect = np.array([9.4, 0.8, -2.1, 12.6, 4.3, -0.4, 6.9, 15.2, 3.0, -5.7])
    error = 1.96 * np.array(
        [3.55, 2.25, 1.9, 5.3, 1.4, 3.1, 2.6, 6.1, 0.9, 4.2]
    )
    years = [2014, 2014, 2015, 2016, 2016, 2017, 2018, 2019, 2021, 2022]
    y = np.arange(len(effect))[::-1]
    ax.errorbar(
        effect,
        y,
        xerr=error,
        fmt="s",
        color="dc.gray8",
        markersize=3.5,
        linewidth=dm.lw(0),
    )
    ax.axvline(0, color="dc.gray5", linewidth=dm.lw(-1), linestyle="--")
    ax.set(xlabel="Mean difference (mmHg)", ylim=(-0.7, 9.7))
    ax.set_yticks(
        y,
        [
            f"Study {name} ({year})"
            for name, year in zip("ABCDEFGHIJ", years, strict=True)
        ],
    )
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    texts = [
        ax.text(
            1.02,
            row,
            f"{value:.1f} [{value - err:.1f}, {value + err:.1f}]",
            transform=ax.get_yaxis_transform(),
            va="center",
        )
        for row, value, err in zip(y, effect, error, strict=True)
    ]
    if aligned:
        dm.align_texts(texts, "decimal")
    dm.simple_layout(fig)
    return fig


def korean_alignment(aligned=True):
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("14cm", "6cm"))
    names = ["제주", "인천", "부산", "경기", "대구", "서울"]
    sales = [8.6, 96.8, 412.3, 987.0, 1012.4, 1240.5]
    ax.barh(names, sales)
    ax.set_xlabel("매출 (억 원)")
    for offset, title, values in (
        (12, "매출", [f"{value:,.1f}" for value in sales]),
        (61, "비중", [f"{value / sum(sales):.1%}" for value in sales]),
    ):
        ax.annotate(
            title,
            (1, 1),
            (offset, 6),
            xycoords=ax.transAxes,
            textcoords="offset points",
            annotation_clip=False,
        )
        texts = [
            ax.annotate(
                value,
                (1, y),
                (offset, 0),
                xycoords=ax.get_yaxis_transform(),
                textcoords="offset points",
                va="center",
                annotation_clip=False,
            )
            for y, value in enumerate(values)
        ]
        if aligned:
            dm.align_texts(texts, "decimal")
    dm.simple_layout(fig)
    return fig
