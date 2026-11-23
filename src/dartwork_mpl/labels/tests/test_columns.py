"""``dm.place_columns`` on real charts: the distances it leaves, measured."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

import dartwork_mpl as dm

SHARES = [58, 46, 39, 25, 13, 7]
AREAS = ["Security", "Analytics", "Automation", "Training", "Travel", "Offices"]


def bars() -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=dm.figsize("14cm", 0.6))
    ax.barh(AREAS, SHARES)
    ax.set(xlim=(0, 60), xlabel="Share (%)")
    return fig, ax


def column(ax: Axes, x: float, strings: list[str], ha: str) -> list[Text]:
    side = ax.get_yaxis_transform()
    return [
        ax.text(x, y, s, transform=side, ha=ha, va="center")
        for y, s in enumerate(strings)
    ]


def box(texts: list[Text]) -> Bbox:
    return Bbox.union([t.get_window_extent() for t in texts])


def test_columns_sit_a_text_size_from_the_plot_and_a_gutter_apart():
    with dm.style.context("report"):
        fig, ax = bars()
        net = column(ax, 1.3, [f"{v - 30:+d}" for v in SHARES], "right")
        count = column(ax, 1.9, [f"{v * 131:,}" for v in SHARES], "right")
        dm.place_columns(ax, net, count)
        dm.simple_layout(fig)
        found = dm.check(fig)
        em = dm.fs(0) * fig.dpi / 72
        first, second = box(net), box(count)
        assert first.x0 - ax.bbox.x1 == pytest.approx(em, abs=1)
        assert second.x0 - first.x1 == pytest.approx(1.5 * em, abs=1)
        assert {round(t.get_window_extent().x1) for t in net} == {
            round(first.x1)
        }
        assert second.x1 <= fig.bbox.x1
        assert not {"TEXT_COLUMN_GAP", "OVERFLOW"} & set(found.rules)
        plt.close(fig)


def test_a_left_column_clears_the_tick_labels():
    with dm.style.context("report"):
        fig, ax = bars()
        rank = column(ax, -0.5, [f"#{i + 1}" for i in range(6)], "left")
        dm.place_columns(ax, rank)
        dm.simple_layout(fig)
        em = dm.fs(0) * fig.dpi / 72
        ticks = box(ax.get_yticklabels())
        assert ticks.x0 - box(rank).x1 == pytest.approx(1.5 * em, abs=1)
        assert box(rank).x0 >= 0
        plt.close(fig)


def test_decimal_rows_and_a_heading_move_as_one_block():
    with dm.style.context("report"):
        fig, ax = bars()
        values = column(
            ax, 1.4, ["8.6", "96.8", "412.3", "9.0", "12.4", "1.5"], "left"
        )
        head = ax.annotate(
            "Sales",
            (1.4, -0.7),
            xycoords=ax.get_yaxis_transform(),
            annotation_clip=False,
        )
        rows = dm.align_texts(values, "decimal")
        before = box(rows).x0 - head.get_window_extent().x0
        dm.place_columns(ax, [head, *rows])
        dm.simple_layout(fig)
        em = dm.fs(0) * fig.dpi / 72
        assert box([head, *rows]).x0 - ax.bbox.x1 == pytest.approx(em, abs=1)
        after = box(rows).x0 - head.get_window_extent().x0
        assert after == pytest.approx(before, abs=1)
        plt.close(fig)


def test_a_heading_wider_than_its_rows_runs_on_over_the_plot():
    with dm.style.context("report"):
        fig, ax = bars()
        ax.set_ylim(5.6, -1.4)
        change = column(ax, 1.5, [f"{v - 30:+d}" for v in SHARES], "right")
        head = ax.text(
            1.5,
            -0.9,
            "Change since the last survey (points)",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
        )
        dm.place_columns(ax, [head, *change])
        dm.simple_layout(fig)
        em = dm.fs(0) * fig.dpi / 72
        assert box(change).x0 - ax.bbox.x1 == pytest.approx(em, abs=1)
        assert head.get_window_extent().x1 == pytest.approx(
            box(change).x1, abs=1
        )
        assert head.get_window_extent().x0 < ax.bbox.x1
        assert "TEXT_COLUMN_GAP" not in dm.check(fig).rules
        plt.close(fig)
