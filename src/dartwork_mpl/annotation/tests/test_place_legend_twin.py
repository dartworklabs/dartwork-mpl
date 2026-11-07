"""``place_legend`` on a twin pair keeps the legend's details (spec call 7).

The rebuilt twin legend carries the existing legend's title, ``handler_map`` and
the other settings the public ``Legend`` API exposes; a legend whose handles
cannot be rebuilt faithfully (tuple handles, custom labels) is left untouched.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colors import to_rgba
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
            assert isinstance(
                legend.get_legend_handler_map()[Rectangle], HandlerPatch
            )
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


def _artist_count(legend) -> int:
    """Artists drawn in the legend's handle boxes (a tuple entry has several)."""
    from matplotlib.offsetbox import DrawingArea

    def walk(node) -> int:
        total = 0
        for child in node.get_children():
            if isinstance(child, DrawingArea):
                total += len(child.get_children())
            elif child.__class__.__module__ == "matplotlib.offsetbox":
                total += walk(child)
        return total

    return walk(legend.get_children()[0])


class _Obj:
    """A handle matplotlib has no handler for."""


class _ObjHandler:
    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        patch = Rectangle((0, 0), handlebox.width, handlebox.height)
        handlebox.add_artist(patch)
        return patch


def _unlabeled_pair():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    twin = ax.twinx()
    (a,) = ax.plot([1, 2])
    (b,) = twin.plot([2, 1])
    return fig, ax, twin, a, b


class TestExplicitLegendWins:
    """Structure, not labels, decides whether a legend can be rebuilt."""

    @pytest.mark.parametrize("target", ["host", "twin"])
    def test_unlabeled_tuple_on_a_twin_pair_untouched(self, target) -> None:
        fig, ax, twin, a, b = _unlabeled_pair()
        try:
            kept = ax.legend([(a, b)], ["Both"])
            before = _artist_count(kept)
            assert place_legend(ax if target == "host" else twin) is kept
            assert ax.get_legend() is kept
            assert twin.get_legend() is None
            assert _artist_count(kept) == before == 2
        finally:
            plt.close(fig)

    def test_unlabeled_tuple_on_a_lone_axes_untouched(self) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        try:
            (a,) = ax.plot([1, 2])
            (b,) = ax.plot([2, 1])
            kept = ax.legend([(a, b)], ["Both"])
            assert place_legend(ax) is kept
            assert _artist_count(kept) == 2
        finally:
            plt.close(fig)

    def test_custom_object_handler_untouched(self) -> None:
        fig, ax, twin, a, b = _unlabeled_pair()
        try:
            kept = ax.legend(
                [_Obj()], ["Custom"], handler_map={_Obj: _ObjHandler()}
            )
            assert place_legend(ax) is kept
            assert [t.get_text() for t in kept.get_texts()] == ["Custom"]
            assert _artist_count(kept) == 1
        finally:
            plt.close(fig)

    def test_tuple_whose_label_equals_an_artist_label_untouched(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            (extra,) = ax.plot([1, 2])
            sales = ax.containers[0]
            kept = ax.legend([(sales, extra)], ["Sales"])
            assert place_legend(ax) is kept
            assert _artist_count(kept) > 1
            assert twin.get_legend() is None
        finally:
            plt.close(fig)

    def test_tuple_over_labeled_artists_with_its_own_label_untouched(
        self,
    ) -> None:
        fig, ax, twin = _twin_pair()
        try:
            line = twin.get_lines()[0]
            kept = ax.legend([(ax.containers[0], line)], ["Temp"])
            assert place_legend(ax) is kept
            assert [t.get_text() for t in kept.get_texts()] == ["Temp"]
        finally:
            plt.close(fig)

    def test_a_plain_twin_legend_is_still_rebuilt(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            old = ax.legend(*_merged(ax, twin), title="Series")
            legend = place_legend(ax)
            assert legend is not old
            assert legend.get_title().get_text() == "Series"
            assert [t.get_text() for t in legend.get_texts()] == [
                "Sales",
                "Margin",
            ]
        finally:
            plt.close(fig)

    def test_separate_plain_legends_still_merge(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend()
            twin.legend()
            legend = place_legend(ax)
            assert len(legend.get_texts()) == 2
            assert [a.get_legend() for a in (ax, twin)].count(None) == 1
        finally:
            plt.close(fig)


def _texts(legend) -> list[str]:
    return [t.get_text() for t in legend.get_texts()]


def _lone_axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    (a,) = ax.plot([1, 2], label="A")
    return fig, ax, a


class TestPlacedLegendFollowsTheArtists:
    """A legend ``place_legend`` built is the library's: it follows the data.

    Series added or removed since appear in or leave the next call's
    legend, which keeps the settings; a legend the caller built (or
    edited) after it is the caller's and keeps the explicit rule.
    """

    def test_series_added_on_a_lone_axes(self) -> None:
        fig, ax, _a = _lone_axes()
        try:
            first = place_legend(ax, title="Series", frameon=False)
            assert first._dm_placed_legend is True
            ax.plot([2, 1], label="B")
            legend = place_legend(ax)
            assert _texts(legend) == ["A", "B"]
            assert legend.get_title().get_text() == "Series"
            assert not legend.get_frame_on()
            assert ax.get_legend() is legend
            assert legend._dm_placed_legend is True
        finally:
            plt.close(fig)

    def test_series_added_on_a_twin_pair(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            place_legend(ax, title="Series", frameon=False)
            twin.plot(np.arange(1, 7), np.full(6, 6.0), label="Target")
            legend = place_legend(ax)
            assert _texts(legend) == ["Sales", "Margin", "Target"]
            assert legend.get_title().get_text() == "Series"
            assert not legend.get_frame_on()
            assert twin.get_legend() is legend
            assert ax.get_legend() is None
        finally:
            plt.close(fig)

    def test_series_added_on_the_other_twin_by_zorder(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.set_zorder(twin.get_zorder() + 1)
            ax.patch.set_visible(False)
            place_legend(twin, title="Series")
            ax.plot(np.arange(1, 7), np.full(6, 12.0), label="Plan")
            legend = place_legend(twin)
            # matplotlib lists an Axes' lines before its bar containers.
            assert _texts(legend) == ["Plan", "Sales", "Margin"]
            assert legend.get_title().get_text() == "Series"
            assert ax.get_legend() is legend
            assert twin.get_legend() is None
        finally:
            plt.close(fig)

    def test_series_removed_on_a_lone_axes(self) -> None:
        fig, ax, a = _lone_axes()
        try:
            ax.plot([2, 1], label="B")
            place_legend(ax, title="Series")
            a.remove()
            legend = place_legend(ax)
            assert _texts(legend) == ["B"]
            assert legend.get_title().get_text() == "Series"
        finally:
            plt.close(fig)

    def test_series_removed_on_a_twin_pair(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            place_legend(ax, loc="above")
            twin.get_lines()[0].remove()
            legend = place_legend(ax, loc="above")
            assert _texts(legend) == ["Sales"]
            assert [a.get_legend() for a in (ax, twin)].count(legend) == 1
        finally:
            plt.close(fig)

    def test_last_series_removed_takes_the_legend(self) -> None:
        fig, ax, a = _lone_axes()
        try:
            place_legend(ax)
            a.remove()
            assert place_legend(ax) is None
            assert ax.get_legend() is None
        finally:
            plt.close(fig)

    def test_caller_partial_legend_after_a_placement_wins(self) -> None:
        fig, ax, _a = _lone_axes()
        try:
            (b,) = ax.plot([2, 1], label="B")
            place_legend(ax)
            kept = ax.legend([b], ["B"])
            assert place_legend(ax) is kept
            assert _texts(kept) == ["B"]
            assert not getattr(kept, "_dm_placed_legend", False)
        finally:
            plt.close(fig)

    def test_caller_edit_of_a_placed_entry_wins(self) -> None:
        fig, ax, _a = _lone_axes()
        try:
            legend = place_legend(ax)
            legend.get_texts()[0].set_text("Pretty A")
            assert place_legend(ax) is legend
            assert _texts(legend) == ["Pretty A"]
        finally:
            plt.close(fig)

    def test_settings_passed_again_win(self) -> None:
        fig, ax, _a = _lone_axes()
        try:
            place_legend(ax, title="Old")
            ax.plot([2, 1], label="B")
            legend = place_legend(ax, title="New")
            assert _texts(legend) == ["A", "B"]
            assert legend.get_title().get_text() == "New"
        finally:
            plt.close(fig)


class TestMoreSettingsKept:
    """Draggable, font properties, label colour and marker scale survive."""

    def test_font_weight_family_colour_markerscale_draggable(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend(
                *_merged(ax, twin),
                title="T",
                prop={"weight": "bold", "family": "monospace", "size": 8},
                title_fontproperties={"weight": "bold", "size": 10},
                labelcolor="red",
                markerscale=2.0,
                draggable=True,
            )
            legend = place_legend(ax)
            text = legend.get_texts()[0]
            assert text.get_fontweight() == "bold"
            assert text.get_fontfamily() == ["monospace"]
            assert text.get_fontsize() == 8
            assert to_rgba(text.get_color()) == to_rgba("red")
            assert legend.get_title().get_fontweight() == "bold"
            assert legend.get_title().get_fontsize() == 10
            assert legend.markerscale == 2.0
            assert legend.get_draggable()
        finally:
            plt.close(fig)

    def test_caller_fontsize_wins_over_kept_font_properties(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend(*_merged(ax, twin), prop={"weight": "bold", "size": 8})
            legend = place_legend(ax, fontsize=11)
            assert legend.get_texts()[0].get_fontsize() == 11
        finally:
            plt.close(fig)

    def test_defaults_are_not_pinned_by_the_new_settings(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            twin.legend()
            legend = place_legend(ax)
            assert legend.markerscale == plt.rcParams["legend.markerscale"]
            assert not legend.get_draggable()
        finally:
            plt.close(fig)


def _corner(fig, ax, legend) -> tuple[float, float]:
    """The legend's centre as a fraction of the axes box, after a draw."""
    fig.canvas.draw()
    box = legend.get_window_extent()
    frame = ax.get_window_extent()
    return (
        (box.x0 + box.x1) / 2 / frame.width - frame.x0 / frame.width,
        (box.y0 + box.y1) / 2 / frame.height - frame.y0 / frame.height,
    )


class TestUntouchedLegendFollowsPlacement:
    """An explicit loc moves an untouched legend; a rebuild-only one warns."""

    def _kept(self):
        fig, ax, twin, a, b = _unlabeled_pair()
        kept = ax.legend([(a, b)], ["Both"], loc="upper left")
        return fig, ax, kept

    def test_loc_is_applied(self) -> None:
        fig, ax, kept = self._kept()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                assert place_legend(ax, loc="lower right") is kept
            cx, cy = _corner(fig, ax, kept)
            assert cx > 0.5 and cy < 0.5  # lower right
        finally:
            plt.close(fig)

    def test_bbox_to_anchor_is_applied(self) -> None:
        fig, ax, kept = self._kept()
        try:
            place_legend(ax, loc="upper left", bbox_to_anchor=(1.0, 1.0))
            assert tuple(kept.get_bbox_to_anchor().bounds[:2]) != (0.0, 0.0)
        finally:
            plt.close(fig)

    def test_default_loc_leaves_it_where_it_is(self) -> None:
        fig, ax, kept = self._kept()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                place_legend(ax)
            cx, cy = _corner(fig, ax, kept)
            assert cx < 0.5 and cy > 0.5  # upper left
        finally:
            plt.close(fig)

    def test_outside_side_warns_and_leaves_it(self) -> None:
        fig, ax, kept = self._kept()
        try:
            with pytest.warns(UserWarning, match="above"):
                assert place_legend(ax, loc="above") is kept
            cx, cy = _corner(fig, ax, kept)
            assert cx < 0.5 and cy > 0.5  # still upper left
        finally:
            plt.close(fig)

    def test_lone_axes_explicit_labels_kept_and_placed(self) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        try:
            ax.plot([1, 2], label="raw")
            kept = ax.legend(["Pretty"], loc="upper left")
            assert place_legend(ax, loc="lower left") is kept
            assert [t.get_text() for t in kept.get_texts()] == ["Pretty"]
            cx, cy = _corner(fig, ax, kept)
            assert cx < 0.5 and cy < 0.5  # lower left
        finally:
            plt.close(fig)


class TestFailsSafeWhenStructureIsUnreadable:
    """A legend whose entries cannot be read or matched is never rebuilt."""

    @pytest.mark.parametrize("order", ["tuple-first", "plain-first"])
    def test_duplicate_label_tuple_and_plain_stays_untouched(
        self, order: str
    ) -> None:
        fig, ax, twin = _twin_pair()
        try:
            bar = ax.containers[0]
            line = twin.get_lines()[0]
            entries = [(bar, line), bar]
            if order == "plain-first":
                entries.reverse()
            kept = ax.legend(entries, ["Sales", "Sales"])
            assert place_legend(ax) is kept
            assert ax.get_legend() is kept
            assert len(kept.get_texts()) == 2
        finally:
            plt.close(fig)

    def test_legend_with_a_dropped_entry_of_its_own_axes_untouched(
        self,
    ) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.plot([1, 2], label="Extra")
            kept = ax.legend(
                [ax.containers[0], twin.get_lines()[0]], ["Sales", "Margin"]
            )
            assert place_legend(ax) is kept
            assert len(kept.get_texts()) == 2
        finally:
            plt.close(fig)

    def test_legend_of_one_axes_only_still_merges_the_twin(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend()
            legend = place_legend(ax)
            assert [t.get_text() for t in legend.get_texts()] == [
                "Sales",
                "Margin",
            ]
        finally:
            plt.close(fig)

    @pytest.mark.parametrize("failure", ["empty", "raises"])
    def test_unreadable_structure_is_untouched_and_still_placed(
        self, monkeypatch, failure: str
    ) -> None:
        import dartwork_mpl.annotation._legend_entries as legend_entries

        fig, ax, twin = _twin_pair()
        try:
            kept = ax.legend(*_merged(ax, twin), loc="upper left")

            def unreadable(legend):
                if failure == "raises":
                    raise AttributeError("no offset boxes")
                return []

            monkeypatch.setattr(legend_entries, "_entry_signatures", unreadable)
            assert place_legend(ax, loc="lower right") is kept
            assert ax.get_legend() is kept
            cx, cy = _corner(fig, ax, kept)
            assert cx > 0.5 and cy < 0.5
        finally:
            plt.close(fig)

    def test_ordinary_twin_pair_still_merges(self) -> None:
        fig, ax, twin = _twin_pair()
        try:
            ax.legend()
            twin.legend()
            legend = place_legend(ax)
            assert [t.get_text() for t in legend.get_texts()] == [
                "Sales",
                "Margin",
            ]
        finally:
            plt.close(fig)
