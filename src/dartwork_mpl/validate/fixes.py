"""Fix suggestions for visual-validation warnings and the auto-apply shell.

Part of the validate slice; re-exported under the public path
:mod:`dartwork_mpl.validate_fixes`. Surface: ``get_fix_suggestions``,
``validate_with_fixes``. Each check's fix handler lives next to the check in
``_checks/<check>.py`` and registers in ``_checks/_registry.py``.
"""

from __future__ import annotations

from matplotlib.figure import Figure

from ..layout import simple_layout
from ._checks._registry import _FIX_HANDLERS
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
