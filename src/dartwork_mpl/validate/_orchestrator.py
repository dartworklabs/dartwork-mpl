"""Orchestrator: runs every registered check and renders the stdout log."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from .._figure_geometry import get_renderer
from ._checks import RegisteredCheck, registered_checks
from ._checks._detail import wire
from ._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["validate_figure"]


@dataclass(frozen=True)
class CheckCompleted:
    """A check ran to the end; ``warnings`` may be empty (a clean result)."""

    warnings: list[VisualWarning]


@dataclass(frozen=True)
class CheckFailed:
    """A tolerated bbox error stopped the check; the figure is not proven clean."""

    check_id: str


CheckOutcome: TypeAlias = CheckCompleted | CheckFailed


class CheckFailedDetail(TypedDict):
    """Wire detail of a ``CHECK_FAILED`` warning: the check that could not run."""

    check_id: str


def _run_check_safely(
    check: RegisteredCheck, fig: Figure, renderer: RendererBase
) -> CheckOutcome:
    """Run one check as ``fn(fig, renderer)``; a bbox error is ``CheckFailed``.

    Isolating the ``try`` here (rather than inside the orchestration
    loop) keeps a failing check from crashing the save pipeline while
    still letting the caller distinguish "ran clean" from "could not
    run" — the latter must never be reported as a clean figure. Any
    other exception is a defect and propagates.
    """
    try:
        return CheckCompleted(check.fn(fig, renderer))
    except BBOX_ERRORS:
        return CheckFailed(check.check_id)


def _outcome_warnings(outcome: CheckOutcome) -> list[VisualWarning]:
    """The public warnings for one outcome; a failure becomes ``CHECK_FAILED``."""
    match outcome:
        case CheckCompleted(warnings):
            return warnings
        case CheckFailed(check_id):
            return [
                VisualWarning(
                    Severity.WARNING,
                    "CHECK_FAILED",
                    f"Check {check_id} could not run; validation is incomplete.",
                    wire(CheckFailedDetail(check_id=check_id)),
                )
            ]


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
        ``TICK_ROTATION``, ``TICK_DECIMAL``, ``VALUE_LABEL_DECIMAL``,
        ``EMPTY_AXES``, ``MARGIN_ASYMMETRY``, ``PIE_LABEL_OFFSET``,
        ``CLIPPED_TEXT``.
    quiet : bool, optional
        If True, suppresses stdout output. Default is False.

    Returns
    -------
    list[VisualWarning]
        Detected issues in registry order, including ``CHECK_FAILED`` warnings
        with the original ID in ``detail["check_id"]`` when a tolerated bbox
        error prevents a check from completing. Quiet mode only changes output.
        Unexpected check exceptions propagate to the caller.
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
    for check in selected:
        # Never crash the save pipeline, but don't silently swallow a
        # failed check either — a check that raises must not let the
        # figure be reported "clean" as if it had run and found nothing.
        # Every check is invoked uniformly as ``fn(fig, renderer)``.
        warnings.extend(
            _outcome_warnings(_run_check_safely(check, fig, renderer))
        )

    # Structured stdout output for agent consumption.
    if not quiet:
        if warnings:
            for w in warnings:
                print(str(w), file=sys.stdout, flush=True)
        else:
            print(
                "[VISUAL] ✅ No visual issues detected.",
                file=sys.stdout,
                flush=True,
            )

    return warnings
