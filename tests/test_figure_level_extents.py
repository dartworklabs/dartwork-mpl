"""Tests for the shared figure-level artist extent iterator.

``_helpers.iter_figure_level_extents`` is the single source three sites
now share — ``layout._figure_artist_reservations``, ``layout.tight_crop``,
and the ``OVERFLOW`` check — for walking ``fig.suptitle`` / ``fig.text`` /
``fig.legend`` with one guard triplet. These tests pin the guard and the
one intentional consistency fix the consolidation surfaced: a blank
(whitespace-only) figure title no longer reserves crop space.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

from dartwork_mpl._helpers import get_renderer, iter_figure_level_extents
from dartwork_mpl.layout import tight_crop

matplotlib.use("Agg")  # Non-interactive backend for testing.


def _extents(fig, **kwargs):
    fig.canvas.draw()
    return list(iter_figure_level_extents(fig, get_renderer(fig), **kwargs))


class TestIterFigureLevelExtents:
    def test_yields_suptitle_figtext_and_legend(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="s")
        fig.suptitle("Title")
        fig.text(0.5, 0.01, "footnote")
        fig.legend(handles=[line], labels=["s"], loc="upper right")
        assert len(_extents(fig)) == 3  # suptitle + figtext + legend
        plt.close(fig)

    def test_skips_whitespace_only_text(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        fig.suptitle("   ")  # blank -> reserves nothing
        assert _extents(fig) == []
        plt.close(fig)

    def test_skips_invisible_artist(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        fig.suptitle("Title").set_visible(False)
        assert _extents(fig) == []
        plt.close(fig)

    def test_legends_flag(self) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        (line,) = ax.plot([1, 2, 3], [1, 2, 3], label="s")
        fig.legend(handles=[line], labels=["s"], loc="upper right")
        assert len(_extents(fig, legends=True)) == 1
        assert _extents(fig, legends=False) == []
        plt.close(fig)

    def test_supxlabel_counted_once(self) -> None:
        # matplotlib stores supxlabel in both fig._supxlabel and
        # fig.texts; the iterator must dedup and yield it exactly once.
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        fig.supxlabel("shared x")
        assert len(_extents(fig)) == 1
        plt.close(fig)


class TestConsolidatedGuardConsistency:
    """The consolidation unified a latent guard divergence: ``tight_crop``
    used to reserve space for a blank suptitle while the layout engine and
    OVERFLOW already skipped it."""

    @staticmethod
    def _crop_with_title(title):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3])
        if title is not None:
            fig.suptitle(title)
        size = tight_crop(fig)
        plt.close(fig)
        return tuple(round(v, 3) for v in size)

    def test_whitespace_title_crops_like_no_title(self) -> None:
        no_title = self._crop_with_title(None)
        whitespace = self._crop_with_title("   ")
        assert whitespace == no_title

    def test_real_title_still_reserves_space(self) -> None:
        no_title = self._crop_with_title(None)
        real = self._crop_with_title("A Real Title")
        # A non-blank title must still enlarge the crop (guards only drop
        # blank/degenerate artists, never real content).
        assert real[1] > no_title[1]
