"""``label_axes`` keeps panel letters off the panel titles (#523).

With ``set_title(..., loc="left")`` per panel and a shared y axis, the
default letter position (just left of the spine, above the axes) put "a"
on "Line A" (the advanced small_multiples template). With ``x="auto"`` a
left title now always takes the letter onto its line, before the title;
a centre or right title does only when the letter would touch it.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import axes_titles
from dartwork_mpl.annotation import label_axes
from tests.support.mpl_observe import drawn_renderer

TOL_PX = 0.5


def _left(ax):
    return axes_titles(ax)["left"]


def _grid(preset: str):
    """A 2 x 3 shared-y grid with a left title per panel, like the template."""
    dm.style.use(preset)
    fig, axes = plt.subplots(
        2, 3, figsize=dm.figsize("17cm", "wide"), sharex=True, sharey=True
    )
    months = np.arange(24)
    for i, ax in enumerate(axes.flat):
        ax.plot(months, 50 + i * months)
        ax.set_title(
            f"Line {'ABCDEF'[i]}",
            loc="left",
            fontsize=dm.fs(0),
            fontweight=dm.fw(1),
            pad=4,
        )
    return fig, list(axes.flat)


def _gap_px(fig, text) -> float:
    return 0.5 * text.get_fontsize() * fig.dpi / 72.0


class TestLeftTitles:
    """A left title takes the panel letter onto its line, just before it."""

    @pytest.mark.parametrize("preset", ("report", "scientific"))
    def test_letters_clear_left_titles_without_overlap_findings(
        self, preset: str
    ) -> None:
        fig, axes = _grid(preset)
        sizes = [_left(ax).get_fontsize() for ax in axes]
        texts = label_axes(axes)
        renderer = drawn_renderer(fig)
        for ax, text, size in zip(axes, texts, sizes, strict=True):
            title = _left(ax)
            label_box = text.get_window_extent(renderer)
            title_box = title.get_window_extent(renderer)
            assert not label_box.overlaps(title_box)
            assert title_box.x0 - label_box.x1 == pytest.approx(
                _gap_px(fig, text), abs=TOL_PX
            )
            assert label_box.y0 == pytest.approx(title_box.y0, abs=TOL_PX)
            assert title.get_fontsize() == size
            assert title.get_text().startswith("Line ")
        ids = {
            w.check_id
            for w in dm.validate_figure(fig, quiet=True)
            if w.check_id in {"OVERLAP", "CROSS_AXES_OVERLAP"}
        }
        assert ids == set()
        plt.close(fig)

    def test_letters_follow_the_title_through_simple_layout(self) -> None:
        fig, axes = _grid("report")
        texts = label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        for ax, text in zip(axes, texts, strict=True):
            label_box = text.get_window_extent(renderer)
            title_box = _left(ax).get_window_extent(renderer)
            assert title_box.x0 - label_box.x1 == pytest.approx(
                _gap_px(fig, text), abs=TOL_PX
            )
        plt.close(fig)

    def test_letter_follows_a_title_lifted_over_a_legend(self) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot([0, 1], [0, 1], label="one")
        ax.plot([0, 1], [1, 0], label="two")
        # Long enough to run over the centred legend, so the title is lifted.
        ax.set_title("A left headline that runs over the legend", loc="left")
        (text,) = label_axes([ax])
        dm.place_legend(ax, loc="above")
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        legend_box = ax.get_legend().get_window_extent(renderer)
        assert _left(ax).get_window_extent(renderer).x1 > legend_box.x0
        label_box = text.get_window_extent(renderer)
        assert label_box.y0 >= legend_box.y1 - TOL_PX
        assert label_box.y0 == pytest.approx(
            _left(ax).get_window_extent(renderer).y0, abs=TOL_PX
        )
        plt.close(fig)


class TestCallerAndOtherTitles:
    """Explicit positions win; centre titles move the letter only on contact."""

    def test_explicit_x_wins(self) -> None:
        fig, axes = _grid("report")
        texts = label_axes(axes, x=-0.02)
        for text in texts:
            assert text.get_position() == (-0.02, 1.05)
        plt.close(fig)

    def test_explicit_y_is_kept_before_the_title(self) -> None:
        fig, axes = _grid("report")
        texts = label_axes(axes, y=1.2)
        renderer = drawn_renderer(fig)
        for ax, text in zip(axes, texts, strict=True):
            label_box = text.get_window_extent(renderer)
            expected = ax.transAxes.transform((0.0, 1.2))[1]
            assert label_box.y0 == pytest.approx(expected, abs=TOL_PX)
            assert label_box.x1 <= _left(ax).get_window_extent(renderer).x0
        plt.close(fig)

    def test_no_title_keeps_the_default_spot(self) -> None:
        fig, (left, right) = plt.subplots(1, 2)
        left.set_ylabel("Value")
        texts = label_axes([left, right])
        assert [t.get_position() for t in texts] == [
            (-0.18, 1.05),
            (-0.02, 1.05),
        ]
        plt.close(fig)

    def test_short_centre_title_keeps_the_default_spot(self) -> None:
        fig, ax = plt.subplots()
        ax.set_title("Short")
        (text,) = label_axes([ax])
        assert text.get_position() == (-0.02, 1.05)
        plt.close(fig)

    def test_centre_title_reaching_the_letter_moves_it(self) -> None:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
        ax.set_title("A centre title wider than its own panel here")
        (text,) = label_axes([ax])
        renderer = drawn_renderer(fig)
        label_box = text.get_window_extent(renderer)
        title_box = ax.title.get_window_extent(renderer)
        assert not label_box.overlaps(title_box)
        assert label_box.x1 <= title_box.x0
        plt.close(fig)
