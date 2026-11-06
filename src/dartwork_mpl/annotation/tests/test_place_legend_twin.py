"""``place_legend`` on a twin pair keeps the legend's details (spec call 7).

The rebuilt twin legend carries the existing legend's title, ``handler_map`` and
the other settings the public ``Legend`` API exposes; a legend whose handles
cannot be rebuilt faithfully (tuple handles, custom labels) is left untouched.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.legend_handler import HandlerLine2D, HandlerPatch
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

import dartwork_mpl as dm
from dartwork_mpl.annotation import place_legend


class _Fat(HandlerLine2D):
    """A custom handler, to tell it from the default."""


def _twin_pair():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    x = np.arange(1, 7)
    ax.bar(x, 10 + x, label="Sales")
    twin = ax.twinx()
    twin.plot(x, 5 + x / 2, color="k", label="Margin")
    return fig, ax, twin


def _merged(ax, twin):
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = twin.get_legend_handles_labels()
    return h1 + h2, l1 + l2


class TestKeepsDetails:
    """The rebuilt legend repeats the old legend's readable settings."""

    def test_rebuild_on_top_twin_keeps_title_and_handler_map(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            handles, labels = _merged(ax, twin)
            ax.legend(
                handles,
                labels,
                title="Series",
                handler_map={Line2D: _Fat()},
                frameon=False,
                alignment="left",
                fontsize=7,
                title_fontsize=9,
            )
            legend = place_legend(ax)
            assert legend is not None
            assert legend.get_title().get_text() == "Series"
            assert legend.get_title().get_fontsize() == 9
            assert isinstance(legend.get_legend_handler_map()[Line2D], _Fat)
            assert not legend.get_frame_on()
            assert legend.get_alignment() == "left"
            assert {t.get_fontsize() for t in legend.get_texts()} == {7}
            assert [t.get_text() for t in legend.get_texts()] == [
                "Sales",
                "Margin",
            ]
            assert twin.get_legend() is legend
            assert ax.get_legend() is None
        finally:
            plt.close(fig)

    def test_title_survives_when_the_legend_sits_on_the_other_twin(
        self,
    ) -> None:
        fig, ax, twin = _twin_pair()
        try:
            twin.legend(title="Per axis")
            legend = place_legend(ax)
            assert legend is not None
            assert legend.get_title().get_text() == "Per axis"
        finally:
            plt.close(fig)

    def test_caller_keywords_win_over_the_kept_settings(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend(*_merged(ax, twin), title="Old", frameon=False)
            legend = place_legend(ax, title="New", frameon=True)
            assert legend.get_title().get_text() == "New"
            assert legend.get_frame_on()
        finally:
            plt.close(fig)

    def test_default_settings_are_not_pinned(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            twin.legend()
            legend = place_legend(ax)
            assert legend.get_title().get_text() == ""
            assert legend.get_frame_on() == plt.rcParams["legend.frameon"]
            assert legend.get_alignment() == "center"
        finally:
            plt.close(fig)

    def test_top_twin_is_chosen_by_zorder(self) -> None:
        """The ``set_zorder`` idiom puts the legend on ``ax``, the line axes."""
        fig, ax, twin = _twin_pair()
        try:
            ax.set_zorder(twin.get_zorder() + 1)
            ax.patch.set_visible(False)
            legend = place_legend(twin)
            assert ax.get_legend() is legend
            assert twin.get_legend() is None
        finally:
            plt.close(fig)


class TestLeavesUnrebuildableLegends:
    """An explicit legend that cannot be rebuilt faithfully is left alone."""

    def test_tuple_handles_legend_left_untouched(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            line = Line2D([], [], color="k")
            patch = Rectangle((0, 0), 1, 1, color="C0")
            kept = ax.legend(
                [(patch, line)],
                ["Sales + Margin"],
                title="Pair",
                loc="upper left",
            )
            result = place_legend(ax)
            assert result is kept
            assert ax.get_legend() is kept
            assert [t.get_text() for t in kept.get_texts()] == [
                "Sales + Margin"
            ]
            assert kept.get_title().get_text() == "Pair"
        finally:
            plt.close(fig)

    def test_tuple_legend_on_the_lower_twin_is_not_removed(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            kept = ax.legend(
                [(Rectangle((0, 0), 1, 1), Line2D([], []))], ["Both"]
            )
            place_legend(twin)
            assert ax.get_legend() is kept
        finally:
            plt.close(fig)

    def test_custom_handler_for_a_foreign_type_is_kept_not_dropped(
        self,
    ) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend(
                *_merged(ax, twin), handler_map={Rectangle: HandlerPatch()}
            )
            legend = place_legend(ax)
            assert legend.get_legend_handler_map()[Rectangle] is not None
            assert len(legend.get_texts()) == 2
        finally:
            plt.close(fig)


def test_single_axes_legend_keeps_its_title() -> None:
    """The kept settings apply to a lone Axes too."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    try:
        ax.plot([1, 2], label="a")
        ax.legend(title="T")
        legend = place_legend(ax)
        assert legend.get_title().get_text() == "T"
    finally:
        plt.close(fig)
