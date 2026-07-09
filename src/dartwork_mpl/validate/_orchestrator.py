"""Orchestrator: runs every registered check and renders the stdout log."""

from __future__ import annotations

import sys
from functools import partial
from typing import TYPE_CHECKING

from .._helpers import get_renderer
from ._checks import registered_checks
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
        Supported IDs: ``OVERFLOW``, ``OVERLAP``, ``UNIT_DUP``,
        ``CROSS_AXES_OVERLAP``, ``LEGEND_OVERFLOW``, ``TICK_CROWD``,
        ``TICK_ROTATION``, ``TICK_DECIMAL``, ``EMPTY_AXES``,
        ``MARGIN_ASYMMETRY``, ``PIE_LABEL_OFFSET``, ``CLIPPED_TEXT``.
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

    # Checks self-register via ``@register_check`` in their own modules;
    # ``registered_checks()`` returns them in deterministic run order, so
    # the orchestrator no longer hand-mirrors a check→callable dict that
    # could silently drift out of sync with the check modules.
    selected = registered_checks()
    valid_ids = {check.check_id for check in selected}

    # Fail loud on unknown IDs: a typo (``"OVERFLW"``) or a renamed
    # check would otherwise silently run *zero* checks and report the
    # figure clean when it was never inspected.
    if checks is not None:
        unknown = set(checks) - valid_ids
        if unknown:
            raise ValueError(
                f"Unknown check IDs: {sorted(unknown)}. "
                f"Valid IDs: {sorted(valid_ids)}"
            )
        selected = [check for check in selected if check.check_id in checks]

    warnings: list[VisualWarning] = []
    errored: list[str] = []
    for check in selected:
        # Never crash the save pipeline, but don't silently swallow a
        # failed check either — a check that raises must not let the
        # figure be reported "clean" as if it had run and found nothing.
        # Every check is invoked uniformly as ``fn(fig, renderer)``.
        result = _run_check_safely(partial(check.fn, fig, renderer))
        if result is None:
            errored.append(check.check_id)
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
