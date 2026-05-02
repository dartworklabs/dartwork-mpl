"""Tests for visual validation module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

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

        fig, ax = dm.subplots(width="9cm", aspect="standard")
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

        fig, ax = dm.subplots(width="13cm", aspect="standard")
        # Data tops out at 78 → matplotlib auto-locator extends ticks
        # to 90 (a "nice" round number outside the axis ylim of ~82).
        ax.bar(["A", "B", "C", "D", "E"], [23, 45, 56, 78, 33])
        ax.set_ylabel("Value")
        dm.auto_layout(fig)
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

        fig, ax = dm.subplots(width="13cm", aspect="standard")
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

        fig, ax = dm.subplots(width="13cm", aspect="standard")
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
        warnings = validate_figure(
            fig, checks=("CLIPPED_TEXT",), quiet=True
        )
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) > 0
        plt.close(fig)

    def test_clean_figure_no_clipped(self) -> None:
        """A normally-laid-out figure should not flag CLIPPED_TEXT."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        fig.subplots_adjust(
            left=0.20, right=0.95, bottom=0.18, top=0.92
        )
        warnings = validate_figure(
            fig, checks=("CLIPPED_TEXT",), quiet=True
        )
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) == 0
        plt.close(fig)

    def test_clipped_text_in_default_check_set(self) -> None:
        """CLIPPED_TEXT is registered in the default check set."""
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([0, 1, 2], [1, 2, 3])
        ax.set_xticklabels(["A" * 30, "B" * 30, "C" * 30])
        warnings = validate_figure(fig, quiet=True)  # default checks
        ids = {w.check_id for w in warnings}
        assert "CLIPPED_TEXT" in ids
        plt.close(fig)
