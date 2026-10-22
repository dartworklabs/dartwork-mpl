"""Agent coding-requirement checks and the agent validation report.

A quality check, not a visual-validation check: it scores DPI, style,
labels, data and colour use. Part of the validate slice; re-exported under
the public path :mod:`dartwork_mpl.validate_fixes`. Surface:
``check_agent_requirements``, ``generate_validation_report``.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
from matplotlib.figure import Figure

from ..helpers.quality import _MIN_RECOMMENDED_DPI
from ._orchestrator import validate_figure
from ._types import Severity

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

    # Check DPI — threshold comes from the single source in
    # helpers.quality so the two checks can never drift apart again.
    requirements["high_dpi"] = fig.dpi >= _MIN_RECOMMENDED_DPI

    # Check if a (dartwork) style preset was applied — figure-local, not
    # the process-global rcParams (which any later style.use / rcdefaults
    # call mutates independently of *this* figure).
    requirements["style_applied"] = _style_applied(fig)

    # Check for axis labels
    has_labels = True
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        # Axes with no meaningful x/y-label vocabulary are exempt:
        # pie/donut (wedge patches — same detection as pie_label.py),
        # non-rectilinear projections (polar, 3D), and axes whose axis
        # frame is turned off entirely. Requiring labels there produced
        # false failures that dragged the advisory OVERALL SCORE down
        # for perfectly correct charts.
        if not ax.axison:
            continue
        if ax.name != "rectilinear":
            continue
        if any(hasattr(p, "theta1") for p in ax.patches):
            continue
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
    """Detect explicit matplotlib basic colors on data marks.

    Covers lines (original color string preserved), patches
    (bars/areas, resolved RGBA), and collections (scatter/hexbin/
    LineCollection marks, RGBA arrays) — the latter were previously
    skipped, so ``ax.scatter(..., color="red")`` passed the
    ``proper_colors`` requirement it exists to catch.
    """
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
        for coll in ax.collections:
            for getter in (coll.get_facecolor, coll.get_edgecolor):
                try:
                    # ``to_rgba_array`` normalizes every shape a
                    # collection can return (single RGBA, (N, 4) array,
                    # empty) into an (N, 4) float array.
                    rgba_rows = mcolors.to_rgba_array(getter())
                except (ValueError, TypeError):
                    continue
                for row in rgba_rows:
                    if tuple(float(c) for c in row) in _MPL_BASIC_COLOR_RGBA:
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
