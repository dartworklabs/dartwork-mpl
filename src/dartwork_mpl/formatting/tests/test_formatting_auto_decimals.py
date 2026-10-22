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


def _ticks(step: float, n: int, start: float = 0.0) -> list[float]:
    return [start + i * step for i in range(n)]


class TestFormatAxisSiMax:
    """Default ``unit="max"``: one unit from the largest visible tick."""

    def test_integer_axis_below_1000_is_plain(self) -> None:
        labels = _labels(dm.format_axis_si, (0, 800), ticks=_ticks(200, 5))
        assert labels == ["0", "200", "400", "600", "800"]

    def test_largest_tick_picks_k_for_every_tick(self) -> None:
        # 1.2k picks "k" for the axis: no 800 next to 1.2k.
        labels = _labels(dm.format_axis_si, (0, 1200), ticks=_ticks(200, 7))
        assert labels == ["0", "0.2k", "0.4k", "0.6k", "0.8k", "1.0k", "1.2k"]

    def test_quarter_steps_keep_two_decimals_and_stay_exact(self) -> None:
        # 1250 used to print as "1.2k"; every tick now carries two decimals.
        labels = _labels(dm.format_axis_si, (0, 2000), ticks=_ticks(250, 9))
        assert labels == [
            "0",
            "0.25k",
            "0.50k",
            "0.75k",
            "1.00k",
            "1.25k",
            "1.50k",
            "1.75k",
            "2.00k",
        ]

    def test_whole_number_axis_prints_no_decimals(self) -> None:
        labels = _labels(dm.format_axis_si, (0, 5000), ticks=_ticks(1000, 6))
        assert labels == ["0", "1k", "2k", "3k", "4k", "5k"]

    def test_negative_axis_and_zero(self) -> None:
        # line_signals: half steps need one decimal; zero stays a bare 0.
        ticks = _ticks(0.5e6, 5, start=-1e6)
        labels = _labels(dm.format_axis_si, (-1e6, 1e6), ticks=ticks)
        assert labels == ["-1.0M", "-0.5M", "0", "0.5M", "1.0M"]

    def test_all_negative_axis(self) -> None:
        ticks = _ticks(1000, 4, start=-3000)
        labels = _labels(dm.format_axis_si, (-3000, 0), ticks=ticks)
        assert labels == ["-3k", "-2k", "-1k", "0"]

    def test_axis_crossing_a_unit_threshold(self) -> None:
        # 800 → 1.2M: the largest tick (1.2M) sets M for the whole axis.
        ticks = [8e5, 1e6, 1.2e6]
        labels = _labels(dm.format_axis_si, (8e5, 1.2e6), ticks=ticks)
        assert labels == ["0.8M", "1.0M", "1.2M"]

    def test_fractional_axis_below_1000(self) -> None:
        labels = _labels(dm.format_axis_si, (0, 1.5), ticks=_ticks(0.5, 4))
        assert labels == ["0", "0.5", "1.0", "1.5"]

    def test_out_of_view_tick_does_not_pick_the_unit(self) -> None:
        # The locator also returns 1000 (beyond 950); it must not force "k".
        assert _labels(dm.format_axis_si, (0, 950)) == [
            "0",
            "200",
            "400",
            "600",
            "800",
        ]

    def test_log_axis_uses_a_prefix_per_tick(self) -> None:
        # Decades cannot share one unit.
        labels = _labels(dm.format_axis_si, (1, 1e6), log=True)
        assert labels == ["1", "10", "100", "1k", "10k", "100k", "1M"]

    def test_log_axis_sub_unit_ticks_take_their_own_decimals(self) -> None:
        labels = _labels(dm.format_axis_si, (0.01, 100), log=True)
        assert labels == ["0.01", "0.1", "1", "10", "100"]

    def test_both_axes_decide_independently(self) -> None:
        fig, ax = plt.subplots()
        try:
            ax.set_xticks(_ticks(1000, 4))
            ax.set_xlim(0, 3000)
            ax.set_yticks(_ticks(100, 4))
            ax.set_ylim(0, 300)
            dm.format_axis_si(ax, axis="both")
            assert (
                ax.xaxis.get_major_formatter()
                is not ax.yaxis.get_major_formatter()
            )
            assert _drawn_labels(ax, "x") == ["0", "1k", "2k", "3k"]
            assert _drawn_labels(ax, "y") == ["0", "100", "200", "300"]
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
                "1.5k",
                "-2M",
            ]
        finally:
            plt.close(fig)

    def test_explicit_decimals_keep_legacy_labels(self) -> None:
        labels = _labels(
            dm.format_axis_si, (0, 1200), ticks=_ticks(200, 7), decimals=1
        )
        assert labels == [
            "0.0",
            "200.0",
            "400.0",
            "600.0",
            "800.0",
            "1.0k",
            "1.2k",
        ]


class TestFormatAxisSiWhole:
    """``unit="whole"``: a unit in which every visible tick is whole."""

    def test_no_prefix_keeps_whole_numbers(self) -> None:
        labels = _labels(
            dm.format_axis_si, (0, 1200), ticks=_ticks(200, 7), unit="whole"
        )
        assert labels == ["0", "200", "400", "600", "800", "1,000", "1,200"]

    def test_shortest_whole_unit_on_a_negative_axis(self) -> None:
        # Whole in none and in k; "1,000k" is shorter than "1,000,000".
        ticks = _ticks(0.5e6, 5, start=-1e6)
        labels = _labels(
            dm.format_axis_si, (-1e6, 1e6), ticks=ticks, unit="whole"
        )
        assert labels == ["-1,000k", "-500k", "0", "500k", "1,000k"]

    def test_falls_back_to_fewest_decimals(self) -> None:
        labels = _labels(
            dm.format_axis_si, (0, 1.5), ticks=_ticks(0.5, 4), unit="whole"
        )
        assert labels == ["0", "0.5", "1.0", "1.5"]


class TestFormatAxisSiFixedUnit:
    @pytest.mark.parametrize(
        "unit,expected",
        [
            ("", ["-1,000,000", "-500,000", "0", "500,000", "1,000,000"]),
            ("k", ["-1,000k", "-500k", "0", "500k", "1,000k"]),
            ("M", ["-1.0M", "-0.5M", "0", "0.5M", "1.0M"]),
            ("G", ["-0.0010G", "-0.0005G", "0", "0.0005G", "0.0010G"]),
        ],
    )
    def test_fixed_unit_with_automatic_decimals(
        self, unit: str, expected: list[str]
    ) -> None:
        ticks = _ticks(0.5e6, 5, start=-1e6)
        labels = _labels(dm.format_axis_si, (-1e6, 1e6), ticks=ticks, unit=unit)
        assert labels == expected

    def test_fixed_unit_with_fixed_decimals(self) -> None:
        labels = _labels(
            dm.format_axis_si,
            (0, 2000),
            ticks=_ticks(1000, 3),
            unit="k",
            decimals=1,
        )
        assert labels == ["0.0", "1.0k", "2.0k"]

    @pytest.mark.parametrize("unit", ["m", "K", "auto", "억"])
    def test_unknown_unit_raises_before_changing_the_axes(
        self, unit: str
    ) -> None:
        fig, ax = plt.subplots()
        try:
            before = ax.yaxis.get_major_formatter()
            with pytest.raises(ValueError, match="unit must be"):
                dm.format_axis_si(ax, unit=unit)
            assert ax.yaxis.get_major_formatter() is before
        finally:
            plt.close(fig)


class TestFormatAxisMillionsBillionsAuto:
    def test_millions_integer_axis(self) -> None:
        assert _labels(
            dm.format_axis_millions, (0, 5e6), ticks=_ticks(1e6, 6)
        ) == ["0", "1M", "2M", "3M", "4M", "5M"]

    def test_millions_fractional_axis_is_uniform_with_bare_zero(self) -> None:
        labels = _labels(
            dm.format_axis_millions, (0, 1.6e6), ticks=_ticks(0.4e6, 5)
        )
        assert labels == ["0", "0.4M", "0.8M", "1.2M", "1.6M"]

    def test_millions_thousands_separator(self) -> None:
        labels = _labels(
            dm.format_axis_millions, (0, 2e9), ticks=_ticks(1e9, 3)
        )
        assert labels == ["0", "1,000M", "2,000M"]

    def test_millions_explicit_decimals_keep_legacy_labels(self) -> None:
        labels = _labels(
            dm.format_axis_millions, (0, 5e6), ticks=_ticks(1e6, 6), decimals=1
        )
        assert labels == ["0.0", "1.0M", "2.0M", "3.0M", "4.0M", "5.0M"]

    def test_billions_integer_axis(self) -> None:
        assert _labels(
            dm.format_axis_billions, (0, 5e9), ticks=_ticks(1e9, 6)
        ) == ["0", "1B", "2B", "3B", "4B", "5B"]

    def test_billions_custom_suffix(self) -> None:
        labels = _labels(
            dm.format_axis_billions,
            (1e9, 2e9),
            ticks=_ticks(0.25e9, 5, start=1e9),
            suffix=" bn",
        )
        assert labels == ["1.00 bn", "1.25 bn", "1.50 bn", "1.75 bn", "2.00 bn"]


_QUARTERS = _ticks(2.5e7, 8)  # 0 .. 1.75억 in 2,500만 steps


@pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
class TestFormatAxisMyriad:
    def test_max_unit_is_the_largest_tick(self) -> None:
        labels = _labels(dm.format_axis_myriad, (0, 1.75e8), ticks=_QUARTERS)
        assert labels == [
            "0",
            "0.25억",
            "0.50억",
            "0.75억",
            "1.00억",
            "1.25억",
            "1.50억",
            "1.75억",
        ]

    def test_whole_unit(self) -> None:
        labels = _labels(
            dm.format_axis_myriad, (0, 1.75e8), ticks=_QUARTERS, unit="whole"
        )
        assert labels == [
            "0",
            "2,500만",
            "5,000만",
            "7,500만",
            "10,000만",
            "12,500만",
            "15,000만",
            "17,500만",
        ]

    def test_fixed_unit(self) -> None:
        labels = _labels(
            dm.format_axis_myriad, (0, 1.75e8), ticks=_QUARTERS, unit="만"
        )
        assert labels[1] == "2,500만"
        assert labels[-1] == "17,500만"

    def test_integer_units_with_currency(self) -> None:
        ticks = _ticks(2e9, 7, start=2e9)
        labels = _labels(
            dm.format_axis_myriad, (2e9, 1.4e10), ticks=ticks, currency="₩"
        )
        assert labels == [
            "₩20억",
            "₩40억",
            "₩60억",
            "₩80억",
            "₩100억",
            "₩120억",
            "₩140억",
        ]

    def test_negative_axis_with_currency(self) -> None:
        ticks = _ticks(0.5e8, 5, start=-1e8)
        labels = _labels(
            dm.format_axis_myriad, (-1e8, 1e8), ticks=ticks, currency="₩"
        )
        assert labels == ["-₩1.0억", "-₩0.5억", "0", "₩0.5억", "₩1.0억"]

    def test_below_first_unit_is_plain_with_separators(self) -> None:
        labels = _labels(
            dm.format_axis_myriad, (0, 8000), ticks=_ticks(2000, 5)
        )
        assert labels == ["0", "2,000", "4,000", "6,000", "8,000"]

    def test_axis_crossing_a_unit_threshold(self) -> None:
        ticks = [5000, 10000, 15000]
        labels = _labels(dm.format_axis_myriad, (5000, 15000), ticks=ticks)
        assert labels == ["0.5만", "1.0만", "1.5만"]

    @pytest.mark.parametrize(
        "locale,units",
        [
            ("ko", ("만", "억", "조")),
            ("zh", ("万", "亿", "兆")),
            ("ja", ("万", "億", "兆")),
        ],
    )
    def test_every_locale_ladder(
        self, locale: str, units: tuple[str, str, str]
    ) -> None:
        man, eok, jo = units
        for top, unit in ((4e4, man), (4e8, eok), (4e12, jo)):
            ticks = _ticks(top / 4, 5)
            labels = _labels(
                dm.format_axis_myriad, (0, top), ticks=ticks, locale=locale
            )
            assert labels == [
                "0",
                f"1{unit}",
                f"2{unit}",
                f"3{unit}",
                f"4{unit}",
            ]
        fixed = _labels(
            dm.format_axis_myriad,
            (0, 4e8),
            ticks=_ticks(1e8, 5),
            locale=locale,
            unit=man,
        )
        assert fixed[-1] == f"40,000{man}"

    def test_unit_of_another_locale_raises(self) -> None:
        fig, ax = plt.subplots()
        try:
            with pytest.raises(ValueError, match="unit must be"):
                dm.format_axis_myriad(ax, locale="zh", unit="억")
        finally:
            plt.close(fig)

    def test_explicit_decimals_keep_per_tick_trimming(self) -> None:
        labels = _labels(
            dm.format_axis_myriad, (0, 1.75e8), ticks=_QUARTERS, decimals=1
        )
        assert labels[4:] == ["1억", "1.2억", "1.5억", "1.8억"]
