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


class TestStyleAppliedIsFigureLocal:
    """``style_applied`` inspects the figure's own text artists, not the
    process-global ``plt.rcParams`` (which is mutated independently)."""

    def test_custom_font_size_detected(self) -> None:
        from dartwork_mpl.validate_fixes import _style_applied

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        ax.set_xlabel("x", fontsize=14)  # off matplotlib's 10.0 default
        assert _style_applied(fig) is True
        plt.close(fig)

    def test_default_font_size_not_detected(self) -> None:
        # All text artists left at matplotlib's 10.0 default ⇒ no
        # figure-local evidence of a preset. (rcParams reset to defaults
        # so dartwork's import-time style does not leak in.)
        import matplotlib as mpl

        from dartwork_mpl.validate_fixes import _style_applied

        with mpl.rc_context(mpl.rcParamsDefault):
            fig, ax = plt.subplots()
            ax.plot([1, 2, 3])
            assert _style_applied(fig) is False
            plt.close(fig)


class TestProperColorsHeuristic:
    """``proper_colors`` flags explicit matplotlib basic colors on data
    marks — single-letter codes, full names, and patch facecolors."""

    def test_full_name_line_flagged(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], color="red")
        assert check_agent_requirements(fig)["proper_colors"] is False
        plt.close(fig)

    def test_single_letter_bar_flagged(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.bar(["a", "b"], [1, 2], color="g")
        assert check_agent_requirements(fig)["proper_colors"] is False
        plt.close(fig)

    def test_hex_color_not_flagged(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], color="#1a73e8")
        assert check_agent_requirements(fig)["proper_colors"] is True
        plt.close(fig)

    def test_scatter_basic_color_flagged(self) -> None:
        """Scatter marks live in ``ax.collections``, which the heuristic
        previously never inspected — ``color="red"`` passed (VAL-1)."""
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.scatter([1, 2, 3], [1, 2, 3], color="red")
        assert check_agent_requirements(fig)["proper_colors"] is False
        plt.close(fig)

    def test_scatter_hex_color_not_flagged(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.scatter([1, 2, 3], [1, 2, 3], color="#1a73e8")
        assert check_agent_requirements(fig)["proper_colors"] is True
        plt.close(fig)


class TestAxisLabelsExemptions:
    """``axis_labels`` skips axes types that have no meaningful x/y
    labels — pie/donut, polar, 3D, frame-off (VAL-3)."""

    def test_pie_chart_passes_axis_labels(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.pie([1, 2, 3])
        assert check_agent_requirements(fig)["axis_labels"] is True
        plt.close(fig)

    def test_polar_axes_passes_axis_labels(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig = plt.figure()
        fig.add_subplot(projection="polar")
        assert check_agent_requirements(fig)["axis_labels"] is True
        plt.close(fig)

    def test_rectilinear_axes_still_required(self) -> None:
        from dartwork_mpl.validate_fixes import check_agent_requirements

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])  # no labels set
        assert check_agent_requirements(fig)["axis_labels"] is False
        plt.close(fig)


class TestOverflowSuggestionClamped:
    """Suggested ``subplots_adjust`` fractions stay in a valid band even
    for large overflows (VAL-2: px=90 used to suggest left=1.05)."""

    def test_large_left_overflow_clamped(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="left overflow 90px",
            detail={"side": "left", "px": 90},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        adjust = next(s for s in suggestions if "subplots_adjust" in s)
        value = float(adjust.split("left=")[1].rstrip(")"))
        assert 0.0 < value < 0.5

    def test_large_top_overflow_clamped(self) -> None:
        warning = VisualWarning(
            check_id="OVERFLOW",
            severity=Severity.WARNING,
            message="top overflow 90px",
            detail={"side": "top", "px": 90},
        )
        suggestions = dm.validate_fixes.get_fix_suggestions(warning)
        adjust = next(s for s in suggestions if "subplots_adjust" in s)
        value = float(adjust.split("top=")[1].rstrip(")"))
        assert 0.5 < value < 1.0


class TestAutoApplyAppliesLayoutOnce:
    """OVERFLOW / MARGIN_ASYMMETRY share one whole-figure fix; auto-apply
    must call simple_layout at most once, not once per warning."""

    def test_single_layout_fix_entry(self) -> None:
        fig, _ax = _figure_with_overflow()
        _warnings, applied = dm.validate_with_fixes(
            fig, auto_apply=True, verbose=False
        )
        layout_entries = [a for a in applied if "simple_layout" in a]
        assert len(layout_entries) <= 1
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
