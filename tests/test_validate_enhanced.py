"""Tests for dartwork_mpl.validate_enhanced — auto-fix validation helpers."""

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
    dm.auto_layout(fig)
    return fig, ax


class TestGetFixSuggestions:
    def test_returns_list_for_overflow(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="left overflow 12px",
            detail={"side": "left", "px": 12},
        )
        suggestions = dm.validate_enhanced.get_fix_suggestions(warning)
        assert isinstance(suggestions, list)
        assert all(isinstance(s, str) for s in suggestions)
        # The left-overflow branch offers at least one concrete fix
        assert any(
            "auto_layout" in s or "subplots_adjust" in s for s in suggestions
        )

    def test_unknown_check_id_returns_empty(self) -> None:
        warning = VisualWarning(
            check_id="DOES_NOT_EXIST",
            severity=Severity.WARNING,
            message="",
            detail={},
        )
        assert dm.validate_enhanced.get_fix_suggestions(warning) == []


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
        ``dm.validate_enhanced.validate_with_fixes``."""
        assert (
            dm.validate_with_fixes is dm.validate_enhanced.validate_with_fixes
        )


class TestCheckAgentRequirements:
    def test_returns_dict_of_bools(self) -> None:
        fig, _ax = _figure_clean()
        result = dm.validate_enhanced.check_agent_requirements(fig)
        assert isinstance(result, dict)
        assert all(isinstance(v, bool) for v in result.values())
        # Stable keys we actually document
        for key in ("high_dpi", "style_applied", "axis_labels", "has_data"):
            assert key in result
        plt.close(fig)


class TestGenerateValidationReport:
    def test_returns_report_string(self) -> None:
        fig, _ax = _figure_clean()
        report = dm.validate_enhanced.generate_validation_report(fig)
        assert isinstance(report, str)
        assert "VALIDATION REPORT" in report
        assert "OVERALL SCORE" in report
        plt.close(fig)
