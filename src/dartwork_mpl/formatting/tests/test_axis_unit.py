"""``dm.axis_unit``: the axis unit goes in the axis label, ticks stay plain.

The user's B2-1 decision (2026-11-05): ``0, 0.2 … 1.0`` under
``매출 (조원)`` instead of ``0.2조 … 1.0조`` under ``매출 (원)``. The default
rule is ``"max"`` (the largest visible tick's unit); ``"whole"`` and a fixed
unit are one argument away. The expected tick texts are the approved
captures' (review page ``2026-11-05-b2-unit-rule``; ``b12/img/report.json``
entries ``B2/q-max``, ``q-whole``, ``y-max``, ``m-max``). The observed value is
the text after a real canvas draw.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._axis_wide import (
    FINANCE_LADDER,
    MYRIAD_LADDER,
    SI_LADDER,
    Unit,
)
from dartwork_mpl.formatting._label_unit import (
    LabelUnitFormatter,
    _sibling_template,
    _unit_group,
    fill,
)

MINUS = "\N{MINUS SIGN}"

# The approved captures' data (b12/scripts/render.py).
Q_DATES = [
    p.start_time.strftime("%Y-%m")
    for p in pd.period_range("2023Q1", "2025Q4", freq="Q")
]
Q_REVENUE_WON = (
    np.array(
        [5210, 5480, 5830, 6420, 6150, 6690, 7120, 7880, 7540, 8210, 8930, 9650]
    )
    * 1e8
)
M_DATES = pd.date_range("2023-01-01", periods=36, freq="MS")
_T = np.arange(36)
M_REVENUE_USD = (
    1.25e6 + 0.058e6 * _T + 0.18e6 * np.sin(2 * np.pi * (_T - 2) / 12)
).round(-3)
Y_YEARS = np.arange(2015, 2026)
Y_EXPORTS_USD = (
    np.array([38.2, 40.1, 43.5, 46.0, 44.8, 41.2, 49.6, 55.3, 58.9, 64.7, 71.8])
    * 1e9
)

MAX_TICKS = ["0", "0.2", "0.4", "0.6", "0.8", "1.0"]
WHOLE_TICKS = ["0", "2,000", "4,000", "6,000", "8,000", "10,000"]
BILLION_TICKS = ["35", "40", "45", "50", "55", "60", "65", "70", "75"]


@pytest.fixture(autouse=True)
def _restore_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _drawn(ax: Axes, which: str = "y") -> list[str]:
    ax.figure.canvas.draw()
    axis = ax.yaxis if which == "y" else ax.xaxis
    low, high = sorted(axis.get_view_interval())
    return [
        label.get_text()
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high and label.get_text()
    ]


def _quarterly_bars(values: np.ndarray = Q_REVENUE_WON) -> tuple[Figure, Axes]:
    """The q capture: quarterly revenue bars in 원, Korean labels."""
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.bar(np.arange(len(Q_DATES)), values, width=0.65)
    dm.format_axis_dates(ax, Q_DATES)
    return fig, ax


def _quarterly(**kwargs: object) -> tuple[Figure, Axes, LabelUnitFormatter]:
    fig, ax = _quarterly_bars()
    formatter = dm.axis_unit(ax, "y", label="매출 ({unit}원)", **kwargs)  # type: ignore[arg-type]
    dm.simple_layout(fig)
    return fig, ax, formatter


def _yearly() -> tuple[Figure, Axes]:
    """The y capture: yearly exports in USD, English labels."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.plot(Y_YEARS, Y_EXPORTS_USD, marker="o")
    return fig, ax


class TestApprovedCaptures:
    """The tick texts and labels the user approved on the review page."""

    def test_max_korean(self):
        _fig, ax, _ = _quarterly()
        assert _drawn(ax) == MAX_TICKS
        assert ax.get_ylabel() == "매출 (조원)"

    def test_whole_korean(self):
        _fig, ax, _ = _quarterly(scale="whole")
        assert _drawn(ax) == WHOLE_TICKS
        assert ax.get_ylabel() == "매출 (억원)"

    def test_fixed_and_finance(self):
        _fig, ax, _ = _quarterly(scale="억")
        assert _drawn(ax) == WHOLE_TICKS
        assert ax.get_ylabel() == "매출 (억원)"

        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
        dm.simple_layout(fig)
        assert _drawn(ax) == BILLION_TICKS
        assert ax.get_ylabel() == "Revenue (USD B)"

    def test_monthly_finance_max(self):
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
        ax.plot(M_DATES, M_REVENUE_USD)
        dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
        dm.simple_layout(fig)
        assert _drawn(ax) == ["1.0", "1.5", "2.0", "2.5", "3.0"]
        assert ax.get_ylabel() == "Revenue (USD M)"


class TestLadders:
    """``ladder="auto"`` follows the figure's language; the others are fixed."""

    def test_auto_is_myriad_in_korean_figures(self):
        _fig, ax, formatter = _quarterly()
        assert formatter.unit == Unit(1e12, "조")
        assert ax.get_ylabel() == "매출 (조원)"

    def test_auto_is_si_in_english_figures(self):
        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Exports (USD {unit})")
        dm.simple_layout(fig)
        assert _drawn(ax) == BILLION_TICKS
        assert ax.get_ylabel() == "Exports (USD G)"

    def test_korean_text_elsewhere_makes_auto_myriad(self):
        fig, ax = _quarterly_bars()
        ax.set_title("분기 매출")
        dm.axis_unit(ax, "y", label="Revenue ({unit})")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Revenue (조)"

    def test_explicit_ladders(self):
        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Exports ({unit}달러)", ladder="myriad")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Exports (억달러)"
        assert _drawn(ax) == [
            "350",
            "400",
            "450",
            "500",
            "550",
            "600",
            "650",
            "700",
            "750",
        ]

        fig, ax = _quarterly_bars()
        dm.axis_unit(ax, "y", label="매출 ({unit}원)", ladder="si")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "매출 (T원)"
        assert _drawn(ax) == MAX_TICKS

    def test_auto_follows_config_number_ladder(self):
        with dm.config.override(number_ladder="si"):
            _fig, ax, formatter = _quarterly()
        assert formatter.unit == Unit(1e12, "T")
        assert ax.get_ylabel() == "매출 (T원)"

        with dm.config.override(number_ladder="myriad"):
            fig, ax = _yearly()
            dm.axis_unit(ax, "y", label="Exports ({unit})")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Exports (억)"

    def test_bad_config_number_ladder_is_named(self):
        fig, ax = _yearly()
        with (
            dm.config.override(number_ladder="metric"),
            pytest.raises(ValueError, match="config.number_ladder"),
        ):
            dm.axis_unit(ax, "y")


class TestLabelTemplates:
    """The label template: ``{unit}``, no placeholder, ``None``."""

    def test_label_without_placeholder_and_none(self):
        _fig, ax = _quarterly_bars()
        dm.axis_unit(ax, "y", label="매출")
        dm.simple_layout(_fig)
        assert ax.get_ylabel() == "매출 (조)"

        fig, ax = _yearly()
        ax.set_ylabel("Exports")
        dm.axis_unit(ax, "y", ladder="finance")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Exports (B)"
        assert _drawn(ax) == BILLION_TICKS

        fig, ax = _yearly()
        dm.axis_unit(ax, "y", ladder="finance")  # no label at all
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "(B)"

    def test_none_template_is_captured_once(self):
        fig, ax = _yearly()
        ax.set_ylabel("Exports")
        dm.axis_unit(ax, "y", ladder="finance")
        dm.simple_layout(fig)
        dm.axis_unit(ax, "y", ladder="finance")  # again, label=None
        dm.simple_layout(fig)
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Exports (B)"

    def test_none_after_a_new_label_takes_the_new_label(self):
        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Exports ({unit})", ladder="finance")
        dm.simple_layout(fig)
        ax.set_ylabel("Imports")
        dm.axis_unit(ax, "y", ladder="finance")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Imports (B)"

    def test_no_unit_leaves_no_empty_parentheses(self):
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
        ax.bar(range(3), [120, 480, 760])
        dm.axis_unit(ax, "y", label="Count ({unit})")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Count"
        assert _drawn(ax) == [
            "0",
            "100",
            "200",
            "300",
            "400",
            "500",
            "600",
            "700",
            "800",
        ]

    def test_label_is_set_at_install(self):
        _fig, ax = _quarterly_bars()
        dm.axis_unit(ax, "y", label="매출 ({unit}원)")
        assert ax.get_ylabel() == "매출 (원)"

    def test_other_braces_are_kept(self):
        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Exports {x} ({unit})", ladder="finance")
        dm.simple_layout(fig)
        assert ax.get_ylabel() == "Exports {x} (B)"

    @pytest.mark.parametrize(
        ("template", "unit", "expected"),
        [
            ("매출 ({unit}원)", "조", "매출 (조원)"),
            ("매출 ({unit}원)", "", "매출 (원)"),
            ("Revenue (USD {unit})", "B", "Revenue (USD B)"),
            ("Revenue (USD {unit})", "", "Revenue (USD)"),
            ("Revenue ({unit} USD)", "", "Revenue (USD)"),
            ("Count ({unit})", "", "Count"),
            ("({unit})", "", ""),
            ("({unit})", "k", "(k)"),
        ],
    )
    def test_fill(self, template, unit, expected):
        assert fill(template, unit) == expected


class TestFollowsTheAxis:
    """Label and ticks are decided again on every draw."""

    def test_label_is_idempotent_and_follows_limits(self):
        fig, ax, formatter = _quarterly()
        for _ in range(3):
            dm.simple_layout(fig)
        assert ax.get_ylabel() == "매출 (조원)"
        assert _drawn(ax) == MAX_TICKS

        ax.set_ylim(0, 2e9)
        fig.canvas.draw()
        assert formatter.unit == Unit(1e8, "억")
        assert ax.get_ylabel() == "매출 (억원)"
        assert _drawn(ax) == [
            "0",
            "2.5",
            "5.0",
            "7.5",
            "10.0",
            "12.5",
            "15.0",
            "17.5",
            "20.0",
        ]

    def test_x_axis(self):
        dm.style.use("report-kr")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
        ax.barh(np.arange(len(Q_DATES)), Q_REVENUE_WON)
        dm.axis_unit(ax, "x", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert ax.get_xlabel() == "매출 (조원)"
        assert _drawn(ax, "x") == MAX_TICKS

    def test_fixed_decimals(self):
        # A fixed count holds on every tick, zero included (as in
        # format_axis_si(..., unit="k", decimals=2)).
        _fig, ax, _ = _quarterly(decimals=2)
        assert _drawn(ax) == ["0.00", "0.20", "0.40", "0.60", "0.80", "1.00"]

    def test_log_axis_reads_plain_numbers_without_a_unit(self):
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
        ax.plot([1, 2, 3], [1e2, 1e4, 1e6])
        ax.set_yscale("log")
        dm.axis_unit(ax, "y", label="Power ({unit}W)")
        dm.simple_layout(fig)
        assert _drawn(ax) == ["100", "1,000", "10,000", "100,000", "1,000,000"]
        assert ax.get_ylabel() == "Power (W)"
        assert dm.axis_unit_of(ax) == Unit(1.0, "")


class TestDegenerateAxes:
    """Zero, negative and inverted axes."""

    def test_all_zero(self):
        # matplotlib widens the empty range to about ±0.06; its ticks carry
        # float noise (0.06000000000000001) and must still read 0.06.
        fig, ax = _quarterly_bars(np.zeros(len(Q_DATES)))
        dm.axis_unit(ax, "y", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert _drawn(ax) == [
            f"{MINUS}0.06",
            f"{MINUS}0.04",
            f"{MINUS}0.02",
            "0",
            "0.02",
            "0.04",
        ]
        assert ax.get_ylabel() == "매출 (원)"
        assert dm.axis_unit_of(ax) == Unit(1.0, "")

    def test_negative_only_uses_the_minus_sign(self):
        fig, ax = _quarterly_bars(-Q_REVENUE_WON)
        dm.axis_unit(ax, "y", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert _drawn(ax) == [
            f"{MINUS}1.0",
            f"{MINUS}0.8",
            f"{MINUS}0.6",
            f"{MINUS}0.4",
            f"{MINUS}0.2",
            "0",
        ]
        assert ax.get_ylabel() == "매출 (조원)"

    def test_inverted_limits(self):
        fig, ax = _quarterly_bars()
        dm.axis_unit(ax, "y", label="매출 ({unit}원)")
        ax.set_ylim(1e12, 0)
        dm.simple_layout(fig)
        assert _drawn(ax) == MAX_TICKS
        assert ax.get_ylim() == (1e12, 0)
        assert ax.get_ylabel() == "매출 (조원)"


class TestValidation:
    """``UNIT_DUP`` finds nothing; bad arguments raise early."""

    @pytest.mark.parametrize(
        "kwargs", [{}, {"scale": "whole"}, {"scale": "억"}]
    )
    def test_unit_dup_clean(self, kwargs):
        fig, _ax, _ = _quarterly(**kwargs)
        assert dm.validate_figure(fig, checks=("UNIT_DUP",)) == []

    def test_unit_dup_clean_finance(self):
        fig, ax = _yearly()
        dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
        dm.simple_layout(fig)
        assert dm.validate_figure(fig, checks=("UNIT_DUP",)) == []

    def test_bad_arguments_raise_before_touching_the_axis(self):
        fig, ax = _yearly()
        before = ax.yaxis.get_major_formatter()
        with pytest.raises(ValueError, match="axis"):
            dm.axis_unit(ax, "z")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="ladder"):
            dm.axis_unit(ax, "y", ladder="metric")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="scale"):
            dm.axis_unit(ax, "y", scale="G", ladder="finance")
        with pytest.raises(ValueError, match="decimals"):
            dm.axis_unit(ax, "y", decimals=-1)
        assert ax.yaxis.get_major_formatter() is before
        assert ax.get_ylabel() == ""
        with pytest.raises(ValueError, match="axis"):
            dm.axis_unit_of(ax, "z")  # type: ignore[arg-type]


class TestAxisUnitOf:
    """``dm.axis_unit_of`` reads the unit of the last draw."""

    def test_axis_unit_of(self):
        fig, ax = _quarterly_bars()
        assert dm.axis_unit_of(ax, "y") is None  # matplotlib's own formatter
        dm.axis_unit(ax, "y", label="매출 ({unit}원)")
        assert dm.axis_unit_of(ax) is None  # nothing drawn yet
        dm.simple_layout(fig)
        assert dm.axis_unit_of(ax) == Unit(1e12, "조")
        assert dm.axis_unit_of(ax, "x") is None

        ax.set_ylim(0, 2e9)
        fig.canvas.draw()
        assert dm.axis_unit_of(ax, "y") == Unit(1e8, "억")

        ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
        assert dm.axis_unit_of(ax, "y") is None

    def test_returns_the_installed_formatter(self):
        fig, ax = _quarterly_bars()
        formatter = dm.axis_unit(
            ax, "y", label="매출 ({unit}원)", scale="whole"
        )
        assert isinstance(formatter, LabelUnitFormatter)
        assert ax.yaxis.get_major_formatter() is formatter
        dm.simple_layout(fig)
        assert formatter.unit == dm.axis_unit_of(ax) == Unit(1e8, "억")


class TestSharedAxes:
    """Shared axes share one formatter; every axes keeps its own label.

    Review 2026-11-05, Important 3: the loop below left axes[0] reading
    ``매출 (원)`` over 조원 ticks.
    """

    def test_sharey_loop_labels_every_axes(self):
        dm.style.use("report-kr")
        fig, axes = plt.subplots(
            2, 1, sharey=True, figsize=dm.figsize("12cm", "standard")
        )
        for i, a in enumerate(axes):
            a.bar(range(5), np.array([5.2, 6.4, 7.1, 8.2, 9.6]) * 1e11)
            dm.axis_unit(a, "y", label=f"매출 {i} ({{unit}}원)")
        dm.simple_layout(fig)
        for i, a in enumerate(axes):
            assert a.get_ylabel() == f"매출 {i} (조원)"
            assert _drawn(a) == ["0", "0.2", "0.4", "0.6", "0.8", "1.0"]
            assert dm.axis_unit_of(a) == Unit(1e12, "조")
        assert dm.validate_figure(fig, checks=("UNIT_DUP",)) == []
        axes[0].set_ylim(0, 2e9)  # shared: both axes follow
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == [
            "매출 0 (억원)",
            "매출 1 (억원)",
        ]

    def test_sharex_loop_labels_every_axes(self):
        dm.style.use("report-kr")
        fig, axes = plt.subplots(
            1, 2, sharex=True, figsize=dm.figsize("12cm", "wide")
        )
        for a in axes:
            a.plot(np.linspace(0, 3e8, 5), range(5))
            dm.axis_unit(a, "x", label="인구 ({unit}명)")
        dm.simple_layout(fig)
        for a in axes:
            assert a.get_xlabel() == "인구 (억명)"
            assert dm.axis_unit_of(a, "x") == Unit(1e8, "억")

    def test_label_none_loop_keeps_each_label(self):
        dm.style.use("report-kr")
        fig, axes = plt.subplots(
            2, 1, sharey=True, figsize=dm.figsize("12cm", "standard")
        )
        for a, name in zip(axes, ("매출", "비용"), strict=True):
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e8)
            a.set_ylabel(name)
            dm.axis_unit(a, "y")
        dm.simple_layout(fig)
        assert [a.get_ylabel() for a in axes] == ["매출 (억)", "비용 (억)"]
        dm.axis_unit(axes[0], "y")  # again, without a label: no second unit
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == ["매출 (억)", "비용 (억)"]

    @staticmethod
    def _stacked(n: int = 2, **share: object) -> tuple[Figure, list[Axes]]:
        dm.style.use("report-kr")
        fig, axes = plt.subplots(
            n, 1, figsize=dm.figsize("12cm", "standard"), **share
        )
        return fig, list(axes)

    @pytest.mark.parametrize(
        ("other", "expected"),
        [
            ("비용", "비용 (억)"),
            ("비용 (원)", "비용 (억원)"),
            ("비용 (단위: 원)", "비용 (단위: 원) (억)"),
            ("비용 (억원)", "비용 (억원)"),  # a unit already there: not doubled
            ("매출 (별도)", "매출 (별도) (억)"),
        ],
    )
    def test_one_call_on_sharey_labels_the_sibling(self, other, expected):
        """One call rescales the shared ticks of every axes; each label says so.

        A sibling without a template of its own keeps its label. Trailing
        parentheses that hold the installing template's base unit (``(원)``
        for ``매출 ({unit}원)``), or that unit with a ladder unit already in
        it (``(억원)``), take the template's unit group; any other label gets
        `` ({unit})`` appended (review 2026-11-05, R4; user decision,
        follow-up b; re-review rulings N2 and N4).
        """
        fig, axes = self._stacked(sharey=True)
        for a, name in zip(axes, ("매출 (원)", other), strict=True):
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e11)
            a.set_ylabel(name)
        dm.axis_unit(axes[0], "y", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert [a.get_ylabel() for a in axes] == ["매출 (억원)", expected]
        assert _drawn(axes[1]) == ["0", "2,000", "4,000", "6,000"]
        assert dm.validate_figure(fig, checks=("UNIT_DUP",)) == []
        fig.canvas.draw()  # a repeat draw appends nothing
        assert [a.get_ylabel() for a in axes] == ["매출 (억원)", expected]
        axes[0].set_ylim(0, 6e12)  # both follow the shared ticks
        fig.canvas.draw()
        assert axes[1].get_ylabel() == expected.replace("억", "조")

    @pytest.mark.parametrize(
        ("ladder", "unit"), [("finance", "B"), ("si", "G")]
    )
    def test_a_sibling_unit_takes_a_suffix_on_latin_ladders(self, ladder, unit):
        """Finance and SI units follow the currency, after a space."""
        dm.style.use("report")
        fig, axes = plt.subplots(
            2, 1, sharey=True, figsize=dm.figsize("12cm", "standard")
        )
        for a, name in zip(axes, ("Revenue (USD)", "Cost (USD)"), strict=True):
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e10)
            a.set_ylabel(name)
        dm.axis_unit(axes[0], "y", label="Revenue (USD {unit})", ladder=ladder)
        dm.simple_layout(fig)
        for _ in range(3):  # repeated draws write the same text
            fig.canvas.draw()
            assert [a.get_ylabel() for a in axes] == [
                f"Revenue (USD {unit})",
                f"Cost (USD {unit})",
            ]

    @pytest.mark.parametrize(
        ("other", "expected"),
        [
            ("Cost (USD)", "Cost (USD B)"),
            ("Cost (USD B)", "Cost (USD B)"),  # not "(USD B B)"
            ("Cost (est.)", "Cost (est.) (B)"),
            ("Cost (2024)", "Cost (2024) (B)"),
            ("Cost (USD)\n(nominal)", "Cost (USD)\n(nominal) (B)"),
        ],
    )
    def test_only_the_templates_base_unit_takes_it_inside(
        self, other, expected
    ):
        """Re-review 2026-11-05, N2: ``(est.)`` read ``(est. B)``."""
        dm.style.use("report")
        fig, axes = plt.subplots(
            2, 1, sharey=True, figsize=dm.figsize("12cm", "standard")
        )
        for a, name in zip(axes, ("Revenue (USD)", other), strict=True):
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e10)
            a.set_ylabel(name)
        dm.axis_unit(
            axes[0], "y", label="Revenue (USD {unit})", ladder="finance"
        )
        dm.simple_layout(fig)
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == ["Revenue (USD B)", expected]

    def test_without_a_template_every_label_appends(self):
        """label=None: the installer appends, so the siblings do too (N4)."""
        fig, axes = self._stacked(sharey=True)
        for a, name in zip(axes, ("매출 (원)", "비용 (원)"), strict=True):
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e11)
            a.set_ylabel(name)
        dm.axis_unit(axes[0], "y")
        dm.simple_layout(fig)
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == [
            "매출 (원) (억)",
            "비용 (원) (억)",
        ]

    def test_a_sibling_unit_reads_back_on_the_ones_rung(self):
        """No unit: ``비용 (원)`` stays as written, and returns later."""
        fig, axes = self._stacked(sharey=True)
        for a, name in zip(axes, ("매출 (원)", "비용 (원)"), strict=True):
            a.bar(range(3), [2000.0, 4000.0, 6000.0])
            a.set_ylabel(name)
        dm.axis_unit(axes[0], "y", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert [a.get_ylabel() for a in axes] == ["매출 (원)", "비용 (원)"]
        axes[0].set_ylim(0, 6e8)
        fig.canvas.draw()
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == ["매출 (억원)", "비용 (억원)"]
        axes[0].set_ylim(0, 6000)
        fig.canvas.draw()
        assert [a.get_ylabel() for a in axes] == ["매출 (원)", "비용 (원)"]

    def test_an_empty_sibling_label_stays_empty(self):
        """``label_outer`` emptied the right panel's y label: it stays so."""
        dm.style.use("report-kr")
        fig, axes = plt.subplots(
            1, 2, sharey=True, figsize=dm.figsize("12cm", "wide")
        )
        for a in axes:
            a.bar(range(3), np.array([2.0, 4.0, 6.0]) * 1e11)
        axes[0].set_ylabel("매출 (원)")
        dm.axis_unit(axes[0], "y", label="매출 ({unit}원)")
        dm.simple_layout(fig)
        assert [a.get_ylabel() for a in axes] == ["매출 (억원)", ""]

    @pytest.mark.parametrize("on", [0, 1], ids=["inner", "outer"])
    def test_one_call_on_stacked_sharex_labels_the_bottom_only(self, on):
        """The inner panel's x label stays empty, as ``label_outer`` left it.

        Called on the inner (top) panel, the label goes where the shared
        ticks are shown: the bottom panel.
        """
        fig, axes = self._stacked(sharex=True)
        for a in axes:
            a.plot(np.linspace(0, 3e8, 5), range(5))
        dm.axis_unit(axes[on], "x", label="인구 ({unit}명)")
        dm.simple_layout(fig)
        assert [a.get_xlabel() for a in axes] == ["", "인구 (억명)"]
        assert dm.axis_unit_of(axes[0], "x") == Unit(1e8, "억")

    def test_stacked_sharex_loop_labels_the_bottom_only(self):
        fig, axes = self._stacked(3, sharex=True)
        for a in axes:
            a.plot(np.linspace(0, 3e8, 5), range(5))
            dm.axis_unit(a, "x", label="인구 ({unit}명)")
        dm.simple_layout(fig)
        assert [a.get_xlabel() for a in axes] == ["", "", "인구 (억명)"]
        assert _drawn(axes[2], "x") == [
            "0",
            "0.5",
            "1.0",
            "1.5",
            "2.0",
            "2.5",
            "3.0",
        ]

    def test_an_inner_label_someone_wrote_follows_the_unit(self):
        """Only an empty inner label is left alone; a written one is kept up."""
        fig, axes = self._stacked(sharex=True)
        for a in axes:
            a.plot(np.linspace(0, 3e8, 5), range(5))
        axes[0].set_xlabel("상단")
        dm.axis_unit(axes[1], "x", label="인구 ({unit}명)")
        dm.simple_layout(fig)
        assert [a.get_xlabel() for a in axes] == ["상단 (억)", "인구 (억명)"]


@pytest.mark.parametrize(
    ("label", "group", "ladder", "template"),
    [
        ("비용 (원)", "({unit}원)", "myriad", "비용 ({unit}원)"),
        ("비용(원)", "({unit}원)", "myriad", "비용({unit}원)"),
        ("비용 (억원)", "({unit}원)", "myriad", "비용 ({unit}원)"),
        ("비용 (단위: 원)", "({unit}원)", "myriad", "비용 (단위: 원) ({unit})"),
        ("매출 (별도)", "({unit}원)", "myriad", "매출 (별도) ({unit})"),
        ("Cost (USD)", "(USD {unit})", "finance", "Cost (USD {unit})"),
        ("Cost (USD B)", "(USD {unit})", "finance", "Cost (USD {unit})"),
        ("Temp (°C)", "({unit}W)", "si", "Temp (°C) ({unit})"),
        ("비용 (원)", "({unit})", "myriad", "비용 (원) ({unit})"),
        ("비용 (원) (억)", "({unit})", "myriad", "비용 (원) ({unit})"),
        ("비용", "({unit}원)", "myriad", "비용 ({unit})"),
        ("비용 ({unit}원)", "({unit}원)", "myriad", "비용 ({unit}원)"),
    ],
)
def test_sibling_template(label, group, ladder, template):
    rungs = {
        "myriad": MYRIAD_LADDER,
        "finance": FINANCE_LADDER,
        "si": SI_LADDER,
    }
    assert _sibling_template(label, group, rungs[ladder]) == template


def test_unit_group():
    assert _unit_group("매출 ({unit}원)") == "({unit}원)"
    assert _unit_group("Revenue (USD {unit})") == "(USD {unit})"
    assert _unit_group("매출 (원) ({unit})") == "({unit})"
    assert _unit_group("매출 {unit}원") == "({unit})"  # none: the append form


def test_exported_as_experimental():
    assert {"axis_unit", "axis_unit_of"} <= set(dm.__all__)
    assert {"axis_unit", "axis_unit_of"} <= dm.EXPERIMENTAL
