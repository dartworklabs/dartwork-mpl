"""Enhanced validation with auto-fix suggestions for agents.

Extends the base validation with actionable fixes that agents can apply.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib.colors as mcolors
from matplotlib.figure import Figure

from .helpers.quality import _MIN_RECOMMENDED_DPI
from .validate import Severity, VisualWarning, validate_figure

# Auto-apply path of ``validate_with_fixes`` calls ``dm.simple_layout``
# opportunistically. simple_layout can raise from any of these branches:
#   - RuntimeError: matplotlib renderer / canvas state errors
#   - ValueError: BBox arithmetic, dm.figsize unit parsing
#   - AttributeError: an artist subclass missing get_window_extent
#   - TypeError: an invalid kwarg slipping through callers
# A bare ``Exception`` catch was previously used (with a BLE001 noqa
# acknowledging it was too broad). It hid legitimate regressions in
# simple_layout because *every* exception was treated as "fix failed,
# carry on" instead of distinguishing "skippable" from "investigate
# now."
_LAYOUT_FIX_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    AttributeError,
    TypeError,
)

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


# ───────────────────────────────────────────────────────
# Per-check fix-handler registry
# ───────────────────────────────────────────────────────
#
# Each handler takes the VisualWarning and returns a list of code-snippet
# strings the agent (or human reader) can apply. Handlers are pure —
# no side-effects, no figure mutation. Registering a new check elsewhere
# in the codebase just needs another ``@register_fix("MY_CHECK_ID")``
# decorator below; no edits to ``get_fix_suggestions``, no edits to
# ``check_agent_requirements`` aside from optionally tracking the new
# check in its severity grouping.
#
# This mirrors the pattern ``lint.py`` already uses with its ``Rule``
# objects: one handler per check, all discoverable via the dispatcher.

FixHandler = Callable[[VisualWarning], list[str]]

_FIX_HANDLERS: dict[str, FixHandler] = {}


def register_fix(check_id: str) -> Callable[[FixHandler], FixHandler]:
    """Decorator: register a fix-suggestion handler under ``check_id``.

    The handler runs only when ``get_fix_suggestions(warning)`` is called
    with a warning whose ``check_id`` matches. Multiple registrations
    under the same ID raise — the dispatch table must stay
    deterministic.
    """

    def deco(fn: FixHandler) -> FixHandler:
        if check_id in _FIX_HANDLERS:
            raise RuntimeError(
                f"Duplicate fix handler registered for {check_id!r}"
            )
        _FIX_HANDLERS[check_id] = fn
        return fn

    return deco


@register_fix("OVERFLOW")
def _fix_overflow(warning: VisualWarning) -> list[str]:
    suggestions: list[str] = []
    side = warning.detail.get("side", "")
    px = warning.detail.get("px", 0)
    # Clamp the suggested fractions into a valid band: matplotlib
    # requires left/bottom < right/top, all within [0, 1]. Unclamped,
    # a large overflow (px ≈ 90 on a small figure) produced
    # copy-paste suggestions like ``subplots_adjust(left=1.05)`` that
    # raise ValueError when applied.
    grow = min(0.45, 0.15 + px / 100)
    shrink_right = max(0.55, 0.95 - px / 100)
    shrink_top = max(0.55, 0.9 - px / 100)
    if side == "left":
        suggestions.append(
            f"# Increase left margin\nfig.subplots_adjust(left={grow:.2f})"
        )
        suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
    elif side == "right":
        suggestions.append(
            "# Increase right margin\n"
            f"fig.subplots_adjust(right={shrink_right:.2f})"
        )
        suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
    elif side == "bottom":
        suggestions.append(
            f"# Increase bottom margin\nfig.subplots_adjust(bottom={grow:.2f})"
        )
        suggestions.append(
            "# Rotate x-tick labels\nax.tick_params(axis='x', rotation=45)"
        )
    elif side == "top":
        suggestions.append(
            f"# Increase top margin\nfig.subplots_adjust(top={shrink_top:.2f})"
        )
    return suggestions


@register_fix("OVERLAP")
def _fix_overlap(_warning: VisualWarning) -> list[str]:
    return [
        "# Adjust text positions\nax.text(..., ha='left')  # Change alignment",
        "# Use simple_layout\ndm.simple_layout(fig)",
        "# Reduce font size\nax.legend(fontsize=dm.fs(-1))",
    ]


@register_fix("LEGEND_OVERFLOW")
def _fix_legend_overflow(_warning: VisualWarning) -> list[str]:
    return [
        "# Move legend outside\nax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')",
        "# Reduce legend columns\nax.legend(ncol=1)",
        "# Reduce legend font\nax.legend(fontsize=dm.fs(-2))",
    ]


@register_fix("TICK_CROWD")
def _fix_tick_crowd(warning: VisualWarning) -> list[str]:
    suggestions: list[str] = []
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
    return suggestions


@register_fix("EMPTY_AXES")
def _fix_empty_axes(_warning: VisualWarning) -> list[str]:
    return [
        "# Remove empty axes\nax.remove()",
        "# Or hide it\nax.set_visible(False)",
    ]


@register_fix("MARGIN_ASYMMETRY")
def _fix_margin_asymmetry(warning: VisualWarning) -> list[str]:
    side = warning.detail.get("side", "")
    if side in ("left", "right"):
        return ["# Center horizontally\ndm.simple_layout(fig)"]
    return ["# Center vertically\ndm.simple_layout(fig)"]


@register_fix("PIE_LABEL_OFFSET")
def _fix_pie_label_offset(warning: VisualWarning) -> list[str]:
    ideal_r = warning.detail.get("ideal_r", 0.7)
    return [f"# Adjust label position\nax.pie(..., pctdistance={ideal_r:.2f})"]


@register_fix("CLIPPED_TEXT")
def _fix_clipped_text(_warning: VisualWarning) -> list[str]:
    return [
        "# Run the simple_layout pass\ndm.simple_layout(fig)",
        "# Or rotate the offending label\n"
        "dm.rotate_tick_labels(ax, axis='x', rotation=45)",
        "# Or shrink the font\n"
        "ax.tick_params(axis='both', labelsize=dm.fs(-2))",
    ]


def get_fix_suggestions(warning: VisualWarning) -> list[str]:
    """Generate fix suggestions for a visual warning.

    Looks up ``warning.check_id`` in the handler registry above and
    delegates to the matching handler. Unknown check IDs return ``[]``
    so callers don't have to special-case them.

    Parameters
    ----------
    warning : VisualWarning
        The warning to generate fixes for

    Returns
    -------
    list[str]
        List of suggested fixes (code snippets). Empty if no handler is
        registered for ``warning.check_id``.
    """
    handler = _FIX_HANDLERS.get(warning.check_id)
    return handler(warning) if handler is not None else []


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
        except _LAYOUT_FIX_ERRORS as e:
            # Auto-apply is opportunistic — known layout failure modes
            # (simple_layout regressions, backend errors, custom artist
            # exceptions) report a failed fix and continue rather than
            # aborting the whole validate_with_fixes run. Truly unexpected
            # errors (e.g. KeyboardInterrupt, MemoryError) still escape
            # so the user notices them.
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
