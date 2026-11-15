"""Each named edge case of the default canvas: when it fires and what it fixes.

The decision-level tests call ``settle`` with hand-made facts. The drawn tests
check the reason each case exists on real figures.
"""

from __future__ import annotations

import warnings
from itertools import pairwise

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer
from dartwork_mpl.edgecase import settle
from dartwork_mpl.size import decide
from dartwork_mpl.size.edges import EDGES
from dartwork_mpl.size.model import (
    CanvasFacts,
    CanvasKind,
    CanvasRequest,
    Family,
    Grid,
    NameWidths,
    Page,
)

REPORT, PAPER, SLIDES = Page(), Page(Family.PAPER), Page(Family.SLIDES)
TEMPLATES_WITH_NAMES = (
    "advanced/bar.py",
    "waterfall.py",
    "advanced/boxplot.py",
    "advanced/violin.py",
)
CM = 2.54


def _settle(
    request: CanvasRequest, page: Page, names: NameWidths | None = None
) -> tuple[tuple[float, float], tuple[str, ...]]:
    plan = decide.canvas(request, page)
    settled = settle(CanvasFacts(request, page, names), plan, EDGES)
    width, height = settled.plan.size().inches
    return (round(width * CM, 2), round(height * CM, 2)), settled.fired


def _grouped(points: int, series: int) -> CanvasRequest:
    return CanvasRequest(CanvasKind.GROUPED, n_points=points, n_series=series)


class TestGroupedValueLabels:
    """grouped-value-labels: the width holds every bar's value label."""

    @pytest.mark.parametrize(
        ("page", "groups", "series", "width"),
        [
            (SLIDES, 4, 3, 15.4),  # 12 bars
            (SLIDES, 3, 3, 11.4),  # 9 fit half the body
            (SLIDES, 6, 3, 23.4),
            (REPORT, 9, 3, 14.5),  # 27 bars
            (REPORT, 8, 5, 17.0),
            (Page(Family.POSTER, 1.5), 9, 3, 22.0),
        ],
    )
    def test_width_holds_the_bars(
        self, page: Page, groups: int, series: int, width: float
    ) -> None:
        size, fired = _settle(_grouped(groups, series), page)
        assert size[0] == width
        assert "grouped-value-labels" in fired

    def test_a_journal_column_stays_a_column(self) -> None:
        size, fired = _settle(_grouped(8, 5), PAPER)
        assert size[0] == 9.0 and fired == ()

    def test_every_value_label_shows_on_the_slide(self) -> None:
        dm.style.use("presentation")
        fig, ax = plt.subplots(
            figsize=dm.figsize_for("grouped", n_points=4, n_series=3)
        )
        values = [[120, 135, 152, 178], [88, 92, 101, 109], [54, 48, 52, 55]]
        x = np.arange(4)
        for i, vals in enumerate(values):
            ax.bar(x + (i - 1) * 0.26, vals, 0.26, label=f"Series {i + 1}")
        ax.set_xticks(x, ["P1", "P2", "P3", "P4"])
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            dm.label_bars(ax)
            dm.place_legend(ax)
            dm.simple_layout(fig)


class TestFlatCategoryNames:
    """flat-category-names: names widen the canvas until they stand flat."""

    def _names(self, width_pt: float, n: int) -> NameWidths:
        return NameWidths((width_pt,) * n, 10.0)

    def test_short_names_change_nothing(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        size, _ = _settle(request, REPORT, self._names(10.0, 3))
        assert size[0] == 9.0

    def test_long_names_take_the_next_tier_that_fits(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        size, fired = _settle(request, REPORT, self._names(80.0, 3))
        assert size[0] == 12.0 and "flat-category-names" in fired

    def test_past_the_widest_the_widest(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        assert _settle(request, SLIDES, self._names(900.0, 3))[0][0] == 23.4

    def test_a_journal_column_and_a_grid_keep_their_width(self) -> None:
        names = self._names(900.0, 3)
        assert _settle(CanvasRequest(), PAPER, names)[1] == ()
        grid = CanvasRequest(grid=Grid(1, 2))
        assert _settle(grid, REPORT, names)[1] == ()

    @pytest.mark.parametrize("name", TEMPLATES_WITH_NAMES)
    def test_templates_draw_their_names_flat_on_a_slide(
        self, name: str
    ) -> None:
        """Without the names, these turned or wrapped their labels on a slide
        (0.38, 0.25, -0.78 and -0.88 em apart flat)."""
        source = dm.guide.read("template/" + name.removesuffix(".py"))
        ends = ("dm.check(fig)", "dm.save_formats(")
        source = source[: min(source.find(e) % (len(source) + 1) for e in ends)]
        source = source.replace(
            'dm.style.use("scientific")', 'dm.style.use("presentation")'
        )
        namespace: dict[str, object] = {}
        exec(compile(source, name, "exec"), namespace)
        fig = namespace["fig"]
        assert isinstance(fig, plt.Figure)
        dm.simple_layout(fig)
        fig.canvas.draw()
        labels = [
            t for t in drawn_tick_labels(fig.axes[0], "x") if t.get_text()
        ]
        renderer = get_renderer(fig)
        boxes = sorted(
            (t.get_window_extent(renderer) for t in labels), key=lambda b: b.x0
        )
        em = labels[0].get_fontsize() * fig.dpi / 72
        assert {float(t.get_rotation()) for t in labels} == {0.0}
        assert not any("\n" in t.get_text() for t in labels)
        assert min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em >= 0.5


class TestStackedColumn:
    """stacked-column: panels in one column are as tall as a grid row."""

    @pytest.mark.parametrize("page", [REPORT, PAPER])
    def test_two_stacked_panels_are_17_by_13(self, page: Page) -> None:
        size, fired = _settle(CanvasRequest(grid=Grid(2, 1)), page)
        assert size == (17.0, 13.0) and "stacked-column" in fired

    @pytest.mark.parametrize("kind", list(CanvasKind)[:7])
    def test_the_kind_does_not_matter(self, kind: CanvasKind) -> None:
        request = CanvasRequest(kind, grid=Grid(2, 1))
        assert _settle(request, REPORT)[0] == (17.0, 13.0)

    def test_two_columns_are_not_a_stack(self) -> None:
        assert (
            "stacked-column"
            not in _settle(CanvasRequest(grid=Grid(2, 2)), REPORT)[1]
        )


class TestSlideGridRows:
    """slide-grid-rows: two panel rows on a slide take the whole slide."""

    @pytest.mark.parametrize("grid", [Grid(2, 2), Grid(3, 3), Grid(2, 1)])
    def test_takes_the_whole_slide(self, grid: Grid) -> None:
        size, fired = _settle(CanvasRequest(grid=grid), SLIDES)
        assert size == (25.4, 14.29) and fired == ("slide-grid-rows",)

    def test_one_row_stays_in_the_body(self) -> None:
        size, fired = _settle(CanvasRequest(grid=Grid(1, 4)), SLIDES)
        assert size == (23.4, 10.5) and fired == ()

    def test_rows_leave_room_to_plot(self) -> None:
        """The smoke-round grid as drawn: each panel at least 4 cm tall."""
        dm.style.use("presentation")
        fig, axes = plt.subplots(
            2, 2, figsize=dm.figsize_for(nrows=2, ncols=2), sharex=True
        )
        for ax, name in zip(axes.flat, "ABCD", strict=True):
            ax.plot(range(24), [21 + (h % 12) / 6 for h in range(24)])
            ax.set_title(f"Room {name}")
        for ax in axes[-1]:
            ax.set_xlabel("Hour")
        for ax in axes[:, 0]:
            ax.set_ylabel("Indoor temp (°C)")
        dm.simple_layout(fig)
        fig.canvas.draw()
        heights = [
            ax.get_position().height * fig.get_figheight() * CM
            for ax in axes.flat
        ]
        assert min(heights) >= 4.0
