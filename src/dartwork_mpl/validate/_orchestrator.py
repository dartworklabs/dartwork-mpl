"""Orchestrator: runs every check and renders the stdout log."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .._helpers import get_renderer
from ._checks import (
    check_clipped_text,
    check_cross_axes_overlap,
    check_empty_axes,
    check_legend_overflow,
    check_margin_asymmetry,
    check_overflow,
    check_overlap,
    check_pie_label_offset,
    check_tick_crowding,
)
from ._types import BBOX_ERRORS, VisualWarning

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.figure import Figure

__all__ = ["validate_figure"]


def _run_check_safely(
    check_fn: Callable[[], list[VisualWarning]],
) -> list[VisualWarning] | None:
    """Run one check, returning its warnings or ``None`` if it errored.

    Isolating the ``try`` here (rather than inside the orchestration
    loop) keeps a failing check from crashing the save pipeline while
    still letting the caller distinguish "ran clean" from "could not
    run" — the latter must never be reported as a clean figure.
    """
    try:
        return check_fn()
    except BBOX_ERRORS:
        return None


def validate_figure(
    fig: Figure, *, checks: tuple[str, ...] | None = None, quiet: bool = False
) -> list[VisualWarning]:
    """Run comprehensive visual validation on a Matplotlib figure.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to inspect for visual defects.
    checks : tuple[str, ...] | None, optional
        Check IDs to run. If None, all registered checks are executed.
        Supported IDs: ``OVERFLOW``, ``OVERLAP``,
        ``CROSS_AXES_OVERLAP``, ``LEGEND_OVERFLOW``, ``TICK_CROWD``,
        ``EMPTY_AXES``, ``MARGIN_ASYMMETRY``, ``PIE_LABEL_OFFSET``,
        ``CLIPPED_TEXT``.
    quiet : bool, optional
        If True, suppresses stdout output. Default is False.

    Returns
    -------
    list[VisualWarning]
        List of detected visual issues.
    """
    # Render once so all bounding boxes are computed.
    fig.canvas.draw()
    renderer = get_renderer(fig)

    all_checks: dict[str, Any] = {
        "OVERFLOW": lambda: check_overflow(fig, renderer),
        "OVERLAP": lambda: check_overlap(fig, renderer),
        "CROSS_AXES_OVERLAP": lambda: check_cross_axes_overlap(fig, renderer),
        "LEGEND_OVERFLOW": lambda: check_legend_overflow(fig, renderer),
        "TICK_CROWD": lambda: check_tick_crowding(fig, renderer),
        "EMPTY_AXES": lambda: check_empty_axes(fig),
        "MARGIN_ASYMMETRY": lambda: check_margin_asymmetry(fig, renderer),
        "PIE_LABEL_OFFSET": lambda: check_pie_label_offset(
            fig, _renderer=renderer
        ),
        "CLIPPED_TEXT": lambda: check_clipped_text(fig, renderer),
    }

    # Fail loud on unknown IDs: a typo (``"OVERFLW"``) or a renamed
    # check would otherwise silently run *zero* checks and report the
    # figure clean when it was never inspected.
    if checks is not None:
        unknown = set(checks) - all_checks.keys()
        if unknown:
            raise ValueError(
                f"Unknown check IDs: {sorted(unknown)}. "
                f"Valid IDs: {sorted(all_checks)}"
            )

    selected = (
        {k: v for k, v in all_checks.items() if k in checks}
        if checks is not None
        else all_checks
    )

    warnings: list[VisualWarning] = []
    errored: list[str] = []
    for check_id, check_fn in selected.items():
        # Never crash the save pipeline, but don't silently swallow a
        # failed check either — a check that raises must not let the
        # figure be reported "clean" as if it had run and found nothing.
        result = _run_check_safely(check_fn)
        if result is None:
            errored.append(check_id)
        else:
            warnings.extend(result)

    # Structured stdout output for agent consumption.
    if not quiet:
        if warnings:
            for w in warnings:
                print(str(w), file=sys.stdout, flush=True)
        elif errored:
            print(
                "[VISUAL] ⚠️ No issues found, but "
                f"{len(errored)} check(s) could not run "
                f"({', '.join(sorted(errored))}); result is incomplete.",
                file=sys.stdout,
                flush=True,
            )
        else:
            print(
                "[VISUAL] ✅ No visual issues detected.",
                file=sys.stdout,
                flush=True,
            )

    return warnings
