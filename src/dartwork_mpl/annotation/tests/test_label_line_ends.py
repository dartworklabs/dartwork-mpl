"""dm.label_line_ends: line names instead of a legend, one style (#523).

Asked to "label the line ends instead of a legend", agents drew the names in
the line colour, a darker shade or black, at 6, 7 or 8 pt, and widened the
x axis to fit them. The helper settles every detail; these tests read the
drawn labels.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm

YEARS = np.arange(2012, 2024)


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _gdp(ax):
    rows = {
        "Korea": [2.4, 3.2, 2.8, 2.9, 3.2, 3.2, 2.9, 2.2, -0.7, 4.3, 2.6, 1.4],
        "Japan": [1.4, 2.0, 0.3, 1.6, 0.8, 1.7, 0.6, -0.4, -4.1, 2.6, 1.0, 1.9],
        "Germany": [
            0.4,
            0.4,
            2.2,
            1.5,
            2.2,
            2.7,
            1.0,
            1.1,
            -3.8,
            3.2,
            1.8,
            -0.3,
        ],
        "France": [0.3, 0.6, 1.0, 1.1, 1.1, 2.3, 1.9, 1.8, -7.5, 6.4, 2.5, 0.9],
    }
    for name, values in rows.items():
        ax.plot(YEARS, values, label=name)
    return rows


def _fig():
    return plt.subplots(figsize=dm.figsize("12cm", "standard"))


class TestOneStyle:
    """Text, position, size, colour and the legend are the helper's."""

    def test_one_label_per_named_line_at_its_last_point(self):
        fig, ax = _fig()
        rows = _gdp(ax)
        labels = dm.label_line_ends(ax)
        assert [t.get_text() for t in labels] == list(rows)
        for t, values in zip(labels, rows.values(), strict=True):
            assert t.xy == (2023.0, values[-1])
            assert t.get_ha() == "left" and t.get_va() == "center"

    def test_preset_size_and_weight(self):
        fig, ax = _fig()
        _gdp(ax)
        for t in dm.label_line_ends(ax):
            assert t.get_fontsize() == matplotlib.rcParams["font.size"]
            assert t.get_fontweight() == matplotlib.rcParams["font.weight"]

    def test_colour_is_the_line_colour_made_readable(self):
        fig, ax = _fig()
        ax.plot([0, 1], [0, 1], color="#fea6c5", label="pale")
        ax.plot([0, 1], [1, 0], color="#000000", label="dark")
        pale, dark = dm.label_line_ends(ax)
        assert pale.get_color() == dm.ensure_contrast(
            "#fea6c5", ax.patch.get_facecolor()
        )
        assert pale.get_color() != "#fea6c5"
        assert dark.get_color() == "#000000"

    def test_legend_removed_and_limits_kept(self):
        fig, ax = _fig()
        _gdp(ax)
        ax.legend()
        before = ax.get_xlim()
        dm.label_line_ends(ax)
        assert ax.get_legend() is None
        assert ax.get_xlim() == before

    def test_named_style_wins(self):
        fig, ax = _fig()
        _gdp(ax)
        (t, *_rest) = dm.label_line_ends(ax, fontsize=10, color="red")
        assert t.get_fontsize() == 10 and t.get_color() == "red"


class TestSpacing:
    """Labels that would overlap move apart, keep their order, stay in view."""

    def test_close_ends_do_not_overlap(self):
        fig, ax = _fig()
        for i, end in enumerate([1.00, 1.02, 1.04, 3.0]):
            ax.plot([0, 1], [0, end], label=f"s{i}")
        labels = dm.label_line_ends(ax)
        dm.simple_layout(fig)
        fig.canvas.draw()
        boxes = sorted(
            (t.get_window_extent() for t in labels), key=lambda b: b.y0
        )
        for lower, upper in pairwise(boxes):
            assert lower.y1 <= upper.y0 + 0.5
        order = [
            t.get_text()
            for t in sorted(labels, key=lambda t: t.get_window_extent().y0)
        ]
        assert order == ["s0", "s1", "s2", "s3"]

    def test_labels_stay_inside_the_canvas_after_layout(self):
        fig, ax = _fig()
        _gdp(ax)
        labels = dm.label_line_ends(ax)
        dm.simple_layout(fig)
        fig.canvas.draw()
        width = fig.bbox.width
        assert all(t.get_window_extent().x1 <= width + 0.5 for t in labels)

    def test_unlabelled_and_empty_lines_are_skipped(self):
        fig, ax = _fig()
        ax.plot([0, 1], [0, 1], label="a")
        ax.axhline(0.5)  # label starts with "_"
        ax.plot([np.nan, np.nan], [np.nan, np.nan], label="empty")
        assert [t.get_text() for t in dm.label_line_ends(ax)] == ["a"]

    def test_gap_in_the_data_uses_the_last_finite_point(self):
        fig, ax = _fig()
        ax.plot([0, 1, 2], [1.0, 2.0, np.nan], label="a")
        (t,) = dm.label_line_ends(ax)
        assert t.xy == (1.0, 2.0)

    def test_labels_stay_apart_after_the_layout_shrinks_the_axes(self):
        # Spaced at the call, the labels overlapped again once simple_layout
        # shrank the Axes for a three-line note (local codex review,
        # 2026-11-04): -12.3 px between neighbours at 300 dpi.
        dm.style.use("presentation")
        fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=2, n_series=4))
        for name, end in zip(
            ["Japan", "Egypt", "Germany", "France"],
            [1, 1.3, 1.6, 3],
            strict=True,
        ):
            ax.plot([0, 1], [0, end], label=name)
        ax.set(xlabel="Year", ylabel="Value")
        dm.add_note(
            fig, "Source: example data\nProvisional\nUpdated 2026-11-04"
        )
        labels = dm.label_line_ends(ax)
        dm.simple_layout(fig)
        fig.canvas.draw()
        boxes = sorted(
            (t.get_window_extent() for t in labels), key=lambda b: b.y0
        )
        assert all(b.y1 <= c.y0 + 0.5 for b, c in pairwise(boxes))
        found = dm.validate_figure(fig, checks=("OVERLAP",), quiet=True)
        assert found == []
        plt.close(fig)

    def _crowded(self):
        dm.style.use("presentation")
        fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=2, n_series=4))
        for name, end in zip(
            ["Japan", "Egypt", "Germany", "France"],
            [1, 1.3, 1.6, 3],
            strict=True,
        ):
            ax.plot([0, 1], [0, end], label=name)
        ax.set(xlabel="Year", ylabel="Value")
        dm.add_note(
            fig, "Source: example data\nProvisional\nUpdated 2026-11-04"
        )
        return fig, ax

    def test_a_label_moved_after_the_call_keeps_its_place(self):
        fig, ax = self._crowded()
        labels = dm.label_line_ends(ax)
        labels[0].set_position((80, 40))
        dm.simple_layout(fig)
        assert tuple(labels[0].xyann) == (80, 40)
        plt.close(fig)

    def test_every_call_on_an_axes_is_spaced_again(self):
        fig, ax = self._crowded()
        lines = ax.get_lines()
        first = dm.label_line_ends(ax, lines[:2])
        second = dm.label_line_ends(ax, lines[2:])
        dm.simple_layout(fig)
        fig.canvas.draw()
        for group in (first, second):
            boxes = sorted(
                (t.get_window_extent() for t in group), key=lambda b: b.y0
            )
            assert all(b.y1 <= c.y0 + 0.5 for b, c in pairwise(boxes))
        plt.close(fig)
