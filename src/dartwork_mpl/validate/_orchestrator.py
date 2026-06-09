"""Orchestrator: runs every check and renders the stdout log."""

from __future__ import annotations

import contextlib
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
    from matplotlib.figure import Figure

__all__ = ["validate_figure"]


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

    selected = (
        {k: v for k, v in all_checks.items() if k in checks}
        if checks is not None
        else all_checks
    )

    warnings: list[VisualWarning] = []
    for check_fn in selected.values():
        # Never crash the save pipeline.
        with contextlib.suppress(*BBOX_ERRORS):
            warnings.extend(check_fn())

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
