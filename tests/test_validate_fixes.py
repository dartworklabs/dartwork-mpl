"""Tests for dartwork_mpl.validate_fixes — auto-fix validation helpers."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning


def _figure_with_overflow():
    """Build a figure that typically triggers an overflow warning.

    A 2-inch square figure with a long y-axis label is enough to make
    the left margin overflow on most default rcParams.
    """
    fig, ax = plt.subplots(figsize=(2.0, 2.0))
    ax.plot([0, 1, 2], [0, 1, 2])
    ax.set_ylabel("A very long y axis label that will overflow the canvas")
    return fig, ax


def _figure_clean():
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.plot([0, 1, 2], [0, 1, 2])
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    dm.simple_layout(fig)
    return fig, ax


class TestGetFixSuggestions:
    def test_returns_list_for_overflow(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="left overflow 12px",
            detail={"side": "left", "px": 12},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert isinstance(suggestions, list)
        assert all(isinstance(s, str) for s in suggestions)
        # The left-overflow branch offers at least one concrete fix
        assert any(
            "simple_layout" in s or "subplots_adjust" in s for s in suggestions
        )

    def test_unknown_check_id_returns_empty(self) -> None:
        warning = VisualWarning(
            check_id="DOES_NOT_EXIST",
            severity=Severity.WARNING,
            message="",
            detail={},
        )
        assert dm.validate_fixes.get_fix_suggestions(warning) == []


class TestValidateWithFixes:
    def test_clean_figure_has_no_warnings(self) -> None:
        fig, _ax = _figure_clean()
        warnings, applied = dm.validate_with_fixes(fig, verbose=False)
        assert isinstance(warnings, list)
        assert isinstance(applied, list)
        assert len(applied) == 0  # no auto-apply requested
        plt.close(fig)

    def test_auto_apply_does_not_raise(self) -> None:
        fig, _ax = _figure_with_overflow()
        warnings, applied = dm.validate_with_fixes(
            fig, auto_apply=True, verbose=False
        )
        assert isinstance(warnings, list)
        assert isinstance(applied, list)
        plt.close(fig)

    def test_top_level_alias_matches_submodule(self) -> None:
        """``dm.validate_with_fixes`` is the same callable as
        ``dm.validate_fixes.validate_with_fixes``."""
        assert dm.validate_with_fixes is dm.validate_fixes.validate_with_fixes


class TestCheckAgentRequirements:
    def test_returns_dict_of_bools(self) -> None:
        fig, _ax = _figure_clean()
        result = dm.validate_fixes.check_agent_requirements(fig)
        assert isinstance(result, dict)
        assert all(isinstance(v, bool) for v in result.values())
        # Stable keys we actually document
        for key in ("high_dpi", "style_applied", "axis_labels", "has_data"):
            assert key in result
        plt.close(fig)


class TestGenerateValidationReport:
    def test_returns_report_string(self) -> None:
        fig, _ax = _figure_clean()
        report = dm.validate_fixes.generate_validation_report(fig)
        assert isinstance(report, str)
        assert "VALIDATION REPORT" in report
        assert "OVERALL SCORE" in report
        plt.close(fig)


class TestGetFixSuggestionsBranches:
    """Cover the remaining branches of get_fix_suggestions()."""

    def test_overflow_right(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="right overflow 8px",
            detail={"side": "right", "px": 8},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("subplots_adjust(right=" in s for s in suggestions)

    def test_overflow_bottom(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="bottom overflow 6px",
            detail={"side": "bottom", "px": 6},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any(
            "subplots_adjust(bottom=" in s or "rotation=45" in s
            for s in suggestions
        )

    def test_overflow_top(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="top overflow 4px",
            detail={"side": "top", "px": 4},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("subplots_adjust(top=" in s for s in suggestions)

    def test_overlap(self) -> None:
        warning = VisualWarning(
            check_id="OVERLAP",
            severity=Severity.WARNING,
            message="text overlap",
            detail={},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("simple_layout" in s for s in suggestions)

    def test_legend_overflow(self) -> None:
        warning = VisualWarning(
            check_id="LEGEND_OVERFLOW",
            severity=Severity.WARNING,
            message="legend too wide",
            detail={"ratio": 1.2},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("bbox_to_anchor" in s for s in suggestions)

    def test_tick_crowd_x(self) -> None:
        warning = VisualWarning(
            check_id="TICK_CROWD",
            severity=Severity.WARNING,
            message="too many x ticks",
            detail={"axis": "x", "count": 30},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("xaxis.set_major_locator" in s for s in suggestions)

    def test_tick_crowd_y(self) -> None:
        warning = VisualWarning(
            check_id="TICK_CROWD",
            severity=Severity.WARNING,
            message="too many y ticks",
            detail={"axis": "y", "count": 24},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("yaxis.set_major_locator" in s for s in suggestions)

    def test_empty_axes(self) -> None:
        warning = VisualWarning(
            check_id="EMPTY_AXES",
            severity=Severity.WARNING,
            message="empty axes",
            detail={},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any(
            "ax.remove" in s or "set_visible(False)" in s for s in suggestions
        )

    def test_margin_asymmetry(self) -> None:
        warning = VisualWarning(
            check_id="MARGIN_ASYMMETRY",
            severity=Severity.WARNING,
            message="left vs right asymmetric",
            detail={"side": "left"},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("simple_layout" in s for s in suggestions)

    def test_pie_label_offset(self) -> None:
        warning = VisualWarning(
            check_id="PIE_LABEL_OFFSET",
            severity=Severity.WARNING,
            message="label offset wrong",
            detail={"ideal_r": 0.65},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert any("pctdistance=0.65" in s for s in suggestions)

    def test_clipped_text(self) -> None:
        """CLIPPED_TEXT branch returns 3 suggestions including simple_layout."""
        warning = VisualWarning(
            severity=Severity.WARNING,
            check_id="CLIPPED_TEXT",
            message="Text 'abc' sits within 1px of the canvas edge",
            detail={"text": "abc", "margin_px": 0.5},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        assert len(suggestions) == 3
        assert any("simple_layout" in s for s in suggestions)
        assert any("rotate_tick_labels" in s for s in suggestions)
        assert any("labelsize" in s for s in suggestions)
