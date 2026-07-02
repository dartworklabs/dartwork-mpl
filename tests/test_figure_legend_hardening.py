"""Hardening tests for figure-level legend handling.

Figure-level legends (``fig.legend(...)``) are a common multi-panel
idiom, yet two code paths that specifically handle them had zero test
coverage before this file:

* ``validate/_checks/legend.py`` lines 102-110 — the ``for legend in
  fig.legends`` loop that flags a *figure* legend running off the
  canvas. Every prior LEGEND_OVERFLOW test used ``ax.get_legend()``
  (axes legends), so the figure-legend branch never ran.
* ``layout.py`` lines 897-905 — ``tight_crop``'s loop that folds each
  visible ``fig.legends`` entry into the content bounding box. Without
  it a figure legend would be cropped off.

Both are exercised here so a future refactor cannot silently drop
figure-legend support.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

from dartwork_mpl.layout import tight_crop
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


class TestTightCropFigureLegend:
    """tight_crop must fold figure/axes legends into the content bbox."""

    @staticmethod
    def _small_central_axes():
        """A tiny plot in the middle of a large canvas (no legend)."""
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_axes((0.4, 0.4, 0.15, 0.15))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="s")
        return fig, ax, line

    def test_figure_legend_widens_crop(self) -> None:
        """A figure legend placed away from the axes must enlarge the crop.

        The comparison proves the ``fig.legends`` bbox is actually
        unioned into the content box (not merely that tight_crop runs).
        """
        fig0, _, _ = self._small_central_axes()
        w0, h0 = tight_crop(fig0, padding=0.0)
        plt.close(fig0)

        fig1, _, line = self._small_central_axes()
        # Corner legend sits far from the small central axes.
        fig1.legend(handles=[line], labels=["s"], loc="upper right")
        w1, h1 = tight_crop(fig1, padding=0.0)
        plt.close(fig1)

        assert (w1 > w0 + 1e-6) or (h1 > h0 + 1e-6), (
            "figure legend extent must be included in the crop"
        )

    def test_axes_legend_anchored_outside_included(self) -> None:
        """An axes legend anchored outside the axes must be cropped in.

        Exercises the axes-legend branch of tight_crop's bbox loop; the
        resulting figure must still be drawable (valid geometry).
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot([1, 2, 3], [1, 2, 3], label="s")
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
        w, h = tight_crop(fig)
        assert w > 0 and h > 0
        fig.canvas.draw()  # must not raise on the re-laid-out figure
        plt.close(fig)
