"""Tests for the shared figure-level artist extent iterator.

``_figure_geometry.iter_figure_level_extents`` is the one walk the layout's
edge reservations and the ``OVERFLOW`` check share over ``fig.suptitle`` /
``fig.text`` / ``fig.legend``, with one guard triplet. These tests pin the guard and the
rule that a blank (whitespace-only) figure title reserves nothing.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

from dartwork_mpl._figure_geometry import (
    get_renderer,
    iter_figure_level_extents,
)

matplotlib.use("Agg")  # Non-interactive backend for testing.


def _extents(fig, **kwargs):
    fig.canvas.draw()
    return list(iter_figure_level_extents(fig, get_renderer(fig), **kwargs))


class TestIterFigureLevelExtents:
    """Which figure-level artists (suptitle, figtext, legends) count as layout extents,
    and that blank or invisible ones are skipped.
    """

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
