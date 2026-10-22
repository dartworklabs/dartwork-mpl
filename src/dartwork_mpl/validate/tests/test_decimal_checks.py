"""Meaningless decimals in ticks and value labels (#523).

TICK_DECIMAL's trailing-zero rule is a WARNING that names the dm
formatter option, and decimal consistency is judged per unit suffix so
dm's own axis-wide formatters validate clean. VALUE_LABEL_DECIMAL is the
same rule for numeric labels drawn inside an axes.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure

matplotlib.use("Agg")


def _hits(fig: Figure, check_id: str) -> list[VisualWarning]:
    warnings = validate_figure(fig, checks=(check_id,), quiet=True)
    return [w for w in warnings if w.check_id == check_id]


def _tick_fig(ticks: list[float], labels: list[str]) -> Figure:
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot([0, 1], [ticks[0], ticks[-1]])
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)
    pad = 0.05 * (ticks[-1] - ticks[0])
    ax.set_ylim(ticks[0] - pad, ticks[-1] + pad)
    return fig


class TestTickDecimalTrailingZero:
    def test_si_explicit_decimals_warn_and_name_the_formatter(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.set_ylim(0, 200)
        dm.format_axis_si(ax, axis="y", decimals=1)

        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)

        assert len(hits) == 1
        assert hits[0].severity == Severity.WARNING
        assert "trailing zero" in hits[0].message
        assert "format_axis_si" in hits[0].message
        assert hits[0].detail["reason"] == "trailing_zero"
        fixes = dm.validate_fixes.get_fix_suggestions(hits[0])
        assert "decimals" in fixes[0]
        assert "dm.format_axis_si(ax, axis='y')" in fixes[0]

    @pytest.mark.parametrize(
        "detail,leads_with_formatter",
        [
            ({"reason": "trailing_zero", "axis": "x"}, True),
            ({"reason": "excess_precision"}, False),
            ({"reason": "bogus"}, False),
            ({}, False),
        ],
    )
    def test_fix_reads_the_typed_reason(
        self, detail: dict[str, object], leads_with_formatter: bool
    ) -> None:
        warning = VisualWarning(
            severity=Severity.WARNING,
            check_id="TICK_DECIMAL",
            message="hand-built",
            detail=dict(detail),
        )
        first = dm.validate_fixes.get_fix_suggestions(warning)[0]
        assert ("format_axis_si" in first) is leads_with_formatter
        if leads_with_formatter:
            assert "axis='x'" in first

    def test_trailing_zero_in_a_prefixed_group_warns(self) -> None:
        fig = _tick_fig([0, 1000, 2000, 3000], ["0.0", "1.0k", "2.0k", "3.0k"])
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert [h.detail["reason"] for h in hits] == ["trailing_zero"]

    @pytest.mark.parametrize(
        "ylim", [(0, 200), (0, 1300), (0, 2100), (0, 5e6), (-1e6, 1e6)]
    )
    def test_dm_si_default_validates_clean(
        self, ylim: tuple[float, float]
    ) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.set_ylim(*ylim)
        dm.format_axis_si(ax, axis="y")
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert hits == []

    @pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
    def test_unit_change_is_judged_per_unit(self) -> None:
        # Fixed labels, not a formatter: 7,500만 then 1.00억 keeps decimals
        # uniform within each unit, so the axis is not "non-uniform".
        ticks = [2.5e7, 5e7, 7.5e7, 1e8, 1.25e8]
        labels = ["2,500만", "5,000만", "7,500만", "1.00억", "1.25억"]
        fig = _tick_fig(ticks, labels)
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert hits == []

    def test_mixed_decimals_within_one_unit_still_warn(self) -> None:
        fig = _tick_fig([1000, 1500, 2000], ["1k", "1.5k", "2k"])
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert [h.detail["reason"] for h in hits] == ["non_uniform"]

    def test_fractional_axis_with_integer_ticks_is_clean(self) -> None:
        fig = _tick_fig([17.5, 20.0, 22.5], ["17.5", "20.0", "22.5"])
        assert _hits(fig, "TICK_DECIMAL") == []
        plt.close(fig)

    @pytest.mark.parametrize(
        "ticks,labels",
        [
            # The .0 on 1.0M is what the half step needs; 0 has no unit.
            (
                [-1e6, -5e5, 0, 5e5, 1e6],
                ["-1.0M", "-0.5M", "0", "0.5M", "1.0M"],
            ),
            ([0, 0.5, 1.0, 1.5], ["0", "0.5", "1.0", "1.5"]),
            (
                [0, 250, 500, 750, 1000],
                ["0", "0.25k", "0.50k", "0.75k", "1.00k"],
            ),
        ],
    )
    def test_decimals_the_axis_needs_are_clean(
        self, ticks: list[float], labels: list[str]
    ) -> None:
        fig = _tick_fig(ticks, labels)
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert hits == []

    def test_bare_zero_does_not_hide_trailing_zeros(self) -> None:
        fig = _tick_fig([0, 1, 2, 3], ["0", "1.0", "2.0", "3.0"])
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert [h.detail["reason"] for h in hits] == ["trailing_zero"]

    def test_mixed_decimals_beside_a_bare_zero_still_warn(self) -> None:
        fig = _tick_fig([0, 17.5, 20, 22.5], ["0", "17.5", "20", "22.5"])
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert [h.detail["reason"] for h in hits] == ["non_uniform"]

    def test_scaled_precision_is_judged_on_rendered_numbers(self) -> None:
        # 0.25k steps need two decimals; a 250 raw step would say zero.
        ticks = [250, 500, 750, 1000]
        fig = _tick_fig(ticks, ["0.25k", "0.50k", "0.75k", "1.00k"])
        assert _hits(fig, "TICK_DECIMAL") == []
        plt.close(fig)

    def test_excess_precision_still_info(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.set_yticks([0, 0.5, 1.0])
        ax.set_ylim(-0.05, 1.05)
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.4f"))
        hits = _hits(fig, "TICK_DECIMAL")
        plt.close(fig)
        assert [(h.severity, h.detail["reason"]) for h in hits] == [
            (Severity.INFO, "excess_precision")
        ]


def _bar_fig(labels: list[str]) -> Figure:
    fig, ax = plt.subplots(figsize=(5, 3))
    values = list(range(1, len(labels) + 1))
    bars = ax.bar(range(len(labels)), values)
    ax.bar_label(bars, labels=labels)
    return fig


class TestValueLabelDecimal:
    @pytest.mark.parametrize(
        "labels",
        [
            ["120.0", "135.0", "152.0"],
            ["45.0%", "30.0%", "25.0%"],
            ["1,200.0 MWh", "595.0 MWh"],
            ["+12.0", "-3.0", "8"],
        ],
    )
    def test_whole_number_labels_with_decimals_warn(
        self, labels: list[str]
    ) -> None:
        fig = _bar_fig(labels)
        hits = _hits(fig, "VALUE_LABEL_DECIMAL")
        plt.close(fig)
        assert len(hits) == 1
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["labels"] == len(labels)
        with_decimals = sum("." in label for label in labels)
        assert hits[0].detail["with_decimals"] == with_decimals
        fixes = dm.validate_fixes.get_fix_suggestions(hits[0])
        assert f"{with_decimals} labels print" in fixes[0]

    def test_fix_handler_defaults_without_detail(self) -> None:
        warning = VisualWarning(
            severity=Severity.WARNING,
            check_id="VALUE_LABEL_DECIMAL",
            message="hand-built",
            detail={},
        )
        fixes = dm.validate_fixes.get_fix_suggestions(warning)
        assert "but labels print decimals" in fixes[0]
        assert "{:,.0f}" in fixes[0]

    @pytest.mark.parametrize(
        "labels",
        [
            ["120", "135", "152"],  # already clean
            ["88.9%", "90.0%", "75.5%"],  # real fractions keep decimals
            ["1.5", "2.0", "2.5"],
            ["$12", "$15"],
        ],
    )
    def test_clean_or_fractional_labels_pass(self, labels: list[str]) -> None:
        fig = _bar_fig(labels)
        assert _hits(fig, "VALUE_LABEL_DECIMAL") == []
        plt.close(fig)

    def test_single_label_does_not_vote(self) -> None:
        fig = _bar_fig(["3.0"])
        assert _hits(fig, "VALUE_LABEL_DECIMAL") == []
        plt.close(fig)

    def test_prose_and_tokens_are_not_value_labels(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1], [0, 1])
        ax.text(0.1, 0.9, "Synthetic monthly cohort, 24.0 months of data")
        ax.text(0.1, 0.8, "Release v2.0")
        ax.text(0.1, 0.7, "Peak: 175.0\nMonth 24")
        assert _hits(fig, "VALUE_LABEL_DECIMAL") == []
        plt.close(fig)

    def test_annotate_value_labels_count(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [10, 20, 30])
        for x, y in [(0, 10), (1, 20), (2, 30)]:
            dm.annotate_value(ax, x, y, f"{y:.1f}", side="above")
        hits = _hits(fig, "VALUE_LABEL_DECIMAL")
        plt.close(fig)
        assert len(hits) == 1
        assert hits[0].detail["example"] == "10.0"

    def test_hidden_labels_are_ignored(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1], [0, 1])
        for i, label in enumerate(["1.0", "2.0"]):
            ax.text(0.2 * i, 0.5, label).set_visible(False)
        assert _hits(fig, "VALUE_LABEL_DECIMAL") == []
        plt.close(fig)
