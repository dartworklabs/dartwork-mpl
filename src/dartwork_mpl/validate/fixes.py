"""Fix suggestions for visual-validation warnings and the auto-apply shell.

Part of the validate slice; re-exported under the public path
:mod:`dartwork_mpl.validate_fixes`. Surface: ``FixHandler``, ``register_fix``,
``get_fix_suggestions``, ``validate_with_fixes``.
"""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.figure import Figure

from ..layout import simple_layout
from ._orchestrator import validate_figure
from ._types import Severity, VisualWarning

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


@register_fix("UNIT_DUP")
def _fix_unit_dup(warning: VisualWarning) -> list[str]:
    axis = warning.detail.get("axis", "y")
    return [
        "# Keep the unit in the axis label only\n"
        f"ax.{axis}axis.set_major_formatter(mticker.PercentFormatter(symbol=''))",
        "# Or use a bare numeric formatter\n"
        f"ax.{axis}axis.set_major_formatter(mticker.StrMethodFormatter('{{x:g}}'))",
    ]


@register_fix("TICK_ROTATION")
def _fix_tick_rotation(warning: VisualWarning) -> list[str]:
    rotation = warning.detail.get("recommended_rotation", 45)
    return [
        "# Adjust x tick label rotation\n"
        f"dm.rotate_tick_labels(ax, axis='x', rotation={rotation})",
        "# Or reduce tick density\n"
        "ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=6))",
    ]


@register_fix("TICK_DECIMAL")
def _fix_tick_decimal(warning: VisualWarning) -> list[str]:
    axis = warning.detail.get("axis", "y")
    decimals = int(warning.detail.get("recommended_decimals", 0))
    return [
        "# Match tick precision to the tick step\n"
        f"ax.{axis}axis.set_major_formatter(mticker.StrMethodFormatter('{{x:.{decimals}f}}'))",
        "# Or let matplotlib choose compact numeric labels\n"
        f"ax.{axis}axis.set_major_formatter(mticker.ScalarFormatter())",
    ]


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
            simple_layout(fig)
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
