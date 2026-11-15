"""The tick text a realistic axis shows after ``dm.simple_layout``: the text-level judge.

Each row draws one ordinary chart (13 cm, 4:3) and reads the in-view major
tick labels of one axis. The expected text was read from the code before the
``ticks`` rebuild; it is the held look, so a row changes only with an owner's
decision, never to make a rebuild pass.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes

import dartwork_mpl as dm

MONTHS = np.arange("2024-01", "2025-01", dtype="datetime64[M]")
DAYS = np.arange("2024-03-01", "2024-04-01", dtype="datetime64[D]")
QUARTERS = np.arange("2022-01", "2025-01", 3, dtype="datetime64[M]")
YEARS = np.arange(2015, 2025)
M = "\u2212"  # the minus sign matplotlib draws
WAVE = np.sin(np.linspace(0, 10, 100)) * 1e6


@dataclass(frozen=True)
class Row:
    """One chart, the axis read, and the tick text and axis name it must show."""

    name: str
    preset: str
    draw: Callable[[Axes], object]
    axis: str
    ticks: tuple[str, ...]
    label: str = ""
    config: dict[str, object] = field(default_factory=dict)


ROWS = (
    # Numbers.
    Row("plain-thousands", "report", lambda ax: ax.plot([0, 1, 2, 3], [0, 600, 1200, 1750]), "y",
        ("0", "250", "500", "750", "1,000", "1,250", "1,500", "1,750")),
    Row("signed-decimals", "scientific", lambda ax: ax.plot([0, 1], [-1, 1.2]), "y",
        (f"{M}1.0", f"{M}0.5", "0.0", "0.5", "1.0")),
    Row("default-millions", "report", lambda ax: ax.plot([0, 1, 2], [0, 2.5e6, 4e6]), "y",
        ("0", "1M", "2M", "3M", "4M")),
    # Korean numbers (a Korean title makes the figure Korean).
    Row("kr-man", "report-kr", lambda ax: ax.plot([0, 1, 2], [1.0e6, 1.8e6, 2.6e6]), "y",
        ("100만", "125만", "150만", "175만", "200만", "225만", "250만", "275만")),
    Row("kr-eok", "report-kr", lambda ax: ax.plot([0, 1, 2], [0, 0.9e8, 1.75e8]), "y",
        ("0", "0.25억", "0.50억", "0.75억", "1.00억", "1.25억", "1.50억", "1.75억")),
    Row("kr-whole-man", "report-kr", lambda ax: (ax.plot([0, 1, 2], [0, 0.9e8, 1.75e8]), dm.format_axis_myriad(ax, unit="whole")), "y",
        ("0", "2,500만", "5,000만", "7,500만", "10,000만", "12,500만", "15,000만", "17,500만")),
    Row("kr-si-asked", "report-kr", lambda ax: ax.plot([0, 1, 2], [1.0e6, 1.8e6, 2.6e6]), "y",
        ("1.00M", "1.25M", "1.50M", "1.75M", "2.00M", "2.25M", "2.50M", "2.75M"), config={"number_ladder": "si"}),
    # Years and dates.
    Row("whole-years", "report", lambda ax: ax.plot(YEARS, np.arange(10)), "x",
        ("16", "18", "20", "22", "24")),
    Row("whole-years-4", "report", lambda ax: ax.plot(YEARS, np.arange(10)), "x",
        ("2016", "2018", "2020", "2022", "2024"), config={"tick_years": 4}),
    Row("monthly-bars", "report", lambda ax: ax.bar(MONTHS, np.arange(12) + 1), "x",
        ("24.01", "24.03", "24.05", "24.07", "24.09", "24.11")),
    # Changed with the concise date style's deletion (was "monthly-concise":
    # 24, Mar, May ... under config date_style="concise").
    Row("monthly-line", "report", lambda ax: ax.plot(MONTHS, np.arange(12)), "x",
        ("24.01", "24.03", "24.05", "24.07", "24.09", "24.11")),
    Row("daily", "report", lambda ax: ax.plot(DAYS, np.arange(31)), "x",
        ("24.03.01", "24.03.08", "24.03.15", "24.03.22", "24.04.01")),
    Row("quarterly", "report", lambda ax: ax.plot(QUARTERS, np.arange(12)), "x",
        ("22.Q1", "22.Q2", "22.Q3", "22.Q4", "23.Q1", "23.Q2", "23.Q3", "23.Q4", "24.Q1", "24.Q2", "24.Q3", "24.Q4")),
)  # fmt: skip


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
def test_tick_text(row: Row) -> None:
    with dm.config.override(**row.config):
        dm.style.use(row.preset)
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        try:
            row.draw(ax)
            if row.preset.endswith("-kr"):
                ax.set_title("한국어 제목")
            dm.simple_layout(fig)
            fig.canvas.draw()
            axis = ax.xaxis if row.axis == "x" else ax.yaxis
            lo, hi = sorted(axis.get_view_interval())
            slack = 1e-9 * (hi - lo)
            shown = tuple(
                tick.label1.get_text()
                for tick in axis.get_major_ticks()
                if lo - slack <= tick.get_loc() <= hi + slack
            )
            assert (shown, axis.label.get_text()) == (row.ticks, row.label)
        finally:
            plt.close(fig)
