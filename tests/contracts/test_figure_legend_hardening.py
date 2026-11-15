"""Hardening tests for figure-level legend handling.

Figure-level legends (``fig.legend(...)``) are a common multi-panel
idiom; ``validate/_checks/legend.py``'s ``for legend in fig.legends`` loop
flags one running off the canvas. Every other LEGEND_OVERFLOW test uses
``ax.get_legend()``, so the figure-legend branch is exercised here.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

from dartwork_mpl.validate import validate_figure

matplotlib.use("Agg")  # Non-interactive backend for testing.


def _legend_overflow_warnings(fig, *, figure_level_only=False):
    """Run only the LEGEND_OVERFLOW check and return its warnings.

    ``figure_level_only`` keeps just the figure-legend hits (``fig.legend``
    warnings carry ``axes_index is None``; axes-legend hits carry an int).
    """
    warnings = validate_figure(fig, checks=("LEGEND_OVERFLOW",), quiet=True)
    hits = [w for w in warnings if w.check_id == "LEGEND_OVERFLOW"]
    if figure_level_only:
        hits = [w for w in hits if w.detail.get("axes_index") is None]
    return hits


class TestFigureLegendOverflow:
    """LEGEND_OVERFLOW must inspect ``fig.legend`` legends too."""

    def test_figure_legend_offcanvas_is_flagged(self) -> None:
        """A figure legend anchored well past the canvas edge must fire.

        ``ax.get_legend()`` never returns figure-level legends, so this
        can only be caught by the dedicated ``fig.legends`` loop.
        """
        fig, ax = plt.subplots(figsize=(4, 3))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="series")
        # bbox_to_anchor is in figure fraction for fig.legend; 1.4 puts
        # the legend's left edge at 140% of the figure width — entirely
        # off the right side of the canvas.
        fig.legend(
            handles=[line],
            labels=["series"],
            loc="center left",
            bbox_to_anchor=(1.4, 0.5),
        )
        hits = _legend_overflow_warnings(fig, figure_level_only=True)
        assert hits, "off-canvas figure legend must be flagged"
        assert hits[0].detail["overflow_px"] > 2.0
        plt.close(fig)

    def test_figure_legend_inside_canvas_not_flagged(self) -> None:
        """A figure legend that stays on the canvas must NOT fire."""
        fig, ax = plt.subplots(figsize=(6, 4))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="series")
        fig.legend(handles=[line], labels=["series"], loc="upper right")
        hits = _legend_overflow_warnings(fig, figure_level_only=True)
        assert not hits, "on-canvas figure legend is a false positive"
        plt.close(fig)

    def test_invisible_figure_legend_skipped(self) -> None:
        """An invisible figure legend must be skipped even off-canvas.

        Covers the ``if not legend.get_visible(): continue`` guard.
        """
        fig, ax = plt.subplots(figsize=(4, 3))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="series")
        legend = fig.legend(
            handles=[line],
            labels=["series"],
            loc="center left",
            bbox_to_anchor=(1.4, 0.5),
        )
        legend.set_visible(False)
        hits = _legend_overflow_warnings(fig, figure_level_only=True)
        assert not hits, "invisible figure legend must not be flagged"
        plt.close(fig)
