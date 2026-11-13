"""``label_axes(x="auto")`` places letters from what each panel draws, in points.

The 0.7.0 letter sat at an Axes fraction (x = -0.18 with a y-axis name,
-0.02 without; y = 1.05), so its distance from the spine changed with the
panel's size and ignored the real width of tick labels and axis names. In
the insulation-aging figures (17 cm, 1 x 2 and 2 x 2, colour bars) that put
letters inside long category tick labels (-81.7 pt), over a long vertical
axis name (-5.8 pt), and at a different place in every figure. The owner
fixed the rule over three PoCs (2026-11-13): the letter's left edge on the
outer edge of the y-axis name, a column taking its leftmost; its baseline
on the title's baseline. These tests pin those rules in points on the three
failing shapes, after ``dm.simple_layout`` has fitted the figure.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

TOL_PT = 0.25


def _pt(fig) -> float:
    """Display pixels per point."""
    return fig.dpi / 72.0


def _baseline(text) -> float:
    return float(text.get_transform().transform(text.get_position())[1])


def _title_baseline(ax) -> float:
    titles = [
        t
        for t in (ax.title, ax._left_title, ax._right_title)
        if t.get_visible() and t.get_text().strip()
    ]
    return max(_baseline(t) for t in titles)


def _ytick_box(ax, renderer):
    boxes = [
        t.label1.get_window_extent(renderer)
        for t in ax.yaxis.get_major_ticks()
        if t.label1.get_visible()
        and t.label1.get_text().strip()
        and min(ax.get_ylim()) <= t.get_loc() <= max(ax.get_ylim())
    ]
    return matplotlib.transforms.Bbox.union(boxes)


@pytest.fixture(autouse=True)
def _scientific():
    """Every figure here is a 17 cm scientific figure, closed afterwards."""
    dm.style.use("scientific")
    yield
    plt.close("all")


def _colorbar_pair():
    """1 x 2 with a colour bar beside each panel (insulation-aging fig01)."""
    rng = np.random.default_rng(1)
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
    for ax, title in zip(axes, ("Temperature", "Moisture"), strict=True):
        image = ax.imshow(rng.random((12, 20)), aspect="auto")
        fig.colorbar(image, ax=ax, label="Value [-]")
        ax.set_xlabel("Position [mm]")
        ax.set_title(title)
    axes[0].set_ylabel("Depth [mm]")
    axes[1].set_ylabel("Height above floor [mm]")
    return fig, axes


def _category_pair():
    """a: long category tick labels and no y-axis name; b: a y-axis name
    (insulation-aging fig02 / fig05)."""
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
    names = ["Density-conditional model", "Marginal model", "Pooled baseline"]
    axes[0].barh(names, [0.62, 0.48, 0.31])
    axes[0].set_title("Model comparison")
    axes[1].plot([0, 10], [1, 0.1])
    axes[1].set_ylabel("Probability [-]")
    axes[1].set_title("Survival")
    return fig, axes


def _tall_name_grid(height: str = "4.5cm"):
    """2 x 2 of short panels; b and d have no title. At the default height
    b's y-axis name is taller than b (the -5.8 pt case). A wrapped name
    breaks before its unit only (the insulation-aging owner's rule)."""
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", height))
    x = np.linspace(0, 1, 20)
    for i, ax in enumerate(axes.flat):
        ax.plot(x, x ** (i + 1))
    axes[0, 0].set_ylabel("Conductivity ratio\n[-]")
    axes[0, 1].set_ylabel("Relative moisture content after ageing\n[-]")
    axes[1, 0].set_ylabel("Ratio [-]")
    axes[1, 1].set_ylabel("Density")
    axes[0, 0].set_title("Conductivity")
    axes[1, 0].set_title("Ratio")
    return fig, axes


class TestHorizontal:
    """The letter's left edge is the outer edge of the y-axis name."""

    def test_letter_starts_at_the_y_name_with_colour_bars(self) -> None:
        """Each panel of the colour-bar pair: 0 pt from its y-axis name."""
        fig, axes = _colorbar_pair()
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        for ax, text in zip(axes, texts, strict=True):
            name = ax.yaxis.label.get_window_extent(renderer)
            dx = (text.get_window_extent(renderer).x0 - name.x0) / _pt(fig)
            assert dx == pytest.approx(0.0, abs=TOL_PT)

    def test_column_takes_its_leftmost_y_name(self) -> None:
        """c's short name: its letter goes to a's longer name's edge."""
        fig, axes = _tall_name_grid()
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        flat = list(axes.flat)
        for top, bottom in ((0, 2), (1, 3)):
            names = [
                flat[i].yaxis.label.get_window_extent(renderer).x0
                for i in (top, bottom)
            ]
            for i in (top, bottom):
                dx = (
                    texts[i].get_window_extent(renderer).x0 - min(names)
                ) / _pt(fig)
                assert dx == pytest.approx(0.0, abs=TOL_PT)

    def test_panel_without_a_name_keeps_its_neighbours_spine_distance(
        self,
    ) -> None:
        """Long category ticks and no y name: the letter keeps b's distance
        from the spine instead of sitting on the spine inside the ticks."""
        fig, axes = _category_pair()
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        reach = [
            (
                ax.get_window_extent(renderer).x0
                - t.get_window_extent(renderer).x0
            )
            / _pt(fig)
            for ax, t in zip(axes, texts, strict=True)
        ]
        assert reach[0] == pytest.approx(reach[1], abs=TOL_PT)
        assert reach[0] > 20.0  # the 0.7.0 letter sat 2 % of the width out
        # and above the tick labels it now overlaps horizontally
        ticks = _ytick_box(axes[0], renderer)
        assert texts[0].get_window_extent(renderer).y0 > ticks.y1

    def test_distance_is_points_whatever_the_panel_width(self) -> None:
        """Panels 1 : 3 wide with the same y name: one distance in points."""
        fig, axes = plt.subplots(
            1, 2, figsize=dm.figsize("17cm", "6cm"), width_ratios=[1, 3]
        )
        for ax in axes:
            ax.plot([0, 1], [0, 100])
            ax.set_ylabel("Load [kW]")
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        reach = [
            (
                ax.get_window_extent(renderer).x0
                - t.get_window_extent(renderer).x0
            )
            / _pt(fig)
            for ax, t in zip(axes, texts, strict=True)
        ]
        assert reach[0] == pytest.approx(reach[1], abs=TOL_PT)

    def test_no_y_name_anywhere_takes_where_a_name_would_be(self) -> None:
        """Past the tick labels by the name's pad and line height."""
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "6cm"))
        ax.plot([0, 1], [0, 1000])
        (text,) = dm.label_axes([ax])
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        _w, height, _d = renderer.get_text_width_height_descent(
            "Ag", ax.yaxis.label.get_fontproperties(), ismath=False
        )
        expected = (
            _ytick_box(ax, renderer).x0 - ax.yaxis.labelpad * _pt(fig) - height
        )
        dx = (text.get_window_extent(renderer).x0 - expected) / _pt(fig)
        assert dx == pytest.approx(0.0, abs=TOL_PT)

    def test_subfigures_keep_their_own_columns(self) -> None:
        """Row 0 / column 0 of one SubFigure is not that of another: each
        letter stays on its own panel's y name, not a neighbour's."""
        fig = plt.figure(figsize=dm.figsize("17cm", "7cm"))
        left, right = fig.subfigures(1, 2)
        a = left.subplots()
        b = right.subplots()
        a.set_ylabel("Short")
        b.set_ylabel("A much longer axis name\n[unit]")
        b.plot([0, 1], [0, 100000])
        a.set_title("Left")
        b.set_title("Right taller title\nin two lines")
        texts = dm.label_axes([a, b])
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        for ax, text in zip((a, b), texts, strict=True):
            name = ax.yaxis.label.get_window_extent(renderer)
            dx = (text.get_window_extent(renderer).x0 - name.x0) / _pt(fig)
            assert dx == pytest.approx(0.0, abs=TOL_PT)
            dy = (_baseline(text) - _title_baseline(ax)) / _pt(fig)
            assert dy == pytest.approx(0.0, abs=TOL_PT)


class TestVertical:
    """The letter's baseline is its title's; untitled panels follow the row."""

    def test_baseline_is_the_title_baseline(self) -> None:
        """Every titled panel of the three failing shapes: 0 pt (the grid
        tall enough that no y name rises into the title line)."""
        for build in (
            _colorbar_pair,
            _category_pair,
            lambda: _tall_name_grid("12cm"),
        ):
            fig, axes = build()
            flat = list(np.ravel(axes))
            texts = dm.label_axes(flat)
            dm.simple_layout(fig)
            drawn_renderer(fig)
            for ax, text in zip(flat, texts, strict=True):
                if ax.get_title():
                    dy = (_baseline(text) - _title_baseline(ax)) / _pt(fig)
                    assert dy == pytest.approx(0.0, abs=TOL_PT)
            plt.close(fig)

    def test_letter_clears_a_y_name_taller_than_its_panel(self) -> None:
        """b's name rises above b: the letter keeps at least 2 pt above it,
        and d (untitled) takes the highest baseline of its row."""
        fig, axes = _tall_name_grid()
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        renderer = drawn_renderer(fig)
        flat = list(axes.flat)
        b_name = flat[1].yaxis.label.get_window_extent(renderer)
        assert b_name.y1 > flat[1].get_window_extent(renderer).y1  # the shape
        checked = 0
        for ax, text in zip(flat, texts, strict=True):
            name = ax.yaxis.label.get_window_extent(renderer)
            box = text.get_window_extent(renderer)
            if name.x0 < box.x1 and name.x1 > box.x0:
                assert (box.y0 - name.y1) / _pt(fig) >= 2.0 - TOL_PT
                checked += 1
        assert checked >= 1
        assert _baseline(texts[3]) >= _baseline(texts[2]) - 0.5

    def test_titled_panel_keeps_its_own_title_line(self) -> None:
        """A neighbour's title lifted over a legend does not lift this
        letter off its own title (owner decision, PoC 10-B)."""
        fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "7cm"))
        for ax in axes:
            for k in range(4):
                ax.plot([0, 1], [k, k + 1], label=f"Series {k}")
            ax.set_ylabel("Value")
        axes[0].set_title("Plain")
        axes[1].set_title("Lifted")
        dm.place_legend(axes[1], loc="above")
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        drawn_renderer(fig)
        assert _title_baseline(axes[1]) - _title_baseline(axes[0]) > 5.0
        for ax, text in zip(axes, texts, strict=True):
            dy = (_baseline(text) - _title_baseline(ax)) / _pt(fig)
            assert dy == pytest.approx(0.0, abs=TOL_PT)


class TestLifecycle:
    """The letters are measured again by every layout, and only theirs."""

    def test_a_second_layout_draws_the_same_letters(self) -> None:
        """``simple_layout`` twice: no letter moves."""
        fig, axes = _tall_name_grid()
        texts = dm.label_axes(axes)
        dm.simple_layout(fig)
        first = [v for t in texts for v in t.xyann]
        dm.simple_layout(fig)
        assert [v for t in texts for v in t.xyann] == pytest.approx(
            first, abs=1e-3
        )

    def test_a_removed_letter_is_left_alone(self) -> None:
        """A letter removed after ``label_axes`` does not come back."""
        fig, axes = _colorbar_pair()
        texts = dm.label_axes(axes)
        texts[1].remove()
        dm.simple_layout(fig)
        assert texts[1] not in axes[1].texts
        assert texts[0] in axes[0].texts

    def test_labels_are_annotations_offset_in_points(self) -> None:
        """Points from the Axes corner, so a resize keeps the distance."""
        fig, axes = _colorbar_pair()
        texts = dm.label_axes(axes)
        for text in texts:
            assert text.xy == (0.0, 1.0)
            assert text.anncoords == "offset points"
