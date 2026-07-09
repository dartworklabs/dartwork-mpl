"""Tests for visual validation module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, PercentFormatter

from dartwork_mpl.validate import Severity, VisualWarning, validate_figure

matplotlib.use("Agg")  # Non-interactive backend for testing.


class TestVisualWarning:
    """Tests for VisualWarning data class."""

    def test_str_format(self) -> None:
        w = VisualWarning(
            severity=Severity.WARNING, check_id="TEST", message="test message"
        )
        s = str(w)
        assert "[VISUAL]" in s
        assert "TEST" in s
        assert "test message" in s

    def test_info_severity(self) -> None:
        w = VisualWarning(
            severity=Severity.INFO, check_id="INFO_TEST", message="info message"
        )
        s = str(w)
        assert "💡" in s


class TestValidateFigureClean:
    """Tests for validate_figure with clean figures."""

    def test_clean_figure_no_warnings(self) -> None:
        """A simple clean plot should produce no warnings."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        warnings = validate_figure(fig, quiet=True)
        assert len(warnings) == 0
        plt.close(fig)

    def test_quiet_mode(self, capsys) -> None:
        """quiet=True should suppress stdout."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        validate_figure(fig, quiet=True)
        captured = capsys.readouterr()
        assert captured.out == ""
        plt.close(fig)

    def test_unknown_check_id_raises(self) -> None:
        """A typo'd check ID must fail loud, not silently run zero
        checks and report the figure clean (VAL-4)."""
        import pytest

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        with pytest.raises(ValueError, match="Unknown check IDs"):
            validate_figure(fig, checks=("OVERFLW",), quiet=True)
        plt.close(fig)


class TestCheckOverflow:
    """Tests for OVERFLOW detection."""

    def test_text_outside_figure(self) -> None:
        """Text placed far outside bounds should trigger OVERFLOW."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        # Place text way outside the figure
        ax.annotate(
            "far away",
            xy=(0.5, 0.5),
            xycoords="axes fraction",
            xytext=(-200, 0),
            textcoords="offset points",
        )
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        overflow_warnings = [w for w in warnings if w.check_id == "OVERFLOW"]
        assert len(overflow_warnings) > 0
        plt.close(fig)

    def test_long_tick_label_triggers_overflow(self) -> None:
        """A tick label that genuinely cannot fit on the canvas
        should trigger OVERFLOW even after the in-axes filter."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.bar([1, 2, 3], [1, 2, 3])
        ax.set_yticks([1, 2, 3])
        # 60-char tick labels — far wider than a 9 cm canvas.
        ax.set_yticklabels(["A" * 60, "B" * 60, "C" * 60])
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        overflow = [w for w in warnings if w.check_id == "OVERFLOW"]
        assert len(overflow) > 0
        plt.close(fig)

    def test_out_of_range_locator_tick_does_not_trigger_overflow(self) -> None:
        """matplotlib's auto tick locator emits ticks at "nice" round
        positions which can lie just past the data range; those ticks
        are clipped from the rendered axes and must not trigger
        OVERFLOW. (Regression: 11 of 12 0.4 plot templates produced
        spurious warnings before this fix.)"""
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        # Data tops out at 78 → matplotlib auto-locator extends ticks
        # to 90 (a "nice" round number outside the axis ylim of ~82).
        ax.bar(["A", "B", "C", "D", "E"], [23, 45, 56, 78, 33])
        ax.set_ylabel("Value")
        dm.simple_layout(fig)
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        overflow = [w for w in warnings if w.check_id == "OVERFLOW"]
        assert overflow == [], (
            f"Spurious OVERFLOW for clipped tick: "
            f"{[w.message for w in overflow]}"
        )
        plt.close(fig)


class TestCheckOverlap:
    """Tests for OVERLAP detection."""

    def test_overlapping_texts(self) -> None:
        """Two texts at the same position should trigger OVERLAP."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        ax.text(0.5, 0.5, "Label A", transform=ax.transAxes, fontsize=20)
        ax.text(0.5, 0.5, "Label B", transform=ax.transAxes, fontsize=20)
        warnings = validate_figure(fig, checks=("OVERLAP",), quiet=True)
        overlap_warnings = [w for w in warnings if w.check_id == "OVERLAP"]
        assert len(overlap_warnings) > 0
        plt.close(fig)


class TestCheckCrossAxesOverlap:
    """Tests for CROSS_AXES_OVERLAP detection (inter-Axes label collisions)."""

    def test_tight_hspace_triggers_overlap(self) -> None:
        """Stacked subplots with default hspace overlap title↔xlabel."""
        # Default plt.subplots hspace (0.2) is too small once each
        # subplot has both a title and an xlabel.
        fig, axs = plt.subplots(2, 1, figsize=(4, 3))
        for ax, title in zip(axs, ("Upper", "Lower"), strict=True):
            ax.plot([1, 2, 3])
            ax.set_title(title, fontsize=14)
            ax.set_xlabel("Time", fontsize=12)
            ax.set_ylabel("y")
        warnings = validate_figure(
            fig, checks=("CROSS_AXES_OVERLAP",), quiet=True
        )
        assert len(warnings) > 0, "Expected at least one cross-axes overlap"
        plt.close(fig)

    def test_generous_hspace_no_overlap(self) -> None:
        """Same layout with generous hspace + simple_layout should pass."""
        import dartwork_mpl as dm

        fig, axs = plt.subplots(
            2, 1, figsize=(6, 5), gridspec_kw={"hspace": 0.8}
        )
        for ax, title in zip(axs, ("Upper", "Lower"), strict=True):
            ax.plot([1, 2, 3])
            ax.set_title(title, fontsize=14)
            ax.set_xlabel("Time", fontsize=12)
            ax.set_ylabel("y")
        dm.simple_layout(fig)
        warnings = validate_figure(
            fig, checks=("CROSS_AXES_OVERLAP",), quiet=True
        )
        title_xlabel = [
            w
            for w in warnings
            if {w.detail["role_a"], w.detail["role_b"]} == {"title", "xlabel"}
        ]
        assert len(title_xlabel) == 0, (
            f"Did not expect title↔xlabel overlap, got: "
            f"{[w.message for w in title_xlabel]}"
        )
        plt.close(fig)


class TestCheckEmptyAxes:
    """Tests for EMPTY_AXES detection."""

    def test_empty_axes(self) -> None:
        """An axes with no data should trigger EMPTY_AXES."""
        fig, ax = plt.subplots(figsize=(4, 3))
        # Don't plot anything
        warnings = validate_figure(fig, checks=("EMPTY_AXES",), quiet=True)
        empty_warnings = [w for w in warnings if w.check_id == "EMPTY_AXES"]
        assert len(empty_warnings) > 0
        plt.close(fig)

    def test_nonempty_axes(self) -> None:
        """An axes with data should NOT trigger EMPTY_AXES."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        warnings = validate_figure(fig, checks=("EMPTY_AXES",), quiet=True)
        empty_warnings = [w for w in warnings if w.check_id == "EMPTY_AXES"]
        assert len(empty_warnings) == 0
        plt.close(fig)


class TestCheckTickCrowding:
    """Tests for TICK_CROWD detection."""

    def test_crowded_ticks(self) -> None:
        """Many ticks in a small figure should trigger TICK_CROWD."""
        fig, ax = plt.subplots(figsize=(2, 2))
        ax.plot(range(100))
        ax.set_xticks(range(0, 100, 2))  # 50 ticks
        warnings = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
        crowd_warnings = [w for w in warnings if w.check_id == "TICK_CROWD"]
        assert len(crowd_warnings) > 0
        plt.close(fig)

    def test_crowding_is_font_aware(self) -> None:
        """Same tick count + axis size: a large font crowds where a small
        font does not. The detector measures real label extents, so the
        threshold scales with font size instead of a fixed ticks/inch."""

        def crowd_count(fontsize: int) -> int:
            fig, ax = plt.subplots(figsize=(3, 3))
            ax.plot(range(20))
            ax.set_xticks(range(0, 20))
            for t in ax.get_xticklabels():
                t.set_fontsize(fontsize)
            fig.canvas.draw()
            warnings = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
            n = len([w for w in warnings if w.check_id == "TICK_CROWD"])
            plt.close(fig)
            return n

        assert crowd_count(20) > crowd_count(4)


class TestTickUtils:
    """Shared tick parsing helpers used by multiple visual checks."""

    def test_split_tick_affixes_normalizes_commas_and_spacing(self) -> None:
        from dartwork_mpl.validate._checks._tick_utils import (
            parse_numeric_tick,
            split_tick_affixes,
        )

        assert split_tick_affixes("  $ 1,234.50 % ") == ("$ ", "1234.50", " %")
        assert parse_numeric_tick(f"{chr(0x2212)}1,234.5 kg") == -1234.5

    def test_split_tick_affixes_skips_category_and_mathtext(self) -> None:
        from dartwork_mpl.validate._checks._tick_utils import split_tick_affixes

        assert split_tick_affixes("Q1") is None
        assert split_tick_affixes("$10^2$") is None


class TestCheckUnitDup:
    """UNIT_DUP detects duplicated axis-unit declarations."""

    def test_percent_axis_label_and_percent_ticks_warn(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0.0, 0.1, 0.2])
        ax.set_yticks([0.0, 0.1, 0.2])
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
        ax.set_ylabel("수익률 (%)")

        warnings = validate_figure(fig, checks=("UNIT_DUP",), quiet=True)

        hits = [w for w in warnings if w.check_id == "UNIT_DUP"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["axis"] == "y"
        assert hits[0].detail["label_unit"] == "%"
        assert hits[0].detail["tick_affix"] == "%"
        plt.close(fig)

    def test_percent_axis_label_with_bare_numeric_ticks_is_clean(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0.0, 0.1, 0.2])
        ax.set_yticks([0.0, 0.1, 0.2])
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, symbol=""))
        ax.set_ylabel("수익률 (%)")

        warnings = validate_figure(fig, checks=("UNIT_DUP",), quiet=True)

        assert not [w for w in warnings if w.check_id == "UNIT_DUP"]
        plt.close(fig)

    def test_tick_affix_without_axis_unit_is_clean(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0.0, 0.1, 0.2])
        ax.set_yticks([0.0, 0.1, 0.2])
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
        ax.set_ylabel("Rate")

        warnings = validate_figure(fig, checks=("UNIT_DUP",), quiet=True)

        assert not [w for w in warnings if w.check_id == "UNIT_DUP"]
        plt.close(fig)

    def test_mismatched_tick_affix_reports_info(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [1, 2, 3])
        ax.set_yticks([1, 2, 3])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f pts"))
        ax.set_ylabel("Value [score]")

        warnings = validate_figure(fig, checks=("UNIT_DUP",), quiet=True)

        hits = [w for w in warnings if w.check_id == "UNIT_DUP"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.INFO
        assert hits[0].detail["tick_affix"] == " pts"
        plt.close(fig)


class TestCheckTickRotation:
    """TICK_ROTATION catches avoidable and missing x-label rotation."""

    def test_short_labels_rotated_with_room_fire(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 3))
        labels = ["A", "B", "C", "D"]
        ax.plot(range(len(labels)), [1, 2, 3, 4])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45)

        warnings = validate_figure(fig, checks=("TICK_ROTATION",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_ROTATION"]
        assert len(hits) == 1
        assert "rotation=0" in hits[0].message
        plt.close(fig)

    def test_dense_long_labels_without_rotation_fire(self) -> None:
        fig, ax = plt.subplots(figsize=(3, 2))
        labels = [f"very long category {i:02d}" for i in range(6)]
        ax.plot(range(len(labels)), range(len(labels)))
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=0)

        warnings = validate_figure(fig, checks=("TICK_ROTATION",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_ROTATION"]
        assert len(hits) == 1
        assert "45" in hits[0].message
        plt.close(fig)

    def test_horizontal_labels_with_room_are_clean(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 3))
        labels = ["A", "B", "C", "D"]
        ax.plot(range(len(labels)), [1, 2, 3, 4])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=0)

        warnings = validate_figure(fig, checks=("TICK_ROTATION",), quiet=True)

        assert not [w for w in warnings if w.check_id == "TICK_ROTATION"]
        plt.close(fig)


class TestCheckTickDecimal:
    """TICK_DECIMAL detects ambiguous or over-precise numeric tick labels."""

    def test_integer_ticks_rendered_with_decimal_fire(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0, 5, 10])
        ax.set_yticks([0, 5, 10])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.INFO
        assert "trailing zero" in hits[0].message
        plt.close(fig)

    def test_non_uniform_decimal_places_warn(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [17.5, 20.0, 22.5])
        ax.set_yticks([17.5, 20.0, 22.5])
        ax.set_yticklabels(["17.5", "20", "22.5"])

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.WARNING
        assert "non-uniform" in hits[0].message
        plt.close(fig)

    def test_fractional_step_uniform_decimal_places_are_clean(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [17.5, 20.0, 22.5])
        ax.set_yticks([17.5, 20.0, 22.5])
        ax.set_yticklabels(["17.5", "20.0", "22.5"])

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        assert not [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        plt.close(fig)

    def test_half_step_with_one_decimal_is_clean(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0, 2.5, 5.0])
        ax.set_yticks([0, 2.5, 5.0])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        assert not [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        plt.close(fig)

    def test_adjacent_ticks_rendered_same_string_warn(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0, 0.04, 0.08])
        ax.set_yticks([0, 0.04, 0.08])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.WARNING
        assert "same string" in hits[0].message
        plt.close(fig)

    def test_excess_precision_fire(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.plot([0, 1, 2], [0, 0.5, 1.0])
        ax.set_yticks([0, 0.5, 1.0])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.4f"))

        warnings = validate_figure(fig, checks=("TICK_DECIMAL",), quiet=True)

        hits = [w for w in warnings if w.check_id == "TICK_DECIMAL"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.INFO
        assert "precision" in hits[0].message
        plt.close(fig)


class TestCheckLegendOverflow:
    """Tests for LEGEND_OVERFLOW detection."""

    def test_huge_legend(self) -> None:
        """A legend with many items in small plot should trigger warning."""
        fig, ax = plt.subplots(figsize=(2, 2))
        for i in range(20):
            ax.plot([0, 1], [i, i + 1], label=f"Series {i:02d} long label")
        ax.legend(loc="center")
        warnings = validate_figure(fig, checks=("LEGEND_OVERFLOW",), quiet=True)
        legend_warnings = [
            w for w in warnings if w.check_id == "LEGEND_OVERFLOW"
        ]
        assert len(legend_warnings) > 0
        plt.close(fig)

    def test_no_legend(self) -> None:
        """No legend should not trigger LEGEND_OVERFLOW."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        warnings = validate_figure(fig, checks=("LEGEND_OVERFLOW",), quiet=True)
        legend_warnings = [
            w for w in warnings if w.check_id == "LEGEND_OVERFLOW"
        ]
        assert len(legend_warnings) == 0
        plt.close(fig)


class TestCheckSubset:
    """Tests for check filtering."""

    def test_subset_filtering(self) -> None:
        """Only selected checks should run."""
        fig, ax = plt.subplots(figsize=(4, 3))
        # Don't plot anything (triggers EMPTY_AXES)
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        # EMPTY_AXES should NOT appear since it's not selected
        assert all(w.check_id != "EMPTY_AXES" for w in warnings)
        plt.close(fig)


class TestValidateEdgeCases:
    """Edge case tests for increased coverage."""

    def test_verbose_mode_prints_warnings(self, capsys) -> None:
        """Non-quiet mode with warnings should print them."""
        fig, _ax = plt.subplots(figsize=(4, 3))
        # Empty axes triggers EMPTY_AXES warning
        validate_figure(fig, checks=("EMPTY_AXES",), quiet=False)
        captured = capsys.readouterr()
        assert "[VISUAL]" in captured.out
        assert "EMPTY_AXES" in captured.out
        plt.close(fig)

    def test_verbose_mode_prints_ok_when_clean(self, capsys) -> None:
        """Non-quiet mode with no warnings prints success."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        validate_figure(fig, quiet=False)
        captured = capsys.readouterr()
        assert "No visual issues detected" in captured.out
        plt.close(fig)

    def test_all_checks_run_by_default(self) -> None:
        """When checks=None, all check types are executed."""
        fig, _ax = plt.subplots(figsize=(4, 3))
        # Empty axes → should find EMPTY_AXES at minimum
        warnings = validate_figure(fig, quiet=True)
        check_ids = {w.check_id for w in warnings}
        assert "EMPTY_AXES" in check_ids
        plt.close(fig)

    def test_visual_warning_detail_dict(self) -> None:
        """VisualWarning.detail stores arbitrary metadata."""
        w = VisualWarning(
            severity=Severity.WARNING,
            check_id="TEST",
            message="msg",
            detail={"px": 10.5, "side": "left"},
        )
        assert w.detail["px"] == 10.5
        assert w.detail["side"] == "left"

    def test_multi_axes_partial_empty(self) -> None:
        """Mixed figure: one axes with data, one empty."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3))
        ax1.plot([1, 2, 3])
        # ax2 is empty
        warnings = validate_figure(fig, checks=("EMPTY_AXES",), quiet=True)
        empty = [w for w in warnings if w.check_id == "EMPTY_AXES"]
        assert len(empty) == 1
        assert empty[0].detail["axes_index"] == 1
        plt.close(fig)


class TestCheckMarginAsymmetry:
    """Tests for MARGIN_ASYMMETRY detection."""

    def test_asymmetric_margin_detected(self) -> None:
        """A chart pushed to one side should trigger MARGIN_ASYMMETRY."""
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.barh([0], [1])
        # Squeeze subplot into the left 25% of the figure canvas.
        fig.subplots_adjust(left=0.08, right=0.30)
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) > 0
        # The large empty area should be on the right.
        h_warnings = [w for w in asym if w.detail.get("axis") == "horizontal"]
        assert any(w.detail["side"] == "right" for w in h_warnings)
        plt.close(fig)

    def test_balanced_margin_clean(self) -> None:
        """A centered chart should NOT trigger MARGIN_ASYMMETRY."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        ax.set_ylabel("Y Label")
        ax.set_xlabel("X Label")
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) == 0
        plt.close(fig)


class TestCheckPieLabelOffset:
    """Tests for PIE_LABEL_OFFSET detection."""

    def test_donut_default_pctdistance(self) -> None:
        """Donut with default pctdistance=0.6 should flag offset labels."""
        fig, ax = plt.subplots(figsize=(4, 4))
        # Default pctdistance=0.6, wedge width=0.4 → ideal_r = 0.8
        ax.pie(
            [40, 30, 20, 10],
            labels=["A", "B", "C", "D"],
            autopct="%.0f%%",
            pctdistance=0.6,
            wedgeprops={"width": 0.4},
        )
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        pie_w = [w for w in warnings if w.check_id == "PIE_LABEL_OFFSET"]
        assert len(pie_w) > 0
        plt.close(fig)

    def test_donut_centered_pctdistance(self) -> None:
        """Donut with correctly centered pctdistance should be clean."""
        fig, ax = plt.subplots(figsize=(4, 4))
        width = 0.4
        ideal_pct = 1.0 - width / 2.0  # = 0.8
        ax.pie(
            [40, 30, 20, 10],
            labels=["A", "B", "C", "D"],
            autopct="%.0f%%",
            pctdistance=ideal_pct,
            wedgeprops={"width": width},
        )
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        pie_w = [w for w in warnings if w.check_id == "PIE_LABEL_OFFSET"]
        assert len(pie_w) == 0
        plt.close(fig)

    def test_regular_pie_ignored(self) -> None:
        """Regular pie (not donut) should be skipped entirely."""
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie([40, 30, 20, 10], labels=["A", "B", "C", "D"], autopct="%.0f%%")
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        pie_w = [w for w in warnings if w.check_id == "PIE_LABEL_OFFSET"]
        assert len(pie_w) == 0
        plt.close(fig)

    def test_donut_no_autopct(self) -> None:
        """Donut without autopct should not trigger label offset check."""
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie([40, 30, 20, 10], wedgeprops={"width": 0.4})
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        assert len(warnings) == 0
        plt.close(fig)

    def test_thin_donut_centered(self) -> None:
        """Very thin donut (width=0.15) with ideal pctdistance."""
        fig, ax = plt.subplots(figsize=(4, 4))
        width = 0.15
        ax.pie(
            [50, 30, 20],
            autopct="%.0f%%",
            pctdistance=1.0 - width / 2.0,
            wedgeprops={"width": width},
        )
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        assert len(warnings) == 0
        plt.close(fig)

    def test_wide_donut_off_center(self) -> None:
        """Wide donut (width=0.7) with pctdistance far from ideal."""
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(
            [50, 30, 20],
            autopct="%.0f%%",
            pctdistance=0.4,  # ideal = 0.65
            wedgeprops={"width": 0.7},
        )
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        assert len(warnings) > 0
        plt.close(fig)

    def test_many_slices_off_center(self) -> None:
        """Donut with many slices and wrong pctdistance."""
        fig, ax = plt.subplots(figsize=(5, 5))
        sizes = [5, 8, 12, 15, 20, 10, 7, 3, 5, 15]
        ax.pie(
            sizes, autopct="%.0f%%", pctdistance=0.5, wedgeprops={"width": 0.35}
        )
        warnings = validate_figure(
            fig, checks=("PIE_LABEL_OFFSET",), quiet=True
        )
        assert len(warnings) > 0
        plt.close(fig)


class TestMarginAsymmetryEdgeCases:
    """Edge-case tests for MARGIN_ASYMMETRY."""

    def test_empty_figure_no_crash(self) -> None:
        """Empty figure with no axes should not crash."""
        fig = plt.figure(figsize=(6, 4))
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        assert len(warnings) == 0
        plt.close(fig)

    def test_tiny_figure_no_false_positive(self) -> None:
        """Very small figure should not trigger false positives."""
        fig, ax = plt.subplots(figsize=(1.5, 1))
        ax.plot([1, 2, 3])
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) == 0
        plt.close(fig)

    def test_extreme_vertical_asymmetry(self) -> None:
        """Extreme top/bottom asymmetry should be detected."""
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.bar([0, 1, 2], [5, 10, 3])
        fig.subplots_adjust(bottom=0.60, top=0.95)
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        v_warnings = [w for w in asym if w.detail.get("axis") == "vertical"]
        assert len(v_warnings) > 0
        plt.close(fig)

    def test_multi_subplot_balanced(self) -> None:
        """2x2 subplot grid should be balanced by default."""
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        for ax in axes.flat:
            ax.plot([1, 2, 3])
            ax.set_ylabel("Y")
        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) == 0
        plt.close(fig)


class TestCheckOverflowDegenerateData:
    """Regressions for degenerate input that used to crash _check_overflow."""

    def test_nan_only_y_does_not_crash(self) -> None:
        """A line whose y-values are all NaN must not crash validate.

        matplotlib still creates a Line2D artist, but its bbox is
        degenerate. _check_overflow must skip such artists silently."""
        import numpy as np

        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3], [np.nan, np.nan, np.nan])
        ax.set_ylabel("Value")
        # Must return without raising even when the artist tree contains
        # NaN-backed lines whose tightbbox is undefined.
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        # We don't care which warnings fired, only that we didn't crash.
        assert isinstance(warnings, list)
        plt.close(fig)

    def test_empty_extent_text_skipped(self) -> None:
        """A Text artist whose get_window_extent returns a zero-area
        bbox (e.g. text="" but visible) must not produce a spurious
        overflow."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3])
        # ax.text with whitespace-only string is filtered already; this
        # test pins behaviour for a degenerate fontsize=0 label.
        ax.set_xlabel("", fontsize=0)
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        assert all(w.check_id != "OVERFLOW" for w in warnings)
        plt.close(fig)


class TestCheckClippedText:
    """CLIPPED_TEXT fires when a Text artist's drawn pixels overlap the
    edge strip of the figure canvas (≤ 1 px from any side)."""

    def test_clipped_xtick_label(self) -> None:
        """Long x-tick labels with a tight figure should be flagged."""
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([0, 1, 2], [1, 2, 3])
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["LongLabel" * 4, "B" * 30, "C" * 30])
        warnings = validate_figure(fig, checks=("CLIPPED_TEXT",), quiet=True)
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) > 0
        plt.close(fig)

    def test_clean_figure_no_clipped(self) -> None:
        """A normally-laid-out figure should not flag CLIPPED_TEXT."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        fig.subplots_adjust(left=0.20, right=0.95, bottom=0.18, top=0.92)
        warnings = validate_figure(fig, checks=("CLIPPED_TEXT",), quiet=True)
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) == 0
        plt.close(fig)

    def test_clipped_text_in_default_check_set(self) -> None:
        """CLIPPED_TEXT is registered in the default check set."""
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([0, 1, 2], [1, 2, 3])
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["A" * 30, "B" * 30, "C" * 30])
        warnings = validate_figure(fig, quiet=True)  # default checks
        ids = {w.check_id for w in warnings}
        assert "CLIPPED_TEXT" in ids
        plt.close(fig)


class TestValidateAuditRegressions:
    """Regressions for the 2026-07 quality audit (Batch D)."""

    def test_clipped_text_silent_on_flush_layout(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        dm.simple_layout(fig)  # margin=0 -> content flush at edges
        warnings = validate_figure(fig, quiet=True)
        assert not [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        plt.close(fig)

    def test_empty_axes_ignores_legend_panel(self) -> None:
        fig, (ax1, axleg) = plt.subplots(1, 2)
        (line,) = ax1.plot([0, 1], [0, 1], label="s")
        axleg.axis("off")
        axleg.legend(handles=[line], loc="center")
        warnings = validate_figure(fig, quiet=True)
        assert not [w for w in warnings if w.check_id == "EMPTY_AXES"]
        plt.close(fig)

    def test_empty_axes_ignores_invisible_only_artist(self) -> None:
        fig, ax = plt.subplots()
        (line,) = ax.plot([0, 1], [0, 1])
        line.set_visible(False)
        warnings = validate_figure(fig, quiet=True)
        assert [w for w in warnings if w.check_id == "EMPTY_AXES"]
        plt.close(fig)

    def test_overflow_catches_offcanvas_suptitle(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        fig.suptitle("A long suptitle pushed off the top", y=1.15)
        warnings = validate_figure(fig, quiet=True)
        assert [
            w
            for w in warnings
            if w.check_id == "OVERFLOW" and "Figure text" in w.message
        ]
        plt.close(fig)

    def test_legend_overflow_catches_offcanvas_anchor(self) -> None:
        fig, ax = plt.subplots()
        for k in range(12):
            ax.plot([0, 1], [k, k + 1], label=f"series {k}")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
        warnings = validate_figure(fig, quiet=True)
        assert [w for w in warnings if w.check_id == "LEGEND_OVERFLOW"]
        plt.close(fig)

    def test_errored_check_does_not_report_clean(self, capsys) -> None:
        from dartwork_mpl.validate import _types
        from dartwork_mpl.validate._orchestrator import _run_check_safely

        # A check raising a bbox error yields None (could-not-run),
        # never an empty "ran clean" list.
        def boom() -> list:
            raise _types.BBOX_ERRORS[0]("boom")

        assert _run_check_safely(boom) is None
