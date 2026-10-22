"""Axis-wide automatic decimals for the scaled axis formatters (#523).

Integer ticks must never print decimals (``200.0`` -> ``200``,
``1.0k`` -> ``1k``); fractional steps keep one decimal count on every
tick (``17.5, 20.0, 22.5``). The observed value is the label text
matplotlib draws, read after a real canvas draw.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib
import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._decimals import fewest_exact_decimals


def _drawn_labels(ax: Axes, which: str = "y") -> list[str]:
    """Labels of the major ticks matplotlib actually draws (inside view)."""
    ax.figure.canvas.draw()
    axis = ax.yaxis if which == "y" else ax.xaxis
    low, high = sorted(ax.get_ylim() if which == "y" else ax.get_xlim())
    slack = 1e-9 * (high - low)
    return [
        label.get_text()
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low - slack <= loc <= high + slack
    ]


def _labels(
    fmt: Callable[..., None],
    ylim: tuple[float, float],
    *,
    log: bool = False,
    ticks: list[float] | None = None,
    **kwargs: object,
) -> list[str]:
    fig, ax = plt.subplots()
    try:
        if log:
            ax.set_yscale("log")
        if ticks is not None:
            ax.set_yticks(ticks)
        ax.set_ylim(*ylim)
        fmt(ax, axis="y", **kwargs)
        return _drawn_labels(ax)
    finally:
        plt.close(fig)


class TestFewestExactDecimals:
    @pytest.mark.parametrize(
        "values,expected",
        [
            ([0, 5, 10], 0),
            ([200.0, 400.0, 1200.0], 0),
            ([17.5, 20.0, 22.5], 1),
            ([0.25, 0.5, 0.75], 2),
            ([0.1 + 0.2, 0.6], 1),  # float noise 0.30000000000000004
            ([1e6 + 2, 1e6 + 4], 0),
            ([], 0),
            ([float("nan"), 3.0], 0),
            ([1e-9], 9),  # a log-axis decade still prints exactly
            ([5.551115123125783e-17, 0.2, 0.4], 1),  # zero-tick float noise
        ],
    )
    def test_fewest_exact(self, values: list[float], expected: int) -> None:
        assert fewest_exact_decimals(values) == expected

    def test_irregular_values_fall_back_to_distinct(self) -> None:
        # Thirds never render exactly; one decimal already keeps them apart.
        assert fewest_exact_decimals([1 / 3, 2 / 3, 1.0]) == 1

    def test_irregular_lone_value_keeps_three_significant_digits(self) -> None:
        assert fewest_exact_decimals([1 / 3]) == 3


class TestFormatAxisSiAuto:
    def test_integer_axis_prints_no_decimals(self) -> None:
        labels = _labels(dm.format_axis_si, (0, 200))
        assert labels == [
            "0",
            "25",
            "50",
            "75",
            "100",
            "125",
            "150",
            "175",
            "200",
        ]

    def test_integer_prefixed_axis_prints_no_decimals(self) -> None:
        assert _labels(dm.format_axis_si, (0, 5000)) == [
            "0",
            "1k",
            "2k",
            "3k",
            "4k",
            "5k",
        ]

    def test_integers_first_beats_a_fractional_prefix(self) -> None:
        # "k" would need 0.2k; no prefix keeps whole numbers (with a comma).
        labels = _labels(dm.format_axis_si, (0, 1300))
        assert labels == ["0", "200", "400", "600", "800", "1,000", "1,200"]

    def test_quarter_steps_stay_whole_without_prefix(self) -> None:
        # 1250 used to print as "1.2k"; it is now an exact whole number.
        ticks = [i * 250.0 for i in range(9)]
        labels = _labels(dm.format_axis_si, (0, 2000), ticks=ticks)
        assert labels == [
            "0",
            "250",
            "500",
            "750",
            "1,000",
            "1,250",
            "1,500",
            "1,750",
            "2,000",
        ]

    def test_shortest_whole_number_unit_wins(self) -> None:
        # Whole in none and in k; "1,000k" is shorter than "1,000,000".
        ticks = [-1e6, -5e5, 0, 5e5, 1e6]
        labels = _labels(dm.format_axis_si, (-1e6, 1e6), ticks=ticks)
        assert labels == ["-1,000k", "-500k", "0", "500k", "1,000k"]

    def test_fractional_axis_keeps_axis_wide_decimals(self) -> None:
        ticks = [0.0, 0.5, 1.0, 1.5]
        labels = _labels(dm.format_axis_si, (0, 1.5), ticks=ticks)
        assert labels == ["0.0", "0.5", "1.0", "1.5"]

    def test_out_of_view_tick_does_not_pick_the_prefix(self) -> None:
        # The locator also returns 1000 (beyond 950); it must not force "k".
        assert _labels(dm.format_axis_si, (0, 950)) == [
            "0",
            "200",
            "400",
            "600",
            "800",
        ]

    def test_negative_ticks_and_zero(self) -> None:
        ticks = [-2e6, -1e6, 0, 1e6, 2e6]
        labels = _labels(dm.format_axis_si, (-2e6, 2e6), ticks=ticks)
        assert labels == ["-2M", "-1M", "0", "1M", "2M"]

    def test_log_axis_uses_a_prefix_per_tick(self) -> None:
        labels = _labels(dm.format_axis_si, (1, 1e6), log=True)
        assert labels == ["1", "10", "100", "1k", "10k", "100k", "1M"]

    def test_log_axis_sub_unit_ticks_take_their_own_decimals(self) -> None:
        labels = _labels(dm.format_axis_si, (0.01, 100), log=True)
        assert labels == ["0.01", "0.1", "1", "10", "100"]

    def test_explicit_decimals_keep_legacy_labels(self) -> None:
        labels = _labels(dm.format_axis_si, (0, 1300), decimals=1)
        assert labels == [
            "0.0",
            "200.0",
            "400.0",
            "600.0",
            "800.0",
            "1.0k",
            "1.2k",
        ]

    def test_both_axes_decide_independently(self) -> None:
        fig, ax = plt.subplots()
        try:
            ax.set_xlim(0, 3000)
            ax.set_ylim(0, 300)
            dm.format_axis_si(ax, axis="both")
            assert (
                ax.xaxis.get_major_formatter()
                is not ax.yaxis.get_major_formatter()
            )
            assert _drawn_labels(ax, "x")[-1] == "3,000"
            assert _drawn_labels(ax, "y") == [
                "0",
                "50",
                "100",
                "150",
                "200",
                "250",
                "300",
            ]
        finally:
            plt.close(fig)

    def test_standalone_call_decides_from_the_value(self) -> None:
        fig, ax = plt.subplots()
        try:
            dm.format_axis_si(ax)
            fmt = ax.yaxis.get_major_formatter()
            assert [fmt(v) for v in (0, 999, 1000, 1500, -2e6)] == [
                "0",
                "999",
                "1k",
                "1,500",
                "-2M",
            ]
        finally:
            plt.close(fig)


class TestFormatAxisMillionsBillionsAuto:
    def test_millions_integer_axis(self) -> None:
        assert _labels(dm.format_axis_millions, (0, 5e6)) == [
            "0",
            "1M",
            "2M",
            "3M",
            "4M",
            "5M",
        ]

    def test_millions_fractional_axis_is_uniform(self) -> None:
        labels = _labels(dm.format_axis_millions, (0, 1.7e6))
        assert labels[:3] == ["0.0", "0.2M", "0.4M"]
        assert "1.0M" in labels

    def test_millions_explicit_decimals_keep_legacy_labels(self) -> None:
        labels = _labels(dm.format_axis_millions, (0, 5e6), decimals=1)
        assert labels == ["0.0", "1.0M", "2.0M", "3.0M", "4.0M", "5.0M"]

    def test_billions_integer_axis(self) -> None:
        assert _labels(dm.format_axis_billions, (0, 5e9)) == [
            "0",
            "1B",
            "2B",
            "3B",
            "4B",
            "5B",
        ]

    def test_billions_custom_suffix(self) -> None:
        labels = _labels(dm.format_axis_billions, (1e9, 2e9), suffix=" bn")
        assert labels == [
            "1.0 bn",
            "1.2 bn",
            "1.4 bn",
            "1.6 bn",
            "1.8 bn",
            "2.0 bn",
        ]


_QUARTERS = [i * 2.5e7 for i in range(8)]  # 0 .. 1.75억 in 2,500만 steps


@pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
class TestFormatAxisMyriadAuto:
    def test_integer_units_print_no_decimals(self) -> None:
        labels = _labels(dm.format_axis_myriad, (1e9, 1.5e10), currency="₩")
        assert labels == [
            "₩20억",
            "₩40억",
            "₩60억",
            "₩80억",
            "₩100억",
            "₩120억",
            "₩140억",
        ]

    def test_ticks_sharing_a_unit_share_decimals(self) -> None:
        labels = _labels(dm.format_axis_myriad, (0, 1.8e8), ticks=_QUARTERS)
        assert labels[:3] == ["0", "2,500만", "5,000만"]
        # 1.25억 / 1.75억 used to print as "1.2억" / "1.8억".
        assert labels[4:] == ["1.00억", "1.25억", "1.50억", "1.75억"]

    def test_explicit_decimals_keep_per_tick_trimming(self) -> None:
        labels = _labels(
            dm.format_axis_myriad, (0, 1.8e8), ticks=_QUARTERS, decimals=1
        )
        assert labels[4:] == ["1억", "1.2억", "1.5억", "1.8억"]
