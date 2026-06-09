"""Enhanced validation with auto-fix suggestions for agents.

Extends the base validation with actionable fixes that agents can apply.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
from matplotlib.figure import Figure

from .validate import Severity, VisualWarning, validate_figure

# matplotlib's hard default base font size (pt). dartwork style presets
# all move font.size off this value, so a figure whose text artists carry
# a different size is figure-local evidence that a preset was active when
# they were created (see ``_style_applied``).
_MPL_DEFAULT_FONT_SIZE = 10.0

# matplotlib's eight single-letter color codes and their full-name
# aliases. Using any of these for *data* marks is the "default palette"
# smell ``proper_colors`` flags. White is excluded — it is a legitimate
# background / negative-space choice, not a data color.
_MPL_BASIC_COLOR_NAMES = frozenset(
    {
        "b",
        "g",
        "r",
        "c",
        "m",
        "y",
        "k",
        "blue",
        "green",
        "red",
        "cyan",
        "magenta",
        "yellow",
        "black",
    }
)
# Resolved RGBA of the basic colors, for matching patch facecolors (which
# matplotlib stores as resolved RGBA tuples, not the original string).
_MPL_BASIC_COLOR_RGBA = frozenset(
    mcolors.to_rgba(name) for name in ("b", "g", "r", "c", "m", "y", "k")
)


def get_fix_suggestions(warning: VisualWarning) -> list[str]:
    """Generate fix suggestions for a visual warning.

    Parameters
    ----------
    warning : VisualWarning
        The warning to generate fixes for

    Returns
    -------
    list[str]
        List of suggested fixes (code snippets)
    """
    suggestions = []

    if warning.check_id == "OVERFLOW":
        side = warning.detail.get("side", "")
        px = warning.detail.get("px", 0)

        if side == "left":
            suggestions.append(
                f"# Increase left margin\nfig.subplots_adjust(left={0.15 + px / 100:.2f})"
            )
            suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
        elif side == "right":
            suggestions.append(
                f"# Increase right margin\nfig.subplots_adjust(right={0.95 - px / 100:.2f})"
            )
            suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
        elif side == "bottom":
            suggestions.append(
                f"# Increase bottom margin\nfig.subplots_adjust(bottom={0.15 + px / 100:.2f})"
            )
            suggestions.append(
                "# Rotate x-tick labels\nax.tick_params(axis='x', rotation=45)"
            )
        elif side == "top":
            suggestions.append(
                f"# Increase top margin\nfig.subplots_adjust(top={0.9 - px / 100:.2f})"
            )

    elif warning.check_id == "OVERLAP":
        suggestions.append(
            "# Adjust text positions\nax.text(..., ha='left')  # Change alignment"
        )
        suggestions.append("# Use simple_layout\ndm.simple_layout(fig)")
        suggestions.append("# Reduce font size\nax.legend(fontsize=dm.fs(-1))")

    elif warning.check_id == "LEGEND_OVERFLOW":
        suggestions.append(
            "# Move legend outside\nax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')"
        )
        suggestions.append("# Reduce legend columns\nax.legend(ncol=1)")
        suggestions.append(
            "# Reduce legend font\nax.legend(fontsize=dm.fs(-2))"
        )

    elif warning.check_id == "TICK_CROWD":
        axis = warning.detail.get("axis", "")
        count = warning.detail.get("count", 0)

        if axis == "x":
            suggestions.append(
                f"# Reduce x-ticks\nax.xaxis.set_major_locator(plt.MaxNLocator(nbins={count // 2}))"
            )
            suggestions.append(
                "# Rotate labels\nax.tick_params(axis='x', rotation=45)"
            )
        else:
            suggestions.append(
                f"# Reduce y-ticks\nax.yaxis.set_major_locator(plt.MaxNLocator(nbins={count // 2}))"
            )

    elif warning.check_id == "EMPTY_AXES":
        suggestions.append("# Remove empty axes\nax.remove()")
        suggestions.append("# Or hide it\nax.set_visible(False)")

    elif warning.check_id == "MARGIN_ASYMMETRY":
        side = warning.detail.get("side", "")
        if side in ["left", "right"]:
            suggestions.append("# Center horizontally\ndm.simple_layout(fig)")
        else:
            suggestions.append("# Center vertically\ndm.simple_layout(fig)")

    elif warning.check_id == "PIE_LABEL_OFFSET":
        ideal_r = warning.detail.get("ideal_r", 0.7)
        suggestions.append(
            f"# Adjust label position\nax.pie(..., pctdistance={ideal_r:.2f})"
        )

    elif warning.check_id == "CLIPPED_TEXT":
        suggestions.append(
            "# Run the simple_layout pass\ndm.simple_layout(fig)"
        )
        suggestions.append(
            "# Or rotate the offending label\n"
            "dm.rotate_tick_labels(ax, axis='x', rotation=45)"
        )
        suggestions.append(
            "# Or shrink the font\n"
            "ax.tick_params(axis='both', labelsize=dm.fs(-2))"
        )

    return suggestions


def validate_with_fixes(
    fig: Figure, auto_apply: bool = False, verbose: bool = True
) -> tuple[list[VisualWarning], list[str]]:
    """Validate figure and provide fix suggestions.

    Parameters
    ----------
    fig : Figure
        Figure to validate
    auto_apply : bool
        Whether to attempt automatic fixes
    verbose : bool
        Whether to print suggestions

    Returns
    -------
    tuple[list[VisualWarning], list[str]]
        Warnings and applied fixes
    """
    import dartwork_mpl as dm

    warnings = validate_figure(fig, quiet=not verbose)
    applied_fixes: list[str] = []

    if not warnings:
        return warnings, applied_fixes

    if verbose:
        print("\n=== FIX SUGGESTIONS ===")

    # ``dm.simple_layout(fig)`` is a whole-figure operation: one call
    # resolves every OVERFLOW / MARGIN_ASYMMETRY warning at once. The old
    # code called it once *per* such warning inside the loop, which re-ran
    # the layout solver redundantly and listed N identical "Applied
    # simple_layout" entries for a single mutation. Collect the trigger
    # here, apply exactly once below.
    layout_fix_check_ids: list[str] = []

    for warning in warnings:
        suggestions = get_fix_suggestions(warning)

        if verbose and suggestions:
            print(f"\n{warning.check_id}: {warning.message}")
            for i, suggestion in enumerate(suggestions, 1):
                print(
                    f"  Option {i}:\n    {suggestion.replace(chr(10), chr(10) + '    ')}"
                )

        if (
            auto_apply
            and warning.severity == Severity.WARNING
            and warning.check_id in ("OVERFLOW", "MARGIN_ASYMMETRY")
        ):
            layout_fix_check_ids.append(warning.check_id)

    if auto_apply and layout_fix_check_ids:
        triggers = ", ".join(sorted(set(layout_fix_check_ids)))
        try:
            dm.simple_layout(fig)
            applied_fixes.append(
                f"Applied dm.simple_layout() once for {triggers} "
                f"({len(layout_fix_check_ids)} warning(s))"
            )
            if verbose:
                print(f"  ✓ Auto-applied once: dm.simple_layout() [{triggers}]")
        except Exception as e:  # noqa: BLE001
            # Auto-apply is opportunistic — any layout failure
            # (simple_layout regressions, backend errors, custom artist
            # exceptions) must report a failed fix and continue, not
            # abort the whole validate_with_fixes run. Narrowing the
            # catch silently regressed that.
            if verbose:
                print(f"  ✗ Failed to auto-fix: {e}")

    # Re-validate after fixes
    if applied_fixes and auto_apply:
        new_warnings = validate_figure(fig, quiet=True)
        if verbose:
            print(
                f"\n=== AFTER AUTO-FIX: {len(new_warnings)} warnings (was {len(warnings)}) ==="
            )
        return new_warnings, applied_fixes

    return warnings, applied_fixes


def check_agent_requirements(fig: Figure) -> dict[str, bool]:
    """Check if figure meets agent coding requirements.

    Parameters
    ----------
    fig : Figure
        Figure to check

    Returns
    -------
    dict[str, bool]
        Requirement name -> pass/fail
    """
    requirements = {}

    # Check DPI
    requirements["high_dpi"] = fig.dpi >= 200

    # Check if a (dartwork) style preset was applied — figure-local, not
    # the process-global rcParams (which any later style.use / rcdefaults
    # call mutates independently of *this* figure).
    requirements["style_applied"] = _style_applied(fig)

    # Check for axis labels
    has_labels = True
    for ax in fig.axes:
        if ax.get_visible():
            if ax.xaxis.get_visible() and not ax.get_xlabel():
                has_labels = False
            if ax.yaxis.get_visible() and not ax.get_ylabel():
                has_labels = False
    requirements["axis_labels"] = has_labels

    # Check for data
    has_data = False
    for ax in fig.axes:
        if (
            len(ax.lines) > 0
            or len(ax.patches) > 0
            or len(ax.collections) > 0
            or len(ax.images) > 0
        ):
            has_data = True
            break
    requirements["has_data"] = has_data

    # Check color usage (no matplotlib basic-palette defaults). Heuristic:
    # flag explicit basic colors on data marks — single-letter codes *and*
    # their full-name aliases on lines (which preserve the original string),
    # plus basic-color RGBA on patches (bars/areas store resolved RGBA).
    requirements["proper_colors"] = not _uses_basic_default_colors(fig)

    return requirements


def _style_applied(fig: Figure) -> bool:
    """Heuristic: did the author apply a non-default (dartwork) style?

    Inspects the figure's own text artists instead of the process-global
    ``plt.rcParams`` (which any later ``style.use`` / ``rcdefaults`` call
    mutates independently of *this* figure). matplotlib resolves the active
    ``font.size`` into each Text artist at creation, so a base-font-sized
    title / label / tick label that differs from matplotlib's hard default
    (10.0 pt) is figure-local evidence a preset was active.

    Returns ``False`` when nothing distinguishes the figure from a vanilla
    matplotlib build — a conservative default for an advisory score.
    """
    texts = list(fig.texts)
    for ax in fig.axes:
        texts.append(ax.xaxis.label)
        texts.append(ax.yaxis.label)
        texts.extend(ax.get_xticklabels())
        texts.extend(ax.get_yticklabels())
        legend = ax.get_legend()
        if legend is not None:
            texts.extend(legend.get_texts())
    for text in texts:
        try:
            size = float(text.get_fontsize())
        except (TypeError, ValueError):
            continue
        if abs(size - _MPL_DEFAULT_FONT_SIZE) > 1e-6:
            return True
    return False


def _is_default_color_string(color: object) -> bool:
    """True if ``color`` is a matplotlib basic-palette name/code string."""
    return (
        isinstance(color, str)
        and color.strip().lower() in _MPL_BASIC_COLOR_NAMES
    )


def _uses_basic_default_colors(fig: Figure) -> bool:
    """Detect explicit matplotlib basic colors on data marks."""
    for ax in fig.axes:
        for line in ax.lines:
            if _is_default_color_string(line.get_color()):
                return True
        for patch in ax.patches:
            try:
                rgba = mcolors.to_rgba(patch.get_facecolor())
            except (ValueError, TypeError):
                continue
            if rgba in _MPL_BASIC_COLOR_RGBA:
                return True
    return False


def generate_validation_report(fig: Figure) -> str:
    """Generate a comprehensive validation report for agents.

    Parameters
    ----------
    fig : Figure
        Figure to validate

    Returns
    -------
    str
        Formatted validation report
    """
    report = []
    report.append("=== DARTWORK-MPL VALIDATION REPORT ===\n")

    # Basic requirements
    requirements = check_agent_requirements(fig)
    report.append("BASIC REQUIREMENTS:")
    for req, passed in requirements.items():
        status = "✓" if passed else "✗"
        report.append(f"  {status} {req.replace('_', ' ').title()}")

    # Visual warnings
    warnings = validate_figure(fig, quiet=True)
    report.append(f"\nVISUAL WARNINGS: {len(warnings)}")

    if warnings:
        # Group by severity
        severe = [w for w in warnings if w.severity == Severity.WARNING]
        info = [w for w in warnings if w.severity == Severity.INFO]

        if severe:
            report.append(f"  ⚠️  {len(severe)} warnings")
            report.extend(
                f"    - {w.check_id}: {w.message}" for w in severe[:3]
            )

        if info:
            report.append(f"  💡 {len(info)} info messages")
            report.extend(f"    - {w.check_id}: {w.message}" for w in info[:2])

    # Overall score
    n_passed = sum(requirements.values())
    n_total = len(requirements)
    score = n_passed / n_total * 100 if n_total > 0 else 0

    report.append(
        f"\nOVERALL SCORE: {score:.0f}% ({n_passed}/{n_total} requirements met)"
    )

    # Recommendation
    if score == 100 and not warnings:
        report.append("STATUS: ✅ Excellent - Ready for production")
    elif score >= 80 and len(warnings) <= 2:
        report.append("STATUS: ⚠️  Good - Minor improvements recommended")
    else:
        report.append("STATUS: ❌ Needs work - Please review issues above")

    return "\n".join(report)
