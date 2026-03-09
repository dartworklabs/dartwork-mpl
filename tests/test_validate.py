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
