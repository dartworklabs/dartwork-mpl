"""Unit tests for tests/robustness/pixel_assertions.py.

These helpers operate on the rendered RGBA buffer of a Figure so the
robustness suite can verify *what was actually drawn* rather than
trusting matplotlib's artist-tree bookkeeping.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Rectangle

import dartwork_mpl as dm
from tests.robustness.pixel_assertions import (
    PixelAssertionError,
    assert_minimum_white_border,
    assert_no_clipped_text,
    assert_no_edge_overflow,
    figure_to_rgba,
)


class TestFigureToRgba:
    def test_returns_uint8_4channel(self) -> None:
        fig, ax = plt.subplots(figsize=(2, 2))
        ax.plot([1, 2, 3])
        arr = figure_to_rgba(fig)
        assert arr.dtype == np.uint8
        assert arr.ndim == 3
        assert arr.shape[2] == 4
        plt.close(fig)


class TestAssertNoEdgeOverflow:
    def test_clean_figure_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        ax.set_ylabel("Y")
        ax.set_xlabel("X")
        fig.subplots_adjust(left=0.20, right=0.95, bottom=0.20, top=0.92)
        # Should not raise.
        assert_no_edge_overflow(fig, side="left", min_white_px=4)
        plt.close(fig)

    def test_text_pushed_against_left_edge_fails(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        # Force the plot to start at x=0 of the canvas.
        fig.subplots_adjust(left=0.0, right=0.95, bottom=0.20, top=0.92)
        ax.set_ylabel("very long left label that will be cut")
        with pytest.raises(PixelAssertionError, match="left"):
            assert_no_edge_overflow(fig, side="left", min_white_px=4)
        plt.close(fig)


class TestAssertMinimumWhiteBorder:
    """All four margins are checked against the current rendered Figure."""

    def test_default_white_border_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.plot([1, 2, 3])
        # Default subplots_adjust leaves > 8 px white border.
        assert_minimum_white_border(fig, min_px=8)
        plt.close(fig)

    @pytest.mark.parametrize("side", ["left", "right", "top", "bottom"])
    def test_new_edge_content_is_detected(self, side: str) -> None:
        """A new colored edge must fail even after the same canvas passed."""
        fig = plt.figure(figsize=dm.figsize("5cm", "square"))
        fig.patch.set_facecolor("white")
        assert_minimum_white_border(fig, min_px=8)
        rectangles = {
            "left": (0.0, 0.4, 0.05, 0.2),
            "right": (0.95, 0.4, 0.05, 0.2),
            "top": (0.4, 0.95, 0.2, 0.05),
            "bottom": (0.4, 0.0, 0.2, 0.05),
        }
        x, y, width, height = rectangles[side]
        fig.add_artist(
            Rectangle(
                (x, y), width, height, transform=fig.transFigure, color="red"
            )
        )

        with pytest.raises(PixelAssertionError, match=side):
            assert_minimum_white_border(fig, min_px=8)
        plt.close(fig)


class TestAssertNoClippedText:
    def test_text_inside_axes_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        ax.text(0.5, 0.5, "OK", transform=ax.transAxes)
        # Should not raise.
        assert_no_clipped_text(fig)
        plt.close(fig)

    def test_text_at_negative_axes_fraction_fails(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        # Place text at y = -0.4 axes-fraction; tight figure makes it spill.
        ax.text(0.5, -0.4, "spill", transform=ax.transAxes, fontsize=18)
        fig.subplots_adjust(bottom=0.05)
        with pytest.raises(PixelAssertionError):
            assert_no_clipped_text(fig)
        plt.close(fig)
